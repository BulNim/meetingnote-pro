"""팀 6개 - 생성 · 목록 · 합류 · 멤버 · 초대코드 재발급 · 이름 변경."""
import secrets
import string

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import activity, config
from ..db import get_db
from ..errors import AppError, validation
from ..models import Membership, Team, Todo, User
from ..security import current_user, membership_of, require_member, require_owner
from ..serial import team_out

router = APIRouter(prefix="/api/teams", tags=["team"])

CODE_CHARS = string.ascii_uppercase + string.digits


class TeamIn(BaseModel):
    name: str


class JoinIn(BaseModel):
    code: str


def new_code(db: Session) -> str:
    while True:
        code = "MN-" + "".join(secrets.choice(CODE_CHARS) for _ in range(4))
        if not db.scalar(select(Team).where(Team.invite_code == code)):
            return code


def _name(raw: str) -> str:
    name = raw.strip()
    if not name:
        raise validation("팀 이름을 입력")
    return name


@router.post("", status_code=201, summary="팀 생성 - 만든 사람이 owner. 활동 기록 없음")
def create_team(data: TeamIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = _name(data.name)
    if membership_of(db, user.id):
        raise validation("이미 팀에 소속됨 - 한 사람은 한 팀")
    t = Team(name=name, invite_code=new_code(db), owner_id=user.id)
    db.add(t)
    db.flush()
    db.add(Membership(team_id=t.id, user_id=user.id, role="owner"))
    db.commit()
    return team_out(db, t, user)


@router.get("", summary="내 팀 목록 - 0개 또는 1개")
def my_teams(user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = membership_of(db, user.id)
    return [team_out(db, db.get(Team, m.team_id), user)] if m else []


@router.post("/join", summary="초대코드로 합류 - member 로 등록, member_join 기록")
def join(data: JoinIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    code = data.code.strip().upper()
    t = db.scalar(select(Team).where(Team.invite_code == code))
    if t is None:
        raise AppError(404, "INVITE_NOT_FOUND", "없는 초대코드")
    if membership_of(db, user.id):
        raise validation("이미 팀에 소속됨 - 한 사람은 한 팀")
    count = db.scalar(select(func.count()).select_from(Membership).where(Membership.team_id == t.id))
    if count >= config.TEAM_MAX_MEMBERS:
        raise AppError(409, "TEAM_FULL", f"{t.name}은 이미 {config.TEAM_MAX_MEMBERS}명")
    db.add(Membership(team_id=t.id, user_id=user.id, role="member"))
    activity.record(db, t.id, user.id, "member_join")
    db.commit()
    return team_out(db, t, user)


@router.get("/{team_id}/members", summary="멤버 목록 - todo_count 는 배정된 할 일 전부(완료 포함)")
def members(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    rows = db.execute(
        select(User, Membership.role).join(Membership, Membership.user_id == User.id)
        .where(Membership.team_id == team_id).order_by(Membership.joined_at, Membership.id)
    ).all()
    out = []
    for u, role in rows:
        n = db.scalar(select(func.count()).select_from(Todo).where(Todo.team_id == team_id, Todo.assignee_id == u.id))
        out.append({"id": u.id, "name": u.name, "email": u.email, "role": role, "todo_count": n})
    return out


@router.put("/{team_id}/code", summary="초대코드 재발급 - owner 만. 이전 코드 폐기")
def reissue_code(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_owner(db, user, team_id)
    t = db.get(Team, team_id)
    t.invite_code = new_code(db)
    db.commit()
    return team_out(db, t, user)


@router.put("/{team_id}", summary="팀 이름 변경 - owner 만")
def rename(team_id: int, data: TeamIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_owner(db, user, team_id)
    t = db.get(Team, team_id)
    t.name = _name(data.name)
    db.commit()
    return team_out(db, t, user)
