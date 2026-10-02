"""Application errors carry a stable code next to the English detail."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from jarit.api.errors import AppError, ErrorCode, app_error_handler

CONTRACT_CODES = [
    "INVALID_TOKEN",
    "USER_NOT_FOUND",
    "INVALID_CREDENTIALS",
    "REGISTRATION_DISABLED",
    "EMAIL_TAKEN",
    "USERNAME_TAKEN",
    "ADMIN_REQUIRED",
    "CANNOT_DELETE_SELF",
    "API_KEY_NOT_FOUND",
    "JOB_NOT_FOUND",
    "JOB_NOT_EDITABLE",
    "JOB_NOT_UPLOADABLE",
    "JOB_NOT_RETRYABLE",
    "JOB_NOT_DELETABLE",
    "MEALIE_NOT_CONFIGURED",
    "MEALIE_URL_NOT_CONFIGURED",
    "MEALIE_CREDENTIALS_UNREADABLE",
    "MEALIE_ERROR",
    "MEALIE_INVALID_CREDENTIALS",
]


def test_codes_match_contract():
    assert [code.value for code in ErrorCode] == CONTRACT_CODES


def make_client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/app-error")
    def app_error():
        raise AppError(
            409, ErrorCode.JOB_NOT_RETRYABLE, "Only failed extractions can be retried"
        )

    @app.get("/plain-error")
    def plain_error():
        raise HTTPException(status_code=404, detail="Not here")

    return TestClient(app)


def test_app_error_has_detail_and_code():
    response = make_client().get("/app-error")
    assert response.status_code == 409
    assert response.json() == {
        "detail": "Only failed extractions can be retried",
        "code": "JOB_NOT_RETRYABLE",
    }


def test_plain_http_exception_keeps_its_shape():
    response = make_client().get("/plain-error")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not here"}
