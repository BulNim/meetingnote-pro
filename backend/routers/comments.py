"""댓글 3개 - 등록 · 목록 · 삭제."""
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import activity, config
from ..db import get_db
from ..errors import forbidden, not_found, validation
from ..models import Comment, Meeting, User
from ..security import current_user, membership_of
from ..serial import can_delete_comment, comment_out
from .meetings import visible_meeting

router = APIRouter(tags=["comment"])


class CommentIn(BaseModel):
    content: str


@router.post("/api/meetings/{meeting_id}/comments", status_code=201, summary="댓글 등록 - 1~500자, comment_add 기록")
def add_comment(meeting_id: int, data: CommentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = visible_meeting(db, user, meeting_id)
    content = data.content.strip()
    if not content or len(content) > config.COMMENT_MAX:
        raise validation(f"댓글은 1~{config.COMMENT_MAX}자")
    c = Comment(meeting_id=m.id, user_id=user.id, content=content)
    db.add(c)
    activity.record(db, m.team_id, user.id, "comment_add", title=m.title)
    db.commit()
    return comment_out(db, c, user, m.team_id)


@router.get("/api/meetings/{meeting_id}/comments", summary="댓글 목록 - 오래된 순")
def list_comments(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = visible_meeting(db, user, meeting_id)
    rows = db.scalars(select(Comment).where(Comment.meeting_id == m.id).order_by(Comment.created_at, Comment.id)).all()
    return [comment_out(db, c, user, m.team_id) for c in rows]


@router.delete("/api/comments/{comment_id}", status_code=204, summary="댓글 삭제 - 쓴 사람 · owner")
def delete_comment(comment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(Comment, comment_id)
    m = db.get(Meeting, c.meeting_id) if c else None
    mine = membership_of(db, user.id)
    if c is None or m is None or mine is None or mine.team_id != m.team_id:
        raise not_found("댓글을 찾을 수 없음")
    if not can_delete_comment(db, user, c, m.team_id):
        raise forbidden("쓴 사람과 owner 만 삭제")
    db.delete(c)
    db.commit()
    return Response(status_code=204)
