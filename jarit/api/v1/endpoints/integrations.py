from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import httpx
from jarit.models.output_models.recipe import Recipe
from jarit.integrations.mealie_integration import (
    push_recipe_to_mealie,
    verify_mealie_user,
)
from jarit.api.v1.endpoints.users import get_current_user
from jarit.db.models.api_keys import APIKey
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
        raise HTTPException(
            status_code=404,
            detail="Mealie API key not configured. Please add your Mealie credentials first.",
        )

    if not api_key_entry.base_url:
        raise HTTPException(
            status_code=400,
            detail="Mealie base URL not configured. Please update your Mealie credentials.",
        )

    return {"endpoint": api_key_entry.base_url, "api_key": api_key_entry.api_key}


@router.post("/upload-mealie")
async def upload_to_mealie(
    recipe: Recipe, mealie_creds: dict = Depends(get_mealie_credentials)
):
    """Upload a recipe to Mealie."""
    try:
        response = await push_recipe_to_mealie(
            recipe.model_dump(by_alias=True, mode="json"),
            mealie_creds["endpoint"],
            mealie_creds["api_key"],
        )
        return {"message": response}
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Mealie error: {e.response.text}",
        )


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
            content={"error": "Invalid Mealie credentials", "detail": e.response.text},
        )
