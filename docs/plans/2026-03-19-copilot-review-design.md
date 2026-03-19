# GitHub Copilot Review Configuration Design

**Date:** 2026-03-19

## Goal

Enable automatic GitHub Copilot review for pull requests in `zhd4n/codex-switch`, and provide repository-specific instructions so Copilot reviews focus on real risks in this project.

## Requirements

- Configure automatic Copilot review for the repository, targeting the default branch `master`.
- Enable review for draft pull requests.
- Enable re-review on new pushes.
- Add repository custom instructions for the repo as a whole.
- Add review-only instructions that tighten review focus without affecting coding-agent behavior.
- Prefer CLI/API automation over manual UI setup.
- Fall back to manual UI guidance only if GitHub rejects ruleset configuration for account/product reasons.

## Architecture

Use a layered setup:

1. GitHub repository ruleset for automatic Copilot code review
2. Repo-wide `.github/copilot-instructions.md`
3. Review-only `.github/instructions/code-review.instructions.md`

This gives a clean separation:

- ruleset decides **when** Copilot reviews run
- repo-wide instructions describe **what this repository is**
- review-only instructions define **what Copilot should prioritize when reviewing pull requests**

## Ruleset Design

Create a repository branch ruleset for `master` with a `copilot_code_review` rule configured to:

- review draft pull requests
- review new pushes to open pull requests

The ruleset should not introduce unrelated branch protections in the same change. Its scope is only to enable Copilot review automation.

## Instruction Design

### Repo-wide instructions

The repo-wide file should explain:

- this is a Python CLI project in `src/codex_switch/`
- installation entrypoint is `install.sh`
- launcher is `bin/codex-switch`
- mutable state must live in `~/.codex-switch/`
- `activate` must preserve unsaved live auth via autosnapshot
- `delete` must not mutate live `~/.codex/auth.json`
- `update` must refresh the managed copy and rerun installation
- README must stay aligned with actual CLI behavior
- test changes must preserve `pytest` success and `100%` coverage

### Review-only instructions

The review-only file should apply to all paths and exclude the coding agent. It should direct Copilot review to prioritize:

- data loss
- auth/session safety
- install/update regressions
- symlink and path resolution problems
- CLI UX regressions
- documentation drift
- coverage regressions

It should explicitly de-prioritize cosmetic comments that do not affect behavior.

## Verification

After applying the configuration:

- verify ruleset creation via `gh api repos/zhd4n/codex-switch/rulesets`
- verify `.github/` files exist in the branch
- verify branch remains clean and pushed

## Expected Fallback

If the GitHub API rejects the Copilot ruleset due to missing product availability or policy restrictions, keep the instruction files committed and provide exact UI steps for the user to enable automatic Copilot review manually.
