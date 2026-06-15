from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet


def _fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_token(token: str, secret: str) -> str:
    return Fernet(_fernet_key(secret)).encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(token_encrypted: str, secret: str) -> str:
    return Fernet(_fernet_key(secret)).decrypt(token_encrypted.encode("utf-8")).decode("utf-8")
