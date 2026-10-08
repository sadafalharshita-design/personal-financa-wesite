import math
from collections import defaultdict
from datetime import datetime, timezone

from lib.db import db


def to_paise(value: float) -> int:
    return int(round(value * 100))


def to_rupees(value: int) -> float:
    return round(value / 100, 2)


def transaction_public(doc: dict) -> dict:
    return {
        "id": doc["id"],
        "type": doc["type"],
        "amount": to_rupees(doc["amount_paise"]),
        "description": doc["description"],
        "date": doc["date"],
        "category": doc["category"],
        "merchant": doc.get("merchant"),
        "account_id": doc["account_id"],
        "is_recurring": doc.get("is_recurring", False),
        "recurring_interval": doc.get("recurring_interval"),
        "status": doc.get("status", "COMPLETED"),
        "created_at": doc["created_at"],
    }


async def baseline_for_user(user_id: str) -> dict:
    accounts = await db.accounts.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    transactions = await db.transactions.find({"user_id": user_id}, {"_id": 0}).sort("date", -1).to_list(2000)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).sort("priority", 1).to_list(100)

    monthly: dict[str, dict[str, int]] = defaultdict(lambda: {"income": 0, "expenses": 0})
    categories: dict[str, int] = defaultdict(int)
    for item in transactions:
        month = str(item["date"])[:7]
        if item["type"] == "INCOME":
            monthly[month]["income"] += item["amount_paise"]
        else:
            monthly[month]["expenses"] += item["amount_paise"]
            categories[item["category"]] += item["amount_paise"]

    month_count = max(len(monthly), 1)
    total_income = sum(value["income"] for value in monthly.values())
    total_expenses = sum(value["expenses"] for value in monthly.values())
    avg_income = round(total_income / month_count)
    avg_expenses = round(total_expenses / month_count)
    return {
        "accounts": accounts,
        "transactions": transactions,
        "goals": goals,
        "monthly": monthly,
        "categories": categories,
        "total_balance": sum(item["balance_paise"] for item in accounts),
        "total_income": total_income,
        "total_expenses": total_expenses,
        "avg_income": avg_income,
        "avg_expenses": avg_expenses,
        "avg_savings": avg_income - avg_expenses,
        "months": month_count,
    }


def projected_months(remaining_paise: int, monthly_paise: int) -> int | None:
    if remaining_paise <= 0:
        return 0
    if monthly_paise <= 0:
        return None
    return math.ceil(remaining_paise / monthly_paise)


def goal_public(doc: dict, monthly_savings_paise: int = 0) -> dict:
    remaining = max(doc["target_paise"] - doc["current_paise"], 0)
    completion_months = projected_months(remaining, monthly_savings_paise)
    projected = None
    if completion_months is not None:
        projected = f"{completion_months} months" if completion_months else "Funded"
    return {
        "id": doc["id"],
        "name": doc["name"],
        "target_amount": to_rupees(doc["target_paise"]),
        "current_amount": to_rupees(doc["current_paise"]),
        "target_date": doc.get("target_date"),
        "priority": doc.get("priority", 2),
        "category": doc.get("category", "Savings"),
        "remaining_amount": to_rupees(remaining),
        "progress_percentage": round(min(doc["current_paise"] / doc["target_paise"] * 100, 100), 1),
        "projected_completion": projected,
        "created_at": doc["created_at"],
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
