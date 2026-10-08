"""응답 모양 - 여러 라우터가 같이 쓰는 것"""
from sqlalchemy.orm import Session

from .models import Todo, User


def todo_dict(todo: Todo, assignee_name: str | None, meeting_title: str | None = None) -> dict:
    row = {
        "id": todo.id,
        "what": todo.what,
        "assignee_id": todo.assignee_id,
        "assignee_name": assignee_name,
        "due_text": todo.due_text,
        "status": todo.status,
    }
    if meeting_title is not None:
        row["meeting_title"] = meeting_title
    return row


def user_names(db: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {u.id: u.name for u in db.query(User).filter(User.id.in_(ids)).all()}
