"""6. comment · activity 스펙 시나리오"""
import pytest

from app.deps import log_activity
from conftest import signup


@pytest.fixture()
def meeting_id(client, owner, team):
    r = client.post(
        f"/api/teams/{team['id']}/meetings",
        json={"title": "계획 회의", "met_at": "2026-09-24T05:00:00Z", "body": "본문"},
        headers=owner,
    )
    return r.json()["id"]


def comment(client, mid, headers, content="의견입니다"):
    return client.post(f"/api/meetings/{mid}/comments", json={"content": content}, headers=headers)


def test_댓글_등록은_201이고_comment_add가_남는다(client, owner, team, meeting_id):
    r = comment(client, meeting_id, owner, "a" * 500)
    assert r.status_code == 201 and r.json()["can_delete"] is True
    kinds = [a["kind"] for a in client.get(f"/api/teams/{team['id']}/activities", headers=owner).json()]
    assert "comment_add" in kinds


def test_501자와_빈_댓글은_거절(client, owner, meeting_id):
    for content in ("a" * 501, "   "):
        r = comment(client, meeting_id, owner, content)
        assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"
    assert client.get(f"/api/meetings/{meeting_id}/comments", headers=owner).json() == []


def test_댓글_목록은_오래된_순이고_can_delete는_서버가_판정(client, owner, member, meeting_id):
    comment(client, meeting_id, owner, "첫째")
    comment(client, meeting_id, member, "둘째")
    rows = client.get(f"/api/meetings/{meeting_id}/comments", headers=member).json()
    assert [r["content"] for r in rows] == ["첫째", "둘째"]
    assert [r["can_delete"] for r in rows] == [False, True]
    assert set(rows[0]) == {"id", "user_id", "user_name", "content", "created_at", "can_delete"}


def test_남의_댓글_삭제는_FORBIDDEN_owner는_가능(client, owner, member, meeting_id):
    mine = comment(client, meeting_id, member, "박과장 의견").json()
    third = signup(client, "t@example.com", "셋째")
    team_code = client.get("/api/teams", headers=owner).json()[0]["invite_code"]
    client.post("/api/teams/join", json={"invite_code": team_code}, headers=third)
    denied = client.delete(f"/api/comments/{mine['id']}", headers=third)
    assert denied.status_code == 403 and denied.json()["code"] == "FORBIDDEN"
    assert client.delete(f"/api/comments/{mine['id']}", headers=owner).status_code == 204
    assert client.get(f"/api/meetings/{meeting_id}/comments", headers=owner).json() == []


def test_작성자는_자기_댓글을_지운다(client, member, meeting_id):
    mine = comment(client, meeting_id, member).json()
    assert client.delete(f"/api/comments/{mine['id']}", headers=member).status_code == 204


def test_활동은_최신순_50건까지(client, owner, team):
    from app import db as dbmod
    from app.main import app

    session = next(app.dependency_overrides[dbmod.get_db]())
    me_id = client.get("/api/auth/me", headers=owner).json()["id"]
    for i in range(60):
        log_activity(session, team["id"], me_id, "meeting_add", f"회의 {i}")
    session.commit()
    rows = client.get(f"/api/teams/{team['id']}/activities", headers=owner).json()
    assert len(rows) == 50 and rows[0]["text"].endswith("'회의 59'을(를) 추가했습니다")
    assert set(rows[0]) == {"id", "kind", "actor_name", "text", "created_at"}


def test_활동_kind는_5종뿐(client, owner, team):
    from app import db as dbmod
    from app.main import app

    session = next(app.dependency_overrides[dbmod.get_db]())
    with pytest.raises(AssertionError):
        log_activity(session, team["id"], 1, "invented_kind")


def test_내_활동은_본인_것만_없으면_빈_배열(client, owner, team, member):
    assert client.get("/api/me/activities", headers=owner).json() == []
    rows = client.get("/api/me/activities", headers=member).json()
    assert [r["kind"] for r in rows] == ["member_join"] and "박과장" in rows[0]["text"]
