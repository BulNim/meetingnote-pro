from datetime import datetime, timedelta, timezone

import jwt as pyjwt

from app.config import get_settings
from app.security import create_token, decode_token
from app.errors import ApiError
import pytest

from .helpers import signup


# ---- 2.1 보안 ----
def test_expired_token_is_token_expired():
    old = datetime.now(timezone.utc) - timedelta(hours=25)
    token = create_token(1, now=old)  # 25시간 전에 발급 = 1시간 전에 만료
    with pytest.raises(ApiError) as e:
        decode_token(token)
    assert e.value.code == "TOKEN_EXPIRED"


def test_token_lives_24_hours():
    token = create_token(7)
    payload = pyjwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    assert payload["exp"] - payload["iat"] == 24 * 3600


def test_tampered_and_garbage_tokens_are_unauthorized():
    token = create_token(1)
    for bad in (token[:-3] + "abc", "garbage", pyjwt.encode({"sub": "1"}, "other-secret", algorithm="HS256")):
        with pytest.raises(ApiError) as e:
            decode_token(bad)
        assert e.value.code == "UNAUTHORIZED"


def test_no_token_is_unauthorized(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401 and r.json()["code"] == "UNAUTHORIZED"
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401 and r.json()["code"] == "UNAUTHORIZED"


def test_expired_token_on_api_call(client):
    headers, user = signup(client)
    old = datetime.now(timezone.utc) - timedelta(hours=30)
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {create_token(user['id'], now=old)}"})
    assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"


# ---- 2.2 가입 · 로그인 · 로그아웃 ----
def test_signup_ok_hashes_password(client, db_session):
    from app.models import User

    r = client.post("/api/auth/signup", json={"email": "User@Example.com", "password": "mypassword", "name": "홍길동"})
    assert r.status_code == 201
    body = r.json()
    assert body["token"] and body["user"]["email"] == "user@example.com"
    stored = db_session.query(User).one()
    assert stored.password_hash != "mypassword" and stored.password_hash.startswith("$2")


def test_signup_email_invalid(client):
    r = client.post("/api/auth/signup", json={"email": "user@@example", "password": "mypassword", "name": "가"})
    assert r.status_code == 400 and r.json()["code"] == "EMAIL_INVALID"


def test_signup_duplicate(client):
    signup(client, "a@example.com")
    r = client.post("/api/auth/signup", json={"email": "a@example.com", "password": "mypassword", "name": "나"})
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_DUPLICATED"


def test_signup_weak_password(client):
    r = client.post("/api/auth/signup", json={"email": "a@example.com", "password": "1234", "name": "가"})
    assert r.status_code == 400 and r.json()["code"] == "PASSWORD_TOO_WEAK"


def test_signup_missing_field_is_validation_error(client):
    r = client.post("/api/auth/signup", json={"email": "a@example.com"})
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


def test_login_ok(client):
    signup(client, "a@example.com", password="mypassword")
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "mypassword"})
    assert r.status_code == 200 and r.json()["token"]


def test_login_failure_does_not_reveal_which_part_is_wrong(client):
    signup(client, "a@example.com", password="mypassword")
    no_user = client.post("/api/auth/login", json={"email": "none@example.com", "password": "mypassword"})
    bad_pw = client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrongpass1"})
    assert no_user.status_code == bad_pw.status_code == 401
    assert no_user.json() == bad_pw.json()
    assert no_user.json()["code"] == "INVALID_CREDENTIALS"


def test_logout_ok(client):
    headers, _ = signup(client)
    r = client.post("/api/auth/logout", headers=headers)
    assert r.status_code == 200


def test_signup_and_login_do_not_need_a_token_but_others_do(client):
    # 로그인 없이 부르면 401 (회의록 목록은 팀 그룹에서 확인, 여기서는 대표로 me 와 logout)
    assert client.post("/api/auth/logout").status_code == 401
    assert client.put("/api/auth/me", json={"name": "x"}).status_code == 401


# ---- 2.3 내 정보 ----
def test_me_shows_role_none_without_team(client):
    headers, user = signup(client)
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"id": user["id"], "name": "김대리", "email": "kim@example.com", "role": None, "team_id": None}


def test_me_update_name_only_keeps_password(client):
    headers, _ = signup(client, "a@example.com", password="mypassword")
    r = client.put("/api/auth/me", json={"name": "김수석"}, headers=headers)
    assert r.status_code == 200 and r.json()["name"] == "김수석"
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "mypassword"}).status_code == 200


def test_password_change_needs_correct_current_password(client):
    headers, _ = signup(client, "a@example.com", password="mypassword")
    bad = client.put("/api/auth/me", json={"current_password": "wrongpass1", "new_password": "newpass1234"}, headers=headers)
    assert bad.status_code == 401 and bad.json()["code"] == "INVALID_CREDENTIALS"
    # 틀렸으니 바뀌지 않았다
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "mypassword"}).status_code == 200
    ok = client.put("/api/auth/me", json={"current_password": "mypassword", "new_password": "newpass1234"}, headers=headers)
    assert ok.status_code == 200
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "newpass1234"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "mypassword"}).status_code == 401


def test_password_change_without_current_password_is_rejected(client):
    headers, _ = signup(client)
    r = client.put("/api/auth/me", json={"new_password": "newpass1234"}, headers=headers)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


def test_weak_new_password(client):
    headers, _ = signup(client, password="mypassword")
    r = client.put("/api/auth/me", json={"current_password": "mypassword", "new_password": "1234"}, headers=headers)
    assert r.status_code == 400 and r.json()["code"] == "PASSWORD_TOO_WEAK"


def test_old_token_still_works_after_password_change(client):
    headers, _ = signup(client, password="mypassword")
    client.put("/api/auth/me", json={"current_password": "mypassword", "new_password": "newpass1234"}, headers=headers)
    assert client.get("/api/auth/me", headers=headers).status_code == 200
