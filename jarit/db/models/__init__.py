# Import every model so Base.metadata is complete (Alembic, relationships).
from jarit.db.models import api_keys, extraction_jobs, users  # noqa: F401
