"""2. auth 스펙 시나리오"""
import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app import config, security
from conftest import signup


def test_가입_성공후_같은_이메일로_로그인된다(client):
    signup(client)
    r = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password1"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_이메일_형식_오류(client):
    r = client.post("/api/auth/signup", json={"email": "kim.example.com", "password": "password1", "name": "김"})
    assert r.status_code == 400 and r.json()["code"] == "EMAIL_INVALID"


def test_이메일_중복은_기존_계정을_바꾸지_않는다(client):
    signup(client)
    r = client.post("/api/auth/signup", json={"email": "kim@example.com", "password": "otherpass1", "name": "다른이름"})
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_DUPLICATED"
    ok = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password1"})
    assert ok.status_code == 200


def test_7자_비밀번호는_약함(client):
    r = client.post("/api/auth/signup", json={"email": "a@b.co", "password": "1234567", "name": "김"})
    assert r.status_code == 400 and r.json()["code"] == "PASSWORD_TOO_WEAK"


def test_로그인_실패는_두_경우_같은_응답(client):
    signup(client)
    no_user = client.post("/api/auth/login", json={"email": "none@example.com", "password": "password1"})
    bad_pw = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "wrongpass1"})
    assert no_user.status_code == bad_pw.status_code == 401
    assert no_user.json() == bad_pw.json() and bad_pw.json()["code"] == "INVALID_CREDENTIALS"


def test_로그인_토큰은_24시간_유효(client):
    signup(client)
    token = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password1"}).json()["access_token"]
    claims = jwt.decode(token, config.jwt_secret(), algorithms=["HS256"])
    assert claims["exp"] - claims["iat"] == 24 * 3600


def test_만료_토큰으로_me를_부르면_401(client):
    signup(client)
    past = datetime.now(timezone.utc) - timedelta(hours=25)
    old = jwt.encode({"sub": "1", "iat": past, "exp": past + timedelta(hours=24)}, config.jwt_secret(), algorithm="HS256")
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old}"})
    assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"


def test_me는_고정_필드만(client, owner):
    r = client.get("/api/auth/me", headers=owner)
    assert r.status_code == 200 and set(r.json()) == {"id", "name", "email", "role"}
    assert r.json()["role"] is None


def test_팀을_만들면_me의_role이_owner(client, owner, team):
    assert client.get("/api/auth/me", headers=owner).json()["role"] == "owner"


def test_이름_변경(client, owner):
    r = client.put("/api/auth/me", json={"name": "새이름"}, headers=owner)
    assert r.status_code == 200 and client.get("/api/auth/me", headers=owner).json()["name"] == "새이름"


def test_약한_새_비밀번호는_기존을_유지(client, owner):
    r = client.put("/api/auth/me", json={"password": "1234567"}, headers=owner)
    assert r.status_code == 400 and r.json()["code"] == "PASSWORD_TOO_WEAK"
    assert client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password1"}).status_code == 200


def test_비밀번호_변경이_반영된다(client, owner):
    client.put("/api/auth/me", json={"password": "newpassword1"}, headers=owner)
    assert client.post("/api/auth/login", json={"email": "kim@example.com", "password": "newpassword1"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password1"}).status_code == 401


def test_로그아웃은_200(client, owner):
    assert client.post("/api/auth/logout", headers=owner).status_code == 200


def test_비밀번호는_bcrypt_해시로만_저장되고_응답에_없다(client):
    from sqlalchemy.orm import Session
    from app import db as dbmod
    from app.main import app
    from app.models import User

    r = client.post("/api/auth/signup", json={"email": "h@example.com", "password": "password1", "name": "해시"})
    assert "password" not in r.text
    session = next(app.dependency_overrides[dbmod.get_db]())
    stored = session.query(User).filter(User.email == "h@example.com").one().password_hash
    assert stored != "password1" and stored.startswith("$2")
    assert "password1" not in client.get("/api/auth/me", headers={"Authorization": "Bearer " + r.json()["access_token"]}).text


@pytest.mark.skipif(config.bcrypt_rounds() < 4, reason="n/a")
def test_로그인_평균_250ms_이내_기본_비용(client, monkeypatch):
    """bcrypt 비용을 운영 기본값으로 돌려 잰다 - 정의서 8-1 ACME M"""
    monkeypatch.setenv("BCRYPT_ROUNDS", str(config.DEFAULT_BCRYPT_ROUNDS))
    signup(client)
    body = {"email": "kim@example.com", "password": "password1"}
    times = []
    for _ in range(3):
        t = time.perf_counter()
        assert client.post("/api/auth/login", json=body).status_code == 200
        times.append(time.perf_counter() - t)
    avg = sum(times) / len(times)
    assert avg <= 0.25, f"로그인 평균 {avg * 1000:.0f}ms"
