"""bcrypt 해시 · JWT 발급과 검증 · 현재 사용자 · 팀 소속 확인."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .errors import AppError, forbidden, owner_only
from .models import Membership, User

bearer = HTTPBearer(auto_error=False, description="로그인 응답의 token 을 그대로 붙여 넣는다")


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def make_token(user_id: int, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=config.JWT_TTL_HOURS)}
    return jwt.encode(payload, config.jwt_secret(), algorithm=config.JWT_ALGORITHM)


def _expired() -> AppError:
    return AppError(401, "TOKEN_EXPIRED", "다시 로그인 필요")


def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """토큰 없음 · 위조 · 만료는 모두 401 TOKEN_EXPIRED."""
    if cred is None or not cred.credentials:
        raise _expired()
    try:
        data = jwt.decode(cred.credentials, config.jwt_secret(), algorithms=[config.JWT_ALGORITHM])
        user = db.get(User, int(data["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _expired()
    if user is None:
        raise _expired()
    return user


def membership_of(db: Session, user_id: int) -> Membership | None:
    return db.scalar(select(Membership).where(Membership.user_id == user_id))


def require_member(db: Session, user: User, team_id: int) -> Membership:
    """그 팀의 멤버가 아니면 403 FORBIDDEN."""
    m = membership_of(db, user.id)
    if m is None or m.team_id != team_id:
        raise forbidden("다른 팀의 자료")
    return m


def require_owner(db: Session, user: User, team_id: int) -> Membership:
    m = require_member(db, user, team_id)
    if m.role != "owner":
        raise owner_only()
    return m
