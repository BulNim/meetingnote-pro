from app import models
from app.services.gemini import Organized, TodoItem

from .helpers import join_team, make_team, signup

BODY = {"title": "2차 스프린트 계획 회의", "met_at": "2026-09-24T05:00:00Z", "attendees": "김대리", "body": "본문"}


def _setup(client, fake_gemini):
    """owner(김대리) + member(박과장) 팀, 할 일 3건이 있는 회의록 하나"""
    ho, owner = signup(client, "o@example.com", "김대리")
    team = make_team(client, ho)
    hm, member = signup(client, "p@example.com", "박과장")
    join_team(client, hm, team["invite_code"])
    fake_gemini.organized = Organized(
        summary="요약",
        decisions=["결정"],
        todos=[TodoItem("목록 구현", "김대리", "다음 주 금요일"),
               TodoItem("받아쓰기 오류 처리", "박과장", "이번 주 안"),
               TodoItem("사용자 인터뷰", None, "미정")],
    )
    meeting = client.post(f"/api/teams/{team['id']}/meetings", json=BODY, headers=ho).json()
    return ho, owner, hm, member, team, meeting


def _kinds(db):
    return [a.kind for a in db.query(models.Activity).order_by(models.Activity.id).all()]


# ---- 6.1 목록 ----
def test_team_and_my_todos(client, fake_gemini):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    all_rows = client.get(f"/api/teams/{team['id']}/todos", headers=ho).json()
    assert len(all_rows) == 3
    assert all(r["meeting_title"] == "2차 스프린트 계획 회의" for r in all_rows)
    assert set(all_rows[0]) == {"id", "what", "assignee_id", "assignee_name", "due_text", "status", "meeting_title"}
    mine = client.get("/api/me/todos", headers=hm).json()
    assert [r["what"] for r in mine] == ["받아쓰기 오류 처리"]
    assert client.get("/api/me/todos", headers=signup(client, "n@example.com", "신입")[0]).json() == []


def test_sorted_by_status_then_due(client, fake_gemini):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    rows = client.get(f"/api/teams/{team['id']}/todos", headers=ho).json()
    client.put(f"/api/todos/{rows[0]['id']}", json={"status": "DONE"}, headers=ho)
    got = client.get(f"/api/teams/{team['id']}/todos", headers=ho).json()
    assert [r["status"] for r in got] == ["OPEN", "OPEN", "DONE"]


def test_todo_of_other_team_is_hidden(client, fake_gemini):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    tid = client.get(f"/api/teams/{team['id']}/todos", headers=ho).json()[0]["id"]
    hb, _ = signup(client, "b@example.com", "다른")
    make_team(client, hb, "다른팀")
    assert client.get(f"/api/teams/{team['id']}/todos", headers=hb).status_code == 404
    assert client.put(f"/api/todos/{tid}", json={"status": "DONE"}, headers=hb).status_code == 404
    assert client.delete(f"/api/todos/{tid}", headers=hb).status_code == 404


# ---- 6.2 수정과 활동 ----
def test_status_changes_and_done_activity(client, fake_gemini, db_session):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    tid = client.get("/api/me/todos", headers=hm).json()[0]["id"]
    before = _kinds(db_session)
    assert client.put(f"/api/todos/{tid}", json={"status": "DOING"}, headers=hm).json()["status"] == "DOING"
    assert _kinds(db_session) == before  # 진행으로 옮기는 것은 기록하지 않는다
    r = client.put(f"/api/todos/{tid}", json={"status": "DONE"}, headers=hm)
    assert r.status_code == 200 and r.json()["meeting_title"]
    assert _kinds(db_session) == before + ["todo_done"]
    client.put(f"/api/todos/{tid}", json={"status": "DONE"}, headers=hm)  # 같은 값은 또 기록하지 않음
    assert _kinds(db_session) == before + ["todo_done"]
    back = client.put(f"/api/todos/{tid}", json={"status": "OPEN"}, headers=hm)  # 되돌림 허용
    assert back.status_code == 200 and back.json()["status"] == "OPEN"
    assert _kinds(db_session) == before + ["todo_done"]
    assert client.put(f"/api/todos/{tid}", json={"status": "PAUSED"}, headers=hm).status_code == 400
    texts = [a.target for a in db_session.query(models.Activity).filter_by(kind="todo_done")]
    assert texts == ["할 일 「받아쓰기 오류 처리」 완료"]


def test_assign_records_only_when_new_assignee(client, fake_gemini, db_session):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    unassigned = [r for r in client.get(f"/api/teams/{team['id']}/todos", headers=ho).json() if r["assignee_id"] is None][0]
    before = _kinds(db_session)
    r = client.put(f"/api/todos/{unassigned['id']}", json={"assignee_id": member["id"]}, headers=ho)
    assert r.status_code == 200 and r.json()["assignee_name"] == "박과장"
    assert _kinds(db_session) == before + ["todo_assign"]
    assert db_session.query(models.Activity).filter_by(kind="todo_assign").one().target == "할 일 「사용자 인터뷰」를 박과장에게 배정"
    # 미정으로 되돌리면 담당자가 비고 기록은 늘지 않는다
    r = client.put(f"/api/todos/{unassigned['id']}", json={"assignee_id": None}, headers=ho)
    assert r.json()["assignee_id"] is None and r.json()["assignee_name"] is None
    assert _kinds(db_session) == before + ["todo_assign"]
    # 같은 사람으로 다시 보내면 변화가 없어 기록하지 않는다
    client.put(f"/api/todos/{unassigned['id']}", json={"assignee_id": owner["id"]}, headers=ho)
    client.put(f"/api/todos/{unassigned['id']}", json={"assignee_id": owner["id"]}, headers=ho)
    assert _kinds(db_session).count("todo_assign") == 2


