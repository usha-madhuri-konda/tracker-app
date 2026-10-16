import os
import sys

# Tests must never reach a real database: drop any Postgres settings, and set a
# throwaway SECRET_KEY before the app module is imported (it refuses to start without one).
for var in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_PASSWORD", "POSTGRES_USER"):
    os.environ.pop(var, None)
os.environ["SECRET_KEY"] = "test-only-secret-key"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from app import app as flask_app  # noqa: E402
from models import db  # noqa: E402


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    # Safety net: the schema is wiped for every test, so only ever do that to SQLite.
    assert flask_app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite")
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
    return flask_app.test_client()


@pytest.fixture
def other_client(client):
    """A second, separate browser session sharing the same database."""
    return flask_app.test_client()