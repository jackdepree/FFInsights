"""CEO question (2026-11-04): does the room a player joins change their share? A high-share player
leaving a weak room for a deeper, evenly shared one should lose share, and their new teammates
should too. Does career share help for that reason? Discovery only: never proof.
Run from pcf/: PYTHONUTF8=1 .venv/Scripts/python.exe projects/participation/explore/new_team_room.py

A player's "usual share" is their average over their last 8 active games, wherever they played.
The room is the same-position players on this week's roster, not listed Out or Doubtful, by usual
share. Rooms are fixed before looking at results:
- thin: nobody else has a usual share of 40%+;
- even: the top two others are both 40%+, within 20 points of each other;
- leader: anything else, one clear leader.
A mover is in their first 4 games on a new team, with some history. Scored rows are the saved
walk-forward histories, 2016-2024, so the "miss" is what the expert already can't see. It has the
depth chart, which should carry much of this.
"""

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

from pcf.data.gateway import Gateway

sys.path.insert(0, str(Path(__file__).parent))
from career_share import with_memory  # noqa: E402
from compare_rungs import KEYS, history  # noqa: E402
from profile_participation import frame  # noqa: E402

c = pl.col
HIGH = 0.6  # a high-share mover
ROOM = ["mate_top", "mate_second", "mate_sum", "old_top", "old_second", "old_sum"]
CAREER = ["career_active_avg", "career_gap"]
BASE = ["usual", "is_rb", "is_wr", "is_te", "is_qb"]
SETS = {
    "plain": BASE,
    "room": [*BASE, *ROOM],
    "career": [*BASE, *CAREER],
    "both": [*BASE, *ROOM, *CAREER],
}


def room_type(top: str, second: str) -> pl.Expr:
    return (
        pl.when(c(top) < 0.4).then(pl.lit("thin"))
        .when((c(second) >= 0.4) & (c(top) - c(second) < 0.2)).then(pl.lit("even"))
        .otherwise(pl.lit("leader"))
    )  # fmt: skip


def rooms() -> pl.DataFrame:
    d = with_memory(frame()).with_columns(usual=c("active_avg8").cast(pl.Float64).fill_nan(None))
    keyed = d.with_columns(
        here=(c("report") < 2).fill_null(True),
        u=c("usual").fill_null(0.0),
    ).with_columns(a=pl.when(c("here")).then(c("u")).otherwise(0.0))
    group = ["game_id", "team", "position"]
    tops = keyed.group_by(group).agg(
        room_sum=c("a").sum(),
        t1=c("a").top_k(3).get(0, null_on_oob=True),
        t2=c("a").top_k(3).get(1, null_on_oob=True),
        t3=c("a").top_k(3).get(2, null_on_oob=True),
    )
    d = keyed.join(tops, on=group).with_columns(c("t1", "t2", "t3").fill_null(0.0)).with_columns(
        mate_top=pl.when(c("a") >= c("t1")).then(c("t2")).otherwise(c("t1")),
        mate_second=pl.when(c("a") >= c("t2")).then(c("t3")).otherwise(c("t2")),
        mate_sum=c("room_sum") - c("a"),
    )  # fmt: skip
    g = ["gsis_id"]
    # The room they left is the one in their last game before this stint, and stays so all stint
    stint = [*g, "stint"]
    first = c("games_on_team") == 0
    d = (
        d.sort("gsis_id", "kickoff")
        .with_columns(
            old_top=c("mate_top").shift(1).over(g),
            old_second=c("mate_second").shift(1).over(g),
            old_sum=c("mate_sum").shift(1).over(g),
            moved_season=c("season") != c("season").shift(1).over(g),
        )
        .with_columns(
            pl.when(first).then(c(x)).forward_fill().over(stint).alias(x)
            for x in ("old_top", "old_second", "old_sum", "moved_season")
        )
    )
    return d.with_columns(
        mover=(c("stint") >= 1) & (c("games_on_team") <= 3) & c("usual").is_not_null(),
        room=room_type("mate_top", "mate_second"),
        old_room=room_type("old_top", "old_second"),
        career_gap=c("usual") - c("career_active_avg").cast(pl.Float64).fill_nan(None),
        **{
            f"is_{p.lower()}": (c("position") == p).cast(pl.Float64)
            for p in ("QB", "RB", "WR", "TE")
        },
    )


def spread(ids: np.ndarray, d: np.ndarray, seed: int = 0) -> tuple[float, float]:
    """A 90% interval on a mean, resampling whole players."""
    people = (
        pl.DataFrame({"id": ids, "d": d}).group_by("id").agg(s=c("d").sum(), n=pl.len()).sort("id")
    )
    s, n = people["s"].to_numpy(), people["n"].to_numpy()
    draws = np.random.default_rng(seed).integers(0, len(s), (2000, len(s)))
    return tuple(np.quantile(s[draws].sum(1) / n[draws].sum(1), [0.05, 0.95]))


