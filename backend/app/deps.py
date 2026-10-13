"""공통 의존성 - 인증 사용자, 팀 소속 검사, 시각 변환, 활동 기록"""
from datetime import datetime, timezone

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .errors import AppError
from .models import Activity, Membership, Team, User
from .security import decode_token

# Swagger UI 의 Authorize 에 로그인 응답의 JWT 를 붙여넣는 방식
bearer = HTTPBearer(auto_error=False, description="POST /api/auth/login 응답의 access_token")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise AppError(401, "TOKEN_EXPIRED", "로그인이 필요합니다")
    user = db.get(User, decode_token(creds.credentials))
    if user is None:
        raise AppError(401, "TOKEN_EXPIRED", "세션이 만료되었습니다")
    return user


def membership_of(db: Session, user: User) -> Membership | None:
    return db.query(Membership).filter(Membership.user_id == user.id).first()


def require_member(db: Session, user: User, team_id: int) -> Membership:
    if db.get(Team, team_id) is None:
        raise AppError(404, "NOT_FOUND", "팀을 찾을 수 없습니다")
    m = (
        db.query(Membership)
        .filter(Membership.team_id == team_id, Membership.user_id == user.id)
        .first()
    )
    if m is None:
        raise AppError(403, "FORBIDDEN", "이 팀의 멤버가 아닙니다")
    return m


def iso(dt: datetime | None) -> str | None:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def parse_dt(value: str, end_of_day: bool = False) -> datetime:
    """ISO 8601 문자열 → UTC naive. 날짜만 오면 하루의 시작(또는 끝)으로 본다"""
    try:
        text = value.strip().replace("Z", "+00:00")
        date_only = len(text) <= 10
        dt = datetime.fromisoformat(text)
    except (ValueError, AttributeError):
        raise AppError(400, "VALIDATION_ERROR", "날짜 형식이 올바르지 않습니다")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    if date_only and end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt


def log_activity(db: Session, team_id: int, actor_id: int, kind: str, target: str = "") -> None:
    """활동 kind 는 5종뿐 - 정의서 6절"""
    assert kind in {"meeting_add", "todo_assign", "todo_done", "comment_add", "member_join"}
    db.add(Activity(team_id=team_id, actor_id=actor_id, kind=kind, target=target))


def activity_text(kind: str, actor: str, target: str) -> str:
    what, _, who = target.partition("||")
    return {
        "meeting_add": f"{actor}님이 회의록 '{target}'을(를) 추가했습니다",
        "todo_assign": f"{actor}님이 '{what}' 할 일을 {who}님에게 배정했습니다",
        "todo_done": f"{actor}님이 '{target}' 할 일을 완료했습니다",
        "comment_add": f"{actor}님이 '{target}' 회의록에 댓글을 남겼습니다",
        "member_join": f"{actor}님이 팀에 합류했습니다",
    }[kind]
