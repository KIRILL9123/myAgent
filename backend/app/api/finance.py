from fastapi import APIRouter, Query, HTTPException
from typing import Any, Optional
from pydantic import BaseModel
from datetime import date, datetime

from backend.app.finance.finance_service import (
    add_transaction, 
    get_transactions, 
    get_summary,
    add_recurring_template,
    get_recurring_templates,
    delete_recurring_template
)

router = APIRouter()

class TransactionCreate(BaseModel):
    type: str
    amount: float
    category: str
    description: Optional[str] = ""
    date: Optional[str] = None
    is_recurring: Optional[bool] = False

class RecurringTemplateCreate(BaseModel):
    type: str
    amount: float
    category: str
    description: Optional[str] = ""
    day_of_month: int

@router.post("/transactions")
async def api_add_transaction(txn: TransactionCreate):
    txn_date = txn.date if txn.date else date.today().strftime("%Y-%m-%d")
    result = add_transaction(
        type=txn.type,
        amount=txn.amount,
        category=txn.category,
        description=txn.description,
        transaction_date=txn_date
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    if txn.is_recurring:
        try:
            dt_obj = datetime.strptime(txn_date, "%Y-%m-%d")
            day_of_month = dt_obj.day
            add_recurring_template(
                type=txn.type,
                amount=txn.amount,
                category=txn.category,
                description=txn.description,
                day_of_month=day_of_month
            )
        except Exception as e:
            result["warning"] = f"Failed to save recurring template: {str(e)}"
            
    return result

@router.get("/transactions")
async def api_get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None
):
    return get_transactions(start_date, end_date, category)

@router.get("/summary")
async def api_get_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    return get_summary(start_date, end_date)

@router.delete("/transactions/{transaction_id}")
async def api_delete_transaction(transaction_id: int):
    from backend.app.finance.finance_service import delete_transaction
    result = delete_transaction(transaction_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

# ─── Recurring Templates Endpoints ──────────────────────────────────────────

@router.get("/recurring")
async def api_get_recurring_templates():
    return get_recurring_templates()

@router.post("/recurring")
async def api_add_recurring_template(template: RecurringTemplateCreate):
    result = add_recurring_template(
        type=template.type,
        amount=template.amount,
        category=template.category,
        description=template.description,
        day_of_month=template.day_of_month
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.delete("/recurring/{template_id}")
async def api_delete_recurring_template(template_id: int):
    result = delete_recurring_template(template_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
