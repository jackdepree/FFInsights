"""participation-late exploration (2026-11-12): what can a second edition of the map, made later,
add to the morning-after map?

- **H39 (the CEO):** "add the snap counts for the next game, and then we just predict the past
  game". Each player's snap share in his team's next game (and, for comparison, the previous one)
  as inputs: `xn` (next game's share log-odds minus this game's; 0 if he didn't play in it: his
  share is 0) with `hn` (the team has a next game this season); `xp`, `hp` the same for the game
  before.
- **FTN's counts per play** (2022 on): the backfield count, the box count, pass rushers,
  blitzers, motion, play action, screen; `fmiss` when the play isn't charted.

Held out 2023 and 2024. The snap-share tests train on the three seasons before (as the
morning-after map does); the FTN tests on the FTN seasons before only (2023 on 2022, 2024 on
2022-2023), against the same model trained on the same seasons without them. Sequence rung, the
likeliest lineup. Writes late_inputs.txt.

FTN is read from the retrospective view here (an exploration); the build will read it at each
game's own moment.
"""

# ruff: noqa: E501
import sys
import time
from pathlib import Path

import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.participation_live import chain, grid, model, reconstruct, score

c = pl.col
HERE = Path(__file__).parent
SEASONS = [int(x) for x in sys.argv[1:]] or [2023, 2024]
FTN_FIRST = 2022
ADJ_NEXT = ["xn", "hn"]
ADJ_BOTH = ["xn", "hn", "xp", "hp"]
FTN = ["bf", "box", "rush", "blitz", "motion", "pa", "screen", "fmiss"]
ORIG = model.base_columns


def logit(x: pl.Expr) -> pl.Expr:
    s = x.clip(0.01, 0.99)
    return (s / (1 - s)).log()


def adjacent(g: pl.DataFrame) -> pl.DataFrame:
    """Each player's share in his team's next and previous game of the season (0 if he didn't
    play in it)."""
    games = (
        g.select("season", "team", "side", "game_id", "week").unique()
        .sort("season", "team", "side", "week")
        .with_columns(
            next_game=c("game_id").shift(-1).over("season", "team", "side"),
            prev_game=c("game_id").shift(1).over("season", "team", "side"),
        )
    )
    shares = g.select("game_id", "side", "team", "gsis_id", "share").unique(["game_id", "side", "team", "gsis_id"])
    pg = g.select("game_id", "side", "team", "gsis_id", "share").unique(["game_id", "side", "team", "gsis_id"]).join(
        games.select("game_id", "side", "team", "next_game", "prev_game"), on=["game_id", "side", "team"]
    )
    for k, col in (("n", "next_game"), ("p", "prev_game")):
        pg = pg.join(
            shares.rename({"game_id": col, "share": f"s{k}"}), on=[col, "side", "team", "gsis_id"], how="left"
        ).with_columns(
            **{f"h{k}": c(col).is_not_null().cast(pl.Float64)},
        ).with_columns(
            **{f"x{k}": pl.when(c(f"h{k}") == 1).then(logit(c(f"s{k}").fill_null(0.0)) - logit(c("share"))).otherwise(0.0)}
        )
    return g.join(pg.select("game_id", "side", "team", "gsis_id", "xn", "hn", "xp", "hp"), on=["game_id", "side", "team", "gsis_id"], how="left")


def ftn_counts(seasons: list[int]) -> pl.DataFrame:
    out = []
    for s in seasons:
        if s < FTN_FIRST:
            continue
        gw = Gateway(TableSource(seasons=[s]))
        v = gw.view(END_OF_TIME, "retrospective", {"play": ("ftn",)})
        f = v.table("play", seasons=[s]).select("game_id", "play_id", "n_offense_backfield", "n_defense_box", "n_pass_rushers", "n_blitzers", "is_motion", "is_play_action", "is_screen_pass")
        out.append(f)
    f = pl.concat(out)
    return f.select(
        "game_id", "play_id",
        bf=(c("n_offense_backfield").clip(0, 3) - 1).cast(pl.Float64),
        box=(c("n_defense_box").clip(3, 9) - 6).cast(pl.Float64),
        rush=(c("n_pass_rushers").clip(0, 8) / 4).cast(pl.Float64),
        blitz=c("n_blitzers").clip(0, 4).cast(pl.Float64),
        motion=c("is_motion").cast(pl.Float64),
        pa=c("is_play_action").cast(pl.Float64),
        screen=c("is_screen_pass").cast(pl.Float64),
    )


