from fastapi import APIRouter, Query, HTTPException
from typing import Any, Literal, Optional
from pydantic import BaseModel
from datetime import date, datetime

from backend.app.finance.finance_service import (
    add_transaction, 
    get_transactions, 
    get_summary,
    update_transaction,
    add_recurring_template,
    create_recurring_transaction,
    get_categories,
    get_recurring_templates,
    delete_recurring_template,
    get_forecast,
)

router = APIRouter()

class TransactionCreate(BaseModel):
    type: str
    amount: float
    category: str
    description: Optional[str] = ""
    date: Optional[str] = None
    is_recurring: Optional[bool] = False
    currency: Optional[str] = None
    frequency: Literal["weekly", "monthly", "yearly"] = "monthly"

class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None

class RecurringTemplateCreate(BaseModel):
    type: str
    amount: float
    category: str
    description: Optional[str] = ""
    day_of_month: Optional[int] = None
    currency: Optional[str] = None
    frequency: Literal["weekly", "monthly", "yearly"] = "monthly"
    day_of_week: Optional[int] = None
    month_of_year: Optional[int] = None

@router.post("/transactions")
async def api_add_transaction(txn: TransactionCreate):
    try:
        txn_date = txn.date if txn.date else date.today().strftime("%Y-%m-%d")
        result = add_transaction(
            type=txn.type,
            amount=txn.amount,
            category=txn.category,
            description=txn.description,
            transaction_date=txn_date,
            currency=txn.currency,
        )
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
            
        if txn.is_recurring:
            try:
                dt_obj = datetime.strptime(txn_date, "%Y-%m-%d")
                day_of_month = dt_obj.day if txn.frequency in {"monthly", "yearly"} else None
                add_recurring_template(
                    type=txn.type,
                    amount=txn.amount,
                    category=txn.category,
                    description=txn.description,
                    day_of_month=day_of_month,
                    currency=txn.currency,
                    frequency=txn.frequency,
                    day_of_week=dt_obj.weekday() if txn.frequency == "weekly" else None,
                    month_of_year=dt_obj.month if txn.frequency == "yearly" else None,
                )
            except Exception as e:
                result["warning"] = f"Failed to save recurring template: {str(e)}"
                
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions")
async def api_get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None
):
    try:
        # Validate date formats before invoking service
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            datetime.strptime(end_date, "%Y-%m-%d")
            
        return get_transactions(start_date, end_date, category)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(ve)}. Use YYYY-MM-DD.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def api_get_categories():
    try:
        return get_categories()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def api_get_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    try:
        # Validate date formats before invoking service
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            datetime.strptime(end_date, "%Y-%m-%d")
            
        return get_summary(start_date, end_date)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(ve)}. Use YYYY-MM-DD.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast")
async def api_get_forecast(
    months: int = Query(default=3, ge=1, le=24),
    start_date: Optional[str] = None,
):
    try:
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
        return get_forecast(months=months, start_date=start_date)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/transactions/{transaction_id}")
async def api_delete_transaction(transaction_id: int):
    try:
        from backend.app.finance.finance_service import delete_transaction
        result = delete_transaction(transaction_id)
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Recurring Templates Endpoints ──────────────────────────────────────────

@router.get("/recurring")
async def api_get_recurring_templates():
    try:
        return get_recurring_templates()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recurring")
async def api_add_recurring_template(template: RecurringTemplateCreate):
    try:
        result = add_recurring_template(
            type=template.type,
            amount=template.amount,
            category=template.category,
            description=template.description,
            day_of_month=template.day_of_month,
            currency=template.currency,
            frequency=template.frequency,
            day_of_week=template.day_of_week,
            month_of_year=template.month_of_year,
        )
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/recurring/{template_id}")
async def api_delete_recurring_template(template_id: int):
    try:
        result = delete_recurring_template(template_id)
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
