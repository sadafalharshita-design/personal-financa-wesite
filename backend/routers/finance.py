import re
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from lib.db import db
from lib.security import current_user
from models.wealth import (
    Account, AccountCreate, AccountUpdate, Budget, BudgetUpdate, BulkDeleteInput,
    ContributionInput, DashboardSummary, Goal, GoalCreate, GoalUpdate,
    Transaction, TransactionCreate, TransactionList,
)
from services.finance import baseline_for_user, goal_public, to_paise, to_rupees, transaction_public, utc_now


router = APIRouter(tags=["finance"])


def account_public(doc: dict) -> dict:
    return {**doc, "balance": to_rupees(doc["balance_paise"])}


@router.get("/accounts", response_model=list[Account])
async def list_accounts(user: dict = Depends(current_user)):
    docs = await db.accounts.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", 1).to_list(100)
    return [account_public(doc) for doc in docs]


@router.post("/accounts", response_model=Account, status_code=status.HTTP_201_CREATED)
async def create_account(payload: AccountCreate, user: dict = Depends(current_user)):
    now = utc_now()
    if payload.is_default:
        await db.accounts.update_many({"user_id": user["id"]}, {"$set": {"is_default": False}})
    doc = {
        "id": str(uuid.uuid4()), "user_id": user["id"], "name": payload.name, "type": payload.type,
        "balance_paise": to_paise(payload.balance), "is_default": payload.is_default,
        "created_at": now, "updated_at": now,
    }
    await db.accounts.insert_one(doc)
    return account_public(doc)


