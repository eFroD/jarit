"""Tests for the startup check of JARIT_ENCRYPTION_KEY."""

import re

import pytest
from cryptography.fernet import Fernet

from jarit.core import crypto

SUGGESTION = re.compile(r"^JARIT_ENCRYPTION_KEY=(\S{44})$", re.MULTILINE)


@pytest.fixture(autouse=True)
def fresh_cipher_cache():
    crypto.get_cipher.cache_clear()
    yield
    crypto.get_cipher.cache_clear()


def run_check(capsys) -> tuple[str, str]:
    with pytest.raises(SystemExit) as exc_info:
        crypto.require_encryption_key()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    return captured.err, SUGGESTION.search(captured.err).group(1)


def test_missing_key_aborts_with_usable_suggestion(monkeypatch, capsys):
    monkeypatch.delenv("JARIT_ENCRYPTION_KEY", raising=False)
    err, suggested = run_check(capsys)
    Fernet(suggested)
    assert "missing" in err
    assert "become\nunreadable" in err


def test_invalid_key_aborts_without_echoing_value(monkeypatch, capsys):
    monkeypatch.setenv("JARIT_ENCRYPTION_KEY", "CHANGEME")
    err, suggested = run_check(capsys)
    Fernet(suggested)
    assert "invalid" in err
    assert "CHANGEME" not in err


def test_each_failed_start_suggests_a_new_key(monkeypatch, capsys):
    monkeypatch.delenv("JARIT_ENCRYPTION_KEY", raising=False)
    _, first = run_check(capsys)
    _, second = run_check(capsys)
    assert first != second


def test_valid_key_passes_silently(monkeypatch, capsys):
    monkeypatch.setenv("JARIT_ENCRYPTION_KEY", Fernet.generate_key().decode())
    crypto.require_encryption_key()
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
