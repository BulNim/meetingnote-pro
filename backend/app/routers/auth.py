"""인증 - 가입 · 로그인 · 로그아웃 · 내 정보 (스토리보드 B, J)"""
from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, my_membership
from ..errors import ApiError
from ..models import User
from ..security import MAX_PASSWORD_BYTES, create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

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
    current_password: str | None = None
    new_password: str | None = None


def _clean_email(raw: str) -> str:
    try:
        return validate_email(raw.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise ApiError(400, "EMAIL_INVALID", "이메일 형식이 올바르지 않음")


def _check_new_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise ApiError(400, "PASSWORD_TOO_WEAK", "비밀번호는 8자 이상")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ApiError(400, "VALIDATION_ERROR", "비밀번호가 너무 김")


def _me(db: Session, user: User) -> dict:
    membership = my_membership(db, user)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": membership.role if membership else None,
        "team_id": membership.team_id if membership else None,
    }


def _session(user: User) -> dict:
    return {"token": create_token(user.id), "user": {"id": user.id, "name": user.name, "email": user.email}}


@router.post("/signup", status_code=201, summary="회원가입")
def signup(body: SignupIn, db: Session = Depends(get_db)):
    email = _clean_email(body.email)
    _check_new_password(body.password)
    name = body.name.strip()
    if not name:
        raise ApiError(400, "VALIDATION_ERROR", "이름을 입력해야 함")
    if db.query(User).filter(User.email == email).first():
        raise ApiError(409, "EMAIL_DUPLICATED", "이미 가입된 이메일")
    user = User(email=email, password_hash=hash_password(body.password), name=name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "EMAIL_DUPLICATED", "이미 가입된 이메일")
    return _session(user)


@router.post("/login", summary="로그인")
def login(body: LoginIn, db: Session = Depends(get_db)):
    # 이메일이 없는 것과 비밀번호가 틀린 것을 구분하지 않는다
    user = db.query(User).filter(User.email == body.email.strip().lower()).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않음")
    return _session(user)


@router.post("/logout", summary="로그아웃")
def logout(_: User = Depends(get_current_user)):
    # JWT 는 무상태라 서버는 블랙리스트를 두지 않는다. 화면이 토큰을 지운다
    return {"ok": True}


@router.get("/me", summary="내 정보")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _me(db, user)


@router.put("/me", summary="내 정보 수정")
def update_me(body: MeUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise ApiError(400, "VALIDATION_ERROR", "이름을 입력해야 함")
        user.name = name
    if body.new_password is not None:
        if not body.current_password:
            raise ApiError(400, "VALIDATION_ERROR", "현재 비밀번호를 입력해야 함")
        if not verify_password(body.current_password, user.password_hash):
            raise ApiError(401, "INVALID_CREDENTIALS", "현재 비밀번호가 올바르지 않음")
        _check_new_password(body.new_password)
        user.password_hash = hash_password(body.new_password)
    db.commit()
    return _me(db, user)
