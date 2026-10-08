import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status

from lib.db import db
from lib.security import COOKIE_NAME, create_session_token, current_user, hash_password, verify_password
from models.wealth import AuthInput, AuthResponse, OnboardingInput, UserPublic
from services.finance import to_paise


router = APIRouter(prefix="/auth", tags=["auth"])


def public_user(user: dict) -> UserPublic:
    return UserPublic(**{key: user.get(key) for key in ["id", "email", "name", "image_url", "onboarded"]})


def set_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        COOKIE_NAME, create_session_token(user_id), httponly=True, secure=False,
        samesite="lax", max_age=60 * 60 * 24 * 7, path="/",
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: AuthInput, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    now = datetime.now(timezone.utc)
    user = {
        "id": str(uuid.uuid4()), "email": email, "name": payload.name or email.split("@")[0].title(),
        "password_hash": hash_password(payload.password), "image_url": None, "onboarded": False,
        "created_at": now, "updated_at": now,
    }
    await db.users.insert_one(user)
    set_cookie(response, user["id"])
    return AuthResponse(user=public_user(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: AuthInput, response: Response):
    user = await db.users.find_one({"email": payload.email.lower()}, {"_id": 0})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    set_cookie(response, user["id"])
    return AuthResponse(user=public_user(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserPublic)
async def me(user: dict = Depends(current_user)):
    return public_user(user)


@router.post("/onboarding", response_model=UserPublic)
async def onboarding(payload: OnboardingInput, user: dict = Depends(current_user)):
    if user.get("onboarded"):
        raise HTTPException(status_code=409, detail="Onboarding is already complete")
    now = datetime.now(timezone.utc)
    account_id = str(uuid.uuid4())
    await db.accounts.insert_one({
        "id": account_id, "user_id": user["id"], "name": payload.account_name,
        "type": payload.account_type, "balance_paise": to_paise(payload.initial_balance),
        "is_default": True, "created_at": now, "updated_at": now,
    })
    await db.budgets.insert_one({
        "user_id": user["id"], "monthly_limit_paise": to_paise(payload.monthly_budget),
        "alert_threshold": 80, "created_at": now, "updated_at": now,
    })
    if payload.goal_name and payload.goal_target:
        await db.goals.insert_one({
            "id": str(uuid.uuid4()), "user_id": user["id"], "name": payload.goal_name,
            "target_paise": to_paise(payload.goal_target), "current_paise": 0,
            "target_date": None, "priority": 1, "category": "Savings",
            "created_at": now, "updated_at": now,
        })
    await db.users.update_one({"id": user["id"]}, {"$set": {"name": payload.name, "onboarded": True, "updated_at": now}})
    user.update({"name": payload.name, "onboarded": True})
    return public_user(user)
