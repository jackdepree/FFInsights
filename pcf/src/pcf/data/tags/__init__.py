"""Tag tables: football's shared vocabulary as labels on plays, drives, games and players.

The catalog (`catalog.py`) defines each tag once; `build.py` computes them from the built tables
and saves them as table parts (`play.tags`, `drive`, `team_game.tags`, `player_game.tags`), so
`tables.load` returns them like any column. `docs/TAGS.md` is generated from the catalog.
"""

from pcf.data.tags.build import build_tags
from pcf.data.tags.catalog import BEFORE, REFERENCES, TAGS, Reference, Tag, tags_for

__all__ = ["BEFORE", "REFERENCES", "TAGS", "Reference", "Tag", "build_tags", "tags_for"]
