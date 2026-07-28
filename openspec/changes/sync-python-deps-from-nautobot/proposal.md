## Why

Projects that share dependencies with Nautobot (e.g., `celery`, `redis`, `pydantic`) can silently diverge from the versions Nautobot actually tests against. The only way to discover a conflict today is at runtime or during a failing test run. This change introduces an automated, repeatable process to keep shared dependencies in sync with the upstream Nautobot release pinned in `invoke.yml`.

## What Changes

- Introduce a reusable agent (`update_python_modules_from_nautobot`) that reads the Nautobot version from `invoke.yml`, fetches the upstream `pyproject.toml` from GitHub at that tag, and updates the local `pyproject.toml` with any shared modules where Nautobot's minimum version is higher.
- Python version constraint in `[tool.poetry.dependencies]` is always synced to match Nautobot's `requires-python` exactly.
- Modules sourced from a git URL are skipped (not compared against PyPI).
- When no updates are found, the agent reports that and exits without touching any file.
- When updates are found, the agent applies them and runs `poetry update` to regenerate the lock file.

## Capabilities

### New Capabilities

- `nautobot-dep-sync`: Read `nautobot_ver` from `invoke.yml`, fetch Nautobot's `pyproject.toml` from GitHub at `v{nautobot_ver}`, compare shared PyPI dependencies, update versions and Python constraint in the local `pyproject.toml`, then run `poetry update`.

### Modified Capabilities

<!-- none -->

## Impact

- Modifies `pyproject.toml` (and `poetry.lock` indirectly via `poetry update`) in any project that runs this agent.
- Requires network access to `raw.githubusercontent.com` at invocation time.
- No database, API, or Nautobot runtime changes.
- Reusable: the agent and its instructions live in `.github/` and can be copied or referenced across any Poetry-based Nautobot-adjacent project.
