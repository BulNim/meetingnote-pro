r"""Neon(Postgres) 스키마 마이그레이션 - 7테이블을 만든다. 반복 실행해도 안전하다(있는 테이블은 건드리지 않음)

    cd backend
    .venv\Scripts\python migrate.py            # 없는 테이블만 만든다
    .venv\Scripts\python migrate.py --reset    # 모든 테이블을 지우고 다시 만든다 (데이터가 사라짐)

접속 주소는 DATABASE_URL_UNPOOLED(DDL 은 풀러를 거치지 않는 직접 연결이 안전), 없으면 DATABASE_URL 을 쓴다.
환경변수가 없으면 프로젝트 루트의 .env.local (vercel env pull 이 만든 파일)에서 읽는다.
"""
import os
import sys

from app import config

config.load_env(config.ROOT / ".env.local")
url = os.environ.get("DATABASE_URL_UNPOOLED") or os.environ.get("DATABASE_URL")
if not url:
    sys.exit("DATABASE_URL 이 없습니다. vercel env pull 로 .env.local 을 만들거나 환경변수로 넘기세요.")
os.environ["DATABASE_URL"] = url   # db.py 가 같은 주소를 쓰도록 맞춘다

from sqlalchemy import inspect  # noqa: E402

from app import db, models  # noqa: E402,F401  (모델 등록)

engine = db.make_engine()
host = engine.url.host
print(f"대상: {engine.url.drivername} @ {host}")
if "--reset" in sys.argv:
    print("--reset: 기존 테이블을 모두 지웁니다")
    db.Base.metadata.drop_all(engine)
db.Base.metadata.create_all(engine)

names = sorted(inspect(engine).get_table_names())
expected = sorted(db.Base.metadata.tables)
print("테이블:", ", ".join(names))
missing = set(expected) - set(names)
if missing:
    sys.exit(f"만들지 못한 테이블: {sorted(missing)}")
print(f"완료: {len(expected)}개 테이블 확인")
