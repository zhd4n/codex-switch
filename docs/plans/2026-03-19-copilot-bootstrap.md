# Copilot Bootstrap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Land Copilot custom instruction files in `master` via a minimal bootstrap PR, then use that base branch context for future Copilot reviews.

**Architecture:** The implementation is intentionally split from the main feature branch. Planning artifacts stay in the current branch, while the bootstrap PR is built from a clean worktree off `master` and contains only the `.github/` Copilot instruction files.

**Tech Stack:** Git, GitHub CLI, repository rulesets, Markdown instruction files

---

### Task 1: Record The Approved Bootstrap Design

**Files:**
- Create: `docs/plans/2026-03-19-copilot-bootstrap-design.md`
- Create: `docs/plans/2026-03-19-copilot-bootstrap.md`

**Step 1: Write the approved design doc**

Capture the purpose of the bootstrap PR, why it must be separate from the main feature PR, and the exact file scope.

**Step 2: Write the implementation plan**

Describe the isolated worktree flow, file copy scope, commit intent, and PR creation flow.

**Step 3: Commit the planning docs**

Run:

```bash
git add docs/plans/2026-03-19-copilot-bootstrap-design.md docs/plans/2026-03-19-copilot-bootstrap.md
git commit -m "docs: add copilot bootstrap plan"
```

Expected: a single docs-only commit on the current feature branch.

### Task 2: Create An Isolated Bootstrap Worktree From `master`

**Files:**
- Modify: `.worktrees/` contents only via `git worktree add`

**Step 1: Verify `.worktrees/` is ignored**

Run:

```bash
git check-ignore -q .worktrees
```

Expected: success exit code.

**Step 2: Create the bootstrap branch from `master`**

Run:

```bash
git worktree add .worktrees/zhdan-copilot-bootstrap -b zhdan/copilot-bootstrap master
```

Expected: a clean worktree rooted at `master`.

**Step 3: Verify the baseline is clean**

Run:

```bash
git status --short
```

Expected: no output.

### Task 3: Add Only The Copilot Instruction Files

**Files:**
- Create: `.github/copilot-instructions.md`
- Create: `.github/instructions/code-review.instructions.md`

**Step 1: Copy the approved instruction contents**

Bring in the exact instruction files already validated on the main feature branch.

**Step 2: Verify scope**

Run:

```bash
git status --short
```

Expected: only the two `.github/` files appear as new files.

**Step 3: Commit the bootstrap change**

Run:

```bash
git add .github/copilot-instructions.md .github/instructions/code-review.instructions.md
git commit -m "docs: add copilot review instructions to base branch"
```

Expected: one minimal docs-only commit in the bootstrap branch.

### Task 4: Push And Open The Bootstrap PR

**Files:**
- No repository file changes beyond the committed `.github/` files

**Step 1: Push the bootstrap branch**

Run:

```bash
git push -u origin zhdan/copilot-bootstrap
```

Expected: remote branch created successfully.

**Step 2: Open the PR**

Run:

```bash
gh pr create --base master --head zhdan/copilot-bootstrap --title "docs: add copilot review instructions to base branch" --body "## Summary
- add repository-wide Copilot review instructions to the base branch
- add review-only Copilot guidance for PR feedback

## Why
- GitHub Copilot code review reads custom instructions from the base branch of a pull request
- this bootstrap PR puts the instruction files into \`master\` before re-triggering Copilot review on the main feature PR"
```

Expected: a dedicated bootstrap PR URL.

### Task 5: Prepare The Next Review Trigger

**Files:**
- No additional files

**Step 1: Report the bootstrap PR URL**

State clearly that this PR should merge before retrying Copilot review on the main feature PR.

**Step 2: After merge, re-request Copilot review on PR `#1`**

Use either the GitHub UI Reviewers menu or the known API reviewer slug for Copilot after `master` contains the instruction files.

**Step 3: Verify whether Copilot review appears**

Check PR reviews and review requests again before claiming success.
