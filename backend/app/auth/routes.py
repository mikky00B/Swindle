from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.auth.dependencies import resolve_user_id_strict
from app.auth.schemas import AuthUserResponse, LoginRequest, LogoutResponse, RegisterRequest
from app.auth.service import (
    SESSION_COOKIE_NAME,
    AuthError,
    auth_attempt_allowed,
    authenticate_user,
    clear_session_cookie,
    create_auth_session,
    get_user,
    register_user,
    revoke_auth_session,
    set_session_cookie,
)
from app.integrations.lichess.service import create_lichess_login_url

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/lichess/start")
async def lichess_login_start() -> RedirectResponse:
    """Begin "Continue with Lichess" sign-in/sign-up (no account required)."""
    return RedirectResponse(create_lichess_login_url(), status_code=302)


@router.post("/register", response_model=AuthUserResponse)
async def register(payload: RegisterRequest, request: Request, response: Response) -> AuthUserResponse:
    _guard_attempts(request, "register")
    try:
        user = register_user(payload.username, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    set_session_cookie(response, create_auth_session(user.id))
    return AuthUserResponse(id=user.id, username=user.username)


@router.post("/login", response_model=AuthUserResponse)
async def login(payload: LoginRequest, request: Request, response: Response) -> AuthUserResponse:
    _guard_attempts(request, "login", username=payload.username)
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    set_session_cookie(response, create_auth_session(user.id))
    return AuthUserResponse(id=user.id, username=user.username)


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: Request, response: Response) -> LogoutResponse:
    revoke_auth_session(request.cookies.get(SESSION_COOKIE_NAME))
    clear_session_cookie(response)
    return LogoutResponse()


@router.get("/me", response_model=AuthUserResponse)
async def me(request: Request) -> AuthUserResponse:
    user_id = resolve_user_id_strict(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not signed in")
    user = get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return AuthUserResponse(id=user.id, username=user.username)


def _guard_attempts(request: Request, kind: str, username: str | None = None) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = f"{kind}:{client_ip}"
    if username:
        key = f"{key}:{username.strip().lower()}"
    if not auth_attempt_allowed(key):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")
