# cpp-header-guard

Utilities for maintaining consistent include guards in C++ header files.

## Local development

This project uses [Hatch](https://hatch.pypa.io/) to manage its virtual
environments and packaging metadata. Install Hatch (for example via
`pip install hatch`) and then run the built-in tasks:

```bash
# Run the test suite
hatch run test

# Enter a shell inside the project environment
hatch shell
```

The pre-commit hooks reuse the same Hatch-managed environment, so make sure the
environment is created before running `pre-commit run` for the first time.
