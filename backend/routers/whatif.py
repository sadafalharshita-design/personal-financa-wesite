import math
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from lib.db import db
from lib.security import current_user
from models.wealth import ScenarioRequest, ScenarioResult
from services.ai import explain_with_gemini, interpret_with_gemini
from services.finance import baseline_for_user, projected_months, to_paise, to_rupees, utc_now


router = APIRouter(prefix="/what-if", tags=["what-if"])


@router.get("/history", response_model=list[ScenarioResult])
async def history(user: dict = Depends(current_user)):
    return await db.scenarios.find({"user_id": user["id"]}, {"_id": 0, "user_id": 0}).sort("created_at", -1).limit(20).to_list(20)


@router.get("/{scenario_id}", response_model=ScenarioResult)
async def get_scenario(scenario_id: str, user: dict = Depends(current_user)):
    doc = await db.scenarios.find_one({"id": scenario_id, "user_id": user["id"]}, {"_id": 0, "user_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return doc


@router.post("/simulate", response_model=ScenarioResult)
async def simulate(payload: ScenarioRequest, user: dict = Depends(current_user)):
    since = utc_now() - timedelta(hours=1)
    request_count = await db.ai_usage.count_documents({"user_id": user["id"], "kind": {"$in": ["scenario", None]}, "created_at": {"$gte": since}})
    if request_count >= 10:
        raise HTTPException(status_code=429, detail="You've reached the hourly simulation limit. Try again shortly.")

    data = await baseline_for_user(user["id"])
    if not data["transactions"]:
        raise HTTPException(status_code=422, detail="We need at least one month of financial activity to make a meaningful simulation.")
    await db.ai_usage.insert_one({"user_id": user["id"], "kind": "scenario", "created_at": utc_now()})
    intent, interpretation_ai = await interpret_with_gemini(payload.query)
    avg_income = data["avg_income"]
    avg_expenses = data["avg_expenses"]
    avg_savings = avg_income - avg_expenses
    monthly_change = max(to_paise(intent.monthly_change), 0)

    if intent.scenario_type == "CATEGORY_REDUCTION" and intent.category:
        category_avg = round(data["categories"].get(intent.category, 0) / data["months"])
        monthly_change = min(monthly_change, category_avg) if category_avg else monthly_change
    simulated_expenses = max(avg_expenses - monthly_change, 0)
    simulated_savings = avg_income - simulated_expenses

    available = max(data["total_balance"] - to_paise(payload.safety_buffer), 0)
    affordability_months = None
    if intent.scenario_type == "GOAL_AFFORDABILITY" and intent.target_amount:
        remaining_target = max(to_paise(intent.target_amount) - available, 0)
        affordability_months = projected_months(remaining_target, max(avg_savings, 0))
        monthly_change = 0
        simulated_expenses = avg_expenses
        simulated_savings = avg_savings

    active_goal = next((goal for goal in data["goals"] if goal["current_paise"] < goal["target_paise"]), None)
    baseline_goal = simulated_goal = None
    acceleration = 0
    if active_goal:
        remaining = active_goal["target_paise"] - active_goal["current_paise"]
        baseline_goal = projected_months(remaining, max(avg_savings, 0))
        simulated_goal = projected_months(remaining, max(simulated_savings, 0))
        if baseline_goal is not None and simulated_goal is not None:
            acceleration = max(baseline_goal - simulated_goal, 0)

    projections = [
        {"month": month, "baseline": to_rupees(avg_savings * month), "simulated": to_rupees(simulated_savings * month)}
        for month in [0, 1, 3, 6, 12]
    ]
    if intent.scenario_type == "GOAL_AFFORDABILITY":
        summary = f"Estimate affordability for {intent.target_name or 'your goal'} while keeping a safety buffer."
    elif intent.category:
        summary = f"Reduce {intent.category} spending by {to_rupees(monthly_change):,.0f} per month."
    else:
        summary = f"Increase monthly savings by {to_rupees(monthly_change):,.0f}."

    calculated = {
        "scenario": summary,
        "baseline_monthly_savings_inr": to_rupees(avg_savings),
        "simulated_monthly_savings_inr": to_rupees(simulated_savings),
        "additional_12_month_savings_inr": to_rupees((simulated_savings - avg_savings) * 12),
        "goal": active_goal["name"] if active_goal else None,
        "goal_acceleration_months": acceleration,
        "affordability_months": affordability_months,
        "safety_buffer_inr": payload.safety_buffer,
        "fallback_explanation": f"This change may add ₹{to_rupees((simulated_savings - avg_savings) * 12):,.0f} over 12 months based on your recent averages. Projections are estimates and actual results may differ.",
    }
    explanation, explanation_ai = await explain_with_gemini(calculated)
    now = utc_now()
    result = {
        "id": str(uuid.uuid4()), "user_id": user["id"], "query": payload.query,
        "scenario_type": intent.scenario_type, "scenario_summary": summary,
        "baseline_monthly_income": to_rupees(avg_income), "baseline_monthly_expenses": to_rupees(avg_expenses),
        "baseline_monthly_savings": to_rupees(avg_savings), "simulated_monthly_expenses": to_rupees(simulated_expenses),
        "simulated_monthly_savings": to_rupees(simulated_savings), "current_balance": to_rupees(data["total_balance"]),
        "projections": projections, "goal_name": active_goal["name"] if active_goal else None,
        "baseline_goal_months": baseline_goal, "simulated_goal_months": simulated_goal,
        "goal_acceleration_months": acceleration, "affordability_months": affordability_months,
        "ai_explanation": explanation, "ai_powered": interpretation_ai or explanation_ai,
        "assumptions": [
            f"Uses an average across {data['months']} month(s) of recorded activity.",
            f"Maintains a ₹{payload.safety_buffer:,.0f} safety buffer for affordability checks.",
            "Income, expenses, and behavior are assumed to remain otherwise unchanged.",
        ], "created_at": now,
    }
    await db.scenarios.insert_one(result)
    return {key: value for key, value in result.items() if key != "user_id"}
