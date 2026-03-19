import os
import subprocess


def test_store_module_imports_under_python310(repo_root):
    result = subprocess.run(
        ["python3.10", "-c", "import codex_switch.store"],
        cwd=repo_root,
        env={**os.environ, "PYTHONPATH": str(repo_root / "src")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
