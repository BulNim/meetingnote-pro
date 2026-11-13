"""응답 모양 - 정의서 7-1 의 필드를 그대로 만든다. 권한 판정(can_edit · can_delete)도 여기서 API 와 같은 함수로."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Activity, Comment, Meeting, Membership, Team, Todo, User

STATUS_ORDER = {"OPEN": 0, "DOING": 1, "DONE": 2}


def iso(dt: datetime | None) -> str | None:
    return None if dt is None else dt.replace(microsecond=0).isoformat() + "Z"


def role_of(db: Session, user_id: int) -> str | None:
    return db.scalar(select(Membership.role).where(Membership.user_id == user_id))


def user_out(db: Session, u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": role_of(db, u.id)}


def team_out(db: Session, t: Team, me: User) -> dict:
    count = db.scalar(select(func.count()).select_from(Membership).where(Membership.team_id == t.id))
    return {"id": t.id, "name": t.name, "invite_code": t.invite_code, "owner_id": t.owner_id,
            "role": role_of(db, me.id), "member_count": count, "created_at": iso(t.created_at)}


def decision_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


# ── 권한 판정 - 화면 잠금(can_*)과 서버 거부(403)가 같은 함수를 쓴다 ──
def is_owner(db: Session, user: User, team_id: int) -> bool:
    m = db.scalar(select(Membership).where(Membership.user_id == user.id))
    return m is not None and m.team_id == team_id and m.role == "owner"


def can_edit_meeting(db: Session, user: User, m: Meeting) -> bool:
    return m.author_id == user.id or is_owner(db, user, m.team_id)


def can_delete_todo(db: Session, user: User, t: Todo) -> bool:
    return user.id in (t.author_id, t.assignee_id) or is_owner(db, user, t.team_id)


def can_delete_comment(db: Session, user: User, c: Comment, team_id: int) -> bool:
    return c.user_id == user.id or is_owner(db, user, team_id)


# ── 회의록 ──
def meeting_item(db: Session, m: Meeting) -> dict:
    total = db.scalar(select(func.count()).select_from(Todo).where(Todo.meeting_id == m.id))
    done = db.scalar(select(func.count()).select_from(Todo).where(Todo.meeting_id == m.id, Todo.status == "DONE"))
    return {"id": m.id, "title": m.title, "met_at": iso(m.met_at), "attendees": m.attendees,
            "summary": m.summary, "created_at": iso(m.created_at),
            "todo_done_count": done, "todo_total_count": total,
            "decision_count": len(decision_lines(m.decisions))}


def meeting_detail(db: Session, m: Meeting, me: User) -> dict:
    out = meeting_item(db, m)
    todos = db.scalars(select(Todo).where(Todo.meeting_id == m.id)).all()
    author = db.get(User, m.author_id)
    out.update({"body": m.body, "decisions": m.decisions, "author_id": m.author_id,
                "author_name": author.name if author else None,
                "todos": sort_todos([todo_out(db, t, me) for t in todos]),
                "can_edit": can_edit_meeting(db, me, m)})
    return out


# ── 할 일 ──
def todo_out(db: Session, t: Todo, me: User) -> dict:
    assignee = db.get(User, t.assignee_id) if t.assignee_id else None
    meeting = db.get(Meeting, t.meeting_id) if t.meeting_id else None
    return {"id": t.id, "what": t.what, "assignee_id": t.assignee_id,
            "assignee_name": assignee.name if assignee else None,
            "due_text": t.due_text, "due_date": t.due_date.isoformat() if t.due_date else None, "status": t.status, "meeting_id": t.meeting_id,
            "meeting_title": meeting.title if meeting else None,
            "can_delete": can_delete_todo(db, me, t)}


def sort_todos(items: list[dict]) -> list[dict]:
    """status 다음 due_date. 날짜를 정하지 못한 것은 각 상태의 뒤로."""
    return sorted(items, key=lambda x: (STATUS_ORDER.get(x["status"], 9), x["due_date"] is None, x["due_date"] or "", x["id"]))


# ── 댓글 · 활동 ──
def comment_out(db: Session, c: Comment, me: User, team_id: int) -> dict:
    u = db.get(User, c.user_id)
    return {"id": c.id, "user_id": c.user_id, "user_name": u.name if u else None,
            "content": c.content, "created_at": iso(c.created_at),
            "can_delete": can_delete_comment(db, me, c, team_id)}


def activity_out(db: Session, a: Activity) -> dict:
    u = db.get(User, a.actor_id)
    return {"id": a.id, "kind": a.kind, "actor_name": u.name if u else None,
            "text": a.target, "created_at": iso(a.created_at)}
