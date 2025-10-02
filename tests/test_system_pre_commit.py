"""System test that exercises the pre-commit hook distribution."""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

import header_guard


@pytest.mark.skipif(
    not shutil.which("pre-commit"),
    reason="pre-commit executable is required for this test",
)
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

    env = os.environ | {"PRE_COMMIT_HOME": str(repo / ".pre-commit-cache")}
    subprocess.run(
        ["pre-commit", "run", "header-guard", "--files", str(header)],
        check=True,
        cwd=repo,
        env=env,
    )

    guard = header_guard.header_guard_name(repo, header)
    content = header.read_text(encoding="utf-8")
    assert content.startswith(f"#ifndef {guard}\n#define {guard}\n\n")
    assert content.rstrip().endswith(f"#endif  // {guard}")

