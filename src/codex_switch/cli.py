import argparse


COMMANDS = ("save", "list", "activate", "status", "delete", "update")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-switch")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        subparsers.add_parser(name)
    return parser
