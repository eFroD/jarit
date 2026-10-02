import logging

import pytest

from jarit.jobs.settings import MAX_CONCURRENT_ENV, max_concurrent_extractions


def test_default_when_unset(monkeypatch):
    monkeypatch.delenv(MAX_CONCURRENT_ENV, raising=False)
    assert max_concurrent_extractions() == 2


@pytest.mark.parametrize("raw, expected", [("3", 3), (" 1 ", 1), ("10", 10)])
def test_valid_values(monkeypatch, raw, expected):
    monkeypatch.setenv(MAX_CONCURRENT_ENV, raw)
    assert max_concurrent_extractions() == expected


@pytest.mark.parametrize("raw", ["0", "-1", "abc", "1.5", ""])
def test_invalid_values_fall_back_with_warning(monkeypatch, caplog, raw):
    monkeypatch.setenv(MAX_CONCURRENT_ENV, raw)
    caplog.set_level(logging.WARNING)
    assert max_concurrent_extractions() == 2
    assert MAX_CONCURRENT_ENV in caplog.text
