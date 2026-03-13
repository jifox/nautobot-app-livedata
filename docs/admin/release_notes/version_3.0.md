# v3.0 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

## Breaking Changes

- Renamed API endpoint from `managed-device` to `primary-device` for clarity:
    - Old: `/api/plugins/livedata/managed-device/<uuid>/<object_type>/`
    - New: `/api/plugins/livedata/primary-device/<uuid>/<object_type>/`
- Dropped support for Nautobot 2.x; the app now requires Nautobot 3.0 or newer to match the Bootstrap 5 UI and Celery queue model used in this release.

## Added

- Documented three additional background jobs in README: `LivedataQueryJob`, `LivedataCleanupJobResultsJob`, `EnforceDefaultJobQueueJob`.

## Changed

- Updated Jobs module to export `jobs` iterable per Nautobot 3.x convention (previously `registered_job_classes`). (commit ff472c6)
- Clarified README overview: Nautobot App LiveData is now a "lightweight plugin" compatible with Nautobot 3.0+ that fetches live device/interface data via Netmiko. (commit ff472c6)

## Compatibility

- This release adds compatibility with Nautobot `v3.0`. Note that some third-party
    plugins may also need updates to be compatible with Nautobot 3.x; please consult
    the individual plugin release notes for migration guidance.
- Poetry version 2.0+ is required to manage the updated dependencies and lockfile format used in this release.

## Migration Notes

- API endpoint rename: the endpoint previously exposed as `managed-device` has been
    renamed to `primary-device`. Update any external integrations, scripts, or monitoring
    tools that call the old URL.
    - Old: `/api/plugins/livedata/managed-device/<uuid>/<object_type>/`
    - New: `/api/plugins/livedata/primary-device/<uuid>/<object_type>/`

- Update any references in your codebase (client libraries, automation playbooks,
    recorded API tests, or webhooks) to use the new endpoint path and route name.

- If you maintain local tests that assert the old URL or URL name, update them to
    reference the new endpoint. Run the test-suite to confirm everything passes.

- If you rely on third-party plugins that call `managed-device`, contact the plugin
    maintainers or check their release notes for compatibility updates.

## Deprecation

- The old `managed-device` API endpoint is officially deprecated and will be removed
    in a future release (target: next major release). Consumers are strongly advised
    to migrate to the `primary-device` endpoint. Recommended steps:
    - Update integrations, automation, recorded tests, and monitoring to call
        `/api/plugins/livedata/primary-device/<uuid>/<object_type>/`.
    - Update any code using reverse URL lookups or route names to the new name.
    - Run your test-suite against the updated endpoint and address failures.

- For short-term compatibility during migration, you may implement a shim that
    forwards requests from the old path to the new one, but plan to remove such
    shims once consumers are updated.

## [v3.0.1 (2026-03-13)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v3.0.1)

### Fixed

- [#188](https://github.com/jifox/nautobot-app-livedata/issues/188) - install Nautobot exactly at the version defined in invoke.yml, not the latest version.

## [v3.0.0 (2026-03-11)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v3.0.0)

### Breaking Changes (tag)

- [#64](https://github.com/jifox/nautobot-app-livedata/issues/64) - Rename the api 'managed-device' to 'primary-device'
- [#171](https://github.com/jifox/nautobot-app-livedata/issues/171) - Dropped support for Nautobot 2.x; the app now requires Nautobot 3.0 or newer to match the Bootstrap 5 UI and Celery queue model used in this release.

### Added (tag)

- [#171](https://github.com/jifox/nautobot-app-livedata/issues/171) - Introduced the EnforceDefaultJobQueueJob to realign every Nautobot job with the default Celery queue, including dry-run reporting and automatic creation or normalization of the default queue where needed.

### Fixed (tag) (tag)

- [#171](https://github.com/jifox/nautobot-app-livedata/issues/171) - Resolved breadcrumb and active tab configuration in Live Data views.
- [#171](https://github.com/jifox/nautobot-app-livedata/issues/171) - Provided a default `query_job_task_queue` plugin setting so the Livedata query APIs no longer raise HTTP 500 errors when the Celery queue name is omitted from user configuration.

### Dependencies (tag)

- [#78](https://github.com/jifox/nautobot-app-livedata/issues/78) - Bump yamllint from 1.35.1 to 1.37.1
- [#154](https://github.com/jifox/nautobot-app-livedata/issues/154) - Bump coverage from 6.4 to 7.10.7
- [#167](https://github.com/jifox/nautobot-app-livedata/issues/167) - Bump towncrier from 24.8.0 to 25.8.0
- [#168](https://github.com/jifox/nautobot-app-livedata/issues/168) - Bump Python-dotenv from 1.1.1 to 1.2.1
- [#169](https://github.com/jifox/nautobot-app-livedata/issues/169) - Bump mkdocstrings-Python from 1.16.12 to 1.18.2
- [#170](https://github.com/jifox/nautobot-app-livedata/issues/170) - Bump Django from 4.2.25 to 4.2.26
- [#171](https://github.com/jifox/nautobot-app-livedata/issues/171) - Raised the runtime stack to Nautobot 3.x by bumping the Nautobot runtime constraint to `~3.0.0`, aligning Nautobot-plugin-Nornir to its 3.x release, and increasing the supported Python range to 3.10–3.13.
- [#172](https://github.com/jifox/nautobot-app-livedata/issues/172) - Bump actions/checkout from 5 to 6
- [#178](https://github.com/jifox/nautobot-app-livedata/issues/178) - Bump pynacl from 1.6.1 to 1.6.2
- [#179](https://github.com/jifox/nautobot-app-livedata/issues/179) - Bump urllib3 from 2.5.0 to 2.6.3
- [#181](https://github.com/jifox/nautobot-app-livedata/issues/181) - Bump pyasn1 from 0.6.1 to 0.6.2
- [#183](https://github.com/jifox/nautobot-app-livedata/issues/183) - Bump cryptography from 46.0.3 to 46.0.5
- [#184](https://github.com/jifox/nautobot-app-livedata/issues/184) - Bump sqlparse from 0.5.3 to 0.5.4
- [#185](https://github.com/jifox/nautobot-app-livedata/issues/185) - Bump Django from 4.2.26 to 4.2.29

## Documentation

- Refreshed README with complete feature list and Nautobot 3.0+ compatibility notice; improved formatting and clarity.

### Housekeeping (tag) (tag)

- [#171](https://github.com/jifox/nautobot-app-livedata/issues/171) - Refreshed the developer tooling: the Invoke task collection now auto-detects compose directories, parses the Nautobot version from pyproject.toml, adds djlint/djhtml/markdownlint helpers plus coverage exporters, and a new restore-database.sh script streamlines loading production backups into local environments.
- [#171](https://github.com/jifox/nautobot-app-livedata/issues/171) - Added a dedicated Nautobot test settings module and regression test that asserts the plugin configuration exposes all expected defaults, keeping future queue/alignment behavior covered by CI.
