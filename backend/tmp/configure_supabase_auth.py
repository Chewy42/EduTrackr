import json
import os
import pathlib
import sys
from typing import List

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def extract_project_ref(supabase_url: str) -> str:
    cleaned = supabase_url.replace("https://", "").replace("http://", "")
    parts = cleaned.split('.')
    if not parts or len(parts[0]) == 0:
        raise SystemExit("Unable to derive project ref from SUPABASE_URL")
    return parts[0]


def infer_site_urls() -> tuple[str, List[str]]:
    site_url = os.getenv("PROD_SERVER_URL") or os.getenv("DEV_SERVER_URL") or "http://localhost:5173"
    redirect_raw = os.getenv("SUPABASE_AUTH_ADDITIONAL_REDIRECTS", "")
    redirects = [url.strip() for url in redirect_raw.split(',') if url.strip()]
    if site_url not in redirects:
        redirects.append(site_url)
    return site_url, redirects


def patch_auth_config() -> None:
    supabase_url = require_env("SUPABASE_URL")
    access_token = require_env("SUPABASE_ACCESS_TOKEN")
    project_ref = extract_project_ref(supabase_url)
    site_url, redirects = infer_site_urls()

    endpoint = f"https://api.supabase.com/v1/projects/{project_ref}/config/auth"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "site_url": site_url,
        "additional_redirect_urls": redirects,
        "mailer_autoconfirm": False,
        "mailer_allow_unverified_email_sign_ins": False,
        "external_email_enabled": True,
    }

    response = requests.patch(endpoint, headers=headers, json=payload, timeout=30)
    try:
        body = response.json()
        formatted = json.dumps(body, indent=2)
    except ValueError:
        formatted = response.text

    print(f"Auth config patch status: {response.status_code}")
    print(formatted)
    if response.status_code >= 300:
        raise SystemExit("Failed to update Supabase auth settings")


if __name__ == "__main__":
    patch_auth_config()
