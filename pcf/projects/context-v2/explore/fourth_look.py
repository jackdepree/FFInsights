# ruff: noqa: E501
"""context-v2, the fourth look (2026-11-20): I94, the blame split. A play's sack over expected is
split into the pressure part (E1 - E0) and the after-pressure part (sack - E1), where E0 is the sack
chance before the snap and E1 the chance given whether there was a pressure; then each part's
repeat and movers' share kept, for QBs and linemen (skill-over-expected's yardstick).

Discovery only, 2016-2024 regular season; the 2025 vault untouched. Design and pass rules
committed before the run (EXPLORATION.md, "Fourth look"; commit 24a1956).

Run from pcf/:  python projects/context-v2/explore/fourth_look.py > projects/context-v2/explore/fourth_look.txt
"""

from __future__ import annotations

import importlib.util
import pathlib

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier

from pcf.config import get_config
from pcf.data.gateway import Gateway
from pcf.experts.context_live import back, models

c = pl.col
SEED = get_config().seed
FIRST, LAST = 2017, 2024
ERAS = (tuple(range(2016, 2023)), (2023, 2024))  # participation's two pressure providers
FIELDS = back.EDITIONS["calls16"]
OL = ["C", "LT", "RT", "LG", "RG", "G", "T"]

_p = pathlib.Path(__file__).parents[2] / "skill-over-expected" / "explore" / "third_look.py"
_spec = importlib.util.spec_from_file_location("soe_third", _p)
tl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tl)


def X(d: pl.DataFrame, fields: list[str]) -> np.ndarray:
    return d.select([c(f).cast(pl.Float64) for f in fields]).to_numpy()


def crossfit(d: pl.DataFrame, y: str, extra: list[str]) -> np.ndarray:
    """Each season's chance from trees trained on the other seasons of its provider."""
    out = np.full(d.height, np.nan)
    s = d["season"].to_numpy()
    fields = FIELDS + extra
    for era in ERAS:
        for t in era:
            tr = d.filter(c("season").is_in([x for x in era if x != t]))
            m = HistGradientBoostingClassifier(**models.TREES, random_state=SEED)
            m.fit(X(tr, fields), tr[y].to_numpy())
            out[s == t] = m.predict_proba(X(d.filter(c("season") == t), fields))[:, 1]
    return out


def share(y: np.ndarray, p: np.ndarray) -> float:
    return float(100 * (1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)))


