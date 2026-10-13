"""1. 뼈대 - 7테이블 · 오류 형식 · 토큰"""
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import create_engine, inspect

from app import config, db as dbmod, security
from app.errors import AppError


def test_빈_DB에_7테이블이_생긴다():
    engine = create_engine("sqlite://")
    dbmod.init_db(engine)
    assert set(inspect(engine).get_table_names()) == {
        "users", "teams", "memberships", "meetings", "todos", "comments", "activities",
    }


def test_없는_경로와_잘못된_입력이_같은_형식이다(client):
    r = client.get("/api/없는경로")
    assert r.status_code == 404 and set(r.json()) == {"code", "msg"} and r.json()["code"] == "NOT_FOUND"
    r = client.post("/api/auth/login", json={"email": "a"})
    assert r.status_code == 400 and set(r.json()) == {"code", "msg"} and r.json()["code"] == "VALIDATION_ERROR"


def test_토큰_발급_검증():
    assert security.decode_token(security.create_token(7)) == 7


def test_만료된_토큰은_TOKEN_EXPIRED():
    past = datetime.now(timezone.utc) - timedelta(hours=25)
    old = jwt.encode(
        {"sub": "1", "iat": past, "exp": past + timedelta(hours=24)}, config.jwt_secret(), algorithm="HS256"
    )
    try:
        security.decode_token(old)
        raise AssertionError("만료 토큰이 통과함")
    except AppError as e:
        assert (e.status, e.code) == (401, "TOKEN_EXPIRED")


def test_위조된_토큰은_TOKEN_EXPIRED():
    forged = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "다른-비밀", algorithm="HS256")
    try:
        security.decode_token(forged)
        raise AssertionError("위조 토큰이 통과함")
    except AppError as e:
        assert e.code == "TOKEN_EXPIRED"


def test_토큰_없이_부르면_401(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"


def test_Neon_주소는_psycopg_드라이버_주소로_바뀐다():
    assert dbmod.normalize_url("postgresql://u:p@h/db?sslmode=require") == "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert dbmod.normalize_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert dbmod.normalize_url("sqlite:///x.db") == "sqlite:///x.db"
