from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuthSnapshot:
    raw: dict[str, Any]
    id_payload: dict[str, Any]
    access_payload: dict[str, Any]
    auth_mode: str | None
    last_refresh: str | None
    email: str | None
    name: str | None
    plan: str | None
    account_id: str | None
    session_id: str | None
    default_org_title: str | None
    email_verified: bool


def decode_jwt_payload(token: str) -> dict[str, Any]:
    payload = token.split(".")[1]
    payload += "=" * ((4 - len(payload) % 4) % 4)
    decoded = base64.urlsafe_b64decode(payload.encode())
    return json.loads(decoded)


def extract_default_org_title(id_payload: dict[str, Any]) -> str | None:
    organizations = id_payload.get("https://api.openai.com/auth", {}).get(
        "organizations", []
    )
    for organization in organizations:
        if organization.get("is_default"):
            return organization.get("title")
    return organizations[0].get("title") if organizations else None


def load_auth_snapshot(path: Path) -> AuthSnapshot:
    raw = json.loads(path.read_text())
    id_payload = decode_jwt_payload(raw["tokens"]["id_token"])
    access_payload = decode_jwt_payload(raw["tokens"]["access_token"])
    return AuthSnapshot(
        raw=raw,
        id_payload=id_payload,
        access_payload=access_payload,
        auth_mode=raw.get("auth_mode"),
        last_refresh=raw.get("last_refresh"),
        email=id_payload.get("email")
        or access_payload.get("https://api.openai.com/profile", {}).get("email"),
        name=id_payload.get("name"),
        plan=id_payload.get("https://api.openai.com/auth", {}).get("chatgpt_plan_type")
        or access_payload.get("https://api.openai.com/auth", {}).get("chatgpt_plan_type"),
        account_id=raw.get("tokens", {}).get("account_id")
        or access_payload.get("https://api.openai.com/auth", {}).get("chatgpt_account_id"),
        session_id=access_payload.get("session_id"),
        default_org_title=extract_default_org_title(id_payload),
        email_verified=bool(id_payload.get("email_verified")),
    )
