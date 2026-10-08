"""비밀번호 해시(bcrypt)와 JWT(24시간, 갱신 없음)"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import JWT_HOURS, get_settings
from .errors import ApiError

MAX_PASSWORD_BYTES = 72  # bcrypt 의 입력 한계


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:MAX_PASSWORD_BYTES], password_hash.encode("ascii"))
    except ValueError:
        return False


def create_token(user_id: int, hours: int = JWT_HOURS, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=hours)}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm="HS256")


def decode_token(token: str) -> int:
    """만료는 TOKEN_EXPIRED, 그 밖에 깨지거나 위조된 토큰은 UNAUTHORIZED"""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "TOKEN_EXPIRED", "세션이 만료됨. 다시 로그인 필요")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise ApiError(401, "UNAUTHORIZED", "로그인이 필요함")
