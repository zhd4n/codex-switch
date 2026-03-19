from codex_switch.auth import load_auth_snapshot


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
