"""MeetingNote Pro - FastAPI 진입점. 로컬: cd backend && uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, errors
from .db import init_db, using_postgres
from .routers import activity, auth, comment, meeting, team, todo

TAGS = [
    {"name": "auth", "description": "회원가입 · 로그인 · 내 정보. 로그인 응답의 access_token 을 Authorize 에 붙여넣는다"},
    {"name": "team", "description": "팀 생성 · 초대코드 · 합류 · 멤버"},
    {"name": "meeting", "description": "녹취 업로드(받아쓰기) · 회의록 CRUD · 검색"},
    {"name": "todo", "description": "할 일 칸반 · 담당자 배정"},
    {"name": "comment", "description": "회의록 댓글"},
    {"name": "activity", "description": "팀 활동 · 내 활동"},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not using_postgres():   # 로컬 SQLite 는 자동으로 만들고, Postgres(Neon)는 backend/migrate.py 로 만든다
        init_db()
    yield


app = FastAPI(
    title="MeetingNote Pro",
    version="1.0.0",
    openapi_tags=TAGS,
    lifespan=lifespan,
    docs_url="/docs" if config.docs_enabled() else None,
    redoc_url=None,
    openapi_url="/openapi.json" if config.docs_enabled() else None,
)
errors.install(app)

# 같은 서버가 화면과 API 를 함께 내므로 같은 출처만 허용한다. 외부 출처는 여기에 명시한다
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
for module in (auth, team, meeting, todo, comment, activity):
    api.include_router(module.router)
app.include_router(api)

# 화면 6종 - /login.html 처럼 확장자를 붙여 제공 (정의서 7-2 정적 파일 경로)
if config.FRONTEND.exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND, html=True), name="frontend")
