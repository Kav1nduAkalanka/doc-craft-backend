from fastapi import Request, HTTPException
from database import supabase
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

async def get_me(request: Request):
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not configured")
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token")
            
        token = auth_header.split(" ")[1]
        
        # Get user from Supabase using the provided token
        res = supabase.auth.get_user(token)
        
        if not res or not res.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_id = res.user.id
        email = res.user.email
        
        # Read plan from public.users table (where it actually lives)
        plan = "free"
        try:
            user_row = supabase.table("users").select("plan").eq("id", user_id).single().execute()
            if user_row.data:
                plan = user_row.data.get("plan", "free")
            else:
                raise Exception("User not found in public.users")
        except Exception:
            # Fallback: Auto-create the user in public.users to fix existing accounts
            try:
                supabase.table("users").upsert({
                    "id": user_id,
                    "email": email,
                    "auth_provider": "email",
                    "plan": "free"
                }).execute()
            except Exception:
                pass
            
        return {
            "user_id": user_id,
            "email": email,
            "auth_provider": "email",
            "plan": plan
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

async def get_quota(request: Request):
    user_data = await get_me(request)
    plan = user_data.get("plan", "free")
    user_id = user_data["user_id"]
    
    try:
        # Count exported documents for the user to determine usage
        res = supabase.table("documents").select("id", count="exact").eq("user_id", user_id).eq("status", "exported").execute()
        count = res.count if res.count is not None else 0
        
        limit = 3 if plan == "free" else 9999
        remaining = max(0, limit - count)
        
        return {
            "plan": plan,
            "used_today": count,
            "daily_limit": limit,
            "remaining": remaining
        }
    except Exception:
        return {
            "plan": plan,
            "used_today": 0,
            "daily_limit": 3 if plan == "free" else 9999,
            "remaining": 3 if plan == "free" else 9999
        }
