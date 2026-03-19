import subprocess

from conftest import build_cli_env


def test_update_refreshes_managed_clone_and_reinstalls(repo_root, isolated_home):
    result = subprocess.run(
        ["python3", "-m", "codex_switch.cli", "update"],
        cwd=repo_root,
        env=build_cli_env(isolated_home, repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert (isolated_home / ".codex-switch" / "tmp" / "codex-switch").exists()
    assert (isolated_home / ".local" / "bin" / "codex-switch").exists()
    assert "updated" in result.stdout.lower()
