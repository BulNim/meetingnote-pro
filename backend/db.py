"""DB 엔진과 세션. DATABASE_URL 이 있으면 Postgres(Neon), 없으면 SQLite."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from . import config


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_Session: sessionmaker | None = None


def init_engine(url: str | None = None) -> Engine:
    """엔진을 (다시) 만든다. 시험은 임시 SQLite 주소를 넘긴다."""
    global _engine, _Session
    url = url or config.database_url()
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
    _engine = create_engine(url, **kwargs)
    _Session = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def engine() -> Engine:
    return _engine or init_engine()


def create_all() -> None:
    from . import models  # noqa: F401 - 테이블 등록

    Base.metadata.create_all(engine())


def get_db() -> Iterator[Session]:
    if _Session is None:
        init_engine()
    db = _Session()
    try:
        yield db
    finally:
        db.close()
