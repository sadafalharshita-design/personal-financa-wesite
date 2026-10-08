import asyncio
import uuid
from datetime import date, datetime, timezone

from calendar import monthrange

from lib.db import client, db, ensure_indexes
from lib.security import hash_password
from services.finance import to_paise


EMAIL = "rahul@wealth.demo"
PASSWORD = "WealthDemo123!"


async def seed() -> None:
    existing = await db.users.find_one({"email": EMAIL})
    if existing:
        print("Demo user already seeded")
        return
    now = datetime.now(timezone.utc)
    user_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": user_id, "email": EMAIL, "name": "Rahul Sharma", "password_hash": hash_password(PASSWORD),
        "image_url": None, "onboarded": True, "created_at": now, "updated_at": now,
    })
    await db.accounts.insert_one({
        "id": account_id, "user_id": user_id, "name": "HDFC Savings", "type": "SAVINGS",
        "balance_paise": to_paise(128500), "is_default": True, "created_at": now, "updated_at": now,
    })
    await db.budgets.insert_one({
        "user_id": user_id, "monthly_limit_paise": to_paise(35000), "alert_threshold": 80,
        "created_at": now, "updated_at": now,
    })
    await db.goals.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "name": "MacBook Pro", "target_paise": to_paise(180000),
        "current_paise": to_paise(72000), "target_date": None, "priority": 1, "category": "Technology",
        "created_at": now, "updated_at": now,
    })
    templates = [
        ("INCOME", 65000, "Monthly salary", "Salary", "Acme India"),
        ("EXPENSE", 18000, "Apartment rent", "Rent", "Greenview Homes"),
        ("EXPENSE", 6200, "Groceries and essentials", "Groceries", "Reliance Fresh"),
        ("EXPENSE", 4200, "Food delivery", "Food", "Swiggy"),
        ("EXPENSE", 2800, "Metro and cab", "Transport", "Namma Metro"),
        ("EXPENSE", 1400, "Streaming and software", "Subscription", "Digital services"),
        ("EXPENSE", 2300, "Electricity and internet", "Utilities", "BESCOM"),
    ]
    docs = []
    for offset in range(3):
        current = date.today()
        month_index = current.year * 12 + current.month - 1 - offset
        year, month_zero = divmod(month_index, 12)
        tx_date = date(year, month_zero + 1, min(5, monthrange(year, month_zero + 1)[1])).isoformat()
        for tx_type, amount, description, category, merchant in templates:
            docs.append({
                "id": str(uuid.uuid4()), "user_id": user_id, "account_id": account_id, "type": tx_type,
                "amount_paise": to_paise(amount + (offset * 300 if category == "Food" else 0)),
                "description": description, "date": tx_date, "category": category, "merchant": merchant,
                "is_recurring": category in {"Salary", "Rent", "Subscription"},
                "recurring_interval": "MONTHLY" if category in {"Salary", "Rent", "Subscription"} else None,
                "status": "COMPLETED", "created_at": now, "updated_at": now,
            })
    await db.transactions.insert_many(docs)
    await ensure_indexes()
    print(f"Seeded demo account: {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    finally:
        client.close()