"""오류 - 모든 API 오류를 {code, msg} 로 돌려준다. code 는 정의서 7-2 의 13종뿐."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

CODES = {
    "EMAIL_INVALID", "PASSWORD_TOO_WEAK", "TOKEN_EXPIRED", "INVITE_NOT_FOUND",
    "MEETING_NOT_FOUND", "EMAIL_DUPLICATED", "TEAM_FULL", "UNSUPPORTED_MEDIA_TYPE",
    "INVALID_CREDENTIALS", "FORBIDDEN", "OWNER_ONLY", "VALIDATION_ERROR", "NOT_FOUND",
}


class AppError(Exception):
    def __init__(self, status: int, code: str, msg: str):
        assert code in CODES, code
        self.status, self.code, self.msg = status, code, msg


def body(code: str, msg: str) -> dict:
    return {"code": code, "msg": msg}


# 자주 쓰는 오류
def validation(msg: str) -> AppError:
    return AppError(400, "VALIDATION_ERROR", msg)


def forbidden(msg: str = "권한이 없음") -> AppError:
    return AppError(403, "FORBIDDEN", msg)


def owner_only() -> AppError:
    return AppError(403, "OWNER_ONLY", "owner 만 할 수 있음")


def not_found(msg: str = "찾을 수 없음") -> AppError:
    return AppError(404, "NOT_FOUND", msg)


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, e: AppError):
        return JSONResponse(body(e.code, e.msg), status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        first = e.errors()[0] if e.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        return JSONResponse(body("VALIDATION_ERROR", f"입력 형식 오류 - {where}: {first.get('msg', '')}"), status_code=400)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        if e.status_code == 404:
            return JSONResponse(body("NOT_FOUND", "없는 경로"), status_code=404)
        if e.status_code == 405:
            return JSONResponse(body("VALIDATION_ERROR", "허용되지 않는 메서드"), status_code=405)
        return JSONResponse(body("VALIDATION_ERROR", str(e.detail)), status_code=e.status_code)
