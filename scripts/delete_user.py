import json
import os
import sys
import requests
from typing import Any, Dict, List, Optional


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
        "Prefer": "return=representation",
    }


def delete_storage_files(supabase_url: str, service_key: str, user_id: str) -> None:
    """Deletes files associated with the user from Supabase Storage."""
    # 1. Get all evaluations to find storage paths
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/program_evaluations"
    resp = requests.get(
        endpoint,
        headers=supabase_admin_headers(service_key),
        params={"user_id": f"eq.{user_id}", "select": "storage_path,storage_bucket"}
    )
    
    if resp.status_code != 200:
        print(f"Warning: Could not fetch evaluations for storage cleanup: {resp.text}")
        return

    evals = resp.json()
    count = 0
    for ev in evals:
        bucket = ev.get("storage_bucket", "program-evaluations")
        path = ev.get("storage_path")
        if bucket and path:
            # Delete object
            del_endpoint = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{path}"
            del_resp = requests.delete(del_endpoint, headers=supabase_admin_headers(service_key))
            if del_resp.status_code in (200, 204):
                print(f"Deleted storage file: {bucket}/{path}")
                count += 1
            else:
                print(f"Failed to delete storage file {bucket}/{path}: {del_resp.text}")
    
    if count > 0:
        print(f"Cleaned up {count} storage files.")


def delete_app_user_data(supabase_url: str, service_key: str, email: str) -> None:
    """Deletes user data from the application database (app_users table)."""
    # 1. Find user in app_users
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/app_users"
    resp = requests.get(
        endpoint,
        headers=supabase_admin_headers(service_key),
        params={"email": f"eq.{email}", "select": "id"}
    )
    
    if resp.status_code != 200:
        print(f"Failed to query app_users: {resp.text}")
        return

    users = resp.json()
    if not users:
        print(f"No app_user found in database for {email} (already cleaned up?)")
        return

    user_id = users[0]["id"]
    print(f"Found app_user record: {user_id}")

    # 2. Delete storage files first (while we still have the records to know paths)
    try:
        delete_storage_files(supabase_url, service_key, user_id)
    except Exception as e:
        print(f"Error deleting storage files: {e}")

    # 3. Delete app_user record (cascades to other tables)
    del_endpoint = f"{supabase_url.rstrip('/')}/rest/v1/app_users"
    del_resp = requests.delete(
        del_endpoint,
        headers=supabase_admin_headers(service_key),
        params={"id": f"eq.{user_id}"}
    )
    if del_resp.status_code in (200, 204):
        print(f"Deleted app_user record {user_id} (cascaded to preferences, evaluations, etc.)")
    else:
        print(f"Failed to delete app_user record: {del_resp.text}")


def find_auth_user_id_by_email(supabase_url: str, service_key: str, email: str) -> Optional[str]:
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
            body = response.json()
            print(f"Auth lookup error body: {body}")
        except:
            pass
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    if isinstance(data, dict):
        if "id" in data and isinstance(data["id"], str):
            return data["id"]
        user = data.get("user")
        if isinstance(user, dict) and isinstance(user.get("id"), str):
            return user["id"]
        users = data.get("users")
        if isinstance(users, list) and users and isinstance(users[0], dict):
            user0 = users[0]
            return user0.get("id")

    return None


def delete_auth_user(supabase_url: str, service_key: str, email: str) -> None:
    user_id = find_auth_user_id_by_email(supabase_url, service_key, email)
    if not user_id:
        print(f"No Supabase Auth user found for email: {email}")
        return

    endpoint = f"{supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"
    response = requests.delete(
        endpoint,
        headers=supabase_admin_headers(service_key),
        timeout=30,
    )

    if response.status_code >= 400:
        print(f"Failed to delete auth user: {response.status_code} {response.text}")
    else:
        print(f"Deleted Supabase Auth user {user_id}")


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit(f"Usage: {argv[0]} <email>")
    
    email = argv[1].strip()
    if not email:
        raise SystemExit("Provide an email address to delete")

    supabase_url = require_env("SUPABASE_URL")
    # Prioritize SERVICE_ROLE_KEY, fallback to ACCESS_TOKEN for back-compat
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ACCESS_TOKEN")
    if not service_key:
        raise SystemExit("Missing required environment variable: SUPABASE_SERVICE_ROLE_KEY")

    print(f"--- Cleaning up data for {email} ---")
    
    # 1. Clean up Application Data (DB + Storage)
    delete_app_user_data(supabase_url, service_key, email)
    
    # 2. Clean up Auth User
    delete_auth_user(supabase_url, service_key, email)
    
    print("--- Done ---")


if __name__ == "__main__":
    main(sys.argv)

