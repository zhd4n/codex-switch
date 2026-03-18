import base64
import copy
import json
from pathlib import Path

import pytest

from codex_switch.store import SessionStore
from codex_switch.paths import AppPaths


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
def auth_file_factory(tmp_path: Path, auth_payloads: tuple[dict, dict]):
    counter = 0

    def make_auth_file(
        *,
        email: str = "author@example.com",
        plan: str = "plus",
        account_id: str = "acct-123",
        session_id: str = "authsess_123",
        org_title: str = "Personal",
        auth_mode: str = "chatgpt",
    ) -> Path:
        nonlocal counter
        counter += 1
        id_payload, access_payload = copy.deepcopy(auth_payloads)
        id_payload["email"] = email
        id_payload["https://api.openai.com/auth"]["chatgpt_plan_type"] = plan
        id_payload["https://api.openai.com/auth"]["organizations"] = [
            {"title": org_title, "is_default": True}
        ]
        access_payload["session_id"] = session_id
        access_payload["https://api.openai.com/auth"]["chatgpt_plan_type"] = plan
        access_payload["https://api.openai.com/auth"]["chatgpt_account_id"] = account_id
        access_payload["https://api.openai.com/profile"]["email"] = email
        auth_json = {
            "auth_mode": auth_mode,
            "last_refresh": "2026-03-18T12:55:53.815614Z",
            "tokens": {
                "account_id": account_id,
                "id_token": _encode_jwt(id_payload),
                "access_token": _encode_jwt(access_payload),
                "refresh_token": "refresh",
            },
        }
        path = tmp_path / f"auth-{counter}.json"
        path.write_text(json.dumps(auth_json, indent=2))
        return path

    return make_auth_file


@pytest.fixture
def auth_file(auth_file_factory) -> Path:
    return auth_file_factory()


@pytest.fixture
def app_paths(tmp_path: Path) -> AppPaths:
    return AppPaths.from_home(tmp_path)


@pytest.fixture
def saved_session(app_paths: AppPaths, auth_file: Path):
    return SessionStore(app_paths).save(auth_file)


@pytest.fixture
def live_auth_matches_saved(app_paths: AppPaths, saved_session) -> Path:
    app_paths.live_auth_file.parent.mkdir(parents=True, exist_ok=True)
    app_paths.live_auth_file.write_text(saved_session.snapshot_path.read_text())
    return app_paths.live_auth_file


@pytest.fixture
def other_saved_session(app_paths: AppPaths, auth_file_factory):
    other_auth_file = auth_file_factory(
        email="target@example.com",
        account_id="acct-456",
        session_id="authsess_456",
        org_title="Target Org",
    )
    return SessionStore(app_paths).save(other_auth_file, name="target-session")
