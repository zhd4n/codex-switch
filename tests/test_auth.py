import json

from codex_switch.auth import load_auth_snapshot
from codex_switch.diagnostics import build_auth_summary


def test_load_auth_snapshot_extracts_email_plan_and_org(auth_file):
    snapshot = load_auth_snapshot(auth_file)

    assert snapshot.email == "author@example.com"
    assert snapshot.plan == "plus"
    assert snapshot.account_id == "acct-123"
    assert snapshot.default_org_title == "Personal"
    assert snapshot.email_verified is True


def test_load_auth_snapshot_falls_back_to_first_org_when_no_default(auth_file_factory):
    auth_file = auth_file_factory(
        organizations=[
            {"title": "Fallback Org", "is_default": False},
            {"title": "Another Org", "is_default": False},
        ]
    )

    snapshot = load_auth_snapshot(auth_file)

    assert snapshot.default_org_title == "Fallback Org"


def test_load_auth_snapshot_handles_missing_organizations(auth_file_factory):
    auth_file = auth_file_factory(organizations=[])

    snapshot = load_auth_snapshot(auth_file)

    assert snapshot.default_org_title is None


def test_build_auth_summary_masks_identifiers_and_preserves_safe_fields(auth_file):
    snapshot = load_auth_snapshot(auth_file)

    summary = build_auth_summary(snapshot)

    assert summary["email"] == "a***@example.com"
    assert summary["account_id"] == "acct-***123"
    assert summary["session_id"] == "authsess_***123"
    assert summary["plan"] == "plus"
    assert summary["default_org"] == "Personal"
    assert summary["auth_mode"] == "chatgpt"
    assert summary["last_refresh"] == "2026-03-18T12:55:53.815614Z"
    assert "refresh_token" not in json.dumps(summary)


def test_build_auth_summary_omits_missing_token_fingerprints(auth_file):
    snapshot = load_auth_snapshot(auth_file)
    snapshot.raw["tokens"].pop("access_token")

    summary = build_auth_summary(snapshot)

    assert "access_token" not in summary["token_fingerprints"]


def test_load_auth_snapshot_can_emit_decode_anomaly_events(tmp_path):
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "last_refresh": "2026-03-18T12:55:53.815614Z",
                "tokens": {"id_token": "bad", "access_token": "bad"},
            }
        )
    )
    seen = []

    snapshot = load_auth_snapshot(
        auth_file,
        recorder=lambda name, **data: seen.append((name, data)),
    )

    assert snapshot.email is None
    assert any(name == "jwt_decode_fallback" for name, _ in seen)
