from codex_switch.auth import load_auth_snapshot


def test_load_auth_snapshot_extracts_email_plan_and_org(auth_file):
    snapshot = load_auth_snapshot(auth_file)

    assert snapshot.email == "author@example.com"
    assert snapshot.plan == "plus"
    assert snapshot.account_id == "acct-123"
    assert snapshot.default_org_title == "Personal"
    assert snapshot.email_verified is True
