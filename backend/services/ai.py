import json
import os
import re
import uuid

from emergentintegrations.llm.chat import LlmChat, StreamDone, TextDelta, UserMessage

from models.wealth import ScenarioInterpretation


def deterministic_interpret(query: str) -> ScenarioInterpretation:
    lowered = query.lower().replace(",", "")
    amounts = re.findall(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(lakh|lac|k)?", lowered)
    amount = 0.0
    for raw, suffix in amounts:
        candidate = float(raw)
        if suffix in {"lakh", "lac"}:
            candidate *= 100_000
        elif suffix == "k":
            candidate *= 1_000
        if candidate >= 100:
            amount = candidate
            break
    if not amount:
        amount = 3_000

    if any(word in lowered for word in ["afford", "buy", "when can"]):
        target = "Laptop" if "laptop" in lowered else "Goal"
        return ScenarioInterpretation(
            scenario_type="GOAL_AFFORDABILITY", direction="AFFORD_GOAL",
            target_amount=amount, target_name=target,
        )

    category_map = {
        "food": "Food", "dining": "Dining", "shopping": "Shopping",
        "subscription": "Subscription", "fuel": "Fuel", "travel": "Travel",
        "grocery": "Groceries", "groceries": "Groceries",
    }
    category = next((value for key, value in category_map.items() if key in lowered), None)
    return ScenarioInterpretation(
        scenario_type="CATEGORY_REDUCTION" if category else "MONTHLY_SAVING_CHANGE",
        direction="REDUCE_EXPENSE" if any(word in lowered for word in ["less", "reduce", "stop", "cut"]) else "INCREASE_SAVING",
        monthly_change=amount,
        category=category,
    )


async def _collect(chat: LlmChat, prompt: str) -> str:
    chunks: list[str] = []
    async for event in chat.stream_message(UserMessage(text=prompt)):
        if isinstance(event, TextDelta):
            chunks.append(event.content)
        elif isinstance(event, StreamDone):
            break
    return "".join(chunks).strip()


async def interpret_with_gemini(query: str) -> tuple[ScenarioInterpretation, bool]:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return deterministic_interpret(query), False
    chat = LlmChat(
        api_key=key,
        session_id=f"wealth-intent-{uuid.uuid4()}",
        system_message=(
            "You convert personal finance what-if questions into strict JSON. "
            "Never calculate projections and never include markdown. Currency is INR."
        ),
    ).with_model("gemini", "gemini-3.1-pro-preview")
    prompt = f'''Interpret: {query}\nReturn only JSON with keys: scenario_type (MONTHLY_SAVING_CHANGE, CATEGORY_REDUCTION, or GOAL_AFFORDABILITY), monthly_change number, direction (REDUCE_EXPENSE, INCREASE_SAVING, or AFFORD_GOAL), category nullable, target_amount nullable, target_name nullable, duration_months integer default 12.'''
    try:
        raw = await _collect(chat, prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON object")
        return ScenarioInterpretation.model_validate(json.loads(match.group())), True
    except Exception:
        return deterministic_interpret(query), False


async def explain_with_gemini(calculated: dict) -> tuple[str, bool]:
    key = os.environ.get("EMERGENT_LLM_KEY")
    fallback = calculated["fallback_explanation"]
    if not key:
        return fallback, False
    chat = LlmChat(
        api_key=key,
        session_id=f"wealth-explain-{uuid.uuid4()}",
        system_message=(
            "You are Wealth, a cautious Indian personal-finance decision-support assistant. "
            "Explain only the supplied calculated facts in 2 concise sentences. Never alter a number, "
            "promise an outcome, or claim to be a financial adviser."
        ),
    ).with_model("gemini", "gemini-3.1-pro-preview")
    try:
        explanation = await _collect(chat, json.dumps(calculated, default=str))
        return explanation or fallback, bool(explanation)
    except Exception:
        return fallback, False
