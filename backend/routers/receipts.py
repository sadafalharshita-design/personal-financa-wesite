from datetime import timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from lib.db import db
from lib.security import current_user
from models.wealth import ReceiptScanResponse
from services.ai import extract_receipt_with_gemini
from services.finance import utc_now


router = APIRouter(prefix="/receipts", tags=["receipts"])

MAX_IMAGE_BYTES = 8 * 1024 * 1024


def detected_mime(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.post("/scan", response_model=ReceiptScanResponse)
async def scan_receipt(file: UploadFile = File(...), user: dict = Depends(current_user)):
    content = await file.read(MAX_IMAGE_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=422, detail="Choose a receipt or bill image to scan")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Receipt image must be 8 MB or smaller")
    actual_mime = detected_mime(content)
    if actual_mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Use a JPG, PNG, or WEBP receipt image")
    if file.content_type and file.content_type != actual_mime:
        raise HTTPException(status_code=415, detail="The file content does not match its image type")

    since = utc_now() - timedelta(hours=1)
    count = await db.ai_usage.count_documents({"user_id": user["id"], "kind": "receipt", "created_at": {"$gte": since}})
    if count >= 8:
        raise HTTPException(status_code=429, detail="You've reached the hourly receipt scan limit. Try again shortly.")
    await db.ai_usage.insert_one({"user_id": user["id"], "kind": "receipt", "created_at": utc_now()})
    try:
        extraction, warnings = await extract_receipt_with_gemini(content, actual_mime)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="We couldn't read this receipt reliably. Try a clearer, well-lit image.") from exc
    finally:
        content = b""
    return ReceiptScanResponse(extraction=extraction, warnings=warnings, ai_powered=True)