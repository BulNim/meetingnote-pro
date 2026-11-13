"""회의록 6개 - 목록 · 생성 · 단건 · 수정 · 삭제 · 녹취 업로드."""
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from .. import activity, config, gemini
from ..db import get_db
from ..errors import AppError, forbidden, validation
from ..models import Comment, Meeting, Membership, Todo, User
from ..security import current_user, membership_of, require_member
from ..serial import can_edit_meeting, meeting_detail, meeting_item

router = APIRouter(tags=["meeting"])


class MeetingIn(BaseModel):
    title: str
    met_at: str
    attendees: str = ""
    body: str


class MeetingEdit(BaseModel):
    title: str | None = None
    met_at: str | None = None
    attendees: str | None = None
    body: str | None = None


def gemini_failed(e: gemini.GeminiError) -> AppError:
    return AppError(502, "VALIDATION_ERROR", f"받아쓰기 · 구분 실패 - {e}")


def parse_when(raw: str) -> datetime:
    """ISO 8601 을 받아 UTC(tz 없음)로. tz 가 없으면 UTC 로 본다."""
    try:
        dt = datetime.fromisoformat(raw.strip())
    except (ValueError, AttributeError):
        raise validation("회의 시각은 ISO 8601 형식")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def parse_day(raw: str, name: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise validation(f"{name} 는 YYYY-MM-DD")


def visible_meeting(db: Session, user: User, meeting_id: int) -> Meeting:
    """없거나 다른 팀의 회의록은 존재를 드러내지 않고 404 MEETING_NOT_FOUND."""
    m = db.get(Meeting, meeting_id)
    mine = membership_of(db, user.id)
    if m is None or mine is None or mine.team_id != m.team_id:
        raise AppError(404, "MEETING_NOT_FOUND", "회의록을 찾을 수 없음")
    return m


def required(value: str | None, label: str) -> str:
    v = (value or "").strip()
    if not v:
        raise validation(f"{label} 필수")
    return v


@router.get("/api/teams/{team_id}/meetings", summary="회의록 목록 - body 없음. ?q= 는 제목 · 참석자만")
def list_meetings(
    team_id: int,
    q: str | None = Query(None, description="제목 또는 참석자"),
    from_: str | None = Query(None, alias="from", description="YYYY-MM-DD"),
    to: str | None = Query(None, description="YYYY-MM-DD"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_member(db, user, team_id)
    stmt = select(Meeting).where(Meeting.team_id == team_id)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Meeting.title.ilike(like), Meeting.attendees.ilike(like)))
    if from_:
        stmt = stmt.where(Meeting.met_at >= datetime.combine(parse_day(from_, "from"), time.min))
    if to:
        stmt = stmt.where(Meeting.met_at < datetime.combine(parse_day(to, "to") + timedelta(days=1), time.min))
    rows = db.scalars(stmt.order_by(Meeting.met_at.desc(), Meeting.id.desc())).all()
    return [meeting_item(db, m) for m in rows]


@router.post("/api/teams/{team_id}/meetings", status_code=201,
             summary="회의록 저장 - 본문을 요약 · 결정사항 · 할 일로 나눠 함께 저장")
def create_meeting(team_id: int, data: MeetingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    title = required(data.title, "제목")
    body = required(data.body, "본문")
    met_at = parse_when(required(data.met_at, "회의 시각"))

    members = db.execute(
        select(User.id, User.name).join(Membership, Membership.user_id == User.id).where(Membership.team_id == team_id)
    ).all()
    try:
        parts = gemini.classify(body, [n for _, n in members])
    except gemini.GeminiError as e:
        raise gemini_failed(e)  # 저장하지 않음 - 본문은 화면 칸에 남는다

    by_name = {gemini.normalize_name(n): (uid, n) for uid, n in members}
    m = Meeting(team_id=team_id, title=title, met_at=met_at, attendees=(data.attendees or "").strip(), body=body,
                summary=parts.summary.strip(),
                decisions="\n".join(d.strip() for d in parts.decisions if d.strip()),
                author_id=user.id)
    db.add(m)
    db.flush()
    activity.record(db, team_id, user.id, "meeting_add", title=title)
    for item in parts.todos:
        what = item.what.strip()
        if not what:
            continue
        hit = by_name.get(gemini.normalize_name(item.assignee)) if item.assignee else None
        t = Todo(team_id=team_id, meeting_id=m.id, what=what, due_text=item.due.strip(),
                 assignee_id=hit[0] if hit else None, author_id=user.id)
        db.add(t)
        if hit:
            activity.record(db, team_id, user.id, "todo_assign", what=what, assignee=hit[1])
    db.commit()
    return meeting_detail(db, m, user)


@router.get("/api/meetings/{meeting_id}", summary="회의록 단건 - body · todos · can_edit 포함")
def get_meeting(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return meeting_detail(db, visible_meeting(db, user, meeting_id), user)


@router.put("/api/meetings/{meeting_id}", summary="회의록 수정 - 작성자 · owner. 받아쓰기 · 구분을 다시 돌리지 않음")
def edit_meeting(meeting_id: int, data: MeetingEdit, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = visible_meeting(db, user, meeting_id)
    if not can_edit_meeting(db, user, m):
        raise forbidden("작성자와 owner 만 수정")
    if data.title is not None:
        m.title = required(data.title, "제목")
    if data.met_at is not None:
        m.met_at = parse_when(required(data.met_at, "회의 시각"))
    if data.attendees is not None:
        m.attendees = data.attendees.strip()
    if data.body is not None:
        m.body = required(data.body, "본문")
    db.commit()
    return meeting_detail(db, m, user)


@router.delete("/api/meetings/{meeting_id}", status_code=204, summary="회의록 삭제 - 딸린 할 일 · 댓글도 함께")
def delete_meeting(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = visible_meeting(db, user, meeting_id)
    if not can_edit_meeting(db, user, m):
        raise forbidden("작성자와 owner 만 삭제")
    db.execute(delete(Todo).where(Todo.meeting_id == m.id))
    db.execute(delete(Comment).where(Comment.meeting_id == m.id))
    db.delete(m)
    db.commit()
    return Response(status_code=204)


@router.post("/api/upload", summary="녹취 업로드와 받아쓰기 - mp3 · wav 만. 저장은 하지 않음")
def upload(file: UploadFile = File(...), user: User = Depends(current_user)):
    data = file.file.read()
    mime = gemini.audio_mime(data)
    if mime is None:
        raise AppError(415, "UNSUPPORTED_MEDIA_TYPE", "mp3 또는 wav 만 올릴 수 있음")
    limit = config.upload_max()
    if len(data) > limit:
        raise validation(f"파일이 너무 큼 - {limit / config.MB:g}MB 까지")
    try:
        return {"body": gemini.transcribe(data, mime)}
    except gemini.GeminiError as e:
        raise gemini_failed(e)
