"""Unit tests for async Mealie integration module."""

import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from pydantic import HttpUrl, BaseModel
import httpx
from jarit.integrations.mealie_integration import (
    push_recipe_to_mealie,
    push_image_to_mealie,
    MEALIE_ENDPOINT,
    MEALIE_API_KEY,
)


class RecipeIngredient(BaseModel):
    """Sample ingredient model."""

    name: str
    amount: str


class Recipe(BaseModel):
    """Sample Recipe Pydantic model for testing."""

    name: str
    description: str
    image: HttpUrl | None = None
    recipeYield: str
    recipeIngredient: list[str]
    recipeInstructions: list[dict]

    class Config:
        populate_by_name = True


@pytest.fixture
def sample_recipe_model():
    """Sample recipe as Pydantic model."""
    return Recipe(
        name="Test Recipe",
        description="A test recipe",
        image="https://example.com/image.jpg",
        recipeYield="4 servings",
        recipeIngredient=["1 cup flour", "2 eggs"],
        recipeInstructions=[{"@type": "HowToStep", "text": "Mix ingredients"}],
    )


@pytest.fixture
def sample_recipe_dict():
    """Sample recipe as dict with HttpUrl."""
    return {
        "name": "Test Recipe",
        "@type": "Recipe",
        "@context": "https://schema.org/",
        "description": "A test recipe",
        "image": "https://example.com/image.jpg",
        "recipeYield": "4 servings",
        "recipeIngredient": ["1 cup flour", "2 eggs"],
        "recipeInstructions": [{"@type": "HowToStep", "text": "Mix ingredients"}],
    }


@pytest.fixture
def sample_recipe_without_image():
    """Sample recipe without image."""
    return {
        "name": "Test Recipe No Image",
        "description": "A test recipe without image",
        "recipeYield": "2 servings",
        "recipeIngredient": ["salt"],
        "recipeInstructions": [{"@type": "HowToStep", "text": "Add salt"}],
    }


