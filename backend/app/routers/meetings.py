"""회의록 - 업로드(받아쓰기) · 저장과 세 항목 구분 · 목록 · 상세 · 수정 · 삭제 (스토리보드 C, D)"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, File, Query, UploadFile
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from ..config import MAX_UPLOAD_BYTES
from ..db import get_db
from ..deps import get_current_user, require_team
from ..errors import ApiError
from ..models import Meeting, Membership, Todo, User
from ..serializers import todo_dict, user_names
from ..services import activity
from ..services.gemini import GeminiError, Organized, UNDECIDED, get_gemini
from ..util import iso, parse_iso

router = APIRouter(tags=["meeting"])


# ---------- 업로드 / 받아쓰기 ----------
def sniff_audio(data: bytes) -> str | None:
    """확장자가 아니라 파일 내용으로 판정한다. mp3 · wav 만 통과"""
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:3] == b"ID3":
        return "audio/mpeg"
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "audio/mpeg"
    return None


@router.post("/api/upload", summary="녹취 파일 받아쓰기 (저장하지 않음)")
async def upload(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
    gemini=Depends(get_gemini),
):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "4.4MB 를 넘는 파일")
    mime = sniff_audio(data)
    if mime is None:
        raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "mp3 또는 wav 만 올릴 수 있음")
    try:
        text = await run_in_threadpool(gemini.transcribe, data, mime)
    except GeminiError as e:
        raise ApiError(502, "UPSTREAM_ERROR", f"받아쓰기에 실패함: {e}")
    return {"body": text}


# ---------- 공통 ----------
class MeetingIn(BaseModel):
    title: str
    met_at: str
    attendees: str = ""
    body: str


class MeetingPatch(BaseModel):
    title: str | None = None
    met_at: str | None = None
    attendees: str | None = None
    body: str | None = None


def _met_at(raw: str) -> datetime:
    try:
        return parse_iso(raw)
    except ValueError:
        raise ApiError(400, "VALIDATION_ERROR", "회의 시각 형식이 올바르지 않음")


def _required(value: str, label: str, limit: int | None = None) -> str:
    text = value.strip()
    if not text or (limit and len(text) > limit):
        raise ApiError(400, "VALIDATION_ERROR", f"{label} 은(는) 필수")
    return text


def load_meeting(db: Session, user: User, meeting_id: int) -> tuple[Meeting, Membership]:
    """없는 회의록과 남의 팀 회의록을 같은 404 로 응답"""
    meeting = db.get(Meeting, meeting_id)
    if meeting is not None:
        _, membership = _team_of(db, user, meeting.team_id)
        return meeting, membership
    raise ApiError(404, "MEETING_NOT_FOUND", "없는 회의록")


def _team_of(db: Session, user: User, team_id: int):
    try:
        return require_team(db, user, team_id)
    except ApiError:
        raise ApiError(404, "MEETING_NOT_FOUND", "없는 회의록")


def can_edit(meeting: Meeting, user: User, membership: Membership) -> bool:
    return meeting.author_id == user.id or membership.role == "owner"


def _decision_count(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def _list_row(m: Meeting, done: int, total: int) -> dict:
    return {
        "id": m.id,
        "title": m.title,
        "met_at": iso(m.met_at),
        "attendees": m.attendees,
        "summary": m.summary,
        "created_at": iso(m.created_at),
        "todo_done_count": done,
        "todo_total_count": total,
        "decision_count": _decision_count(m.decisions),
    }


def _detail(db: Session, m: Meeting, user: User, membership: Membership) -> dict:
    todos = db.query(Todo).filter(Todo.meeting_id == m.id).order_by(Todo.id).all()
    names = user_names(db, {t.assignee_id for t in todos if t.assignee_id})
    return {
        "id": m.id,
        "team_id": m.team_id,
        "title": m.title,
        "met_at": iso(m.met_at),
        "attendees": m.attendees,
        "body": m.body,
        "summary": m.summary,
        "decisions": m.decisions,
        "author_id": m.author_id,
        "created_at": iso(m.created_at),
        "can_edit": can_edit(m, user, membership),
        "todos": [todo_dict(t, names.get(t.assignee_id)) for t in todos],
    }


# ---------- 저장과 세 항목 구분 ----------
@router.post("/api/teams/{team_id}/meetings", status_code=201, summary="회의록 저장 (세 항목 구분 포함)")
def create_meeting(
    team_id: int,
    body: MeetingIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gemini=Depends(get_gemini),
):
    team, membership = require_team(db, user, team_id)
    title = _required(body.title, "제목", 200)
    text = _required(body.body, "본문")
    met_at = _met_at(body.met_at)

    members = (
        db.query(User)
        .join(Membership, Membership.user_id == User.id)
        .filter(Membership.team_id == team.id)
        .all()
    )
    by_name = {u.name: u.id for u in members}

    # 정리에 실패해도 회의록은 저장한다 (요약 · 결정사항 · 할 일은 빈 값)
    try:
        organized = gemini.organize(text, list(by_name), met_at)
    except GeminiError:
        organized = Organized()

    meeting = Meeting(
        team_id=team.id,
        title=title,
        met_at=met_at,
        attendees=body.attendees.strip(),
        body=text,
        summary=organized.summary,
        decisions="\n".join(organized.decisions),
        author_id=user.id,
    )
    db.add(meeting)
    db.flush()
    for item in organized.todos:
        db.add(Todo(
            meeting_id=meeting.id,
            what=item.what,
            assignee_id=by_name.get(item.assignee) if item.assignee else None,
            due_text=item.due or UNDECIDED,
        ))
    activity.record(db, team.id, user.id, "meeting_add", activity.meeting_added(title))
    db.commit()
    return _detail(db, meeting, user, membership)


# ---------- 목록 ----------
def _day(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ApiError(400, "VALIDATION_ERROR", "날짜 형식이 올바르지 않음 (YYYY-MM-DD)")


@router.get("/api/teams/{team_id}/meetings", summary="회의록 목록 (본문 없음)")
def list_meetings(
    team_id: int,
    q: str | None = None,
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    team, _ = require_team(db, user, team_id)
    query = db.query(Meeting).filter(Meeting.team_id == team.id)
    if q and q.strip():
        term = q.strip()
        query = query.filter(
            Meeting.title.icontains(term, autoescape=True) | Meeting.attendees.icontains(term, autoescape=True)
        )
    if from_:
        query = query.filter(Meeting.met_at >= datetime.combine(_day(from_), datetime.min.time()))
    if to:
        query = query.filter(Meeting.met_at < datetime.combine(_day(to) + timedelta(days=1), datetime.min.time()))
    meetings = query.order_by(Meeting.met_at.desc(), Meeting.id.desc()).all()

    counts = {
        mid: (int(done or 0), int(total))
        for mid, done, total in db.query(
            Todo.meeting_id,
            func.sum(case((Todo.status == "DONE", 1), else_=0)),
            func.count(Todo.id),
        )
        .join(Meeting, Meeting.id == Todo.meeting_id)
        .filter(Meeting.team_id == team.id)
        .group_by(Todo.meeting_id)
        .all()
    }
    return [_list_row(m, *counts.get(m.id, (0, 0))) for m in meetings]


# ---------- 상세 / 수정 / 삭제 ----------
@router.get("/api/meetings/{meeting_id}", summary="회의록 한 건 (본문 포함)")
def get_meeting(meeting_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    meeting, membership = load_meeting(db, user, meeting_id)
    return _detail(db, meeting, user, membership)


@router.put("/api/meetings/{meeting_id}", summary="회의록 수정 (올린 사람 · owner)")
def update_meeting(
    meeting_id: int,
    body: MeetingPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meeting, membership = load_meeting(db, user, meeting_id)
    if not can_edit(meeting, user, membership):
        raise ApiError(403, "FORBIDDEN", "올린 사람과 owner 만 고칠 수 있음")
    # 본문을 고쳐도 받아쓰기와 세 항목 구분은 다시 돌리지 않는다
    if body.title is not None:
        meeting.title = _required(body.title, "제목", 200)
    if body.met_at is not None:
        meeting.met_at = _met_at(body.met_at)
    if body.attendees is not None:
        meeting.attendees = body.attendees.strip()
    if body.body is not None:
        meeting.body = _required(body.body, "본문")
    db.commit()
    return _detail(db, meeting, user, membership)


@router.delete("/api/meetings/{meeting_id}", status_code=204, summary="회의록 삭제 (할 일 · 댓글도 함께)")
def delete_meeting(meeting_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    meeting, membership = load_meeting(db, user, meeting_id)
    if not can_edit(meeting, user, membership):
        raise ApiError(403, "FORBIDDEN", "올린 사람과 owner 만 지울 수 있음")
    db.delete(meeting)
    db.commit()
