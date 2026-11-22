"""The blame split summed by player, and the test of its owners (the brief's goal 2 and its "split,
out of sample" test; decision 0040).

Per dropback: the pressure part (sack E1 - E0: how much the pressure, or its absence, moved the
sack chance) and the after-pressure part (sack - E1: what happened once the pressure was known).
They add up to the sack over expected (sack - E0). Summed per player-game for the passer and for
the offensive linemen on the field (participation's true list, not the in-season map: context-live
R18), with dropbacks, pressures and sacks.

The owner test uses skill-over-expected's yardstick (`pcf.validation.owners`) on the walk-forward
chances: regular season, season pairs 2017-2024, QBs with 150+ dropbacks in both seasons and
linemen with 300+. The brief's bar: the QB's after-pressure part repeats 0.2+ and QB movers keep
half (context-v2 F13, replicated out of sample).

    python -m pcf.experts.context_retro.split --tag backtest
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import polars as pl

from pcf.core.log import get_logger
from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.context_retro import plays
from pcf.validation import owners

log = get_logger(__name__)
c = pl.col
KEYS = plays.KEYS
OL = ["C", "LT", "RT", "LG", "RG", "G", "T", "OL"]  # the on-field list's line positions
FLOORS = {"passer": 150, "lineman": 300}  # dropbacks in both seasons (the fourth look's)
OWNER_INPUTS = {"player_game": ("roster",), "player_play": ("on_field",)}
# rate: (numerator, denominator); per pressured dropback, or per dropback with both chances
RATES = {
    "sacks per pressure (a sack counts)": ("sacks", "pressures"),
    "sacks per pressure over E1": ("over_e1_pressured", "pressures"),
    "sacks per dropback": ("sacks", "dropbacks"),
    "sack over E0 per dropback (the whole)": ("over_e0", "split_dropbacks"),
    "after-pressure part per dropback": ("after_part", "split_dropbacks"),
    "pressure part per dropback": ("pressure_part", "split_dropbacks"),
}
SUMS = ["dropbacks", "split_dropbacks", "pressures", "sacks", "over_e1_pressured", "over_e0",
        "after_part", "pressure_part"]  # fmt: skip


def play_parts(history: pl.DataFrame, data: pl.DataFrame) -> pl.DataFrame:
    """One row per dropback: the passer, the pressure, the sack and, where both chances exist,
    E0, E1 and the two parts; with the history's as_of and train_end (the later of the two)."""
    h = history.filter(c("quantity").is_in(["sack_e0", "sack_e1"]))
    wide = h.pivot(on="quantity", index=KEYS, values="mean")
    ends = h.group_by(KEYS).agg(c("as_of").max(), c("train_end").max(), c("run_id").first())
    d = data.select(*KEYS, "season", "season_type", "week", "posteam", "passer_id", "sack_y",
                    "pressure_y")  # fmt: skip
    d = d.join(wide, on=KEYS, how="inner").join(ends, on=KEYS, how="left")
    both = c("sack_e0").is_not_null() & c("sack_e1").is_not_null()
    return d.with_columns(
        pressure_part=pl.when(both).then(c("sack_e1") - c("sack_e0")),
        after_part=pl.when(both).then(c("sack_y") - c("sack_e1")),
        over_e0=pl.when(both).then(c("sack_y") - c("sack_e0")),
        over_e1_pressured=pl.when(both & (c("pressure_y") == 1)).then(c("sack_y") - c("sack_e1")),
        split=both,
    )


def _sum(frame: pl.DataFrame, who: str) -> pl.DataFrame:
    return frame.group_by("game_id", who, "season", "season_type", "week", "posteam").agg(
        dropbacks=pl.len(),
        split_dropbacks=c("split").sum(),
        pressures=c("pressure_y").sum(),
        sacks=c("sack_y").sum(),
        over_e1_pressured=c("over_e1_pressured").sum(),
        over_e0=c("over_e0").sum(),
        after_part=c("after_part").sum(),
        pressure_part=c("pressure_part").sum(),
        as_of=c("as_of").max(),
        train_end=c("train_end").max(),
        run_id=c("run_id").first(),
    )


def player_game(parts: pl.DataFrame, linemen: pl.DataFrame) -> pl.DataFrame:
    """Each passer's and lineman's sums per game (`role` passer or lineman). `linemen`: game_id,
    play_id, gsis_id for the offensive linemen on the field."""
    qb = _sum(parts.drop_nulls("passer_id").rename({"passer_id": "gsis_id"}), "gsis_id")
    ol = _sum(linemen.join(parts, on=KEYS, how="inner"), "gsis_id")
    out = pl.concat([qb.with_columns(role=pl.lit("passer")),
                     ol.with_columns(role=pl.lit("lineman"))])  # fmt: skip
    return (
        out.rename({"posteam": "team"})
        .with_columns(model=pl.lit("context-retro"), cadence=pl.lit("retrospective"))
        .sort("season", "week", "game_id", "role", "gsis_id")
    )


