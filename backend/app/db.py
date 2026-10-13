"""DB 연결 - DATABASE_URL 이 있으면 Postgres(Neon), 없으면 로컬 SQLite 파일 한 줄 분기"""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from .config import ROOT


class Base(DeclarativeBase):
    pass


def normalize_url(url: str) -> str:
    """Neon 이 주는 postgresql:// 주소를 psycopg(3) 드라이버로 연결되는 형태로 바꾼다"""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def using_postgres() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def make_engine(url: str | None = None):
    url = url or os.environ.get("DATABASE_URL")
    if url:
        # 서버리스는 요청마다 새 환경이라 연결을 붙들어 두지 않는다 (Neon 풀러가 연결을 모아 준다)
        return create_engine(normalize_url(url), poolclass=NullPool)
    engine = create_engine(
        f"sqlite:///{ROOT / 'meetingnote.db'}", connect_args={"check_same_thread": False}
    )
    enable_sqlite_fk(engine)
    return engine


def enable_sqlite_fk(engine) -> None:
    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind=None) -> None:
    from . import models  # noqa: F401  (테이블 등록)

    Base.metadata.create_all(bind or engine)
