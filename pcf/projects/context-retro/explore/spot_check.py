"""The CEO's spot-check (2026-11-22): why the QB's after-pressure part didn't repeat from 2024 to
2025 (-0.04), beside plain sacks per dropback (0.14). Is it that season pair, the model, or
something else? Writes build/spot_check.txt.

Causes looked at, each against the other seven season pairs (2017-2024 walk-forward from the
backtest run, 2025 from the vault run):
  1. the provider: the league's levels by season (pressure, sacks, E0 and E1's calibration);
  2. sample size: within-season reliability (odd against even weeks) and the ceiling it sets,
     and how often 31 QBs drawn from the other pairs repeat this little;
  3. outliers: rank r, and r without the most influential QBs;
  4. QB turnover: stayers only, and without QBs in their first or second season;
  5. the vault's scoring: does 2025's after-pressure part track the plain sack numbers as
     closely as other seasons' does, and do model-free measures fail too;
  plus offenses (team sacks per dropback), which have no model in them.

    python projects/context-retro/explore/spot_check.py
"""

from __future__ import annotations

import json

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.experts.context_retro import plays, split
from pcf.experts.context_retro.run import cache_dir, report_dir
from pcf.validation.owners import r

c = pl.col
FLOOR = 150
RNG = np.random.default_rng(20261122)
out: list[str] = []


def say(*lines: str) -> None:
    out.extend(lines)
    print(*lines, sep="\n")


def table(frame: pl.DataFrame) -> str:
    with pl.Config(tbl_rows=60, tbl_cols=20, tbl_width_chars=250, fmt_str_lengths=30,
                   tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True):  # fmt: skip
        return str(frame.with_columns(pl.selectors.float().round(3)))


def spearman(x, y) -> float:
    x, y = pl.Series(x).rank(), pl.Series(y).rank()
    return r(x, y)


# ---- the data: every dropback's parts, 2017-2025
runs = {t: json.loads((cache_dir() / t / "run.json").read_text()) for t in ("backtest", "vault")}
hist = pl.concat([pl.read_parquet(i["path"]) for i in runs.values()], how="vertical_relaxed")
data = plays.load(range(2017, 2026))
parts = split.play_parts(hist, data).filter(c("season_type") == "REG")
players = pl.read_parquet(get_config().zone("raw") / "nflverse" / "players" / "players.parquet")
names = players.select(passer_id="gsis_id", name="display_name", rookie="rookie_season")

say("context-retro spot-check: the QB's after-pressure part, 2024 to 2025 (the CEO, 2026-11-22)",
    f"runs: backtest {runs['backtest']['run_id'][:8]} (2017-2024 walk-forward), vault "
    f"{runs['vault']['run_id'][:8]} (2025, trained through 2024); regular season; QBs with "
    f"{FLOOR}+ dropbacks in both seasons unless said. Rates per 100 dropbacks.", "")  # fmt: skip

# ---- 1. the league by season
both = c("sack_e0").is_not_null() & c("sack_e1").is_not_null()
lg = (parts.group_by("season").agg(
        dropbacks=pl.len(), pressure=100 * c("pressure_y").mean(), sacks=100 * c("sack_y").mean(),
        sacks_per_pressure=100 * c("sack_y").filter(c("pressure_y") == 1).sum()
        / (c("pressure_y") == 1).sum(),
        e0=100 * c("sack_e0").filter(both).mean(), e1=100 * c("sack_e1").filter(both).mean(),
        sack_with_both=100 * c("sack_y").filter(both).mean(),
        e1_miss_pressured=100 * (c("sack_y") - c("sack_e1")).filter(both & (c("pressure_y") == 1)).mean(),
        e1_miss_clean=100 * (c("sack_y") - c("sack_e1")).filter(both & (c("pressure_y") == 0)).mean(),
      ).sort("season"))  # fmt: skip
say("== 1. The league by season (per 100 dropbacks; e1_miss = actual sacks minus E1)", table(lg), "")

