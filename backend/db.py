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
    upgrade()


def upgrade() -> None:
    """이미 있는 DB 를 맞춘다 - todos.due_date 칼럼이 없으면 만들고, 빈 due_date 를 기한 글자에서 한 번 채운다."""
    from sqlalchemy import inspect, select, text

    from .duedate import base_date, resolve
    from .models import Meeting, Todo

    eng = engine()
    cols = {c["name"] for c in inspect(eng).get_columns("todos")}
    if "due_date" not in cols:
        with eng.begin() as conn:
            conn.execute(text("ALTER TABLE todos ADD COLUMN due_date DATE"))
    db = _Session() if _Session is not None else sessionmaker(bind=eng)()
    try:
        rows = db.execute(
            select(Todo, Meeting.met_at).outerjoin(Meeting, Meeting.id == Todo.meeting_id)
            .where(Todo.due_date.is_(None), Todo.due_text != "")
        ).all()
        changed = 0
        for t, met_at in rows:
            d = resolve(t.due_text, base_date(t.created_at, met_at))
            if d is not None:
                t.due_date, changed = d, changed + 1
        if changed:
            db.commit()
    finally:
        db.close()


def get_db() -> Iterator[Session]:
    if _Session is None:
        init_engine()
    db = _Session()
    try:
        yield db
    finally:
        db.close()
