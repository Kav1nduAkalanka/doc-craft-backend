from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import supabase
from dependencies import get_me

router = APIRouter(prefix="/api/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/users", tags=["users"])

class AuthReq(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(req: AuthReq):
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        res = supabase.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password
        })
        
        user_plan = "free"
        try:
            user_row = supabase.table("users").select("plan").eq("id", res.user.id).single().execute()
            if user_row.data:
                user_plan = user_row.data.get("plan", "free")
        except Exception:
            pass
            
        user_data = {
            "user_id": res.user.id,
            "email": res.user.email,
            "auth_provider": "email",
            "plan": user_plan
        }
        
        return {
            "access_token": res.session.access_token,
            "token_type": "bearer",
            "expires_in": res.session.expires_in,
            "user": user_data
        }
    except Exception as e:
        print(f"Login Error Details: {str(e)}")
        return JSONResponse(status_code=401, content={"error": "auth_error", "message": str(e)})

@router.post("/register")
async def register(req: AuthReq):
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not configured")
            
        res = supabase.auth.sign_up({
            "email": req.email,
            "password": req.password
        })
        
        user_id = res.user.id if res.user else "pending"
        
        if res.user:
            # Create user in public.users table so foreign keys (like documents) don't fail
            try:
                supabase.table("users").upsert({
                    "id": user_id,
                    "email": req.email,
                    "auth_provider": "email",
                    "plan": "free"
                }).execute()
            except Exception as insert_err:
                print(f"Failed to insert into public.users: {insert_err}")
                
        return {
            "user_id": user_id,
            "email": req.email,
            "auth_provider": "email",
            "created_at": res.user.created_at if res.user else ""
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": "registration_error", "message": str(e)})

@router.post("/logout")
async def logout():
    try:
        if supabase:
            supabase.auth.sign_out()
    except Exception:
        pass
    return {"message": "Logged out successfully"}

@users_router.get("/me")
async def get_me_endpoint(request: Request):
    return await get_me(request)
