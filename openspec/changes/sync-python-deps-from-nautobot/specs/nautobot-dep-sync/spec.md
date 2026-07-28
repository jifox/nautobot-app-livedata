## ADDED Requirements

### Requirement: Resolve Nautobot version from invoke.yml

The agent SHALL read the `nautobot_ver` key from the `invoke.yml` file located in the project root directory.

#### Scenario: nautobot_ver present

- **WHEN** `invoke.yml` exists and contains a `nautobot_ver` key (at any nesting level)
- **THEN** the agent uses that value as the Nautobot version string for all subsequent steps

#### Scenario: invoke.yml missing

- **WHEN** no `invoke.yml` file is found in the project root
- **THEN** the agent exits with an error message: "invoke.yml not found"

#### Scenario: nautobot_ver key absent

- **WHEN** `invoke.yml` exists but contains no `nautobot_ver` key
- **THEN** the agent exits with an error message: "nautobot_ver not found in invoke.yml"

---

### Requirement: Fetch Nautobot pyproject.toml from GitHub

The agent SHALL fetch `https://raw.githubusercontent.com/nautobot/nautobot/v{nautobot_ver}/pyproject.toml` and parse its dependencies.

#### Scenario: Successful fetch

- **WHEN** the URL is reachable and the tag exists
- **THEN** the agent parses both `[project.dependencies]` and `[tool.poetry.dependencies]` sections and builds a normalised name-to-constraint map

#### Scenario: Fetch failure (network error or tag not found)

- **WHEN** the HTTP request fails or returns a non-200 status
- **THEN** the agent exits with an error message that includes the URL and HTTP status, without modifying any local file

---

### Requirement: Skip git-sourced local dependencies

The agent SHALL ignore any local dependency declared with a `git` key when building the comparison set.

#### Scenario: Git-sourced dependency encountered

- **WHEN** a local dependency entry contains a `git` key (e.g., `secresolve = {git = "..."}`)
- **THEN** that dependency is excluded from comparison and no update is applied to it

---

### Requirement: Compare and collect version updates

The agent SHALL compare each local PyPI dependency against Nautobot's constraint for the same normalised package name, and collect updates where Nautobot's lower bound is strictly higher.

#### Scenario: Nautobot minimum is higher

- **WHEN** a local dependency exists in both pyproject.toml files with the same normalised name, is not git-sourced, AND Nautobot's lower bound is strictly greater than the local lower bound
- **THEN** the dependency is added to the update queue with Nautobot's exact constraint string as the new value

#### Scenario: Local version already meets or exceeds Nautobot

- **WHEN** the local lower bound is equal to or greater than Nautobot's lower bound
- **THEN** no update is queued for that dependency

#### Scenario: Dependency not present in Nautobot

- **WHEN** a local dependency has no matching normalised name in Nautobot's pyproject.toml
- **THEN** no update is queued for that dependency

---

### Requirement: Sync Python version constraint

The agent SHALL replace the local `python` constraint in `[tool.poetry.dependencies]` with Nautobot's `requires-python` value whenever they differ.

#### Scenario: Python constraints differ

- **WHEN** the local `python` constraint string does not exactly match Nautobot's `requires-python`
- **THEN** the local constraint is replaced with Nautobot's value and this change is included in the update summary

#### Scenario: Python constraints already match

- **WHEN** the local `python` constraint exactly matches Nautobot's `requires-python`
- **THEN** no change is made to the python constraint

---

### Requirement: Report no updates available

The agent SHALL inform the user and exit without modifying any file when neither dependency updates nor a Python version change are required.

#### Scenario: Nothing to update

- **WHEN** the update queue is empty AND the Python constraint already matches
- **THEN** the agent prints "No updates available - all shared dependencies already meet or exceed Nautobot v{nautobot_ver} requirements" and exits with code 0

---

### Requirement: Apply updates and run poetry update

The agent SHALL write all queued changes to `pyproject.toml` and then execute `poetry update` when at least one update was collected.

#### Scenario: Updates applied successfully

- **WHEN** one or more dependency constraints or the Python version are updated in `pyproject.toml`
- **THEN** the agent runs `poetry update`, then runs `poetry run invoke build --force-rm --no-cache`, prints a summary of all changed packages and their old/new constraints, and exits with code 0

#### Scenario: poetry update fails

- **WHEN** `poetry update` exits with a non-zero code
- **THEN** the agent reports the error output, leaves `pyproject.toml` with the applied edits intact for manual inspection, exits with a non-zero code, and does NOT proceed to the build step

#### Scenario: invoke build fails

- **WHEN** `poetry update` succeeds but `poetry run invoke build --force-rm --no-cache` exits with a non-zero code
- **THEN** the agent captures the error output and passes it to the build error recovery step (see `Attempt to fix build errors and retry`)

---

### Requirement: Attempt to fix build errors and retry

The agent SHALL analyse captured build error output, apply targeted fixes to `pyproject.toml`, and re-run `poetry run invoke build --force-rm --no-cache` at most once.

#### Scenario: Build error is a version conflict

- **WHEN** the build error output contains a dependency conflict or version resolution error
- **THEN** the agent identifies the conflicting package(s) from the error output, reverts only those packages to their previous constraint in `pyproject.toml`, runs `poetry update` again for the affected packages, and proceeds to the rebuild step

#### Scenario: Build error is a missing or unresolvable package

- **WHEN** the build error output contains a "package not found" or "no matching distribution" message
- **THEN** the agent identifies the package name, removes the queued constraint update for that package (restoring the original value), and proceeds to the rebuild step

#### Scenario: Rebuild succeeds after fix

- **WHEN** the fix is applied and `poetry run invoke build --force-rm --no-cache` exits with code 0 on the second attempt
- **THEN** the agent prints a summary of the fix applied alongside the changed packages and exits with code 0

#### Scenario: Rebuild fails after fix attempt

- **WHEN** `poetry run invoke build --force-rm --no-cache` exits with a non-zero code on the second attempt, OR the error type is unrecognised
- **THEN** the agent reports the full error output, leaves `pyproject.toml` in its current state for manual inspection, and exits with a non-zero code without further retries
