
# v2.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

## [v2.4.0b1 (2025-02-15)](https://github.com/jifox/nautobot-app-livedata.git/releases/tag/v2.4.0b1)

### Added

- [#1](https://github.com/jifox/nautobot-app-livedata/issues/1) - Added tests for the current implementation of the functions

### Fixed

- [#1](https://github.com/jifox/nautobot-app-livedata/issues/1) - Fixed nautobot_database_ready_callback to wait for the database initialization of dependent apps before running the callback. This ensures that the callback is only run once the database is fully initialized and ready for use.
- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - Fixed Read The Docs build error
- [#2](https://github.com/jifox/nautobot-app-livedata/issues/2) - Fixed the test case for the version check
