from fastapi import APIRouter, Query, HTTPException
from typing import Any, Optional
from pydantic import BaseModel
from datetime import date

from backend.app.finance.finance_service import add_transaction, get_transactions, get_summary

router = APIRouter()

class TransactionCreate(BaseModel):
    type: str
    amount: float
    category: str
    description: Optional[str] = ""
    date: Optional[str] = None

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
