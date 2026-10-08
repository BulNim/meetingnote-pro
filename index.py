"""Vercel 진입점 - 로컬은 `uvicorn app.main:app --app-dir backend` 로 같은 앱을 띄운다"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.main import app  # noqa: E402,F401  (Vercel 이 이 이름 app 을 찾는다)
