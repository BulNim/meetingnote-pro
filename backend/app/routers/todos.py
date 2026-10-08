"""할 일 - 칸반 목록 · 상태 / 담당자 / 기한 변경 · 삭제(owner) (스토리보드 E, D-03, D-04)

할 일은 회의록 저장 때 만들어진다. 따로 만드는 API 는 없다.
기한(due_text)은 자유 글자라 서버는 날짜로 해석하거나 비교하지 않는다 (결정기록 D-003, D-011).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, my_membership, require_owner, require_team
from ..errors import ApiError
from ..models import TODO_STATUSES, Meeting, Membership, Todo, User
from ..serializers import todo_dict, user_names
from ..services import activity

router = APIRouter(prefix="/api", tags=["todo"])

STATUS_ORDER = case({"OPEN": 0, "DOING": 1, "DONE": 2}, value=Todo.status, else_=3)


class TodoPatch(BaseModel):
    status: str | None = None
    assignee_id: int | None = None  # 보내면서 null 이면 담당자 미정
    due_text: str | None = None


def _rows(db: Session, query) -> list[dict]:
    rows = (
        query.with_entities(Todo, Meeting.title)  # 호출한 쪽이 Meeting 을 이미 조인했다
        .order_by(STATUS_ORDER, Todo.due_text, Todo.id)
        .all()
    )
    names = user_names(db, {t.assignee_id for t, _ in rows if t.assignee_id})
    return [todo_dict(t, names.get(t.assignee_id), title) for t, title in rows]


@router.get("/teams/{team_id}/todos", summary="팀 전체 할 일")
def team_todos(team_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team, _ = require_team(db, user, team_id)
    return _rows(db, db.query(Todo).join(Meeting, Meeting.id == Todo.meeting_id).filter(Meeting.team_id == team.id))


@router.get("/me/todos", summary="내게 배정된 할 일")
def my_todos(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = my_membership(db, user)
    if membership is None:
        return []
    query = (
        db.query(Todo)
        .join(Meeting, Meeting.id == Todo.meeting_id)
        .filter(Meeting.team_id == membership.team_id, Todo.assignee_id == user.id)
    )
    return _rows(db, query)


def _load(db: Session, user: User, todo_id: int) -> tuple[Todo, Meeting, Membership]:
    todo = db.get(Todo, todo_id)
    meeting = db.get(Meeting, todo.meeting_id) if todo else None
    if meeting is None:
        raise ApiError(404, "NOT_FOUND", "찾을 수 없음")
    _, membership = require_team(db, user, meeting.team_id)
    return todo, meeting, membership


@router.put("/todos/{todo_id}", summary="상태 · 담당자 · 기한 변경")
def update_todo(
    todo_id: int,
    body: TodoPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo, meeting, _ = _load(db, user, todo_id)
    sent = body.model_fields_set

    if "status" in sent:
        if body.status not in TODO_STATUSES:
            raise ApiError(400, "VALIDATION_ERROR", "상태는 OPEN · DOING · DONE 중 하나")
    if "assignee_id" in sent and body.assignee_id is not None:
        member = db.query(Membership).filter_by(team_id=meeting.team_id, user_id=body.assignee_id).first()
        if member is None:
            raise ApiError(400, "VALIDATION_ERROR", "팀 멤버만 담당자로 정할 수 있음")
    due = None
    if "due_text" in sent:
        due = (body.due_text or "").strip()
        if not due or len(due) > 100:
            raise ApiError(400, "VALIDATION_ERROR", "기한은 1~100자")

    if "status" in sent and body.status != todo.status:
        if body.status == "DONE":
            activity.record(db, meeting.team_id, user.id, "todo_done", activity.todo_done(todo.what))
        todo.status = body.status
    if "assignee_id" in sent and body.assignee_id != todo.assignee_id:
        todo.assignee_id = body.assignee_id
        if body.assignee_id is not None:  # 미정으로 되돌리는 것은 기록하지 않는다
            name = db.get(User, body.assignee_id).name
            activity.record(db, meeting.team_id, user.id, "todo_assign", activity.todo_assigned(todo.what, name))
    if due is not None:
        todo.due_text = due
    db.commit()

    names = user_names(db, {todo.assignee_id} if todo.assignee_id else set())
    return todo_dict(todo, names.get(todo.assignee_id), meeting.title)


@router.delete("/todos/{todo_id}", status_code=204, summary="할 일 삭제 (owner)")
def delete_todo(todo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo, _, membership = _load(db, user, todo_id)
    require_owner(membership)
    db.delete(todo)
    db.commit()
