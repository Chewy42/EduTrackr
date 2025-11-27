import os
from typing import Any, Dict

import requests

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
# Prefer SERVICE_ROLE_KEY for backend admin access, fallback to ACCESS_TOKEN
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ACCESS_TOKEN")


def supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY and SUPABASE_SERVICE_KEY)


def ensure_supabase_env() -> None:
    if not supabase_configured():
        missing = []
        if not SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not SUPABASE_ANON_KEY:
            missing.append("SUPABASE_ANON_KEY")
        if not SUPABASE_SERVICE_KEY:
            missing.append("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ACCESS_TOKEN")
        raise RuntimeError(f"Missing Supabase configuration: {', '.join(missing)}")


def supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_ANON_KEY or "",
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }


def supabase_request(method: str, path: str, **kwargs: Any) -> requests.Response:
    ensure_supabase_env()
    url = f"{SUPABASE_URL}{path}"
    headers = kwargs.pop("headers", {})
    merged_headers = {**supabase_headers(), **headers}
    timeout = kwargs.pop("timeout", 30)
    return requests.request(
        method=method.upper(),
        url=url,
        headers=merged_headers,
        timeout=timeout,
        **kwargs,
    )
