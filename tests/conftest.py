import base64
import json
from pathlib import Path

import pytest


def _encode_jwt(payload: dict) -> str:
    header = {"alg": "none", "typ": "JWT"}
    parts = []
    for item in (header, payload):
        encoded = base64.urlsafe_b64encode(json.dumps(item).encode()).decode()
        parts.append(encoded.rstrip("="))
    parts.append("signature")
    return ".".join(parts)


@pytest.fixture
def auth_payloads() -> tuple[dict, dict]:
    id_payload = {
        "email": "author@example.com",
        "email_verified": True,
        "name": "Author",
        "https://api.openai.com/auth": {
            "chatgpt_plan_type": "plus",
            "organizations": [
                {"title": "Secondary", "is_default": False},
                {"title": "Personal", "is_default": True},
            ],
            "chatgpt_subscription_active_until": "2026-04-16T16:35:40+00:00",
            "chatgpt_subscription_last_checked": "2026-03-18T12:55:50+00:00",
            "user_id": "user-123",
        },
    }
    access_payload = {
        "session_id": "authsess_123",
        "https://api.openai.com/auth": {
            "chatgpt_plan_type": "plus",
            "chatgpt_account_id": "acct-123",
            "chatgpt_compute_residency": "no_constraint",
            "user_id": "user-123",
        },
        "https://api.openai.com/profile": {
            "email": "author@example.com",
            "email_verified": True,
        },
    }
    return id_payload, access_payload


@pytest.fixture
def auth_file(tmp_path: Path, auth_payloads: tuple[dict, dict]) -> Path:
    id_payload, access_payload = auth_payloads
    auth_json = {
        "auth_mode": "chatgpt",
        "last_refresh": "2026-03-18T12:55:53.815614Z",
        "tokens": {
            "account_id": "acct-123",
            "id_token": _encode_jwt(id_payload),
            "access_token": _encode_jwt(access_payload),
            "refresh_token": "refresh",
        },
    }
    path = tmp_path / "auth.json"
    path.write_text(json.dumps(auth_json, indent=2))
    return path
