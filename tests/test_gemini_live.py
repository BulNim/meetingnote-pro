"""실제 Gemini 전사 시험 - GEMINI_API_KEY 가 있을 때만 돈다. 없으면 skip.

회의_녹음.wav 를 업로드해 본문을 받고, 그 본문으로 회의록을 저장해 요약이 채워지는지 본다.
"""
import pytest
from fastapi.testclient import TestClient

from backend import config, db

WAV_PATH = config.ROOT / "회의_녹음.wav"

pytestmark = [
    pytest.mark.skipif(not config.gemini_key(), reason="GEMINI_API_KEY 없음 - 실제 전사 시험 건너뜀"),
    pytest.mark.skipif(not WAV_PATH.exists(), reason="회의_녹음.wav 없음"),
]


def test_live_transcribe_and_classify(tmp_path, monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    db.init_engine(f"sqlite:///{(tmp_path / 'live.db').as_posix()}")
    db.create_all()
    from backend.main import app

    with TestClient(app) as c:
        r = c.post("/api/auth/signup", json={"email": "live@example.com", "password": "password1", "name": "김대리"})
        h = {"Authorization": f"Bearer {r.json()['token']}"}
        team_id = c.post("/api/teams", json={"name": "기획팀"}, headers=h).json()["id"]

        up = c.post("/api/upload", files={"file": ("회의_녹음.wav", WAV_PATH.read_bytes(), "audio/wav")}, headers=h)
        assert up.status_code == 200, up.text
        body = up.json()["body"]
        assert len(body.strip()) > 20
        print("\n[받아쓰기 앞부분]", body[:200].replace("\n", " "))

        m = c.post(f"/api/teams/{team_id}/meetings", headers=h, json={
            "title": "전사 시험 회의", "met_at": "2026-11-13T05:00:00Z", "attendees": "", "body": body})
        assert m.status_code == 201, m.text
        d = m.json()
        assert d["summary"].strip()
        print("[요약]", d["summary"].replace("\n", " / "))
        print("[결정사항]", d["decisions"].replace("\n", " / ") or "(없음)")
        print("[할 일]", [(t["what"], t["assignee_name"], t["due_text"]) for t in d["todos"]] or "(없음)")
