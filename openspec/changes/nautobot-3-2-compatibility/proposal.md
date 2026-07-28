## Why

Nautobot 3.2.0 was released on 2026-07-27 with several breaking changes and deprecations.
This app must be verified compatible and any deprecated API usage updated to prevent
runtime warnings and ensure forward compatibility with future Nautobot 3.x releases.

## What Changes

- Update `JobResult.enqueue_job()` call to pass `job_kwargs` as a single named parameter
  instead of the deprecated `**splat` pattern (required by Nautobot 3.2's job execution API change)
- Verify the compatibility matrix (`min_version`/`max_version`) already covers 3.2
- Verify `pyproject.toml` Nautobot dependency bounds already cover 3.2
- Add changelog fragment documenting 3.2 compatibility
- Verify existing tests pass under Nautobot 3.2

## Capabilities

### New Capabilities

- `nautobot-3-2-job-api`: Conform to Nautobot 3.2 job execution API by passing `job_kwargs`
  as a named parameter to `JobResult.enqueue_job()` instead of using `**kwargs` splat

### Modified Capabilities

<!-- No existing specs to modify -->

## Impact

- **Code**: `nautobot_app_livedata/api/views.py` — `_enqueue_job()` method (1 line change)
- **Configuration**: `nautobot_app_livedata/__init__.py` — compatibility matrix verified (no change needed)
- **Dependencies**: `pyproject.toml` — Nautobot bounds verified (no change needed)
- **Documentation**: Changelog fragment for 3.2 compatibility
- **Testing**: Run existing test suite to confirm no regressions
