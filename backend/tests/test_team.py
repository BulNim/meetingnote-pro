import re

from app import models

from .helpers import join_team, make_team, signup


def _owner_and_team(client):
    h, u = signup(client, "owner@example.com", "김대리")
    return h, u, make_team(client, h)


# ---- 3.1 팀 생성 · 조회 ----
def test_create_team_makes_owner_and_code(client):
    h, u, team = _owner_and_team(client)
    assert re.fullmatch(r"MN-[A-Z2-9]{4}", team["invite_code"])
    assert team["role"] == "owner"
    me = client.get("/api/auth/me", headers=h).json()
    assert me["role"] == "owner" and me["team_id"] == team["id"]


def test_team_creation_leaves_no_activity(client, db_session):
    _owner_and_team(client)
    assert db_session.query(models.Activity).count() == 0


def test_one_team_per_user(client):
    h, _, _ = _owner_and_team(client)
    r = client.post("/api/teams", json={"name": "둘째"}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


def test_my_teams_empty_then_one(client):
    h, _ = signup(client)
    assert client.get("/api/teams", headers=h).json() == []
    team = make_team(client, h)
    got = client.get("/api/teams", headers=h).json()
    assert len(got) == 1 and got[0]["id"] == team["id"] and got[0]["member_count"] == 1


def test_team_name_required(client):
    h, _ = signup(client)
    r = client.post("/api/teams", json={"name": "   "}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


# ---- 3.2 합류 ----
def test_join_ok_records_member_join(client, db_session):
    _, _, team = _owner_and_team(client)
    h2, _ = signup(client, "p@example.com", "박과장")
    r = join_team(client, h2, team["invite_code"])
    assert r.status_code == 200 and r.json()["role"] == "member"
    acts = db_session.query(models.Activity).all()
    assert [a.kind for a in acts] == ["member_join"]
    assert acts[0].target == "초대코드로 합류"


def test_join_accepts_lowercase_code(client):
    _, _, team = _owner_and_team(client)
    h2, _ = signup(client, "p@example.com", "박과장")
    assert join_team(client, h2, team["invite_code"].lower()).status_code == 200


def test_join_unknown_code_keeps_account(client):
    h, _ = signup(client)
    r = join_team(client, h, "MN-0000")
    assert r.status_code == 404 and r.json()["code"] == "INVITE_NOT_FOUND"
    assert client.get("/api/auth/me", headers=h).status_code == 200  # 계정은 그대로


def test_join_full_team(client):
    _, _, team = _owner_and_team(client)
    for i in range(5):  # 방장 포함 6명
        h, _ = signup(client, f"m{i}@example.com", f"멤버{i}")
        assert join_team(client, h, team["invite_code"]).status_code == 200
    h7, _ = signup(client, "late@example.com", "늦은사람")
    r = join_team(client, h7, team["invite_code"])
    assert r.status_code == 409 and r.json()["code"] == "TEAM_FULL"
    assert client.get("/api/auth/me", headers=h7).json()["role"] is None


def test_join_when_already_in_team(client):
    h, _, team = _owner_and_team(client)
    r = join_team(client, h, team["invite_code"])
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


# ---- 3.3 이름 · 코드 (owner 전용) ----
def test_owner_renames_and_reissues_code(client):
    h, _, team = _owner_and_team(client)
    h2, _ = signup(client, "p@example.com", "박과장")
    join_team(client, h2, team["invite_code"])

    r = client.put(f"/api/teams/{team['id']}", json={"name": "개발팀"}, headers=h)
    assert r.status_code == 200 and r.json()["name"] == "개발팀"

    old = team["invite_code"]
    new = client.put(f"/api/teams/{team['id']}/code", headers=h).json()["invite_code"]
    assert new != old and new.startswith("MN-")
    h3, _ = signup(client, "n@example.com", "신입")
    assert join_team(client, h3, old).status_code == 404  # 앞의 코드는 폐기
    assert join_team(client, h3, new).status_code == 200
    members = client.get(f"/api/teams/{team['id']}/members", headers=h).json()
    assert [m["name"] for m in members] == ["김대리", "박과장", "신입"]  # 기존 멤버 유지


def test_member_cannot_rename_or_reissue(client):
    _, _, team = _owner_and_team(client)
    h2, _ = signup(client, "p@example.com", "박과장")
    join_team(client, h2, team["invite_code"])
    r1 = client.put(f"/api/teams/{team['id']}", json={"name": "해킹"}, headers=h2)
    r2 = client.put(f"/api/teams/{team['id']}/code", headers=h2)
    for r in (r1, r2):
        assert r.status_code == 403 and r.json()["code"] == "OWNER_ONLY"


# ---- 3.4 멤버 · 남의 팀 ----
def test_members_list_with_todo_count(client, db_session):
    h, owner, team = _owner_and_team(client)
    h2, p = signup(client, "p@example.com", "박과장")
    join_team(client, h2, team["invite_code"])
    m = models.Meeting(team_id=team["id"], title="회의", met_at=models.utcnow(), body="본문", author_id=owner["id"])
    db_session.add(m)
    db_session.commit()
    db_session.add_all([
        models.Todo(meeting_id=m.id, what="가", assignee_id=owner["id"], status="DONE"),
        models.Todo(meeting_id=m.id, what="나", assignee_id=owner["id"]),
        models.Todo(meeting_id=m.id, what="다", assignee_id=None),
    ])
    db_session.commit()
    rows = client.get(f"/api/teams/{team['id']}/members", headers=h2).json()
    by_name = {r["name"]: r for r in rows}
    assert by_name["김대리"]["todo_count"] == 2 and by_name["김대리"]["role"] == "owner"
    assert by_name["박과장"]["todo_count"] == 0 and by_name["박과장"]["role"] == "member"
    assert set(rows[0]) == {"id", "name", "email", "role", "todo_count"}


def test_other_team_gets_404_without_leaking_existence(client):
    _, _, team_a = _owner_and_team(client)
    hb, _ = signup(client, "b@example.com", "다른팀장")
    make_team(client, hb, "다른팀")
    r = client.get(f"/api/teams/{team_a['id']}/members", headers=hb)
    assert r.status_code == 404
    missing = client.get("/api/teams/9999/members", headers=hb)
    assert missing.status_code == 404 and missing.json() == r.json()  # 있는 팀과 없는 팀이 같은 응답
