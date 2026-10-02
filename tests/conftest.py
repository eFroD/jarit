import os

from cryptography.fernet import Fernet
from pydantic_ai import models

# Every test run uses a throwaway key, so no real key ever lives in the repo.
os.environ.setdefault("JARIT_ENCRYPTION_KEY", Fernet.generate_key().decode())

# No test may ever reach a real LLM provider.
models.ALLOW_MODEL_REQUESTS = False

DATABASE_URL = os.getenv("DATABASE_URL", "")
# tests/db truncates tables, so only ever run it against a dedicated *_test database.
HAS_POSTGRES = DATABASE_URL.startswith("postgresql") and DATABASE_URL.rsplit("/", 1)[
    -1
].split("?")[0].endswith("_test")

# integration and model_eval need real external services; tests/db needs PostgreSQL.
collect_ignore = ["integration", "model_eval"]
if not HAS_POSTGRES:
    collect_ignore.append("db")


def pytest_report_header():
    if not HAS_POSTGRES:
        return (
            "tests/db skipped: set DATABASE_URL to a PostgreSQL database "
            "whose name ends in _test to run them"
        )
