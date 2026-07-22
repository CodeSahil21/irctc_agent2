from __future__ import annotations
from typing import Optional
import jwt


def verify_jwt(token: str, secret: str, algorithm: str = "HS256") -> dict:
    return jwt.decode(token, secret, algorithms=[algorithm])


def extract_user_from_token(token: Optional[str], secret: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (email, name) from a JWT access_token, or (None, None) on failure."""
    if not token:
        return None, None
    try:
        payload = verify_jwt(token, secret)
        return payload.get("email"), payload.get("name")
    except Exception:
        return None, None