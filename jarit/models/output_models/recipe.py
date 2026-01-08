from typing import List, Optional, Union
from pydantic import BaseModel, HttpUrl, Field


class NutritionInformation(BaseModel):
    calories: Optional[str]
    fatContent: Optional[str]
    carbohydrateContent: Optional[str]
    proteinContent: Optional[str]
    fiberContent: Optional[str]
    sugarContent: Optional[str]
    servingSize: Optional[str]


class HowToStep(BaseModel):
    type_: str = Field("HowToStep", alias="@type")
    text: str


class HowToSection(BaseModel):
    name: Optional[str]
    itemListElement: List[HowToStep]


class Author(BaseModel):
    type_: Optional[str] = Field("Person", alias="@type")
    name: str


class Recipe(BaseModel):
    context: str = Field("https://schema.org", alias="@context")
    type_: str = Field("Recipe", alias="@type")
    name: str
    description: Optional[str]
    image: Optional[Union[HttpUrl, List[HttpUrl], str]] = ""
    recipeYield: str = ""
    recipeIngredient: List[str]
    recipeInstructions: Optional[Union[List[HowToStep], List[HowToSection]]]
    prepTime: str = ""
    cookTime: str = ""
    totalTime: str = ""
    recipeCategory: str = ""
    recipeCuisine: str = ""
    keywords: Optional[List[str]]
    suitableForDiet: str = ""
    author: Optional[Author]
    video: Optional[HttpUrl]
    url: Optional[HttpUrl]


class RecipeError(BaseModel):
    error: str = ""
    missing_fields: List[str] = []


class RecipeResponse(BaseModel):
    recipe: Optional[Recipe]
    suggested_version: Optional[Recipe]
    error_info: RecipeError = Field(default_factory=RecipeError)
