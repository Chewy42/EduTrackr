import json
import os
import sys
from typing import Any, Dict, Optional

import requests


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def supabase_admin_headers(service_key: str) -> Dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }


def find_user_id_by_email(supabase_url: str, service_key: str, email: str) -> Optional[str]:
    endpoint = f"{supabase_url.rstrip('/')}/auth/v1/admin/users"
    response = requests.get(
        endpoint,
        headers=supabase_admin_headers(service_key),
        params={"email": email},
        timeout=30,
    )

    if response.status_code == 404:
        return None

    if response.status_code >= 400:
        try:
            body: Any = response.json()
            body_text = json.dumps(body)
        except ValueError:
            body_text = response.text
        raise SystemExit(f"Failed to look up user: {response.status_code} {body_text}")

    try:
        data: Any = response.json()
    except ValueError:
        raise SystemExit("Supabase returned non-JSON response while looking up user")

    if isinstance(data, dict):
        if "id" in data and isinstance(data["id"], str):
            return data["id"]
        user: Any = data.get("user")
        if isinstance(user, dict) and isinstance(user.get("id"), str):
            return user["id"]
        users: Any = data.get("users")
        if isinstance(users, list) and users and isinstance(users[0], dict):
            user0: Dict[str, Any] = users[0]
            user0_id = user0.get("id")
            if isinstance(user0_id, str):
                return user0_id

    raise SystemExit("Unable to extract user id from Supabase response")


def delete_user_by_email(email: str) -> None:
    email_normalized = email.strip()
    if not email_normalized:
        raise SystemExit("Provide an email address to delete")

    supabase_url = require_env("SUPABASE_URL")
    service_key = require_env("SUPABASE_ACCESS_TOKEN")

    user_id = find_user_id_by_email(supabase_url, service_key, email_normalized)
    if not user_id:
        print(f"No Supabase user found for email: {email_normalized}")
        return

    endpoint = f"{supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"
    response = requests.delete(
        endpoint,
        headers=supabase_admin_headers(service_key),
        timeout=30,
    )

    if response.status_code >= 400:
        try:
            body: Any = response.json()
            body_text = json.dumps(body)
        except ValueError:
            body_text = response.text
        raise SystemExit(f"Failed to delete user: {response.status_code} {body_text}")

    print(f"Deleted Supabase user {user_id} for email {email_normalized}")


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit(f"Usage: {argv[0]} <email>")
    delete_user_by_email(argv[1])


if __name__ == "__main__":
    main(sys.argv)

