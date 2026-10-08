"""환경 설정 - 키는 프로젝트 루트의 .env 에서만 읽는다"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

MAX_UPLOAD_BYTES = 4_400_000  # 4.4MB (결정기록 D-004. Vercel 은 파일 약 4.49MB 부터 413 이라 여유를 둠)
JWT_HOURS = 24
TEAM_MAX_MEMBERS = 6
COMMENT_MAX_CHARS = 500
ACTIVITY_LIMIT = 50


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    jwt_secret: str
    database_url: str
    cors_origins: list[str]


def get_settings() -> Settings:
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        jwt_secret=os.getenv("JWT_SECRET", "dev-only-secret-change-me-in-production-0000"),
        database_url=os.getenv("DATABASE_URL", ""),
        cors_origins=[
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
    )
