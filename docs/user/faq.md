# Frequently Asked Questions

## How is the Primary Device determined?
If multiple devices share a single management plane, it is necessary to determine the Primary Device. The Primary Device is the one used for live data queries when several devices are configured for a single interface.
The Primary Device is selected based on the following logic:

1. The device associated with the object is initially considered as the Primary Device.
2. If this device does not have a primary IP address:
  - If it is part of a virtual chassis, each member of the chassis is checked for a primary IP address. The first member found with a primary IP is selected as the Primary Device.
  - If no member has a primary IP, an error is raised.
3. The selected device must have a status of "Active". If not, an error is raised.

This ensures that live data queries are always directed to an active device with a valid primary IP address.
