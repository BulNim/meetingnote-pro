"""인증 5개 - signup · login · me(GET · PUT) · logout."""
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..errors import AppError, validation
from ..models import User
from ..security import current_user, hash_password, make_token, verify_password
from ..serial import user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupIn(BaseModel):
    email: str
    password: str
    name: str


class LoginIn(BaseModel):
    email: str
    password: str


class MeIn(BaseModel):
    name: str | None = None
    password: str | None = None


def _check_password(pw: str) -> None:
    if len(pw) < config.PASSWORD_MIN:
        raise AppError(400, "PASSWORD_TOO_WEAK", "비밀번호는 8자 이상")


@router.post("/signup", status_code=201, summary="회원가입 - 초대코드는 받지 않음")
def signup(data: SignupIn, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise AppError(400, "EMAIL_INVALID", "이메일 형식이 올바르지 않음")
    _check_password(data.password)
    name = data.name.strip()
    if not name:
        raise validation("이름을 입력")
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise AppError(409, "EMAIL_DUPLICATED", "이미 가입된 이메일")
    u = User(email=email, password_hash=hash_password(data.password), name=name)
    db.add(u)
    db.commit()
    return {"token": make_token(u.id), "user": user_out(db, u)}


@router.post("/login", summary="로그인 - 이메일 없음과 비밀번호 틀림을 구분하지 않음")
def login(data: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(func.lower(User.email) == data.email.strip().lower()))
    if u is None or not verify_password(data.password, u.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않음")
    return {"token": make_token(u.id), "user": user_out(db, u)}


@router.get("/me", summary="내 정보 - role 은 소속 팀의 owner / member")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_out(db, user)


@router.put("/me", summary="내 정보 수정 - 비밀번호를 보내지 않으면 그대로")
def update_me(data: MeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise validation("이름을 입력")
        user.name = name
    if data.password:
        _check_password(data.password)
        user.password_hash = hash_password(data.password)
    db.commit()  # 계정 변경은 활동 기록에 남기지 않음
    return user_out(db, user)


@router.post("/logout", summary="로그아웃 - 서버 블랙리스트 없음. 화면이 토큰을 지움")
def logout(user: User = Depends(current_user)):
    return {"ok": True}