@router.put("/accounts/{account_id}", response_model=Account)
async def update_account(account_id: str, payload: AccountUpdate, user: dict = Depends(current_user)):
    doc = await db.accounts.find_one({"id": account_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Account not found")
    if payload.is_default:
        await db.accounts.update_many({"user_id": user["id"]}, {"$set": {"is_default": False}})
    changes = {**payload.model_dump(), "updated_at": utc_now()}
    await db.accounts.update_one({"id": account_id, "user_id": user["id"]}, {"$set": changes})
    doc.update(changes)
    return account_public(doc)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: str, user: dict = Depends(current_user)):
    if await db.transactions.find_one({"account_id": account_id, "user_id": user["id"]}):
        raise HTTPException(status_code=409, detail="Delete or move this account's transactions first")
    result = await db.accounts.delete_one({"id": account_id, "user_id": user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Account not found")


@router.get("/transactions", response_model=TransactionList)
async def list_transactions(
    search: str | None = None, transaction_type: str | None = None, category: str | None = None,
    sort: str = Query(default="newest", pattern="^(newest|oldest|highest)$"),
    user: dict = Depends(current_user),
):
    query: dict = {"user_id": user["id"]}
    if search:
        query["$or"] = [
            {"description": {"$regex": re.escape(search), "$options": "i"}},
            {"merchant": {"$regex": re.escape(search), "$options": "i"}},
        ]
    if transaction_type in {"INCOME", "EXPENSE"}:
        query["type"] = transaction_type
    if category:
        query["category"] = category
    sort_field, direction = ("amount_paise", -1) if sort == "highest" else ("date", 1 if sort == "oldest" else -1)
    total = await db.transactions.count_documents(query)
    docs = await db.transactions.find(query, {"_id": 0}).sort(sort_field, direction).limit(200).to_list(200)
    return TransactionList(items=[transaction_public(doc) for doc in docs], total=total)


async def require_account(account_id: str, user_id: str) -> dict:
    account = await db.accounts.find_one({"id": account_id, "user_id": user_id}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def balance_effect(transaction_type: str, amount_paise: int) -> int:
    return amount_paise if transaction_type == "INCOME" else -amount_paise


@router.post("/transactions", response_model=Transaction, status_code=status.HTTP_201_CREATED)
async def create_transaction(payload: TransactionCreate, user: dict = Depends(current_user)):
    await require_account(payload.account_id, user["id"])
    amount = to_paise(payload.amount)
    now = utc_now()
    doc = {
        **payload.model_dump(exclude={"amount"}), "date": payload.date.isoformat(),
        "amount_paise": amount, "id": str(uuid.uuid4()), "user_id": user["id"],
        "status": "COMPLETED", "created_at": now, "updated_at": now,
    }
    await db.transactions.insert_one(doc)
    try:
        await db.accounts.update_one({"id": payload.account_id, "user_id": user["id"]}, {"$inc": {"balance_paise": balance_effect(payload.type, amount)}})
    except Exception:
        await db.transactions.delete_one({"id": doc["id"]})
        raise
    return transaction_public(doc)


@router.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(transaction_id: str, payload: TransactionCreate, user: dict = Depends(current_user)):
    old = await db.transactions.find_one({"id": transaction_id, "user_id": user["id"]}, {"_id": 0})
    if not old:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await require_account(payload.account_id, user["id"])
    await db.accounts.update_one({"id": old["account_id"]}, {"$inc": {"balance_paise": -balance_effect(old["type"], old["amount_paise"])}})
    amount = to_paise(payload.amount)
    changes = {**payload.model_dump(exclude={"amount"}), "date": payload.date.isoformat(), "amount_paise": amount, "updated_at": utc_now()}
    await db.transactions.update_one({"id": transaction_id, "user_id": user["id"]}, {"$set": changes})
    await db.accounts.update_one({"id": payload.account_id}, {"$inc": {"balance_paise": balance_effect(payload.type, amount)}})
    old.update(changes)
    return transaction_public(old)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(transaction_id: str, user: dict = Depends(current_user)):
    doc = await db.transactions.find_one({"id": transaction_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.accounts.update_one({"id": doc["account_id"]}, {"$inc": {"balance_paise": -balance_effect(doc["type"], doc["amount_paise"])}})
    await db.transactions.delete_one({"id": transaction_id, "user_id": user["id"]})


@router.post("/transactions/bulk-delete")
async def bulk_delete_transactions(payload: BulkDeleteInput, user: dict = Depends(current_user)):
    docs = await db.transactions.find({"id": {"$in": payload.ids}, "user_id": user["id"]}, {"_id": 0}).to_list(100)
    for doc in docs:
        await db.accounts.update_one({"id": doc["account_id"]}, {"$inc": {"balance_paise": -balance_effect(doc["type"], doc["amount_paise"])}})
    result = await db.transactions.delete_many({"id": {"$in": payload.ids}, "user_id": user["id"]})
    return {"deleted": result.deleted_count}


@router.get("/budget", response_model=Budget)
async def get_budget(user: dict = Depends(current_user)):
    now = date.today()
    month = now.strftime("%Y-%m")
    budget = await db.budgets.find_one({"user_id": user["id"]}, {"_id": 0})
    limit = budget["monthly_limit_paise"] if budget else 0
    pipeline = [{"$match": {"user_id": user["id"], "type": "EXPENSE", "date": {"$regex": f"^{month}"}}}, {"$group": {"_id": None, "spent": {"$sum": "$amount_paise"}}}]
    totals = await db.transactions.aggregate(pipeline).to_list(1)
    spent = totals[0]["spent"] if totals else 0
    usage = round(spent / limit * 100, 1) if limit else 0
    return Budget(monthly_limit=to_rupees(limit), spent=to_rupees(spent), remaining=to_rupees(limit - spent), usage_percentage=usage, alert_threshold=(budget or {}).get("alert_threshold", 80), month=month)


@router.put("/budget", response_model=Budget)
async def update_budget(payload: BudgetUpdate, user: dict = Depends(current_user)):
    await db.budgets.update_one({"user_id": user["id"]}, {"$set": {"monthly_limit_paise": to_paise(payload.monthly_limit), "alert_threshold": payload.alert_threshold, "updated_at": utc_now()}, "$setOnInsert": {"created_at": utc_now()}}, upsert=True)
    return await get_budget(user)


@router.get("/goals", response_model=list[Goal])
async def list_goals(user: dict = Depends(current_user)):
    baseline = await baseline_for_user(user["id"])
    return [goal_public(doc, max(baseline["avg_savings"], 0)) for doc in baseline["goals"]]


@router.post("/goals", response_model=Goal, status_code=status.HTTP_201_CREATED)
async def create_goal(payload: GoalCreate, user: dict = Depends(current_user)):
    now = utc_now()
    doc = {"id": str(uuid.uuid4()), "user_id": user["id"], "name": payload.name, "target_paise": to_paise(payload.target_amount), "current_paise": to_paise(payload.current_amount), "target_date": payload.target_date.isoformat() if payload.target_date else None, "priority": payload.priority, "category": payload.category, "created_at": now, "updated_at": now}
    await db.goals.insert_one(doc)
    return goal_public(doc)


@router.put("/goals/{goal_id}", response_model=Goal)
async def update_goal(goal_id: str, payload: GoalUpdate, user: dict = Depends(current_user)):
    doc = await db.goals.find_one({"id": goal_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Goal not found")
    changes = {"name": payload.name, "target_paise": to_paise(payload.target_amount), "current_paise": to_paise(payload.current_amount), "target_date": payload.target_date.isoformat() if payload.target_date else None, "priority": payload.priority, "category": payload.category, "updated_at": utc_now()}
    await db.goals.update_one({"id": goal_id, "user_id": user["id"]}, {"$set": changes})
    doc.update(changes)
    return goal_public(doc)


@router.post("/goals/{goal_id}/contribute", response_model=Goal)
async def contribute(goal_id: str, payload: ContributionInput, user: dict = Depends(current_user)):
    doc = await db.goals.find_one({"id": goal_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Goal not found")
    new_amount = min(doc["current_paise"] + to_paise(payload.amount), doc["target_paise"])
    await db.goals.update_one({"id": goal_id, "user_id": user["id"]}, {"$set": {"current_paise": new_amount, "updated_at": utc_now()}})
    doc["current_paise"] = new_amount
    return goal_public(doc)


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: str, user: dict = Depends(current_user)):
    result = await db.goals.delete_one({"id": goal_id, "user_id": user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Goal not found")


@router.get("/dashboard", response_model=DashboardSummary)
async def dashboard(user: dict = Depends(current_user)):
    data = await baseline_for_user(user["id"])
    budget = await get_budget(user)
    categories = sorted(data["categories"].items(), key=lambda item: item[1], reverse=True)
    monthly = sorted(data["monthly"].items())[-6:]
    recent = data["transactions"][:5]
    return DashboardSummary(
        total_balance=to_rupees(data["total_balance"]), total_income=to_rupees(data["total_income"]),
        total_expenses=to_rupees(data["total_expenses"]), net_cash_flow=to_rupees(data["total_income"] - data["total_expenses"]),
        budget_remaining=budget.remaining, savings_rate=round((data["total_income"] - data["total_expenses"]) / data["total_income"] * 100, 1) if data["total_income"] else 0,
        largest_category=categories[0][0] if categories else None,
        category_spend=[{"category": key, "amount": to_rupees(value)} for key, value in categories],
        monthly_flow=[{"month": key, "income": to_rupees(value["income"]), "expenses": to_rupees(value["expenses"])} for key, value in monthly],
        recent_transactions=[transaction_public(doc) for doc in recent],
        goals=[goal_public(doc, max(data["avg_savings"], 0)) for doc in data["goals"]],
    )
