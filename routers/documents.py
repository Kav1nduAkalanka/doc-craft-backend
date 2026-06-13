from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
from database import supabase
from dependencies import get_me, get_quota

router = APIRouter(prefix="/api/documents", tags=["documents"])
templates_router = APIRouter(prefix="/api/templates", tags=["templates"])

class GenerateDocumentRequest(BaseModel):
    session_id: str
    document_type: str
    template_id: str
    accent_color: str
    data: Dict[str, Any]

@router.post("/generate")
async def generate_document(req: GenerateDocumentRequest, request: Request):
    try:
        user_data = await get_me(request)
        user_id = user_data["user_id"]
        
        doc_data = {
            "user_id": user_id,
            "document_type": req.document_type,
            "document_number": req.data.get("invoiceNumber", req.data.get("quoteNumber", req.data.get("receiptNumber", ""))),
            "client_name": req.data.get("clientName", ""),
            "template_id": req.template_id,
            "accent_color": req.accent_color,
            "status": "draft"
        }
        res = supabase.table("documents").insert(doc_data).execute()
        doc_id = res.data[0]["id"]
        
        return {
            "document_id": doc_id,
            "preview_html": "", 
            "layout_state": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class LayoutUpdateRequest(BaseModel):
    section: str
    controls: Dict[str, Any]

@router.patch("/{document_id}/layout")
async def update_layout(document_id: str, req: LayoutUpdateRequest):
    return {
        "document_id": document_id,
        "updated_preview_html": "",
        "layout_state": {}
    }

class ContentUpdateRequest(BaseModel):
    slot: str
    value: Any

@router.patch("/{document_id}/content")
async def update_content(document_id: str, req: ContentUpdateRequest):
    return {
        "document_id": document_id,
        "updated_slot": req.slot,
        "updated_preview_html": ""
    }

@router.post("/{document_id}/export/pdf")
async def export_pdf(document_id: str, request: Request):
    try:
        quota = await get_quota(request)
        if quota["plan"] == "free" and quota["remaining"] <= 0:
            raise HTTPException(status_code=403, detail="Daily limit reached. Please upgrade to Pro.")

        if supabase:
            existing = supabase.table("documents").select("status").eq("id", document_id).single().execute()
            if existing.data and existing.data.get("status") != "exported":
                supabase.table("documents").update({
                    "status": "exported",
                    "exported_at": datetime.utcnow().isoformat() + "Z"
                }).eq("id", document_id).execute()
        return {"message": "Export tracked"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export tracking failed: {str(e)}")

@templates_router.get("")
async def get_templates(document_type: str = "invoice"):
    templates = [
        {"template_id": f"{document_type[:3]}_standard", "name": f"Standard {document_type.capitalize()}", "thumbnail_url": "", "tier": "free"},
        {"template_id": f"{document_type[:3]}_minimal", "name": f"Minimal {document_type.capitalize()}", "thumbnail_url": "", "tier": "free"},
        {"template_id": f"{document_type[:3]}_classic", "name": f"Classic {document_type.capitalize()}", "thumbnail_url": "", "tier": "pro"},
    ]
    return {"templates": templates}
