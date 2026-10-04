"""Languages a user can choose for the app and for extracted recipes."""

from enum import Enum


class Language(str, Enum):
    EN = "en"
    DE = "de"
    ES = "es"
    FR = "fr"
    IT = "it"


# How the extraction prompt names each language.
PROMPT_NAMES: dict[Language, str] = {
    Language.EN: "English",
    Language.DE: "German",
    Language.ES: "Spanish",
    Language.FR: "French",
    Language.IT: "Italian",
}


def prompt_name(value: str) -> str:
    """Name for the prompt; values from before language codes pass through."""
    try:
        return PROMPT_NAMES[Language(value)]
    except ValueError:
        return value
