## Context

Nautobot 3.2.0 introduced a behavioral change to job execution APIs. The `job_kwargs`
parameter must now be passed as a single named keyword argument to `enqueue_job()`,
`execute_job()`, `run_job_for_testing()`, and `create_schedule()`. The previous pattern
of splatting `**kwargs` (which Nautobot previously collected and repackaged) is
deprecated and emits warnings in 3.2, with removal planned for a future release.

The `nautobot_app_livedata` app uses `JobResult.enqueue_job()` in `api/views.py` to
enqueue `LivedataQueryJob` when users request live data from the Device or Interface tabs.

The app has no other Nautobot 3.2 breaking change impacts (no cable model usage, no
`?depth=N` queries, no GraphQL, no `settings_or_config` filter, no git repository sync).

## Goals / Non-Goals

**Goals:**
- Update the single deprecated `enqueue_job()` call site to use the new `job_kwargs` named parameter
- Verify the compatibility matrix and dependency bounds already cover 3.2
- Add a changelog fragment documenting 3.2 compatibility
- Verify existing tests pass without modification

**Non-Goals:**
- Adding new features or changing app behavior
- Upgrading other dependencies (nautobot-plugin-nornir, jsonschema, etc.)
- Refactoring other parts of the codebase
- Changing the job's `before_start`/`run` signature (the job itself is unaffected)

## Decisions

### Decision 1: Change `**job_kwargs` to `job_kwargs=job_kwargs`

**Alternatives considered:**

| Option | Pros | Cons |
|---|---|---|
| `job_kwargs=job_kwargs` (chosen) | Clean, explicit, matches Nautobot 3.2 API contract | None |
| Keep `**job_kwargs` with `DeprecationWarning` suppression | No code change | Warning suppression is fragile, breaks in future Nautobot |
| Conditionally branch on Nautobot version | Handles both old and new | Unnecessary complexity for a simple change |

**Rationale:** The app's dependency bounds (`nautobot >= 3.0.0, <4.0.0`) mean it will
always run on a Nautobot version that supports the new signature. The old pattern
was already deprecated before 3.2 (warnings existed), and 3.2 makes it required.
Switching unconditionally is the simplest, cleanest approach.

## Risks / Trade-offs

- **Risk**: If someone runs this app version against an older Nautobot (pre-`job_kwargs` parameter)
  → **Mitigation**: The `pyproject.toml` already requires `nautobot >= 3.0.0`. The `job_kwargs`
  parameter was added before 3.2 and is available in all 3.x releases the app targets.
  No compatibility issue.

- **Risk**: The `job_kwargs` dict keys might need to match Job variable names exactly
  → **Mitigation**: No change in behavior. The same dict is passed, just through a named
  parameter instead of `**splat`. The existing test suite validates this.
