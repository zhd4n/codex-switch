# GitHub CI Design

## Goal

Add a minimal GitHub Actions pipeline that blocks broken changes before merge by enforcing formatting, linting, tests, and the existing `100%` coverage requirement.

## Context

- The repository is a small Python CLI project with application code in `src/codex_switch/` and tests in `tests/`.
- `pytest.ini` already enforces branch coverage and `--cov-fail-under=100`, so CI does not need separate coverage logic.
- The repository does not currently contain a GitHub Actions workflow.
- `tests/test_python_compat.py` explicitly checks that `codex_switch.store` imports under `python3.10`, so the simplest non-matrix CI target is Python `3.10`.
- A dry run with Ruff showed that `ruff check` already passes, while `ruff format --check` would currently reformat 7 files. That means introducing formatting as a required gate should include one initial formatting cleanup.
- Adding a bare `pyproject.toml` for Ruff configuration means local `uv run --with ...` commands are no longer viable in this repository, because `uv run` expects a `[project]` table. Local docs should therefore use `uvx --with-requirements requirements-dev.txt ...` while CI continues to use `pip`.

## Approaches Considered

### 1. One workflow with separate `format`, `lint`, and `test` jobs

This is the recommended approach. It keeps the YAML small, gives clear PR status signals, and avoids overengineering while still making failures easy to diagnose.

### 2. One workflow with a single sequential job

This is slightly shorter on paper, but it hides which quality gate failed until the full log is opened. That trade-off is not worth it here because splitting into three jobs adds very little complexity.

### 3. A multi-version Python matrix

This would be useful if the project had an explicit support policy across several interpreter versions. Right now the repository only has one concrete compatibility assertion, Python `3.10`, so a matrix would add maintenance cost without a clear requirement.

## Approved Design

- Add a single workflow at `.github/workflows/ci.yml`.
- Trigger it on:
  - `pull_request`
  - `push` to `master`
- Add `concurrency` so stale runs on the same branch are canceled automatically.
- Use `ubuntu-latest` and a single configured Python version: `3.10`.
- Install tooling with standard Python packaging commands and the repository's dev dependency file.
- Add Ruff as the single tool for both formatting and linting:
  - `ruff format --check .`
  - `ruff check .`
- Keep tests on the existing pytest configuration:
  - `pytest -q`
  - coverage stays enforced by `pytest.ini`
- Add a minimal Ruff configuration in `pyproject.toml` so the repository owns its lint/format settings explicitly instead of burying them in workflow commands.
- Add `ruff==0.15.6` to `requirements-dev.txt` so local development and CI use the same formatter version and avoid formatting drift over time.
- Keep local developer commands on the repository's existing `uv` workflow by using `uvx --with-requirements requirements-dev.txt ...`, so the local checks use the same dependency set as CI without requiring a `[project]` table.
- Update `README.md` to document CI-equivalent local checks and a separate fix-format command.

## Risks And Handling

- The first CI rollout will likely require a one-time formatting commit because Ruff already wants to reformat 7 files. That should be done as part of the same change so CI starts green.
- Choosing only Python `3.10` keeps the workflow simple, but it means CI does not validate newer interpreters separately. If the project later adopts an explicit multi-version support policy, the workflow can grow into a matrix without changing its basic structure.
- CI and local developer workflows intentionally use different launchers, `pip` in GitHub Actions and `uvx` locally. The commands are not identical, but the plan should keep the Ruff version pinned in both places so the format and lint results stay aligned.
- No release automation is included. That is intentional because the current install flow is repository-based via `./install.sh`, not package publication or release artifacts.
