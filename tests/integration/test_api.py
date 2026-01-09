from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from jarit.main import app

client = TestClient(app)


@patch("jarit.agents.video_agent.video_agent.run", new_callable=AsyncMock)
def test_extract_recipe(mock_run):
    mock_run.return_value.output = AsyncMock()  # Ensure output is a mock object
    mock_run.return_value.output = {
        "recipe": {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Einfaches Thai Curry",
            "description": "Ein einfaches Thai Curry Rezept, das vegan ist und sich gut für 2 Portionen eignet. Es enthält rote Currypaste, Gemüsefond, Kokosmilch und frisches Gemüse und wird mit Reis und frittiertem Tofu serviert.",
            "image": "https://i.ytimg.com/vi/MZVPy_taU_g/maxresdefault.jpg",
            "recipeYield": "2 Portionen",
            "recipeIngredient": [
                "Öl zum Braten",
                "1 große Knoblauchzehe",
                "1 TL geriebener Ingwer",
                "1 EL Zitronengras, fein geschnitten",
                "50 g rote Currypaste",
                "250 ml Gemüsefond",
                "500 ml Kokosmilch",
                "1 TL Rohrzucker",
                "Einige Limettenblätter",
                "Einige grüne Bohnen",
                "1 Karotte",
                "1 rote Paprika",
                "1 Handvoll Thai-Basilikum",
                "Reis (als Beilage)",
                "Frittierter Naturtofu (als Beilage)",
            ],
            "recipeInstructions": [
                {
                    "@type": "HowToStep",
                    "text": "Öl in einer Pfanne erhitzen. Knoblauch fein hacken, Ingwer reiben, Zitronengras klein schneiden und kurz im Öl anschwitzen. Currypaste dazugeben und weitere 3 Minuten anschwitzen.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Mit Gemüsefond ablöschen und ca. 5 Minuten köcheln lassen.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Kokosmilch, Limettenblätter sowie Rohrzucker ergänzen, alles gut verrühren und die Soße ca. 10 Minuten bei geschlossenem Deckel köcheln lassen.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Gemüse deiner Wahl hinzufügen (zum Beispiel grüne Bohnen, Karotten, Paprika etc.) und köcheln lassen, bis das Gemüse gar ist.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Zum Schluss mit Salz abschmecken. Thai-Basilikum in kleine Stücke reißen und dazugeben.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Auf Reis mit frittiertem Tofu servieren und genießen!",
                },
            ],
            "prepTime": "",
            "cookTime": "",
            "totalTime": "",
            "recipeCategory": "",
            "recipeCuisine": "Thai",
            "keywords": ["vegan", "Thai Curry", "einfach"],
            "suitableForDiet": "Vegan",
            "author": {"@type": "Person", "name": ""},
            "video": "https://www.youtube.com/shorts/MZVPy_taU_g",
            "url": "https://www.youtube.com/shorts/MZVPy_taU_g",
        },
        "suggested_version": {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Einfaches Thai Curry",
            "description": "Ein einfaches und veganes Thai Curry Rezept für 2 Portionen, das mit frischem Gemüse, roter Currypaste und Kokosmilch zubereitet wird. Serviert wird es mit Reis und frittiertem Tofu.",
            "image": "https://i.ytimg.com/vi/MZVPy_taU_g/maxresdefault.jpg",
            "recipeYield": "2 Portionen",
            "recipeIngredient": [
                "Öl zum Braten",
                "1 große Knoblauchzehe, fein gehackt",
                "1 TL geriebener Ingwer",
                "1 EL Zitronengras, fein geschnitten",
                "50 g rote Currypaste",
                "250 ml Gemüsefond",
                "500 ml Kokosmilch",
                "1 TL Rohrzucker",
                "Einige Limettenblätter",
                "Einige grüne Bohnen",
                "1 Karotte, in Scheiben geschnitten",
                "1 rote Paprika, in Streifen geschnitten",
                "1 Handvoll Thai-Basilikum",
                "Reis als Beilage",
                "Frittierter Naturtofu als Beilage",
            ],
            "recipeInstructions": [
                {
                    "@type": "HowToStep",
                    "text": "Öl in einer Pfanne erhitzen. Knoblauch, Ingwer und Zitronengras darin kurz anschwitzen.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Rote Currypaste hinzufügen und weitere 3 Minuten anschwitzen.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Mit Gemüsefond ablöschen und 5 Minuten köcheln lassen.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Kokosmilch, Limettenblätter und Rohrzucker hinzufügen, gut verrühren und die Soße bei geschlossenem Deckel 10 Minuten köcheln lassen.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Gemüse (grüne Bohnen, Karotten, Paprika) hinzufügen und köcheln lassen, bis es gar ist.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Mit Salz abschmecken. Thai-Basilikum in kleine Stücke reißen und unterrühren.",
                },
                {
                    "@type": "HowToStep",
                    "text": "Mit Reis und frittiertem Tofu servieren und genießen.",
                },
            ],
            "prepTime": "10 Minuten",
            "cookTime": "20 Minuten",
            "totalTime": "30 Minuten",
            "recipeCategory": "Hauptgericht",
            "recipeCuisine": "Thai",
            "keywords": ["vegan", "Thai Curry", "einfach"],
            "suitableForDiet": "Vegan",
            "author": {"@type": "Person", "name": "YouTube Creator"},
            "video": "https://www.youtube.com/shorts/MZVPy_taU_g",
            "url": "https://www.youtube.com/shorts/MZVPy_taU_g",
        },
    }

    response = client.post(
        "recipes/extract-recipe",
        json={"url": "http://example.com/video", "target_language": "german"},
    )
    assert response.status_code == 200
    assert "recipe" in response.json()
    assert "suggested_version" in response.json()
    assert "error_info" in response.json()
