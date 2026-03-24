from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from codex_switch.auth import load_auth_snapshot
from codex_switch.diagnostics import DiagnosticRun
from codex_switch.paths import AppPaths


@dataclass(frozen=True)
class SessionRecord:
    name: str
    slug: str
    snapshot_path: Path
    metadata_path: Path
    email: str | None
    plan: str | None
    account_id: str | None
    default_org_title: str | None
    last_refresh: str | None
    auto_snapshot: bool
    is_active: bool = False


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "session"


class SessionAlreadyExistsError(RuntimeError):
    pass


class SessionStore:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    def save(
        self,
        auth_path: Path,
        name: str | None = None,
        *,
        force: bool = False,
        auto_snapshot: bool = False,
        diagnostics: DiagnosticRun | None = None,
    ) -> SessionRecord:
        if diagnostics is not None:
            diagnostics.record_event(
                "save_started",
                auth_path=auth_path,
                requested_session_name=name,
                auto_snapshot=auto_snapshot,
            )
        snapshot = load_auth_snapshot(
            auth_path,
            recorder=diagnostics.record_event if diagnostics is not None else None,
        )
        session_name = name or snapshot.email or "session"
        slug = slugify(session_name)
        self.paths.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.paths.snapshots_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = self.paths.snapshots_dir / f"{slug}.auth.json"
        metadata_path = self.paths.sessions_dir / f"{slug}.json"
        if metadata_path.exists() and not force:
            raise SessionAlreadyExistsError(session_name)

        shutil.copy2(auth_path, snapshot_path)
        record = SessionRecord(
            name=session_name,
            slug=slug,
            snapshot_path=snapshot_path,
            metadata_path=metadata_path,
            email=snapshot.email,
            plan=snapshot.plan,
            account_id=snapshot.account_id,
            default_org_title=snapshot.default_org_title,
            last_refresh=snapshot.last_refresh,
            auto_snapshot=auto_snapshot,
        )
        metadata_path.write_text(
            json.dumps(
                {
                    "name": record.name,
                    "slug": record.slug,
                    "snapshot_path": str(record.snapshot_path),
                    "email": record.email,
                    "plan": record.plan,
                    "account_id": record.account_id,
                    "default_org_title": record.default_org_title,
                    "last_refresh": record.last_refresh,
                    "auto_snapshot": record.auto_snapshot,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            )
        )
        if diagnostics is not None:
            diagnostics.record_event(
                "save_completed",
                session_name=record.name,
                auto_snapshot=record.auto_snapshot,
            )
            if record.auto_snapshot:
                diagnostics.record_event("autosave_created", session_name=record.name)
        return record

    def list_records(self) -> list[SessionRecord]:
        current_bytes = (
            self.paths.live_auth_file.read_bytes()
            if self.paths.live_auth_file.exists()
            else None
        )
        records = []
        for metadata_path in sorted(self.paths.sessions_dir.glob("*.json")):
            record = load_record(metadata_path)
            is_active = (
                current_bytes is not None
                and record.snapshot_path.exists()
                and record.snapshot_path.read_bytes() == current_bytes
            )
            records.append(replace(record, is_active=is_active))
        return records

    def get_record(
        self, name: str, diagnostics: DiagnosticRun | None = None
    ) -> SessionRecord:
        if diagnostics is not None:
            diagnostics.record_event("record_lookup_started", session_name=name)
        for record in self.list_records():
            if record.name == name:
                return record
        if diagnostics is not None:
            diagnostics.record_event("record_lookup_failed", session_name=name)
        raise KeyError(name)

    def activate(
        self, name: str, diagnostics: DiagnosticRun | None = None
    ) -> SessionRecord:
        target = self.get_record(name, diagnostics=diagnostics)
        live_bytes = (
            self.paths.live_auth_file.read_bytes()
            if self.paths.live_auth_file.exists()
            else None
        )
        if live_bytes is not None:
            matches_existing = any(
                record.snapshot_path.exists()
                and record.snapshot_path.read_bytes() == live_bytes
                for record in self.list_records()
            )
            if not matches_existing:
                self.save(
                    self.paths.live_auth_file,
                    name=build_autosave_name(),
                    auto_snapshot=True,
                    diagnostics=diagnostics,
                )
        write_atomic(
            self.paths.live_auth_file,
            target.snapshot_path.read_bytes(),
            0o600,
            diagnostics=diagnostics,
        )
        if diagnostics is not None:
            diagnostics.record_event("activate_completed", session_name=name)
        return self.get_record(name, diagnostics=diagnostics)

    def delete(self, name: str, diagnostics: DiagnosticRun | None = None) -> None:
        record = self.get_record(name, diagnostics=diagnostics)
        record.metadata_path.unlink(missing_ok=True)
        record.snapshot_path.unlink(missing_ok=True)
        if diagnostics is not None:
            diagnostics.record_event("delete_completed", session_name=name)


def load_record(metadata_path: Path) -> SessionRecord:
    payload = json.loads(metadata_path.read_text())
    return SessionRecord(
        name=payload["name"],
        slug=payload["slug"],
        snapshot_path=Path(payload["snapshot_path"]),
        metadata_path=metadata_path,
        email=payload.get("email"),
        plan=payload.get("plan"),
        account_id=payload.get("account_id"),
        default_org_title=payload.get("default_org_title"),
        last_refresh=payload.get("last_refresh"),
        auto_snapshot=bool(payload.get("auto_snapshot")),
        is_active=bool(payload.get("is_active", False)),
    )


def build_autosave_name() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"autosave-{timestamp}"


def write_atomic(
    path: Path,
    content: bytes,
    mode: int,
    diagnostics: DiagnosticRun | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if diagnostics is not None:
        diagnostics.record_event("atomic_write_started", path=path)
        diagnostics.attach_path_context("live_auth_file", path)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    if diagnostics is not None:
        # Capture the temp path before chmod/replace so a mid-flight failure
        # still leaves enough IO context in the diagnostics artifact.
        diagnostics.attach_path_context("temp_write_path", temp_path)
    os.chmod(temp_path, mode)
    temp_path.replace(path)
    if diagnostics is not None:
        diagnostics.attach_path_context("live_auth_file", path)
        diagnostics.record_event("atomic_write_completed", path=path)
