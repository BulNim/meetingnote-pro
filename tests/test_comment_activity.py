import pytest
from sqlalchemy import select

from backend import activity, db
from backend.models import Activity
from tests.conftest import Classified, TodoItem, assert_error


def test_comment_flow(client, team, fake):
    owner, park, lee = team["owner"], team["park"], team["lee"]
    m = owner.new_meeting()
    url = f"/api/meetings/{m['id']}/comments"
    assert owner.get(url).json() == []
    c1 = park.post(url, json={"content": "첫 의견"})
    assert c1.status_code == 201
    assert set(c1.json()) == {"id", "user_id", "user_name", "content", "created_at", "can_delete"}
    park.post(url, json={"content": "두 번째"})
    rows = lee.get(url).json()
    assert [r["content"] for r in rows] == ["첫 의견", "두 번째"]
    assert all(r["can_delete"] is False for r in rows)
    assert all(r["can_delete"] is True for r in owner.get(url).json())
    assert_error(lee.delete(f"/api/comments/{rows[0]['id']}"), 403, "FORBIDDEN")
    assert owner.delete(f"/api/comments/{rows[0]['id']}").status_code == 204
    assert park.delete(f"/api/comments/{rows[1]['id']}").status_code == 204
    assert_error(park.delete(f"/api/comments/{rows[1]['id']}"), 404, "NOT_FOUND")


def test_comment_length(client, team, fake):
    owner = team["owner"]
    url = f"/api/meetings/{owner.new_meeting()['id']}/comments"
    assert owner.post(url, json={"content": "가" * 500}).status_code == 201
    assert_error(owner.post(url, json={"content": "가" * 501}), 400, "VALIDATION_ERROR")
    assert_error(owner.post(url, json={"content": "   "}), 400, "VALIDATION_ERROR")
    assert_error(owner.post("/api/meetings/999/comments", json={"content": "x"}), 404, "MEETING_NOT_FOUND")


def test_only_five_kinds(client, team, fake):
    owner, park = team["owner"], team["park"]
    fake.result = Classified(summary="s", decisions=[], todos=[TodoItem(what="일", assignee="박과장")])
    m = owner.new_meeting()  # meeting_add + todo_assign
    tid = m["todos"][0]["id"]
    owner.put(f"/api/todos/{tid}", json={"status": "DOING"})  # 기록 없음
    owner.put(f"/api/todos/{tid}", json={"status": "DONE"})  # todo_done
    park.post(f"/api/meetings/{m['id']}/comments", json={"content": "의견"})  # comment_add
    owner.put("/api/auth/me", json={"name": "김대리2"})  # 기록 없음
    owner.put(f"/api/teams/{owner.team_id}", json={"name": "새이름"})  # 기록 없음
    acts = owner.get(f"/api/teams/{owner.team_id}/activities").json()
    assert sorted(a["kind"] for a in acts) == sorted(
        ["member_join", "member_join", "meeting_add", "todo_assign", "todo_done", "comment_add"])
    a = acts[0]
    assert set(a) == {"id", "kind", "actor_name", "text", "created_at"}
    texts = {x["kind"]: x["text"] for x in acts}
    assert texts["todo_assign"] == "할 일 「일」를 박과장에게 배정"
    assert texts["comment_add"] == f"회의록 「{m['title']}」에 댓글 작성"
    assert [x["kind"] for x in park.get("/api/me/activities").json()] == ["comment_add", "member_join"]
    with pytest.raises(ValueError):
        activity.record(None, 1, 1, "team_create")


def test_activity_limit_50_latest_first(client, team, fake):
    owner = team["owner"]
    m = owner.new_meeting()
    for i in range(55):
        owner.post(f"/api/meetings/{m['id']}/comments", json={"content": f"댓글 {i}"})
    acts = owner.get(f"/api/teams/{owner.team_id}/activities").json()
    assert len(acts) == 50 and acts[0]["id"] > acts[-1]["id"]
    assert len(owner.get("/api/me/activities").json()) == 50
    with next(db.get_db()) as s:
        assert len(s.scalars(select(Activity)).all()) == 2 + 1 + 55


def test_owner_with_no_activity(client):
    from tests.conftest import Api
    a = Api(client, "새팀장")
    a.make_team()
    assert a.get("/api/me/activities").json() == []
