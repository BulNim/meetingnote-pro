"""팀 - 생성 · 합류 · 초대코드 · 이름 · 멤버 (스토리보드 F)"""
import secrets

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import TEAM_MAX_MEMBERS
from ..db import get_db
from ..deps import get_current_user, my_membership, require_owner, require_team
from ..errors import ApiError
from ..models import Meeting, Membership, Team, Todo, User
from ..services import activity

router = APIRouter(prefix="/api/teams", tags=["team"])

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 헷갈리는 0 O 1 I 는 뺀다


class TeamIn(BaseModel):
    name: str


class JoinIn(BaseModel):
    invite_code: str


def _clean_name(raw: str) -> str:
    name = raw.strip()
    if not name or len(name) > 100:
        raise ApiError(400, "VALIDATION_ERROR", "팀 이름은 1~100자")
    return name


def _new_code(db: Session) -> str:
    for _ in range(50):
        code = "MN-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(4))
        if not db.query(Team).filter(Team.invite_code == code).first():
            return code
    raise ApiError(400, "VALIDATION_ERROR", "초대코드를 만들지 못함")


def _member_count(db: Session, team_id: int) -> int:
    return db.query(func.count(Membership.id)).filter(Membership.team_id == team_id).scalar() or 0


def _team_body(db: Session, team: Team, role: str) -> dict:
    return {
        "id": team.id,
        "name": team.name,
        "invite_code": team.invite_code,
        "role": role,
        "member_count": _member_count(db, team.id),
    }


@router.post("", status_code=201, summary="팀 만들기")
def create_team(body: TeamIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if my_membership(db, user):
        raise ApiError(400, "VALIDATION_ERROR", "이미 소속된 팀이 있음")
    team = Team(name=_clean_name(body.name), invite_code=_new_code(db), owner_id=user.id)
    db.add(team)
    db.flush()
    db.add(Membership(team_id=team.id, user_id=user.id, role="owner"))
    db.commit()  # 팀 생성은 활동 기록을 남기지 않는다
    return _team_body(db, team, "owner")


@router.get("", summary="내 팀 (0개 또는 1개)")
def my_teams(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = my_membership(db, user)
    if membership is None:
        return []
    return [_team_body(db, db.get(Team, membership.team_id), membership.role)]


@router.post("/join", summary="초대코드로 합류")
def join_team(body: JoinIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if my_membership(db, user):
        raise ApiError(400, "VALIDATION_ERROR", "이미 소속된 팀이 있음")
    code = body.invite_code.strip().upper()
    team = db.query(Team).filter(Team.invite_code == code).first()
    if team is None:
        raise ApiError(404, "INVITE_NOT_FOUND", "초대코드를 찾을 수 없음")
    if _member_count(db, team.id) >= TEAM_MAX_MEMBERS:
        raise ApiError(409, "TEAM_FULL", f"팀 정원({TEAM_MAX_MEMBERS}명)이 찼음")
    db.add(Membership(team_id=team.id, user_id=user.id, role="member"))
    activity.record(db, team.id, user.id, "member_join", activity.member_joined())
    db.commit()
    return _team_body(db, team, "member")


@router.get("/{team_id}/members", summary="멤버 목록")
def members(team_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team, _ = require_team(db, user, team_id)
    rows = (
        db.query(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .filter(Membership.team_id == team.id)
        .order_by(Membership.joined_at, Membership.id)
        .all()
    )
    counts = dict(
        db.query(Todo.assignee_id, func.count(Todo.id))
        .join(Meeting, Meeting.id == Todo.meeting_id)
        .filter(Meeting.team_id == team.id, Todo.assignee_id.isnot(None))
        .group_by(Todo.assignee_id)
        .all()
    )
    return [
        {"id": u.id, "name": u.name, "email": u.email, "role": role, "todo_count": counts.get(u.id, 0)}
        for u, role in rows
    ]


@router.put("/{team_id}", summary="팀 이름 변경 (owner)")
def rename_team(team_id: int, body: TeamIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team, membership = require_team(db, user, team_id)
    require_owner(membership)
    team.name = _clean_name(body.name)
    db.commit()
    return _team_body(db, team, membership.role)


@router.put("/{team_id}/code", summary="초대코드 재발급 (owner)")
def reissue_code(team_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team, membership = require_team(db, user, team_id)
    require_owner(membership)
    team.invite_code = _new_code(db)
    db.commit()
    return {"invite_code": team.invite_code}
