from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/revenue-risk", tags=["Revenue Risk"])

class RiskEventSchema(BaseModel):
    id: str
    merchant_id: str
    event_type: str
    severity: str
    status: str
    amount: float
    currency: str
    customer_id: Optional[str] = None
    customer_email: Optional[str] = None
    risk_score: float
    detected_at: str

@router.get("/", response_model=List[RiskEventSchema])
async def list_risk_events(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None)
):
    """Retrieve filtered revenue risk events."""
    # In production, queries Supabase with user's JWT for RLS enforcement
    sample_data = [
        {
            "id": "risk_01H9A123",
            "merchant_id": "merchant_acme_01",
            "event_type": "failed_payment",
            "severity": "high",
            "status": "in_recovery",
            "amount": 2450.00,
            "currency": "USD",
            "customer_id": "cust_9921",
            "customer_email": "sarah.j@enterprise.com",
            "risk_score": 0.89,
            "detected_at": "2026-08-21T14:32:00Z"
        },
        {
            "id": "risk_01H9A124",
            "merchant_id": "merchant_acme_01",
            "event_type": "abandoned_cart",
            "severity": "medium",
            "status": "open",
            "amount": 890.00,
            "currency": "USD",
            "customer_id": "cust_4410",
            "customer_email": "alex.m@techcorp.io",
            "risk_score": 0.65,
            "detected_at": "2026-08-21T16:05:00Z"
        }
    ]
    if status:
        sample_data = [d for d in sample_data if d["status"] == status]
    if severity:
        sample_data = [d for d in sample_data if d["severity"] == severity]
    return sample_data

@router.post("/{event_id}/trigger-recovery")
async def trigger_recovery(event_id: str):
    """Trigger autonomous recovery protocol for a given risk event."""
    return {
        "status": "success",
        "event_id": event_id,
        "action_taken": "smart_retry_schedule",
        "message": f"Autonomous recovery triggered for event {event_id}"
    }
