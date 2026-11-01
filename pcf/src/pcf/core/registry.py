"""Read `projects/registry.yaml`: every project's id, status, cadence and dependencies.

A small reader for now. `registry-tooling` adds the checks (no missing ids, no cycles) and the
impact map.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from pcf import config


def projects(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Every project in the registry, by id."""
    text = (path or config.REGISTRY_FILE).read_text(encoding="utf-8")
    return {p["id"]: p for p in yaml.safe_load(text)["projects"]}


def project(project_id: str, path: Path | None = None) -> dict[str, Any]:
    """One project's entry. Raises KeyError naming the registry when the id isn't there."""
    entries = projects(path)
    if project_id not in entries:
        raise KeyError(f"no project {project_id!r} in {path or config.REGISTRY_FILE}")
    return entries[project_id]