def main() -> None:
    src = Gateway().source
    d = back.load(range(2016, LAST + 1)).filter(c("is_dropback"))
    d = d.with_columns(pres=pl.when(c("sack_y") == 1).then(1.0).otherwise(c("pressure_y")))
    print(
        f"Dropbacks 2016-{LAST}: {d.height}; pressure flag missing (not a sack) on {d['pres'].is_null().sum()}, left out"
    )
    d = d.filter(c("pres").is_not_null())
    d = d.with_columns(
        e0=pl.Series(crossfit(d, "sack_y", [])), e1=pl.Series(crossfit(d, "sack_y", ["pres"]))
    )
    a = d.filter(c("is_attempt") & c("complete_y").is_not_null())
    a = a.with_columns(
        c0=pl.Series(crossfit(a, "complete_y", [])),
        c1=pl.Series(crossfit(a, "complete_y", ["pres"])),
    )

    print(
        "\n== The sack and completion chances: share of squared error removed, by season (E0 before the snap; E1 given the pressure)"
    )
    rows = []
    for s in range(2016, LAST + 1):
        ds, as_ = d.filter(c("season") == s), a.filter(c("season") == s)
        y, ya = ds["sack_y"].to_numpy(), as_["complete_y"].to_numpy()
        rows.append({"season": s, "pressure_rate": ds["pres"].mean(), "sack_rate": y.mean(),
                     "sack_E0": share(y, ds["e0"].to_numpy()), "sack_E1": share(y, ds["e1"].to_numpy()),
                     "comp_E0": share(ya, as_["c0"].to_numpy()), "comp_E1": share(ya, as_["c1"].to_numpy())})  # fmt: skip
    print(pl.DataFrame(rows).with_columns(pl.selectors.float().round(3)))

    teams = tl.fl.main_team(src)
    sch = src.part("game", "schedule").select("game_id", "season", "week", "game_type")
    reg = sch.filter((c("game_type") == "REG") & c("season").is_between(FIRST, LAST)).select(
        "game_id", "week"
    )
    pb = (
        src.part("play", "pbp")
        .select("game_id", c("play_id").cast(pl.Int64), "passer_player_id")
        .join(reg, on="game_id")
    )
    keys = ["game_id", "play_id"]
    plays = d.select(*keys, "season", "sack_y", "pres", "e0", "e1").join(pb, on=keys)
    plays = plays.with_columns(
        after=c("sack_y") - c("e1"),
        prpart=c("e1") - c("e0"),
        ov0=c("sack_y") - c("e0"),
    )
    att = a.select(*keys, "season", "complete_y", "c0", "c1").join(pb, on=keys)

    def agg(frame: pl.DataFrame, by: str) -> pl.DataFrame:
        return frame.group_by(pid=by, season="season", week="week").agg(
            n=pl.len(),
            sk=c("sack_y").sum(),
            npres=c("pres").sum(),
            ov1p=(c("sack_y") - c("e1")).filter(c("pres") == 1).sum(),
            after=c("after").sum(),
            prpart=c("prpart").sum(),
            ov0=c("ov0").sum(),
        )

    rates = {
        "sacks per pressure, plain": ("sk", "npres"),
        "sacks per pressure over E1 (I94)": ("ov1p", "npres"),
        "sacks per dropback, plain": ("sk", "n"),
        "sack over E0 per dropback (the whole)": ("ov0", "n"),
        "after-pressure part per dropback": ("after", "n"),
        "pressure part per dropback": ("prpart", "n"),
    }
    sums = ["n", "sk", "npres", "ov1p", "after", "prpart", "ov0"]
    out = []
    qb_ids = teams.filter(c("position") == "QB").select("pid", "season")
    qb = agg(plays.drop_nulls("passer_player_id"), "passer_player_id").join(
        qb_ids, on=["pid", "season"]
    )
    p = tl.season_pairs(qb, sums, "n", 150, rates, teams)
    for k in rates:
        out.append({"who": "QB", **tl.kept(p, k, k, "I94")})

    ol = (
        src.part("player_play", "on_field")
        .filter(
            (c("side") == "offense") & c("position").is_in(OL) & c("season").is_between(FIRST, LAST)
        )
        .select("game_id", c("play_id").cast(pl.Int64), olid="gsis_id")
    )
    olp = agg(ol.join(plays, on=keys), "olid")
    p = tl.season_pairs(olp, sums, "n", 300, rates, teams)
    for k in rates:
        out.append({"who": "OL", **tl.kept(p, k, k, "I94")})

    ca = att.drop_nulls("passer_player_id").group_by(pid="passer_player_id", season="season", week="week").agg(
        na=pl.len(), cmp=c("complete_y").sum(), o0=(c("complete_y") - c("c0")).sum(), o1=(c("complete_y") - c("c1")).sum()
    ).join(qb_ids, on=["pid", "season"])  # fmt: skip
    crates = {"completion, plain": ("cmp", "na"), "completion over E0": ("o0", "na"), "completion over E1 (given pressure)": ("o1", "na")}  # fmt: skip
    p = tl.season_pairs(ca, ["na", "cmp", "o0", "o1"], "na", 150, crates, teams)
    for k in crates:
        out.append({"who": "QB", **tl.kept(p, k, k, "I94")})

    t = (
        pl.DataFrame(out, infer_schema_length=None)
        .select(
            "who",
            "measure",
            "pairs",
            "movers",
            "repeat",
            "lo90",
            "hi90",
            "stayers",
            "movers_r",
            "share_kept",
        )
        .with_columns(passes=(c("repeat") >= 0.2) & (c("share_kept") >= 0.5))
    )
    pl.Config.set_tbl_rows(100)
    pl.Config.set_tbl_width_chars(400)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_fmt_str_lengths(60)
    print(
        "\n== Every measure, 2017-2024 season pairs (each season's league average out; repeat = r with next season; share_kept = movers' r over stayers'; passes = repeat 0.2+ and movers keep half)"
    )
    print(t.with_columns(pl.selectors.float().round(3)))


if __name__ == "__main__":
    main()
