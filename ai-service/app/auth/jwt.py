from __future__ import annotations

import jwt


def verify_jwt(token: str, secret: str, algorithm: str = "HS256") -> dict:
    return jwt.decode(token, secret, algorithms=[algorithm])