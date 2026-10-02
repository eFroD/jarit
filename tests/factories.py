"""Builders for test data shared by unit and DB tests."""

from jarit.models.output_models.recipe import Recipe, RecipeResponse


def recipe_dict(name: str = "Shakshuka") -> dict:
    return {
        "name": name,
        "description": "Eggs in tomato sauce",
        "recipeYield": "2",
        "recipeIngredient": ["4 eggs", "400 g tomatoes"],
        "recipeInstructions": [{"@type": "HowToStep", "text": "Cook"}],
        "keywords": ["eggs"],
        "author": None,
        "video": None,
        "url": None,
    }


def make_recipe(name: str = "Shakshuka") -> Recipe:
    return Recipe.model_validate(recipe_dict(name))


def make_response(
    name: str = "Shakshuka", suggested: str | None = None
) -> RecipeResponse:
    return RecipeResponse(
        recipe=make_recipe(name),
        suggested_version=make_recipe(suggested) if suggested else None,
    )


def empty_response() -> RecipeResponse:
    return RecipeResponse(recipe=None, suggested_version=None)
