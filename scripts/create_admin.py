import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
# To create a user with auto-confirm and app_metadata, the service role key is required.
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in your .env file.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_admin(email, password):
    try:
        # We use the admin API to bypass email confirmation and assign metadata
        # This requires the SUPABASE_KEY to be a Service Role key.
        res = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "app_metadata": {"role": "admin"},
            "user_metadata": {"plan": "pro"}
        })
        print(f"✅ Admin account created successfully for {email}!")
    except Exception as e:
        print(f"❌ Failed to create admin: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    create_admin(email, password)
