"""환경 설정 - 프로젝트 루트의 .env 를 읽고, 경로 상수를 한 곳에 둔다"""
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env()


def jwt_secret() -> str:
    """JWT_SECRET 이 없으면 처음 한 번 만들어 backend/.jwt_secret(gitignore)에 보관한다"""
    value = os.environ.get("JWT_SECRET")
    if value:
        return value
    path = BACKEND / ".jwt_secret"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


# 로그인·가입 250ms 이내(정의서 8-1 ACME M)를 지키는 비용. 이 PC 에서 12 는 bcrypt 만 평균 224ms(최대 271ms), 11 은 106ms
DEFAULT_BCRYPT_ROUNDS = 11


def bcrypt_rounds() -> int:
    return int(os.environ.get("BCRYPT_ROUNDS", DEFAULT_BCRYPT_ROUNDS))


def docs_enabled() -> bool:
    return os.environ.get("ENABLE_DOCS", "1") != "0"
