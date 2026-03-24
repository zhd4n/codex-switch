from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Callable


# Optional observational hook used by CLI diagnostics. Callers receive
# `(event_name, **data)`, but auth parsing must behave identically when absent.
EventRecorder = Callable[..., None]


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


class MalformedAuthPayloadError(ValueError):
    pass


def decode_jwt_payload(
    token: str, recorder: EventRecorder | None = None
) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode())
        loaded = json.loads(decoded)
        return loaded if isinstance(loaded, dict) else {}
    except (
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        binascii.Error,
    ):
        if recorder is not None:
            recorder("jwt_decode_fallback")
        return {}


def extract_default_org_title(id_payload: dict[str, Any]) -> str | None:
    organizations = id_payload.get("https://api.openai.com/auth", {}).get(
        "organizations", []
    )
    for organization in organizations:
        if organization.get("is_default"):
            return organization.get("title")
    return organizations[0].get("title") if organizations else None


def load_auth_snapshot(
    path: Path, recorder: EventRecorder | None = None
) -> AuthSnapshot:
    if recorder is not None:
        recorder("auth_snapshot_load_started", path=path)
    raw = json.loads(path.read_text())
    try:
        tokens = raw.get("tokens", {})
        id_payload = decode_jwt_payload(tokens.get("id_token", ""), recorder=recorder)
        access_payload = decode_jwt_payload(
            tokens.get("access_token", ""), recorder=recorder
        )
        snapshot = AuthSnapshot(
            raw=raw,
            id_payload=id_payload,
            access_payload=access_payload,
            auth_mode=raw.get("auth_mode"),
            last_refresh=raw.get("last_refresh"),
            email=id_payload.get("email")
            or access_payload.get("https://api.openai.com/profile", {}).get("email"),
            name=id_payload.get("name"),
            plan=id_payload.get("https://api.openai.com/auth", {}).get("chatgpt_plan_type")
            or access_payload.get("https://api.openai.com/auth", {}).get(
                "chatgpt_plan_type"
            ),
            account_id=tokens.get("account_id")
            or access_payload.get("https://api.openai.com/auth", {}).get(
                "chatgpt_account_id"
            ),
            session_id=access_payload.get("session_id"),
            default_org_title=extract_default_org_title(id_payload),
            email_verified=bool(id_payload.get("email_verified")),
        )
    except (AttributeError, TypeError) as error:
        raise MalformedAuthPayloadError(str(error)) from error
    if recorder is not None:
        recorder("auth_snapshot_load_completed", path=path)
    return snapshot
