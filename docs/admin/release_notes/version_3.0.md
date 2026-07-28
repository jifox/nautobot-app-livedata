# v3.0 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

## [v3.0.3 (2026-07-28)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v3.0.3)

### Fixed

- [#195](https://github.com/jifox/nautobot-app-livedata/issues/195) - Fix enqueue_job() regression on Nautobot < 3.2 by using version-aware dispatch: `**job_kwargs` on Nautobot < 3.2, `job_kwargs=job_kwargs` on Nautobot >= 3.2.

### Dependencies

- [#180](https://github.com/jifox/nautobot-app-livedata/issues/180) - Bump networktocode/gh-action-setup-poetry-environment from v6 to v7.

## [v3.0.2 (2026-07-28)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v3.0.2)

### Changed

- [#192](https://github.com/jifox/nautobot-app-livedata/issues/192) - Standardize test classes on Nautobot base test classes by migrating processor, content type, and output filter tests away from Django and unittest base classes.
- [#192](https://github.com/jifox/nautobot-app-livedata/issues/192) - Improve job timestamp handling by using timezone-aware values from Django timezone utilities.
- [#192](https://github.com/jifox/nautobot-app-livedata/issues/192) - Replace startup print statements with structured logging in signal handlers to improve operational diagnostics.
- [#194](https://github.com/jifox/nautobot-app-livedata/issues/194) - Update `JobResult.enqueue_job()` call to pass `job_kwargs` as a single named parameter instead of the deprecated `**kwargs` splat pattern, ensuring compatibility with Nautobot 3.2 job execution API.
- [#194](https://github.com/jifox/nautobot-app-livedata/issues/194) - Bump Markdown dev dependency from ~=3.8.2 to ~=3.10.2 (Nautobot 3.2 requires >=3.10.2)
- [#194](https://github.com/jifox/nautobot-app-livedata/issues/194) - Update assertion for Nautobot 3.2 ContentType string representation (dcim | device → DCIM | device)

### Fixed

- [#90](https://github.com/jifox/nautobot-app-livedata/issues/90) - Improve Liveupdate error feedback when a device has no Secrets Group by raising a clear, actionable message so users can quickly resolve the missing configuration.
- [#90](https://github.com/jifox/nautobot-app-livedata/issues/90) - For GitHub Actions workflows, added the recommended environment variables at the top of the workflow so they apply to all jobs:
- [#90](https://github.com/jifox/nautobot-app-livedata/issues/90) - - FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true — opt in to Node.js 24 now
- [#90](https://github.com/jifox/nautobot-app-livedata/issues/90) - - ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true — allows falling back to Node.js 20 if needed once Node.js 24 becomes the default (per GitHub’s guidance)
- [#192](https://github.com/jifox/nautobot-app-livedata/issues/192) - Prevent false negatives when resolving a primary device from virtual chassis members by checking all members for a primary IP before failing, and harden active-status detection across status representations.
- [#192](https://github.com/jifox/nautobot-app-livedata/issues/192) -
- [#192](https://github.com/jifox/nautobot-app-livedata/issues/192) - Replace import-time dependency failures in API views with runtime dependency checks, returning a
- [#192](https://github.com/jifox/nautobot-app-livedata/issues/192) - service-unavailable response when required modules are missing.

### Housekeeping

- [#192](https://github.com/jifox/nautobot-app-livedata/issues/192) - Align runtime dependency checks and startup messaging with more resilient production defaults while preserving existing API and job behavior.
- [#192](https://github.com/jifox/nautobot-app-livedata/issues/192) - Standardize `invoke` task commands to match the conventions used in the main Nautobot repository.
