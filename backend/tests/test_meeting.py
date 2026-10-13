"""4. meeting 스펙 시나리오 - Gemini 는 고정 응답으로 바꿔 끼운다"""
from pathlib import Path

import pytest

from app import transcriber

SAMPLE = Path(__file__).resolve().parents[2] / "회의_녹음.wav"
FAKE = {
    "body": "자. 시작하겠습니다.",
    "summary": "스프린트 계획",
    "decisions": ["검색은 제목과 참석자만"],
    "todos": [{"what": "업로드 화면 연결", "due_text": "금요일"}],
}


@pytest.fixture(autouse=True)
def fake_gemini(monkeypatch):
    calls = []

    def fake(data, mime):
        calls.append((len(data), mime))
        return FAKE

    monkeypatch.setattr(transcriber, "process", fake)
    return calls


def meeting(title="2차 스프린트 계획 회의", met_at="2026-09-24T05:00:00Z", **extra):
    return {"title": title, "met_at": met_at, "attendees": "김대리, 박과장", "body": "본문", **extra}


def post(client, team, headers, **kw):
    return client.post(f"/api/teams/{team['id']}/meetings", json=meeting(**kw), headers=headers)


def test_업로드_성공은_3항목을_돌려준다(client, owner, fake_gemini):
    r = client.post("/api/upload", files={"file": ("a.wav", b"RIFF" + b"0" * 100, "audio/wav")}, headers=owner)
    assert r.status_code == 200
    assert set(r.json()) == {"body", "summary", "decisions", "todos"} and fake_gemini == [(104, "audio/wav")]


@pytest.mark.skipif(not SAMPLE.exists(), reason="회의_녹음.wav 가 없는 환경")
def test_실제_녹음_파일은_업로드_제한을_통과한다(client, owner, fake_gemini):
    data = SAMPLE.read_bytes()
    r = client.post("/api/upload", files={"file": (SAMPLE.name, data, "audio/wav")}, headers=owner)
    assert r.status_code == 200 and fake_gemini[0] == (len(data), "audio/wav")


def test_25MB_초과는_413(client, owner, fake_gemini):
    big = b"0" * (25 * 1024 * 1024 + 1)
    r = client.post("/api/upload", files={"file": ("big.wav", big, "audio/wav")}, headers=owner)
    assert r.status_code == 413 and r.json()["code"] == "PAYLOAD_TOO_LARGE" and not fake_gemini


def test_m4a는_415(client, owner, fake_gemini):
    r = client.post("/api/upload", files={"file": ("a.m4a", b"x", "audio/mp4")}, headers=owner)
    assert r.status_code == 415 and r.json()["code"] == "UNSUPPORTED_MEDIA_TYPE" and not fake_gemini


def test_저장은_201이고_할일과_meeting_add가_생긴다(client, owner, team):
    r = post(client, team, owner, decisions=["a", "b"], todos=[{"what": "하나"}, "둘"])
    assert r.status_code == 201
    assert [t["status"] for t in r.json()["todos"]] == ["OPEN", "OPEN"]
    acts = client.get(f"/api/teams/{team['id']}/activities", headers=owner).json()
    assert acts[0]["kind"] == "meeting_add"


def test_필수값_누락은_VALIDATION_ERROR(client, owner, team):
    r = client.post(f"/api/teams/{team['id']}/meetings", json={"met_at": "2026-09-24T05:00:00Z", "body": "x"}, headers=owner)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"
    assert post(client, team, owner, title="  ").status_code == 400


def test_목록은_met_at_내림차순이고_body가_없다(client, owner, team):
    post(client, team, owner, title="첫", met_at="2026-09-01T00:00:00Z")
    post(client, team, owner, title="셋", met_at="2026-09-03T00:00:00Z")
    post(client, team, owner, title="둘", met_at="2026-09-02T00:00:00Z")
    rows = client.get(f"/api/teams/{team['id']}/meetings", headers=owner).json()
    assert [r["title"] for r in rows] == ["셋", "둘", "첫"]
    assert all("body" not in r for r in rows)
    assert set(rows[0]) == {
        "id", "title", "met_at", "attendees", "summary", "created_at",
        "todo_done_count", "todo_total_count", "decision_count",
    }


