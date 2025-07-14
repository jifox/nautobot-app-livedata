
# v2.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

### Filter Syntax for Platform Commands

You can append a filter command to the end of a device command using the `!!` delimiter. The string following `!!` specifies the filter operation to be applied to the command output. 

Multiple filters can be chained in a single line by separating each filter with `!!`, for example: `show logging !!EXACT:{{intf_number}}!!LAST:10!!`. Each `!!` acts as a command terminator, and filters are applied in the order they appear.

!!! note
    Added multiple filters in v2.4.2, this feature allows for more flexible and powerful command filtering directly in the Live Data tab.

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

## [v2.4.5 (2025-07-14)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.5)

### Fixed

- [#121](https://github.com/jifox/nautobot-app-livedata/issues/121) - Traceback on opening Live Data tab for a interface at chassis-2

## [v2.4.4 (2025-06-26)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.4)

### Added

- [#113](https://github.com/jifox/nautobot-app-livedata/issues/113) - Added the Filter 'FIRST: <n>' to output only the top <n> lines

### Changed

- [#113](https://github.com/jifox/nautobot-app-livedata/issues/113) - changed ci.yml to include the python version 3.10

## [v2.4.3 (2025-06-25)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.3)

### Fixed

- [#109](https://github.com/jifox/nautobot-app-livedata/issues/109) - Fixed filter EXACT: is not matching Interface Numbers in Log Lines

### Dependencies

- [#74](https://github.com/jifox/nautobot-app-livedata/issues/74) - Bump django-debug-toolbar from 5.0.1 to 5.2.0
- [#94](https://github.com/jifox/nautobot-app-livedata/issues/94) - Bump griffe from 1.5.7 to 1.7.3
- [#108](https://github.com/jifox/nautobot-app-livedata/issues/108) - Bump ruff from 0.11.13 to 0.12.0

## [v2.4.2 (2025-06-22)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.2)

### Added

- [#91](https://github.com/jifox/nautobot-app-livedata/issues/91) - Multiple filters can be chained in a single line using `!!` as a separator, with filters applied in order.

### Dependencies

- [#88](https://github.com/jifox/nautobot-app-livedata/issues/88) - Bump docker/build-push-action from 5.4.0 to 6.18.0
- [#100](https://github.com/jifox/nautobot-app-livedata/issues/100) - Bump mkdocs-include-markdown-plugin from 7.1.5 to 7.1.6

## [v2.4.1 (2025-06-19)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.1)

### Added

- [#91](https://github.com/jifox/nautobot-app-livedata/issues/91) - # This file describes the change for issue #91: Support for Filter Commands in Live Device Output Using !! Syntax
- [#91](https://github.com/jifox/nautobot-app-livedata/issues/91) - feature: Support for post-processing filter commands in live device output using the `!!` syntax (e.g., `!!EXACT:foo!!`, `!!LAST:100!!`).

### Dependencies

- [#95](https://github.com/jifox/nautobot-app-livedata/issues/95) - Bump mkdocstrings-python from 1.13.0 to 1.16.7

## [v2.4.1a0 (2025-06-08)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.1a0)

No significant changes.

### Security

- [#4](https://github.com/jifox/nautobot-app-livedata/issues/4) - Bump h11 from 0.14.0 to 0.16.0 (h11 accepts some malformed Chunked-Encoding bodies)
- [#6](https://github.com/jifox/nautobot-app-livedata/issues/6) - Bump setuptools from 76.1.0 to 78.1.1 (CVE-2022-40897)

### Changed

- [#75](https://github.com/jifox/nautobot-app-livedata/issues/75) - Bump mkdocs-material from 9.5.50 to 9.6.14
- [#75](https://github.com/jifox/nautobot-app-livedata/issues/75) - Bump debugpy from 1.8.12 to 1.8.14

### Fixed

- [#6](https://github.com/jifox/nautobot-app-livedata/issues/6) - ci.yml to use valid nautobot version un unittest.

### Dependencies

- [#69](https://github.com/jifox/nautobot-app-livedata/issues/69) - Bump mkdocstrings from 0.27.0 to 0.29.1
- [#75](https://github.com/jifox/nautobot-app-livedata/issues/75) - Supported python Versions set to ">=3.9.2,<3.13"
- [#89](https://github.com/jifox/nautobot-app-livedata/issues/89) - Bump ruff from 0.8.6 to 0.11.12

## [v2.4.0 (2025-03-20)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.0)

### Security

- [#57](https://github.com/jifox/nautobot-app-livedata/issues/57) - Fixed Information exposure through an exception (Weakness CWE-209, CWE-497).
- [#57](https://github.com/jifox/nautobot-app-livedata/issues/57) - Fixed Github Action Workflow does not contain permissions (Weakness CWE-275).

### Added

- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - Added a "Live Data" Tab to the Device Details page.

### Changed

- [#12](https://github.com/jifox/nautobot-app-livedata/issues/12) - Changed - Bump docker/build-push-action (5 -> 6)
- [#40](https://github.com/jifox/nautobot-app-livedata/issues/40) - Changed - Bump actions/checkout (2 -> 4)
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
- [#58](https://github.com/jifox/nautobot-app-livedata/issues/58) - Changed - Downgrade mkdocs-material (9.6.4 -> 9.5.50)

### Removed

- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - The following environment variable names are removed
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - 
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - `LIVEDATA_INTERFACE_QUERY_JOB_NAME` use `LIVEDATA_QUERY_JOB_NAME` instead
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - `LIVEDATA_QUERY_INTERFACE_JOB_DESCRIPTION` use `LIVEDATA_QUERY_JOB_DESCRIPTION` instead
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - `LIVEDATA_QUERY_INTERFACE_JOB_SOFT_TIME_LIMIT` use `LIVEDATA_QUERY_JOB_SOFT_TIME_LIMIT` instead
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - `LIVEDATA_QUERY_INTERFACE_JOB_TASK_QUEUE` use `LIVEDATA_QUERY_JOB_TASK_QUEUE`
- [#45](https://github.com/jifox/nautobot-app-livedata/issues/45) - - `LIVEDATA_QUERY_INTERFACE_JOB_HIDDEN` use `LIVEDATA_QUERY_JOB_HIDDEN`


## [v2.4.0b2 (2025-02-19)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.0b2)

### Security

- [#1](https://github.com/jifox/nautobot-app-livedata/issues/1) - Vulnerable OpenSSL included in cryptography wheels fixed weaknesses CWE-392, CWE-1395

### Added

- [#9](https://github.com/jifox/nautobot-app-livedata/issues/9) - Add Dependabot configuration
- [#26](https://github.com/jifox/nautobot-app-livedata/issues/26) - Automated the Towncrier change fragement creation for Dependabot PRs

### Changed

- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - - Update Documentation
- [#32](https://github.com/jifox/nautobot-app-livedata/issues/32) - Revise App description to be more dynamic

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
