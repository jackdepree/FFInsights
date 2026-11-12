"""The CEO's spot-check (2026-11-12): "the meta logic of the inputs into the model". Are we giving
the model the right inputs to learn who was on the field?

For held-out 2023 and 2024 (each trained on the three seasons before, as in the backtest), the
sequence rung is refitted:
- **without each family of inputs** (its columns set to 0 in training and test), to measure what
  each family adds;
- **with three candidate inputs it doesn't have**, all known by the morning after:
  - `gn`, `gfull`: competition within his position group (teammates of his group named on this
    snap; his group's every-snap players in the game). The chances are balanced to 11 a snap but
    don't know that a second named back pushes the first one off;
  - `o_rb`, `o_te`, `o_wr` (defense only): the offense's expected backs, tight ends and receivers
    on this snap, from the offense's own walk-forward chances (`p_sequence`, rule e). A defense
    picks its package against the offense's personnel;
  - the same with the offense's true counts (an oracle: what perfect personnel would be worth).

Scores: log loss on open cells, and open spots right in the likeliest lineup (the CEO's headline,
2026-11-12), offense and defense. Writes spot_inputs.txt.
"""

# ruff: noqa: E501
import sys
import time
from pathlib import Path

import polars as pl

from pcf.experts.participation_live import chain, grid, model, reconstruct, score

c = pl.col
HERE = Path(__file__).parent
SEASONS = [int(x) for x in sys.argv[1:]] or [2023, 2024]
FLAGS = [x for x in model.LEAGUE if x.startswith("f_")]
PH = [x for x in model.HISTORY if x.startswith("ph")]
TH = [x for x in model.HISTORY if x.startswith("th_")]
COMP = ["gn", "gfull"]
OPP = ["o_rb", "o_te", "o_wr"]
ORACLE = ["t_rb", "t_te", "t_wr"]
VARIANTS = {
    "full": ([], []),
    "no_situation": (FLAGS, []),
    "no_player_history": (PH, []),
    "no_team_history": (TH, []),
    "no_stay_return": (["stay", "ret"], []),
    "no_drive_count": (["dn"], []),
    "plus_competition": ([], COMP),
    "plus_offense_personnel": ([], OPP),
    "plus_both": ([], COMP + OPP),
    "plus_true_personnel": ([], ORACLE),
}
ORIG = model.base_columns

S = pl.scan_parquet(reconstruct.cache_dir() / "scored_2019_2024.parquet")


def offense_counts(seasons):
    """Per play: the offense's expected (p_sequence) and true counts of backs, tight ends and
    receivers."""
    o = S.filter(c("side") == "offense", c("season").is_in(seasons), c("group").is_in(["RB", "TE", "WR"]))
    o = o.group_by("game_id", "play_id").agg(
        *[(c("p_sequence") * (c("group") == g)).sum().alias(f"o_{g.lower()}") for g in ("RB", "TE", "WR")],
        *[(c("on") * (c("group") == g)).sum().cast(pl.Float64).alias(f"t_{g.lower()}") for g in ("RB", "TE", "WR")],
    )
    return o.collect()


def add_inputs(g: pl.DataFrame, oc: pl.DataFrame) -> pl.DataFrame:
    key = ["game_id", "play_id", "side", "team", "group"]
    g = g.with_columns(
        gn=(c("named").cast(pl.Float64).sum().over(key) - c("named").cast(pl.Float64)),
        gfull=c("full").cast(pl.Float64).sum().over("game_id", "side", "team", "group", "n") - c("full").cast(pl.Float64),
    )
    g = g.join(oc, on=["game_id", "play_id"], how="left")
    d = c("side") == "defense"
    return g.with_columns(
        [pl.when(d).then(c(x)).otherwise(0.0).fill_null(0.0).alias(x) for x in OPP + ORACLE]
    )


def run(season: int) -> list[dict]:
    seasons = [s for s in range(season - reconstruct.TRAIN_SEASONS, season + 1)]
    oc = offense_counts(seasons)
    train0 = add_inputs(reconstruct.train_frame(season), oc)
    test0 = add_inputs(reconstruct.load(season), oc)
    rows = []
    for name, (drop, extra) in VARIANTS.items():
        t0 = time.time()
        zero = [pl.lit(0.0).alias(x) for x in drop]
        train = train0.with_columns(zero) if zero else train0
        test = test0.with_columns(zero) if zero else test0
        model.base_columns = lambda kind, extra=extra: [*ORIG(kind), *extra] if kind == "sequence" else ORIG(kind)
        m = model.fit(train, "sequence", seed=season)
        model.base_columns = ORIG
        inf = chain.infer(test, m)
        t = test.join(inf.select(*grid.CELL_KEYS, c("p").alias("p_v")), on=grid.CELL_KEYS, how="left")
        top = chain.likeliest(t.with_columns(p=c("p_v")))
        t = t.join(top.select(*grid.CELL_KEYS, c("likeliest").alias("top_v")), on=grid.CELL_KEYS, how="left")
        pp = score.per_play(t, "v", "top_v")
        r = {"season": season, "variant": name, "seconds": round(time.time() - t0)}
        for side in ("offense", "defense"):
            r[f"{side}_log_loss"] = pp[f"{side}_log_loss"]
            r[f"{side}_open_right"] = pp[f"{side}_open_right"]
        bg = score.by_group(t, "v", "top_v")
        for row in bg.filter(c("group").is_in(["RB", "TE", "WR", "DL", "LB", "DB"])).iter_rows(named=True):
            if (row["side"] == "offense") == (row["group"] in ("RB", "TE", "WR")):
                r[f"ll_{row['group']}"] = row["log_loss"]
        rows.append(r)
        print(r, flush=True)
    return rows


rows = [r for s in SEASONS for r in run(s)]
df = pl.DataFrame(rows)
base = df.filter(c("variant") == "full").select("season", *[pl.col(x).alias(f"{x}_full") for x in ("offense_log_loss", "defense_log_loss")])
df = df.join(base, on="season").with_columns(
    off_change_pct=100 * (c("offense_log_loss") / c("offense_log_loss_full") - 1),
    def_change_pct=100 * (c("defense_log_loss") / c("defense_log_loss_full") - 1),
).drop("offense_log_loss_full", "defense_log_loss_full")
pooled = df.group_by("variant", maintain_order=True).agg(pl.exclude("season", "variant").mean())
lines = [
    "Spot-check of the inputs: the sequence rung refitted without each family, and with candidate inputs.",
    "Change in log loss on open cells against the full model (negative = better). Open right = the likeliest lineup.",
    "", "Mean of the seasons:",
]
with pl.Config(tbl_cols=30, tbl_width_chars=400, float_precision=4, tbl_rows=40):
    lines += [str(pooled), "", "By season:", str(df)]
text = "\n".join(lines)
(HERE / "spot_inputs.txt").write_text(text, encoding="utf-8")
print(text)
