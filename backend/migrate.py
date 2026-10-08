"""DB 테이블을 만든다 (멱등). DATABASE_URL 이 있으면 그 Postgres(Neon), 없으면 로컬 SQLite.

    DATABASE_URL=postgresql://... python backend/migrate.py
"""
from sqlalchemy import inspect

from app import models  # noqa: F401  (테이블 정의 등록)
from app.db import Base, engine

EXPECTED = ["activities", "comments", "meetings", "memberships", "teams", "todos", "users"]


def main() -> list[str]:
    Base.metadata.create_all(engine)
    tables = sorted(inspect(engine).get_table_names())
    missing = [t for t in EXPECTED if t not in tables]
    print(f"대상: {engine.url.render_as_string(hide_password=True)}")
    print("테이블:", ", ".join(tables))
    if missing:
        raise SystemExit(f"없는 테이블: {', '.join(missing)}")
    return tables


if __name__ == "__main__":
    main()
