# The encryption key check must run before anything else, in particular before
# Logfire is configured, so the suggested key never leaves this process.
from jarit.core.crypto import require_encryption_key

require_encryption_key()

import logging  # noqa: E402
import os  # noqa: E402

import logfire  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from jarit.api.router import router  # noqa: E402
from jarit.db.database import Base, engine  # noqa: E402
from jarit.integrations.credentials import migrate_plaintext_secrets  # noqa: E402

logger = logging.getLogger("jarit")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

Base.metadata.create_all(bind=engine)

try:
    migrate_plaintext_secrets()
except Exception:
    logger.warning("Migration of legacy plaintext credentials failed; will retry")

app = FastAPI(title="JarIt API", version="1.0.0")

logfire_token = os.environ.get("LOGFIRE_WRITE_TOKEN")
logfire.configure(token=logfire_token)
logfire.instrument_pydantic_ai()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("DOMAIN_NAME", "http://localhost"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(router)
