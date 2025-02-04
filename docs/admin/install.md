# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the App within your Nautobot environment.

## Prerequisites

- The app is compatible with Nautobot 2.4.0 and higher.
- Databases supported: PostgreSQL, MySQL

### Dependencies

- The app `nautobot_plugin_nornir` is required to be installed and configured. See the [Nautobot Plugin Nornir documentation](https://docs.nautobot.com/projects/plugin-nornir/en/stable/) for more details. 

## Install Guide

!!! note
    Apps can be installed from the [Python Package Index](https://pypi.org/) or locally. See the [Nautobot documentation](https://docs.nautobot.com/projects/core/en/stable/user-guide/administration/installation/app-install/) for more details. The pip package name for this app is [`livedata`](https://pypi.org/project/livedata/).

The app is available as a Python package via PyPI and can be installed with `pip`:

```shell
pip install livedata
```

To ensure Nautobot App Livedata is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `livedata` package:

```shell
echo livedata >> local_requirements.txt
```

Once installed, the app needs to be enabled in your Nautobot configuration. The following block of code below shows the additional configuration required to be added to your `nautobot_config.py` file:

- Append `"nautobot_app_livedata"` to the `PLUGINS` list.
- Append the `"nautobot_app_livedata"` dictionary to the `PLUGINS_CONFIG` dictionary and override any defaults.

```python
# In your nautobot_config.py
PLUGINS = ["nautobot_app_livedata"]

PLUGINS_CONFIG = {
    "nautobot_app_livedata": {
        "query_interface_job_name": os.getenv(
            "LIVEDATA_QUERY_INTERFACE_JOB_NAME", "Livedata Query Interface Job"
        ),
        "query_interface_job_description": os.getenv(
            "LIVEDATA_QUERY_INTERFACE_JOB_DESCRIPTION", "Job to query live data on an interface."
        ),
        "query_interface_job_soft_time_limit": int(
            os.getenv("LIVEDATA_QUERY_INTERFACE_JOB_SOFT_TIME_LIMIT", "30")
        ),
        "query_interface_job_task_queue": os.getenv("LIVEDATA_QUERY_INTERFACE_JOB_TASK_QUEUE", None),
        "query_interface_job_hidden": is_truthy(os.getenv("LIVEDATA_QUERY_INTERFACE_JOB_HIDDEN", "True")),
        "query_interface_job_has_sensitive_variables": False,
    }
}
```

The following configuration shows an example of how to configure
the `nautobot_plugin_nornir` app:

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

!!! warning "Developer Note - Remove Me!"
    Any configuration required to get the App set up. Edit the table below as per the examples provided.

The app behavior can be controlled with the following list of settings:

| Key     | Example | Default | Description                          |
| ------- | ------ | -------- | ------------------------------------- |
| `query_interface_job_name` | | "Livedata Query Interface Job" | The unique name of the job that queries live data on an interface. |
| `query_interface_job_description` | | `"Job to query live data on an interface."` | The description of the job that queries live data on an interface. |
| `query_interface_job_soft_time_limit` | 30 | 30 | The soft time limit for the job that queries live data on an interface. |
| `query_interface_job_task_queue` | | None | The task queue for the job that queries live data on an interface. |
| `query_interface_job_hidden` | True | True | Whether the job that queries live data on an interface is a hidden job. |


Environment variables can be used to override the default settings:

| Environment Variable | Key | 
| -------------------- | --- |
| `LIVEDATA_QUERY_INTERFACE_JOB_NAME` | `query_interface_job_name` |
| `LIVEDATA_QUERY_INTERFACE_JOB_DESCRIPTION` | `query_interface_job_description` |
| `LIVEDATA_QUERY_INTERFACE_JOB_SOFT_TIME_LIMIT` | `query_interface_job_soft_time_limit` |
| `LIVEDATA_QUERY_INTERFACE_JOB_TASK_QUEUE` | `query_interface_job_task_queue` |
| `LIVEDATA_QUERY_INTERFACE_JOB_HIDDEN` | `query_interface_job_hidden` |
