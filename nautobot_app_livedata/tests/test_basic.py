"""Basic tests that do not require Django."""

import os
import unittest

import toml


class TestDocsPackaging(unittest.TestCase):
    """Validate that docs dependency versions remain consistent."""

    def test_version(self):
        """Ensure pyproject docs dependencies match docs/requirements.txt constraints."""
        parent_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        poetry_path = os.path.join(parent_path, "pyproject.toml")
        docs_requirements_path = os.path.join(parent_path, "docs", "requirements.txt")

        poetry_details = self._load_pyproject_docs_dependencies(poetry_path)
        requirements = self._load_requirements(docs_requirements_path)

        for package_name, requirement_spec in requirements.items():
            self.assertIn(package_name, poetry_details)
            expected_version = self._normalize_version_string(poetry_details[package_name])
            actual_version = self._normalize_version_string(requirement_spec)
            self.assertEqual(expected_version, actual_version)

    @staticmethod
    def _load_pyproject_docs_dependencies(pyproject_path):
        """Return a mapping of docs dependency specs regardless of pyproject layout."""
        pyproject_details = toml.load(pyproject_path)
        docs_block = (
            pyproject_details.get("tool", {}).get("poetry", {}).get("group", {}).get("docs", {}).get("dependencies")
        )
        if docs_block is None:
            docs_block = pyproject_details.get("project", {}).get("optional-dependencies", {}).get("docs")
        if docs_block is None:
            raise AssertionError("Docs dependencies not defined in pyproject.toml.")
        if isinstance(docs_block, dict):
            return {package: TestDocsPackaging._normalize_spec(value) for package, value in docs_block.items()}
        normalized = {}
        for entry in docs_block:
            package, spec = TestDocsPackaging._split_dependency_entry(entry)
            normalized[package] = spec
        return normalized

    @staticmethod
    def _load_requirements(requirements_path):
        """Load docs/requirements.txt into a package->spec mapping."""
        with open(requirements_path, "r", encoding="utf-8") as file:
            requirements = [line for line in file.read().splitlines() if line and not line.startswith("#")]
        normalized = {}
        for entry in requirements:
            package, spec = TestDocsPackaging._split_dependency_entry(entry)
            normalized[package] = spec
        return normalized

    @staticmethod
    def _normalize_spec(value):
        """Normalize dependency specs declared in dict form."""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value.get("version", "*")
        return "*"

    @staticmethod
    def _split_dependency_entry(entry):
        """Split a dependency string into package name and version spec."""
        normalized = entry.strip().strip('"').strip("'")
        normalized = normalized.split(";", maxsplit=1)[0]
        operators = ("==", ">=", "<=", "~=", "!=", ">", "<")
        for operator in operators:
            if operator in normalized:
                package, constraint = normalized.split(operator, 1)
                return package.strip(), f"{operator}{constraint.strip()}"
        return normalized.strip(), "*"

    @staticmethod
    def _normalize_version_string(spec):
        """Return comparable numeric content from a version spec string."""
        return "".join(ch for ch in spec if ch.isdigit() or ch == ".")


if __name__ == "__main__":
    unittest.main()
