# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the App within your Nautobot environment.

## Prerequisites

- The app is compatible with Nautobot 2.4.0 and higher.
- Databases supported: PostgreSQL, MySQL

### Dependencies

- The app `nautobot_plugin_nornir` is required to be installed and configured. See the [Nautobot Plugin Nornir documentation](https://docs.nautobot.com/projects/plugin-nornir/en/stable/) for more details. 

## Install Guide

!!! note
    Apps can be installed from the [Python Package Index](https://pypi.org/) or locally. See the [Nautobot documentation](https://docs.nautobot.com/projects/core/en/stable/user-guide/administration/installation/app-install/) for more details. The pip package name for this app is [`nautobot_app_livedata`](https://pypi.org/project/nautobot_app_livedata/).

### Installation Steps

The app is available as a Python package via PyPI and can be installed with `pip`:

```shell
pip install nautobot_app_livedata
```

To ensure Nautobot App Livedata is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `nautobot_app_livedata` package:

```shell
echo "nautobot_app_livedata" >> local_requirements.txt
```

### Configuration

Once installed, the app needs to be enabled in your Nautobot configuration. The following block of code below shows the additional configuration required to be added to your `nautobot_config.py` file:

- Append `"nautobot_app_livedata"` to the `PLUGINS` list.
- Append the `"nautobot_app_livedata"` dictionary to the `PLUGINS_CONFIG` dictionary and override any defaults.

```python
# In your nautobot_config.py
PLUGINS = ["nautobot_app_livedata"]

PLUGINS_CONFIG = {
    "nautobot_app_livedata": {
        "query_job_name": os.getenv("LIVEDATA_QUERY_JOB_NAME", "Livedata Query Job"),
        "query_job_description": os.getenv(
            "LIVEDATA_QUERY_JOB_DESCRIPTION", "Job to query live data on a device."
        ),
        "query_job_soft_time_limit": int(
            os.getenv("LIVEDATA_QUERY_JOB_SOFT_TIME_LIMIT", "30")
        ),
        "query_job_task_queue": os.getenv("LIVEDATA_QUERY_JOB_TASK_QUEUE", None),
        "query_job_hidden": is_truthy(os.getenv("LIVEDATA_QUERY_JOB_HIDDEN", "True")),
        "query_job_has_sensitive_variables": False,
    }
}
```

### Example Configuration for `nautobot_plugin_nornir`

The following configuration shows an example of how to configure the [nautobot_plugin_nornir](https://docs.nautobot.com/projects/plugin-nornir/en/latest) app:

```python
# In your nautobot_config.py
PLUGINS.append("nautobot_plugin_nornir")
PLUGINS_CONFIG.update(  # type: ignore
    {
        "nautobot_plugin_nornir": {
            "allowed_location_types": ["region", "site"],
            "denied_location_types": ["rack"],
            "nornir_settings": {
                "credentials": (
                    "nautobot_plugin_nornir.plugins.credentials." "nautobot_secrets.CredentialsNautobotSecrets"
                ),
                "runner": {
                    "plugin": "threaded",
                    "options": {
                        "num_workers": 20,
                    },
                },
                # "napalm": {
                #     "extras": {"optional_args": {"global_delay_factor": 5}},
                # },
                "jobs": {
                    "jinja_env": {
                        "undefined": "jinja2.StrictUndefined",
                        "trim_blocks": True,
                        "lstrip_blocks": False,
                    },
                },
            },
            # "secret_access_type": "GENERIC",
            #    (default: GENERIC|CONSOLE|GNMI|HTTP|NETCONF|REST|RESTCONF|SNMP|SSH")
        }
    }
)
```

### Post Installation Steps

Once the Nautobot configuration is updated, run the Post Upgrade command (`nautobot-server post_upgrade`) to run migrations and clear any cache:

```shell
nautobot-server post_upgrade
```

Then restart (if necessary) the Nautobot services which may include:

- Nautobot
- Nautobot Workers
- Nautobot Scheduler

```shell
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```

## App Configuration

The app behavior can be controlled with the following list of settings:

| Key     | Example | Default | Description                          |
| ------- | ------- | ------- | ------------------------------------- |
| `query_job_name` | | "Livedata Query Job" | The unique name of the job that queries live data. |
| `query_job_description` | | `"Job to query live data."` | The description of the job that queries live data. |
| `query_job_soft_time_limit` | 30 | 30 | The soft time limit for the job that queries live data. |
| `query_job_task_queue` | | None | The task queue for the job that queries live data. |
| `query_job_hidden` | True | True | Whether the job that queries live data is a hidden job. |

### Environment Variables

Environment variables can be used to override the default settings:

| Environment Variable | Key | 
| -------------------- | --- |
| `LIVEDATA_QUERY_JOB_NAME` | `query_interface_job_name` |
| `LIVEDATA_QUERY_JOB_DESCRIPTION` | `query_job_description` |
| `LIVEDATA_QUERY_JOB_SOFT_TIME_LIMIT` | `query_job_soft_time_limit` |
| `LIVEDATA_QUERY_JOB_TASK_QUEUE` | `query_job_task_queue` |
| `LIVEDATA_QUERY_JOB_HIDDEN` | `query_job_hidden` |

## Platform Commands

You can configure the show commands to be executed at the platform level. The custom fields are used to store the show commands that are executed on the device. 

![Custom Fields Table](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-custom-fields-table.png)

The [nautobot-plugin-nornir](https://docs.nautobot.com/projects/plugin-nornir/en/latest/) uses Kirk Byers' [Netmiko](https://github.com/ktbyers/netmiko) library to collect data. Data is collected using the `send_command` method with platform-specific show commands.

Open the Nautobot Platform model and configure the custom fields with the show commands that are executed on the device.

### Example Platform Configuration

Here is an example of the platform configuration:

![Platform Detail Form](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-platform-detail.png)

In the input field **Livedata Interface Commands**, add the show commands for interfaces that are executed on the device. One command per line.

The commands are executed in the order they are added to the field.

The following Jinja2 template variables are available to be used in the show commands:

- `{{ device_ip }}` - The primary IP address of the primary device
- `{{ device_name }}` - The device name of the device where the interface is located
- `{{ intf.abbrev }}` - The abbreviated interface name (e.g. "Gi1/0/10")
- `{{ intf.name }}` - The interface name (e.g. "GigabitEthernet1/0/10")
- `{{ intf.name_only }}` - The interface name without the interface number (e.g. "GigabitEthernet")
- `{{ intf.number }}` - The interface name without the interface number (e.g. "1/0/10")
- `{{ obj }}` - The Interface object
- `{{ timestamp }}` - The current timestamp in the format "YYYY-MM-DD HH:MM:SS"

!!! attention
    To insert a linebreak that is visible when showing the Platform detail page, add **two spaces at the end of each line**. The linebreaks are removed when the show commands are executed on the device.

![Livedata Platform Detail Screenshot](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-platform-detail.png)

## Cleanup Job

The app provides a job to clean up old data. The job can be executed on a regular basis to clean up old data that is stored in the database. The job is executed via the Nautobot Scheduler.

![ Cleanup Job Results Screenshot](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-app-cleanup-job-results.png)

The input field **Days to keep** is used to configure the number of days that the query job results is stored in the database. The data that is older than the configured number of days is deleted from the database.

The job provides a **dry-run** mode that can be used to test the job before executing it. The dry-run mode will not delete any data from the database but show the number of records that would be deleted.

## Livedata Query Job

The app uses a job to query live data on an interface. The hidden job is executed when the interface tab "Live Data" is opened. The job is executed via the Nautobot Worker and therefore is not blocking the user interface.

![Livedata Query Job](https://raw.githubusercontent.com/jifox/nautobot-app-livedata/develop/docs/images/livedata-query-job.png)

The job name and description can be configured via envirnment variables.

Here you can also define the time limit and the soft time limit for the job. The soft time limit is the time limit that is used to determine if the job is taking too long to execute. The job is then terminated if the soft time limit is reached.

[Back to App Configuration](#app-configuration)
