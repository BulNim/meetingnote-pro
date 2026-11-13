"""설정 - 루트 .env 를 실행 위치와 상관없이 읽고, 고정 상수를 한 곳에 둔다."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# 인증
JWT_SECRET_DEFAULT = "meetingnote-pro-local-secret-change-on-deploy"
JWT_ALGORITHM = "HS256"
JWT_TTL_HOURS = 24
PASSWORD_MIN = 8

# 팀 · 댓글 · 활동
TEAM_MAX_MEMBERS = 6
COMMENT_MAX = 500
ACTIVITY_LIMIT = 50

# 업로드 상한 - 로컬 20MB, 배포(Vercel) 4.5MB. 로컬에서 20MB 를 넘으면 Gemini Files API 로 올린다
MB = 1024 * 1024
UPLOAD_MAX_LOCAL = 20 * MB
UPLOAD_MAX_DEPLOY = int(4.5 * MB)
INLINE_MAX = 20 * MB

DEFAULT_MODEL = "gemini-3.1-flash-lite"

# CORS - 화면과 API 가 같은 주소라 개발 주소만 허용
CORS_ORIGINS = ["http://127.0.0.1:8000", "http://localhost:8000"]


def jwt_secret() -> str:
    return os.environ.get("JWT_SECRET") or JWT_SECRET_DEFAULT


def gemini_key() -> str:
    return (os.environ.get("GEMINI_API_KEY") or "").strip()


def gemini_model() -> str:
    return (os.environ.get("GEMINI_MODEL") or "").strip() or DEFAULT_MODEL


def is_deploy() -> bool:
    return bool(os.environ.get("VERCEL"))


def upload_max() -> int:
    return UPLOAD_MAX_DEPLOY if is_deploy() else UPLOAD_MAX_LOCAL


def database_url() -> str:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        return f"sqlite:///{(ROOT / 'meetingnote.db').as_posix()}"
    # Neon 이 주는 postgres:// 를 SQLAlchemy + psycopg 형식으로
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url
