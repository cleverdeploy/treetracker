import os
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://nobody@localhost/none")
os.environ.setdefault("SESSION_SECRET", "test-secret")
os.environ.setdefault("PHOTOS_DIR", tempfile.mkdtemp(prefix="tt-photos-"))
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")
os.environ.setdefault("BASE_URL", "http://testserver")

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "fixtures"
