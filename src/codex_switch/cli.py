import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from codex_switch.auth import load_auth_snapshot
from codex_switch.diagnostics import build_auth_summary
from codex_switch.diagnostics import DiagnosticRun
from codex_switch.paths import AppPaths
from codex_switch.store import SessionAlreadyExistsError
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


def handle_status(
    store: SessionStore, diagnostics: DiagnosticRun | None = None
) -> int:
    if diagnostics is not None:
        diagnostics.context["auth_summary"] = {}
    snapshot = load_auth_snapshot(
        store.paths.live_auth_file,
        recorder=diagnostics.record_event if diagnostics is not None else None,
    )
    if diagnostics is not None:
        diagnostics.context["auth_summary"] = build_auth_summary(snapshot)
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


def handle_save(
    store: SessionStore, name: str | None, diagnostics: DiagnosticRun | None = None
) -> int:
    store.save(store.paths.live_auth_file, name=name, diagnostics=diagnostics)
    return 0


def handle_activate(
    store: SessionStore, name: str, diagnostics: DiagnosticRun | None = None
) -> int:
    store.activate(name, diagnostics=diagnostics)
    return 0


def handle_delete(
    store: SessionStore, name: str, diagnostics: DiagnosticRun | None = None
) -> int:
    store.delete(name, diagnostics=diagnostics)
    return 0


def resolve_repo_url() -> str:
    return os.environ.get("CODEX_SWITCH_REPO_URL", DEFAULT_REPO_URL)


def is_debug_enabled() -> bool:
    return os.environ.get("CODEX_SWITCH_DEBUG") == "1"


def tail_lines(value: str | None, *, limit: int = 10) -> list[str]:
    if not value:
        return []
    return value.splitlines()[-limit:]


def run_subprocess(
    cmd: list[str],
    *,
    diagnostics: DiagnosticRun | None = None,
    **kwargs,
):
    started = time.monotonic()
    if diagnostics is not None:
        diagnostics.record_event("subprocess_started", command=cmd)
    try:
        completed = subprocess.run(cmd, **kwargs)
    except subprocess.CalledProcessError as error:
        if diagnostics is not None:
            details = {
                "command": list(error.cmd) if isinstance(error.cmd, (list, tuple)) else [str(error.cmd)],
                "exit_code": error.returncode,
                "stdout_tail": tail_lines(error.output),
                "stderr_tail": tail_lines(error.stderr),
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
            diagnostics.record_subprocess_failure(**details)
        raise
    if diagnostics is not None:
        diagnostics.record_event(
            "subprocess_completed",
            command=cmd,
            duration_ms=round((time.monotonic() - started) * 1000),
        )
    return completed


def refresh_managed_repo(
    managed_repo_dir: Path,
    repo_url: str,
    *,
    diagnostics: DiagnosticRun | None = None,
) -> None:
    managed_repo_dir.parent.mkdir(parents=True, exist_ok=True)
    if (managed_repo_dir / ".git").exists():
        run_subprocess(
            ["git", "-C", str(managed_repo_dir), "pull", "--ff-only"],
            diagnostics=diagnostics,
            check=True,
            capture_output=True,
            text=True,
        )
        return
    if managed_repo_dir.exists():
        shutil.rmtree(managed_repo_dir)
    run_subprocess(
        ["git", "clone", repo_url, str(managed_repo_dir)],
        diagnostics=diagnostics,
        check=True,
        capture_output=True,
        text=True,
    )


def handle_update(paths: AppPaths, diagnostics: DiagnosticRun | None = None) -> int:
    refresh_managed_repo(
        paths.managed_repo_dir,
        resolve_repo_url(),
        diagnostics=diagnostics,
    )
    run_subprocess(
        ["bash", "install.sh"],
        diagnostics=diagnostics,
        cwd=paths.managed_repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    print("Updated managed codex-switch installation.")
    return 0


def dispatch_command(
    args: argparse.Namespace,
    store: SessionStore,
    paths: AppPaths,
    diagnostics: DiagnosticRun | None = None,
) -> int:
    if args.command == "save":
        return handle_save(store, args.name, diagnostics=diagnostics)
    if args.command == "activate":
        return handle_activate(store, args.name, diagnostics=diagnostics)
    if args.command == "delete":
        return handle_delete(store, args.name, diagnostics=diagnostics)
    if args.command == "status":
        return handle_status(store, diagnostics=diagnostics)
    if args.command == "list":
        return handle_list(store)
    if args.command == "update":
        return handle_update(paths, diagnostics=diagnostics)
    raise NotImplementedError(args.command)  # pragma: no cover


def classify_error(error: Exception) -> str:
    """Map concrete exceptions to stable diagnostics categories."""
    if isinstance(error, SessionAlreadyExistsError):
        return "user_error"
    if isinstance(error, KeyError):
        return "user_error"
    if isinstance(error, json.JSONDecodeError):
        return "data_error"
    if isinstance(error, subprocess.CalledProcessError):
        return "dependency_error"
    if isinstance(error, FileNotFoundError):
        if error.filename in {"git", "bash", "install.sh"}:
            return "dependency_error"
        return "user_error"
    if isinstance(error, PermissionError):
        return "system_error"
    if isinstance(error, OSError):
        return "system_error"
    return "system_error"


def main(argv: list[str] | None = None, home: Path | None = None) -> int:
    # Keep one authoritative argv snapshot so parsing and diagnostics describe
    # the same invocation, even when callers let argparse read from sys.argv.
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(raw_argv)
    paths = AppPaths.from_home(home or Path.home())
    store = SessionStore(paths)
    diagnostics = DiagnosticRun(
        command=args.command,
        args=raw_argv,
        diagnostics_dir=paths.diagnostics_dir,
    )
    diagnostics.record_event("command_started")
    try:
        exit_code = dispatch_command(args, store, paths, diagnostics)
        if is_debug_enabled():
            diagnostics.write_success_report()
        return exit_code
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        report_path = diagnostics.write_failure_report(
            error,
            error_category=classify_error(error),
        )
        if report_path is not None:
            print(f"Diagnostic report: {report_path}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
