# Using the App

This document describes common use-cases and scenarios for this App.

## General Usage

When the app is installed, it will provide a new tab in the interface view called 'Life Data'. This tab will show the latest data collected from the device for the specific interface.

The data is collected via the Netmiko library, which is a multi-vendor library to simplify Paramiko SSH connections to network devices. The data is collected via the `send_command` method of Netmiko, which is using the platform specific show commands to collect the data.

The data is collected in real-time when the user is accessing the 'Life Data' tab. The data is not stored in the database, and the data is not collected in the background.

## Screenshots

- Live Data Output for interfaces

  ![Livedata output screenshot](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-app-output.png)
