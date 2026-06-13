import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: credentials missing")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get all auth users
try:
    auth_users_response = supabase.auth.admin.list_users()
    auth_users = auth_users_response.users
    print(f"Found {len(auth_users)} auth users")
    
    for u in auth_users:
        user_data = {
            "id": u.id,
            "email": u.email,
            "plan": u.user_metadata.get("plan", "free") if u.user_metadata else "free"
        }
        # Insert or update
        res = supabase.table("users").upsert(user_data).execute()
        print(f"Synced {u.email} to public.users")
        
except Exception as e:
    print("Error syncing users:", e)
