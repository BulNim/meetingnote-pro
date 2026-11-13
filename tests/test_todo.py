from tests.conftest import Api, Classified, TodoItem, assert_error


def test_direct_create_and_fields(client, team):
    owner, park = team["owner"], team["park"]
    r = owner.post(f"/api/teams/{owner.team_id}/todos", json={"what": "인터뷰", "assignee_id": park.id, "due_text": "금요일"})
    assert r.status_code == 201
    t = r.json()
    assert set(t) == {"id", "what", "assignee_id", "assignee_name", "due_text", "due_date", "status",
                      "meeting_id", "meeting_title", "can_delete"}
    assert t["status"] == "OPEN" and t["meeting_title"] is None and t["assignee_name"] == "박과장"
    assert [a["kind"] for a in owner.get("/api/me/activities").json()] == ["todo_assign"]
    assert_error(owner.post(f"/api/teams/{owner.team_id}/todos", json={"what": " "}), 400, "VALIDATION_ERROR")


def test_status_changes_and_activity(client, team):
    owner = team["owner"]
    t = owner.post(f"/api/teams/{owner.team_id}/todos", json={"what": "일"}).json()
    url = f"/api/todos/{t['id']}"
    assert team["lee"].put(url, json={"status": "DOING"}).json()["status"] == "DOING"  # 팀원 누구나
    assert owner.get(f"/api/teams/{owner.team_id}/activities").json()[0]["kind"] == "member_join"  # DOING 은 기록 없음
    assert owner.put(url, json={"status": "DONE"}).json()["status"] == "DONE"
    assert owner.put(url, json={"status": "OPEN"}).json()["status"] == "OPEN"  # 되돌림 허용
    kinds = [a["kind"] for a in owner.get(f"/api/teams/{owner.team_id}/activities").json()]
    assert kinds.count("todo_done") == 1
    assert_error(owner.put(url, json={"status": "WAIT"}), 400, "VALIDATION_ERROR")


def test_assign_rules(client, team):
    owner, park = team["owner"], team["park"]
    t = owner.post(f"/api/teams/{owner.team_id}/todos", json={"what": "일"}).json()
    url = f"/api/todos/{t['id']}"
    r = owner.put(url, json={"assignee_id": park.id, "due_text": "어제"})
    assert r.json()["assignee_name"] == "박과장" and r.json()["due_text"] == "어제"
    assert owner.put(url, json={"assignee_id": None}).json()["assignee_id"] is None  # 미정도 한 값
    outsider = Api(client, "외부인")
    outsider.make_team("다른팀")
    assert_error(owner.put(url, json={"assignee_id": outsider.id}), 400, "VALIDATION_ERROR")
    assert_error(outsider.put(url, json={"status": "DONE"}), 404, "NOT_FOUND")


def test_delete_permission_matches_can_delete(client, team):
    owner, park, lee = team["owner"], team["park"], team["lee"]
    tid = owner.team_id
    t = park.post(f"/api/teams/{tid}/todos", json={"what": "박과장이 만든 일", "assignee_id": owner.id}).json()
    seen = {x["id"]: x["can_delete"] for x in lee.get(f"/api/teams/{tid}/todos").json()}
    assert seen[t["id"]] is False
    assert_error(lee.delete(f"/api/todos/{t['id']}"), 403, "FORBIDDEN")
    t2 = park.post(f"/api/teams/{tid}/todos", json={"what": "담당자가 지움", "assignee_id": lee.id}).json()
    assert lee.get(f"/api/teams/{tid}/todos").json()  # 목록 확인
    assert next(x for x in lee.get(f"/api/teams/{tid}/todos").json() if x["id"] == t2["id"])["can_delete"] is True
    assert lee.delete(f"/api/todos/{t2['id']}").status_code == 204
    assert owner.delete(f"/api/todos/{t['id']}").status_code == 204  # owner


def test_meeting_todo_author_is_uploader(client, team, fake):
    owner, park, lee = team["owner"], team["park"], team["lee"]
    fake.result = Classified(summary="s", decisions=[], todos=[TodoItem(what="뽑힌 일")])
    m = park.new_meeting()
    t = m["todos"][0]
    assert t["meeting_title"] == m["title"]
    assert next(x for x in lee.get(f"/api/teams/{park.team_id}/todos").json() if x["id"] == t["id"])["can_delete"] is False
    assert park.delete(f"/api/todos/{t['id']}").status_code == 204


