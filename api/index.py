"""Vercel 진입점 - backend/app 의 FastAPI 앱을 그대로 노출한다 (로컬은 backend 에서 uvicorn app.main:app)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app  # noqa: E402,F401
