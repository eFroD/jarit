from jarit.agents.video_agent import video_agent
from jarit.models.input_models.video import VideoRequest
from jarit.models.output_models.recipe import RecipeResponse


async def extract_recipe_from_url(request: VideoRequest) -> RecipeResponse:
    response = await video_agent.run(
        f"Please extract the recipe from the given url: {request.url}. The target language is {request.target_language}."
    )
    output = RecipeResponse.model_validate(response.output)
    return output
