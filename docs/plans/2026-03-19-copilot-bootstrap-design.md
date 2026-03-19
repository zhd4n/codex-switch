# Copilot Bootstrap PR Design

## Goal

Create a minimal bootstrap pull request that lands Copilot review instructions in `master` before retrying GitHub Copilot code review on the main `codex-switch` feature PR.

## Context

- The repository already has an active GitHub ruleset for automatic Copilot review.
- The main feature PR already contains `.github/copilot-instructions.md` and `.github/instructions/code-review.instructions.md`.
- GitHub Copilot code review reads custom instructions from the base branch of a pull request, not from the head branch.
- The repository also has a separate automated reviewer, `chatgpt-codex-connector[bot]`, which is distinct from GitHub Copilot.

## Approaches Considered

### 1. Merge the feature PR first

This would eventually place the instructions in `master`, but it defeats the purpose of improving review quality on the current feature PR.

### 2. Create a tiny bootstrap PR with only the `.github/` instruction files

This is the recommended approach. It isolates the instruction bootstrap from the functional CLI work and minimizes merge risk.

### 3. Add docs or README updates to the bootstrap PR

Rejected for now. The bootstrap PR should stay as small as possible so it can merge quickly and become the base branch context for later Copilot reviews.

## Approved Design

- Create a new branch from `master` in a separate worktree.
- Copy only these two files into that branch:
  - `.github/copilot-instructions.md`
  - `.github/instructions/code-review.instructions.md`
- Do not include `docs/plans`, `README.md`, or any functional code changes.
- Open a dedicated bootstrap PR.
- After that PR is merged into `master`, retry GitHub Copilot review on the main feature PR.

## Risks And Handling

- If Copilot still does not review the main PR after the bootstrap PR is merged, the remaining blocker is likely product availability or account entitlement rather than repository configuration.
- The bootstrap PR must not accidentally include functional files from the larger feature branch, so the work will be done in an isolated worktree created from `master`.
