import os
import sys
import requests

def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value

def main():
    supabase_url = require_env("SUPABASE_URL").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ACCESS_TOKEN")
    
    if not service_key:
        print("Error: SUPABASE_SERVICE_ROLE_KEY is required.")
        sys.exit(1)

    bucket_id = "program-evaluations"
    
    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "apikey": service_key
    }

    # Check if bucket exists
    print(f"Checking bucket '{bucket_id}'...")
    resp = requests.get(f"{supabase_url}/storage/v1/bucket/{bucket_id}", headers=headers)
    
    if resp.status_code == 200:
        print(f"Bucket '{bucket_id}' already exists.")
    else:
        print(f"Bucket '{bucket_id}' not found (Status {resp.status_code}). Creating...")
        # Create bucket
        payload = {
            "id": bucket_id,
            "name": bucket_id,
            "public": False,  # Private bucket for sensitive data
            "file_size_limit": 5242880, # 5MB
            "allowed_mime_types": ["application/pdf"]
        }
        create_resp = requests.post(f"{supabase_url}/storage/v1/bucket", headers=headers, json=payload)
        
        if create_resp.status_code in (200, 201):
            print(f"Successfully created bucket '{bucket_id}'.")
        else:
            print(f"Failed to create bucket: {create_resp.status_code} {create_resp.text}")
            sys.exit(1)

if __name__ == "__main__":
    main()
