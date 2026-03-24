import json
import os
from pathlib import Path
import re
import time

from codex_switch.diagnostics import DiagnosticRun
from codex_switch.diagnostics import build_file_context
from codex_switch.diagnostics import fingerprint_bytes
from codex_switch.diagnostics import fingerprint_text
from codex_switch.diagnostics import mask_email
from codex_switch.diagnostics import mask_identifier


def create_report(diagnostics_dir: Path, *, name: str, age_days: int) -> Path:
    path = diagnostics_dir / name
    path.write_text("{}")
    ts = time.time() - (age_days * 24 * 60 * 60)
    os.utime(path, (ts, ts))
    return path


def test_fingerprint_text_returns_short_stable_hash():
    assert fingerprint_text("abc") == fingerprint_text("abc")
    assert len(fingerprint_text("abc")) == 12


def test_write_failure_report_uses_timestamped_filename_and_base_schema(tmp_path):
    run = DiagnosticRun(command="status", args=[], diagnostics_dir=tmp_path)
    run.record_event("command_started")

    report_path = run.write_failure_report(
        RuntimeError("boom"),
        error_category="system_error",
    )

    assert report_path is not None
    assert re.match(r"\d{8}T\d{6}Z-status-[a-f0-9]{12}\.json", report_path.name)
    payload = json.loads(report_path.read_text())
    assert payload["schema_version"] == 1
    assert payload["command"] == "status"
    assert payload["result"] == "error"
    assert payload["environment"]["python_version"]
    assert payload["context"] == {}
    assert payload["events"][0]["name"] == "command_started"


def test_write_failure_report_falls_back_when_event_data_is_not_json_safe(tmp_path):
    run = DiagnosticRun(command="status", args=[], diagnostics_dir=tmp_path)
    run.record_event("unsafe", value=object())

    report_path = run.write_failure_report(
        RuntimeError("boom"),
        error_category="system_error",
    )

    assert report_path is not None
    payload = json.loads(report_path.read_text())
    assert payload["exception"]["type"] == "RuntimeError"
    assert payload["events"][0]["data"]["value"] == "<non-serializable: object>"


def test_write_failure_report_uses_fallback_payload_when_primary_write_fails(
    monkeypatch, tmp_path
):
    run = DiagnosticRun(command="status", args=[], diagnostics_dir=tmp_path)
    original_write_text = Path.write_text
    calls = {"count": 0}

    def flaky_write_text(self, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("disk full")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", flaky_write_text)

    report_path = run.write_failure_report(
        RuntimeError("boom"),
        error_category="system_error",
    )

    assert report_path is not None
    payload = json.loads(report_path.read_text())
    assert payload["exception"]["type"] == "RuntimeError"
    assert payload["diagnostics_error"] == "disk full"


def test_write_failure_report_returns_none_when_fallback_write_also_fails(
    monkeypatch, tmp_path
):
    run = DiagnosticRun(command="status", args=[], diagnostics_dir=tmp_path)
    monkeypatch.setattr(Path, "write_text", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")))

    assert run.write_failure_report(
        RuntimeError("boom"),
        error_category="system_error",
    ) is None


def test_write_failure_report_keeps_primary_payload_when_cleanup_fails(
    monkeypatch, tmp_path
):
    run = DiagnosticRun(command="status", args=[], diagnostics_dir=tmp_path)
    monkeypatch.setattr(
        DiagnosticRun,
        "cleanup_old_reports",
        lambda self: (_ for _ in ()).throw(OSError("cleanup failed")),
    )

    report_path = run.write_failure_report(
        RuntimeError("boom"),
        error_category="system_error",
    )

    assert report_path is not None
    payload = json.loads(report_path.read_text())
    assert payload["exception"]["type"] == "RuntimeError"
    assert "diagnostics_error" not in payload


def test_mask_helpers_cover_edge_cases():
    assert fingerprint_bytes(b"abc") == fingerprint_text("abc")
    assert mask_email(None) is None
    assert mask_email("plain") == "plain"
    assert mask_email("@example.com") == "***@example.com"
    assert mask_identifier(None) is None
    assert mask_identifier("abc", keep_prefix=4, keep_suffix=3) == "abc"


def test_retention_removes_expired_and_caps_recent_files(tmp_path):
    diagnostics_dir = tmp_path / "diagnostics"
    diagnostics_dir.mkdir()
    create_report(diagnostics_dir, name="old.json", age_days=30)
    for index in range(25):
        create_report(diagnostics_dir, name=f"recent-{index}.json", age_days=1)

    run = DiagnosticRun(command="status", args=[], diagnostics_dir=diagnostics_dir)
    run.write_failure_report(RuntimeError("boom"), error_category="system_error")

    remaining = sorted(diagnostics_dir.glob("*.json"))
    assert all(path.name != "old.json" for path in remaining)
    assert len(remaining) == 20


def test_build_file_context_reports_directory_entries(tmp_path):
    directory = tmp_path / "sample-dir"
    directory.mkdir()
    (directory / "a.txt").write_text("a")
    (directory / "b.txt").write_text("b")

    context = build_file_context(directory)

    assert context["exists"] is True
    assert context["entries"] == 2


def test_write_success_report_returns_none_when_write_fails(monkeypatch, tmp_path):
    run = DiagnosticRun(command="status", args=[], diagnostics_dir=tmp_path)
    monkeypatch.setattr(Path, "write_text", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")))

    assert run.write_success_report() is None
