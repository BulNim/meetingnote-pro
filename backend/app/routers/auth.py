"""auth - 정의서 7절 Auth 5개. 근거: 스토리보드 B(login.html), J(profile.html)"""
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, membership_of
from ..errors import AppError
from ..models import User
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8


class SignupIn(BaseModel):
    email: str
    password: str
    name: str


class LoginIn(BaseModel):
    email: str
    password: str


class MeUpdateIn(BaseModel):
    name: str | None = None
    password: str | None = None


def _token_body(user: User) -> dict:
    return {"access_token": create_token(user.id), "token_type": "bearer"}


def _me(db: Session, user: User) -> dict:
    m = membership_of(db, user)
    return {"id": user.id, "name": user.name, "email": user.email, "role": m.role if m else None}


@router.post("/signup", status_code=201, summary="회원가입")
def signup(body: SignupIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise AppError(400, "EMAIL_INVALID", "올바른 이메일 형식이 아닙니다")
    if len(body.password) < MIN_PASSWORD:
        raise AppError(400, "PASSWORD_TOO_WEAK", "8자 이상 입력해 주세요")
    if not body.name.strip():
        raise AppError(400, "VALIDATION_ERROR", "이름을 입력해 주세요")
    if db.query(User).filter(User.email == email).first():
        raise AppError(409, "EMAIL_DUPLICATED", "이미 가입된 이메일입니다")
    user = User(email=email, password_hash=hash_password(body.password), name=body.name.strip())
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "EMAIL_DUPLICATED", "이미 가입된 이메일입니다")
    return _token_body(user)


@router.post("/login", summary="로그인 - JWT 24시간")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.strip().lower()).first()
    # 이메일 존재 여부를 드러내지 않도록 두 경우를 같은 응답으로 통일
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다")
    return _token_body(user)


@router.get("/me", summary="내 정보 조회")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _me(db, user)


@router.put("/me", summary="내 정보 수정 (이름·비밀번호)")
def update_me(body: MeUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.password is not None and len(body.password) < MIN_PASSWORD:
        raise AppError(400, "PASSWORD_TOO_WEAK", "8자 이상 입력해 주세요")
    if body.name is not None:
        if not body.name.strip():
            raise AppError(400, "VALIDATION_ERROR", "이름을 입력해 주세요")
        user.name = body.name.strip()
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    db.commit()
    return _me(db, user)


@router.post("/logout", summary="로그아웃 - 서버 블랙리스트 없음")
def logout(_: User = Depends(current_user)):
    return {"ok": True}
