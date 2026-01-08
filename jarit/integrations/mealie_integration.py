"""This module serves the functionality for communication with a Mealie instance."""

import httpx
import json
from pydantic import HttpUrl


async def push_image_to_mealie(
    image_url: HttpUrl, slug: str, mealie_endpoint: str, mealie_api_key: str
) -> bool:
    """Uploads an image to a Mealie recipe asynchronously.

    Args:
        image_url: URL of the image to download and upload
        slug: The recipe slug identifier
        mealie_endpoint: Mealie instance base URL
        mealie_api_key: User's Mealie API key

    Returns:
        bool: True if successful
    """
    headers = {"Authorization": f"Bearer {mealie_api_key}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Download the image asynchronously
        img_response = await client.get(str(image_url))
        img_response.raise_for_status()
        image_binary = img_response.content

        # Determine image extension from URL or content-type
        content_type = img_response.headers.get("content-type", "")
        if "jpeg" in content_type or "jpg" in content_type:
            extension = "jpg"
        elif "png" in content_type:
            extension = "png"
        elif "webp" in content_type:
            extension = "webp"
        elif "?" in str(image_url):
            extension = str(image_url).split("?")[0].split(".")[-1]
        else:
            extension = "jpg"

        # Prepare multipart form data
        files = {
            "image": ("image." + extension, image_binary, f"image/{extension}"),
            "extension": (None, extension),
        }

        # Upload to Mealie asynchronously
        response = await client.put(
            f"{mealie_endpoint}/api/recipes/{slug}/image", headers=headers, files=files
        )
        response.raise_for_status()

    return True


async def push_recipe_to_mealie(
    recipe: dict, mealie_endpoint: str, mealie_api_key: str
) -> str:
    """Pushes a recipe to a Mealie instance asynchronously.

    Args:
        recipe: The recipe to be pushed
        mealie_endpoint: Mealie instance base URL
        mealie_api_key: User's Mealie API key

    Returns:
        str: Success message
    """
    mealie_endpoint = mealie_endpoint.rstrip("/")
    send_recipe_url = f"{mealie_endpoint}/api/recipes/create/html-or-json"

    headers = {
        "Authorization": f"Bearer {mealie_api_key}",
        "accept": "application/json",
        "Content-Type": "application/json",
    }
    body = {
        "includeTags": False,
        "data": json.dumps(recipe, ensure_ascii=False),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(send_recipe_url, headers=headers, json=body)
        response.raise_for_status()
        slug = response.json()

    # Check if there is an image in the recipe and upload it separately
    if "image" in recipe and recipe["image"]:
        await push_image_to_mealie(
            recipe["image"], slug, mealie_endpoint, mealie_api_key
        )

    return "Recipe pushed to Mealie successfully."


async def verify_mealie_user(mealie_endpoint: str, mealie_api_key: str) -> bool:
    """Verify Mealie user credentials.

    Args:
        mealie_endpoint: Mealie instance base URL
        mealie_api_key: User's Mealie API key

    Returns:
        bool: True if credentials are valid
    """
    mealie_endpoint = mealie_endpoint.rstrip("/")
    check_user_url = f"{mealie_endpoint}/api/users/self"

    headers = {
        "Authorization": f"Bearer {mealie_api_key}",
        "accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(check_user_url, headers=headers)
        response.raise_for_status()
        return True
