"""MeetingNote Pro - FastAPI 앱.

등록 순서가 중요하다: API 라우터 → /docs → 정적 화면(frontend/)을 맨 마지막에 "/" 로.
그래야 /docs · /api/* 가 정적 파일에 가려지지 않는다.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, errors
from .routers import activities, auth, comments, meetings, teams, todos

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.create_all()  # 이미 있으면 건너뜀
    yield


app = FastAPI(
    title="MeetingNote Pro API",
    version="0.1.0",
    description="로그인한 팀이 함께 쓰는 회의록. 오른쪽 위 **Authorize** 에 로그인 응답의 `token` 을 넣으면 인증이 필요한 API 도 여기서 호출된다.",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
errors.install(app)

for r in (auth, teams, meetings, todos, comments, activities):
    app.include_router(r.router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/login.html")


app.mount("/", StaticFiles(directory=config.ROOT / "frontend", html=True, check_dir=False), name="frontend")
