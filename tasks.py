"""Tasks for use with Invoke.

Copyright (c) 2023, Network to Code, LLC
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
from pathlib import Path
import re
import sys
from time import sleep

from dotenv import load_dotenv
from invoke.collection import Collection
from invoke.exceptions import Exit, UnexpectedExit
from invoke.tasks import Task, task as invoke_task
import jinja2
import toml
import yaml  # Added for parsing docker compose config output

# Set the environment files to be sourced in order. The highest priority file should be listed last.
ENVIRONMENT_FILENAMES = ["dev.env", "development.env", "local.env", ".env", ".creds.env", "creds.env"]
ENVIRONMENT_DIRS = [
    ".",  # Current directory
    "development",  # Development directory
    "environments",  # Environments directory
]
# Load environment variables from the specified files
for envfile in ENVIRONMENT_FILENAMES:
    for dir in ENVIRONMENT_DIRS:
        if not os.path.isabs(dir):
            dir = os.path.join(os.getcwd(), dir)
            # Check if the environment file exists in the current directory or in the development directory
        if not os.path.exists(dir):
            continue
        # If the file exists, source it
        # If the directory is not absolute, make it absolute
        dir = os.path.abspath(dir)
        fname = os.path.join(dir, envfile)
        if os.path.isfile(fname):
            print(f"Loading environment variables from {fname}")
            load_dotenv(fname, override=True)


# This is the invoke configuration name that is used as context for the tasks. (invoke.yml)
CONFIGURATION_NAMESPACE = os.getenv("CONFIGURATION_NAMESPACE", "nautobot_app_livedata")


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Examples:
        >>> is_truthy('yes')
        True
    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg

    val = str(arg).lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"Invalid truthy value: `{arg}`")


# Defined in local.env or creds.env
db_container_name = os.getenv("NAUTOBOT_DB_HOST", "db")
redis_container_name = os.getenv("NAUTOBOT_REDIS_HOST", "redis")

# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_NAUTOBOT_APP_LIVEUPDATE_xxx
namespace = Collection(CONFIGURATION_NAMESPACE)
namespace.configure(
    {
        CONFIGURATION_NAMESPACE: {
            "nautobot_ver": "2.4.14",
            "project_name": CONFIGURATION_NAMESPACE,
            "python_ver": "3.12",
            "local": False,
            "use_django_extensions": True,
            "docker_swarm_mode": False,
            "render_templates": False,  # Automatically render docker-compose templates from Jinja2 templates
            "compose_dir": os.path.join(os.path.dirname(__file__), "development/"),
            "compose_files": [
                "docker-compose.base.yml",
                "docker-compose.redis.yml",
                "docker-compose.postgres.yml",
                "docker-compose.dev.yml",
            ],
            "compose_http_timeout": "86400",
            "nautobot_container_name": "nautobot",
            "db_container_name": globals().get("db_container_name", "db"),
            "redis_container_name": globals().get("redis_container_name", redis_container_name),
        }
    }
)


def get_pyproject_nautobot_version():
    with open("pyproject.toml", "r", encoding="utf8") as pyproject:
        parsed_toml = toml.load(pyproject)
    try:
        pyproject_neutobot_version = parsed_toml["tool"]["poetry"]["dependencies"]["nautobot"]["version"]
    except TypeError:
        pyproject_neutobot_version = parsed_toml["tool"]["poetry"]["dependencies"]["nautobot"]
    # Filter all Chars but 0-9,a-z,'.'
    pyproject_neutobot_version = re.sub(r"[^0-9a-z.]+", "", pyproject_neutobot_version.lower())
    return pyproject_neutobot_version


def get_nautobot_version(context):
    """Get Nautobot version from the context."""
    if context.nautobot_ver == "pyproject":
        context.nautobot_ver = get_pyproject_nautobot_version()
    return context.nautobot_ver


def _available_services(context):
    """Get a list of available services from the docker compose configuration."""
    result = docker_compose(context, "config --services", pty=False, echo=False, hide=True)
    return [service.strip() for service in result.stdout.splitlines() if service.strip()]


def _await_healthy_service(context, service):
    container_id = docker_compose(context, f"ps -q -- {service}", pty=False, echo=False, hide=True).stdout.strip()
    _await_healthy_container(context, container_id)


def _await_healthy_container(context, container_id):
    while True:
        result = context.run(
            "docker inspect --format='{{.State.Health.Status}}' " + container_id,
            pty=False,
            echo=False,
            hide=True,
        )
        if result.stdout.strip() == "healthy":
            break
        print(f"Waiting for `{container_id}` container to become healthy ...")
        sleep(1)


def _get_docker_nautobot_version(context, nautobot_ver=None, python_ver=None):
    """Extract Nautobot version from base docker image."""
    ctx = context[CONFIGURATION_NAMESPACE]
    if nautobot_ver is None:
        nautobot_ver = get_nautobot_version(context)
    if python_ver is None:
        python_ver = ctx.python_ver
    dockerfile_path = os.path.join(ctx.compose_dir, "Dockerfile")
    base_image = context.run(f"grep --max-count=1 '^FROM ' {dockerfile_path}", hide=True).stdout.strip().split(" ")[1]
    base_image = base_image.replace(r"${NAUTOBOT_VER}", nautobot_ver).replace(r"${PYTHON_VER}", python_ver)
    pip_nautobot_ver = context.run(f"docker run --rm --entrypoint '' {base_image} pip show nautobot", hide=True)
    match_version = re.search(r"^Version: (.+)$", pip_nautobot_ver.stdout.strip(), flags=re.MULTILINE)
    if match_version:
        return match_version.group(1)
    else:
        raise Exit(f"Nautobot version not found in Docker base image {base_image}.")


def _is_compose_included(context, name):
    """Check if a specific docker compose file is included in the current context."""
    ctx = context[CONFIGURATION_NAMESPACE]
    return f"docker-compose.{name}.yml" in ctx.compose_files


def _is_service_running(context, service):
    """Check if a specific service is running in the current context."""
    results = docker_compose(context, "ps --services --filter status=running", hide="out")
    return service in results.stdout.splitlines()


def _print_context_info(context):
    """Print the Nautobot Docker Compose context information."""
    ctx = context[CONFIGURATION_NAMESPACE]
    if not ctx:
        print("Nautobot Docker Compose context is not configured.")
        return
    print("--" * 40)
    print("Nautobot Docker Compose Environment")
    print(f"Using PYPROJECT_NAUTOBOT_VERSION:   {get_pyproject_nautobot_version()}")
    print(f"Using Nautobot version:             {get_nautobot_version(ctx)}")
    print(f"Using Python version:               {ctx.python_ver}")
    print(f"Using database container name:      {ctx.db_container_name}")
    print(f"Using redis container name:         {ctx.redis_container_name}")
    print(f"Using nautobot container name:      {ctx.nautobot_container_name}")
    print("--" * 40)


def _service_name(context, service):
    """Get the service name from the context."""
    ctx = context[CONFIGURATION_NAMESPACE]
    if service == "nautobot":
        return ctx.nautobot_container_name
    elif service == "db":
        print("Using db container name:", ctx.db_container_name)
        return ctx.db_container_name
    elif service == "redis":
        print("Using redis container name:", ctx.redis_container_name)
        return ctx.redis_container_name
    else:
        return service


def task(function=None, *args, **kwargs):
    """Task decorator to override the default Invoke task decorator and add each task to the invoke namespace."""

    def task_wrapper(function=None):
        """Wrapper around invoke.task to add the task to the namespace as well."""
        if args or kwargs:
            task_func = invoke_task(*args, **kwargs)(function)
        else:
            task_func = invoke_task(function)
        if not isinstance(task_func, Task):
            task_func = Task(task_func)
        namespace.add_task(task_func)
        return task_func

    if function:
        # The decorator was called with no arguments
        return task_wrapper(function)
    # The decorator was called with arguments
    return task_wrapper


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
COMPOSE_ENV_DIR = os.path.join(os.path.dirname(__file__), "environments")

# Render docker-compose YAML from Jinja2 templates before running docker compose


def render_compose_templates(context):
    """Render all docker-compose .j2 templates to environments/ as .yml files."""
    ctx = context[CONFIGURATION_NAMESPACE]
    # ruff: noqa: S701
    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR), autoescape=False)
    imgnam = ctx.nautobot_container_name.replace("_", "-").replace(" ", "-").lower().replace("nautobot-", "nautobot2-")
    variables = {
        "nautobot_container_name": ctx.nautobot_container_name,
        "nautobot_image_name": imgnam,
        "db_container_name": ctx.db_container_name,
        "nautobot_version": get_nautobot_version(ctx),
        "python_ver": ctx.python_ver,
    }
    print("Rendering docker-compose templates with variables:")
    for key, value in variables.items():
        print(f"  {key}: {value}")
    for fname in os.listdir(TEMPLATE_DIR):
        if fname.endswith(".j2"):
            template = jinja_env.get_template(fname)
            rendered = template.render(**variables)
            outname = fname[:-3]  # remove .j2
            outpath = os.path.join(COMPOSE_ENV_DIR, outname)
            with open(outpath, "w") as f:
                f.write(rendered)


# Remove the broken patching logic (orig_docker_compose = docker_compose)
# The correct docker_compose function is already defined below with render_compose_templates at the start.


def docker_compose(context, command, **kwargs):
    """Helper function for running a specific docker compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """
    ctx = context[CONFIGURATION_NAMESPACE]
    if ctx.render_templates:
        render_compose_templates(context)

    compose_env = {
        "NAUTOBOT_CONTAINER_NAME": ctx.nautobot_container_name,
        # Note: 'docker compose logs' will stop following after 60 seconds by default,
        # so we are overriding that by setting this environment variable.
        "COMPOSE_HTTP_TIMEOUT": ctx.compose_http_timeout,
        "NAUTOBOT_VER": ctx.nautobot_ver,
        "PYTHON_VER": ctx.python_ver,
        **kwargs.pop("env", {}),
    }
    compose_command_tokens = [
        "docker compose",
        f"--project-name {ctx.project_name}",
        f'--project-directory "{ctx.compose_dir}"',
    ]
    for compose_file in ctx.compose_files:
        compose_file_path = os.path.join(ctx.compose_dir, compose_file)
        compose_command_tokens.append(f' -f "{compose_file_path}"')

    compose_command_tokens.append(command)

    # If `service` was passed as a kwarg, add it to the end.
    service = kwargs.pop("service", None)
    if service is not None:
        compose_command_tokens.append(service)

    silent = kwargs.pop("silent", False)
    if not silent:
        print(f'Running docker compose command "{command}"')
    compose_command = " ".join(compose_command_tokens)

    return context.run(compose_command, env=compose_env, **kwargs)


def run_command(context, command, service="nautobot", **kwargs):
    """Wrapper to run a command locally or inside the nautobot container."""
    ctx = context[CONFIGURATION_NAMESPACE]
    service = _service_name(context, service)
    if is_truthy(ctx.local):
        if "command_env" in kwargs:
            kwargs["env"] = {
                **kwargs.get("env", {}),
                **kwargs.pop("command_env"),
            }
        return context.run(command, **kwargs)
    else:
        # Check if service is running, no need to start another container to run a command
        docker_compose_status = "ps --services --filter status=running"
        results = docker_compose(context, docker_compose_status, hide="out")

        command_env_args = ""
        if "command_env" in kwargs:
            command_env = kwargs.pop("command_env")
            for key, value in command_env.items():
                command_env_args += f' --env="{key}={value}"'

        if service in results.stdout:
            compose_command = f"exec{command_env_args} {service} {command}"
        else:
            compose_command = f"run{command_env_args} --rm --entrypoint='{command}' {service}"

        pty = kwargs.pop("pty", True)

        return docker_compose(context, compose_command, pty=pty, **kwargs)


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task(
    help={
        "force_rm": "Always remove intermediate containers (defaults to True)",
        "cache": "Whether to use Docker's cache when building the image (defaults to enabled)",
    }
)
def build(context, force_rm=True, cache=True):
    """Build Nautobot docker image."""
    ctx = context[CONFIGURATION_NAMESPACE]
    # Pull all git repositories in the plugins directory (but not the main repo)
    # Update the submodules to ensure all plugins are up-to-date
    if not ctx.local:
        print("Pulling latest changes from git submodules...")
        context.run("git submodule update --remote --merge", pty=False, echo=False, hide=True)
    else:
        print("Updating git submodules...")

    command = "build"

    if not cache:
        command += " --no-cache"
    if force_rm:
        command += " --force-rm"

    print(f"Building Nautobot with Python {ctx.python_ver}...")
    docker_compose(context, command)


@task
def generate_packages(context):
    """Generate all Python packages inside docker and copy the file locally under dist/."""
    command = "poetry build"
    run_command(context, command)


@task(
    help={
        "check": (
            "If enabled, check for outdated dependencies in the poetry.lock file, "
            "instead of generating a new one. (default: disabled)"
        ),
        "constrain_nautobot_ver": (
            "Run 'poetry add nautobot@[version] --lock' to generate the lockfile, "
            "where [version] is the version installed in the Dockerfile's base image. "
            "Generally intended to be used in CI and not for local development. (default: disabled)"
        ),
        "constrain_python_ver": (
            "When using `constrain_nautobot_ver`, further constrain the nautobot version "
            "to python_ver so that poetry doesn't complain about python version incompatibilities. "
            "Generally intended to be used in CI and not for local development. (default: disabled)"
        ),
    }
)
def lock(context, check=False, constrain_nautobot_ver=False, constrain_python_ver=False):
    """Generate poetry.lock file."""
    ctx = context[CONFIGURATION_NAMESPACE]
    if constrain_nautobot_ver:
        docker_nautobot_version = _get_docker_nautobot_version(context)
        command = f"poetry add --lock nautobot@{docker_nautobot_version}"
        if constrain_python_ver:
            command += f" --python {ctx.python_ver}"
        try:
            run_command(context, command, hide=True)
            output = run_command(context, command, hide=True)
            print(output.stdout, end="")
            print(output.stderr, file=sys.stderr, end="")
        except UnexpectedExit:
            print("Unable to add Nautobot dependency with version constraint, falling back to git branch.")
            command = f"poetry add --lock git+https://github.com/nautobot/nautobot.git#{get_nautobot_version(ctx)}"
            if constrain_python_ver:
                command += f" --python {ctx.python_ver}"
            run_command(context, command)
    else:
        command = f"poetry {'check' if check else 'lock --no-update'}"
        run_command(context, command)


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------
@task(help={"service": "If specified, only affect this service."})
def debug(context, service=""):
    """Start specified or all services and its dependencies in debug mode."""
    _print_context_info(context)
    print(f"Starting {service} in debug mode...")
    docker_compose(context, "up", service=service)


@task(help={"service": "If specified, only affect this service."})
def start(context, service=""):
    """Start specified or all services and its dependencies in detached mode."""
    _print_context_info(context)
    print("Starting Nautobot in detached mode...")
    service = _service_name(context, service)
    docker_compose(context, "up --detach", service=service)


@task(help={"service": "If specified, only affect this service."})
def restart(context, service=""):
    """Gracefully restart specified or all services."""
    print("Restarting Nautobot...")
    docker_compose(context, "restart", service=service)


@task(help={"service": "If specified, only affect this service."})
def stop(context, service=""):
    """Stop specified or all services, if service is not specified, remove all containers."""
    print("Stopping Nautobot...")
    docker_compose(context, "stop" if service else "down --remove-orphans", service=service)


@task(
    aliases=("down",),
    help={
        "volumes": "Remove Docker compose volumes (default: True)",
        "import-db-file": "Import database from `import-db-file` file into the fresh environment (default: empty)",
        "confirm": "Require confirmation before destroying all data (default: True)",
    },
)
def destroy(context, volumes=True, import_db_file="", confirm=True):
    """Destroy all containers and volumes. WARNING: This will delete ALL data!"""
    ctx = context[CONFIGURATION_NAMESPACE]
    if confirm:
        print("Conatiner Name: ", ctx.nautobot_container_name)
        print("WARNING: This operation will delete ALL containers, volumes, and data. This action is irreversible!")
        response = input("Are you sure you want to continue? Type 'yes' to proceed: ")
        if response.strip().lower() != "yes":
            print("Aborted by user.")
            return
    print("Destroying Nautobot...")
    docker_compose(context, f"down --remove-orphans {'--volumes' if volumes else ''}")

    if not import_db_file:
        return

    if not volumes:
        raise ValueError("Cannot specify `--no-volumes` and `--import-db-file` arguments at the same time.")

    print(f"Importing database file: {import_db_file}...")

    input_path = Path(import_db_file).absolute()
    if not input_path.is_file():
        raise ValueError(f"File not found: {input_path}")

    command = [
        "run",
        "--rm",
        "--detach",
        f"--volume='{input_path}:/docker-entrypoint-initdb.d/dump.sql'",
        "--",
        f"{ctx.db_container_name}",
    ]

    container_id = docker_compose(context, " ".join(command), pty=False, echo=False, hide=True).stdout.strip()
    _await_healthy_container(context, container_id)
    print("Stopping database container...")
    context.run(f"docker stop {container_id}", pty=False, echo=False, hide=True)

    print("Database import complete, you can start Nautobot with the following command:")
    print("invoke start")


@task
def export(context):
    """Export docker compose configuration to `compose.yaml` file.

    Useful to:

    - Debug docker compose configuration.
    - Allow using `docker compose` command directly without invoke.
    """
    docker_compose(context, "convert > compose.yaml")


@task(name="ps", help={"all": "Show all, including stopped containers"})
def ps_task(context, all=False):
    """List containers."""
    docker_compose(context, f"ps {'--all' if all else ''}")


@task
def vscode(context):
    """Launch Visual Studio Code with the appropriate Environment variables to run in a container."""
    command = "code nautobot.code-workspace"

    context.run(command)


@task(
    help={
        "service": "If specified, only display logs for this service (default: all)",
        "follow": "Flag to follow logs (default: False)",
        "tail": "Tail N number of lines (default: all)",
    }
)
def logs(context, service="", follow=False, tail=0):
    """View the logs of a docker compose service."""
    command = "logs "

    if follow:
        command += "--follow "
    if tail:
        command += f"--tail={tail} "

    docker_compose(context, command, service=service)


@task(help={"service": "If specified, only affect this service."})
def config(context, service=""):
    """Generate and validate the docker compose configuration."""
    if service:
        service = _service_name(context, service)
    print("Generating Docker Compose configuration...")
    docker_compose(context, "config", service=service)


@task(help={"service": "If specified, only affect this service."})
def image_names(context, service=""):
    """List Docker image names for the specified service or all services.

    If no service is specified, it will list all services and their images.

    Output format:
        service_name: image_name
    """
    if service:
        service = _service_name(context, service)
    # Get the full docker compose config as YAML
    result = docker_compose(context, "config", service=service, pty=False, echo=False, hide=True, silent=True)
    config = yaml.safe_load(result.stdout)
    services = config.get("services", {})
    if not services:
        print("No services found in docker compose config.")
        return
    if service:
        svc = services.get(service)
        if svc:
            image = svc.get("image")
            if image:
                print(f"{service}: {image}")
            else:
                print(f"{service}: <no image specified>")
        else:
            print(f"Service '{service}' not found in docker compose config.")
    else:
        for svc_name, svc in services.items():
            image = svc.get("image")
            if image:
                print(f"{svc_name}: {image}")
            else:
                print(f"{svc_name}: <no image specified>")


@task(
    help={
        "service": "Docker compose service name to push image for (default: nautobot).",
        "registry": "Registry to push to (default: Docker Hub)",
    }
)
def image_push(context, service="nautobot", registry=""):
    """Push the docker image for the specified service to the registry."""
    if service:
        service = _service_name(context, service)
    # Get the full docker compose config as YAML
    result = docker_compose(context, "config", service=service, pty=False, echo=False, hide=True, silent=True)
    config = yaml.safe_load(result.stdout)
    services = config.get("services", {})
    if not services or not services.get(service):
        print(f"No image specified for service '{service}' in docker compose config.")
        return
    image = services[service].get("image")
    # Optionally prepend registry
    if registry:
        image_tag = f"{registry}/{image}"
    else:
        image_tag = f"{image}"
    print(f"Pushing image {image_tag} to registry...")
    context.run(f"docker push {image_tag}")
    print(f"Image {image_tag} pushed successfully.")


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task(
    help={
        "file": "Python file to execute",
        "env": "Environment variables to pass to the command",
        "plain": "Flag to run nbshell in plain mode (default: False)",
    },
)
def nbshell(context, file="", env={}, plain=False):
    """Launch an interactive nbshell session."""
    command = [
        "nautobot-server",
        "nbshell",
        "--plain" if plain else "",
        f"< '{file}'" if file else "",
    ]
    run_command(context, " ".join(command), pty=not bool(file), command_env=env)


@task(
    help={},
)
def shell_plus(context):
    """Launch an interactive nbshell session."""
    ctx = context[CONFIGURATION_NAMESPACE]
    if not ctx.use_django_extensions:
        nbshell(context)
    else:
        command = "nautobot-server shell_plus"
        run_command(context, command, pty=True)


@task(
    help={
        "service": "Docker compose service name to launch cli in (default: nautobot).",
    }
)
def cli(context, service="nautobot"):
    """Launch a bash shell inside the container."""
    service = _service_name(context, service)
    run_command(context, "bash", service=service)


@task(
    help={
        "service": "Docker compose service name to run command in (default: nautobot).",
        "command": "Command to run (default: bash).",
        "file": "File to run command with (default: empty)",
    }
)
def exec(context, service="nautobot", command="bash", file=""):
    """Launch a command inside the running container (defaults to bash shell inside nautobot container)."""
    service = _service_name(context, service)
    command = [
        "exec",
        "--",
        service,
        command,
        f"< '{file}'" if file else "",
    ]
    docker_compose(context, " ".join(command), pty=not bool(file))


@task(
    help={
        "user": "name of the superuser to create (default: admin)",
    }
)
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    command = f"nautobot-server createsuperuser --username {user}"

    run_command(context, command)


@task(
    help={
        "name": "name of the migration to be created; if unspecified, will autogenerate a name",
    }
)
def makemigrations(context, name=""):
    """Perform makemigrations operation in Django."""
    command = f"nautobot-server makemigrations {CONFIGURATION_NAMESPACE}"

    if name:
        command += f" --name {name}"

    run_command(context, command)


@task
def migrate(context):
    """Perform migrate operation in Django."""
    command = "nautobot-server migrate"

    run_command(context, command)


@task(help={})
def post_upgrade(context):
    """
    Performs Nautobot common post-upgrade operations using a single entrypoint.

    This will run the following management commands with default settings, in order:

    - migrate
    - trace_paths
    - collectstatic
    - remove_stale_contenttypes
    - clearsessions
    - invalidate all
    """
    command = "nautobot-server post_upgrade"

    run_command(context, command)


@task(
    help={
        "action": (
            "Available values are `['lint', 'format']`. Can be used multiple times. (default: `['lint', 'format']`)"
        ),
        "target": "File or directory to inspect, repeatable (default: all files in the project will be inspected)",
        "fix": "Automatically fix selected actions. May not be able to fix all issues found. (default: False)",
        "output_format": "See https://docs.astral.sh/ruff/settings/#output-format for details. (default: `concise`)",
    },
    iterable=["action", "target"],
)
def ruff(context, action=None, target=None, fix=False, output_format="concise"):
    """Run ruff to perform code formatting and/or linting."""
    _print_context_info(context)
    if not action:
        action = ["lint", "format"]
    if not target:
        target = ["."]

    exit_code = 0

    if "format" in action:
        command = "ruff format "
        if not fix:
            command += "--check "
        command += " ".join(target)
        if not run_command(context, command, warn=True):
            exit_code = 1

    if "lint" in action:
        command = "ruff check "
        if fix:
            command += "--fix "
        command += f"--output-format {output_format} "
        command += " ".join(target)
        if not run_command(context, command, warn=True):
            exit_code = 1

    if exit_code != 0:
        raise Exit(code=exit_code)


@task
def import_nautobot_data(context):
    """Import nautobot_data.json."""
    # This task expects to be run in the docker container for now
    ctx = context[CONFIGURATION_NAMESPACE]
    ctx.local = False
    nautobot = ctx.nautobot_container_name
    copy_cmd = f"docker cp nautobot_data.json {ctx.project_name}_{nautobot}_1:/tmp/nautobot_data.json"
    import_cmd = "nautobot-server import_nautobot_json /tmp/nautobot_data.json 2.10.4"
    print("Starting Nautobot")
    start(context)
    print("Copying Nautobot data to container")
    context.run(copy_cmd)
    print("Starting Import")
    print(import_cmd)
    run_command(context, import_cmd)


@task
def render_compose(context):
    """Render docker-compose YAML files from Jinja2 templates only."""
    render_compose_templates(context)
    print("Docker Compose YAML files rendered from templates.")


# ------------------------------------------------------------------------------
# BACKUP / EXPORT
# ------------------------------------------------------------------------------


@task(
    help={
        "db-name": "Database name to backup (default: Nautobot database)",
        "output-file": "Ouput file, overwrite if exists (default: `dump.sql`)",
        "readable": "Flag to dump database data in more readable format (default: `True`)",
    }
)
def backup_db(context, db_name="", output_file="dump.sql", readable=True):
    """Dump database into `output_file` file from `db` container.
    This task will ensure that the `db` container is running and healthy before performing the backup.
    """
    ctx = context[CONFIGURATION_NAMESPACE]
    db = ctx.db_container_name
    if not _is_service_running(context, db):
        start(context, db)
    _await_healthy_service(context, db)

    command = [f"exec -- {db} sh -c '"]

    if _is_compose_included(context, "mysql"):
        command += [
            "mysqldump",
            "--user=root",
            "--password=$MYSQL_ROOT_PASSWORD",
            "--skip-extended-insert" if readable else "",
            db_name if db_name else "$MYSQL_DATABASE",
        ]
    elif _is_compose_included(context, "postgres"):
        command += [
            "pg_dump",
            "--username=$POSTGRES_USER",
            f"--dbname={db_name or '$POSTGRES_DB'}",
            "--inserts" if readable else "",
        ]
    else:
        raise ValueError("Unsupported database backend.")

    command += [
        "'",
        f"> '{output_file}'",
    ]

    docker_compose(context, " ".join(command), pty=False)

    print(50 * "=")
    print("The database backup has been successfully completed and saved to the following file:")
    print(output_file)
    print("You can import this database backup with the following command:")
    print(f"invoke import-db --input-file '{output_file}'")
    print(50 * "=")


@task(
    help={
        "db-name": "Database name to backup (default: Nautobot database)",
        "output-file": "Ouput file, overwrite if exists (default: `dump.sql`)",
        "readable": "Flag to dump database data in more readable format (default: `True`)",
    }
)
def db_export(context, db_name="", output_file="dump.sql", readable=True):
    """Alias for `backup_db` task.
    DEPRECATED: Use `invoke backup-db` instead.
    """
    backup_db(context, db_name=db_name, output_file=output_file, readable=readable)


@task(
    help={
        "media-dir": "Media directory to backup (default: `/opt/nautobot/media`)",
        "output-file": "Ouput file, overwrite if exists (default: `media.tgz`)",
    }
)
def backup_media(context, media_dir="/opt/nautobot/media", output_file="media.tgz"):
    """Dump all media files into `output_file` file from `nautobot` container."""
    ctx = context[CONFIGURATION_NAMESPACE]
    media_dir = media_dir.strip().rstrip("/")  # Ensure the media directory ends with a slash
    if not media_dir.startswith("/"):
        raise ValueError("Media directory must be an absolute path, starting with '/'.")
    # Check if nautobot is running, no need to start another nautobot container to run a command
    nautobot = ctx.nautobot_container_name
    is_run = _is_service_running(context, service=nautobot)
    if not is_run:
        start(context, nautobot)
    _await_healthy_service(context, nautobot)

    command = [f"exec -- {nautobot} sh -c '"]
    command += ["tar", "-czf", "-", media_dir]
    command += [
        "'",
        f"> '{output_file}'",
    ]

    docker_compose(context, " ".join(command), pty=False)

    print(50 * "=")
    print("The media files backup has been successfully completed and saved to the following file:")
    print(output_file)
    print("You can import this media files backup with the following command:")
    print(f"invoke import-media --input-file '{output_file}'")
    print(50 * "=")


@task(
    help={
        "media-dir": "Media directory to backup (default: `/opt/nautobot/media`)",
        "output-file": "Ouput file, overwrite if exists (default: `media.tgz`)",
    }
)
def media_export(context, media_dir="/opt/nautobot/media", output_file="media.tgz"):
    """Alias for `backup_media` task.
    DEPRECATED: Use `invoke backup-media` instead.
    """
    backup_media(context, media_dir=media_dir, output_file=output_file)


# ------------------------------------------------------------------------------
# RESTORE / IMPORT
# ------------------------------------------------------------------------------


@task(
    help={
        "db-name": "Database name to create (default: Nautobot database)",
        "input-file": (
            "SQL dump file to replace the existing database with. This can be generated "
            "using `invoke backup-db` (default: `dump.sql`)."
        ),
    }
)
def restore_db(context, db_name="", input_file="dump.sql"):
    """Stop Nautobot containers and replace the current database with the dump into `db` container."""
    ctx = context[CONFIGURATION_NAMESPACE]
    all_services = _available_services(context)
    stop_db_dependend_services = all_services.copy()
    stop_services_str = ""
    for service in all_services:
        if service in [ctx.nautobot_container_name, ctx.db_container_name]:
            continue
        stop_db_dependend_services.remove(service)
    stop_services_str = " ".join(stop_db_dependend_services)

    if stop_services_str == "":
        print("No services to stop, starting Nautobot DB import...")
    else:
        print(f"Stopping services: {stop_services_str} before DB import...")
        docker_compose(context, f"stop -- {stop_services_str}", pty=False)
    print("Starting Database Service for import...\n")
    db = ctx.db_container_name
    start(context, db)
    _await_healthy_service(context, db)

    command = [f"exec -- {db} sh -c '"]

    if _is_compose_included(context, "mysql"):
        if not db_name:
            db_name = "$MYSQL_DATABASE"
        command += [
            "mysql --user root --password=$MYSQL_ROOT_PASSWORD",
            '--execute="',
            f"DROP DATABASE IF EXISTS {db_name};",
            f"CREATE DATABASE {db_name};",
            (
                ""
                if db_name == "$MYSQL_DATABASE"
                else f"GRANT ALL PRIVILEGES ON {db_name}.* TO $MYSQL_USER; FLUSH PRIVILEGES;"
            ),
            '"',
            "&&",
            "mysql",
            f"--database={db_name}",
            "--user=$MYSQL_USER",
            "--password=$MYSQL_PASSWORD",
        ]
    elif _is_compose_included(context, "postgres"):
        if not db_name:
            db_name = "$POSTGRES_DB"
        command += [
            f"dropdb --if-exists --user=$POSTGRES_USER {db_name} &&",
            f"createdb --user=$POSTGRES_USER {db_name} &&",
            f"psql --user=$POSTGRES_USER --dbname={db_name}",
        ]
    else:
        raise ValueError("Unsupported database backend.")

    command += [
        "'",
        f"< '{input_file}'",
    ]
    docker_compose(context, " ".join(command), pty=False)
    print("Database import complete, you can start Nautobot now: `invoke stop post-upgrade start`")


@task(
    help={
        "db-name": "Database name to create (default: Nautobot database)",
        "input-file": (
            "SQL dump file to replace the existing database with. This can be generated "
            "using `invoke backup-db` (default: `dump.sql`)."
        ),
    }
)
def db_import(context, db_name="", input_file="dump.sql"):
    """Alias for `restore_db_import` task.
    DEPRECATED: Use `invoke restore-db` instead.
    """
    restore_db(context, db_name=db_name, input_file=input_file)


@task(
    help={
        "input-file": (
            "Tar file containing media files from backup. This can be generated "
            "using `invoke backup-media` (default: `media.tgz`)."
        ),
    }
)
def restore_media(context, input_file="media.tgz"):
    """Start Nautobot containers and restore the media files into `nautobot` container."""
    ctx = context[CONFIGURATION_NAMESPACE]
    # Check if nautobot is running, no need to start another nautobot container to run a command
    nautobot = ctx.nautobot_container_name
    is_run = _is_service_running(context, service=nautobot)
    if not is_run:
        start(context, nautobot)
    _await_healthy_service(context, nautobot)
    command = [f"exec -- {nautobot} sh -c '"]
    command += ["tar", "-xzf", "-", "-C", "/"]
    command += [
        "'",
        f"< '{input_file}'",
    ]

    docker_compose(context, " ".join(command), pty=False)
    print("Media files import complete, all files are now available in Nautobot container.")


@task(
    help={
        "input-file": (
            "Tar file containing media files from backup. This can be generated "
            "using `invoke backup-media` (default: `media.tgz`)."
        ),
    }
)
def media_import(context, input_file="media.tgz"):
    """Alias for `restore_media` task.
    DEPRECATED: Use `invoke restore-media` instead.
    """
    restore_media(context, input_file=input_file)


@task(
    help={
        "db-name": "Database name (default: Nautobot database)",
        "input-file": "SQL file to execute and quit (default: empty, start interactive CLI)",
        "output-file": "Ouput file, overwrite if exists (default: empty, output to stdout)",
        "query": "SQL command to execute and quit (default: empty)",
    }
)
def dbshell(context, db_name="", input_file="", output_file="", query=""):
    """Start database CLI inside the running `db` container.

    Doesn't use `nautobot-server dbshell`, using started `db` service container only.
    """
    ctx = context[CONFIGURATION_NAMESPACE]
    db = ctx.db_container_name
    if input_file and query:
        raise ValueError("Cannot specify both, `input_file` and `query` arguments")
    if output_file and not (input_file or query):
        raise ValueError("`output_file` argument requires `input_file` or `query` argument")

    env = {}
    if query:
        env["_SQL_QUERY"] = query

    command = [
        "exec",
        "--env=_SQL_QUERY" if query else "",
        f"-- {db} sh -c '",
    ]

    if _is_compose_included(context, "mysql"):
        command += [
            "mysql",
            "--user=$MYSQL_USER",
            "--password=$MYSQL_PASSWORD",
            f"--database={db_name or '$MYSQL_DATABASE'}",
        ]
    elif _is_compose_included(context, "postgres"):
        command += [
            "psql",
            "--username=$POSTGRES_USER",
            f"--dbname={db_name or '$POSTGRES_DB'}",
        ]
    else:
        raise ValueError("Unsupported database backend.")

    command += [
        "'",
        '<<<"$_SQL_QUERY"' if query else "",
        f"< '{input_file}'" if input_file else "",
        f"> '{output_file}'" if output_file else "",
    ]

    docker_compose(context, " ".join(command), env=env, pty=not (input_file or output_file or query))


# ------------------------------------------------------------------------------
# DOCS
# ------------------------------------------------------------------------------
@task
def docs(context):
    """Build and serve docs locally for development."""
    ctx = context[CONFIGURATION_NAMESPACE]
    command = "mkdocs serve -v"

    if is_truthy(ctx.local):
        print(">>> Serving Documentation at http://localhost:8001")
        run_command(context, command)
    else:
        start(context, service="docs")


@task(help={"service": "If specified, only pull images for this service."})
def pull_images(context, service=""):
    """Pull Docker images for all services or a specific service using docker compose."""
    if service:
        service = _service_name(context, service)
        print(f"Pulling Docker image for service: {service} ...")
    else:
        print("Pulling Docker images for all services ...")
    docker_compose(context, "pull", service=service)


@task
def build_and_check_docs(context):
    """Build documentation to be available within Nautobot."""
    command = "mkdocs build --no-directory-urls --strict"
    run_command(context, command)


@task(name="help")
def help_task(context):
    """Print the help of available tasks."""
    import tasks  # pylint: disable=all

    root = Collection.from_module(tasks)
    for task_name in sorted(root.task_names):
        print(50 * "-")
        print(f"invoke {task_name} --help")
        context.run(f"invoke {task_name} --help")


@task(
    help={
        "version": "Version of Nautobot App Livedata to generate the release notes for.",
    }
)
def generate_release_notes(context, version=""):
    """Generate Release Notes using Towncrier."""
    command = "poetry run towncrier build"
    if version:
        command += f" --version {version}"
    else:
        command += " --version `poetry version -s`"
    # Due to issues with git repo ownership in the containers, this must always run locally.
    context.run(command)


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


@task
def hadolint(context):
    """Check Dockerfile for hadolint compliance and other style issues."""
    command = "hadolint development/Dockerfile"
    run_command(context, command)


@task
def pylint(context):
    """Run pylint code analysis."""
    exit_code = 0

    base_pylint_command = 'pylint --verbose --init-hook "import nautobot; nautobot.setup()" --rcfile pyproject.toml'
    command = f"{base_pylint_command} {CONFIGURATION_NAMESPACE}"
    if not run_command(context, command, warn=True):
        exit_code = 1

    # run the pylint_django migrations checkers on the migrations directory, if one exists
    migrations_dir = Path(__file__).absolute().parent / Path(CONFIGURATION_NAMESPACE) / Path("migrations")
    if migrations_dir.is_dir():
        migrations_pylint_command = (
            f"{base_pylint_command} --load-plugins=pylint_django.checkers.migrations"
            " --disable=all --enable=fatal,new-db-field-with-default,missing-backwards-migration-callable"
            f" {CONFIGURATION_NAMESPACE}.migrations"
        )
        if not run_command(context, migrations_pylint_command, warn=True):
            exit_code = 1
    else:
        print("No migrations directory found, skipping migrations checks.")

    if exit_code != 0:
        raise Exit(code=exit_code)


@task(aliases=("a",))
def autoformat(context):
    """Run code autoformatting."""
    ruff(context, action=["format"], fix=True)


@task
def yamllint(context):
    """Run yamllint to validate formatting adheres to NTC defined YAML standards.

    Args:
        context (obj): Used to run specific commands
    """
    command = "yamllint . --format standard"
    run_command(context, command)


@task
def check_migrations(context):
    """Check for missing migrations."""
    command = "nautobot-server makemigrations --dry-run --check"

    run_command(context, command)


@task(
    help={
        "keepdb": "save and re-use test database between test runs for faster re-testing.",
        "label": "specify a directory or module to test instead of running all Nautobot tests",
        "failfast": "fail as soon as a single test fails don't run the entire test suite",
        "buffer": "Discard output from passing tests",
        "pattern": "Run specific test methods, classes, or modules instead of all tests",
        "verbose": "Enable verbose test output.",
    }
)
def unittest(
    context,
    keepdb=False,
    label=None,
    failfast=False,
    buffer=True,
    pattern="",
    verbose=False,
):
    """Run Nautobot unit tests."""
    if not label:
        label = CONFIGURATION_NAMESPACE
    command = f"coverage run --module nautobot.core.cli test {label}"

    if keepdb:
        command += " --keepdb"
    if failfast:
        command += " --failfast"
    if buffer:
        command += " --buffer"
    if pattern:
        command += f" -k='{pattern}'"
    if verbose:
        command += " --verbosity 2"

    run_command(context, command)


@task
def unittest_coverage(context):
    """Report on code test coverage as measured by 'invoke unittest'."""
    command = "coverage report --skip-covered --include 'nautobot_app_liveupdate/*' --omit *migrations*"

    run_command(context, command)


@task(
    help={
        "failfast": "fail as soon as a single test fails don't run the entire test suite. (default: False)",
        "keepdb": "Save and re-use test database between test runs for faster re-testing. (default: False)",
        "lint-only": "Only run linters; unit tests will be excluded. (default: False)",
    }
)
def tests(context, failfast=False, keepdb=False, lint_only=False):
    """Run all tests for this app."""
    ctx = context[CONFIGURATION_NAMESPACE]
    # If we are not running locally, start the docker containers so we don't have to for each test
    if not is_truthy(ctx.local):
        print("Starting Docker Containers...")
        start(context)
    # Sorted loosely from fastest to slowest
    print("Running ruff...")
    ruff(context)
    print("Running yamllint...")
    yamllint(context)
    print("Running poetry check...")
    lock(context, check=True)
    print("Running migrations check...")
    check_migrations(context)
    print("Running pylint...")
    pylint(context)
    print("Running mkdocs...")
    build_and_check_docs(context)
    print("Checking app config schema...")
    validate_app_config(context)
    if not lint_only:
        print("Running unit tests...")
        unittest(context, failfast=failfast, keepdb=keepdb)
        unittest_coverage(context)
    print("All tests have passed!")


@task
def generate_app_config_schema(context):
    """Generate the app config schema from the current app config.

    WARNING: Review and edit the generated file before committing.

    Its content is inferred from:

    - The current configuration in `PLUGINS_CONFIG`
    - `NautobotAppConfig.default_settings`
    - `NautobotAppConfig.required_settings`
    """
    start(context, service="nautobot")
    nbshell(context, file="development/app_config_schema.py", env={"APP_CONFIG_SCHEMA_COMMAND": "generate"})


@task
def validate_app_config(context):
    """Validate the app config based on the app config schema."""
    start(context, service="nautobot")
    nbshell(context, plain=True, file="development/app_config_schema.py", env={"APP_CONFIG_SCHEMA_COMMAND": "validate"})
