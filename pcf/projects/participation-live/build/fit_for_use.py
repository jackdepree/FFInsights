"""Fit for use (the brief's goal 3): the measures higher layers will build from the estimates,
against the same measures built from the true lineups, 2019-2024.

1. **Each player's on-field plus-minus** (player-pace's: his team's pass rate over expected and
   pace over expected with him on minus with him off, weighted on x off / team snaps), per player-
   season, for players with at least 20 weight in the truth: the correlation of the estimate's
   with the truth's, and the mean miss. Built the same way for every version on the grid's snaps
   (a defender's rates are the opposing offense's), with the on-field weight 1/0 for a lineup and
   the chance itself for `chances` (a player 60% likely on counts 0.6 on and 0.4 off).
2. **Personnel per play** (offense: backs and tight ends on the field, "11" = 1 back, 1 tight end):
   the share of plays whose estimated personnel is right, and each team-game's 11 and 12 rates.

Reads the backtest's scored lineups (`reconstruct.cache_dir()/scored_2019_2024.parquet`) and the
play tables through a retrospective view (the answer key is allowed here: this is scoring).
Writes fit_for_use.txt.
"""

# ruff: noqa: E501
from pathlib import Path

import numpy as np
import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.participation_live import reconstruct

c = pl.col
HERE = Path(__file__).parent
SEASONS = list(range(2019, 2025))
LINEUPS = {
    "truth": "on",
    "sequence chances": "p_sequence",
    "sequence, snap-matched": "best_sequence",
    "sequence, likeliest": "top_sequence",
    "sequence, snap-matched, no mix": "best_sequence_nomix",
    "sequence, likeliest, no mix": "top_sequence_nomix",
    "history chances": "p_history",
    "history, snap-matched": "best_history",
    "history, likeliest": "top_history",
    "share chances": "p_share",
    "share, snap-matched": "best_share",
    "share, likeliest": "top_share",
}
MIN_WEIGHT = 20.0
KEYS = ["game_id", "side", "team", "gsis_id"]

S = pl.read_parquet(reconstruct.cache_dir() / "scored_2019_2024.parquet").filter(c("full_truth"))
lines = []

# ---------- 1. plus-minus ----------
plays = []
for season in SEASONS:
    gw = Gateway(TableSource(seasons=[season]))
    view = gw.view(END_OF_TIME, "retrospective", {"play": ("pbp", "pace")})
    p = view.table("play", seasons=[season]).select("game_id", c("play_id").cast(pl.Int64), "pcf_pass_oe", "pace_oe")
    plays.append(p)
P = pl.concat(plays)
G = S.join(P, on=["game_id", "play_id"], how="left")


def plus_minus(w: pl.Expr, x: str) -> pl.DataFrame:
    """Per player-season: the weighted mean over games of (mean x on - mean x off), and the
    summed weight (on x off / snaps), with on-field weight `w` per snap."""
    d = G.filter(c(x).is_not_null()).with_columns(w=w.cast(pl.Float64))
    g = d.group_by(*KEYS).agg(
        season=c("season").first(), n=pl.len(), sw=c("w").sum(), swx=(c("w") * c(x)).sum(), sx=c(x).sum()
    ).with_columns(
        pm=c("swx") / c("sw") - (c("sx") - c("swx")) / (c("n") - c("sw")),
        wt=c("sw") * (c("n") - c("sw")) / c("n"),
    ).filter(c("wt") > 1e-9)  # fmt: skip
    return g.group_by("gsis_id", "season").agg(
        pm=(c("pm") * c("wt")).sum() / c("wt").sum(), wt=c("wt").sum()
    )


groups = S.group_by("gsis_id", "season").agg(group=c("group").mode().first())
lines.append("1. Player-season on-field plus-minus, estimate against truth (players with 20+ weight in the truth, 2019-2024):")
rows = []
pm = {(name, x): plus_minus(c(col), x) for name, col in LINEUPS.items() for x in ("pcf_pass_oe", "pace_oe")}
for name in LINEUPS:
    if name == "truth":
        continue
    r = {"version": name}
    for x, short in (("pcf_pass_oe", "proe"), ("pace_oe", "pace")):
        t = pm[("truth", x)].filter(c("wt") >= MIN_WEIGHT)
        j = t.join(pm[(name, x)], on=["gsis_id", "season"], suffix="_e", how="left")
        r[f"{short}_players"] = j.height
        r[f"{short}_missing"] = j["pm_e"].null_count()
        jj = j.drop_nulls("pm_e")
        r[f"{short}_r"] = float(np.corrcoef(jj["pm"], jj["pm_e"])[0, 1])
        r[f"{short}_mean_miss"] = float((jj["pm"] - jj["pm_e"]).abs().mean())
        r[f"{short}_sd_truth"] = float(t["pm"].std())
        if short == "proe":
            jg = jj.join(groups, on=["gsis_id", "season"], how="left")
            for grp in ("RB", "TE", "WR", "DL", "LB", "DB"):
                z = jg.filter(c("group") == grp)
                r[f"proe_r_{grp}"] = float(np.corrcoef(z["pm"], z["pm_e"])[0, 1]) if z.height > 30 else None
    rows.append(r)
with pl.Config(tbl_cols=30, tbl_width_chars=400, float_precision=3, tbl_rows=30):
    lines.append(str(pl.DataFrame(rows)))

# ---------- 2. personnel ----------
off = S.filter(c("side") == "offense")
pers = {}
for name, col in LINEUPS.items():
    if col.startswith("p_"):
        continue
    on = off.filter(c(col) == 1) if col == "on" else off.filter(c(col))
    pers[name] = on.group_by("game_id", "play_id", "team").agg(
        rb=(c("group") == "RB").sum(), te=(c("group") == "TE").sum()
    ).with_columns(code=c("rb").cast(pl.String) + c("te").cast(pl.String))
t = pers["truth"]
lines += ["", "2. Offensive personnel per play (backs and tight ends), estimate against truth:"]
rows = []
for name in pers:
    if name == "truth":
        continue
    j = t.join(pers[name], on=["game_id", "play_id", "team"], suffix="_e")
    tg = j.group_by("game_id", "team").agg(r11=(c("code") == "11").mean(), r11_e=(c("code_e") == "11").mean(), r12=(c("code") == "12").mean(), r12_e=(c("code_e") == "12").mean())
    rows.append({
        "lineup": name, "plays": j.height, "personnel_right": float((j["code"] == j["code_e"]).mean()),
        "backs_right": float((j["rb"] == j["rb_e"]).mean()), "tight_ends_right": float((j["te"] == j["te_e"]).mean()),
        "no_back_est": float((j["rb_e"] == 0).mean()), "no_back_true": float((j["rb"] == 0).mean()),
        "team_game_11_rate_r": float(np.corrcoef(tg["r11"], tg["r11_e"])[0, 1]),
        "team_game_12_rate_r": float(np.corrcoef(tg["r12"], tg["r12_e"])[0, 1]),
        "11_rate_true": float(tg["r11"].mean()), "11_rate_est": float(tg["r11_e"].mean()),
    })  # fmt: skip
with pl.Config(tbl_cols=30, tbl_width_chars=400, float_precision=3):
    lines.append(str(pl.DataFrame(rows)))
text = "\n".join(lines)
(HERE / "fit_for_use.txt").write_text(text, encoding="utf-8")
print(text)
