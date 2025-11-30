#!/usr/bin/env python3
"""
Apply the scheduling_preferences migration to Supabase.
Run from backend directory: python tmp/apply_scheduling_migration.py
"""
import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.supabase_client import SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY
import requests

def run_sql(sql: str) -> dict:
    """Execute SQL via Supabase's REST SQL endpoint (requires service role key)."""
    # Supabase doesn't have a direct SQL endpoint via REST, but we can use the
    # postgres connection or check if the table exists and create via RPC.
    # For now, let's just try inserting to see if the table exists.
    
    # Actually, let's use the PostgREST endpoint to check if table exists
    url = f"{SUPABASE_URL}/rest/v1/scheduling_preferences?select=user_id&limit=1"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    resp = requests.get(url, headers=headers, timeout=10)
    return {"status": resp.status_code, "body": resp.text}


if __name__ == "__main__":
    print(f"SUPABASE_URL: {SUPABASE_URL}")
    print(f"Service key present: {bool(SUPABASE_SERVICE_KEY)}")
    
    result = run_sql("")
    print(f"Table check result: {result}")
    
    if result["status"] == 404 and "scheduling_preferences" in result["body"]:
        print("\n❌ Table 'scheduling_preferences' does NOT exist in Supabase!")
        print("\nYou need to run this SQL in the Supabase Dashboard SQL Editor:")
        print("-" * 60)
        
        with open("app/db/migrations/add_scheduling_preferences.sql") as f:
            print(f.read())
        
        print("-" * 60)
        print("\nGo to: https://supabase.com/dashboard → Your Project → SQL Editor")
        print("Paste the above SQL and click 'Run'")
    elif result["status"] == 200:
        print("\n✅ Table 'scheduling_preferences' exists!")
    else:
        print(f"\nUnexpected response: {result}")
