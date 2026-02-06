"""MkDocs Macros plugin default module.

The `mkdocs-macros-plugin` looks for a Python module named `main` by default.
Keeping this file at the repository root avoids noisy "No default module `main` found"
messages during `mkdocs build`.
"""


def define_env(env):  # noqa: ARG001
    # Intentionally empty for now.
    return
