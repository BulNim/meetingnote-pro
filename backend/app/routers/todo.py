"""todo - 정의서 7절 Todo 4개. 근거: 스토리보드 E(todos.html), D-03/D-04(detail.html)"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, log_activity, require_member
from ..errors import AppError
from ..models import Meeting, Membership, Todo, User

router = APIRouter(tags=["todo"])

STATUSES = ("OPEN", "DOING", "DONE")
STATUS_ORDER = {s: i for i, s in enumerate(STATUSES)}


class TodoUpdateIn(BaseModel):
    status: str | None = None
    assignee_id: int | None = None


def _rows(db: Session, query) -> list[dict]:
    rows = query.all()
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_({t.assignee_id for t, _ in rows if t.assignee_id} or {0})).all()}
    out = [
        {
            "id": t.id,
            "what": t.what,
            "assignee_id": t.assignee_id,
            "assignee_name": names.get(t.assignee_id),
            "due_text": t.due_text,
            "status": t.status,
            "meeting_title": m.title,
        }
        for t, m in rows
    ]
    out.sort(key=lambda r: (STATUS_ORDER.get(r["status"], 9), r["due_text"] or "~", r["id"]))
    return out


@router.get("/teams/{team_id}/todos", summary="팀 전체 할 일")
def team_todos(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    q = db.query(Todo, Meeting).join(Meeting, Meeting.id == Todo.meeting_id).filter(Meeting.team_id == team_id)
    return _rows(db, q)


@router.get("/me/todos", summary="내게 배정된 할 일")
def my_todos(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Todo, Meeting).join(Meeting, Meeting.id == Todo.meeting_id).filter(Todo.assignee_id == user.id)
    return _rows(db, q)


def _load(db: Session, user: User, todo_id: int) -> tuple[Todo, Meeting, Membership]:
    todo = db.get(Todo, todo_id)
    if todo is None:
        raise AppError(404, "NOT_FOUND", "할 일을 찾을 수 없습니다")
    meeting = db.get(Meeting, todo.meeting_id)
    return todo, meeting, require_member(db, user, meeting.team_id)


@router.put("/todos/{todo_id}", summary="상태 변경 · 담당자 배정")
def update_todo(todo_id: int, body: TodoUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    todo, meeting, _ = _load(db, user, todo_id)
    fields = body.model_fields_set
    if "status" in fields:
        if body.status not in STATUSES:
            raise AppError(400, "VALIDATION_ERROR", "상태는 OPEN, DOING, DONE 중 하나입니다")
        if body.status == "DONE" and todo.status != "DONE":
            log_activity(db, meeting.team_id, user.id, "todo_done", todo.what)
        todo.status = body.status
    if "assignee_id" in fields:
        if body.assignee_id is None:
            todo.assignee_id = None
        else:
            target = db.get(User, body.assignee_id)
            ok = target is not None and (
                db.query(Membership)
                .filter(Membership.team_id == meeting.team_id, Membership.user_id == target.id)
                .first()
            )
            if not ok:
                raise AppError(400, "VALIDATION_ERROR", "같은 팀의 멤버만 담당자로 지정할 수 있습니다")
            if todo.assignee_id != target.id:
                log_activity(db, meeting.team_id, user.id, "todo_assign", f"{todo.what}||{target.name}")
            todo.assignee_id = target.id
    db.commit()
    return _rows(db, db.query(Todo, Meeting).join(Meeting, Meeting.id == Todo.meeting_id).filter(Todo.id == todo.id))[0]


@router.delete("/todos/{todo_id}", status_code=204, summary="할 일 삭제 - owner 전용")
def delete_todo(todo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    todo, _, membership = _load(db, user, todo_id)
    if membership.role != "owner":
        raise AppError(403, "OWNER_ONLY", "owner 만 할 수 있습니다")
    db.delete(todo)
    db.commit()
