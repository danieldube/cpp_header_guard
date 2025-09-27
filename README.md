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
```

The hook rewrites any staged header files so they use the repository-relative
guard name convention implemented by this tool.

### Configurable spacing

The tool accepts an optional `--spaces-between-endif-and-comment` argument to
control how many spaces appear between `#endif` and the trailing comment. The
default is `2`:

```bash
header-guard --spaces-between-endif-and-comment=1 path/to/header.hpp
```

When using the tool via pre-commit you can pass the same flag through the hook
configuration:

```yaml
repos:
  - repo: https://github.com/danieldube/cpp_header_guard
    rev: v0.1.0
    hooks:
      - id: header-guard
        args: ["--spaces-between-endif-and-comment=1"]
```
