"""The CEO's spot-check (2026-11-12), round 2: after round 1 (`spot_inputs_round1.txt`, with
`spot_inputs_round1.py`) found that the competition in a player's group on the snap helps, the
model now has it (`gn`, `gfull`) and the pair habits with the teammates named on the snap (`pn`,
H36, H37). For held-out 2023 and 2024 (each trained on the three seasons before), the sequence
rung refitted without each family of inputs (its columns set to 0 in training and test).

Scores: log loss on open cells, and open spots right in the likeliest lineup. Writes
spot_inputs.txt.
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
VARIANTS = {
    "full": [],
    "no_competition": ["gn", "gfull"],
    "no_partner": ["pn"],
    "no_competition_or_partner": ["gn", "gfull", "pn"],
    "no_team_history": TH,
    "no_stay_return": ["stay", "ret"],
    "no_drive_count": ["dn"],
}


def run(season: int) -> list[dict]:
    train0 = reconstruct.train_frame(season)
    test0 = reconstruct.load(season)
    rows = []
    for name, drop in VARIANTS.items():
        t0 = time.time()
        zero = [pl.lit(0.0).alias(x) for x in drop]
        train = train0.with_columns(zero) if zero else train0
        test = test0.with_columns(zero) if zero else test0
        m = model.fit(train, "sequence", seed=season)
        inf = chain.infer(test, m)
        t = test.join(
            inf.select(*grid.CELL_KEYS, c("p").alias("p_v")), on=grid.CELL_KEYS, how="left"
        )
        top = chain.likeliest(t.with_columns(p=c("p_v")))
        t = t.join(
            top.select(*grid.CELL_KEYS, c("likeliest").alias("top_v")),
            on=grid.CELL_KEYS,
            how="left",
        )
        pp = score.per_play(t, "v", "top_v")
        r = {"season": season, "variant": name, "seconds": round(time.time() - t0)}
        for side in ("offense", "defense"):
            r[f"{side}_log_loss"] = pp[f"{side}_log_loss"]
            r[f"{side}_open_right"] = pp[f"{side}_open_right"]
        bg = score.by_group(t, "v", "top_v")
        for row in bg.filter(c("group").is_in(["RB", "TE", "WR", "DL", "LB", "DB"])).iter_rows(
            named=True
        ):
            if (row["side"] == "offense") == (row["group"] in ("RB", "TE", "WR")):
                r[f"ll_{row['group']}"] = row["log_loss"]
        rows.append(r)
        print(r, flush=True)
    return rows


rows = [r for s in SEASONS for r in run(s)]
df = pl.DataFrame(rows)
base = df.filter(c("variant") == "full").select(
    "season", *[pl.col(x).alias(f"{x}_full") for x in ("offense_log_loss", "defense_log_loss")]
)
df = (
    df.join(base, on="season")
    .with_columns(
        off_change_pct=100 * (c("offense_log_loss") / c("offense_log_loss_full") - 1),
        def_change_pct=100 * (c("defense_log_loss") / c("defense_log_loss_full") - 1),
    )
    .drop("offense_log_loss_full", "defense_log_loss_full")
)
pooled = df.group_by("variant", maintain_order=True).agg(pl.exclude("season", "variant").mean())
lines = [
    "Spot-check of the inputs: the sequence rung refitted without each family, and with candidate inputs.",
    "Change in log loss on open cells against the full model (negative = better). Open right = the likeliest lineup.",
    "",
    "Mean of the seasons:",
]
with pl.Config(tbl_cols=30, tbl_width_chars=400, float_precision=4, tbl_rows=40):
    lines += [str(pooled), "", "By season:", str(df)]
text = "\n".join(lines)
(HERE / "spot_inputs.txt").write_text(text, encoding="utf-8")
print(text)
