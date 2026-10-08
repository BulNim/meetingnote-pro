from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

import os

from .config import ROOT, get_settings
from . import models  # noqa: F401  (테이블 정의가 등록돼야 create_all 이 만든다)
from .db import Base, engine
from .errors import install_error_handlers

API_DESCRIPTION = (
    "MeetingNote Pro API. 로그인으로 받은 JWT 를 오른쪽 위 Authorize 에 붙여 넣으면 "
    "나머지 API 를 이 화면에서 바로 시험할 수 있다."
)


def create_app() -> FastAPI:
    app = FastAPI(title="MeetingNote Pro", version="0.1.0", description=API_DESCRIPTION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    if not os.getenv("MEETINGNOTE_SKIP_INIT"):  # 테스트는 자기 DB 를 따로 만든다
        Base.metadata.create_all(engine)

    # 라우터는 정적 파일보다 먼저 등록한다 (/docs · /openapi.json 이 가려지지 않게)
    from .routers import ROUTERS

    for router in ROUTERS:
        app.include_router(router)

    @app.get("/", include_in_schema=False)
    def root():  # 주소만 열었을 때 로그인 화면으로 (API 26개 계산에는 들어가지 않는다)
        return RedirectResponse("/login.html")

    frontend = ROOT / "frontend"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
