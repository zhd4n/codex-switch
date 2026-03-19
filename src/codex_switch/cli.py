import argparse
import os
from pathlib import Path
import shutil
import subprocess

from codex_switch.auth import load_auth_snapshot
from codex_switch.paths import AppPaths
from codex_switch.store import SessionStore

COMMANDS = ("save", "list", "activate", "status", "delete", "update")
DEFAULT_REPO_URL = "https://github.com/zhd4n/codex-switch.git"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-switch")
    subparsers = parser.add_subparsers(dest="command", required=True)
    save_parser = subparsers.add_parser("save")
    save_parser.add_argument("name", nargs="?")

    subparsers.add_parser("list")
    subparsers.add_parser("status")
    subparsers.add_parser("update")

    activate_parser = subparsers.add_parser("activate")
    activate_parser.add_argument("name")

    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("name")
    return parser


def handle_status(store: SessionStore) -> int:
    snapshot = load_auth_snapshot(store.paths.live_auth_file)
    print(f"auth_mode: {snapshot.auth_mode}")
    print(f"email: {snapshot.email}")
    print(f"name: {snapshot.name}")
    print(f"plan: {snapshot.plan}")
    print(f"account_id: {snapshot.account_id}")
    print(f"session_id: {snapshot.session_id}")
    print(f"default_org: {snapshot.default_org_title}")
    print(f"email_verified: {snapshot.email_verified}")
    print(f"last_refresh: {snapshot.last_refresh}")
    return 0


def handle_list(store: SessionStore) -> int:
    print("active name email plan account_id default_org last_refresh")
    for record in store.list_records():
        active = "*" if record.is_active else " "
        print(
            f"{active} {record.name} {record.email} {record.plan} "
            f"{record.account_id} {record.default_org_title} {record.last_refresh}"
        )
    return 0


def handle_save(store: SessionStore, name: str | None) -> int:
    store.save(store.paths.live_auth_file, name=name)
    return 0


def handle_activate(store: SessionStore, name: str) -> int:
    store.activate(name)
    return 0


def handle_delete(store: SessionStore, name: str) -> int:
    store.delete(name)
    return 0


def resolve_repo_url() -> str:
    return os.environ.get("CODEX_SWITCH_REPO_URL", DEFAULT_REPO_URL)


def refresh_managed_repo(managed_repo_dir: Path, repo_url: str) -> None:
    managed_repo_dir.parent.mkdir(parents=True, exist_ok=True)
    if (managed_repo_dir / ".git").exists():
        subprocess.run(
            ["git", "-C", str(managed_repo_dir), "pull", "--ff-only"],
            check=True,
            capture_output=True,
            text=True,
        )
        return
    if managed_repo_dir.exists():
        shutil.rmtree(managed_repo_dir)
    subprocess.run(
        ["git", "clone", repo_url, str(managed_repo_dir)],
        check=True,
        capture_output=True,
        text=True,
    )


def handle_update(paths: AppPaths) -> int:
    refresh_managed_repo(paths.managed_repo_dir, resolve_repo_url())
    subprocess.run(
        ["bash", "install.sh"],
        cwd=paths.managed_repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    print("Updated managed codex-switch installation.")
    return 0


def main(argv: list[str] | None = None, home: Path | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = AppPaths.from_home(home or Path.home())
    store = SessionStore(paths)
    if args.command == "save":
        return handle_save(store, args.name)
    if args.command == "activate":
        return handle_activate(store, args.name)
    if args.command == "delete":
        return handle_delete(store, args.name)
    if args.command == "status":
        return handle_status(store)
    if args.command == "list":
        return handle_list(store)
    if args.command == "update":
        return handle_update(paths)
    raise NotImplementedError(args.command)  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
