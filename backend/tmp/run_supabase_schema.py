import json
import os
import pathlib
import sys
import textwrap
from typing import Tuple

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "app" / "db" / "schema.sql"


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


def run_sql(sql: str) -> Tuple[int, str]:
    supabase_url = require_env("SUPABASE_URL")
    access_token = require_env("SUPABASE_ACCESS_TOKEN")
    project_ref = extract_project_ref(supabase_url)

    endpoint = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"query": sql}

    response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
    try:
        body = response.json()
        body_text = json.dumps(body, indent=2)
    except ValueError:
        body_text = response.text
    return response.status_code, body_text


def main() -> None:
    if not SCHEMA_PATH.exists():
        raise SystemExit(f"Schema file not found: {SCHEMA_PATH}")
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    status, body = run_sql(sql)
    print(f"Supabase responded with status {status}")
    print(body)
    if status >= 300:
        raise SystemExit("Failed to apply schema. See response above.")


if __name__ == "__main__":
    main()
