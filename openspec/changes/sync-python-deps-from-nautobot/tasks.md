## 1. Agent Scaffolding

- [ ] 1.1 Create `.github/agents/update_python_modules_from_nautobot/` directory and `AGENT.md` entry point
- [ ] 1.2 Add required Python dependencies (`requests`, `packaging`, `tomlkit`) to the agent's own requirements or confirm they are available in the runtime environment
- [ ] 1.3 Create the agent script `update_deps.py` (or equivalent entrypoint) that will be invoked by the agent

## 2. invoke.yml Reader

- [ ] 2.1 Implement `read_nautobot_ver(project_root)` - load `invoke.yml`, traverse nested keys, return `nautobot_ver` string
- [ ] 2.2 Handle missing file and missing key with clear exit messages per spec `Resolve Nautobot version from invoke.yml`

## 3. Nautobot pyproject.toml Fetcher

- [ ] 3.1 Implement `fetch_nautobot_pyproject(nautobot_ver)` - fetch raw GitHub URL and return parsed TOML
- [ ] 3.2 Handle HTTP errors and network failures per spec `Fetch Nautobot pyproject.toml from GitHub`
- [ ] 3.3 Build normalised name-to-constraint dict from both `[project.dependencies]` and `[tool.poetry.dependencies]` sections

## 4. Dependency Comparator

- [ ] 4.1 Implement name normalisation (lowercase, replace underscores with hyphens)
- [ ] 4.2 Implement `extract_lower_bound(constraint_str)` using `packaging.version.Version` to handle `^`, `>=`, `~=` notations
- [ ] 4.3 Implement `collect_updates(local_deps, nautobot_deps)` - skip git-sourced, compare lower bounds, return list of `(name, old_constraint, new_constraint)` per specs `Skip git-sourced`, `Compare and collect version updates`

## 5. Python Version Comparator

- [ ] 5.1 Extract `requires-python` from the fetched Nautobot pyproject
- [ ] 5.2 Compare with local `python` constraint under `[tool.poetry.dependencies]`
- [ ] 5.3 Add to update queue when they differ per spec `Sync Python version constraint`

## 6. pyproject.toml Writer

- [ ] 6.1 Use `tomlkit` to load the local `pyproject.toml` preserving formatting and comments
- [ ] 6.2 Apply all queued dependency updates in-place
- [ ] 6.3 Apply Python version update if queued
- [ ] 6.4 Write the modified content back to `pyproject.toml`

## 7. No-Update Exit Path

- [ ] 7.1 Detect empty update queue (no dep changes, no python change) and print the "No updates available" message per spec `Report no updates available`
- [ ] 7.2 Exit with code 0 without touching any file

## 8. poetry update Execution

- [ ] 8.1 Invoke `poetry update` as a subprocess after writing `pyproject.toml`
- [ ] 8.2 Stream or capture output and display to the user
- [ ] 8.3 Handle non-zero exit code per spec `Apply updates and run poetry update` - exit without running build step
- [ ] 8.4 Print a summary table of changed packages (name, old constraint, new constraint) on success
- [ ] 8.5 Invoke `poetry run invoke build --force-rm --no-cache` after `poetry update` succeeds
- [ ] 8.6 On non-zero exit, capture full build error output and pass to the error recovery path (task group 10)

## 9. Agent Wiring

- [ ] 9.1 Wire the agent entrypoint so it can be invoked via `update_python_modules_from_nautobot` from the VS Code agent panel
- [ ] 9.2 Accept optional package name arguments to limit scope (future: `--dry-run` flag noted as open question in design)
- [ ] 9.3 Document usage in `AGENT.md` or `README.md` for reuse in other projects

## 10. Build Error Recovery

- [ ] 10.1 Implement `classify_build_error(error_output)` - return one of: `version_conflict`, `missing_package`, `unknown`
- [ ] 10.2 For `version_conflict`: parse conflicting package name(s) from error output and revert only those entries in `pyproject.toml` to their original constraints
- [ ] 10.3 For `missing_package`: parse the package name from the error output and restore its original constraint in `pyproject.toml`
- [ ] 10.4 After revert, run `poetry update` scoped to the affected package(s) only
- [ ] 10.5 Re-run `poetry run invoke build --force-rm --no-cache` (second and final attempt)
- [ ] 10.6 On success: include fix details in the final summary output
- [ ] 10.7 For `unknown` error type OR second build failure: report full error, leave `pyproject.toml` intact, exit with non-zero code - no further retries

## 9. Agent Wiring

- [ ] 9.1 Wire the agent entrypoint so it can be invoked via `update_python_modules_from_nautobot` from the VS Code agent panel
- [ ] 9.2 Accept optional package name arguments to limit scope (future: `--dry-run` flag noted as open question in design)
- [ ] 9.3 Document usage in `AGENT.md` or `README.md` for reuse in other projects
