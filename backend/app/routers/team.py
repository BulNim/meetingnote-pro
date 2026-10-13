"""team - 정의서 7절 Team 6개. 근거: 스토리보드 F(team.html), B-11(login.html)"""
import secrets

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, log_activity, membership_of, require_member
from ..errors import AppError
from ..models import Membership, Team, Todo, User
from ..models import Meeting

router = APIRouter(prefix="/teams", tags=["team"])

MAX_MEMBERS = 6
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class TeamIn(BaseModel):
    name: str


class JoinIn(BaseModel):
    invite_code: str


def _team(team: Team, role: str) -> dict:
    return {"id": team.id, "name": team.name, "invite_code": team.invite_code, "role": role}


def _new_code(db: Session) -> str:
    while True:
        code = "MN-" + "".join(secrets.choice(CODE_CHARS) for _ in range(4))
        if not db.query(Team).filter(Team.invite_code == code).first():
            return code


def _name(value: str) -> str:
    value = value.strip()
    if not value:
        raise AppError(400, "VALIDATION_ERROR", "팀 이름을 입력해 주세요")
    return value


@router.post("", status_code=201, summary="팀 생성 - 만든 사람이 owner")
def create_team(body: TeamIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if membership_of(db, user):
        raise AppError(400, "VALIDATION_ERROR", "이미 팀에 속해 있습니다")
    team = Team(name=_name(body.name), invite_code=_new_code(db), owner_id=user.id)
    db.add(team)
    db.flush()
    db.add(Membership(team_id=team.id, user_id=user.id, role="owner"))
    db.commit()
    return _team(team, "owner")


@router.get("", summary="내 팀 목록 - 소속이 없으면 빈 배열")
def my_teams(user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = membership_of(db, user)
    return [_team(db.get(Team, m.team_id), m.role)] if m else []


@router.post("/join", summary="초대코드로 합류")
def join_team(body: JoinIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.invite_code == body.invite_code.strip().upper()).first()
    if team is None:
        raise AppError(404, "INVITE_NOT_FOUND", "초대코드를 찾을 수 없습니다")
    if membership_of(db, user):
        raise AppError(400, "VALIDATION_ERROR", "이미 팀에 속해 있습니다")
    count = db.query(func.count(Membership.id)).filter(Membership.team_id == team.id).scalar()
    if count >= MAX_MEMBERS:
        raise AppError(409, "TEAM_FULL", "정원(6명)이 가득 찼습니다")
    db.add(Membership(team_id=team.id, user_id=user.id, role="member"))
    log_activity(db, team.id, user.id, "member_join")
    db.commit()
    return _team(team, "member")


@router.get("/{team_id}/members", summary="멤버 목록 - 1인당 할 일 수 포함")
def members(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    rows = (
        db.query(Membership, User)
        .join(User, User.id == Membership.user_id)
        .filter(Membership.team_id == team_id)
        .order_by(Membership.id)
        .all()
    )
    counts = dict(
        db.query(Todo.assignee_id, func.count(Todo.id))
        .join(Meeting, Meeting.id == Todo.meeting_id)
        .filter(Meeting.team_id == team_id, Todo.assignee_id.isnot(None))
        .group_by(Todo.assignee_id)
        .all()
    )
    return [
        {"id": u.id, "name": u.name, "email": u.email, "role": m.role, "todo_count": counts.get(u.id, 0)}
        for m, u in rows
    ]


def _owner_only(db: Session, user: User, team_id: int) -> Team:
    m = require_member(db, user, team_id)
    if m.role != "owner":
        raise AppError(403, "OWNER_ONLY", "owner 만 할 수 있습니다")
    return db.get(Team, team_id)


@router.put("/{team_id}", summary="팀 이름 변경 - owner 전용")
def rename_team(team_id: int, body: TeamIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    team = _owner_only(db, user, team_id)
    team.name = _name(body.name)
    db.commit()
    return _team(team, "owner")


@router.put("/{team_id}/code", summary="초대코드 재발급 - owner 전용, 앞의 코드는 무효")
def reissue_code(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    team = _owner_only(db, user, team_id)
    team.invite_code = _new_code(db)
    db.commit()
    return _team(team, "owner")
