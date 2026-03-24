"""Diagnostics helpers for one CLI invocation.

Invariants:
- `cli.main()` owns exactly one `DiagnosticRun` per invocation.
- `DiagnosticRun.args` mirrors the exact argv snapshot used for parsing.
- event payload fields live under `data`; the event identifier always lives in
  the top-level `name` field.
- retention cleanup is post-write best-effort and must never change the outcome
  of a successfully written report.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from datetime import timedelta
import hashlib
import json
import platform
from pathlib import Path
import traceback
import uuid

from codex_switch.auth import AuthSnapshot


ACCOUNT_ID_PREFIX_LEN = 5
SESSION_ID_PREFIX_LEN = 9


def fingerprint_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def make_json_safe(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [make_json_safe(item) for item in value]
    return f"<non-serializable: {type(value).__name__}>"


def fingerprint_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def mask_email(value: str | None) -> str | None:
    if value is None or "@" not in value:
        return value
    local, _, domain = value.partition("@")
    if not local:
        return f"***@{domain}"
    return f"{local[:1]}***@{domain}"


def mask_identifier(
    value: str | None, *, keep_prefix: int = 4, keep_suffix: int = 3
) -> str | None:
    if value is None:
        return None
    if len(value) <= keep_suffix:
        return value
    return f"{value[:keep_prefix]}***{value[-keep_suffix:]}"


def build_auth_summary(snapshot: AuthSnapshot) -> dict:
    tokens = snapshot.raw.get("tokens", {})
    token_fingerprints = {}
    for key in ("id_token", "access_token"):
        token = tokens.get(key)
        if token:
            token_fingerprints[key] = fingerprint_text(token)
    # Identifier shapes differ, so callers must preserve field-specific prefixes
    # instead of assuming one generic masking policy fits every token-like value.
    return {
        "email": mask_email(snapshot.email),
        "account_id": mask_identifier(
            snapshot.account_id,
            keep_prefix=ACCOUNT_ID_PREFIX_LEN,
            keep_suffix=3,
        ),
        "session_id": mask_identifier(
            snapshot.session_id,
            keep_prefix=SESSION_ID_PREFIX_LEN,
            keep_suffix=3,
        ),
        "plan": snapshot.plan,
        "default_org": snapshot.default_org_title,
        "auth_mode": snapshot.auth_mode,
        "last_refresh": snapshot.last_refresh,
        "token_fingerprints": token_fingerprints,
    }


def build_file_context(path: Path) -> dict:
    context = {
        "path": str(path),
        "exists": path.exists(),
    }
    if not path.exists():
        return context
    stat = path.stat()
    context["mode"] = oct(stat.st_mode & 0o777)
    if path.is_dir():
        context["entries"] = len(list(path.iterdir()))
        return context
    context["size"] = stat.st_size
    context["sha256_12"] = fingerprint_bytes(path.read_bytes())
    return context


@dataclass
class DiagnosticRun:
    command: str
    args: list[str]
    diagnostics_dir: Path
    invocation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    context: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    exception_details: dict = field(default_factory=dict)

    def record_event(self, event_name: str, **data) -> None:
        """Append a structured event to the in-memory trace."""
        self.events.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "name": event_name,
                "data": make_json_safe(data),
            }
        )

    def attach_path_context(self, key: str, path: Path) -> None:
        self.context.setdefault("paths", {})[key] = build_file_context(path)

    def record_subprocess_failure(
        self,
        command: list[str],
        *,
        exit_code: int | None,
        stdout_tail: list[str],
        stderr_tail: list[str],
        duration_ms: int,
    ) -> None:
        details = {
            "command": command,
            "exit_code": exit_code,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "duration_ms": duration_ms,
        }
        self.exception_details["subprocess"] = details
        self.record_event("subprocess_failed", **details)

    def build_report_path(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return self.diagnostics_dir / f"{timestamp}-{self.command}-{self.invocation_id}.json"

    def build_failure_payload(self, error: Exception, *, error_category: str) -> dict:
        exception = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            ),
        }
        if self.exception_details:
            exception["details"] = make_json_safe(self.exception_details)
        return {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "invocation_id": self.invocation_id,
            "command": self.command,
            "args": self.args,
            "result": "error",
            "error_category": error_category,
            "environment": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
            },
            "context": make_json_safe(self.context),
            "events": make_json_safe(self.events),
            "exception": exception,
        }

    def build_fallback_payload(
        self, error: Exception, *, error_category: str, diagnostics_error: Exception
    ) -> dict:
        payload = self.build_failure_payload(error, error_category=error_category)
        payload["diagnostics_error"] = str(diagnostics_error)
        return payload

    def build_success_payload(self) -> dict:
        return {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "invocation_id": self.invocation_id,
            "command": self.command,
            "args": self.args,
            "result": "success",
            "environment": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
            },
            "context": make_json_safe(self.context),
            "events": make_json_safe(self.events),
        }

    def cleanup_old_reports(self) -> None:
        now = datetime.now(timezone.utc)
        recent_paths = []
        for path in self.diagnostics_dir.glob("*.json"):
            age = now - datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if age > timedelta(days=14):
                path.unlink(missing_ok=True)
                continue
            recent_paths.append(path)
        recent_paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        for path in recent_paths[20:]:
            path.unlink(missing_ok=True)

    def cleanup_old_reports_best_effort(self) -> None:
        """Run retention without letting cleanup failures affect report writes."""
        try:
            self.cleanup_old_reports()
        except Exception:
            return

    def write_failure_report(
        self, error: Exception, *, error_category: str
    ) -> Path | None:
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.build_report_path()
        try:
            payload = self.build_failure_payload(error, error_category=error_category)
            report_path.write_text(json.dumps(payload, indent=2))
            # Cleanup is intentionally decoupled from write success so retention
            # can never turn a valid report path into a diagnostics failure.
            self.cleanup_old_reports_best_effort()
            return report_path
        except Exception as diagnostics_error:
            try:
                fallback = self.build_fallback_payload(
                    error,
                    error_category=error_category,
                    diagnostics_error=diagnostics_error,
                )
                report_path.write_text(json.dumps(fallback, indent=2))
                self.cleanup_old_reports_best_effort()
                return report_path
            except Exception:
                return None

    def write_success_report(self) -> Path | None:
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.build_report_path()
        try:
            report_path.write_text(json.dumps(self.build_success_payload(), indent=2))
            # Success reports obey the same invariant as failure reports: a
            # cleanup problem must not invalidate an already-written artifact.
            self.cleanup_old_reports_best_effort()
            return report_path
        except Exception:
            return None
