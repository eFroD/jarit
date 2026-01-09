from fastapi import APIRouter, HTTPException
from jarit.models.input_models.video import VideoRequest
from jarit.models.output_models.recipe import RecipeResponse
from jarit.core.recipe_service import extract_recipe_from_url

router = APIRouter()


@router.post("/extract-recipe")
async def extract_recipe(request: VideoRequest) -> RecipeResponse:
    try:
        recipe = await extract_recipe_from_url(request)
        return recipe
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
