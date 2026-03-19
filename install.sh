#!/usr/bin/env bash
set -euo pipefail

APP_HOME="${HOME}/.codex-switch"
MANAGED_REPO="${APP_HOME}/tmp/codex-switch"
BIN_DIR="${HOME}/.local/bin"

mkdir -p \
  "${APP_HOME}/sessions" \
  "${APP_HOME}/snapshots" \
  "${APP_HOME}/tmp" \
  "${BIN_DIR}"

rsync -a --delete \
  --exclude '.git' \
  --exclude '.worktrees' \
  --exclude '.pytest_cache' \
  --exclude '__pycache__' \
  ./ "${MANAGED_REPO}/"

ln -sfn "${MANAGED_REPO}/bin/codex-switch" "${BIN_DIR}/codex-switch"
