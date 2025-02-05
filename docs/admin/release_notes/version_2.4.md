# v2.4.0 Release Notes

!!! warning "Developer Note - Remove Me!"
    Guiding Principles:

    - Changelogs are for humans, not machines.
    - There should be an entry for every single version.
    - The same types of changes should be grouped.
    - Versions and sections should be linkable.
    - The latest version comes first.
    - The release date of each version is displayed.
    - Mention whether you follow Semantic Versioning.

    Types of changes:

    - `Added` for new features.
    - `Changed` for changes in existing functionality.
    - `Deprecated` for soon-to-be removed features.
    - `Removed` for now removed features.
    - `Fixed` for any bug fixes.
    - `Security` in case of vulnerabilities.


This document describes all new features and changes in the release `2.4`. The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.4.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- First release of the Nautobot LiveData plugin
- Achieved in this `2.4` release
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

## [v2.4.0] - 2025-02-01

### Added

### Changed

### Fixed

### Deprecated

### Removed

### Security

### Developer Notes

- Setting `NAUTOBOT_TEST_FACTORY_SEED=stable_test_database_records`

    Added to the file `development/development.env` to allow for the use of stable test database records when running tests. This setting is only used when running tests and should not be used in production environments.

- Debugging Nautobot Tests

    To allow debugging tests during executing in docker container the library `debugpy` is used to wait for attaching the debugger.

    To enable the debugging functionality add the following code snippets:

    ```python
    from django.test import TestCase

    from .conftest import wait_for_debugger_connection

    class YourTest(TestCase):
        """Test the ContentTypeUtils class."""

        @classmethod
        def setUpTestData(cls):
            """Set up test data."""
            wait_for_debugger_connection()  # To enable set env REMOTE_TEST_DEBUG_ENABLE=True

        def setUp(self):
            """Set up test data."""
    ```

    Run your tests with the following commands:

    ```bash
    invoke cli

    # root@be0d56e917f9:/source# 
    REMOTE_TEST_DEBUG_ENABLE=True nautobot test --keepdb nautobot_app_livedata
    ```
