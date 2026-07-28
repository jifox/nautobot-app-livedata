## Context

Nautobot-adjacent Python projects (apps, scripts, automation tools) share a subset of dependencies with Nautobot core (e.g., `celery`, `redis`, `pydantic`). As Nautobot releases updates, its pinned minimum versions advance. Local projects that don't track these changes risk import errors, API incompatibilities, or subtle behaviour differences at runtime.

The Nautobot version currently in use by a project is already declared in `invoke.yml` under `nautobot_ver`. GitHub hosts every Nautobot release with a matching git tag (`v{nautobot_ver}`), and the raw `pyproject.toml` is accessible without authentication.

## Goals / Non-Goals

**Goals:**

- Automate detection and update of shared PyPI dependencies whose Nautobot minimum version exceeds the local constraint.
- Always sync the Python version constraint to match Nautobot's `requires-python`.
- Skip git-sourced dependencies (no PyPI version to compare).
- Exit cleanly with a user-facing message when nothing needs updating.
- Run `poetry update` after applying changes to regenerate the lock file.
- Be reusable across any Poetry-based project with an `invoke.yml` containing `nautobot_ver`.

**Non-Goals:**

- Syncing dev, docs, or linting dependency groups (only `[tool.poetry.dependencies]` / `[project.dependencies]`).
- Downgrading local versions that are already ahead of Nautobot's.
- Resolving package renames or equivalencies (e.g., `psycopg` vs `psycopg2-binary` are treated as distinct packages).
- Handling Nautobot optional extras.

## Decisions

### D1 - Version constraint format: adopt Nautobot's exact range

**Decision:** When updating a module, replace the local constraint verbatim with Nautobot's constraint string (e.g., `>=5.6.3,<5.7`).

**Rationale:** Nautobot has integration-tested these exact bounds. Keeping a looser local caret (`^5.6.3`) would permit versions Nautobot has not validated. Conservative is safer here.

**Alternative considered:** Bump local caret minimum only (`^5.6.3`). Rejected - allows upper versions outside Nautobot's tested range.

---

### D2 - Python version sync direction: always match Nautobot

**Decision:** Always replace the local `python` constraint with Nautobot's `requires-python`, regardless of whether it is looser or tighter.

**Rationale:** The project is deployed alongside a specific Nautobot version. The Python constraint should reflect exactly what that Nautobot version supports, not a local guess.

**Alternative considered:** Only tighten (never loosen). Rejected - would leave the local constraint permanently ahead of Nautobot if it was once set stricter.

---

### D3 - Version source: GitHub raw file, not PyPI

**Decision:** Fetch `https://raw.githubusercontent.com/nautobot/nautobot/v{ver}/pyproject.toml` directly.

**Rationale:** The full `pyproject.toml` contains both PEP 508-style `[project.dependencies]` and Poetry-style `[tool.poetry.dependencies]`. PyPI metadata (e.g., via `pip index`) only exposes the resolved requires, not the declared constraint range.

---

### D4 - Comparison key: normalised package name

**Decision:** Normalise package names to lowercase with hyphens (`celery`, `django-celery-beat`) when comparing local vs Nautobot deps.

**Rationale:** PyPI normalises names (`Celery` == `celery`). Without normalisation, a case mismatch would silently skip a legitimate match.

---

### D5 - Version comparison: minimum version extracted from constraint string

**Decision:** Extract the lower bound from both constraints (e.g., `^5.4.0` → `5.4.0`, `>=5.6.3,<5.7` → `5.6.3`) using `packaging.version.Version` and compare. Update only when Nautobot's lower bound is strictly higher.

**Rationale:** The full constraint strings use different notation styles. Comparing raw strings is unreliable; comparing parsed lower bounds is deterministic.

## Risks / Trade-offs

| Risk                                                                                           | Mitigation                                                                                                                                          |
| ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| GitHub fetch fails (network, tag not found)                                                    | Agent reports the error and exits without modifying any file.                                                                                       |
| Nautobot uses a package name the local project spells differently (e.g., `PyYAML` vs `pyyaml`) | Normalisation (D4) handles case. Genuine renames are out of scope (Non-Goals).                                                                      |
| `poetry update` fails after edits                                                              | Agent reports the error; `pyproject.toml` edits remain so the user can inspect.                                                                     |
| Future Nautobot versions switch from Poetry to pure PEP 517 (already partially done)           | Parser must handle both `[project.dependencies]` (PEP 508) and `[tool.poetry.dependencies]` (Poetry). Nautobot 3.x already publishes both sections. |

## Open Questions

- Should the agent support a `--dry-run` flag to preview changes without writing? (Nice-to-have for v2.)
- Should dev-group deps (`[tool.poetry.group.dev.dependencies]`) ever be synced? Current answer: no.
