from datetime import timedelta

import pytest

from app import models
from app.services import activity

from .helpers import join_team, make_team, signup


def test_record_rejects_unknown_kind(db_session):
    with pytest.raises(AssertionError):
        activity.record(db_session, 1, 1, "team_create", "x")


def test_sentences():
    assert activity.meeting_added("2차 스프린트 계획 회의") == "회의록 「2차 스프린트 계획 회의」 등록"
    assert activity.todo_assigned("인터뷰", "최선임") == "할 일 「인터뷰」를 최선임에게 배정"
    assert activity.todo_done("배포 키") == "할 일 「배포 키」 완료"
    assert activity.comment_added("배포 환경 점검") == "회의록 「배포 환경 점검」에 댓글 작성"
    assert activity.member_joined() == "초대코드로 합류"


def test_join_records_member_join_but_rename_and_account_change_do_not(client, db_session):
    h, _ = signup(client, "o@example.com", "김대리")
    team = make_team(client, h)
    h2, _ = signup(client, "p@example.com", "박과장", password="mypassword")
    join_team(client, h2, team["invite_code"])
    client.put(f"/api/teams/{team['id']}", json={"name": "개발팀"}, headers=h)
    client.put("/api/auth/me", json={"name": "박수석"}, headers=h2)
    kinds = [a.kind for a in db_session.query(models.Activity).all()]
    assert kinds == ["member_join"]


def _seed(db, team_id, actor_id, n):
    base = models.utcnow()
    for i in range(n):
        db.add(models.Activity(team_id=team_id, actor_id=actor_id, kind="meeting_add",
                               target=f"회의록 「{i}」 등록", created_at=base + timedelta(seconds=i)))
    db.commit()


def test_team_activities_latest_50_in_descending_order(client, db_session):
    h, u = signup(client, "o@example.com", "김대리")
    team = make_team(client, h)
    _seed(db_session, team["id"], u["id"], 60)
    rows = client.get(f"/api/teams/{team['id']}/activities", headers=h).json()
    assert len(rows) == 50
    assert rows[0]["text"] == "회의록 「59」 등록" and rows[-1]["text"] == "회의록 「10」 등록"
    assert set(rows[0]) == {"id", "kind", "actor_name", "text", "created_at"}
    assert rows[0]["actor_name"] == "김대리" and rows[0]["created_at"].endswith("Z")


def test_my_activities_only_mine_and_empty(client, db_session):
    h, u = signup(client, "o@example.com", "김대리")
    team = make_team(client, h)
    h2, u2 = signup(client, "p@example.com", "박과장")
    join_team(client, h2, team["invite_code"])  # 박과장의 member_join 한 건
    _seed(db_session, team["id"], u["id"], 2)
    mine = client.get("/api/me/activities", headers=h).json()
    assert len(mine) == 2 and all(r["actor_name"] == "김대리" for r in mine)
    other = client.get("/api/me/activities", headers=h2).json()
    assert [r["kind"] for r in other] == ["member_join"]
    h3, _ = signup(client, "n@example.com", "신입")
    assert client.get("/api/me/activities", headers=h3).json() == []


def test_team_activities_hidden_from_other_team(client):
    h, _ = signup(client, "o@example.com", "김대리")
    team = make_team(client, h)
    hb, _ = signup(client, "b@example.com", "다른")
    make_team(client, hb, "다른팀")
    assert client.get(f"/api/teams/{team['id']}/activities", headers=hb).status_code == 404
