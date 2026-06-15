from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from app.core.config import get_settings


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)[:128]


def code_challenge_s256(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def oauth_state_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=10)


def build_authorize_url(state: str, code_challenge: str) -> str:
    settings = get_settings()
    params = {
        "response_type": "code",
        "client_id": settings.lichess_client_id,
        "redirect_uri": settings.lichess_redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if settings.lichess_scopes:
        params["scope"] = settings.lichess_scopes
    return f"{settings.lichess_oauth_authorize_url}?{urlencode(params)}"
