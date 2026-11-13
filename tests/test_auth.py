from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend import db
from backend.models import Activity, User
from backend.security import make_token
from tests.conftest import Api, assert_error


def signup(client, email="hong@example.com", password="password1", name="홍길동"):
    return client.post("/api/auth/signup", json={"email": email, "password": password, "name": name})


def test_signup_ok_and_password_hashed(client):
    r = signup(client)
    assert r.status_code == 201
    j = r.json()
    assert j["token"] and j["user"] == {"id": j["user"]["id"], "name": "홍길동", "email": "hong@example.com", "role": None}
    with next(db.get_db()) as s:
        u = s.scalar(select(User).where(User.email == "hong@example.com"))
        assert u.password_hash != "password1" and u.password_hash.startswith("$2")


def test_signup_errors(client):
    assert_error(signup(client, email="hong@example"), 400, "EMAIL_INVALID")
    assert_error(signup(client, password="12345"), 400, "PASSWORD_TOO_WEAK")
    assert signup(client, email="kim@example.com").status_code == 201
    assert_error(signup(client, email="KIM@example.com"), 409, "EMAIL_DUPLICATED")


def test_login_ok_and_failures_look_the_same(client):
    signup(client)
    r = client.post("/api/auth/login", json={"email": "hong@example.com", "password": "password1"})
    assert r.status_code == 200 and r.json()["token"] and r.json()["user"]["name"] == "홍길동"
    wrong = client.post("/api/auth/login", json={"email": "hong@example.com", "password": "nope-nope"})
    nobody = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "password1"})
    assert_error(wrong, 401, "INVALID_CREDENTIALS")
    assert_error(nobody, 401, "INVALID_CREDENTIALS")
    assert wrong.json() == nobody.json()


def test_token_missing_forged_expired(client):
    a = Api(client, "홍길동")
    assert_error(client.get("/api/auth/me"), 401, "TOKEN_EXPIRED")
    assert_error(client.get("/api/auth/me", headers={"Authorization": "Bearer forged.token.value"}), 401, "TOKEN_EXPIRED")
    old = make_token(a.id, now=datetime.now(timezone.utc) - timedelta(hours=25))
    assert_error(client.get("/api/auth/me", headers={"Authorization": f"Bearer {old}"}), 401, "TOKEN_EXPIRED")
    assert a.get("/api/auth/me").status_code == 200


def test_me_role_and_update(client):
    a = Api(client, "홍길동")
    a.make_team()
    assert a.get("/api/auth/me").json()["role"] == "owner"
    r = a.put("/api/auth/me", json={"name": "홍길순"})
    assert r.status_code == 200 and r.json()["name"] == "홍길순"
    # 비밀번호를 보내지 않으면 그대로
    assert client.post("/api/auth/login", json={"email": a.email, "password": "password1"}).status_code == 200
    assert_error(a.put("/api/auth/me", json={"password": "12345"}), 400, "PASSWORD_TOO_WEAK")
    assert a.put("/api/auth/me", json={"password": "newpassword"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": a.email, "password": "newpassword"}).status_code == 200
    # 계정 변경은 활동 기록에 남기지 않음
    with next(db.get_db()) as s:
        assert s.scalars(select(Activity)).all() == []


def test_logout(client):
    a = Api(client, "홍길동")
    assert a.post("/api/auth/logout").status_code == 200


def test_error_body_shape(client):
    assert_error(client.post("/api/auth/signup", json={"email": "a@b.co"}), 400, "VALIDATION_ERROR")
    assert_error(client.post("/api/auth/signup", content=b"{not json", headers={"Content-Type": "application/json"}), 400, "VALIDATION_ERROR")
    assert_error(client.get("/api/nothing-here"), 404, "NOT_FOUND")
    a = Api(client, "홍길동")
    a.make_team()
    assert_error(a.put("/api/todos/999", json={"status": "DONE"}), 404, "NOT_FOUND")


def test_docs_and_static_do_not_collide(client):
    assert "swagger" in client.get("/docs").text.lower()
    spec = client.get("/openapi.json").json()
    ops = sum(len(v) for k, v in spec["paths"].items() if k.startswith("/api/"))
    assert ops == 27
    assert "HTTPBearer" in spec["components"]["securitySchemes"]
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/login.html"
