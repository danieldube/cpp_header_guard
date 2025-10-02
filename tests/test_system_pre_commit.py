"""System test that exercises the pre-commit hook distribution."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import header_guard


def ensure_pre_commit_installed() -> None:
    """Install the pre-commit package if it is not yet available."""

    try:
        importlib.import_module("pre_commit")
    except ModuleNotFoundError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pre-commit"],
            check=True,
        )
        importlib.invalidate_caches()
        importlib.import_module("pre_commit")


def test_pre_commit_hook_updates_cpp_header(tmp_path: Path) -> None:
    """Run the published pre-commit hook to rewrite a header guard."""

    repo = tmp_path / "project"
    repo.mkdir()

    subprocess.run(["git", "init"], check=True, cwd=repo)

    config = textwrap.dedent(
        """
        repos:
          - repo: https://github.com/danieldube/cpp_header_guard
            rev: main
            hooks:
              - id: header-guard
        """
    )
    (repo / ".pre-commit-config.yaml").write_text(config, encoding="utf-8")

    header = repo / "include" / "value.hpp"
    header.parent.mkdir(parents=True)
    header.write_text("int value;\n", encoding="utf-8")

    ensure_pre_commit_installed()

    env = os.environ | {"PRE_COMMIT_HOME": str(repo / ".pre-commit-cache")}
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pre_commit",
            "run",
            "header-guard",
            "--files",
            str(header),
        ],
        check=True,
        cwd=repo,
        env=env,
    )

    guard = header_guard.header_guard_name(repo, header)
    content = header.read_text(encoding="utf-8")
    assert content.startswith(f"#ifndef {guard}\n#define {guard}\n\n")
    assert content.rstrip().endswith(f"#endif  // {guard}")

