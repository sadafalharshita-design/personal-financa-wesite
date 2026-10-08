import base64
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Cookie, HTTPException

from lib.db import db


COOKIE_NAME = "wealth_session"


def hash_password(password: str, salt: str | None = None) -> str:
    resolved_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), resolved_salt.encode(), 240_000)
    return f"{resolved_salt}${base64.b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt, expected = encoded.split("$", 1)
    except ValueError:
        return False
    actual = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(actual, expected)


def create_session_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(days=7), "jti": str(uuid.uuid4())}
    return jwt.encode(payload, os.environ["AUTH_SECRET"], algorithm="HS256")


async def current_user(wealth_session: str | None = Cookie(default=None)) -> dict:
    if not wealth_session:
        raise HTTPException(status_code=401, detail="Please sign in to continue")
    try:
        payload = jwt.decode(wealth_session, os.environ["AUTH_SECRET"], algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Your session has expired") from exc
    user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    return user
