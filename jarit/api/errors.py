"""Application errors with a stable code the frontend can translate."""

from enum import Enum

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    INVALID_TOKEN = "INVALID_TOKEN"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    REGISTRATION_DISABLED = "REGISTRATION_DISABLED"
    EMAIL_TAKEN = "EMAIL_TAKEN"
    USERNAME_TAKEN = "USERNAME_TAKEN"
    ADMIN_REQUIRED = "ADMIN_REQUIRED"
    CANNOT_DELETE_SELF = "CANNOT_DELETE_SELF"
    API_KEY_NOT_FOUND = "API_KEY_NOT_FOUND"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_NOT_EDITABLE = "JOB_NOT_EDITABLE"
    JOB_NOT_UPLOADABLE = "JOB_NOT_UPLOADABLE"
    JOB_NOT_RETRYABLE = "JOB_NOT_RETRYABLE"
    JOB_NOT_DELETABLE = "JOB_NOT_DELETABLE"
    MEALIE_NOT_CONFIGURED = "MEALIE_NOT_CONFIGURED"
    MEALIE_URL_NOT_CONFIGURED = "MEALIE_URL_NOT_CONFIGURED"
    MEALIE_CREDENTIALS_UNREADABLE = "MEALIE_CREDENTIALS_UNREADABLE"
    MEALIE_ERROR = "MEALIE_ERROR"
    MEALIE_INVALID_CREDENTIALS = "MEALIE_INVALID_CREDENTIALS"


class AppError(HTTPException):
    """An HTTPException whose response also carries `code`."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        detail: str,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code.value},
        headers=exc.headers,
    )