def test_빈_목록은_200_빈_배열(client, owner, team):
    r = client.get(f"/api/teams/{team['id']}/meetings", headers=owner)
    assert r.status_code == 200 and r.json() == []


def test_제목_검색과_참석자_검색(client, owner, team):
    post(client, team, owner, title="2차 스프린트 계획")
    post(client, team, owner, title="회고", attendees="이주임")
    url = f"/api/teams/{team['id']}/meetings"
    assert [r["title"] for r in client.get(url, params={"q": "스프린트"}, headers=owner).json()] == ["2차 스프린트 계획"]
    assert [r["title"] for r in client.get(url, params={"q": "이주임"}, headers=owner).json()] == ["회고"]


def test_본문에만_있는_단어는_0건(client, owner, team):
    post(client, team, owner, body="비밀단어는 본문에만")
    r = client.get(f"/api/teams/{team['id']}/meetings", params={"q": "비밀단어"}, headers=owner)
    assert r.status_code == 200 and r.json() == []


def test_기간_필터(client, owner, team):
    post(client, team, owner, title="8월", met_at="2026-08-31T12:00:00Z")
    post(client, team, owner, title="9월말", met_at="2026-09-30T23:00:00Z")
    post(client, team, owner, title="10월", met_at="2026-10-01T00:00:00Z")
    r = client.get(f"/api/teams/{team['id']}/meetings", params={"from": "2026-09-01", "to": "2026-09-30"}, headers=owner)
    assert [m["title"] for m in r.json()] == ["9월말"]
    bad = client.get(f"/api/teams/{team['id']}/meetings", params={"from": "어제"}, headers=owner)
    assert bad.status_code == 400


def test_상세는_본문과_3항목과_decision_count(client, owner, team):
    made = post(client, team, owner, decisions="a\n\nb\n", summary="요약").json()
    r = client.get(f"/api/meetings/{made['id']}", headers=owner)
    assert r.status_code == 200
    d = r.json()
    assert d["body"] == "본문" and d["summary"] == "요약" and d["decision_count"] == 2 and d["met_at"].endswith("Z")


def test_없는_회의록은_MEETING_NOT_FOUND(client, owner, team):
    r = client.get("/api/meetings/9999", headers=owner)
    assert r.status_code == 404 and r.json()["code"] == "MEETING_NOT_FOUND"


def test_작성자는_수정_삭제하고_하위_데이터도_사라진다(client, owner, team):
    made = post(client, team, owner, todos=["할 일"]).json()
    client.post(f"/api/meetings/{made['id']}/comments", json={"content": "댓글"}, headers=owner)
    assert client.put(f"/api/meetings/{made['id']}", json={"title": "바뀜"}, headers=owner).json()["title"] == "바뀜"
    assert client.delete(f"/api/meetings/{made['id']}", headers=owner).status_code == 204
    assert client.get(f"/api/meetings/{made['id']}", headers=owner).status_code == 404
    assert client.get("/api/me/todos", headers=owner).json() == []
    assert client.get(f"/api/teams/{team['id']}/todos", headers=owner).json() == []


def test_남의_회의록_수정_삭제는_FORBIDDEN(client, owner, team, member):
    made = client.post(f"/api/teams/{team['id']}/meetings", json=meeting(), headers=member).json()
    third = None
    from conftest import signup
    third = signup(client, "third@example.com", "셋째")
    client.post("/api/teams/join", json={"invite_code": team["invite_code"]}, headers=third)
    assert client.delete(f"/api/meetings/{made['id']}", headers=third).status_code == 403
    assert client.put(f"/api/meetings/{made['id']}", json={"title": "x"}, headers=third).json()["code"] == "FORBIDDEN"
    assert client.get(f"/api/meetings/{made['id']}", headers=third).status_code == 200


def test_owner는_남의_회의록도_삭제한다(client, owner, team, member):
    made = client.post(f"/api/teams/{team['id']}/meetings", json=meeting(), headers=member).json()
    assert client.delete(f"/api/meetings/{made['id']}", headers=owner).status_code == 204


def test_시각은_UTC_ISO8601(client, owner, team):
    made = post(client, team, owner, met_at="2026-09-24T14:00:00+09:00").json()
    assert made["met_at"] == "2026-09-24T05:00:00Z" and made["created_at"].endswith("Z")
