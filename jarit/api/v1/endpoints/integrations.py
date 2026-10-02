from fastapi import APIRouter, Depends
from jarit.api.errors import AppError, ErrorCode
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import httpx
from jarit.integrations.mealie_integration import verify_mealie_user
from jarit.api.v1.endpoints.users import get_current_user
from jarit.db.models.api_keys import APIKey
from jarit.integrations.credentials import SecretUnreadableError, reveal_secret
from jarit.db.models.users import User
from jarit.db.database import get_db


router = APIRouter()


async def get_mealie_credentials(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Retrieve user's Mealie API credentials from database."""
    api_key_entry = (
        db.query(APIKey)
        .filter(
            APIKey.user_id == current_user.id,
            APIKey.service_name == "mealie",
            APIKey.is_active,
        )
        .first()
    )

    if not api_key_entry:
        raise AppError(
            404,
            ErrorCode.MEALIE_NOT_CONFIGURED,
            "Mealie API key not configured. Please add your Mealie credentials first.",
        )

    if not api_key_entry.base_url:
        raise AppError(
            400,
            ErrorCode.MEALIE_URL_NOT_CONFIGURED,
            "Mealie base URL not configured. Please update your Mealie credentials.",
        )

    try:
        api_key = reveal_secret(db, api_key_entry)
    except SecretUnreadableError:
        raise AppError(
            409,
            ErrorCode.MEALIE_CREDENTIALS_UNREADABLE,
            (
                "Your stored Mealie credentials can no longer be read (the server's "
                "encryption key has changed). Please enter your Mealie API key again "
                "in the settings."
            ),
        ) from None

    return {"endpoint": api_key_entry.base_url, "api_key": api_key}


@router.get("/verify-mealie-user")
async def verify_user_mealie(mealie_creds: dict = Depends(get_mealie_credentials)):
    """Verify Mealie user credentials."""
    try:
        is_valid = await verify_mealie_user(
            mealie_creds["endpoint"], mealie_creds["api_key"]
        )
        return {"valid": is_valid}
    except httpx.HTTPStatusError as e:
        return JSONResponse(
            status_code=401,
            content={
                "error": "Invalid Mealie credentials",
                "detail": e.response.text,
                "code": ErrorCode.MEALIE_INVALID_CREDENTIALS.value,
            },
        )
