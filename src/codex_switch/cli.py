import argparse
from pathlib import Path

from codex_switch.auth import load_auth_snapshot
from codex_switch.paths import AppPaths
from codex_switch.store import SessionStore

COMMANDS = ("save", "list", "activate", "status", "delete", "update")


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
    print(f"email: {snapshot.email}")
    print(f"plan: {snapshot.plan}")
    print(f"account_id: {snapshot.account_id}")
    print(f"session_id: {snapshot.session_id}")
    return 0


def handle_list(store: SessionStore) -> int:
    print("active name email plan account_id")
    for record in store.list_records():
        active = "*" if record.is_active else " "
        print(
            f"{active} {record.name} {record.email} {record.plan} {record.account_id}"
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


def main(argv: list[str] | None = None, home: Path | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = SessionStore(AppPaths.from_home(home or Path.home()))
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
    raise NotImplementedError(args.command)
