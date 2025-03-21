# External Interactions

This document provides an overview of the external interactions of the Nautobot App LiveData, including dependencies and integrations with other systems.

## Dependencies

The Nautobot App LiveData relies on the following external dependencies:

- **Netmiko**: The app uses the [Netmiko](https://github.com/ktbyers/netmiko) library to interact with network devices. Netmiko is a multi-vendor library that simplifies the process of connecting to and executing commands on network devices.
- **Nautobot Plugin Nornir**: The app requires the [Nautobot Plugin Nornir](https://docs.nautobot.com/projects/plugin-nornir/en/stable/) to be installed and configured. This plugin provides the necessary framework for running Nornir tasks within Nautobot.

## Integrations

The Nautobot App LiveData integrates with the following systems:

- **Nautobot**: The app is designed to work seamlessly within the Nautobot ecosystem. It leverages Nautobot's plugin architecture to extend its functionality and provide real-time data from network devices.
- **Nornir**: The app uses Nornir, a Python automation framework, to execute tasks on network devices. Nornir provides a flexible and scalable way to manage network automation tasks.

## Configuration

To configure the external dependencies and integrations, follow these steps:

1. **Install Netmiko**: Ensure that the Netmiko library is installed in your environment. You can install it using pip:
    ```shell
    pip install netmiko
    ```

2. **Install Nautobot Plugin Nornir**: Follow the installation instructions provided in the [Nautobot Plugin Nornir documentation](https://docs.nautobot.com/projects/plugin-nornir/en/stable/).

3. **Configure Nautobot Plugin Nornir**: Add the necessary configuration to your `nautobot_config.py` file to enable and configure the Nautobot Plugin Nornir. Refer to the example configuration provided in the [installation guide](../admin/install.md).

## Usage

After configuring the dependencies and integrations, and defining the platform-specific show commands, you can begin using the Nautobot App LiveData to gather and display real-time data from network devices. The app offers an intuitive interface within Nautobot to view live data on interfaces and devices.

For more information on how to use the app, refer to the [user guide](app_overview.md).
