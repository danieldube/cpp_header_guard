# cpp-header-guard

Utilities for maintaining consistent include guards in C++ header files.

## Local development

This project uses [Hatch](https://hatch.pypa.io/) to manage its virtual
environments and packaging metadata. Install Hatch (for example via
`pip install hatch`) and then run the built-in tasks:

```bash
# Create the managed environment the first time you work on the project
hatch env create

# Run the test suite
hatch run test

# Enter a shell inside the project environment
hatch shell
```

The pre-commit hooks reuse the same Hatch-managed environment, so the commands
above ensure linting and typing run with the dependencies declared in
`pyproject.toml` and mirrored in `requirements-test.txt`.

## Why a header-guard hook?

Modern compilers support `#pragma once`, but it is a non-standard extension
that can break down when a header is reachable through multiple filesystem
paths (for example because of symlinks, generated files, or network shares).
Traditional include guards avoid these pitfalls because the preprocessor only
needs to reason about a macro name. Unfortunately, hand-written guards often
drift: two developers might choose different macro formats, copy-paste from the
wrong directory, or forget to update the guard when a file moves. Those small
discrepancies make refactors harder and can even reintroduce multiple-inclusion
bugs that `#pragma once` was meant to prevent. The pre-commit hook distributed
with this project standardizes guard names based on the repository layout, so
every header has a deterministic, portable include guard that survives file
renames and cross-platform builds.

## Pre-commit integration

The project publishes a pre-commit hook so repositories can enforce consistent
include guards automatically. Add the following to your
`.pre-commit-config.yaml` to enable it:

```yaml
repos:
  - repo: https://github.com/danieldube/cpp_header_guard
    rev: v0.1.0  # Replace with the desired tag or commit.
    hooks:
      - id: header-guard
        # Optional: control the spacing before the trailing comment.
        args: ["--spaces-between-endif-and-comment", "3"]
```

### Step-by-step usage instructions

1. **Install pre-commit** (once per machine): `pip install pre-commit`.
2. **Install the hook locally** inside your repository: run
   `pre-commit install`. This configures Git so the hook runs on every commit.
3. **(Optional) Run it on demand** for all tracked headers with
   `pre-commit run header-guard --all-files`.
4. **Commit as usual.** When you `git commit`, the hook rewrites any staged
   header files so they use the repository-relative guard name convention
   implemented by this tool. If it makes changes, the commit will stop so you
   can review and re-stage the files before retrying. Once all headers conform
   to the rule, the commit proceeds normally.

The command line interface exposes the same
`--spaces-between-endif-and-comment` option, allowing you to customize how many
blanks appear between `#endif` and the trailing comment.
