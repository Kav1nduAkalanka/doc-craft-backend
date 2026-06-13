import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
import google.generativeai as genai

from dependencies import limiter

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Document Schemas mapping
SCHEMAS = {
    "invoice": {
        "required": ["businessName", "invoiceNumber", "issueDate", "dueDate", "senderEmail", "clientName", "lineItems"],
        "optional": ["senderAddress", "clientAddress", "taxRate", "notesAndTerms", "bankName", "accountNumber", "accountName"]
    },
    "quotation": {
        "required": ["businessName", "quoteNumber", "issueDate", "validUntil", "clientName", "lineItems"],
        "optional": ["senderAddress", "clientAddress", "notesAndTerms", "projectScope", "estimatedDelivery", "paymentTerms"]
    },
    "receipt": {
        "required": ["businessName", "receiptNumber", "issueDate", "clientName", "lineItems"],
        "optional": ["senderAddress", "clientAddress", "taxRate", "notesAndTerms", "bankName", "accountNumber", "accountName"]
    },
    "proposal": {
        "required": ["businessName", "proposalNumber", "issueDate", "validUntil", "clientName", "lineItems"],
        "optional": ["senderAddress", "clientAddress", "notesAndTerms", "projectScope", "estimatedDelivery", "paymentTerms"]
    },
    "purchase_order": {
        "required": ["businessName", "poNumber", "issueDate", "clientName", "lineItems"],
        "optional": ["senderAddress", "clientAddress", "notesAndTerms", "projectScope", "estimatedDelivery", "paymentTerms"]
    }
}

QUESTIONS = {
    "businessName": "What is your business name?",
    "invoiceNumber": "What invoice number should we use?",
    "issueDate": "What's the issue date?",
    "dueDate": "When is payment due?",
    "senderEmail": "What's your business email?",
    "clientName": "Who are you billing?",
    "lineItems": "Please list the items or services (e.g., 'Web Design, qty 1, price 1500').",
    "senderAddress": "What's your business address?",
    "clientAddress": "What's the client's address?",
    "taxRate": "What is the tax rate?",
    "notesAndTerms": "Any notes or payment terms?",
    "quoteNumber": "What quote number should we use?",
    "validUntil": "Until when is this valid?",
    "notes": "Any additional notes?",
    "receiptNumber": "What receipt number should we use?",
    "proposalNumber": "What proposal number should we use?",
    "poNumber": "What purchase order (PO) number should we use?",
    "bankName": "What is the receiving bank name?",
    "accountNumber": "What is the account number?",
    "accountName": "What is the account holder's name?",
    "projectScope": "What is the project or scope title? (e.g. Website Redesign)",
    "estimatedDelivery": "What is the estimated delivery time? (e.g. 4 weeks)",
    "paymentTerms": "What are the payment terms? (e.g. 50% upfront)"
}

class SessionStartReq(BaseModel):
    document_type: str

class ChatReq(BaseModel):
    session_id: str
    document_type: str
    current_field: str
    message: str = Field(..., max_length=1000)
    conversation_history: List[Dict[str, str]]
    collected_slots: Optional[Dict[str, Any]] = {}

class CorrectionConfirmReq(BaseModel):
    session_id: str
    field: str
    original_value: str
    suggested_value: str
    accept: bool
    collected_slots: Optional[Dict[str, Any]] = {}

class MissingFieldsReq(BaseModel):
    session_id: str
    document_type: str
    collected_slots: Optional[Dict[str, Any]] = {}

class SummaryReq(BaseModel):
    session_id: str
    collected_slots: Optional[Dict[str, Any]] = {}

@router.post("/session/start")
@limiter.limit("10/minute")
async def start_session(request: Request, req: SessionStartReq):
    doc_type = req.document_type
    schema = SCHEMAS.get(doc_type, SCHEMAS["invoice"])
    
    first_field = schema["required"][0]
    
    return {
        "session_id": str(uuid.uuid4()),
        "document_type": doc_type,
        "schema_summary": {
            "total_fields": len(schema["required"]) + len(schema["optional"]),
            "required_fields": len(schema["required"]),
            "optional_fields": len(schema["optional"]),
            "computed_fields": ["subtotal", "totalDue"],
            "required_keys": schema["required"]
        },
        "collected_slots": {},
        "pending_required": schema["required"],
        "pending_optional": schema["optional"],
        "opening_message": f"Let's build your {doc_type}! {QUESTIONS.get(first_field)}"
    }