# ---- per QB-season sums, with odd and even weeks for the split halves
qs = (parts.drop_nulls("passer_id").group_by("passer_id", "season").agg(
        db=pl.len(), sdb=both.sum(), sacks=c("sack_y").sum(), press=c("pressure_y").sum(),
        after=c("after_part").sum(), ppart=c("pressure_part").sum(),
        team=c("posteam").mode().first(), teams=c("posteam").n_unique(),
        after_odd=c("after_part").filter(c("week") % 2 == 1).sum(),
        after_even=c("after_part").filter(c("week") % 2 == 0).sum(),
        db_odd=(c("week") % 2 == 1).sum(), db_even=(c("week") % 2 == 0).sum(),
        sacks_odd=c("sack_y").filter(c("week") % 2 == 1).sum(),
        sacks_even=c("sack_y").filter(c("week") % 2 == 0).sum(),
      ).filter(c("db") >= FLOOR)
      .with_columns(sr=100 * c("sacks") / c("db"), ap=100 * c("after") / c("sdb"),
                    pp=100 * c("ppart") / c("sdb"), spp=100 * c("sacks") / c("press"),
                    ap_odd=100 * c("after_odd") / c("db_odd"), ap_even=100 * c("after_even") / c("db_even"),
                    sr_odd=100 * c("sacks_odd") / c("db_odd"), sr_even=100 * c("sacks_even") / c("db_even"))
      .join(names, on="passer_id", how="left"))  # fmt: skip
MEASURES = {"sr": "sacks per dropback", "ap": "after-pressure part", "pp": "pressure part",
            "spp": "sacks per pressure"}  # fmt: skip
nxt = qs.select("passer_id", (c("season") - 1).alias("season"), *[c(k).alias(f"{k}_n") for k in MEASURES],
                c("team").alias("team_n"), c("db").alias("db_n"))  # fmt: skip
pairs = qs.join(nxt, on=["passer_id", "season"]).with_columns(moved=c("team") != c("team_n"),
                                                              year=c("season") - c("rookie") + 1)


def sb(x, y) -> float:
    """Split-half reliability, stepped up to the full season (Spearman-Brown)."""
    h = r(x, y)
    return 2 * h / (1 + h) if np.isfinite(h) else float("nan")


rel = {}
for s in range(2017, 2026):
    d = qs.filter(c("season") == s)
    rel[s] = (sb(d["ap_odd"], d["ap_even"]), sb(d["sr_odd"], d["sr_even"]), d.height)

# ---- 2-4. each pair's repeat, beside its ceiling, rank r, stayers and the young
rows = []
for s in range(2017, 2025):
    d = pairs.filter(c("season") == s)
    st = d.filter(~c("moved"))
    old = d.filter(c("year") >= 3)
    rows.append({
        "pair": f"{s}-{str(s + 1)[2:]}", "qbs": d.height, "movers": int(d["moved"].sum()),
        "young": int((d["year"] <= 2).sum()),
        "sacks_db": r(d["sr"], d["sr_n"]), "after": r(d["ap"], d["ap_n"]),
        "press_part": r(d["pp"], d["pp_n"]), "sacks_press": r(d["spp"], d["spp_n"]),
        "after_rank": spearman(d["ap"], d["ap_n"]),
        "after_stayers": r(st["ap"], st["ap_n"]), "after_year3plus": r(old["ap"], old["ap_n"]),
        "after_ceiling": float(np.sqrt(max(rel[s][0], 0) * max(rel[s + 1][0], 0))),
        "rel_after_a": rel[s][0], "rel_after_b": rel[s + 1][0],
        "rel_sacks_a": rel[s][1], "rel_sacks_b": rel[s + 1][1],
    })  # fmt: skip
pt = pl.DataFrame(rows)
say("== 2-4. Each season pair: plain r with next season (sacks_db, after, press_part, "
    "sacks_press), the after part's rank r, stayers only, QBs in year 3+ only (young = in their "
    "first or second season in the first year); rel_* = within-season reliability (odd against "
    "even weeks, stepped up to a season) in the first (a) and second (b) season; after_ceiling = "
    "the most r could be given those reliabilities", table(pt), "")  # fmt: skip

