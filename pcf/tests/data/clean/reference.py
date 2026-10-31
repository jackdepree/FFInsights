"""The old cleaning functions, read straight from the notebook in old/ (read only) at test time.

Golden tests compare `pcf.data.clean.legacy` with these. Reading the notebook, rather than keeping
a second copy, means the reference can't drift from what the old models actually ran.
"""

import ast
import json
from functools import cache

import numpy as np
import pandas as pd
import pytest

from pcf.config import PCF_DIR

OLD_NOTEBOOK = PCF_DIR.parent / "old" / "code" / "Fatigue_Model_Prod.ipynb"
NAMES = (
    "pivot_wide_both_sides",
    "clean_depth_charts",
    "pivot_long_both_sides",
    "get_position_groups",
)


@cache
def reference() -> dict:
    """Compile only the four functions from the notebook's code cells; run nothing else."""
    if not OLD_NOTEBOOK.exists():
        pytest.skip(f"{OLD_NOTEBOOK} is not here")
    namespace: dict = {"pd": pd, "np": np}
    for cell in json.loads(OLD_NOTEBOOK.read_text(encoding="utf-8"))["cells"]:
        if cell["cell_type"] != "code":
            continue
        try:
            tree = ast.parse("".join(cell["source"]))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in NAMES:
                code = compile(ast.Module([node], []), str(OLD_NOTEBOOK), "exec")
                exec(code, namespace)  # noqa: S102 - the CEO's own old code, read only
    missing = set(NAMES) - set(namespace)
    if missing:
        raise RuntimeError(f"not found in {OLD_NOTEBOOK.name}: {sorted(missing)}")
    return {name: namespace[name] for name in NAMES}