class TestPushRecipeToMealie:
    """Tests for async push_recipe_to_mealie function."""

    @pytest.mark.asyncio
    async def test_push_recipe_with_image_success(self, sample_recipe_dict):
        """Test successful recipe push with image upload."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            # Setup mock client
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock POST response for recipe creation
            mock_post_response = Mock()
            mock_post_response.json.return_value = "test-recipe-slug"
            mock_post_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_post_response)

            # Mock GET response for image download
            mock_get_response = Mock()
            mock_get_response.content = b"fake_image_data"
            mock_get_response.headers = {"content-type": "image/jpeg"}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            # Mock PUT response for image upload
            mock_put_response = Mock()
            mock_put_response.raise_for_status = Mock()
            mock_client.put = AsyncMock(return_value=mock_put_response)

            # Call function
            result = await push_recipe_to_mealie(sample_recipe_dict)

            # Assertions
            assert result == "Recipe pushed to Mealie successfully."

            # Verify recipe POST was called correctly
            mock_client.post.assert_called_once()
            post_call_args = mock_client.post.call_args
            assert post_call_args[0][0] == f"{MEALIE_ENDPOINT}/api/recipes"
            assert (
                post_call_args[1]["headers"]["Authorization"]
                == f"Bearer {MEALIE_API_KEY}"
            )
            assert post_call_args[1]["json"] == sample_recipe_dict

            # Verify image was downloaded
            mock_client.get.assert_called_once_with("https://example.com/image.jpg")

            # Verify image was uploaded
            mock_client.put.assert_called_once()
            put_call_args = mock_client.put.call_args
            assert "test-recipe-slug" in put_call_args[0][0]
            assert "files" in put_call_args[1]

    @pytest.mark.asyncio
    async def test_push_recipe_without_image(self, sample_recipe_without_image):
        """Test recipe push without image."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock POST response
            mock_post_response = Mock()
            mock_post_response.json.return_value = "test-slug-no-image"
            mock_post_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_post_response)

            # Call function
            result = await push_recipe_to_mealie(sample_recipe_without_image)

            # Assertions
            assert result == "Recipe pushed to Mealie successfully."
            mock_client.post.assert_called_once()

            # Verify no GET or PUT calls for image
            mock_client.get.assert_not_called()
            mock_client.put.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_recipe_with_empty_image(self, sample_recipe_dict):
        """Test recipe push with empty image field."""
        sample_recipe_dict["image"] = ""

        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_post_response = Mock()
            mock_post_response.json.return_value = "test-slug"
            mock_post_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_post_response)

            result = await push_recipe_to_mealie(sample_recipe_dict)

            assert result == "Recipe pushed to Mealie successfully."
            # Empty string should not trigger image upload
            mock_client.get.assert_not_called()
            mock_client.put.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_recipe_pydantic_model(self, sample_recipe_model):
        """Test pushing a Pydantic model (converted to dict first)."""
        recipe_dict = sample_recipe_model.model_dump(by_alias=True, mode="json")

        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock responses
            mock_post_response = Mock()
            mock_post_response.json.return_value = "pydantic-recipe-slug"
            mock_post_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_post_response)

            mock_get_response = Mock()
            mock_get_response.content = b"image_data"
            mock_get_response.headers = {"content-type": "image/jpeg"}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            mock_put_response = Mock()
            mock_put_response.raise_for_status = Mock()
            mock_client.put = AsyncMock(return_value=mock_put_response)

            result = await push_recipe_to_mealie(recipe_dict)

            assert result == "Recipe pushed to Mealie successfully."
            mock_client.post.assert_called_once()

            # Verify the dict was passed correctly (HttpUrl converted to string)
            post_call_args = mock_client.post.call_args
            posted_data = post_call_args[1]["json"]
            assert isinstance(posted_data["image"], str)
            assert posted_data["image"] == "https://example.com/image.jpg"

    @pytest.mark.asyncio
    async def test_push_recipe_http_error(self, sample_recipe_dict):
        """Test handling of HTTP errors during recipe push."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock 401 error
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "401 Unauthorized", request=Mock(), response=Mock(status_code=401)
                )
            )

            with pytest.raises(httpx.HTTPStatusError):
                await push_recipe_to_mealie(sample_recipe_dict)

    @pytest.mark.asyncio
    async def test_push_recipe_422_unprocessable_entity(self, sample_recipe_dict):
        """Test handling of 422 validation errors."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock 422 error with response text
            mock_response = Mock()
            mock_response.status_code = 422
            mock_response.text = '{"detail": "Invalid recipe format"}'

            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "422 Unprocessable Entity", request=Mock(), response=mock_response
                )
            )

            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await push_recipe_to_mealie(sample_recipe_dict)

            assert exc_info.value.response.status_code == 422

    @pytest.mark.asyncio
    async def test_slug_format_without_quotes(self, sample_recipe_dict):
        """Test that slug is returned without quotes."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock response with clean slug
            mock_post_response = Mock()
            mock_post_response.json.return_value = (
                "blumenkohlsteak-mit-goldener-grana-padano"
            )
            mock_post_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_post_response)

            mock_get_response = Mock()
            mock_get_response.content = b"image"
            mock_get_response.headers = {"content-type": "image/png"}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            mock_put_response = Mock()
            mock_put_response.raise_for_status = Mock()
            mock_client.put = AsyncMock(return_value=mock_put_response)

            await push_recipe_to_mealie(sample_recipe_dict)

            # Verify slug in PUT URL has no quotes or encoding
            put_call_url = mock_client.put.call_args[0][0]
            assert "blumenkohlsteak-mit-goldener-grana-padano" in put_call_url
            assert "%22" not in put_call_url
            assert '"' not in put_call_url


class TestPushImageToMealie:
    """Tests for async push_image_to_mealie function."""

    @pytest.mark.asyncio
    async def test_upload_png_image_success(self):
        """Test successful PNG image upload."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock image download
            mock_get_response = Mock()
            mock_get_response.content = b"fake_png_content"
            mock_get_response.headers = {"content-type": "image/png"}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            # Mock image upload
            mock_put_response = Mock()
            mock_put_response.raise_for_status = Mock()
            mock_client.put = AsyncMock(return_value=mock_put_response)

            # Call function
            image_url = HttpUrl("https://example.com/test.png")
            slug = "test-recipe-slug"
            result = await push_image_to_mealie(image_url, slug)

            # Assertions
            assert result is True
            mock_client.get.assert_called_once_with("https://example.com/test.png")

            # Verify PUT request
            mock_client.put.assert_called_once()
            put_call_args = mock_client.put.call_args
            assert put_call_args[0][0] == f"{MEALIE_ENDPOINT}/api/recipes/{slug}/image"
            assert (
                put_call_args[1]["headers"]["Authorization"]
                == f"Bearer {MEALIE_API_KEY}"
            )

            # Verify files parameter
            files = put_call_args[1]["files"]
            assert "image" in files
            assert "extension" in files
            assert files["extension"][1] == "png"
            assert files["image"][1] == b"fake_png_content"
            assert files["image"][2] == "image/png"

    @pytest.mark.asyncio
    async def test_upload_jpg_image_from_content_type(self):
        """Test JPG image upload with content-type detection."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.content = b"fake_jpeg_content"
            mock_get_response.headers = {"content-type": "image/jpeg"}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            mock_put_response = Mock()
            mock_put_response.raise_for_status = Mock()
            mock_client.put = AsyncMock(return_value=mock_put_response)

            image_url = HttpUrl("https://example.com/photo")
            result = await push_image_to_mealie(image_url, "test-slug")

            assert result is True
            files = mock_client.put.call_args[1]["files"]
            assert files["extension"][1] == "jpg"
            assert files["image"][0] == "image.jpg"

    @pytest.mark.asyncio
    async def test_upload_webp_image(self):
        """Test WebP image upload."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.content = b"fake_webp_content"
            mock_get_response.headers = {"content-type": "image/webp"}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            mock_put_response = Mock()
            mock_put_response.raise_for_status = Mock()
            mock_client.put = AsyncMock(return_value=mock_put_response)

            image_url = HttpUrl("https://cdn.example.com/image.webp")
            result = await push_image_to_mealie(image_url, "webp-recipe")

            assert result is True
            files = mock_client.put.call_args[1]["files"]
            assert files["extension"][1] == "webp"

    @pytest.mark.asyncio
    async def test_image_extension_fallback_from_url(self):
        """Test extension detection from URL when content-type is missing."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.content = b"fake_content"
            mock_get_response.headers = {"content-type": "application/octet-stream"}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            mock_put_response = Mock()
            mock_put_response.raise_for_status = Mock()
            mock_client.put = AsyncMock(return_value=mock_put_response)

            # URL with query parameters
            image_url = HttpUrl("https://example.com/photo.png?size=large&format=web")
            result = await push_image_to_mealie(image_url, "fallback-test")

            assert result is True
            files = mock_client.put.call_args[1]["files"]
            assert files["extension"][1] == "png"

    @pytest.mark.asyncio
    async def test_image_extension_default_fallback(self):
        """Test default jpg extension when detection fails."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.content = b"fake_content"
            mock_get_response.headers = {}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            mock_put_response = Mock()
            mock_put_response.raise_for_status = Mock()
            mock_client.put = AsyncMock(return_value=mock_put_response)

            # No extension in URL
            image_url = HttpUrl("https://example.com/image")
            result = await push_image_to_mealie(image_url, "default-extension")

            assert result is True
            files = mock_client.put.call_args[1]["files"]
            assert files["extension"][1] == "jpg"  # Default fallback

    @pytest.mark.asyncio
    async def test_image_download_404_error(self):
        """Test handling of image download failure."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "404 Not Found", request=Mock(), response=Mock(status_code=404)
                )
            )

            image_url = HttpUrl("https://example.com/missing.jpg")

            with pytest.raises(httpx.HTTPStatusError):
                await push_image_to_mealie(image_url, "test-slug")

    @pytest.mark.asyncio
    async def test_image_upload_500_error(self):
        """Test handling of image upload failure."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Successful download
            mock_get_response = Mock()
            mock_get_response.content = b"fake_content"
            mock_get_response.headers = {"content-type": "image/png"}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            # Failed upload
            mock_client.put = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "500 Server Error", request=Mock(), response=Mock(status_code=500)
                )
            )

            image_url = HttpUrl("https://example.com/test.png")

            with pytest.raises(httpx.HTTPStatusError):
                await push_image_to_mealie(image_url, "test-slug")

    @pytest.mark.asyncio
    async def test_instagram_cdn_url_handling(self):
        """Test handling of Instagram CDN URLs with query parameters."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.content = b"instagram_image"
            mock_get_response.headers = {"content-type": "image/jpeg"}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            mock_put_response = Mock()
            mock_put_response.raise_for_status = Mock()
            mock_client.put = AsyncMock(return_value=mock_put_response)

            # Instagram-style URL
            image_url = HttpUrl(
                "https://scontent-fra3-1.cdninstagram.com/v/t51.2885-15/"
                "522819255_18519012295046223_5891187172040965353_n.jpg"
                "?stp=dst-jpg_e15_fr_p1080x1080_tt6"
            )
            result = await push_image_to_mealie(image_url, "instagram-recipe")

            assert result is True
            files = mock_client.put.call_args[1]["files"]
            assert files["extension"][1] == "jpg"

    @pytest.mark.asyncio
    async def test_timeout_configuration(self):
        """Test that timeout is properly configured."""
        with patch(
            "jarit.integrations.mealie_integration.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.content = b"content"
            mock_get_response.headers = {"content-type": "image/png"}
            mock_get_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_get_response)

            mock_put_response = Mock()
            mock_put_response.raise_for_status = Mock()
            mock_client.put = AsyncMock(return_value=mock_put_response)

            image_url = HttpUrl("https://example.com/test.png")
            await push_image_to_mealie(image_url, "test")

            # Verify AsyncClient was called with timeout
            mock_client_class.assert_called_with(timeout=30.0)
