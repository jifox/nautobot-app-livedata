## 1. Code Fix

- [x] 1.1 Update `_enqueue_job()` in `nautobot_app_livedata/api/views.py` to pass `job_kwargs` as a named parameter instead of `**job_kwargs` splat

## 2. Compatibility Verification

- [x] 2.1 Verify `min_version` and `max_version` in `nautobot_app_livedata/__init__.py` cover Nautobot 3.2 (already `min_version="3.0.0"`, `max_version="3.9999"`)
- [x] 2.2 Verify Nautobot dependency bounds in `pyproject.toml` cover 3.2 (already `nautobot = ">=3.0.0,<4.0.0"`)

## 3. Changelog

- [x] 3.1 Add towncrier changelog fragment for Nautobot 3.2 compatibility (e.g., `changes/3_2_compat.changed.md`)

## 4. Validation

- [x] 4.1 Run `poetry run invoke build --force-rm --no-cache` to build the Docker image and verify it builds successfully. Successfully finish building the image because the further tasks depend on a working image. If the build fails, investigate and fix the issue.
- [x] 4.2 Run `poetry run invoke stop post-upgrade start` to verify the app starts successfully in a Nautobot 3.2 environment
- [x] 4.3 Run `poetry run invoke ruff` to verify code style. Also fix unrelated style issues in the codebase if they are found. If the style check fails, investigate and fix the issue.
- [x] 4.4 Run `poetry run invoke pylint` to verify static analysis. Also fix unrelated style issues in the codebase if they are found. If the style check fails, investigate and fix the issue.
- [x] 4.5 Run `poetry run invoke tests` to verify all tests pass
- [x] 4.6 Run `poetry run invoke markdownlint` to verify markdown files
- [x] 4.7 Run `poetry run invoke yamllint` to verify YAML files
- [x] 4.8 Run `poetry run invoke tests --keepdb` to verify all tests pass in a Nautobot 3.2 environment. If the test fails, run without --keepdb to verify the failure is not due to a stale database. If the test still fails, investigate and fix the issue.
