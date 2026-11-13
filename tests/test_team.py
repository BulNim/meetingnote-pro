import re

from tests.conftest import Api, assert_error


def test_create_team_owner_and_code(client):
    a = Api(client, "김대리")
    t = a.make_team("기획팀")
    assert t["role"] == "owner" and t["name"] == "기획팀" and re.fullmatch(r"MN-[A-Z0-9]{4}", t["invite_code"])
    assert a.get("/api/teams").json()[0]["id"] == t["id"]
    assert_error(a.post("/api/teams", json={"name": "두번째"}), 400, "VALIDATION_ERROR")
    # 팀 생성은 활동 기록 없음
    assert a.get(f"/api/teams/{t['id']}/activities").json() == []


def test_no_team_returns_empty_list(client):
    assert Api(client, "홍길동").get("/api/teams").json() == []


def test_join_flow(client, team):
    park = team["park"]
    assert park.get("/api/auth/me").json()["role"] == "member"
    kinds = [a["kind"] for a in team["owner"].get(f"/api/teams/{park.team_id}/activities").json()]
    assert kinds.count("member_join") == 2
    assert_error(park.join(team["code"]), 400, "VALIDATION_ERROR")
    assert_error(Api(client, "외부인").join("MN-0000"), 404, "INVITE_NOT_FOUND")


def test_team_full(client, team):
    for n in ("최선임", "정사원", "한대리"):  # 3 + 3 = 6
        assert Api(client, n).join(team["code"]).status_code == 200
    assert_error(Api(client, "일곱째").join(team["code"]), 409, "TEAM_FULL")


def test_reissue_code(client, team):
    owner, park = team["owner"], team["park"]
    assert_error(park.put(f"/api/teams/{owner.team_id}/code"), 403, "OWNER_ONLY")
    new = owner.put(f"/api/teams/{owner.team_id}/code").json()["invite_code"]
    assert new != team["code"]
    assert_error(Api(client, "늦은사람").join(team["code"]), 404, "INVITE_NOT_FOUND")
    assert Api(client, "새사람").join(new).status_code == 200
    assert len(owner.get(f"/api/teams/{owner.team_id}/members").json()) == 4


def test_rename_owner_only(client, team):
    owner, park = team["owner"], team["park"]
    assert_error(park.put(f"/api/teams/{owner.team_id}", json={"name": "바꿈"}), 403, "OWNER_ONLY")
    assert owner.put(f"/api/teams/{owner.team_id}", json={"name": "기획2팀"}).json()["name"] == "기획2팀"


def test_members_and_todo_count(client, team, fake):
    owner, park = team["owner"], team["park"]
    tid = owner.team_id
    t1 = owner.post(f"/api/teams/{tid}/todos", json={"what": "a", "assignee_id": park.id}).json()
    owner.post(f"/api/teams/{tid}/todos", json={"what": "b", "assignee_id": park.id})
    owner.put(f"/api/todos/{t1['id']}", json={"status": "DONE"})
    rows = {m["name"]: m for m in owner.get(f"/api/teams/{tid}/members").json()}
    assert set(rows) == {"김대리", "박과장", "이주임"}
    assert rows["박과장"]["todo_count"] == 2 and rows["김대리"]["role"] == "owner"
    assert set(rows["박과장"]) == {"id", "name", "email", "role", "todo_count"}


def test_other_team_forbidden(client, team):
    other = Api(client, "남의팀")
    other.make_team("다른팀")
    assert_error(other.get(f"/api/teams/{team['owner'].team_id}/members"), 403, "FORBIDDEN")
