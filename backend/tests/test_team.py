"""3. team 스펙 시나리오"""
import re

from conftest import signup


def test_팀_만들기는_owner와_MN_코드를_돌려준다(client, owner):
    r = client.post("/api/teams", json={"name": "기획팀"}, headers=owner)
    assert r.status_code == 201
    assert re.fullmatch(r"MN-[A-Z0-9]{4}", r.json()["invite_code"]) and r.json()["role"] == "owner"


def test_소속_팀_없음은_빈_배열(client, owner):
    r = client.get("/api/teams", headers=owner)
    assert r.status_code == 200 and r.json() == []


def test_내_팀_조회(client, owner, team):
    r = client.get("/api/teams", headers=owner)
    assert [t["id"] for t in r.json()] == [team["id"]]


def test_합류_성공시_member_join_이_남는다(client, owner, team, member):
    acts = client.get(f"/api/teams/{team['id']}/activities", headers=owner).json()
    assert [a["kind"] for a in acts] == ["member_join"]
    assert client.get("/api/auth/me", headers=member).json()["role"] == "member"


def test_없는_초대코드는_404(client, owner):
    r = client.post("/api/teams/join", json={"invite_code": "MN-ZZZZ"}, headers=owner)
    assert r.status_code == 404 and r.json()["code"] == "INVITE_NOT_FOUND"


def test_정원_6명_초과는_TEAM_FULL(client, owner, team):
    for i in range(5):
        h = signup(client, f"u{i}@example.com", f"멤버{i}")
        assert client.post("/api/teams/join", json={"invite_code": team["invite_code"]}, headers=h).status_code == 200
    extra = signup(client, "late@example.com", "늦은사람")
    r = client.post("/api/teams/join", json={"invite_code": team["invite_code"]}, headers=extra)
    assert r.status_code == 409 and r.json()["code"] == "TEAM_FULL"
    assert len(client.get(f"/api/teams/{team['id']}/members", headers=owner).json()) == 6


def test_멤버_목록은_고정_필드와_todo_count(client, owner, team, member):
    rows = client.get(f"/api/teams/{team['id']}/members", headers=owner).json()
    assert {tuple(sorted(r)) for r in rows} == {("email", "id", "name", "role", "todo_count")}
    assert sorted(r["role"] for r in rows) == ["member", "owner"] and all(r["todo_count"] == 0 for r in rows)


def test_owner는_팀_이름을_바꾼다(client, owner, team):
    r = client.put(f"/api/teams/{team['id']}", json={"name": "새이름"}, headers=owner)
    assert r.status_code == 200 and client.get("/api/teams", headers=owner).json()[0]["name"] == "새이름"


def test_member의_팀_이름_변경은_OWNER_ONLY(client, owner, team, member):
    r = client.put(f"/api/teams/{team['id']}", json={"name": "해킹"}, headers=member)
    assert r.status_code == 403 and r.json()["code"] == "OWNER_ONLY"
    assert client.get("/api/teams", headers=owner).json()[0]["name"] == "기획팀"


def test_코드_재발급후_옛_코드는_무효(client, owner, team):
    old = team["invite_code"]
    new = client.put(f"/api/teams/{team['id']}/code", headers=owner).json()["invite_code"]
    assert new != old
    h = signup(client, "x@example.com", "엑스")
    assert client.post("/api/teams/join", json={"invite_code": old}, headers=h).json()["code"] == "INVITE_NOT_FOUND"
    assert client.post("/api/teams/join", json={"invite_code": new}, headers=h).status_code == 200


def test_member의_코드_재발급은_OWNER_ONLY(client, team, member):
    r = client.put(f"/api/teams/{team['id']}/code", headers=member)
    assert r.status_code == 403 and r.json()["code"] == "OWNER_ONLY"


def test_다른_팀_자원은_FORBIDDEN(client, team):
    other = signup(client, "o@example.com", "타팀")
    client.post("/api/teams", json={"name": "다른팀"}, headers=other)
    r = client.get(f"/api/teams/{team['id']}/members", headers=other)
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"
