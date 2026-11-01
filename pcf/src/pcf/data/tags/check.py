"""Football sanity for tags (rule h): each tag's rate per season, against its expected band."""

from pathlib import Path

import polars as pl

from pcf.data.tables.store import load
from pcf.data.tags.catalog import Tag, tags_for

c = pl.col
TABLE = {"play": "play", "drive": "drive", "team_game": "team_game", "player_game": "player_game"}


def rates(level: str, root: Path | None = None) -> pl.DataFrame:
    """tag, season, rows (where the tag applies) and share (of those rows where it's true).

    Category tags give one row per value, as `<tag>=<value>`.
    """
    tags = tags_for(level)
    parts = sorted({t.part for t in tags})
    df = load(TABLE[level], parts=parts, root=root)
    out = []
    for tag in tags:
        col = c(tag.column)
        if tag.values is None:
            out.append(
                df.group_by("season").agg(
                    tag=pl.lit(tag.name),
                    rows=col.is_not_null().sum(),
                    share=col.cast(pl.Float64).mean(),
                )
            )
        else:
            for value in tag.values:
                out.append(
                    df.group_by("season").agg(
                        tag=pl.lit(f"{tag.name}={value}"),
                        rows=col.is_not_null().sum(),
                        share=(col == value).cast(pl.Float64).mean(),
                    )
                )
    return (
        pl.concat(out)
        .select("tag", "season", "rows", "share")
        .filter(c("rows") > 0)
        .sort("tag", "season")
    )


def complete_seasons(root: Path | None = None) -> list[int]:
    """Seasons whose every game has a result. A season in progress isn't held to the bands: its
    early weeks aren't a season's mix (no cold games in September)."""
    games = load("game", parts=["result"], root=root)
    done = games.group_by("season").agg(c("result_known_at").is_not_null().all().alias("done"))
    return sorted(done.filter("done")["season"].to_list())


def out_of_band(level: str, root: Path | None = None) -> pl.DataFrame:
    """Complete seasons where a yes/no tag's share falls outside its band (empty when all is
    well)."""
    bands = pl.DataFrame(
        [(t.name, *t.band) for t in tags_for(level) if t.band is not None],
        schema=["tag", "low", "high"],
        orient="row",
    )
    return (
        rates(level, root)
        .filter(c("season").is_in(complete_seasons(root)))
        .join(bands, on="tag")
        .filter((c("share") < c("low")) | (c("share") > c("high")))
    )


def band_text(tag: Tag) -> str:
    return "—" if tag.band is None else f"{tag.band[0]:.1%}–{tag.band[1]:.1%}"