# ---- 2. chance: 31 QBs drawn from the other pairs, each season's mean taken out
other = pairs.filter(c("season") < 2024).with_columns(
    *[(c(k) - c(k).mean().over("season")).alias(k) for k in ("sr", "ap")],
    *[(c(f"{k}_n") - c(f"{k}_n").mean().over("season")).alias(f"{k}_n") for k in ("sr", "ap")])  # fmt: skip
n = pairs.filter(c("season") == 2024).height
obs = pt.filter(c("pair") == "2024-25").row(0, named=True)
draws = {"sr": [], "ap": []}
for _ in range(5000):
    i = RNG.choice(other.height, n, replace=False)
    d = other[i]
    draws["sr"].append(r(d["sr"], d["sr_n"]))
    draws["ap"].append(r(d["ap"], d["ap_n"]))
p_sr = float(np.mean(np.array(draws["sr"]) <= obs["sacks_db"]))
p_ap = float(np.mean(np.array(draws["ap"]) <= obs["after"]))
both_low = float(np.mean((np.array(draws["sr"]) <= obs["sacks_db"]) & (np.array(draws["ap"]) <= obs["after"])))
say(f"== 2. Chance: {n} QBs drawn 5,000 times from the 2017-2023 pairs ({other.height} pairs)",
    f"  the after part: r {np.mean(draws['ap']):.2f} on average (90%: {np.quantile(draws['ap'], .05):.2f} "
    f"to {np.quantile(draws['ap'], .95):.2f}); as low as {obs['after']:.2f} in {100 * p_ap:.1f}% of draws",
    f"  sacks per dropback: r {np.mean(draws['sr']):.2f} on average (90%: {np.quantile(draws['sr'], .05):.2f} "
    f"to {np.quantile(draws['sr'], .95):.2f}); as low as {obs['sacks_db']:.2f} in {100 * p_sr:.1f}% of draws",
    f"  both as low at once: {100 * both_low:.1f}% of draws", "")  # fmt: skip

# ---- 3. outliers: the 2024-25 QBs, and r leaving each out
d = pairs.filter(c("season") == 2024).sort("ap")
loo = [r(d["ap"].filter(np.arange(d.height) != k), d["ap_n"].filter(np.arange(d.height) != k))
       for k in range(d.height)]  # fmt: skip
d = d.with_columns(r_without=pl.Series(loo), change=pl.Series(loo) - obs["after"])
show = d.select("name", "team", "team_n", "year", "db", "db_n", c("sr").alias("sacks_24"),
                c("sr_n").alias("sacks_25"), c("ap").alias("after_24"), c("ap_n").alias("after_25"),
                "r_without", "change").sort("change", descending=True)  # fmt: skip
top = show.head(3)["name"].to_list()
keep = ~d["name"].is_in(top)
r3 = r(d["ap"].filter(keep), d["ap_n"].filter(keep))
say("== 3. The 2024-25 QBs (after part and sacks per 100 dropbacks; year = his NFL season in 2024; "
    "r_without = the after part's r leaving him out; sorted by how much he pulls r down)", table(show),
    f"  without the three that pull it down most ({', '.join(top)}): r {r3:.2f}", "")  # fmt: skip

# ---- 4b. 300+ dropbacks both seasons
for fl in (300,):
    dd = pairs.filter((c("db") >= fl) & (c("db_n") >= fl))
    say(f"== 4b. QBs with {fl}+ dropbacks both seasons: the after part's r by pair",
        "  " + "; ".join(f"{s}-{str(s + 1)[2:]} {r(g['ap'], g['ap_n']):+.2f} ({g.height})"
                         for (s,), g in sorted(dd.group_by("season"), key=lambda t: t[0][0])), "")  # fmt: skip

