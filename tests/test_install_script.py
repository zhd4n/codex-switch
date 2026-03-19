import subprocess

from conftest import build_install_env


def test_install_script_creates_managed_clone_and_shim(repo_root, isolated_home):
    result = subprocess.run(
        ["bash", "install.sh"],
        cwd=repo_root,
        env=build_install_env(isolated_home),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert (isolated_home / ".codex-switch" / "tmp" / "codex-switch").exists()
    assert (isolated_home / ".local" / "bin" / "codex-switch").exists()

    help_result = subprocess.run(
        ["codex-switch", "--help"],
        env={
            **build_install_env(isolated_home),
            "PATH": f"{isolated_home / '.local' / 'bin'}:{build_install_env(isolated_home)['PATH']}",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert help_result.returncode == 0
    assert "codex-switch" in help_result.stdout
