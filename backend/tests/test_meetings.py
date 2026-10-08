import io
import wave
from pathlib import Path

import pytest

from app import models
from app.config import MAX_UPLOAD_BYTES
from app.services.gemini import Organized, TodoItem, UNDECIDED, normalize, _OrganizedOut, _TodoOut

from .helpers import join_team, make_team, signup

REAL_WAV = Path(__file__).resolve().parents[2] / "회의_녹음.wav"


def tiny_wav(seconds=1, rate=8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * rate * seconds)
    return buf.getvalue()


# 최소한의 mp3 프레임 머리 (MPEG-1 Layer III, 128kbps, 44.1kHz) - 내용 판정 시험용
MP3_BYTES = b"\xff\xfb\x90\x00" + b"\x00" * 413


def _team(client):
    h, u = signup(client, "owner@example.com", "김대리")
    return h, u, make_team(client, h)


def _meeting_body(**over):
    body = {"title": "2차 스프린트 계획 회의", "met_at": "2026-09-24T05:00:00Z",
            "attendees": "김대리, 박과장", "body": "김대리: 목록과 검색은 제가 다음 주 금요일까지 하겠습니다."}
    body.update(over)
    return body


# ---- 5.1 Gemini 결과 다듬기 ----
def test_normalize_keeps_assignee_only_if_member():
    raw = _OrganizedOut(
        summary=" 요약 ",
        decisions=["확정 1", "  ", "확정 2"],
        todos=[_TodoOut(what="목록 구현", assignee="김대리", due="다음 주 금요일"),
               _TodoOut(what="인터뷰", assignee="없는사람", due=""),
               _TodoOut(what="  ", assignee="김대리")],
    )
    out = normalize(raw, ["김대리", "박과장"])
    assert out.summary == "요약" and out.decisions == ["확정 1", "확정 2"]
    assert [(t.what, t.assignee, t.due) for t in out.todos] == [
        ("목록 구현", "김대리", "다음 주 금요일"),
        ("인터뷰", None, UNDECIDED),  # 멤버가 아니면 지어내지 않고 미정
    ]


# ---- 5.2 업로드 ----
def test_upload_wav_and_mp3_both_ok(client, fake_gemini):
    h, _, _ = _team(client)
    r = client.post("/api/upload", files={"file": ("a.wav", tiny_wav(), "audio/wav")}, headers=h)
    assert r.status_code == 200 and r.json() == {"body": fake_gemini.transcript}
    assert fake_gemini.last_mime == "audio/wav"
    r = client.post("/api/upload", files={"file": ("b.mp3", MP3_BYTES, "audio/mpeg")}, headers=h)
    assert r.status_code == 200 and fake_gemini.last_mime == "audio/mpeg"
    r = client.post("/api/upload", files={"file": ("c.mp3", b"ID3" + b"\x00" * 100, "audio/mpeg")}, headers=h)
    assert r.status_code == 200


def test_upload_does_not_store_anything(client, fake_gemini, db_session):
    h, _, _ = _team(client)
    client.post("/api/upload", files={"file": ("a.wav", tiny_wav(), "audio/wav")}, headers=h)
    assert db_session.query(models.Meeting).count() == 0


def test_upload_judges_by_content_not_extension(client, fake_gemini):
    h, _, _ = _team(client)
    mp4_like = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64
    r = client.post("/api/upload", files={"file": ("fake.mp3", mp4_like, "audio/mpeg")}, headers=h)
    assert r.status_code == 415 and r.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"
    # 반대로 확장자가 txt 여도 내용이 wav 면 통과
    r = client.post("/api/upload", files={"file": ("memo.txt", tiny_wav(), "text/plain")}, headers=h)
    assert r.status_code == 200


def test_upload_over_limit_is_413_and_limit_is_4_4mb(client, fake_gemini):
    assert MAX_UPLOAD_BYTES == 4_400_000
    h, _, _ = _team(client)
    over = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * MAX_UPLOAD_BYTES
    r = client.post("/api/upload", files={"file": ("big.wav", over, "audio/wav")}, headers=h)
    assert r.status_code == 413 and r.json()["code"] == "PAYLOAD_TOO_LARGE"
    exact = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * (MAX_UPLOAD_BYTES - 12)
    r = client.post("/api/upload", files={"file": ("edge.wav", exact, "audio/wav")}, headers=h)
    assert r.status_code == 200


def test_upload_gemini_failure_is_502(client, fake_gemini):
    h, _, _ = _team(client)
    fake_gemini.fail_transcribe = True
    r = client.post("/api/upload", files={"file": ("a.wav", tiny_wav(), "audio/wav")}, headers=h)
    assert r.status_code == 502 and r.json()["code"] == "UPSTREAM_ERROR"


def test_upload_requires_login_and_file(client, fake_gemini):
    assert client.post("/api/upload", files={"file": ("a.wav", tiny_wav(), "audio/wav")}).status_code == 401
    h, _, _ = _team(client)
    assert client.post("/api/upload", headers=h).status_code == 400


