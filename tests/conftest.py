"""시험 공통 - 시험마다 임시 SQLite, 가짜 Gemini, 사용자 · 팀 도우미."""
import itertools

import pytest
from fastapi.testclient import TestClient

from backend import db, gemini
from backend.gemini import Classified, TodoItem

_seq = itertools.count(1)

# 가짜로 바꾸기 전 진짜 함수 (키 없음 시험용)
REAL_TRANSCRIBE = gemini.transcribe

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 64
MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 64
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


class FakeGemini:
    """transcribe · classify 를 대신한다. fail_* 를 켜면 GeminiError."""

    def __init__(self):
        self.body = "김대리: 검색은 제목과 참석자로 하기로 했습니다."
        self.result = Classified(summary="검색 범위를 정함", decisions=["검색은 제목과 참석자"], todos=[])
        self.fail_transcribe = False
        self.fail_classify = False
        self.calls = []

    def transcribe(self, data, mime):
        self.calls.append(("transcribe", mime))
        if self.fail_transcribe:
            raise gemini.GeminiError("GEMINI_API_KEY 없음")
        return self.body

    def classify(self, body, members):
        self.calls.append(("classify", tuple(members)))
        if self.fail_classify:
            raise gemini.GeminiError("세 항목 구분 응답을 읽지 못함")
        return self.result


@pytest.fixture
def fake(monkeypatch):
    f = FakeGemini()
    monkeypatch.setattr(gemini, "transcribe", f.transcribe)
    monkeypatch.setattr(gemini, "classify", f.classify)
    return f


@pytest.fixture
def client(tmp_path, fake, monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    db.init_engine(f"sqlite:///{(tmp_path / 't.db').as_posix()}")
    db.create_all()
    from backend.main import app

    with TestClient(app) as c:
        yield c


class Api:
    """사람 하나 - 가입하고 토큰을 들고 다닌다."""

    def __init__(self, client, name):
        self.c = client
        self.name = name
        self.email = f"user{next(_seq)}@example.com"
        r = client.post("/api/auth/signup", json={"email": self.email, "password": "password1", "name": name})
        assert r.status_code == 201, r.text
        self.token = r.json()["token"]
        self.id = r.json()["user"]["id"]
        self.team_id = None

    @property
    def h(self):
        return {"Authorization": f"Bearer {self.token}"}

    def get(self, url, **kw):
        return self.c.get(url, headers=self.h, **kw)

    def post(self, url, **kw):
        return self.c.post(url, headers=self.h, **kw)

    def put(self, url, **kw):
        return self.c.put(url, headers=self.h, **kw)

    def delete(self, url, **kw):
        return self.c.delete(url, headers=self.h, **kw)

    def make_team(self, name="기획팀"):
        r = self.post("/api/teams", json={"name": name})
        assert r.status_code == 201, r.text
        self.team_id = r.json()["id"]
        return r.json()

    def join(self, code):
        r = self.post("/api/teams/join", json={"code": code})
        if r.status_code == 200:
            self.team_id = r.json()["id"]
        return r

    def new_meeting(self, title="2차 스프린트 계획 회의", met_at="2026-09-24T05:00:00Z", attendees="김대리, 박과장", body="본문"):
        r = self.post(f"/api/teams/{self.team_id}/meetings",
                      json={"title": title, "met_at": met_at, "attendees": attendees, "body": body})
        assert r.status_code == 201, r.text
        return r.json()


@pytest.fixture
def team(client):
    """owner 김대리 + member 박과장 · 이주임."""
    owner = Api(client, "김대리")
    code = owner.make_team()["invite_code"]
    park, lee = Api(client, "박과장"), Api(client, "이주임")
    assert park.join(code).status_code == 200
    assert lee.join(code).status_code == 200
    return {"owner": owner, "park": park, "lee": lee, "code": code}


def assert_error(r, status, code):
    assert r.status_code == status, r.text
    j = r.json()
    assert j["code"] == code and isinstance(j["msg"], str), j


__all__ = ["Api", "assert_error", "WAV", "MP3", "MP4", "TodoItem", "Classified"]
