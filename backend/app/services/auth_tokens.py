import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt as pyjwt
from flask import request

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


def issue_app_token(email: str, stay_logged_in: bool = False) -> str:
    ttl = timedelta(days=30 if stay_logged_in else 7)
    payload = {
        "email": email,
        "exp": datetime.now(timezone.utc) + ttl,
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_app_token(token: str) -> Dict[str, Any]:
    return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def _extract_token_from_request() -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    query_token = request.args.get("token", "")
    if query_token:
        return query_token
    raise pyjwt.InvalidTokenError("Missing bearer token")


def decode_app_token_from_request() -> Dict[str, Any]:
    token = _extract_token_from_request()
    return decode_app_token(token)
