import base64
import json
import os
import re
import uuid

from emergentintegrations.llm.chat import ImageContent, LlmChat, StreamDone, TextDelta, UserMessage

from models.wealth import ReceiptExtraction, ScenarioInterpretation


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


async def extract_receipt_with_gemini(image_bytes: bytes, mime_type: str) -> tuple[ReceiptExtraction, list[str]]:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("Receipt AI is not configured")
    chat = LlmChat(
        api_key=key,
        session_id=f"wealth-receipt-{uuid.uuid4()}",
        system_message=(
            "You extract transaction fields from Indian receipts and bills. Return strict JSON only, no markdown. "
            "Never invent unreadable fields. Use null for an unreadable merchant/date. Amount must be the final total paid. "
            "Valid categories: Food, Groceries, Dining, Shopping, Transport, Fuel, Rent, Utilities, Bills, Healthcare, "
            "Education, Entertainment, Travel, UPI, Subscription, Other. Type must be EXPENSE unless the document is clearly an income receipt."
        ),
    ).with_model("gemini", "gemini-3.1-pro-preview")
    prompt = (
        "Extract this receipt or bill. Return exactly one JSON object with keys merchant (string or null), "
        "amount (positive number in INR), date (YYYY-MM-DD or null), category (one allowed category), "
        "description (short factual description), type (EXPENSE or INCOME), and warnings (array of short strings). "
        "If currency is not INR, mention it in warnings but keep the printed numeric amount."
    )
    message = UserMessage(
        text=prompt,
        file_contents=[ImageContent(image_base64=base64.b64encode(image_bytes).decode("ascii"))],
    )
    chunks: list[str] = []
    async for event in chat.stream_message(message):
        if isinstance(event, TextDelta):
            chunks.append(event.content)
        elif isinstance(event, StreamDone):
            break
    raw = "".join(chunks).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("Gemini did not return structured receipt data")
    parsed = json.loads(match.group())
    warnings = parsed.pop("warnings", [])
    allowed_categories = {
        "Food", "Groceries", "Dining", "Shopping", "Transport", "Fuel", "Rent", "Utilities", "Bills",
        "Healthcare", "Education", "Entertainment", "Travel", "UPI", "Subscription", "Other",
    }
    category_aliases = {"Grocery": "Groceries", "Restaurant": "Dining", "Medical": "Healthcare", "Bill": "Bills"}
    parsed["category"] = category_aliases.get(parsed.get("category"), parsed.get("category"))
    if parsed.get("category") not in allowed_categories:
        parsed["category"] = "Other"
        warnings.append("Category was unclear and has been set to Other.")
    extraction = ReceiptExtraction.model_validate(parsed)
    if extraction.date is None:
        warnings.append("Date could not be read. Please enter it before saving.")
    if extraction.merchant is None:
        warnings.append("Merchant could not be read. Please review before saving.")
    return extraction, [str(item) for item in warnings[:5]]
