"""DB 연결 - DATABASE_URL 이 있으면 Postgres(Neon), 없으면 SQLite. 분기는 여기 한 곳"""
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import ROOT, get_settings


class Base(DeclarativeBase):
    pass


def resolve_database_url(database_url: str | None = None) -> str:
    url = get_settings().database_url if database_url is None else database_url
    if url:
        # Neon 은 postgres:// 로 주는 경우가 있어 드라이버를 붙여 맞춤
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url
    return f"sqlite:///{(ROOT / 'meetingnote.db').as_posix()}"


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # SQLite 는 외래키(cascade)를 직접 켜야 함
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine
    return create_engine(url, pool_pre_ping=True)


engine = make_engine(resolve_database_url())
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
