---
name: update_python_modules_from_nautobot
description: Sync selected Python dependency versions in this project with the versions pinned in the upstream Nautobot repository.
argument-hint: "Optional module names, or 'all'."
---

You are responsible for aligning Python dependency versions in this project's pyproject.toml with the versions pinned in the upstream Nautobot repository.

## Workflow

1. Locate the upstream Nautobot repository and read its pyproject.toml.
2. Use Poetry consistently for all Python work. Prefer `poetry run python ...` or `poetry run <tool>` rather than bare `python` so the interpreter and environment match the project.
3. Run `poetry update` to refresh the local environment and lock file after any dependency changes.
4. Extract the exact pinned versions for the requested modules, or for all modules if requested.
5. Compare the local and upstream specs with the provided helper script before editing anything: `poetry run python .github/agents/compare_upstream_dependencies.py [module ...]`.
6. Update matching entries in this project's pyproject.toml only when the source is from PyPI.
7. Preserve the existing formatting, comments, ordering, and dependency grouping.
8. Report which modules were updated, which were left unchanged, and any skipped git-based dependencies.

## Agent requirements

- [Ubiquitous] The agent shall preserve the existing formatting, comments, and structural layout of pyproject.toml.
- [Ubiquitous] The agent shall not make unrelated changes or perform any refactoring beyond dependency version updates.
- [Event-driven] When the agent is invoked, the agent shall read the upstream [Nautobot repository's pyproject.toml](https://raw.githubusercontent.com/nautobot/nautobot/refs/heads/develop/pyproject.toml) and extract the exact pinned versions of the requested Python modules.
- [Event-driven] When the agent updates this project's pyproject.toml, the agent shall update only dependencies that are sourced from PyPI.
- [Event-driven] When the agent updates this project's pyproject.toml, the agent shall not modify dependencies declared with a git source.
- [Event-driven] The agent shall not rely on the bare `python` command for dependency inspection or script execution; it must use `poetry run python` so the correct interpreter and environment are used.
- [Event-driven] If the upstream repository or its pyproject.toml cannot be found, the agent shall stop and report the issue instead of making assumptions.
- [Event-driven] When the agent completes an edit to the dependency file, the agent shall verify that the file remains valid TOML and report any missing or unresolved dependencies.
- [Event-driven] The agent should validate the comparison logic with `poetry run python .github/agents/compare_upstream_dependencies.py` before claiming that a dependency set is aligned.
