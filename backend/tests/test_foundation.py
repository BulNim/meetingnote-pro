import pytest
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError

from app import models
from app.db import resolve_database_url
from app.errors import ERROR_CODES, ApiError, install_error_handlers


# ---- 1.3 DB 선택 ----
def test_sqlite_when_no_database_url():
    assert resolve_database_url("").startswith("sqlite:///")
    assert resolve_database_url("").endswith("meetingnote.db")


def test_postgres_when_database_url_given():
    url = resolve_database_url("postgres://u:p@host/db")
    assert url.startswith("postgresql+psycopg://u:p@host/db")
    assert resolve_database_url("postgresql://u:p@host/db").startswith("postgresql+psycopg://")


# ---- 1.4 모델 제약 ----
def _user(db, email="a@example.com"):
    u = models.User(email=email, password_hash="x", name="가")
    db.add(u)
    db.commit()
    return u


def test_one_membership_per_user(db_session):
    u = _user(db_session)
    t1 = models.Team(name="A", invite_code="MN-AAAA", owner_id=u.id)
    t2 = models.Team(name="B", invite_code="MN-BBBB", owner_id=u.id)
    db_session.add_all([t1, t2])
    db_session.commit()
    db_session.add(models.Membership(team_id=t1.id, user_id=u.id, role="owner"))
    db_session.commit()
    db_session.add(models.Membership(team_id=t2.id, user_id=u.id, role="member"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_activity_kind_is_limited(db_session):
    u = _user(db_session)
    t = models.Team(name="A", invite_code="MN-AAAA", owner_id=u.id)
    db_session.add(t)
    db_session.commit()
    db_session.add(models.Activity(team_id=t.id, actor_id=u.id, kind="team_create", target="x"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_todo_status_is_limited(db_session):
    u = _user(db_session)
    t = models.Team(name="A", invite_code="MN-AAAA", owner_id=u.id)
    db_session.add(t)
    db_session.commit()
    m = models.Meeting(team_id=t.id, title="회의", met_at=models.utcnow(), body="본문", author_id=u.id)
    db_session.add(m)
    db_session.commit()
    db_session.add(models.Todo(meeting_id=m.id, what="일", status="PAUSED"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_meeting_cascades_todos_and_comments(db_session):
    u = _user(db_session)
    t = models.Team(name="A", invite_code="MN-AAAA", owner_id=u.id)
    db_session.add(t)
    db_session.commit()
    m = models.Meeting(team_id=t.id, title="회의", met_at=models.utcnow(), body="본문", author_id=u.id)
    db_session.add(m)
    db_session.commit()
    db_session.add_all([
        models.Todo(meeting_id=m.id, what="일"),
        models.Comment(meeting_id=m.id, user_id=u.id, content="댓글"),
    ])
    db_session.commit()
    db_session.delete(m)
    db_session.commit()
    assert db_session.query(models.Todo).count() == 0
    assert db_session.query(models.Comment).count() == 0


# ---- 1.5 오류 본문 ----
def test_error_codes_are_closed_set_of_16():
    assert len(ERROR_CODES) == 16


def test_unknown_error_code_is_rejected():
    with pytest.raises(AssertionError):
        ApiError(400, "SOMETHING_ELSE", "x")


def test_error_body_has_code_and_msg_only():
    from fastapi.testclient import TestClient

    mini = FastAPI()
    install_error_handlers(mini)

    @mini.get("/boom")
    def boom():
        raise ApiError(409, "EMAIL_DUPLICATED", "이미 가입된 이메일")

    @mini.get("/n/{x}")
    def n(x: int):
        return x

    c = TestClient(mini)
    r = c.get("/boom")
    assert r.status_code == 409 and r.json() == {"code": "EMAIL_DUPLICATED", "msg": "이미 가입된 이메일"}
    r = c.get("/n/abc")
    assert r.status_code == 400 and set(r.json()) == {"code", "msg"} and r.json()["code"] == "VALIDATION_ERROR"
    r = c.get("/missing")
    assert r.status_code == 404 and r.json()["code"] == "NOT_FOUND"


# ---- 1.6 Swagger ----
def test_docs_and_openapi_open(client):
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    assert spec.json()["info"]["title"] == "MeetingNote Pro"


def test_starting_the_app_creates_all_seven_tables_in_an_empty_db(tmp_path):
    """서버를 처음 띄우면 빈 DB 에 테이블 7개가 만들어져야 한다 (create_all 이 모델 등록보다 먼저 돌던 사고 방지)"""
    import os
    import sqlite3
    import subprocess
    import sys
    from pathlib import Path

    backend = Path(__file__).resolve().parents[1]
    db = tmp_path / "fresh.db"
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{db.as_posix()}")
    env.pop("MEETINGNOTE_SKIP_INIT", None)
    subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, r'{backend}'); import app.main"],
                   check=True, env=env, capture_output=True)
    tables = {r[0] for r in sqlite3.connect(db).execute("select name from sqlite_master where type='table'")}
    assert {"users", "teams", "memberships", "meetings", "todos", "comments", "activities"} <= tables
