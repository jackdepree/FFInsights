"""The CEO's spot-check of pace#R1 (2026-11-11): is the full-sample habits' win over the neutral
ones real, and is it the measurement (every play against PCF's expected values) or something
else?

The published `_full` set has three habits (pace over expected, PROE, no-huddle) and `_neutral`
has two (tempo, neutral PROE), so the published race isn't strictly like for like. This reruns the
same walk-forward (2016-2024, Saturday run, refit every step) with:
- `none`: no habits at all (what do habits add?);
- `full` and `neutral` as published;
- `full_no_nh`: full without no-huddle (two against two);
- `neutral_nh`: neutral plus the neutral no-huddle rate (three against three);
- `pace_only` / `proe_only`: one full-sample habit swapped in at a time, the other neutral.
Each against `neutral` on the range score, with the week-block 90% interval the harness uses,
per season, and the rows where full and neutral disagree most.
"""

import polars as pl

from pcf.data.gateway import Gateway
from pcf.experts.pace import features as F
from pcf.experts.pace import model as M
from pcf.validation import backtest
from pcf.validation.compare import compare

c = pl.col
SEASONS = list(range(2016, 2025))
F.NEUTRAL["neutral_no_huddle"] = ("no_huddle_rate", "neutral_plays")
SETS = {
    "none": (),
    "neutral": ("tempo", "neutral_pass_oe"),
    "full": ("pace_oe", "proe", "no_huddle"),
    "full_no_nh": ("pace_oe", "proe"),
    "neutral_nh": ("tempo", "neutral_pass_oe", "neutral_no_huddle"),
    "pace_only": ("pace_oe", "neutral_pass_oe"),
    "proe_only": ("tempo", "proe"),
}
M.HABIT_SETS.update(SETS)
FULL = ("pace_oe", "proe", "no_huddle")  # the habit averages the volume features carry
F.FULL_HABITS = FULL
gw = Gateway()
keys = ["game_id", "team"]


def variant(v: str, s: str):
    cls = type(
        f"Spot{v}{s}",
        (M._VolumeModel,),
        {"trait": v, "quantity": v, "habits": s, "variant": f"{v}_{s}", "__module__": __name__},
    )
    return cls()


for v in ("plays", "dropbacks", "runs"):
    runs = {s: backtest.run(variant(v, s), gateway=gw, seasons=SEASONS) for s in SETS}
    base = runs["neutral"].scored
    print(f"\n=== {v}: range score of each against neutral (negative = better), 90% week-block")
    for s, bt in runs.items():
        miss = float((bt.scored["y"] - bt.scored["mean"]).abs().mean())
        if s == "neutral":
            print(f"  {s:<11} miss {miss:.3f}")
            continue
        cmp = compare(bt.scored, base, keys, "step", (s, "neutral"))
        print(f"  {s:<11} miss {miss:.3f}  diff {cmp.diff:+.4f} ({cmp.lo:+.4f} to {cmp.hi:+.4f})")
    full = runs["full"].scored
    seasons = (
        full.select(*keys, "step", "y", "mean", loss_f="loss")
        .join(base.select(*keys, loss_n="loss", mean_n="mean"), on=keys)
        .with_columns(season=c("game_id").str.slice(0, 4).cast(pl.Int32))
    )
    per = seasons.group_by("season").agg((c("loss_f") - c("loss_n")).mean().alias("diff")).sort(
        "season"
    )
    better = per.filter(c("diff") < 0).height
    print(f"  full against neutral by season ({better} of {per.height} better):")
    print("   ", "  ".join(f"{r['season']} {r['diff']:+.3f}" for r in per.iter_rows(named=True)))
    if v == "plays":
        gap = seasons.with_columns(gap=c("mean") - c("mean_n"))
        print("  full minus neutral forecast: sd", round(gap["gap"].std(), 2), "plays; 95% within",
              round(gap["gap"].abs().quantile(0.95), 2))
        top = gap.sort(c("gap").abs(), descending=True).head(8)
        print(top.select(*keys, "y", full=c("mean").round(1), neutral=c("mean_n").round(1)))
        # do the bigger disagreements go the full model's way?
        big = gap.filter(c("gap").abs() > c("gap").abs().quantile(0.8))
        right = big.filter(((c("y") - c("mean_n")) * c("gap")) > 0).height
        print(f"  top 20% disagreements: full's direction right in {right} of {big.height}")