def with_inputs(g: pl.DataFrame, ftn: pl.DataFrame) -> pl.DataFrame:
    g = adjacent(g).join(ftn, on=["game_id", "play_id"], how="left")
    return g.with_columns(fmiss=c("bf").is_null().cast(pl.Float64)).with_columns(
        [c(x).fill_null(0.0) for x in FTN + ADJ_BOTH]
    )


def fit_score(train, test, extra, season, name, era):
    t0 = time.time()
    model.base_columns = lambda kind, extra=extra: [*ORIG(kind), *extra] if kind == "sequence" else ORIG(kind)
    try:
        m = model.fit(train, "sequence", seed=season)
    finally:
        model.base_columns = ORIG
    inf = chain.infer(test, m)
    t = test.join(inf.select(*grid.CELL_KEYS, c("p").alias("p_v")), on=grid.CELL_KEYS, how="left")
    top = chain.likeliest(t.with_columns(p=c("p_v")))
    t = t.join(top.select(*grid.CELL_KEYS, c("likeliest").alias("top_v")), on=grid.CELL_KEYS, how="left")
    pp = score.per_play(t, "v", "top_v")
    r = {"season": season, "train": era, "variant": name, "seconds": round(time.time() - t0)}
    for side in ("offense", "defense"):
        r[f"{side}_log_loss"] = pp[f"{side}_log_loss"]
        r[f"{side}_open_right"] = pp[f"{side}_open_right"]
    bg = score.by_group(t, "v", "top_v")
    for row in bg.filter(c("group").is_in(["QB", "RB", "TE", "WR", "DL", "LB", "DB"])).iter_rows(named=True):
        if (row["side"] == "offense") == (row["group"] in ("QB", "RB", "TE", "WR")):
            r[f"ll_{row['group']}"] = row["log_loss"]
    print(r, flush=True)
    return r


rows = []
for s in SEASONS:
    seasons = list(range(s - reconstruct.TRAIN_SEASONS, s + 1))
    ftn = ftn_counts(seasons)
    train = with_inputs(reconstruct.train_frame(s), ftn)
    test = with_inputs(reconstruct.load(s), ftn)
    for name, extra in (("full", []), ("plus_next_game", ADJ_NEXT), ("plus_next_and_previous", ADJ_BOTH)):
        rows.append(fit_score(train, test, extra, s, name, "three seasons"))
    tr = train.filter(c("season") >= FTN_FIRST)
    for name, extra in (("full", []), ("plus_ftn", FTN), ("plus_ftn_and_next", FTN + ADJ_NEXT)):
        rows.append(fit_score(tr, test, extra, s, name, "FTN seasons"))
    del train, test, tr

df = pl.DataFrame(rows)
base = df.filter(c("variant") == "full").select("season", "train", *[c(x).alias(f"{x}_0") for x in ("offense_log_loss", "defense_log_loss", "offense_open_right", "defense_open_right")])
df = df.join(base, on=["season", "train"]).with_columns(
    off_change_pct=100 * (c("offense_log_loss") / c("offense_log_loss_0") - 1),
    def_change_pct=100 * (c("defense_log_loss") / c("defense_log_loss_0") - 1),
    off_open_pts=100 * (c("offense_open_right") - c("offense_open_right_0")),
    def_open_pts=100 * (c("defense_open_right") - c("defense_open_right_0")),
).drop(c("^.*_0$"))
pooled = df.group_by("train", "variant", maintain_order=True).agg(pl.exclude("season", "train", "variant").mean())
lines = [
    "participation-late exploration: what a later edition can add. Change in log loss on open cells against the same training without the input (negative = better); open points = open spots right in the likeliest lineup.",
    "", "Mean of 2023 and 2024:",
]
with pl.Config(tbl_cols=40, tbl_width_chars=400, float_precision=4, tbl_rows=40):
    lines += [str(pooled), "", "By season:", str(df)]
text = "\n".join(lines)
(HERE / "late_inputs.txt").write_text(text, encoding="utf-8")
print(text)
