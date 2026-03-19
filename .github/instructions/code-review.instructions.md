---
applyTo: "**"
excludeAgent: "coding-agent"
---

When reviewing pull requests in this repository, prioritize behavioral and operational risks over cosmetic style comments.

Focus first on:

- data loss or corruption in saved sessions and live auth state
- auth and session safety around `~/.codex/auth.json`
- regressions in `install.sh`, `update`, managed-copy behavior, symlink resolution, and launcher path handling
- CLI behavior changes that break documented usage or output
- missing or weakened tests, especially anything that could reduce `100%` coverage
- README drift when commands, install flow, or storage layout change

Pay special attention to atomic writes, file permissions, path handling, and assumptions about clean or pre-existing user state.

Avoid low-signal comments about formatting or subjective style unless they indicate a real bug, maintenance risk, or user-facing regression.
