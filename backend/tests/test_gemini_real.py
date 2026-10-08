"""실제 Gemini 를 부르는 시험 (표시: gemini). GEMINI_API_KEY 가 없으면 건너뛴다.

시험 파일은 D:\\meetingnote-pro\\회의_녹음.wav (약 4.39MB, 99.6초). mp3 는 이 wav 를 ffmpeg 로 바꿔 쓴다.
응답 내용을 글자 단위로 비교하지 않는다. 구조와 형식만 확인한다.
"""
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from app.config import get_settings
from app.services.gemini import GeminiService

from .helpers import join_team, make_team, signup

REAL_WAV = Path(__file__).resolve().parents[2] / "회의_녹음.wav"

pytestmark = [
    pytest.mark.gemini,
    pytest.mark.skipif(not get_settings().gemini_api_key, reason="GEMINI_API_KEY 없음"),
    pytest.mark.skipif(not REAL_WAV.exists(), reason="시험 녹취 파일 없음"),
]

HANGUL = re.compile(r"[가-힣]")


@pytest.fixture(scope="module")
def transcript():
    """받아쓰기는 한 번만 호출해 여러 시험이 같이 쓴다"""
    return GeminiService().transcribe(REAL_WAV.read_bytes(), "audio/wav")


def test_transcribe_real_wav(transcript):
    assert len(transcript) > 100
    assert len(HANGUL.findall(transcript)) > 50  # 한국어로 받아썼다


def test_organize_real_body_has_the_three_items(transcript):
    members = ["김대리", "박과장", "이주임"]
    out = GeminiService().organize(transcript, members, datetime(2026, 9, 24, 5, 0))
    assert out.summary.strip()
    assert isinstance(out.decisions, list) and all(isinstance(d, str) and d for d in out.decisions)
    for todo in out.todos:
        assert todo.what.strip()
        assert todo.assignee is None or todo.assignee in members  # 멤버가 아니면 지어내지 않고 미정
        assert todo.due.strip()  # 기한이 없으면 「미정」


def test_upload_then_save_through_the_api_with_real_gemini(client, transcript):
    h, _ = signup(client, "owner@example.com", "김대리")
    team = make_team(client, h)
    r = client.post("/api/upload", files={"file": (REAL_WAV.name, REAL_WAV.read_bytes(), "audio/wav")}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()["body"]
    assert len(HANGUL.findall(body)) > 50

    r = client.post(f"/api/teams/{team['id']}/meetings", headers=h, json={
        "title": "시험 회의", "met_at": "2026-09-24T05:00:00Z", "attendees": "김대리", "body": body})
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["body"] == body and m["summary"].strip()
    assert all(t["status"] == "OPEN" and t["due_text"] for t in m["todos"])


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg 가 없어 mp3 를 만들 수 없음")
def test_mp3_upload_with_real_gemini(client, tmp_path):
    mp3 = tmp_path / "회의_녹음.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(REAL_WAV), "-b:a", "64k", str(mp3)], check=True)
    data = mp3.read_bytes()
    assert len(data) < 4_400_000
    h, _ = signup(client, "owner@example.com", "김대리")
    make_team(client, h)
    r = client.post("/api/upload", files={"file": (mp3.name, data, "audio/mpeg")}, headers=h)
    assert r.status_code == 200, r.text
    assert len(HANGUL.findall(r.json()["body"])) > 50
