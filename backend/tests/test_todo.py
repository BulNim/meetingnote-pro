"""5. todo 스펙 시나리오"""
from conftest import signup


def seed(client, team, headers, todos=("업로드 화면 연결",)):
    r = client.post(
        f"/api/teams/{team['id']}/meetings",
        json={"title": "계획 회의", "met_at": "2026-09-24T05:00:00Z", "body": "본문", "todos": [{"what": w, "due_text": "금요일"} for w in todos]},
        headers=headers,
    )
    return r.json()["todos"]


def my_id(client, h):
    return client.get("/api/auth/me", headers=h).json()["id"]


def test_팀_전체_할일은_회의록_제목과_고정_필드(client, owner, team):
    seed(client, team, owner)
    rows = client.get(f"/api/teams/{team['id']}/todos", headers=owner).json()
    assert len(rows) == 1 and rows[0]["meeting_title"] == "계획 회의"
    assert set(rows[0]) == {"id", "what", "assignee_id", "assignee_name", "due_text", "status", "meeting_title"}


def test_빈_상태는_200_빈_배열(client, owner, team):
    assert client.get(f"/api/teams/{team['id']}/todos", headers=owner).json() == []
    assert client.get("/api/me/todos", headers=owner).json() == []


def test_내_할일은_본인에게_배정된_것만(client, owner, team, member):
    a, b = seed(client, team, owner, ["A", "B"])
    client.put(f"/api/todos/{a['id']}", json={"assignee_id": my_id(client, member)}, headers=owner)
    assert [t["what"] for t in client.get("/api/me/todos", headers=member).json()] == ["A"]
    assert client.get("/api/me/todos", headers=owner).json() == []


def test_정렬은_status_다음_due_text(client, owner, team):
    a, b, c = seed(client, team, owner, ["A", "B", "C"])
    client.put(f"/api/todos/{a['id']}", json={"status": "DONE"}, headers=owner)
    client.put(f"/api/todos/{b['id']}", json={"status": "DOING"}, headers=owner)
    order = [t["status"] for t in client.get(f"/api/teams/{team['id']}/todos", headers=owner).json()]
    assert order == ["OPEN", "DOING", "DONE"]


def test_완료로_옮기면_todo_done이_남는다(client, owner, team, member):
    (t,) = seed(client, team, owner)
    r = client.put(f"/api/todos/{t['id']}", json={"status": "DOING"}, headers=member)
    assert r.status_code == 200 and r.json()["status"] == "DOING"
    client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=member)
    kinds = [a["kind"] for a in client.get(f"/api/teams/{team['id']}/activities", headers=owner).json()]
    assert "todo_done" in kinds
    client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=member)  # 이미 완료 - 중복 기록 없음
    kinds = [a["kind"] for a in client.get(f"/api/teams/{team['id']}/activities", headers=owner).json()]
    assert kinds.count("todo_done") == 1


def test_잘못된_상태는_400이고_그대로(client, owner, team):
    (t,) = seed(client, team, owner)
    r = client.put(f"/api/todos/{t['id']}", json={"status": "FINISHED"}, headers=owner)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"
    assert client.get("/api/teams/%d/todos" % team["id"], headers=owner).json()[0]["status"] == "OPEN"


def test_담당자_배정은_todo_assign을_남긴다(client, owner, team, member):
    (t,) = seed(client, team, owner)
    r = client.put(f"/api/todos/{t['id']}", json={"assignee_id": my_id(client, member)}, headers=owner)
    assert r.status_code == 200 and r.json()["assignee_name"] == "박과장"
    acts = client.get(f"/api/teams/{team['id']}/activities", headers=owner).json()
    assert acts[0]["kind"] == "todo_assign" and "박과장" in acts[0]["text"]


def test_담당자_미정으로_되돌린다(client, owner, team, member):
    (t,) = seed(client, team, owner)
    client.put(f"/api/todos/{t['id']}", json={"assignee_id": my_id(client, member)}, headers=owner)
    r = client.put(f"/api/todos/{t['id']}", json={"assignee_id": None}, headers=owner)
    assert r.json()["assignee_id"] is None


def test_팀_밖_사용자는_담당자가_될_수_없다(client, owner, team):
    (t,) = seed(client, team, owner)
    other = signup(client, "out@example.com", "팀밖")
    r = client.put(f"/api/todos/{t['id']}", json={"assignee_id": my_id(client, other)}, headers=owner)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


def test_owner는_삭제하고_member는_OWNER_ONLY(client, owner, team, member):
    a, b = seed(client, team, owner, ["A", "B"])
    denied = client.delete(f"/api/todos/{a['id']}", headers=member)
    assert denied.status_code == 403 and denied.json()["code"] == "OWNER_ONLY"
    assert client.delete(f"/api/todos/{a['id']}", headers=owner).status_code == 204
    assert [t["what"] for t in client.get(f"/api/teams/{team['id']}/todos", headers=owner).json()] == ["B"]


def test_서버는_기한_지남을_판정하지_않는다(client, owner, team):
    seed(client, team, owner)
    row = client.get(f"/api/teams/{team['id']}/todos", headers=owner).json()[0]
    assert not any("overdue" in k or "late" in k for k in row) and row["due_text"] == "금요일"


def test_다른_팀의_할일은_FORBIDDEN(client, owner, team):
    (t,) = seed(client, team, owner)
    other = signup(client, "o2@example.com", "타팀")
    client.post("/api/teams", json={"name": "다른팀"}, headers=other)
    assert client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=other).status_code == 403
