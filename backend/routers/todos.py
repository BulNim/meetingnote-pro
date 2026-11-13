"""할 일 5개 - 팀 목록 · 직접 등록 · 수정(상태 · 담당자 · 기한) · 내 목록 · 삭제."""
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import activity
from ..db import get_db
from ..errors import forbidden, not_found, validation
from ..models import Membership, Todo, User
from ..security import current_user, membership_of, require_member
from ..serial import STATUS_ORDER, can_delete_todo, sort_todos, todo_out

router = APIRouter(tags=["todo"])


class TodoIn(BaseModel):
    what: str
    assignee_id: int | None = None
    due_text: str = ""


class TodoEdit(BaseModel):
    status: str | None = None
    assignee_id: int | None = None
    due_text: str | None = None


def check_assignee(db: Session, team_id: int, assignee_id: int | None) -> User | None:
    """담당자는 그 팀 멤버이거나 미정(null)."""
    if assignee_id is None:
        return None
    ok = db.scalar(select(Membership).where(Membership.team_id == team_id, Membership.user_id == assignee_id))
    if not ok:
        raise validation("담당자는 팀 멤버여야 함")
    return db.get(User, assignee_id)


def visible_todo(db: Session, user: User, todo_id: int) -> Todo:
    t = db.get(Todo, todo_id)
    mine = membership_of(db, user.id)
    if t is None or mine is None or mine.team_id != t.team_id:
        raise not_found("할 일을 찾을 수 없음")
    return t


@router.get("/api/teams/{team_id}/todos", summary="팀 할 일 - status 다음 due_text 순")
def team_todos(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    rows = db.scalars(select(Todo).where(Todo.team_id == team_id)).all()
    return sort_todos([todo_out(db, t, user) for t in rows])


@router.post("/api/teams/{team_id}/todos", status_code=201, summary="할 일 직접 등록 - 회의록 없이")
def create_todo(team_id: int, data: TodoIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    what = data.what.strip()
    if not what:
        raise validation("내용 필수")
    assignee = check_assignee(db, team_id, data.assignee_id)
    t = Todo(team_id=team_id, meeting_id=None, what=what, due_text=(data.due_text or "").strip(),
             assignee_id=data.assignee_id, author_id=user.id)
    db.add(t)
    if assignee:
        activity.record(db, team_id, user.id, "todo_assign", what=what, assignee=assignee.name)
    db.commit()
    return todo_out(db, t, user)


@router.put("/api/todos/{todo_id}", summary="할 일 수정 - 상태(OPEN · DOING · DONE) · 담당자 · 기한. 팀원 누구나")
def edit_todo(todo_id: int, data: TodoEdit, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = visible_todo(db, user, todo_id)
    sent = data.model_fields_set
    if "status" in sent:
        if data.status not in STATUS_ORDER:
            raise validation("status 는 OPEN · DOING · DONE")
        if data.status == "DONE" and t.status != "DONE":
            activity.record(db, t.team_id, user.id, "todo_done", what=t.what)
        t.status = data.status  # DOING 이동은 활동을 남기지 않음
    if "assignee_id" in sent:
        assignee = check_assignee(db, t.team_id, data.assignee_id)
        if assignee and assignee.id != t.assignee_id:
            activity.record(db, t.team_id, user.id, "todo_assign", what=t.what, assignee=assignee.name)
        t.assignee_id = data.assignee_id
    if "due_text" in sent:
        t.due_text = (data.due_text or "").strip()
    db.commit()
    return todo_out(db, t, user)


@router.get("/api/me/todos", summary="내 할 일 - 나에게 배정된 것만")
def my_todos(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Todo).where(Todo.assignee_id == user.id)).all()
    return sort_todos([todo_out(db, t, user) for t in rows])


@router.delete("/api/todos/{todo_id}", status_code=204, summary="할 일 삭제 - 만든 사람 · 담당자 · owner")
def delete_todo(todo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = visible_todo(db, user, todo_id)
    if not can_delete_todo(db, user, t):
        raise forbidden("만든 사람 · 담당자 · owner 만 삭제")
    db.delete(t)
    db.commit()
    return Response(status_code=204)
