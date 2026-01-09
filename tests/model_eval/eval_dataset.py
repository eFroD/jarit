from pydantic_evals.dataset import Case
from jarit.models.output_models.recipe import Recipe


recipe_1 = {
    "@type": "Recipe",
    "cookTime": "PT17M",
    "totalTime": "PT17M",
    "description": "Ein leckerer Nudelauflauf mit Brokkoli, Schinken und Käse.",
    "name": "Brokkoli-Nudelauflauf",
    "suitableForDiet": "",
    "recipeIngredient": [
        "1 Brokkoli",
        "200 g Rigatoni",
        "1 Zwiebel, rot",
        "1 Peperoni, rot",
        "2 Knoblauchzehen",
        "2 Flocken Butter",
        "150 g Kochschinken",
        "Salz",
        "Pfeffer",
        "Muskat",
        "150 ml Sahne",
        "100 ml Kochwasser",
        "150 g Gouda",
    ],
    "video": "https://m.facebook.com/reel/1098675172447515/?referral_source=external_deeplink",
    "prepTime": "",
    "nutrition": {
        "servingSize": "",
        "fatContent": "",
        "calories": "",
        "carbohydrateContent": "",
        "proteinContent": "",
        "fiberContent": "",
        "sugarContent": "",
    },
    "recipeCategory": "Hauptgericht",
    "recipeInstructions": [
        {
            "@type": "HowToStep",
            "text": "Den Brokkoli vorbereiten: Röschen abschneiden. Ein Stück vom Strunk wegschneiden. Das Äußere vom Stielansatz wegschneiden und den Strunk vierteln.",
        },
        {
            "text": "Den geviertelten Brokkoli-Strunk mit einer Portion Salz in einem Topf mit Deckel 5 Minuten kochen lassen.",
            "@type": "HowToStep",
        },
        {
            "@type": "HowToStep",
            "text": "Zwiebel und Knoblauch schälen und schneiden. Die rote Peperoni ebenfalls schneiden.",
        },
        {
            "@type": "HowToStep",
            "text": "In einer Pfanne eine Flocke Butter schmelzen. Die geschnittenen Zwiebeln, Knoblauch und Peperoni dazugeben und anbraten.",
        },
        {
            "text": "Die Nudeln zum kochenden Brokkoli-Strunk in den Topf geben, einen Deckel auflegen und weitere 3 Minuten kochen.",
            "@type": "HowToStep",
        },
        {
            "text": "Die Brokkoli-Röschen zu den Nudeln in den Topf geben, einen Deckel auflegen und 4 Minuten kochen.",
            "@type": "HowToStep",
        },
        {
            "text": "Den Kochschinken würfeln, falls gewünscht, und zu dem Gemüse in die Pfanne geben und schwenken.",
            "@type": "HowToStep",
        },
        {
            "@type": "HowToStep",
            "text": "Sobald die Nudeln 'mehr als al dente' sind, alles abgießen. Dabei das Kochwasser (ca. 100 ml) und den gekochten Brokkoli-Strunk in ein hohes Gefäß geben.",
        },
        {
            "text": "Zum Strunk und der Flüssigkeit einen Schluck Sahne (insgesamt 150 ml) geben. Mit Salz, Pfeffer und Muskat würzen und alles pürieren, bis eine brokkoliartige Suppe entsteht.",
            "@type": "HowToStep",
        },
        {
            "@type": "HowToStep",
            "text": "Die abgetropften Nudeln und Brokkoli-Röschen zusammen mit dem angebratenen Gemüse (und Schinken) in eine Auflaufform geben und vermengen.",
        },
        {
            "text": "Die pürierte Brokkolisauce über die Mischung in der Auflaufform gießen.",
            "@type": "HowToStep",
        },
        {"@type": "HowToStep", "text": "Den Auflauf mit geriebenem Gouda bestreuen."},
        {
            "text": "Das Ganze gratinieren. Gratinieren dauert 5 Minuten.",
            "@type": "HowToStep",
        },
    ],
    "recipeYield": "",
    "author": {"name": "Hannes / FOODBOOM", "@type": "Person"},
    "recipeCuisine": "Deutsch",
    "image": [],
    "url": "https://m.facebook.com/reel/1098675172447515/?referral_source=external_deeplink",
    "@context": "https://schema.org",
    "keywords": ["Brokkoli", "Nudelauflauf", "Auflauf", "Pasta", "Schinken", "Käse"],
}

recipe_2 = {
    "recipeYield": "2 servings",
    "name": "Oven Dumplings",
    "recipeIngredient": [
        "1 package frozen dumplings (approx. 12 pieces)",
        "1 can coconut milk (400 ml), preferably extra creamy coconut milk",
        "2 tbsp red curry paste",
        "Juice of half a lemon",
        "2-3 tbsp soy sauce",
        "1 tsp honey",
        "(optional: a little water if the sauce is too thick)",
        "1 Bok Choy",
        "1 Bell Pepper",
        "1 handful Edamame (frozen, pre-cooked)",
        "1 handful Bean Sprouts",
        "Crispy Chili Oil (for garnish)",
        "Sesame (for garnish)",
        "Fresh Cilantro (for garnish)",
    ],
    "prepTime": "PT10M",
    "description": "Oh my God, this recipe is an absolute game changer. Super delicious sauce and perfectly cooked dumplings in a casserole dish. Similarly seen at @coconutandbliss, original from @healthygirlkitchen ✨",
    "totalTime": "PT30M",
    "cookTime": "PT20M",
    "keywords": [
        "Oven Dumplings",
        "One Pot Dumplings",
        "Oven Recipe",
        "Dumpling Recipe",
        "Oven Gyoza",
    ],
    "recipeInstructions": [
        {
            "text": "Prepare the sauce: In a bowl, whisk together coconut milk, curry paste, lemon juice, soy sauce, and honey until smooth. Add a little water if needed."
        },
        {
            "text": "Prepare the vegetables: Roughly chop the bok choy, slice the bell pepper into strips. Add them to an ovenproof dish along with the edamame and bean sprouts."
        },
        {"text": "Pour the sauce over the vegetables in the ovenproof dish."},
        {
            "text": "Add dumplings: Place the frozen dumplings on top of the vegetables and sauce."
        },
        {
            "text": "Bake: Bake in a preheated oven at 180 °C (convection) for approx. 15-20 minutes, until the sauce is slightly browned and the dumplings are cooked through."
        },
        {
            "text": "Serve: Top with crispy chili oil, sesame, and fresh cilantro – enjoy directly from the dish."
        },
    ],
    "video": "https://www.instagram.com/reel/DJoCpaCojEx/?igsh=M3FiNzdjcTgwMmht",
    "url": "https://www.instagram.com/reel/DJoCpaCojEx/?igsh=M3FiNzdjcTgwMmht",
    "suitableForDiet": "",
    "author": {"name": "piaundhalloumi"},
    "image": [],
    "recipeCuisine": "Asian",
    "recipeCategory": "Oven Recipe",
}

cases = [
    Case(
        name="recipe_1",
        inputs={
            "url": "https://m.facebook.com/reel/1098675172447515/?referral_source=external_deeplink",
            "language": "german",
        },
        expected_output=Recipe.model_validate(recipe_1),
    )
]
cases.append(
    Case(
        name="recipe_2",
        inputs={
            "url": "https://www.instagram.com/reel/DJoCpaCojEx/?igsh=M3FiNzdjcTgwMmht",
            "language": "english",
        },
        expected_output=Recipe.model_validate(recipe_2),
    )
)