def lineman_plays(seasons: Sequence[int], gw: Gateway | None = None) -> pl.DataFrame:
    """The offensive linemen on the field per play (participation's list, retrospective)."""
    out = []
    for s in seasons:
        g = gw or Gateway(TableSource(seasons=[s]))
        of = g.view(END_OF_TIME, "retrospective", {"player_play": ("on_field",)})
        t = of.table("player_play", seasons=[s])
        out.append(t.filter((c("side") == "offense") & c("position").is_in(OL)).select(
            "game_id", c("play_id").cast(pl.Int64), "gsis_id"))  # fmt: skip
    return pl.concat(out)


def teams_table(seasons: Sequence[int]) -> pl.DataFrame:
    """The main team and position per player-season (owners.main_team), one season at a time."""
    rosters, fields = [], []
    for s in seasons:
        v = Gateway(TableSource(seasons=[s])).view(END_OF_TIME, "retrospective", OWNER_INPUTS)
        rosters.append(v.table("player_game", seasons=[s]).select("gsis_id", "season", "team",
                                                                   "position"))  # fmt: skip
        fields.append(v.table("player_play", seasons=[s]).select("gsis_id", "season", "position"))
    return owners.main_team(pl.concat(rosters), pl.concat(fields))


def owner_table(pg: pl.DataFrame, teams: pl.DataFrame, first: int = 2017, last: int = 2024,
                draws: int = owners.DRAWS) -> pl.DataFrame:  # fmt: skip
    """Every rate's repeat and share kept, for passers (QBs) and linemen, regular season."""
    reg = pg.filter((c("season_type") == "REG") & c("season").is_between(first, last))
    rows = []
    for role in ("passer", "lineman"):
        g = reg.filter(c("role") == role).rename({"gsis_id": "pid"})
        if role == "passer":
            qbs = teams.filter(c("position") == "QB").select("pid", "season")
            g = g.join(qbs, on=["pid", "season"], how="semi")
        p = owners.season_pairs(g, SUMS, "dropbacks", FLOORS[role], RATES, teams)
        for rate in RATES:
            k = owners.kept(p, rate, draws=draws)
            lo, hi = owners.kept_interval(p, rate, draws=draws)
            rows.append({"who": "QB" if role == "passer" else "OL", **k, "kept_lo90": lo,
                         "kept_hi90": hi})  # fmt: skip
    return pl.DataFrame(rows)


def report_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "projects" / "context-retro" / "build"


def run(tag: str = "backtest", seasons: Sequence[int] = range(2017, 2025),
        name: str = "split") -> dict:  # fmt: skip
    """The player-game sums for a saved backtest's history (written beside it as
    player_game.parquet) and the owner table (build/<name>.txt)."""
    from pcf.experts.context_retro.run import cache_dir

    info = json.loads((cache_dir() / tag / "run.json").read_text())
    history = pl.read_parquet(info["path"])
    data = plays.load(seasons)
    parts = play_parts(history, data)
    pg = player_game(parts, lineman_plays(seasons))
    out = Path(info["path"]).parent / "player_game.parquet"
    pg.write_parquet(out)
    teams = teams_table(range(min(seasons), max(seasons) + 1))
    table = owner_table(pg, teams, min(seasons), max(seasons))
    pl.Config.set_tbl_rows(50)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(250)
    pl.Config.set_fmt_str_lengths(45)
    shown = table.select("who", "measure", "pairs", "movers", "repeat", "lo90", "hi90", "stayers",
                         "movers_r", "share_kept", "kept_lo90", "kept_hi90", "passes")  # fmt: skip
    text = (
        f"context-retro: the blame split's owners (run {info['run_id']}, seasons "
        f"{min(seasons)}-{max(seasons)}, regular season; walk-forward chances)\n"
        "repeat: r with next season, each season's league average out (90% from resampling "
        "players); share_kept: movers' r over stayers' (its 90% from resampling players); passes: "
        "repeat 0.2+ and kept half\n\n"
        f"{shown.with_columns(pl.selectors.float().round(3))}\n"
    )
    report_dir().mkdir(parents=True, exist_ok=True)
    (report_dir() / f"{name}.txt").write_text(text, encoding="utf-8")
    return {"player_game": str(out), "rows": pg.height, "table": table.to_dicts()}


def main(argv: Sequence[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m pcf.experts.context_retro.split")
    ap.add_argument("--tag", default="backtest")
    ap.add_argument("--seasons", default="2017-2024")
    ap.add_argument("--name", default="split")
    a = ap.parse_args(argv)
    lo, hi = (int(x) for x in a.seasons.split("-"))
    res = run(a.tag, range(lo, hi + 1), a.name)
    log.info("split: %d player-game rows, %s", res["rows"], res["player_game"])


if __name__ == "__main__":
    main()
