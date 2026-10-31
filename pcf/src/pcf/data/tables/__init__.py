"""Tables at each level of detail, saved as parts with their own known_at (decision 0008).

Read a table with `load(name, at=moment)`; build them with `build()` or `pcf tables build`.
Experts don't call `load` directly: they read through the gateway (`validation-harness`).
"""

from pcf.data.schemas import TABLES
from pcf.data.tables.build import build
from pcf.data.tables.store import load, write_parts

__all__ = ["TABLES", "build", "load", "write_parts"]
