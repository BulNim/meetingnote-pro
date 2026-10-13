"""비밀번호 bcrypt 해시 + JWT(24h) 발급·검증"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from . import config
from .errors import AppError

TOKEN_HOURS = 24


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=config.bcrypt_rounds())).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode())
    except ValueError:
        return False


def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=TOKEN_HOURS)}
    return jwt.encode(payload, config.jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> int:
    try:
        data = jwt.decode(token, config.jwt_secret(), algorithms=["HS256"])
        return int(data["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise AppError(401, "TOKEN_EXPIRED", "세션이 만료되었습니다")
