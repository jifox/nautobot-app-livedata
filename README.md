# Nautobot App Livedata

<!--
Developer Note - Remove Me!

The README will have certain links/images broken until the PR is merged into `develop`. Update the GitHub links with whichever branch you're using (main etc.) if different.

The logo of the project is a placeholder (docs/images/icon-livedata.png) - please replace it with your app icon, making sure it's at least 200x200px and has a transparent background!

To avoid extra work and temporary links, make sure that publishing docs (or merging a PR) is done at the same time as setting up the docs site on RTD, then test everything.
-->

![Nautobot App Livedata logo](https://raw.githubusercontent.com/jifox/Nautobot-app-livedata/develop/docs/images/icon-livedata.png)

[![CI Status](https://github.com/jifox/Nautobot-app-livedata/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/jifox/Nautobot-app-livedata/actions)
[![Docs Status](https://readthedocs.org/projects/Nautobot-app-livedata/badge/)](https://Nautobot-app-livedata.readthedocs.io/en/latest/)
[![PyPI Version](https://img.shields.io/pypi/v/Nautobot-app-livedata)](https://pypi.org/project/Nautobot-app-livedata/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/Nautobot-app-livedata)](https://pypi.org/project/Nautobot-app-livedata/)

An [App](https://networktocode.com/Nautobot-apps/) for [Nautobot](https://Nautobot.com/).

## Overview

The [Nautobot App LiveData](https://github.com/jifox/nautobot-app-livedata/) is providing real-time data from network devices that are supported by [Netmiko](https://github.com/ktbyers/netmiko).

At the moment, the app is supporting only interface specific data. The data is collected from the devices via platform specific show commands and will be presented in the interface's 'Life Data' tab.

This app addresses the need for dynamic and up-to-date network information, allowing network administrators and engineers to make informed decisions based on the latest data.

### Screenshots

- Live Data Interface Output for interfaces

  ![Livedata output screenshot](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-app-output.png)

- Live Data Device Output for devices

  ![Livedata output screenshot](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-device-output.png)

- Configure the show commands to be executed on Platform level:

  ![Platform Screenshot](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-platform-detail.png)

- Job to clean up old data:

  ![Cleanup Job Results Screenshot](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-app-cleanup-job-results.png)

More screenshots can be found in the [Using the App](https://nautobot-app-livedata.readthedocs.io/en/latest/user/app_use_cases/) page in the documentation. Here's a quick overview of some of the app's added functionality:

## Documentation

Full documentation for this App can be found over on the [Nautobot-App-Livedtata Docs](https://nautobot-app-livedata.readthedocs.io/en/latest) website:

- [User Guide](https://nautobot-app-livedata.readthedocs.io/en/latest/user/app_overview/) - Overview, Using the App, Getting Started.
- [Administrator Guide](https://nautobot-app-livedata.readthedocs.io/en/latest/admin/install/) - How to Install, Configure, Upgrade, or Uninstall the App.
- [Developer Guide](https://nautobot-app-livedata.readthedocs.io/en/latest/dev/contributing/) - Extending the App, Code Reference, Contribution Guide.
- [Release Notes / Changelog](https://nautobot-app-livedata.readthedocs.io/en/latest/admin/release_notes/).
- [Frequently Asked Questions](https://nautobot-app-livedata.readthedocs.io/en/latest/user/faq/).

### Contributing to the Documentation

You can find all the Markdown source for the App documentation under the [`docs`](https://github.com/jifox/nautobot-app-livedata/tree/develop/docs) folder in this repository. For simple edits, a Markdown capable editor is sufficient: clone the repository and edit away.

If you need to view the fully-generated documentation site, you can build it with [MkDocs](https://www.mkdocs.org/). A container hosting the documentation can be started using the `invoke` commands (details in the [Development Environment Guide](https://nautobot-app-livedata.readthedocs.io/en/latest/dev/dev_environment/#docker-development-environment)) on [http://localhost:8001](http://localhost:8001). Using this container, as your changes to the documentation are saved, they will be automatically rebuilt and any pages currently being viewed will be reloaded in your browser.

Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](https://nautobot-app-livedata.readthedocs.io/en/latest/user/faq/) first. Feel free to also swing by the [Network to Code Slack](https://networktocode.slack.com/) (channel `#nautobot`), sign up [here](http://slack.networktocode.com/) if you don't have an account.

## Support for Filter Commands in Live Device Output Using !! Syntax

### Filter Syntax

You can now append a filter command to the end of a device command using the `!!` delimiter. The string following `!!` specifies the filter operation to be applied to the command output.

#### Examples

- `show logging | i {{intf_number}} !!EXACT:{{intf_number}}!!` — Filters the output to contain only lines that contain the interface number as a whole word (e.g., matches `Gi1/0/1`, `1/0/1`, `^1/0/1`, `1/0/1$` but not `11/0/1`, `1/0/11`, `foo1/0/1bar`).
- `show logging !!LAST:100!!` — Returns only the last 100 lines of the output.
- `show logging !!FIRST:10!!` — Returns only the first 10 lines of the output.
- `show logging !!EXACT:{{intf_number}}!!FIRST:5!!` — Filters for lines containing the interface number, then returns only the first 5 matching lines.

### Supported Filters

- `!!EXACT:<pattern>!!` — Only lines that contain `<pattern>` as a whole word (ignoring leading/trailing whitespace, not matching substrings within other numbers or words)
- `!!LAST:<N>!!` — Only the last N lines
- `!!FIRST:<N>!!` — Only the first N lines

Additional filters may be added in the future.

This feature provides a consistent filtering mechanism across all supported platforms, reducing the need for custom scripts or manual output parsing.

---
