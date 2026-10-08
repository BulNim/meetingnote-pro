"""라우터 공통 의존성 - 로그인 사용자, 팀 접근 검사"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .errors import ApiError
from .models import Membership, Team, User
from .security import decode_token

# Swagger 의 Authorize 버튼에 JWT 를 붙여 넣는 방식 (로그인 API 가 JSON 을 받으므로 OAuth2 폼은 쓰지 않음)
bearer = HTTPBearer(auto_error=False, description="로그인으로 받은 JWT")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise ApiError(401, "UNAUTHORIZED", "로그인이 필요함")
    user = db.get(User, decode_token(creds.credentials))
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "로그인이 필요함")
    return user


def my_membership(db: Session, user: User) -> Membership | None:
    return db.query(Membership).filter(Membership.user_id == user.id).first()


def require_team(db: Session, user: User, team_id: int) -> tuple[Team, Membership]:
    """같은 팀원만 통과. 다른 팀이거나 없는 팀이면 존재 여부를 숨기려고 같은 404"""
    team = db.get(Team, team_id)
    membership = my_membership(db, user)
    if team is None or membership is None or membership.team_id != team.id:
        raise ApiError(404, "NOT_FOUND", "찾을 수 없음")
    return team, membership


def require_owner(membership: Membership) -> None:
    if membership.role != "owner":
        raise ApiError(403, "OWNER_ONLY", "owner 만 할 수 있음")
