"""댓글 - 등록 · 목록 · 삭제 (스토리보드 D-09 ~ D-12)"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import COMMENT_MAX_CHARS
from ..db import get_db
from ..deps import get_current_user
from ..errors import ApiError
from ..models import Comment, Meeting, User
from ..services import activity
from ..util import iso
from .meetings import load_meeting

router = APIRouter(prefix="/api", tags=["comment"])


class CommentIn(BaseModel):
    content: str


def _row(c: Comment, name: str, can_delete: bool) -> dict:
    return {
        "id": c.id,
        "user_id": c.user_id,
        "user_name": name,
        "content": c.content,
        "created_at": iso(c.created_at),
        "can_delete": can_delete,
    }


@router.post("/meetings/{meeting_id}/comments", status_code=201, summary="댓글 등록 (500자 이내)")
def add_comment(
    meeting_id: int,
    body: CommentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meeting, membership = load_meeting(db, user, meeting_id)
    content = body.content.strip()
    if not content or len(content) > COMMENT_MAX_CHARS:
        raise ApiError(400, "VALIDATION_ERROR", f"댓글은 1~{COMMENT_MAX_CHARS}자")
    comment = Comment(meeting_id=meeting.id, user_id=user.id, content=content)
    db.add(comment)
    activity.record(db, meeting.team_id, user.id, "comment_add", activity.comment_added(meeting.title))
    db.commit()
    return _row(comment, user.name, True)


@router.get("/meetings/{meeting_id}/comments", summary="댓글 목록 (오래된 순)")
def list_comments(meeting_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    meeting, membership = load_meeting(db, user, meeting_id)
    rows = (
        db.query(Comment, User.name)
        .join(User, User.id == Comment.user_id)
        .filter(Comment.meeting_id == meeting.id)
        .order_by(Comment.created_at, Comment.id)
        .all()
    )
    # 지울 수 있는 사람은 쓴 사람과 팀 owner. 서버가 판정한다
    return [_row(c, name, c.user_id == user.id or membership.role == "owner") for c, name in rows]


@router.delete("/comments/{comment_id}", status_code=204, summary="댓글 삭제 (쓴 사람 · owner)")
def delete_comment(comment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comment = db.get(Comment, comment_id)
    meeting = db.get(Meeting, comment.meeting_id) if comment else None
    if meeting is None:
        raise ApiError(404, "NOT_FOUND", "찾을 수 없음")
    try:
        _, membership = load_meeting(db, user, meeting.id)
    except ApiError:
        raise ApiError(404, "NOT_FOUND", "찾을 수 없음")
    if comment.user_id != user.id and membership.role != "owner":
        raise ApiError(403, "FORBIDDEN", "쓴 사람과 owner 만 지울 수 있음")
    db.delete(comment)
    db.commit()