# ---- 5. the vault's scoring: the after part against the plain sack numbers, same season
rows = []
for s in range(2017, 2026):
    g = qs.filter(c("season") == s)
    rows.append({"season": s, "qbs": g.height, "after~sacks_per_press": r(g["ap"], g["spp"]),
                 "after~sacks_db": r(g["ap"], g["sr"]), "press_part~sacks_db": r(g["pp"], g["sr"]),
                 "after_sd": g["ap"].std(), "sacks_db_sd": g["sr"].std()})  # fmt: skip
say("== 5. The vault's scoring: within each season, how the QB's after part lines up with his plain "
    "sack numbers (r across QBs), and how spread out QBs are (sd, per 100 dropbacks). 2025 is "
    "scored by the vault model (trained through 2024), the rest walk-forward", table(pl.DataFrame(rows)), "")  # fmt: skip

# ---- offenses: no model at all
off = (parts.group_by("posteam", "season").agg(sr=100 * c("sack_y").mean(), pr=100 * c("pressure_y").mean()))
on = off.select("posteam", (c("season") - 1).alias("season"), sr_n="sr", pr_n="pr")
op = off.join(on, on=["posteam", "season"])
say("== Offenses (32 teams, no model in it): sacks per dropback and pressures per dropback, r with "
    "next season",
    "  " + "; ".join(f"{s}-{str(s + 1)[2:]} sacks {r(g['sr'], g['sr_n']):+.2f} pressures {r(g['pr'], g['pr_n']):+.2f}"
                     for (s,), g in sorted(op.group_by("season"), key=lambda t: t[0][0])), "")  # fmt: skip

# ---- fairness checks, added after the first read of the results above
def drop_top(d: pl.DataFrame, k: int = 3) -> float:
    """r after leaving out the k QBs whose own removal raises it most (the same cherry-pick)."""
    base = r(d["ap"], d["ap_n"])
    idx = np.arange(d.height)
    gain = [r(d["ap"].filter(idx != j), d["ap_n"].filter(idx != j)) - base for j in range(d.height)]
    keep = ~pl.Series(idx).is_in(list(np.argsort(gain)[-k:]))
    return r(d["ap"].filter(keep), d["ap_n"].filter(keep))


say("== Fairness 1: the same cherry-pick in every pair (leave out the 3 QBs whose removal raises "
    "the after part's r most)",
    "  " + "; ".join(f"{s}-{str(s + 1)[2:]} {r(g['ap'], g['ap_n']):+.2f} -> {drop_top(g):+.2f}"
                     for (s,), g in sorted(pairs.group_by("season"), key=lambda t: t[0][0])), "")  # fmt: skip

eras = {"old provider (pairs 2017-18 to 2021-22)": (2017, 2021),
        "new provider (pairs 2023-24, 2024-25)": (2023, 2024)}  # fmt: skip
lines = []
for label, (a, b) in eras.items():
    g = pairs.filter(c("season").is_between(a, b)).with_columns(
        *[(c(k) - c(k).mean().over("season")).alias(k) for k in ("sr", "ap", "pp", "spp")],
        *[(c(f"{k}_n") - c(f"{k}_n").mean().over("season")).alias(f"{k}_n") for k in ("sr", "ap", "pp", "spp")])  # fmt: skip
    lines.append(f"  {label}, {g.height} pairs: " + "; ".join(
        f"{MEASURES[k]} {r(g[k], g[f'{k}_n']):+.2f}" for k in MEASURES))  # fmt: skip
say("== Fairness 2: pooled by provider (each season's mean out; 2022-23 crosses the change and is "
    "left out)", *lines)  # fmt: skip
skip = qs.filter(c("season") == 2023).join(
    qs.filter(c("season") == 2025).select("passer_id", ap_25="ap"), on="passer_id")
say(f"  2023 to 2025, skipping 2024 ({skip.height} QBs): after part r {r(skip['ap'], skip['ap_25']):+.2f}", "")

report_dir().mkdir(parents=True, exist_ok=True)
(report_dir() / "spot_check.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
