import pytest

import app.core.database as database
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "test-token-key")
    monkeypatch.setenv("LICHESS_CLIENT_ID", "swindle-test")
    monkeypatch.setenv("LICHESS_REDIRECT_URI", "http://testserver/api/v1/integrations/lichess/callback")
    monkeypatch.setenv("LICHESS_SCOPES", "email:read")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://frontend.test")
    get_settings.cache_clear()
    database.reset_engine()
    database.init_db()
    yield
    database.Base.metadata.drop_all(bind=database.engine)
    get_settings.cache_clear()
