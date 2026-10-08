"""Shared Mongo handle — import `client`/`db` from here (server.py, routers, seed.py)."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

logger = logging.getLogger(__name__)

# One entry per collection: every field a route filters, sorts, or dedupes on. Applied by ensure_indexes() at startup.
INDEXES: dict[str, list[IndexModel]] = {
    "status_checks": [IndexModel([("timestamp", DESCENDING)], name="timestamp_desc")],
    "users": [IndexModel([("email", ASCENDING)], name="email_unique", unique=True)],
    "accounts": [
        IndexModel([("id", ASCENDING)], name="account_id_unique", unique=True),
        IndexModel([("user_id", ASCENDING), ("created_at", ASCENDING)], name="account_user_created"),
    ],
    "transactions": [
        IndexModel([("id", ASCENDING)], name="transaction_id_unique", unique=True),
        IndexModel([("user_id", ASCENDING), ("date", DESCENDING)], name="transaction_user_date"),
        IndexModel([("user_id", ASCENDING), ("account_id", ASCENDING)], name="transaction_user_account"),
    ],
    "budgets": [IndexModel([("user_id", ASCENDING)], name="budget_user_unique", unique=True)],
    "goals": [
        IndexModel([("id", ASCENDING)], name="goal_id_unique", unique=True),
        IndexModel([("user_id", ASCENDING), ("priority", ASCENDING)], name="goal_user_priority"),
    ],
    "scenarios": [
        IndexModel([("id", ASCENDING)], name="scenario_id_unique", unique=True),
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="scenario_user_created"),
    ],
    "ai_usage": [IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ai_usage_user_created")],
    "coach_messages": [
        IndexModel([("id", ASCENDING)], name="coach_message_id_unique", unique=True),
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="coach_user_created"),
    ],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:  # one at a time so a bad spec skips only itself
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:  # never block boot on an index; the log line names what to fix
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
