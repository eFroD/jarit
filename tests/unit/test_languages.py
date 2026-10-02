"""Supported language codes and their names in the extraction prompt."""

import pytest

from jarit.languages import Language, prompt_name


def test_supported_codes_in_display_order():
    assert [lang.value for lang in Language] == ["en", "de", "es", "fr", "it"]


@pytest.mark.parametrize(
    ("code", "name"),
    [
        ("en", "English"),
        ("de", "German"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("it", "Italian"),
    ],
)
def test_prompt_name_for_codes(code, name):
    assert prompt_name(code) == name


def test_unknown_legacy_value_passes_through():
    assert prompt_name("japanese") == "japanese"
