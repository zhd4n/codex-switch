# GitHub Copilot Review Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Configure automatic GitHub Copilot pull request review for `codex-switch` and add repository-specific Copilot instructions.

**Architecture:** The repository will gain two instruction files under `.github/`, while repository review automation will be configured through the GitHub repository rulesets API using `gh api`. Verification will check both repository contents and live GitHub ruleset state.

**Tech Stack:** GitHub CLI (`gh`), GitHub REST API, Markdown instruction files, git

---

### Task 1: Add Repo-Wide Copilot Instructions

**Files:**
- Create: `.github/copilot-instructions.md`

**Step 1: Write the failing test**

```text
Define the required repository context and constraints that Copilot cannot infer automatically.
```

**Step 2: Run test to verify it fails**

Run: `test -f .github/copilot-instructions.md`
Expected: FAIL because the file does not exist yet.

**Step 3: Write minimal implementation**

```markdown
# Repository Instructions

- Python CLI project in `src/codex_switch/`
- Public install entrypoint is `install.sh`
- Mutable state belongs in `~/.codex-switch/`
- Preserve autosnapshot, safe delete, update/install contract, README alignment, and `100%` coverage
```

**Step 4: Run test to verify it passes**

Run: `test -f .github/copilot-instructions.md`
Expected: PASS

**Step 5: Commit**

```bash
git add .github/copilot-instructions.md
git commit -m "docs: add copilot repository instructions"
```

### Task 2: Add Review-Only Copilot Instructions

**Files:**
- Create: `.github/instructions/code-review.instructions.md`

**Step 1: Write the failing test**

```text
Define review-only guidance focused on auth safety, install/update regressions, and coverage.
```

**Step 2: Run test to verify it fails**

Run: `test -f .github/instructions/code-review.instructions.md`
Expected: FAIL because the file does not exist yet.

**Step 3: Write minimal implementation**

```markdown
---
applyTo: "**"
excludeAgent: "coding-agent"
---

Prioritize behavioral bugs, data loss, auth/session safety, install/update issues, symlink/path bugs, docs drift, and coverage regressions.
```

**Step 4: Run test to verify it passes**

Run: `test -f .github/instructions/code-review.instructions.md`
Expected: PASS

**Step 5: Commit**

```bash
git add .github/instructions/code-review.instructions.md
git commit -m "docs: add copilot review instructions"
```

### Task 3: Create Automatic Copilot Review Ruleset

**Files:**
- Modify: live GitHub repository settings through `gh api`

**Step 1: Write the failing test**

```text
Query repository rulesets and confirm there is no Copilot code review ruleset yet.
```

**Step 2: Run test to verify it fails**

Run: `gh api repos/zhd4n/codex-switch/rulesets`
Expected: no matching `copilot_code_review` ruleset.

**Step 3: Write minimal implementation**

```bash
gh api repos/zhd4n/codex-switch/rulesets \
  --method POST \
  --input <json-payload-with-branch-ruleset-and-copilot_code_review>
```

**Step 4: Run test to verify it passes**

Run: `gh api repos/zhd4n/codex-switch/rulesets`
Expected: a branch ruleset targeting `master` with `copilot_code_review`, `review_on_push=true`, and `review_draft_pull_requests=true`

**Step 5: Commit**

```bash
git add .github/copilot-instructions.md .github/instructions/code-review.instructions.md
git commit -m "docs: add copilot review configuration"
```

### Task 4: Verify and Push

**Files:**
- Modify: remote branch state only

**Step 1: Write the failing test**

```text
Re-check branch status, repository files, and live ruleset state after setup.
```

**Step 2: Run test to verify it fails**

Run: `git status --short --branch`
Expected: branch is ahead or has unpushed changes before final push.

**Step 3: Write minimal implementation**

```bash
git push
```

**Step 4: Run test to verify it passes**

Run:
- `git status --short --branch`
- `gh api repos/zhd4n/codex-switch/rulesets`

Expected:
- branch clean and aligned with remote
- Copilot review ruleset present

**Step 5: Commit**

```bash
# No additional commit if only pushing remote state
```
