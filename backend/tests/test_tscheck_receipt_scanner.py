"""Backend tests for the Gemini receipt scanner (/api/receipts/scan).

Covers:
- Valid JPEG receipt is analyzed and returns an editable draft extraction
  (never auto-creates a transaction).
- Unsafe / unsupported uploads (e.g. plain text masquerading as an image) are rejected.
- Endpoint requires authentication.
"""

import os
import uuid

import httpx
import pytest

RECEIPT_IMAGE_PATH = "/tmp/assets/receipt.jpg"
DEMO_EMAIL = "rahul@wealth.demo"
DEMO_PASSWORD = "WealthDemo123!"


@pytest.fixture
def demo_client():
    with httpx.Client(base_url="http://localhost:8001/api", timeout=60.0) as c:
        resp = c.post("/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        assert resp.status_code == 200, resp.text
        yield c


def test_valid_jpeg_receipt_is_extracted_without_creating_transaction(demo_client):
    assert os.path.exists(RECEIPT_IMAGE_PATH), "fixture receipt image missing"
    with open(RECEIPT_IMAGE_PATH, "rb") as fh:
        image_bytes = fh.read()

    # Snapshot transaction count before scanning to prove no auto-save happens.
    before = demo_client.get("/transactions")
    assert before.status_code == 200, before.text
    before_count = len(before.json()) if isinstance(before.json(), list) else before.json().get("total")

    resp = demo_client.post(
        "/receipts/scan",
        files={"file": ("tscheck-receipt-sample.jpg", image_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ai_powered"] is True
    extraction = body["extraction"]
    assert extraction["amount"] > 0
    assert extraction["category"]
    assert extraction["description"]
    assert extraction["type"] in {"INCOME", "EXPENSE"}
    # merchant/date may be None with a warning, but amount/category/description/type must be present.

    after = demo_client.get("/transactions")
    assert after.status_code == 200
    after_count = len(after.json()) if isinstance(after.json(), list) else after.json().get("total")
    assert after_count == before_count, "scan endpoint must not create a transaction by itself"


def test_non_image_upload_is_rejected(demo_client):
    resp = demo_client.post(
        "/receipts/scan",
        files={"file": ("tscheck-not-an-image.txt", b"this is plain text, not an image", "text/plain")},
    )
    assert resp.status_code == 415, resp.text
    assert "JPG, PNG, or WEBP" in resp.json()["detail"]


def test_scan_requires_authentication():
    with httpx.Client(base_url="http://localhost:8001/api", timeout=30.0) as c:
        with open(RECEIPT_IMAGE_PATH, "rb") as fh:
            resp = c.post(
                "/receipts/scan",
                files={"file": ("tscheck-receipt-sample.jpg", fh.read(), "image/jpeg")},
            )
    assert resp.status_code == 401