@pytest.mark.skipif(not REAL_WAV.exists(), reason="시험 녹취 파일 없음")
def test_real_test_wav_passes_the_size_limit(client, fake_gemini):
    """사용자가 준 시험 파일(약 4.39MB, 99.6초)은 4.4MB 상한과 길이 무제한 규칙을 통과해야 한다"""
    h, _, _ = _team(client)
    data = REAL_WAV.read_bytes()
    assert len(data) <= MAX_UPLOAD_BYTES
    r = client.post("/api/upload", files={"file": (REAL_WAV.name, data, "audio/wav")}, headers=h)
    assert r.status_code == 200 and r.json()["body"]


# ---- 5.3 저장 ----
def test_create_meeting_saves_body_and_organized_items(client, fake_gemini, db_session):
    h, owner, team = _team(client)
    h2, _ = signup(client, "p@example.com", "박과장")
    join_team(client, h2, team["invite_code"])
    fake_gemini.organized = Organized(
        summary="목록 검색 범위를 정했다.",
        decisions=["검색은 제목과 참석자 범위", "업로드는 4.5MB"],
        todos=[TodoItem("목록 구현", "김대리", "다음 주 금요일"), TodoItem("인터뷰", None, UNDECIDED)],
    )
    r = client.post(f"/api/teams/{team['id']}/meetings", json=_meeting_body(), headers=h)
    assert r.status_code == 201
    m = r.json()
    assert m["body"].startswith("김대리: 목록과 검색은") and m["summary"] == "목록 검색 범위를 정했다."
    assert m["decisions"] == "검색은 제목과 참석자 범위\n업로드는 4.5MB"
    assert [(t["what"], t["assignee_name"], t["due_text"], t["status"]) for t in m["todos"]] == [
        ("목록 구현", "김대리", "다음 주 금요일", "OPEN"),
        ("인터뷰", None, "미정", "OPEN"),
    ]
    # 멤버 이름이 Gemini 에 전달됐다
    assert set(fake_gemini.organize_calls[0][1]) == {"김대리", "박과장"}
    acts = db_session.query(models.Activity).filter_by(kind="meeting_add").all()
    assert len(acts) == 1 and acts[0].target == "회의록 「2차 스프린트 계획 회의」 등록"


def test_create_meeting_required_fields(client, fake_gemini):
    h, _, team = _team(client)
    for bad in ({"title": " "}, {"body": ""}, {"met_at": "어제"}):
        r = client.post(f"/api/teams/{team['id']}/meetings", json=_meeting_body(**bad), headers=h)
        assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR", bad
    r = client.post(f"/api/teams/{team['id']}/meetings", json={"met_at": "2026-09-24T05:00:00Z"}, headers=h)
    assert r.status_code == 400


def test_organize_failure_still_saves_with_empty_items(client, fake_gemini, db_session):
    h, _, team = _team(client)
    fake_gemini.fail_organize = True
    r = client.post(f"/api/teams/{team['id']}/meetings", json=_meeting_body(), headers=h)
    assert r.status_code == 201
    m = r.json()
    assert m["body"] and m["summary"] == "" and m["decisions"] == "" and m["todos"] == []
    assert db_session.query(models.Todo).count() == 0


def test_create_meeting_in_other_team_is_404(client, fake_gemini):
    _, _, team_a = _team(client)
    hb, _ = signup(client, "b@example.com", "다른")
    make_team(client, hb, "다른팀")
    r = client.post(f"/api/teams/{team_a['id']}/meetings", json=_meeting_body(), headers=hb)
    assert r.status_code == 404


