
# v2.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

## [v2.4.0b2 (2025-02-19)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.0b2)

### Security

- [#1](https://github.com/jifox/nautobot-app-livedata/issues/1) - #1 Vulnerable OpenSSL included in cryptography wheels
- [#1](https://github.com/jifox/nautobot-app-livedata/issues/1) - fixes weaknesses CWE-392, CWE-1395
- [#11](https://github.com/jifox/nautobot-app-livedata/issues/11) - - #17 Update python modules (dependabot)
- [#11](https://github.com/jifox/nautobot-app-livedata/issues/11) - - Bump mkdocs-include-markdown-plugin from 7.1.2 to 7.1.4.
- [#11](https://github.com/jifox/nautobot-app-livedata/issues/11) - - Bump nornir-nautobot from 3.2.0 to 3.3.0
- [#11](https://github.com/jifox/nautobot-app-livedata/issues/11) - - Bump pynautobot from 2.4.2 to 2.6.1
- [#11](https://github.com/jifox/nautobot-app-livedata/issues/11) - - #14 Bump pymarkdownlnt from 0.9.26 to 0.9.28.
- [#11](https://github.com/jifox/nautobot-app-livedata/issues/11) - - #15 Bump coverage from 6.4 to 7.6.12
- [#11](https://github.com/jifox/nautobot-app-livedata/issues/11) - - #16 Bump ruff from 0.8.6 to 0.9.6

### Added

- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - 
- [#9](https://github.com/jifox/nautobot-app-livedata/issues/9) - #9 Add Dependabot configuration
- [#26](https://github.com/jifox/nautobot-app-livedata/issues/26) - #26 Automated the Towncrier change fragement creation for Dependabot PRs

### Changed

- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - - #2 Update Documentation
- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - - Updated README.md
- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - - Updated documentation.
- [#32](https://github.com/jifox/nautobot-app-livedata/issues/32) - #32 Revise App description to be more dynamic

### Fixed

- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - - #2 Update Documentation
- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - - Fixed build status badges in README.md
- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - - Fixed yaml syntax in .github/dependabot.yml
- [#21](https://github.com/jifox/nautobot-app-livedata/issues/21) - #21 Remove trailing spaces from each line of livedata show commands
- [#29](https://github.com/jifox/nautobot-app-livedata/issues/29) - #29 Updated permissions for the "Live Data" tab view to grant access to superusers

### Dependencies

- [#14](https://github.com/jifox/nautobot-app-livedata/issues/14) - #14 Update pymarkdownlnt from 0.9.26 to 0.9.28
- [#15](https://github.com/jifox/nautobot-app-livedata/issues/15) - #15 Update coverage from 6.4 to 7.6.12
- [#22](https://github.com/jifox/nautobot-app-livedata/issues/22) - #22 Update mkdocs-material from 9.5.50 to 9.6.4
- [#23](https://github.com/jifox/nautobot-app-livedata/issues/23) - #23 Update mkdocstrings from 0.27.0 to 0.28.1
- [#25](https://github.com/jifox/nautobot-app-livedata/issues/25) - #25 Update griffe from 1.1.1 to 1.5.7
