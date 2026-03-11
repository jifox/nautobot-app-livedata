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
# ruff: noqa: E501

from functools import lru_cache
import json
import os
from pathlib import Path
import re
import sys
from time import sleep

from dotenv import load_dotenv
from invoke.collection import Collection
from invoke.context import Context
from invoke.exceptions import Exit, UnexpectedExit
from invoke.tasks import Task, task as invoke_task
import jinja2
import toml
import yaml  # Added for parsing docker compose config output


def _invoke_echo_enabled(ctx) -> bool:
    """Return True if Invoke was run with -e/--echo.

    This function reads `ctx.config.run.echo` when possible, and falls back
    to `ctx.config.get("run", {}).get("echo")` for mapping-like contexts.
    """
    try:
        return bool(ctx.config.run.echo)
    except Exception:
        try:
            return bool(ctx.config.get("run", {}).get("echo", False))
        except Exception:
            return False


loaded_environment_files = []


def initialize_environment():
    """Initialize environment variables from .env files."""
    # Set the environment files to be sourced in order. The highest priority file should be listed last.
    default_env_filenames = ["dev.env", "development.env", "local.env", ".env", ".creds.env", "creds.env"]
    default_env_dirs = [
        ".",  # Current directory
        "development",  # Development directory
        "environments",  # Environments directory
    ]
    configured_env_filenames = os.getenv("ENVIRONMENT_FILENAMES", default_env_filenames)
    configured_env_dirs = os.getenv("ENVIRONMENT_DIRS", default_env_dirs)
    # Load environment variables from the specified files
    loaded_environment_files = []
    for envfile in configured_env_filenames:
        for dir in configured_env_dirs:
            if not os.path.isabs(dir):
                dir = os.path.join(os.getcwd(), dir)
            if not os.path.exists(dir):
                continue
            # If the file exists, source it
            # If the directory is not absolute, make it absolute
            dir = os.path.abspath(dir)
            fname = os.path.join(dir, envfile)
            if os.path.isfile(fname):
                load_dotenv(fname, override=True)
                loaded_environment_files.append(fname)


initialize_environment()


# This is the invoke configuration name that is used as context for the tasks. (invoke.yml)
try:
    CONFIGURATION_NAMESPACE = os.getenv("CONFIGURATION_NAMESPACE")
except TypeError:
    raise TypeError(
        "CONFIGURATION_NAMESPACE environment variable is not set. Please set "
        "it to the name of your configuration namespace."
    )

VERSION_PATTERN = re.compile(r"\d+(?:\.\d+)+")

REPOSITORY_ROOT = Path(__file__).resolve().parent