def table(d: pl.DataFrame, by: list[str], title: str) -> None:
    rows = []
    for key, g in d.group_by(by, maintain_order=False):
        miss = (g["mean"] - g["y"]).to_numpy() * 100
        lo, hi = spread(g["gsis_id"].to_numpy(), miss)
        rows.append({
            **dict(zip(by, key, strict=True)), "rows": g.height, "players": g["gsis_id"].n_unique(),
            "usual": g["usual"].mean() * 100, "actual": g["y"].mean() * 100,
            "said": g["mean"].mean() * 100, "said-was": miss.mean(), "lo": lo, "hi": hi,
            "MAE": np.abs(miss).mean(),
        })  # fmt: skip
    print(f"\n{title}")
    with pl.Config(float_precision=1, tbl_width_chars=200, tbl_rows=60, tbl_cols=20):
        print(pl.DataFrame(rows).sort(by))


def correct(d: pl.DataFrame, cols: list[str]) -> np.ndarray:
    """Walk-forward: earlier seasons' movers learn the expert's miss, for each later season."""
    out = np.full(d.height, np.nan)
    seasons = d["season"].to_numpy()
    x = d.select(cols).to_numpy()
    miss = (d["y"] - d["mean"]).to_numpy()
    for s in range(2019, 2025):
        train, test = seasons < s, seasons == s
        m = HistGradientBoostingRegressor(
            max_iter=100, learning_rate=0.03, max_depth=3, min_samples_leaf=40, random_state=0
        ).fit(x[train], miss[train])
        out[test] = m.predict(x[test])
    return out


def horizon(variant: str, r: pl.DataFrame, gw: Gateway) -> None:
    h = history(variant, gw).select(*KEYS, "y", "mean").join(r, on=KEYS)
    movers = h.filter(c("mover")).with_columns(
        move=pl.when(c("moved_season")).then(pl.lit("offseason")).otherwise(pl.lit("in season"))
    )  # fmt: skip
    print(f"\n======== {variant}: {movers.height:,} mover rows of {h.height:,}")
    w = h.filter(c("week") == 1)
    for name, d in (("all rows", h), ("week 1", w)):
        mae = (d["mean"] - d["y"]).abs().mean() * 100
        r2 = 1 - ((d["y"] - d["mean"]) ** 2).mean() / d["y"].var()
        print(f"  {name}: MAE {mae:.2f}, R2 {r2:.3f}")
    table(movers, ["move"], "Movers, offseason or in season")
    high = movers.filter(c("usual") >= HIGH)
    table(high, ["room"], f"High-share movers (usual {HIGH:.0%}+) by the room they join")
    table(high.filter(c("position") != "QB"), ["position", "room"], "Same, by position")
    table(high, ["old_room", "room"], "Same, by the room they left and the room they join")

    table(
        high.filter(c("room") == "even"), ["season"], "High-share movers into even rooms, by season"
    )
    table(high.filter(c("old_room") == "thin"), ["room"], "High-share movers leaving a thin room")

    skill = high.filter(c("position") != "QB")  # a QB's "thin" room is simply the normal one
    table(skill, ["room"], "Same, without QBs")
    table(skill.filter(c("old_room") == "thin"), ["room"], "Without QBs, leaving a thin room")

    # The room's own players: did they lose share to a high-share arrival?
    arrivals = movers.filter(c("usual") >= HIGH).select("game_id", "team", "position").unique()
    regulars = h.filter(~c("mover") & (c("usual") >= 0.3)).join(
        arrivals.with_columns(pl.lit("arrival").alias("came")),
        on=["game_id", "team", "position"], how="left",
    ).with_columns(c("came").fill_null("no arrival"))  # fmt: skip
    table(regulars, ["position", "came"], "Regulars already there (usual 30%+)")

    # Would the room, or career share, fix the movers' miss, on later seasons?
    usable = movers.with_columns(
        c(x).cast(pl.Float64).fill_null(0.0).fill_nan(0.0) for x in [*ROOM, *CAREER]
    )
    fixes = {n: correct(usable, cols) for n, cols in SETS.items()}
    keep = usable["season"].to_numpy() >= 2019
    y, p = usable["y"].to_numpy()[keep], usable["mean"].to_numpy()[keep]
    ids = usable["gsis_id"].to_numpy()[keep]
    now = np.abs(y - p) * 100
    print(f"\nWalk-forward correction of movers' miss, 2019-2024, {keep.sum():,} rows: "
          f"MAE now {now.mean():.2f}, bias {(p - y).mean() * 100:+.2f}")  # fmt: skip
    for n, f in fixes.items():
        d = np.abs(y - (p + f[keep]).clip(0, 1)) * 100 - now
        lo, hi = spread(ids, d)
        print(f"   {n:<7} MAE change {d.mean():+.2f} ({lo:+.2f} to {hi:+.2f})")
    plain = np.abs(y - (p + fixes["plain"][keep]).clip(0, 1)) * 100
    for n in ("room", "career", "both"):
        d = np.abs(y - (p + fixes[n][keep]).clip(0, 1)) * 100 - plain
        lo, hi = spread(ids, d)
        print(f"   {n:<7} beyond plain {d.mean():+.2f} ({lo:+.2f} to {hi:+.2f})")


def main() -> None:
    gw = Gateway()
    r = rooms().select(
        *KEYS, "season", "week", "team", "position", "usual", "mover", "moved_season", "stint",
        "games_on_team", "room", "old_room", *ROOM, *CAREER, "is_qb", "is_rb", "is_wr", "is_te",
    )  # fmt: skip
    for variant in ("trees", "lasso_h3", "lasso_rest"):
        horizon(variant, r, gw)


if __name__ == "__main__":
    main()