@router.post("/chat")
@limiter.limit("4/minute")
async def chat(request: Request, req: ChatReq):
    doc_type = req.document_type
    schema = SCHEMAS.get(doc_type, SCHEMAS["invoice"])
    all_fields = schema["required"] + schema["optional"]

    today_str = datetime.now().strftime('%Y-%m-%d')
    prompt = f"""
    You are a data extractor for a {doc_type}.
    Today's date is {today_str}. Please resolve relative dates like "today", "tomorrow", or "next week" into actual YYYY-MM-DD format strings.
    The user is either answering a specific question about: "{req.current_field}" or providing multiple details at once.
    User's message: "{req.message}"
    
    Valid fields for this document: {', '.join(all_fields)}
    
    If the user is providing information for 'lineItems', extract an array of objects with 'description', 'quantity' (number), 'unitPrice' (number), and 'total' (number). 
    For other fields, extract a string.
    
    Return ONLY a JSON object with any fields you can confidently extract. If the user's message is a direct answer to the question, map it to "{req.current_field}". Do not include fields you cannot find.
    Format: {{"field_name": value, ...}}
    """
    
    slots = req.collected_slots or {}

    try:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction="You must respond in valid JSON ONLY.")
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0))
        
        extracted_text = response.text
        extracted_text = extracted_text.replace("```json", "").replace("```", "").strip()
        
        start_idx = extracted_text.find('{')
        end_idx = extracted_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            extracted_text = extracted_text[start_idx:end_idx+1]
            
        data = json.loads(extracted_text)
        if isinstance(data, dict):
            for k, v in data.items():
                if v is not None and v != "":
                    slots[k] = v
    except Exception as e:
        error_msg = str(e)
        print(f"LLM Parsing Error: {type(e).__name__} - {error_msg}")
        return {
            "ai_message": f"⚠️ AI Parsing Failed: {error_msg}. Please check your GEMINI_API_KEY in the backend .env file.",
            "current_field": req.current_field,
            "status": "validation_error",
            "collected_slots": slots,
            "pending_required": [f for f in schema["required"] if f not in slots],
            "pending_optional": [f for f in schema["optional"] if f not in slots],
            "ready_to_generate": False,
            "spell_corrections": []
        }

    pending_req = [f for f in schema["required"] if f not in slots]
    pending_opt = [f for f in schema["optional"] if f not in slots]
    
    if pending_req:
        next_field = pending_req[0]
        ai_message = f"Got it. {QUESTIONS.get(next_field)}"
        status = "ok"
    elif pending_opt:
        next_field = pending_opt[0]
        ai_message = f"Got it. (Optional) {QUESTIONS.get(next_field)}"
        status = "ok"
    else:
        next_field = None
        ai_message = "All details collected! Click the **Review** button above to generate your document."
        status = "complete"

    spell_corrections = []

    return {
        "ai_message": ai_message,
        "current_field": next_field,
        "status": status,
        "collected_slots": slots,
        "pending_required": pending_req,
        "pending_optional": pending_opt,
        "ready_to_generate": len(pending_req) == 0,
        "spell_corrections": spell_corrections
    }

@router.post("/correction/confirm")
async def confirm_correction(req: CorrectionConfirmReq):
    slots = req.collected_slots or {}
    if req.accept:
        slots[req.field] = req.suggested_value
    
    return {
        "ai_message": f"Spelling updated to {req.suggested_value}." if req.accept else "Original spelling kept.",
        "next_field": None, # Should be calculated
        "collected_slots": slots,
        "pending_required": []
    }

@router.post("/missing-fields")
async def missing_fields(req: MissingFieldsReq):
    doc_type = req.document_type
    schema = SCHEMAS.get(doc_type, SCHEMAS["invoice"])
    slots = req.collected_slots or {}
    
    pending_req = [{"key": f, "label": f} for f in schema["required"] if f not in slots]
    pending_opt = [{"key": f, "label": f} for f in schema["optional"] if f not in slots]
    
    return {
        "missing_required": pending_req,
        "missing_optional": pending_opt,
        "ready_to_generate": len(pending_req) == 0
    }

@router.post("/summary")
async def summary(req: SummaryReq):
    slots = req.collected_slots or {}
    summary_text = "Here is a summary of your collected data:\n\n"
    for k, v in slots.items():
        summary_text += f"- **{k}**: {v}\n"
        
    return {
        "summary": summary_text,
        "collected_data": slots,
        "ready_to_generate": True
    }
