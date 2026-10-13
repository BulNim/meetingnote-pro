import os
import sys
from pathlib import Path

# 테스트는 bcrypt 비용을 낮춰 빠르게 돈다. 속도 시험은 test_auth 에서 기본 비용으로 따로 잰다
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-meetingnote-pro-pytest-32b+")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import db as dbmod  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    """테스트마다 새 인메모리 SQLite"""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    dbmod.enable_sqlite_fk(engine)
    dbmod.init_db(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[dbmod.get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def signup(client, email="kim@example.com", name="김대리", password="password1"):
    r = client.post("/api/auth/signup", json={"email": email, "password": password, "name": name})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture()
def owner(client):
    return signup(client)


@pytest.fixture()
def team(client, owner):
    r = client.post("/api/teams", json={"name": "기획팀"}, headers=owner)
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def member(client, team):
    h = signup(client, "park@example.com", "박과장")
    r = client.post("/api/teams/join", json={"invite_code": team["invite_code"]}, headers=h)
    assert r.status_code == 200
    return h
