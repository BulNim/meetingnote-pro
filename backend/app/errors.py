"""오류 본문은 항상 {code, msg}. 코드는 아래 16개로 닫혀 있다"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ERROR_CODES = frozenset({
    "EMAIL_INVALID", "PASSWORD_TOO_WEAK", "TOKEN_EXPIRED", "UNAUTHORIZED",
    "INVITE_NOT_FOUND", "MEETING_NOT_FOUND", "EMAIL_DUPLICATED", "TEAM_FULL",
    "PAYLOAD_TOO_LARGE", "UNSUPPORTED_MEDIA_TYPE", "INVALID_CREDENTIALS",
    "FORBIDDEN", "OWNER_ONLY", "VALIDATION_ERROR", "NOT_FOUND", "UPSTREAM_ERROR",
})


class ApiError(Exception):
    def __init__(self, status: int, code: str, msg: str):
        assert code in ERROR_CODES, f"정의되지 않은 오류 코드: {code}"
        self.status, self.code, self.msg = status, code, msg


def _body(status: int, code: str, msg: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "msg": msg})


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, e: ApiError):
        return _body(e.status, e.code, e.msg)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        return _body(400, "VALIDATION_ERROR", "요청 값이 올바르지 않음")

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        if e.status_code == 404:
            return _body(404, "NOT_FOUND", "찾을 수 없음")
        if e.status_code == 401:
            return _body(401, "UNAUTHORIZED", "로그인이 필요함")
        if e.status_code == 403:
            return _body(403, "FORBIDDEN", "권한이 없음")
        return _body(e.status_code, "VALIDATION_ERROR", str(e.detail))