def test_sort_and_my_todos(client, team):
    owner, park = team["owner"], team["park"]
    tid = owner.team_id
    a = owner.post(f"/api/teams/{tid}/todos", json={"what": "a", "due_text": "", "assignee_id": park.id}).json()
    b = owner.post(f"/api/teams/{tid}/todos", json={"what": "b", "due_text": "금요일"}).json()
    c = owner.post(f"/api/teams/{tid}/todos", json={"what": "c", "due_text": "월요일"}).json()
    owner.put(f"/api/todos/{c['id']}", json={"status": "DONE"})
    assert [x["what"] for x in owner.get(f"/api/teams/{tid}/todos").json()] == ["b", "a", "c"]
    assert [x["id"] for x in park.get("/api/me/todos").json()] == [a["id"]]
    assert team["lee"].get("/api/me/todos").json() == []


# ── modify-todo-due-date ──
from datetime import datetime  # noqa: E402

import backend.routers.todos as todos_router  # noqa: E402


def fix_now(monkeypatch, iso):
    """직접 등록의 기준일(등록 시각, UTC)을 고정한다."""
    monkeypatch.setattr(todos_router, "utcnow", lambda: datetime.fromisoformat(iso))


def test_direct_create_base_is_registration_day(client, team, monkeypatch):
    owner = team["owner"]
    fix_now(monkeypatch, "2026-11-13T03:00:00")  # 한국 11-13(금) 12:00
    t = owner.post(f"/api/teams/{owner.team_id}/todos", json={"what": "a", "due_text": "다음 주까지"}).json()
    assert t["due_text"] == "다음 주까지" and t["due_date"] == "2026-11-20"
    fix_now(monkeypatch, "2026-11-12T16:00:00")  # UTC 11-12 16:00 = 한국 11-13 01:00
    t = owner.post(f"/api/teams/{owner.team_id}/todos", json={"what": "b", "due_text": "내일"}).json()
    assert t["due_date"] == "2026-11-14"
    t = owner.post(f"/api/teams/{owner.team_id}/todos", json={"what": "c", "due_text": "이번 주 안"}).json()
    assert t["due_date"] is None and t["due_text"] == "이번 주 안"


def test_edit_due_text_recomputes(client, team, monkeypatch):
    owner = team["owner"]
    fix_now(monkeypatch, "2026-11-12T03:00:00")  # 한국 11-12(목)
    t = owner.post(f"/api/teams/{owner.team_id}/todos", json={"what": "a", "due_text": "내일"}).json()
    assert t["due_date"] == "2026-11-13"
    fix_now(monkeypatch, "2026-11-20T03:00:00")  # 고치는 날은 기준일이 아님 - 등록일 그대로
    r = owner.put(f"/api/todos/{t['id']}", json={"due_text": "다음 주 월요일"}).json()
    assert r["due_text"] == "다음 주 월요일" and r["due_date"] == "2026-11-16"
    r = owner.put(f"/api/todos/{t['id']}", json={"due_text": ""}).json()
    assert r["due_text"] == "" and r["due_date"] is None
    r = owner.put(f"/api/todos/{t['id']}", json={"status": "DOING"}).json()  # 상태만 바꾸면 기한 그대로
    assert r["due_date"] is None


def test_sort_by_due_date(client, team, monkeypatch):
    owner = team["owner"]
    fix_now(monkeypatch, "2026-11-12T03:00:00")
    tid = owner.team_id
    for what, due in [("20일", "다음 주 금요일"), ("없음", "이번 주 안"), ("13일", "내일"), ("빈칸", "")]:
        owner.post(f"/api/teams/{tid}/todos", json={"what": what, "due_text": due})
    done = owner.post(f"/api/teams/{tid}/todos", json={"what": "완료", "due_text": "어제"}).json()
    owner.put(f"/api/todos/{done['id']}", json={"status": "DONE"})
    rows = owner.get(f"/api/teams/{tid}/todos").json()
    assert [x["what"] for x in rows] == ["13일", "20일", "없음", "빈칸", "완료"]
    assert [x["due_date"] for x in rows][:2] == ["2026-11-13", "2026-11-20"]
