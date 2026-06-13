from fastapi import APIRouter, Request
from dependencies import get_quota

router = APIRouter(prefix="/api/billing", tags=["billing"])

@router.get("/quota")
async def get_quota_endpoint(request: Request):
    return await get_quota(request)

@router.get("/subscription")
async def get_subscription():
    return None

@router.post("/checkout")
async def create_checkout(plan: str):
    return {"checkout_url": "http://localhost:5173"}

@router.post("/portal")
async def create_portal():
    return {"portal_url": "http://localhost:5173"}
