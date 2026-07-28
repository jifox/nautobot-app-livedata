#!/usr/bin/env python3
"""Compare local Poetry dependencies against Nautobot upstream pins.

Run with:
    poetry run python .github/agents/compare_upstream_dependencies.py
    poetry run python .github/agents/compare_upstream_dependencies.py boto3 requests
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from urllib.request import urlopen

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_PYPROJECT = REPO_ROOT / "pyproject.toml"
UPSTREAM_URL = "https://raw.githubusercontent.com/nautobot/nautobot/refs/heads/develop/pyproject.toml"


def gather_dependency_specs(pyproject_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Collect dependency specs from Poetry main and group sections."""
    collected: dict[str, dict[str, Any]] = {}
    poetry = pyproject_data.get("tool", {}).get("poetry", {})

    for section_name in ("dependencies",):
        deps = poetry.get(section_name, {})
        for name, spec in deps.items():
            if isinstance(spec, str):
                collected[name] = {"spec": spec, "section": "main"}
            elif isinstance(spec, dict):
                collected[name] = {"spec": spec.get("version") or "", "section": "main"}

    for group_name, group in poetry.get("group", {}).items():
        deps = group.get("dependencies", {})
        for name, spec in deps.items():
            if isinstance(spec, str):
                collected[name] = {"spec": spec, "section": group_name}
            elif isinstance(spec, dict):
                collected[name] = {"spec": spec.get("version") or "", "section": group_name}

    return collected


def is_simple_pypi_spec(spec: str | None) -> bool:
    """Return True when the spec is a plain version constraint rather than a VCS/path reference."""
    if not spec:
        return False
    lowered = spec.lower()
    if any(marker in lowered for marker in ("git+", "git =", "git:", "path", "file:", "://")):
        return False
    return True


def load_pyproject(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_upstream_pyproject(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=30) as response:  # noqa: S310
        return tomllib.loads(response.read().decode("utf-8"))


def main() -> int:
    requested_modules = [arg.strip() for arg in sys.argv[1:] if arg.strip()]

    local_data = load_pyproject(LOCAL_PYPROJECT)
    upstream_data = load_upstream_pyproject(UPSTREAM_URL)

    local_specs = gather_dependency_specs(local_data)
    upstream_specs = gather_dependency_specs(upstream_data)

    if requested_modules:
        names_to_check = requested_modules
    else:
        names_to_check = sorted(set(local_specs) & set(upstream_specs))

    mismatches: list[tuple[str, str, str]] = []
    skipped: list[tuple[str, str]] = []

    for name in names_to_check:
        local_spec = local_specs.get(name, {}).get("spec", "")
        upstream_spec = upstream_specs.get(name, {}).get("spec", "")

        if name not in local_specs:
            skipped.append((name, "not present in local pyproject.toml"))
            continue
        if name not in upstream_specs:
            skipped.append((name, "not present in upstream Nautobot pyproject.toml"))
            continue
        if not is_simple_pypi_spec(local_spec) or not is_simple_pypi_spec(upstream_spec):
            skipped.append((name, "non-PyPI or non-simple spec"))
            continue
        if local_spec != upstream_spec:
            mismatches.append((name, local_spec, upstream_spec))

    if mismatches:
        print("Mismatched PyPI dependency pins:")
        for name, local_spec, upstream_spec in mismatches:
            print(f"- {name}: local={local_spec!r} upstream={upstream_spec!r}")
    else:
        print("No mismatched PyPI dependency pins found.")

    if skipped:
        print("\nSkipped entries:")
        for name, reason in skipped:
            print(f"- {name}: {reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
