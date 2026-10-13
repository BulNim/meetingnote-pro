"""comment - 정의서 7절 Comment 3개. 근거: 스토리보드 D-09~D-12(detail.html)"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, iso, log_activity, require_member
from ..errors import AppError
from ..models import Comment, Meeting, User

router = APIRouter(tags=["comment"])

MAX_LEN = 500


class CommentIn(BaseModel):
    content: str


def _item(c: Comment, names: dict, me: User, role: str) -> dict:
    return {
        "id": c.id,
        "user_id": c.user_id,
        "user_name": names.get(c.user_id),
        "content": c.content,
        "created_at": iso(c.created_at),
        "can_delete": c.user_id == me.id or role == "owner",
    }


def _meeting(db: Session, user: User, meeting_id: int):
    m = db.get(Meeting, meeting_id)
    if m is None:
        raise AppError(404, "MEETING_NOT_FOUND", "회의록을 찾을 수 없습니다")
    return m, require_member(db, user, m.team_id)


@router.post("/meetings/{meeting_id}/comments", status_code=201, summary="댓글 달기 - 500자 이하")
def add_comment(meeting_id: int, body: CommentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m, membership = _meeting(db, user, meeting_id)
    content = body.content.strip()
    if not content or len(content) > MAX_LEN:
        raise AppError(400, "VALIDATION_ERROR", "댓글은 1자 이상 500자 이하입니다")
    c = Comment(meeting_id=m.id, user_id=user.id, content=content)
    db.add(c)
    log_activity(db, m.team_id, user.id, "comment_add", m.title)
    db.commit()
    return _item(c, {user.id: user.name}, user, membership.role)


@router.get("/meetings/{meeting_id}/comments", summary="댓글 목록 - 오래된 순, can_delete 는 서버가 판정")
def list_comments(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m, membership = _meeting(db, user, meeting_id)
    rows = db.query(Comment).filter(Comment.meeting_id == m.id).order_by(Comment.created_at, Comment.id).all()
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_({c.user_id for c in rows} or {0})).all()}
    return [_item(c, names, user, membership.role) for c in rows]


@router.delete("/comments/{comment_id}", status_code=204, summary="댓글 삭제 - 쓴 사람과 owner")
def delete_comment(comment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(Comment, comment_id)
    if c is None:
        raise AppError(404, "NOT_FOUND", "댓글을 찾을 수 없습니다")
    _, membership = _meeting(db, user, c.meeting_id)
    if c.user_id != user.id and membership.role != "owner":
        raise AppError(403, "FORBIDDEN", "쓴 사람과 owner 만 지울 수 있습니다")
    db.delete(c)
    db.commit()
