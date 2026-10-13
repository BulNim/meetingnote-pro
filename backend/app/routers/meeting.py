"""meeting - 정의서 7절 Meeting 6개. 근거: 스토리보드 C(meetings.html), D(detail.html)"""
from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from .. import transcriber
from ..db import get_db
from ..deps import current_user, iso, log_activity, parse_dt, require_member
from ..errors import AppError
from ..models import Comment, Meeting, Todo, User

router = APIRouter(tags=["meeting"])

MAX_UPLOAD = 25 * 1024 * 1024
ALLOWED = {".mp3": "audio/mpeg", ".wav": "audio/wav"}


class TodoIn(BaseModel):
    what: str
    due_text: str = ""


class MeetingIn(BaseModel):
    title: str
    met_at: str
    attendees: str = ""
    body: str
    summary: str = ""
    decisions: str | list[str] = ""
    todos: list[TodoIn | str] = []


class MeetingUpdateIn(BaseModel):
    title: str | None = None
    met_at: str | None = None
    attendees: str | None = None
    body: str | None = None
    summary: str | None = None
    decisions: str | list[str] | None = None


def _decisions_text(value: str | list[str]) -> str:
    if isinstance(value, list):
        value = "\n".join(value)
    return value


def _decision_count(text: str) -> int:
    return len([ln for ln in text.splitlines() if ln.strip()])


def _todo(t: Todo, names: dict) -> dict:
    return {
        "id": t.id,
        "what": t.what,
        "assignee_id": t.assignee_id,
        "assignee_name": names.get(t.assignee_id),
        "due_text": t.due_text,
        "status": t.status,
    }


def _names(db: Session, ids: set) -> dict:
    ids = {i for i in ids if i}
    return {u.id: u.name for u in db.query(User).filter(User.id.in_(ids)).all()} if ids else {}


def _list_item(m: Meeting, done: int, total: int) -> dict:
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


def _detail(db: Session, m: Meeting) -> dict:
    names = _names(db, {t.assignee_id for t in m.todos} | {m.author_id})
    item = _list_item(m, sum(t.status == "DONE" for t in m.todos), len(m.todos))
    item.update(
        {
            "body": m.body,
            "decisions": m.decisions,
            "author_id": m.author_id,
            "author_name": names.get(m.author_id),
            "todos": [_todo(t, names) for t in sorted(m.todos, key=lambda t: t.id)],
        }
    )
    return item


def _get_meeting(db: Session, user: User, meeting_id: int) -> tuple[Meeting, object]:
    m = db.get(Meeting, meeting_id)
    if m is None:
        raise AppError(404, "MEETING_NOT_FOUND", "회의록을 찾을 수 없습니다")
    return m, require_member(db, user, m.team_id)


@router.post("/upload", summary="녹취 업로드 - 받아쓰기와 3항목 구분 (25MB · mp3 wav)")
async def upload(file: UploadFile = File(...), user: User = Depends(current_user)):
    name = (file.filename or "").lower()
    ext = name[name.rfind("."):] if "." in name else ""
    if ext not in ALLOWED:
        raise AppError(415, "UNSUPPORTED_MEDIA_TYPE", "mp3 또는 wav 파일만 올릴 수 있습니다")
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise AppError(413, "PAYLOAD_TOO_LARGE", "25MB 를 넘는 파일은 받을 수 없습니다")
    return transcriber.process(data, ALLOWED[ext])


@router.post("/teams/{team_id}/meetings", status_code=201, summary="회의록 저장")
def create_meeting(
    team_id: int, body: MeetingIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    require_member(db, user, team_id)
    if not body.title.strip() or not body.body.strip():
        raise AppError(400, "VALIDATION_ERROR", "제목과 본문은 필수입니다")
    m = Meeting(
        team_id=team_id,
        author_id=user.id,
        title=body.title.strip(),
        met_at=parse_dt(body.met_at),
        attendees=body.attendees,
        body=body.body,
        summary=body.summary,
        decisions=_decisions_text(body.decisions),
    )
    db.add(m)
    db.flush()
    for t in body.todos:
        t = TodoIn(what=t) if isinstance(t, str) else t
        if t.what.strip():
            db.add(Todo(meeting_id=m.id, what=t.what.strip(), due_text=t.due_text, status="OPEN"))
    log_activity(db, team_id, user.id, "meeting_add", m.title)
    db.commit()
    db.refresh(m)
    return _detail(db, m)


@router.get("/teams/{team_id}/meetings", summary="회의록 목록 - 본문 제외, met_at 내림차순")
def list_meetings(
    team_id: int,
    q: str | None = None,
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_member(db, user, team_id)
    query = db.query(Meeting).filter(Meeting.team_id == team_id)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(Meeting.title.ilike(like), Meeting.attendees.ilike(like)))
    if from_:
        query = query.filter(Meeting.met_at >= parse_dt(from_))
    if to:
        query = query.filter(Meeting.met_at <= parse_dt(to, end_of_day=True))
    meetings = query.order_by(Meeting.met_at.desc(), Meeting.id.desc()).all()
    counts = {
        mid: (done or 0, total)
        for mid, total, done in db.query(
            Todo.meeting_id, func.count(Todo.id), func.sum(case((Todo.status == "DONE", 1), else_=0))
        )
        .filter(Todo.meeting_id.in_([m.id for m in meetings] or [0]))
        .group_by(Todo.meeting_id)
        .all()
    }
    return [_list_item(m, *counts.get(m.id, (0, 0))) for m in meetings]


@router.get("/meetings/{meeting_id}", summary="회의록 상세 - 본문 · 3항목 · 할 일")
def get_meeting(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m, _ = _get_meeting(db, user, meeting_id)
    return _detail(db, m)


def _author_or_owner(m: Meeting, user: User, membership) -> None:
    if m.author_id != user.id and membership.role != "owner":
        raise AppError(403, "FORBIDDEN", "쓴 사람과 owner 만 할 수 있습니다")


@router.put("/meetings/{meeting_id}", summary="회의록 수정 - 작성자와 owner")
def update_meeting(
    meeting_id: int, body: MeetingUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    m, membership = _get_meeting(db, user, meeting_id)
    _author_or_owner(m, user, membership)
    if body.title is not None:
        if not body.title.strip():
            raise AppError(400, "VALIDATION_ERROR", "제목은 비울 수 없습니다")
        m.title = body.title.strip()
    if body.met_at is not None:
        m.met_at = parse_dt(body.met_at)
    for field in ("attendees", "body", "summary"):
        value = getattr(body, field)
        if value is not None:
            setattr(m, field, value)
    if body.decisions is not None:
        m.decisions = _decisions_text(body.decisions)
    db.commit()
    db.refresh(m)
    return _detail(db, m)


@router.delete("/meetings/{meeting_id}", status_code=204, summary="회의록 삭제 - 할 일 · 댓글도 함께 삭제")
def delete_meeting(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m, membership = _get_meeting(db, user, meeting_id)
    _author_or_owner(m, user, membership)
    db.delete(m)
    db.commit()
