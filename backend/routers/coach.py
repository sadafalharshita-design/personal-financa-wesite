import json
import os
import uuid
from datetime import timedelta

from emergentintegrations.llm.chat import LlmChat, StreamDone, TextDelta, UserMessage
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from lib.db import db
from lib.security import current_user
from models.wealth import CoachExchange, CoachQuestion
from services.finance import baseline_for_user, to_rupees, utc_now


router = APIRouter(prefix="/coach", tags=["coach"])


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


async def aggregate_context(user_id: str) -> dict:
    data = await baseline_for_user(user_id)
    budget = await db.budgets.find_one({"user_id": user_id}, {"_id": 0})
    categories = sorted(data["categories"].items(), key=lambda item: item[1], reverse=True)[:6]
    goals = [
        {
            "name": goal["name"],
            "target_inr": to_rupees(goal["target_paise"]),
            "current_inr": to_rupees(goal["current_paise"]),
            "remaining_inr": to_rupees(max(goal["target_paise"] - goal["current_paise"], 0)),
            "priority": goal.get("priority", 2),
        }
        for goal in data["goals"][:5]
    ]
    return {
        "currency": "INR",
        "months_of_activity": data["months"],
        "total_account_balance_inr": to_rupees(data["total_balance"]),
        "average_monthly_income_inr": to_rupees(data["avg_income"]),
        "average_monthly_expenses_inr": to_rupees(data["avg_expenses"]),
        "average_monthly_savings_inr": to_rupees(data["avg_savings"]),
        "monthly_budget_inr": to_rupees(budget["monthly_limit_paise"]) if budget else None,
        "top_spending_categories": [
            {"category": name, "average_monthly_inr": to_rupees(round(amount / data["months"]))}
            for name, amount in categories
        ],
        "goals": goals,
    }


@router.get("/history", response_model=list[CoachExchange])
async def get_history(user: dict = Depends(current_user)):
    docs = await db.coach_messages.find({"user_id": user["id"]}, {"_id": 0, "user_id": 0}).sort("created_at", -1).limit(30).to_list(30)
    return list(reversed(docs))


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(user: dict = Depends(current_user)):
    await db.coach_messages.delete_many({"user_id": user["id"]})


@router.post("/message")
async def ask_coach(payload: CoachQuestion, user: dict = Depends(current_user)):
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="Ask Wealth is temporarily unavailable")
    since = utc_now() - timedelta(hours=1)
    count = await db.ai_usage.count_documents({"user_id": user["id"], "kind": "coach", "created_at": {"$gte": since}})
    if count >= 20:
        raise HTTPException(status_code=429, detail="You've reached the hourly Ask Wealth limit. Try again shortly.")
    await db.ai_usage.insert_one({"user_id": user["id"], "kind": "coach", "created_at": utc_now()})

    context = await aggregate_context(user["id"])
    history_docs = await db.coach_messages.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(6).to_list(6)
    prior_turns = [
        {"question": item["question"][:500], "answer": item["answer"][:1200]}
        for item in reversed(history_docs)
    ]
    system_message = (
        "You are Ask Wealth, a careful personal-finance decision-support coach for an Indian user. "
        "Ground every personalized statement only in the aggregate financial context supplied by the application. "
        "Never invent transactions, returns, interest rates, tax facts, or guarantees. Never claim to have changed a record. "
        "Do not request account numbers, credentials, identity documents, or other sensitive data. "
        "Use Indian rupee formatting. Be concise but useful: answer the question, explain the relevant evidence, then give 2-3 practical next steps with assumptions. "
        "If data is insufficient, say exactly what is missing. For investment, debt, tax, or legal topics, give general educational guidance and recommend a qualified professional when appropriate. "
        "End projections with a brief reminder that estimates may differ from actual results."
    )
    prompt = json.dumps(
        {"financial_context": context, "recent_conversation": prior_turns, "user_question": payload.message},
        ensure_ascii=False,
    )
    chat = LlmChat(api_key=key, session_id=f"wealth-coach-{uuid.uuid4()}", system_message=system_message).with_model("gemini", "gemini-3.1-pro-preview")

    async def event_stream():
        chunks: list[str] = []
        completed = False
        try:
            async for event in chat.stream_message(UserMessage(text=prompt)):
                if isinstance(event, TextDelta):
                    chunks.append(event.content)
                    yield sse({"type": "token", "content": event.content})
                elif isinstance(event, StreamDone):
                    completed = True
                    break
            answer = "".join(chunks).strip()
            if completed and answer:
                exchange = {
                    "id": str(uuid.uuid4()), "user_id": user["id"], "question": payload.message,
                    "answer": answer, "created_at": utc_now(),
                }
                await db.coach_messages.insert_one(exchange)
                public_exchange = {key: value for key, value in exchange.items() if key not in {"_id", "user_id"}}
                yield sse({"type": "done", "data": public_exchange})
            else:
                yield sse({"type": "error", "message": "The response was interrupted. Please ask again."})
        except Exception:
            yield sse({"type": "error", "message": "Ask Wealth couldn't complete that response. Please try again."})

    return StreamingResponse(
        event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )