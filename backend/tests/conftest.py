import os

os.environ["MEETINGNOTE_SKIP_INIT"] = "1"  # app import 시 운영 DB 파일을 만들지 않게

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db, make_engine
from app.main import app


@pytest.fixture()
def db_session(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def _get_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class FakeGemini:
    """실제 호출 없이 쓰는 가짜. 결과와 실패를 테스트가 정한다"""

    def __init__(self):
        self.transcript = "김대리: 목록 화면 검색 범위를 제목과 참석자로 하겠습니다."
        self.organized = None  # services.gemini.Organized
        self.fail_transcribe = False
        self.fail_organize = False
        self.organize_calls = []

    def transcribe(self, audio, mime_type):
        from app.services.gemini import GeminiError

        if self.fail_transcribe:
            raise GeminiError("가짜 실패")
        self.last_mime = mime_type
        return self.transcript

    def organize(self, body, member_names, met_at):
        from app.services.gemini import GeminiError, Organized

        self.organize_calls.append((body, member_names))
        if self.fail_organize:
            raise GeminiError("가짜 실패")
        return self.organized or Organized()


@pytest.fixture()
def fake_gemini(client):
    from app.services.gemini import get_gemini

    fake = FakeGemini()
    app.dependency_overrides[get_gemini] = lambda: fake
    yield fake
