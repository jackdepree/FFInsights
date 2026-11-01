"""Write `docs/TAGS.md` from the catalog: `python -m pcf.data.tags.page`.

A test fails when the page and the catalog disagree, so the page is never edited by hand.
"""

from pcf.config import PCF_DIR
from pcf.data.tags.catalog import BEFORE, LEVELS, REFERENCES, TAGS, Tag, tags_for
from pcf.data.tags.check import band_text

PAGE = PCF_DIR / "docs" / "TAGS.md"
TIMING_WORDS = {
    "before_snap": "before the snap",
    "before_game": "before the game",
    "after_play": "after the play",
    "after_drive": "after the drive",
    "after_game": "after the game",
    "after_season": "after the season",
}
HEADER = """# Tags

> Generated from `src/pcf/data/tags/catalog.py` by `python -m pcf.data.tags.page`. Don't edit by
> hand: change the catalog (a changed rule is a new version) and regenerate.

Tags are football's shared vocabulary as yes/no (or category) labels: half statistics
(successful, explosive), half what fans, commentators and analysts point out (hero ball, answer
drive, trap game). They give every project the same definitions, and many ways to build features
and stratify models. Glossary: *tag*, *tag family*, *football timing*, *reference tag*.

**How to use them**
- They're table parts: `load("play", parts=["tags"])`, `load("drive")`,
  `load("team_game", parts=["tags", "tags_result"])`, `load("player_game", parts=["tags",
  "tags_result"])`. Each column is `tag_<name>` (`tag_<name>_v2` for a second version).
- **Empty means the tag doesn't apply** (a run has no `low_percentage_throw`) or its data doesn't
  cover that season. It never means "no".
- **Football timing decides how a tag may be used.** Only tags known *before the snap* or *before
  the game* may describe the row a model predicts (stratifying plays by red zone is fine;
  by successful, it leaks the answer). Tags known *after* describe earlier rows only, such as a
  player's share of explosive plays in past games.
- **Data timing** is the part's `known_at`: the latest of the parts each tag reads.
- **Band:** the share of applicable rows the tag fires on in a complete season. The build's checks
  fail when a season falls outside it (rule h).
"""


def _years(tag: Tag) -> str:
    return f"{tag.first_season}→"


def _rule(tag: Tag) -> str:
    if tag.values is None:
        return tag.rule_text
    return f"{tag.rule_text} (values: {', '.join(tag.values)})"


def _table(tags: list[Tag]) -> list[str]:
    lines = [
        "| Tag | Family | Timing | Meaning | Rule | Years | Band |",
        "|---|---|---|---|---|---|---|",
    ]
    for t in tags:
        timing = TIMING_WORDS[t.timing]
        if t.timing in BEFORE:
            timing = f"**{timing}**"
        lines.append(
            f"| `{t.column}` | {t.family} | {timing} | {t.meaning} | {_rule(t)} | {_years(t)} "
            f"| {band_text(t)} |"
        )
    return lines


def render() -> str:
    lines = [HEADER]
    for level in LEVELS:
        tags = tags_for(level)
        parts = sorted({t.part for t in tags})
        lines += [f"## {level.replace('_', '-')} tags ({len(tags)})", ""]
        lines.append(f"Parts: {', '.join(f'`{level}.{p}`' for p in parts)}.")
        lines += ["", *_table(tags), ""]
    lines += [
        f"## Reference tags ({len(REFERENCES)})",
        "",
        "Columns nflverse already has, listed here so they're found, not copied.",
        "",
        "| Name | Column | Meaning | Years |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {r.name} | `{r.table}.{r.part}`: `{r.column}` | {r.meaning} | {r.years} |"
        for r in REFERENCES
    ]
    counts = {f: sum(t.family == f for t in TAGS) for f in ("measured", "situation", "lore")}
    lines += [
        "",
        f"{len(TAGS)} tags: {counts['measured']} measured, {counts['situation']} situation, "
        f"{counts['lore']} lore; {len(REFERENCES)} references.",
        "",
    ]
    return "\n".join(lines)


def write() -> None:
    PAGE.write_text(render(), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    write()
