import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_session
from app.main import app
from app.models import ChessAccount, OAuthState


class MockTokenClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        assert kwargs["data"]["grant_type"] == "authorization_code"
        assert kwargs["data"]["code"] == "cc-code"
        return httpx.Response(
            200,
            json={"access_token": "cc-secret-token", "token_type": "bearer"},
            request=httpx.Request("POST", url),
        )


def test_chesscom_oauth_disabled_by_default() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/integrations/chesscom/connect?username=hikaru", follow_redirects=False)
    assert response.status_code == 404
    status = client.get("/api/v1/integrations/chesscom/status")
    assert status.json()["oauth_enabled"] is False


def _enable_oauth(monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("CHESSCOM_CLIENT_ID", "cc-client")
    monkeypatch.setenv("CHESSCOM_CLIENT_SECRET", "cc-secret")
    get_settings.cache_clear()


def test_chesscom_oauth_link_flow(monkeypatch) -> None:
    from app.core.config import get_settings

    _enable_oauth(monkeypatch)
    try:
        monkeypatch.setattr(httpx, "AsyncClient", MockTokenClient)
        client = TestClient(app)
        assert client.post("/api/v1/auth/register", json={"username": "cc-linker", "password": "supersecret9"}).status_code == 200

        start = client.get("/api/v1/integrations/chesscom/connect?username=CCPlayer", follow_redirects=False)
        assert start.status_code == 302
        assert "chess.com/oauth/authorize" in start.headers["location"]
        assert "state=" in start.headers["location"]

        with get_session() as session:
            state_row = session.scalar(select(OAuthState).where(OAuthState.platform == "chesscom"))
            assert state_row is not None
            assert state_row.username == "CCPlayer"
            state = state_row.state

        callback = client.get(
            f"/api/v1/integrations/chesscom/callback?code=cc-code&state={state}",
            follow_redirects=False,
        )
        assert callback.status_code == 302
        assert "/journal" in callback.headers["location"]

        with get_session() as session:
            account = session.scalar(select(ChessAccount).where(ChessAccount.platform == "chesscom"))
            assert account is not None
            assert account.platform_username == "CCPlayer"
            assert account.access_token_encrypted
            assert "cc-secret-token" not in account.access_token_encrypted

        status = client.get("/api/v1/integrations/chesscom/status")
        assert status.json()["connected"] is True
        assert status.json()["platform_username"] == "CCPlayer"
    finally:
        get_settings.cache_clear()


def test_chesscom_username_taken_by_other(monkeypatch) -> None:
    from app.core.config import get_settings

    _enable_oauth(monkeypatch)
    try:
        monkeypatch.setattr(httpx, "AsyncClient", MockTokenClient)
        client = TestClient(app)
        assert client.post("/api/v1/auth/register", json={"username": "first-owner", "password": "supersecret9"}).status_code == 200
        assert client.get("/api/v1/integrations/chesscom/connect?username=SharedGuy", follow_redirects=False).status_code == 302
        with get_session() as session:
            state_row = session.scalar(select(OAuthState).where(OAuthState.platform == "chesscom"))
        assert client.get(
            f"/api/v1/integrations/chesscom/callback?code=cc-code&state={state_row.state}",
            follow_redirects=False,
        ).status_code == 302
        client.post("/api/v1/auth/logout")

        assert client.post("/api/v1/auth/register", json={"username": "second-user", "password": "supersecret9"}).status_code == 200
        response = client.get("/api/v1/integrations/chesscom/connect?username=sharedguy", follow_redirects=False)
        assert response.status_code == 400
        assert "already linked" in response.json()["detail"]
    finally:
        get_settings.cache_clear()
