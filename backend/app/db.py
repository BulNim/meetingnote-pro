"""DB 연결 - DATABASE_URL 이 있으면 Postgres(Neon), 없으면 로컬 SQLite 파일 한 줄 분기"""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import ROOT


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None):
    url = url or os.environ.get("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return create_engine(url, pool_pre_ping=True)
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
