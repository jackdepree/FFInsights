"""The package matches docs/ARCHITECTURE.md, and contains no hardcoded paths (rule f)."""

import importlib
import json
import re
from pathlib import Path

import pytest

import pcf
from pcf.config import PCF_DIR

SRC = Path(pcf.__file__).parent

LAYERS = ["core", "data", "experts", "composites", "products", "validation"]
SUBPACKAGES = LAYERS + ["data.sources", "data.clean", "data.tables", "data.tags"]


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackages_import(name):
    importlib.import_module(f"pcf.{name}")


@pytest.mark.parametrize("layer", LAYERS)
def test_each_layer_has_a_claude_md(layer):
    assert (SRC / layer / "CLAUDE.md").is_file()


def test_no_hardcoded_user_paths():
    pattern = re.compile(r"[A-Za-z]:\\\\?Users|/Users/|/home/")
    offenders = [
        str(p.relative_to(SRC))
        for p in SRC.rglob("*.py")
        if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_old_folder_is_denied_to_claude_edits():
    # Rule a. `Edit(path)` covers Edit, Write and NotebookEdit; a leading / is the repo root.
    settings = json.loads((PCF_DIR.parent / ".claude" / "settings.json").read_text("utf-8"))
    assert "Edit(/old/**)" in settings["permissions"]["deny"]
