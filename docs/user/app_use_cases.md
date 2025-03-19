# Using the App

This document describes common use-cases and scenarios for this App.

## General Usage

Upon installation, the app introduces a 'Live Data' tab to both the interface and device views. This tab displays the most recent data collected from the device or the specific interface.

The data is collected via the Netmiko library, which is a multi-vendor library to simplify Paramiko SSH connections to network devices. The data is collected via the `send_command` method of Netmiko, which is using the platform specific show commands to collect the data.

The data is collected in real-time when the user is accessing the 'Live Data' tab. The data is not stored in the database.

## Screenshots

- Live Data Output for interfaces

  ![Livedata output screenshot](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-app-output.png)

- Live Data Output for devices

  ![Livedata output screenshot](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-device-output.png)