def test_assignee_must_be_team_member(client, fake_gemini):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    _, outsider = signup(client, "x@example.com", "외부인")
    tid = client.get("/api/me/todos", headers=hm).json()[0]["id"]
    r = client.put(f"/api/todos/{tid}", json={"assignee_id": outsider["id"]}, headers=hm)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


def test_due_text_is_free_text_not_interpreted(client, fake_gemini):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    tid = client.get("/api/me/todos", headers=hm).json()[0]["id"]
    for text in ("다음 주 금요일", "2026-09-12", "지난 주", "미정", "아무 글자나"):
        r = client.put(f"/api/todos/{tid}", json={"due_text": text}, headers=hm)
        assert r.status_code == 200 and r.json()["due_text"] == text
    assert client.put(f"/api/todos/{tid}", json={"due_text": "  "}, headers=hm).status_code == 400


def test_partial_update_leaves_other_fields(client, fake_gemini):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    row = client.get("/api/me/todos", headers=hm).json()[0]
    r = client.put(f"/api/todos/{row['id']}", json={"status": "DOING"}, headers=hm).json()
    assert r["assignee_id"] == row["assignee_id"] and r["due_text"] == row["due_text"]


# ---- 6.3 삭제 ----
def test_delete_is_owner_only(client, fake_gemini):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    tid = client.get("/api/me/todos", headers=hm).json()[0]["id"]
    r = client.delete(f"/api/todos/{tid}", headers=hm)
    assert r.status_code == 403 and r.json()["code"] == "OWNER_ONLY"
    assert len(client.get(f"/api/teams/{team['id']}/todos", headers=ho).json()) == 3
    assert client.delete(f"/api/todos/{tid}", headers=ho).status_code == 204
    assert len(client.get(f"/api/teams/{team['id']}/todos", headers=ho).json()) == 2


# ---- 7.1 댓글 ----
def _cid(client, h, mid, text="의견입니다"):
    r = client.post(f"/api/meetings/{mid}/comments", json={"content": text}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_comment_create_and_activity(client, fake_gemini, db_session):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    r = client.post(f"/api/meetings/{meeting['id']}/comments", json={"content": "받아쓰기 실패는 세 칸을 비우기로"}, headers=hm)
    assert r.status_code == 201 and r.json()["user_name"] == "박과장"
    act = db_session.query(models.Activity).filter_by(kind="comment_add").one()
    assert act.target == "회의록 「2차 스프린트 계획 회의」에 댓글 작성" and act.actor_id == member["id"]


def test_comment_length_limit_500(client, fake_gemini, db_session):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    url = f"/api/meetings/{meeting['id']}/comments"
    assert client.post(url, json={"content": "가" * 500}, headers=hm).status_code == 201
    r = client.post(url, json={"content": "가" * 501}, headers=hm)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"
    assert client.post(url, json={"content": "   "}, headers=hm).status_code == 400
    assert db_session.query(models.Comment).count() == 1


def test_comments_list_order_and_can_delete(client, fake_gemini):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    url = f"/api/meetings/{meeting['id']}/comments"
    assert client.get(url, headers=hm).json() == []  # 댓글이 없는 것이 기본
    _cid(client, ho, meeting["id"], "첫째")
    _cid(client, hm, meeting["id"], "둘째")
    as_member = client.get(url, headers=hm).json()
    assert [c["content"] for c in as_member] == ["첫째", "둘째"]  # 오래된 순
    assert [c["can_delete"] for c in as_member] == [False, True]  # member 는 자기 것만
    assert set(as_member[0]) == {"id", "user_id", "user_name", "content", "created_at", "can_delete"}
    as_owner = client.get(url, headers=ho).json()
    assert [c["can_delete"] for c in as_owner] == [True, True]  # owner 는 전부


def test_comments_on_other_team_meeting_hidden(client, fake_gemini):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    hb, _ = signup(client, "b@example.com", "다른")
    make_team(client, hb, "다른팀")
    url = f"/api/meetings/{meeting['id']}/comments"
    assert client.get(url, headers=hb).status_code == 404
    assert client.post(url, json={"content": "x"}, headers=hb).status_code == 404


# ---- 7.2 삭제 ----
def test_comment_delete_rules(client, fake_gemini):
    ho, owner, hm, member, team, meeting = _setup(client, fake_gemini)
    h3, _ = signup(client, "c@example.com", "최선임")
    join_team(client, h3, team["invite_code"])
    cid = _cid(client, hm, meeting["id"])
    r = client.delete(f"/api/comments/{cid}", headers=h3)  # owner 도 쓴 사람도 아님
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"
    assert client.delete(f"/api/comments/{cid}", headers=hm).status_code == 204  # 쓴 사람
    cid2 = _cid(client, hm, meeting["id"], "또")
    assert client.delete(f"/api/comments/{cid2}", headers=ho).status_code == 204  # owner
    assert client.delete(f"/api/comments/{cid2}", headers=ho).status_code == 404  # 이미 없음


# ---- 전체 API 표면 ----
def test_api_surface_is_exactly_the_26_mapped_operations(client):
    spec = client.get("/openapi.json").json()["paths"]
    ops = {(m.upper(), p) for p, v in spec.items() for m in v}
    assert len(ops) == 26
    assert all(p.startswith("/api/") for _, p in ops)  # /docs · /openapi.json 은 스키마에 없다