def _relative_posix_path(path: Path) -> str:
    """Return the repository-relative POSIX path string if possible."""
    try:
        return path.relative_to(REPOSITORY_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _absolute_path(path_str: str) -> Path:
    """Convert a potentially relative path string to an absolute Path."""
    path = Path(path_str)
    if not path.is_absolute():
        path = REPOSITORY_ROOT / path
    return path


@lru_cache(maxsize=1)
def _load_pyproject_data() -> dict:
    """Load pyproject.toml once for reuse across helper functions."""
    with open(REPOSITORY_ROOT / "pyproject.toml", "r", encoding="utf8") as pyproject:
        return toml.load(pyproject)


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


def compose_dir_setup():
    """Determine the compose directory based on existing paths."""
    if Path(__file__).parent.joinpath("development").exists():
        compose_dir = Path(__file__).parent.joinpath("development").resolve()
    elif Path(__file__).parent.joinpath("environments").exists():
        compose_dir = Path(__file__).parent.joinpath("environments").resolve()
    return compose_dir


# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_NAUTOBOT_xxx
if not CONFIGURATION_NAMESPACE.__contains__("_"):
    print(
        "ERROR: CONFIGURATION_NAMESPACE must contain at least one underscore "
        "(_) character to separate project name and suffix."
    )
    sys.exit(1)


# The Nautobot container name is unique on all swarm nodes
nautobot_container_name = os.getenv("NAUTOBOT_CONTAINER_NAME", "nautobot").replace("_", "-").lower()
# Derived unique Container names as default
celery_container_name = (
    os.getenv("NAUTOBOT_CELERY_CONTAINER_NAME", "celery-beat-" + nautobot_container_name).replace("_", "-").lower()
)
db_container_name = os.getenv("NAUTOBOT_DB_HOST", "db-" + nautobot_container_name).replace("_", "-").lower()
mkdocs_container_name = (
    os.getenv("NAUTOBOT_MKDOCS_CONTAINER_NAME", "mkdocs-" + nautobot_container_name).replace("_", "-").lower()
)
redis_container_name = os.getenv("NAUTOBOT_REDIS_HOST", "redis-" + nautobot_container_name).replace("_", "-").lower()
worker_container_name = (
    os.getenv("NAUTOBOT_WORKER_CONTAINER_NAME", "worker-" + nautobot_container_name).replace("_", "-").lower()
)
worker2_container_name = (
    os.getenv("NAUTOBOT_WORKER2_CONTAINER_NAME", "worker2-" + nautobot_container_name).replace("_", "-").lower()
)
backend_network_name = f"{nautobot_container_name}_net"
docker_registry = os.getenv("NAUTOBOT_DOCKER_REGISTRY", "local").replace("_", "-").lower()
python_ver = os.getenv("PYTHON_VER", "3.12")

# Defined in local.env or creds.env
project_name = str("-".join(str(CONFIGURATION_NAMESPACE).split("_")[:-1]).replace("_", "-")).lower()
project_suffix = str(CONFIGURATION_NAMESPACE).split("_")[-1]

namespace = Collection(CONFIGURATION_NAMESPACE)
namespace.configure(
    {
        CONFIGURATION_NAMESPACE: {
            "nautobot_ver": "3.0.1",  # e.g. 'pyproject' or '3.0.1'
            "project_name": project_name,
            "project_suffix": project_suffix,
            "nautobot_image_name": docker_registry + "/" + nautobot_container_name,
            "python_ver": python_ver,
            "local": False,
            "use_django_extensions": True,
            "docker_swarm_mode": False,
            "docker_registry": docker_registry,
            "compose_dir": compose_dir_setup(),
            "compose_files": [
                "docker-compose.base.yml",
                "docker-compose.redis.yml",
                "docker-compose.postgres.yml",
                "docker-compose.dev.yml",
                "docker-compose.ports.yml",
            ],
            "templates_dir": compose_dir_setup().joinpath("templates"),
            "compose_http_timeout": "86400",
            # Container names
            "celery_container_name": celery_container_name,
            "nautobot_container_name": nautobot_container_name,
            "db_container_name": db_container_name,
            "redis_container_name": redis_container_name,
            # the celery_container_name key was accidentally duplicated above; the
            # second occurrence has been removed to avoid F601 (duplicate key).
            "worker_container_name": worker_container_name,
            "worker2_container_name": worker2_container_name,
            "backend_network_name": backend_network_name,
            "mkdocs_container_name": mkdocs_container_name,
            # the docker_registry key is already defined earlier in this dict; drop
            # the duplicate occurrence here.
            # Other settings
            "render_templates": False,  # Set to True to render templates before running docker compose
            # Build options: docker build target (one of: "final", "dev", "final-dev").
            # If set to None (default), no --target flag will be passed to docker build.
            "build_target": None,
            # Settings for Traefik integration
            "traefik_enabled": False,
            "traefik_external_overlay_network": "t3_proxy",  # only used if traefik_enabled is True
            "public_service_dns": None,  # e.g. "nautobot.example.com"
        }
    }
)


def _parse_pyproject_nautobot_version():
    """Get the Nautobot version from poetry."""
    # Use poetry show nautobot to get the version installed in the current environment.
    # Create a new context and run the command in same directory as this source file
    new_context = Context()
    with new_context.cd(str(REPOSITORY_ROOT)):
        result = new_context.run("poetry show -f json nautobot", hide=True)
    new_context = None
    # extract the version from the JSON output
    nautobot_info = json.loads(result.stdout.strip())
    if not nautobot_info or "version" not in nautobot_info:
        raise Exit("Nautobot version not found in Poetry environment.")
    return nautobot_info["version"]


def _discover_package_dir(dependency_name: str, base_path: Path) -> Path:
    """Return the Python package directory for the editable dependency."""
    slug_candidate = dependency_name.replace("-", "_")
    candidate_path = base_path / slug_candidate
    if candidate_path.is_dir():
        return candidate_path

    for child in sorted(base_path.iterdir()):
        if child.is_dir() and (child / "__init__.py").is_file():
            return child

    raise Exit(f"Unable to locate a Python package directory for '{dependency_name}' under {base_path.as_posix()}.")


def _build_editable_module_metadata(dependency_name: str, dependency_spec: dict) -> dict:
    """Create metadata needed to run tests for an editable dependency."""
    dependency_path = dependency_spec.get("path")
    if not dependency_path:
        raise Exit(f"Editable dependency '{dependency_name}' is missing a path attribute in pyproject.toml.")

    base_path = _absolute_path(dependency_path)
    if not base_path.exists():
        raise Exit(f"Editable dependency '{dependency_name}' references path {dependency_path}, which does not exist.")

    package_dir = _discover_package_dir(dependency_name, base_path)
    return {
        "dependency_name": dependency_name,
        "module": package_dir.name,
        "config_path": _relative_posix_path(config_file)
        if (config_file := package_dir / "tests" / "nautobot_config.py").is_file() and config_file.stat().st_size
        else None,
        "package_path": _relative_posix_path(package_dir),
    }


@lru_cache(maxsize=1)
def _get_editable_app_modules() -> list[dict]:
    """Return metadata for all editable app modules defined in pyproject.toml."""
    parsed_toml = _load_pyproject_data()
    dependencies = parsed_toml.get("tool", {}).get("poetry", {}).get("dependencies", {})
    modules = []
    for dependency_name, dependency_spec in dependencies.items():
        if not isinstance(dependency_spec, dict):
            continue
        if "path" not in dependency_spec:
            continue
        if dependency_spec.get("develop", True) is False:
            continue
        modules.append(_build_editable_module_metadata(dependency_name, dependency_spec))

    # If there are no editable path dependencies, fall back to assuming the
    # current project itself is the editable module.  This is the case for
    # standalone Nautobot apps which do not declare a local dependency on
    # themselves in pyproject.toml.  Use the same inference logic as the
    # pylint task above to determine the package directory.
    if not modules:
        # derive module name from project metadata or packages list
        module_name = parsed_toml.get("project", {}).get("name") or parsed_toml.get("tool", {}).get("poetry", {}).get(
            "name", ""
        )
        if not module_name:
            packages_spec = parsed_toml.get("tool", {}).get("poetry", {}).get("packages", [])
            if packages_spec:
                first = packages_spec[0]
                if isinstance(first, dict):
                    module_name = first.get("include", "")
                elif isinstance(first, str):
                    module_name = first
        module_name = module_name.replace("-", "_")
        if module_name:
            # build a fake dependency spec pointing at the current repo root
            spec = {"path": "."}
            try:
                modules.append(_build_editable_module_metadata(module_name, spec))
            except Exit:
                # if even the fallback fails, we'll raise below
                pass

    if not modules:
        raise Exit("No editable modules with local paths were found in pyproject.toml.")

    fallback_config = next((module["config_path"] for module in modules if module["config_path"]), None)
    if not fallback_config:
        raise Exit("Unable to locate a Nautobot test configuration file for any editable module.")

    for module in modules:
        if not module["config_path"]:
            module["config_path"] = fallback_config
    return modules


def _filter_modules_by_name(modules: list[dict], module_name: str | None) -> list[dict]:
    """Filter editable modules by pip or Python package name."""
    if not module_name:
        return list(modules)

    normalized = module_name.replace("-", "_")
    filtered = [
        module for module in modules if module["module"] == normalized or module["dependency_name"] == module_name
    ]
    if not filtered:
        available = ", ".join(sorted(module["module"] for module in modules))
        raise Exit(f"Module '{module_name}' not found. Available editable modules: {available}")
    return filtered


def _resolve_modules_for_tests(module_name: str | None = None, label: str | None = None) -> list[dict]:
    """Determine which editable modules should have their tests executed."""
    modules = _filter_modules_by_name(_get_editable_app_modules(), module_name)
    if label:
        matched = next((module for module in modules if label.startswith(module["module"])), None)
        if matched:
            return [matched]
        return modules[:1]
    return modules


def _build_test_command(
    module_metadata: dict,
    target_label: str,
    *,
    coverage: bool,
    append: bool,
    keepdb: bool,
    failfast: bool,
    buffer: bool,
    pattern: str,
    verbose: bool,
) -> str:
    """Construct the manage.py test command for a specific module."""
    if coverage:
        append_flag = " --append" if append else ""
        command = (
            f"coverage run{append_flag} --module nautobot.core.cli "
            f"--config={module_metadata['config_path']} test {target_label}"
        )
    else:
        command = f"nautobot-server --config={module_metadata['config_path']} test {target_label}"

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
    return command


def _run_unit_tests(
    context,
    *,
    keepdb: bool,
    module: str,
    label: str,
    failfast: bool,
    buffer: bool,
    pattern: str,
    verbose: bool,
    coverage: bool,
):
    """Execute Nautobot unit tests for the requested editable modules."""
    modules_to_run = _resolve_modules_for_tests(module, label or None)
    coverage_append = False
    for module_metadata in modules_to_run:
        tests_label = label or module_metadata["module"]
        print(f"Running tests for {tests_label}...")
        command = _build_test_command(
            module_metadata,
            tests_label,
            coverage=coverage,
            append=coverage_append,
            keepdb=keepdb,
            failfast=failfast,
            buffer=buffer,
            pattern=pattern,
            verbose=verbose,
        )
        run_command(context, command)
        if coverage:
            coverage_append = True
    return modules_to_run


def _formatted_include_patterns(modules: list[dict]) -> str:
    """Return the comma-separated include patterns for coverage reporting."""
    patterns = sorted({f"{module['package_path']}/*" for module in modules})
    return ",".join(patterns)


def _run_coverage_report(context, modules: list[dict]):
    """Generate the textual coverage report for the provided modules."""
    include_patterns = _formatted_include_patterns(modules)
    command = f"coverage report --skip-covered --include '{include_patterns}' --omit *migrations*"
    run_command(context, command)


def _get_ctx(context):
    """Get the context with validated service names."""
    if not hasattr(context, "_validated_service_names"):
        # Run this code only once
        ctx = context[CONFIGURATION_NAMESPACE]
        if not getattr(ctx, "compose_dir", None):
            # if directory exists:
            # os.path.join(os.path.dirname(__file__), "environments")
            ctx.compose_dir = compose_dir_setup()
        ctx.pyproject_nautobot_ver = _parse_pyproject_nautobot_version()

        try:
            _ = ctx.nautobot_ver
        except (KeyError, AttributeError):
            # If the namespace configuration is not set, fallback to the pyproject.toml version
            ctx.nautobot_ver = ctx.get("pyproject_nautobot_ver")

        if ctx.nautobot_ver == "pyproject":
            # If the Nautobot version is set to 'pyproject', use the version from pyproject.toml
            ctx.nautobot_ver = ctx.get("pyproject_nautobot_ver")

        # Ensure the container names are set in context
        ctx.db_container_name = db_container_name
        ctx.redis_container_name = redis_container_name
        ctx.celery_container_name = celery_container_name
        ctx.worker_container_name = worker_container_name
        ctx.worker2_container_name = worker2_container_name
        ctx.backend_network_name = backend_network_name
        ctx.docker_registry = docker_registry

        # Validate container names are valid DNS labels (no underscores, only lowercase letters, digits, hyphens)
        # This avoids Docker hostname issues caused by invalid characters (e.g., underscores).
        _validate_container_name(str(ctx.nautobot_container_name), "nautobot_container_name")
        _validate_container_name(str(ctx.celery_container_name), "celery_container_name")
        _validate_container_name(str(ctx.db_container_name), "db_container_name")
        _validate_container_name(str(ctx.redis_container_name), "redis_container_name")
        _validate_container_name(str(ctx.worker_container_name), "worker_container_name")
        _validate_container_name(str(ctx.worker2_container_name), "worker2_container_name")

        # Set flag to indicate that service names have been validated
        context._validated_service_names = True

        if _invoke_echo_enabled(context):
            print("")
    return context[CONFIGURATION_NAMESPACE]


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
    ctx = _get_ctx(context)
    if nautobot_ver is None:
        nautobot_ver = ctx.nautobot_ver
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
    ctx = _get_ctx(context)
    return f"docker-compose.{name}.yml" in ctx.compose_files


def _is_service_running(context, service):
    """Check if a specific service is running in the current context."""
    results = docker_compose(context, "ps --services --filter status=running", hide="out")
    return service in results.stdout.splitlines()


def _print_context_info(context, always=False):
    """Print the Nautobot Docker Compose context information."""
    ctx = _get_ctx(context)
    if not (always or _invoke_echo_enabled(ctx)):
        return
    if not ctx:
        print("Nautobot Docker Compose context is not configured.")
        return
    print("--" * 40)
    print("Loaded environment files:")
    for fname in loaded_environment_files:
        print("    -", fname)
    print("--" * 40)
    print("Nautobot Docker Compose Environment")
    print(f"Using configuration namespace:      {CONFIGURATION_NAMESPACE}")
    print(f"Using PYPROJECT_NAUTOBOT_VERSION:   {ctx.get('pyproject_nautobot_ver', 'Not set')}")
    print(f"Using Nautobot version:             {ctx.nautobot_ver}")
    print(f"Using Python version:               {ctx.python_ver}")
    print(f"Using database container name:      {ctx.db_container_name}")
    print(f"Using redis container name:         {ctx.redis_container_name}")
    print(f"Using nautobot container name:      {ctx.nautobot_container_name}")
    print(f"Using celery container name:        {ctx.celery_container_name}")
    print("--" * 40)


def _service_name(context, service):
    """Get the service name from the context.

    Expand common short service names (e.g., 'db', 'redis', 'worker', etc.) to
    the project-specific suffixed name (e.g., 'db-<nautobot_container_name>'),
    unless the provided service already includes the suffix. Print expansion
    details only when the Invoke echo flag is enabled.
    """
    ctx = _get_ctx(context)
    # Map 'nautobot' to configured container name
    if service == "nautobot":
        return ctx.nautobot_container_name
    if service == "db":
        return ctx.db_container_name
    if service in ["celery-beat", "redis", "worker", "worker2"]:
        if context.config.run.echo:
            my_name = "-".join([service, ctx.nautobot_container_name])
            print(f"Using container name: {my_name}")
        else:
            my_name = service
        return my_name
    return service


# Helpers for validating Docker container names (must be valid DNS labels)
def _is_valid_dns_label(name: str) -> bool:
    """Return True if `name` is a valid DNS label (lowercase alphanumeric and hyphens, 1-63 chars)."""
    if not isinstance(name, str) or len(name) == 0 or len(name) > 63:
        return False
    return bool(re.match(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", name))


def _validate_container_name(name: str, varname: str) -> None:
    """Validate a single container name and raise Exit with a helpful message if invalid."""
    if not _is_valid_dns_label(name):
        raise Exit(
            "Invalid container name '{0}' for '{1}'. Container names used as hostnames must be valid DNS labels: "
            "lowercase letters, digits or hyphens only; must start and end with an alphanumeric character; max 63 chars. "
            "Please update the corresponding environment variable or configuration (e.g. replace underscores with hyphens).".format(
                name, varname
            )
        )


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


# Render docker-compose YAML from Jinja2 templates before running docker compose


def _run_vaulttool_if_present(context, should_print: bool = False) -> None:
    """Run vaulttool check-ignore and encrypt if a .vaulttool config is present in the repository root.

    Args:
        context: Invoke context used to run shell commands.
        should_print: When True, vaulttool output is displayed; otherwise it is suppressed.
    """
    if not Path(f"{REPOSITORY_ROOT}/.vaulttool.yml").is_file():
        return
    with context.cd(str(REPOSITORY_ROOT)):
        if should_print:
            print("Running vaulttool to check .vaulttool.yml configuration and encrypt secrets...")

        result = context.run("vaulttool check-ignore", hide=not should_print)
        if result.exited != 0:
            raise Exit("vaulttool check-ignore failed. Please fix the issues before proceeding.")
        result = context.run("vaulttool encrypt", hide=not should_print)
        if result.exited != 0:
            raise Exit("vaulttool encrypt failed. Please fix the issues before proceeding.")


@task(
    help={
        "always": "Always print diagnostic output, even if echo is not enabled",
    }
)
def render_compose_templates(context, always=False):
    """Render all docker-compose .j2 templates in templates_dir to COMPOSE_ENV_DIR/ as .yml files.

    The function attempts to populate the Jinja2 template variables dictionary from the
    configuration context (mapping-style when possible, otherwise by safe attribute
    introspection). It prints diagnostic output only once per process unless `always`
    is True or the Invoke echo flag is enabled.
    """
    ctx = _get_ctx(context)

    current_dir = Path(__file__).parent.resolve()
    compose_dir = Path(ctx.compose_dir).resolve().relative_to(current_dir)
    templates_dir = compose_dir.joinpath("templates")
    if not os.path.exists(compose_dir):
        raise ValueError(f"COMPOSE_ENV_DIR '{compose_dir}' does not exist or is not a directory.")
    if not os.path.isdir(templates_dir):
        raise ValueError(f"templates_dir '{templates_dir}' is not a directory.")
    if _is_compose_included(context, "ldap"):
        dockerfile = f"{ctx.compose_dir}/Dockerfile-LDAP"
    else:
        dockerfile = f"{ctx.compose_dir}/Dockerfile"

    # ruff: noqa: S701
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(templates_dir),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    variables = {
        "compose_dir": compose_dir,
        "dockerfile": dockerfile,
        "templates_dir": templates_dir,
    }

    # Prefer mapping-style extraction from ctx when available
    try:
        if hasattr(ctx, "items"):
            for key, value in ctx.items():
                if not str(key).startswith("_"):
                    variables[str(key)] = value
        else:
            # Fallback to dictionary coercion where possible
            for key, value in dict(ctx).items():
                if not str(key).startswith("_"):
                    variables[str(key)] = value
    except Exception:
        # Best-effort attribute introspection: skip callables and private attributes
        for key in dir(ctx):
            if key.startswith("_"):
                continue
            try:
                value = getattr(ctx, key)
            except Exception as exc:
                # skip attributes that cannot be accessed; log a warning so that
                # we don't silently swallow unexpected failures (ruff:S112)
                print(f"warning: unable to inspect ctx.{key}: {exc}")
                continue
            if callable(value):
                continue
            variables[key] = value

    # Ensure important defaults exist so templates render even if ctx is missing them
    variables.setdefault("project_name", project_name)
    variables.setdefault("project_suffix", project_suffix)
    variables.setdefault(
        "nautobot_image_name", getattr(ctx, "nautobot_image_name", docker_registry + "/" + nautobot_container_name)
    )
    variables.setdefault("nautobot_container_name", getattr(ctx, "nautobot_container_name", nautobot_container_name))
    variables.setdefault("python_ver", getattr(ctx, "python_ver", python_ver))
    variables.setdefault("nautobot_ver", getattr(ctx, "nautobot_ver", None))
    variables.setdefault("docker_registry", getattr(ctx, "docker_registry", docker_registry))
    variables.setdefault("mkdocs_container_name", getattr(ctx, "mkdocs_container_name", mkdocs_container_name))
    variables.setdefault("redis_container_name", getattr(ctx, "redis_container_name", redis_container_name))
    variables.setdefault("db_container_name", getattr(ctx, "db_container_name", db_container_name))
    variables.setdefault("celery_container_name", getattr(ctx, "celery_container_name", celery_container_name))
    variables.setdefault("worker_container_name", getattr(ctx, "worker_container_name", worker_container_name))
    variables.setdefault("worker2_container_name", getattr(ctx, "worker2_container_name", worker2_container_name))
    variables.setdefault("backend_network_name", getattr(ctx, "backend_network_name", backend_network_name))
    variables.setdefault("compose_files", getattr(ctx, "compose_files", []))
    variables.setdefault("traefik_enabled", getattr(ctx, "traefik_enabled", False))
    variables.setdefault(
        "traefik_external_overlay_network", getattr(ctx, "traefik_external_overlay_network", "t3_proxy")
    )
    # Build target may be specified in invoke.yml as `build_target` (e.g. 'dev', 'final').
    # If unset, templates should omit any `target` field.
    variables.setdefault("build_target", getattr(ctx, "build_target", None))

    # Determine whether we should print variable/debug output.
    # Print when `always` is requested or when the Invoke echo flag is enabled.
    should_print = bool(always) or _invoke_echo_enabled(ctx)
    if should_print or context.config.run.echo:
        print("Rendering docker-compose templates with:")
        print("  Variables:")
        for key, value in sorted(variables.items()):
            print(f"     {key.ljust(28)}: {value}")
        print("  Rendered Compose Files:")

    for fname in templates_dir.iterdir():
        if not fname.name.endswith(".j2"):
            continue
        template_name = fname.name
        if template_name.startswith("docker-compose._"):
            # Skip internal templates that start with an underscore
            continue
        # Check if fname starts with 'docker-compose.' and only render if it is in ctx compose files
        if template_name.startswith("docker-compose.") and template_name[:-3] not in ctx.compose_files:
            continue
        template = jinja_env.get_template(template_name)
        rendered = template.render(**variables)
        outname = template_name[:-3]  # remove .j2
        outpath = compose_dir.joinpath(outname)
        if should_print or context.config.run.echo:
            print(f"    - {outpath}")
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(rendered)

    # Mark that we've printed once (if we actually printed)
    if should_print:
        setattr(render_compose_templates, "_printed_once", True)

    _run_vaulttool_if_present(context, should_print=should_print)


def docker_compose(context, command, **kwargs):
    """Helper function for running a specific docker compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """
    ctx = _get_ctx(context)
    if ctx.render_templates:
        render_compose_templates(context)

    compose_env = {
        "NAUTOBOT_CONTAINER_NAME": ctx.nautobot_container_name,
        # Note: 'docker compose logs' will stop following after 60 seconds by default,
        # so we are overriding that by setting this environment variable.
        "COMPOSE_HTTP_TIMEOUT": ctx.compose_http_timeout,
        "NAUTOBOT_VER": ctx.nautobot_ver,
        "NAUTOBOT_VERSION": ctx.nautobot_ver,
        "PYTHON_VER": ctx.python_ver,
        **kwargs.pop("env", {}),
    }
    if ctx.project_suffix and ctx.project_suffix != "":
        project_name = f"{ctx.project_name}-{ctx.project_suffix}"
    else:
        project_name = ctx.project_name
    compose_command_tokens = [
        "docker compose",
        f"--project-name {project_name}",
        f'--project-directory "{ctx.compose_dir}/"',
    ]
    for compose_file in ctx.compose_files:
        compose_file_path = f"{str(ctx.compose_dir).split('/')[-1]}/{compose_file}"
        compose_command_tokens.append(f' -f "{compose_file_path}"')

    compose_command_tokens.append(command)

    # If `service` was passed as a kwarg, add it to the end.
    service = kwargs.pop("service", None)
    if service is not None:
        compose_command_tokens.append(service)

    silent = kwargs.pop("silent", False)
    if not silent:
        if context.config.run.echo:
            print(f"Running docker compose command '{command}'")
    compose_command = " ".join(compose_command_tokens)

    return context.run(compose_command, env=compose_env, **kwargs)


def run_command(context, command, service="nautobot", **kwargs):
    """Wrapper to run a command locally or inside the nautobot container."""
    ctx = _get_ctx(context)
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
    ctx = _get_ctx(context)
    # Pull all git repositories in the plugins directory (but not the main repo)
    # Update the submodules to ensure all plugins are up-to-date
    if not ctx.local:
        if _invoke_echo_enabled(context):
            print("Pulling latest changes from git submodules...")
        context.run("git submodule update --remote --merge", pty=False, echo=False, hide=True)
    else:
        if _invoke_echo_enabled(context):
            print("Updating git submodules...")

    command = "build"

    if not cache:
        command += " --no-cache"
    if force_rm:
        command += " --force-rm"

    if _invoke_echo_enabled(context):
        print(f"Building Nautobot with Python {ctx.python_ver}...")

    _run_vaulttool_if_present(context, should_print=_invoke_echo_enabled(context))
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
    ctx = _get_ctx(context)
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
            command = f"poetry add --lock git+https://github.com/nautobot/nautobot.git#{ctx.nautobot_ver}"
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
    env = {
        "NAUTOBOT_DEBUG": "True",
    }
    docker_compose(context, "up", service=service, env=env)


def _print_compose_info_if_requested(context):
    """Render and print compose templates and info if invoked."""
    try:
        render_compose_templates(context)
    except Exception as exc:
        print(f"Warning: failed to render/print compose templates: {exc}")


@task(help={"service": "If specified, only affect this service."})
def start(context, service=""):
    """Start specified or all services and its dependencies in detached mode."""
    # If invoked with `-e/--echo`, optionally render/print compose templates and details.
    _print_compose_info_if_requested(context)
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
    ctx = _get_ctx(context)
    if confirm:
        print("Container Name: ", ctx.nautobot_container_name)
        print("WARNING: This operation will delete ALL containers, networks and volumes. This action is irreversible!")
        response = input("Are you sure you want to continue? Type 'yes' to proceed: ")
        if response.strip().lower() != "yes":
            print("Aborted by user.")
            return
    print("Destroying Nautobot (removing volumes and orphans)...")
    # always remove volumes and orphaned containers to prevent stale state/port conflicts
    docker_compose(context, "down --remove-orphans --volumes")

    # preserve the import-db-file functionality in case it's still needed
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
    # print("Generating Docker Compose configuration...")
    docker_compose(context, "config", service=service, silent=True)


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
    ctx = _get_ctx(context)
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
    command = "nautobot-server makemigrations "

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


@task(
    help={
        "target": "File or directory to inspect, repeatable (default: all files in the project will be inspected)",
    },
    iterable=["target"],
)
def djlint(context, target=None):
    """Run djlint to lint Django templates."""
    if not target:
        target = ["."]

    command = "djlint --lint "
    command += " ".join(target)

    exit_code = 0 if run_command(context, command, warn=True) else 1
    if exit_code != 0:
        raise Exit(code=exit_code)


@task(
    help={
        "check": "Run djhtml in check mode.",
        "directories": "Comma separated list of directories containing templates to format.",
    },
)
def djhtml(context, check=False, directories=None):
    """Run djhtml to format Django HTML templates."""
    if directories is None:
        return
    directories = [d.strip() for d in directories.split(",")]
    for dir in directories:
        templ_dir = Path(dir).joinpath("templates").resolve()
        if not templ_dir.exists():
            raise ValueError(f"Directory not found: {templ_dir}")
    command = f"djhtml -t 4 {templ_dir}"

    if check:
        command += " --check"

    exit_code = 0 if run_command(context, command, warn=True) else 1
    if exit_code != 0:
        raise Exit(code=exit_code)


@task
def markdownlint(context, fix=False):
    """Lint Markdown files."""
    if fix:
        command = "pymarkdown fix --recurse docs *.md"
        run_command(context, command)
    command = "pymarkdown scan --recurse docs *.md"
    run_command(context, command)


@task(aliases=("a",))
def autoformat(context):
    """Run code autoformatting."""
    ruff(context, action=["format"], fix=True)
    djhtml(context)


@task
def import_nautobot_data(context):
    """Import nautobot_data.json."""
    # This task expects to be run in the docker container for now
    ctx = _get_ctx(context)
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


@task(
    help={
        "always": "Always print diagnostic output, even if echo is not enabled",
    }
)
def render_compose(context, always=False):
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
    ctx = _get_ctx(context)
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
    ctx = _get_ctx(context)
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
    ctx = _get_ctx(context)
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
def import_db(context, db_name="", input_file="dump.sql"):
    """Alias for `restore_db` task."""
    restore_db(context, db_name=db_name, input_file=input_file)


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
    ctx = _get_ctx(context)
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
    ctx = _get_ctx(context)
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
    ctx = _get_ctx(context)
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
        "version": "Version of Live Update to generate the release notes for.",
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
    # Determine the module name from poetry metadata so we don't hardcode it.
    pyproject = _load_pyproject_data()
    # after migration the package name may live under [project] rather than
    # [tool.poetry]; look in both places.  older poetry projects also used a
    # separate `packages` table to declare the Python package(s) that should be
    # included in the distribution.  In minimal pyproject.toml files the
    # metadata name may not be present or may not match the actual package
    # directory, so look there as a fallback.
    module_name = pyproject.get("project", {}).get("name") or pyproject.get("tool", {}).get("poetry", {}).get(
        "name", ""
    )
    if not module_name:
        # try to infer the package name from the [tool.poetry.packages] list
        packages_spec = pyproject.get("tool", {}).get("poetry", {}).get("packages", [])
        if packages_spec:
            first = packages_spec[0]
            if isinstance(first, dict):
                module_name = first.get("include", "")
            elif isinstance(first, str):
                module_name = first
    module_name = module_name.replace("-", "_")

    exit_code = 0

    base_pylint_command = 'pylint --verbose --init-hook "import nautobot; nautobot.setup()" --rcfile pyproject.toml'
    command = f"{base_pylint_command} {module_name}"
    if not run_command(context, command, warn=True):
        exit_code = 1

    # run the pylint_django migrations checkers on the migrations directory, if one exists
    migrations_dir = Path(__file__).absolute().parent / Path(module_name) / Path("migrations")
    if migrations_dir.is_dir():
        migrations_pylint_command = (
            f"{base_pylint_command} --load-plugins=pylint_django.checkers.migrations"
            " --disable=all --enable=fatal,new-db-field-with-default,missing-backwards-migration-callable"
            f" {module_name}.migrations"
        )
        if not run_command(context, migrations_pylint_command, warn=True):
            exit_code = 1
    else:
        print("No migrations directory found, skipping migrations checks.")

    if exit_code != 0:
        raise Exit(code=exit_code)


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
        "module": "Limit execution to a specific editable module (pip name or Python package).",
        "label": "Specify a Django test label to run (defaults to the module name).",
        "failfast": "fail as soon as a single test fails don't run the entire test suite",
        "buffer": "Discard output from passing tests",
        "pattern": "Run specific test methods, classes, or modules instead of all tests",
        "verbose": "Enable verbose test output.",
        "coverage": "Enable coverage reporting. Defaults to False",
        "skip_docs_build": "Skip building the documentation before running tests.",
    }
)
def unittest(
    context,
    keepdb=False,
    module="",
    label="",
    failfast=False,
    buffer=True,
    pattern="",
    verbose=False,
    coverage=False,
    skip_docs_build=False,
):
    """Run Nautobot unit tests for one or more editable modules."""
    if not skip_docs_build:
        build_and_check_docs(context)
    return _run_unit_tests(
        context,
        keepdb=keepdb,
        module=module,
        label=label,
        failfast=failfast,
        buffer=buffer,
        pattern=pattern,
        verbose=verbose,
        coverage=coverage,
    )


@task(
    help={
        "module": "Limit coverage reporting to a specific editable module (pip name or Python package).",
    }
)
def unittest_coverage(context, module=""):
    """Report on code test coverage as measured by 'invoke unittest'."""
    modules = _resolve_modules_for_tests(module)
    _run_coverage_report(context, modules)


@task
def coverage_lcov(context):
    """Generate an LCOV coverage report."""
    command = "coverage lcov -o lcov.info"

    run_command(context, command)


@task
def coverage_xml(context):
    """Generate an XML coverage report."""
    command = "coverage xml -o coverage.xml"

    run_command(context, command)


@task(
    help={
        "failfast": "fail as soon as a single test fails don't run the entire test suite. (default: False)",
        "keepdb": "Save and re-use test database between test runs for faster re-testing. (default: False)",
        "lint-only": "Only run linters; unit tests will be excluded. (default: False)",
        "module": "Limit execution to a specific editable module (pip name or Python package).",
    }
)
def tests(context, failfast=False, keepdb=False, lint_only=False, module=""):
    """Run all tests for this app."""
    ctx = _get_ctx(context)
    # If we are not running locally, start the docker containers so we don't have to for each test
    if not is_truthy(ctx.local):
        print("Starting Docker Containers...")
        start(context)
    # Sorted loosely from fastest to slowest
    print("Running ruff...")
    ruff(context)
    print("Running djlint...")
    djlint(context)
    print("Running djhtml...")
    djhtml(context)
    print("Running yamllint...")
    yamllint(context)
    print("Running markdownlint...")
    markdownlint(context)
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
        executed_modules = unittest(
            context,
            failfast=failfast,
            keepdb=keepdb,
            coverage=True,
            skip_docs_build=True,
            module=module,
        )
        _run_coverage_report(context, executed_modules)
        coverage_lcov(context)
        coverage_xml(context)
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