# ---- 5.4 목록 ----
def _add(client, h, team, **over):
    r = client.post(f"/api/teams/{team['id']}/meetings", json=_meeting_body(**over), headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_list_empty_then_sorted_without_body(client, fake_gemini, db_session):
    h, _, team = _team(client)
    assert client.get(f"/api/teams/{team['id']}/meetings", headers=h).json() == []
    _add(client, h, team, title="오래된", met_at="2026-09-10T00:00:00Z")
    _add(client, h, team, title="최근", met_at="2026-09-24T00:00:00Z")
    fake_gemini.organized = Organized(summary="s", decisions=["a", "b", "c"],
                                     todos=[TodoItem("x"), TodoItem("y")])
    _add(client, h, team, title="가운데", met_at="2026-09-18T00:00:00Z")
    rows = client.get(f"/api/teams/{team['id']}/meetings", headers=h).json()
    assert [r["title"] for r in rows] == ["최근", "가운데", "오래된"]
    mid = rows[1]
    assert "body" not in mid and "decisions" not in mid
    assert mid["decision_count"] == 3 and mid["todo_total_count"] == 2 and mid["todo_done_count"] == 0
    # 할 일 하나를 완료로 바꾸면 done 수가 센다
    todo = db_session.query(models.Todo).first()
    todo.status = "DONE"
    db_session.commit()
    rows = client.get(f"/api/teams/{team['id']}/meetings", headers=h).json()
    assert [r["todo_done_count"] for r in rows if r["title"] == "가운데"] == [1]


def test_search_matches_title_and_attendees_not_body(client, fake_gemini):
    h, _, team = _team(client)
    _add(client, h, team, title="배포 환경 점검", attendees="박과장, 최선임", body="비밀단어 포함 본문")
    _add(client, h, team, title="기획 킥오프", attendees="김대리", body="다른 내용")
    url = f"/api/teams/{team['id']}/meetings"
    assert [r["title"] for r in client.get(url, params={"q": "배포"}, headers=h).json()] == ["배포 환경 점검"]
    assert [r["title"] for r in client.get(url, params={"q": "최선임"}, headers=h).json()] == ["배포 환경 점검"]
    assert client.get(url, params={"q": "비밀단어"}, headers=h).json() == []  # 본문은 검색 대상 아님
    assert client.get(url, params={"q": "없는말"}, headers=h).status_code == 200


def test_search_escapes_wildcards(client, fake_gemini):
    h, _, team = _team(client)
    _add(client, h, team, title="일반 회의")
    assert client.get(f"/api/teams/{team['id']}/meetings", params={"q": "%"}, headers=h).json() == []


def test_period_filter_includes_both_ends(client, fake_gemini):
    h, _, team = _team(client)
    for title, at in (("A", "2026-09-10T00:00:00Z"), ("B", "2026-09-18T23:59:00Z"), ("C", "2026-09-24T09:00:00Z")):
        _add(client, h, team, title=title, met_at=at)
    url = f"/api/teams/{team['id']}/meetings"
    got = client.get(url, params={"from": "2026-09-18", "to": "2026-09-24"}, headers=h).json()
    assert sorted(r["title"] for r in got) == ["B", "C"]
    assert [r["title"] for r in client.get(url, params={"to": "2026-09-10"}, headers=h).json()] == ["A"]
    assert client.get(url, params={"from": "어제"}, headers=h).status_code == 400


# ---- 5.5 상세 · 수정 · 삭제 ----
def test_get_update_delete_flow(client, fake_gemini, db_session):
    h, _, team = _team(client)
    h2, _ = signup(client, "p@example.com", "박과장")
    join_team(client, h2, team["invite_code"])
    fake_gemini.organized = Organized(summary="요약", decisions=["결정"], todos=[TodoItem("일", "김대리", "내일")])
    mid = _add(client, h, team)["id"]

    got = client.get(f"/api/meetings/{mid}", headers=h2).json()
    assert got["body"] and got["can_edit"] is False  # 올린 사람이 아닌 member
    assert client.get(f"/api/meetings/{mid}", headers=h).json()["can_edit"] is True

    r = client.put(f"/api/meetings/{mid}", json={"title": "새 제목", "body": "고친 본문"}, headers=h)
    assert r.status_code == 200
    after = r.json()
    assert after["title"] == "새 제목" and after["body"] == "고친 본문"
    assert after["summary"] == "요약" and after["decisions"] == "결정" and len(after["todos"]) == 1  # 세 항목은 그대로
    assert len(fake_gemini.organize_calls) == 1  # 본문을 고쳐도 다시 돌리지 않음

    r = client.put(f"/api/meetings/{mid}", json={"title": "해킹"}, headers=h2)
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"
    assert client.delete(f"/api/meetings/{mid}", headers=h2).status_code == 403

    db_session.add(models.Comment(meeting_id=mid, user_id=1, content="댓글"))
    db_session.commit()
    assert client.delete(f"/api/meetings/{mid}", headers=h).status_code == 204
    assert db_session.query(models.Todo).count() == 0 and db_session.query(models.Comment).count() == 0
    r = client.get(f"/api/meetings/{mid}", headers=h)
    assert r.status_code == 404 and r.json()["code"] == "MEETING_NOT_FOUND"


def test_owner_can_edit_and_delete_others_meeting(client, fake_gemini):
    h, _, team = _team(client)  # owner
    h2, _ = signup(client, "p@example.com", "박과장")
    join_team(client, h2, team["invite_code"])
    mid = _add(client, h2, team)["id"]  # member 가 올림
    assert client.put(f"/api/meetings/{mid}", json={"title": "owner 수정"}, headers=h).status_code == 200
    assert client.delete(f"/api/meetings/{mid}", headers=h).status_code == 204


def test_meeting_of_other_team_is_not_found(client, fake_gemini):
    h, _, team = _team(client)
    mid = _add(client, h, team)["id"]
    hb, _ = signup(client, "b@example.com", "다른")
    make_team(client, hb, "다른팀")
    for r in (client.get(f"/api/meetings/{mid}", headers=hb),
              client.put(f"/api/meetings/{mid}", json={"title": "x"}, headers=hb),
              client.delete(f"/api/meetings/{mid}", headers=hb)):
        assert r.status_code == 404 and r.json()["code"] == "MEETING_NOT_FOUND"
    assert client.get("/api/meetings/9999", headers=h).json()["code"] == "MEETING_NOT_FOUND"
