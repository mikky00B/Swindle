from fastapi.testclient import TestClient

from app.main import app


def test_register_login_me_logout_flow() -> None:
    client = TestClient(app)

    registered = client.post("/api/v1/auth/register", json={"username": "michael_t", "password": "supersecret9"})
    assert registered.status_code == 200
    assert registered.json()["username"] == "michael_t"
    assert "swindle_session" in registered.cookies

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "michael_t"

    # Cookie identity authorizes journal endpoints without headers.
    assert client.get("/api/v1/games").status_code == 200

    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_rejects_wrong_password() -> None:
    client = TestClient(app)
    client.post("/api/v1/auth/register", json={"username": "wrongpw", "password": "supersecret9"})
    response = client.post("/api/v1/auth/login", json={"username": "wrongpw", "password": "nope-nope"})
    assert response.status_code == 401


def test_login_rejects_unknown_user() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/auth/login", json={"username": "ghost-user", "password": "supersecret9"})
    assert response.status_code == 401


def test_register_rejects_weak_credentials() -> None:
    client = TestClient(app)
    assert client.post("/api/v1/auth/register", json={"username": "ok-name", "password": "short"}).status_code == 400
    assert client.post("/api/v1/auth/register", json={"username": "bad name!", "password": "supersecret9"}).status_code == 400
    assert client.post("/api/v1/auth/register", json={"username": "dup-user", "password": "supersecret9"}).status_code == 200
    duplicate = client.post("/api/v1/auth/register", json={"username": "dup-user", "password": "supersecret9"})
    assert duplicate.status_code == 400


def test_header_session_still_resolves_outside_production() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/games", headers={"X-Session-Id": "header-user"})
    assert response.status_code == 200


def test_cross_origin_post_is_blocked() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/stories/reset-ignored", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


def test_allowed_origin_post_passes() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/stories/reset-ignored", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200


def test_production_requires_cookie_identity(monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        client = TestClient(app)
        header_response = client.get("/api/v1/games", headers={"X-Session-Id": "spoofed-user"})
        assert header_response.status_code == 401
        no_identity = client.get("/api/v1/games")
        assert no_identity.status_code == 401
    finally:
        get_settings.cache_clear()


def test_lichess_login_start_redirects_to_lichess_oauth() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/auth/lichess/start", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].startswith("https://lichess.org/oauth?")


def test_lichess_login_callback_creates_user_and_session(monkeypatch) -> None:
    import httpx as httpx_module
    from sqlalchemy import select as sa_select

    from app.core.database import get_session as db_session
    from app.integrations.lichess.service import create_lichess_login_url
    from app.models import ChessAccount, OAuthState, User as UserModel
    from tests.test_lichess_oauth_import import MockAsyncClient

    monkeypatch.setattr(httpx_module, "AsyncClient", MockAsyncClient)
    client = TestClient(app)

    start = client.get("/api/v1/auth/lichess/start", follow_redirects=False)
    assert start.status_code == 302
    with db_session() as session:
        state_row = session.scalar(
            sa_select(OAuthState).where(OAuthState.purpose == "login")
        )
        assert state_row is not None
        state = state_row.state

    callback = client.get(
        f"/api/v1/integrations/lichess/callback?code=oauth-code&state={state}",
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert "/journal" in callback.headers["location"]
    assert "swindle_session" in callback.cookies

    with db_session() as session:
        user = session.scalar(sa_select(UserModel).where(UserModel.username == "clevermike"))
        assert user is not None
        account = session.scalar(sa_select(ChessAccount).where(ChessAccount.user_id == user.id))
        assert account is not None
        assert account.platform_username == "clevermike"

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "clevermike"

    # A second sign-in with the same Lichess identity resolves the same user.
    start_two = client.get("/api/v1/auth/lichess/start", follow_redirects=False)
    with db_session() as session:
        state_two = session.scalar(sa_select(OAuthState).where(OAuthState.purpose == "login", OAuthState.user_id.is_(None))).state
    callback_two = client.get(
        f"/api/v1/integrations/lichess/callback?code=oauth-code&state={state_two}",
        follow_redirects=False,
    )
    assert callback_two.status_code == 302
    with db_session() as session:
        users = session.scalars(sa_select(UserModel).where(UserModel.username == "clevermike")).all()
    assert len(users) == 1
