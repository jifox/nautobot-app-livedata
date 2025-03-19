# Nautobot App LiveData Overview

The Nautobot App LiveData provides real-time data from network devices that are supported by [Netmiko](https://github.com/ktbyers/netmiko). This app is designed to address the need for dynamic and up-to-date network information, allowing network administrators and engineers to make informed decisions based on the latest data.

## Description

The app supports collecting and displaying interface- and device-specific data from network devices. Data is collected using platform-specific show commands configured in the Nautobot Platform model and presented in the interface's and device's 'Live Data' tab. Additionally, the app includes a cleanup job to remove old data from the database.

## Audience (User Personas) - Who should use this App?

This app is intended for network administrators and engineers who require real-time data from network devices to make informed decisions. It is particularly useful for those who need dynamic and up-to-date network information.

## Authors and Maintainers

The Nautobot App LiveData is maintained by the Nautobot community. Contributions and maintenance are managed by the core development team and community contributors.

## Nautobot Features Used

- **Custom Fields**: The app uses custom fields to store platform-specific show commands.
- **Jobs**: The app includes jobs for querying live data and cleaning up old data.
- **Plugins**: The app is installed and configured as a Nautobot plugin.

### Extras

- **Custom Fields**: The app creates custom fields for storing show commands on the platform level.
- **Jobs**: The app installs the following jobs:
  - `Livedata Query Job`: Queries live data on an interface.
  - `Cleanup Job`: Cleans up old data stored in the database.
