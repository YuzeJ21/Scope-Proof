"""The distribution contract must not admit combinations already known to be unsupported."""

import tomllib
from importlib.metadata import requires
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


@pytest.mark.parametrize("boundary", ["source", "lock", "installed"])
@pytest.mark.parametrize(
    ("name", "version", "admitted"),
    [
        ("httpx", "0.26.0", False),
        ("httpx", "0.27.0", True),
        ("httpx", "1.0.0", False),
        ("pydantic", "2.8.0", False),
        ("pydantic", "2.13.4", True),
        ("pydantic", "3.0.0", False),
        ("streamlit", "1.53.0", False),
        ("streamlit", "1.66.1", True),
        ("streamlit", "2.0.0", False),
        ("pillow", "12.3.0", False),
        ("pillow", "13.0.0", True),
        ("pillow", "14.0.0", False),
    ],
)
def test_runtime_requirement_admission(
    boundary: str, name: str, version: str, admitted: bool
) -> None:
    if boundary == "source":
        declarations = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]["dependencies"]
    elif boundary == "lock":
        packages = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))["package"]
        project = next(package for package in packages if package["name"] == "scopeproof")
        declarations = [
            item["name"] + item.get("specifier", "")
            for item in project["metadata"]["requires-dist"]
            if not item.get("marker")
        ]
    else:
        declarations = requires("scopeproof") or []

    requirements = {
        canonicalize_name(requirement.name): requirement
        for declaration in declarations
        if (requirement := Requirement(declaration)).marker is None
    }
    assert name in requirements, f"{boundary} must explicitly constrain {name}"
    assert requirements[name].specifier.contains(version) is admitted
