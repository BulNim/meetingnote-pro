"""오류 형식 {code, msg} 고정 - 정의서 7-2 오류 코드"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status: int, code: str, msg: str = ""):
        self.status, self.code, self.msg = status, code, msg or code


def _body(code: str, msg: str) -> dict:
    return {"code": code, "msg": msg}


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, e: AppError):
        return JSONResponse(_body(e.code, e.msg), status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        return JSONResponse(_body("VALIDATION_ERROR", "입력값이 올바르지 않습니다"), status_code=400)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        if e.status_code in (404, 405):
            return JSONResponse(_body("NOT_FOUND", "찾을 수 없습니다"), status_code=404)
        return JSONResponse(_body("VALIDATION_ERROR", str(e.detail)), status_code=e.status_code)
