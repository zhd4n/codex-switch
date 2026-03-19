import argparse
from pathlib import Path

from codex_switch.auth import load_auth_snapshot
from codex_switch.paths import AppPaths
from codex_switch.store import SessionStore

COMMANDS = ("save", "list", "activate", "status", "delete", "update")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-switch")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        subparsers.add_parser(name)
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


def main(argv: list[str] | None = None, home: Path | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = SessionStore(AppPaths.from_home(home or Path.home()))
    if args.command == "status":
        return handle_status(store)
    if args.command == "list":
        return handle_list(store)
    raise NotImplementedError(args.command)
