from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from codex_switch.auth import load_auth_snapshot
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
    auto_snapshot: bool


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
    ) -> SessionRecord:
        snapshot = load_auth_snapshot(auth_path)
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
                    "auto_snapshot": record.auto_snapshot,
                    "saved_at": datetime.now(UTC).isoformat(),
                },
                indent=2,
            )
        )
        return record
