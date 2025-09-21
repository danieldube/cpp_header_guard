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
