
# v2.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

## [v2.4.0 (2025-03-20)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.0)

## [v2.4.0b2 (2025-02-19)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.0b2)

### Security

- [#57](https://github.com/jifox/nautobot-app-livedata/issues/57) - Fixed Information exposure through an exception (Weakness CWE-209, CWE-497).
- [#57](https://github.com/jifox/nautobot-app-livedata/issues/57) - Fixed Github Action Workflow does not contain permissions (Weakness CWE-275).

- [#1](https://github.com/jifox/nautobot-app-livedata/issues/1) - Vulnerable OpenSSL included in cryptography wheels fixed weaknesses CWE-392, CWE-1395

### Added

- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - Added a "Live Data" Tab to the Device Details page.

- [#9](https://github.com/jifox/nautobot-app-livedata/issues/9) - Add Dependabot configuration
- [#26](https://github.com/jifox/nautobot-app-livedata/issues/26) - Automated the Towncrier change fragement creation for Dependabot PRs

### Changed

- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - The following environment variable names are changed
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - 
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - LIVEDATA_QUERY_JOB_NAME was previously LIVEDATA_INTERFACE_QUERY_JOB_NAME
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - LIVEDATA_QUERY_JOB_DESCRIPTION was previously LIVEDATA_QUERY_INTERFACE_JOB_DESCRIPTION
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - LIVEDATA_QUERY_JOB_SOFT_TIME_LIMIT was previously LIVEDATA_QUERY_INTERFACE_JOB_SOFT_TIME_LIMIT
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - LIVEDATA_QUERY_JOB_TASK_QUEUE was previously LIVEDATA_QUERY_INTERFACE_JOB_TASK_QUEUE
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - LIVEDATA_QUERY_JOB_HIDDEN was previously LIVEDATA_QUERY_INTERFACE_JOB_HIDDEN
- [#57](https://github.com/jifox/nautobot-app-livedata/issues/57) - Changed - Updating urllib3 (1.26.20 -> 2.3.0)
- [#57](https://github.com/jifox/nautobot-app-livedata/issues/57) - Changed - Updating httpcore (0.17.3 -> 1.0.7)
- [#57](https://github.com/jifox/nautobot-app-livedata/issues/57) - Changed - Updating httpx (0.24.1 -> 0.27.0)
- [#57](https://github.com/jifox/nautobot-app-livedata/issues/57) - Changed - Updating pynautobot (2.0.1 -> 2.6.1)
- [#57](https://github.com/jifox/nautobot-app-livedata/issues/57) - Changed - Updating nornir-nautobot (3.1.0 -> 3.3.1)
- [#57](https://github.com/jifox/nautobot-app-livedata/issues/57) - Changed - Updating nautobot-plugin-nornir (2.2.0 -> 2.2.1)

- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - - Update Documentation
- [#32](https://github.com/jifox/nautobot-app-livedata/issues/32) - Revise App description to be more dynamic

### Removed

- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - The following environment variable names are removed
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - 
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - `LIVEDATA_INTERFACE_QUERY_JOB_NAME` use `LIVEDATA_QUERY_JOB_NAME` instead
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - `LIVEDATA_QUERY_INTERFACE_JOB_DESCRIPTION` use `LIVEDATA_QUERY_JOB_DESCRIPTION` instead
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - `LIVEDATA_QUERY_INTERFACE_JOB_SOFT_TIME_LIMIT` use `LIVEDATA_QUERY_JOB_SOFT_TIME_LIMIT` instead
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - `LIVEDATA_QUERY_INTERFACE_JOB_TASK_QUEUE` use `LIVEDATA_QUERY_JOB_TASK_QUEUE`
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - `LIVEDATA_QUERY_INTERFACE_JOB_HIDDEN` use `LIVEDATA_QUERY_JOB_HIDDEN`

### Fixed

- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - Fixed build status badges in README.md and yaml syntax in `.github/dependabot.yml`
- [#21](https://github.com/jifox/nautobot-app-livedata/issues/21) - Remove trailing spaces from each line of livedata show commands
- [#29](https://github.com/jifox/nautobot-app-livedata/issues/29) - Corrected view permissions for the "Live Data" tab to ensure superusers have access
- [#37](https://github.com/jifox/nautobot-app-livedata/issues/37) - Updated site_url to point to the documentation URL.

### Dependencies

- [#14](https://github.com/jifox/nautobot-app-livedata/issues/14) - Update pymarkdownlnt from 0.9.26 to 0.9.28
- [#15](https://github.com/jifox/nautobot-app-livedata/issues/15) - Update coverage from 6.4 to 7.6.12
- [#16](https://github.com/jifox/nautobot-app-livedata/issues/16) - Update ruff from 0.8.6 to 0.9.6
- [#17](https://github.com/jifox/nautobot-app-livedata/issues/17) - Update mkdocs-include-markdown-plugin from 7.1.2 to 7.1.4.
- [#22](https://github.com/jifox/nautobot-app-livedata/issues/22) - Update mkdocs-material from 9.5.50 to 9.6.4
- [#23](https://github.com/jifox/nautobot-app-livedata/issues/23) - Update mkdocstrings from 0.27.0 to 0.28.1
- [#25](https://github.com/jifox/nautobot-app-livedata/issues/25) - Update griffe from 1.1.1 to 1.5.7
- [#32](https://github.com/jifox/nautobot-app-livedata/issues/32) - Update nautobot-plugin-nornir from 2.2.0 to 2.2.1

## [v2.4.0b1 (2025-02-15)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.0b1)

### Added

- [#1](https://github.com/jifox/nautobot-app-livedata/issues/1) - Added tests for the current implementation of the functions

### Fixed

- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - Github CI workflow for dependabot
- [#1](https://github.com/jifox/nautobot-app-livedata/issues/1) - Fixed nautobot_database_ready_callback to wait for the database initialization of dependent apps before running the callback. This ensures that the callback is only run once the database is fully initialized and ready for use.
- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) Fixed Read The Docs build error and also fixed the test case for the version check
