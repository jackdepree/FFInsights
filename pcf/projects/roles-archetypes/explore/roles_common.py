"""Shared feature code for the roles exploration (EXPLORATION.md, "The terms"). Explore code only."""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config

c = pl.col
CFG = get_config()
O = CFG.zone("interim") / "roles"
GROUPS = ["WR", "TE", "RB", "DL", "OLB", "ILB", "CB", "S"]
OFFENSE = {"WR", "TE", "RB"}
KINDS, DOWNS, PERS, ZONES = ("pass", "run"), ("early", "late"), ("11", "12", "heavy", "other"), ("rz", "of")
CELLS = [f"{k}_{d}_{p}_{z}" for k in KINDS for d in DOWNS for p in PERS for z in ZONES]
MIN_SNAPS = 200


def logit(p):
    return np.log(p / (1 - p))


def _sum(df, pat):
    """His snaps and his team's plays over the cells that pass `pat`."""
    on = sum(df[f"n_{cell}"].to_numpy().astype(float) for cell in CELLS if pat(cell))
    team = sum(df[f"tn_{cell}"].to_numpy().astype(float) for cell in CELLS if pat(cell))
    return on, team


DIMS = {  # each dimension: (X, not X) as cell tests
    "run": (lambda x: x.startswith("run"), lambda x: x.startswith("pass")),
    "p11": (lambda x: "_11_" in x, lambda x: "_11_" not in x),
    "p12": (lambda x: "_12_" in x, lambda x: "_12_" not in x),
    "heavy": (lambda x: "_heavy_" in x, lambda x: "_heavy_" not in x),
    "late": (lambda x: "_late_" in x, lambda x: "_early_" in x),
    "rz": (lambda x: x.endswith("_rz"), lambda x: x.endswith("_of")),
}


def features(df: pl.DataFrame) -> pl.DataFrame:
    """Own-snap (raw and team-adjusted), on/off, usage (shrunk) and the 32 cell log-odds, per row."""
    n_all, t_all = _sum(df, lambda x: True)
    out = {"snap_share": logit((n_all + 1) / (t_all + 2))}
    for d, (isx, notx) in DIMS.items():
        nx, tx = _sum(df, isx)
        nn, tn = _sum(df, notx)
        out[f"own_{d}"] = nx / np.maximum(n_all, 1)
        out[f"adj_{d}"] = out[f"own_{d}"] - tx / np.maximum(t_all, 1)
        out[f"oo_{d}"] = logit((nx + 1) / (tx + 2)) - logit((nn + 1) / (tn + 2))
    for cell in CELLS:
        out[f"cell_{cell}"] = logit((df[f"n_{cell}"].to_numpy() + 1) / (df[f"tn_{cell}"].to_numpy() + 2))
    f = pl.DataFrame(out)
    return pl.concat([df.select("gsis_id", "team", "season", "side", "group", "half", "snaps", "games"), f], how="horizontal")


USAGE = {  # name: (numerator, denominator, prior weight)
    "tgt_per_pass": ("targets", "pass_snaps", 100), "adot": ("air", "air_n", 10), "deep": ("deep", "loc_n", 10),
    "behind": ("behind", "air_n", 10), "middle": ("middle", "loc_n", 10), "car_per_run": ("carries", "run_snaps", 100),
    "outside": ("outside", "run_loc_n", 10), "tkl_per_snap": ("tackles", "snaps", 100), "solo_share": ("solo", "tackles", 10),
    "tkl_depth": ("tackle_yds", "tackles", 10), "rush_per_pass": ("rush", "pass_snaps", 100), "pd_per_pass": ("pd", "pass_snaps", 100),
}


def usage(df: pl.DataFrame, ref: pl.DataFrame) -> pl.DataFrame:
    """Shrunk usage rates: each pulled toward its group's pooled rate (from `ref`) by its prior weight."""
    cols = {}
    for name, (num, den, k) in USAGE.items():
        pooled = ref.group_by("group").agg(m=c(num).sum() / c(den).sum().clip(1))
        mm = df.select("group").join(pooled, on="group", how="left")["m"].fill_null(0).to_numpy()
        cols[name] = (df[num].to_numpy().astype(float) + k * mm) / (df[den].to_numpy().astype(float) + k)
    return pl.DataFrame(cols)


def load(min_snaps: int = MIN_SNAPS, halves: bool = False) -> pl.DataFrame:
    """Player-team-season rows with 200+ snaps (full season), all features, and measurables."""
    cnt = pl.read_parquet(O / "counts.parquet")
    keep = cnt.filter((c("half") == "all") & (c("snaps") >= min_snaps)).select("gsis_id", "team", "season", "side")
    cnt = cnt.join(keep, on=["gsis_id", "team", "season", "side"], how="semi")
    if not halves:
        cnt = cnt.filter(c("half") == "all")
    ref = cnt.filter(c("half") == "all")
    f = features(cnt)
    u = usage(cnt, ref)
    m = pl.read_parquet(O / "measurables.parquet").unique("gsis_id")
    out = pl.concat([f, u, cnt.select("targets", "touches", "epa_tgt", "epa_touch", "pass_snaps", "run_snaps")], how="horizontal").join(m, on="gsis_id", how="left")
    gm = out.group_by("group").agg(c("height").mean().alias("hm"), c("weight").mean().alias("wm"), c("forty").mean().alias("fm"))
    out = out.join(gm, on="group").with_columns(
        forty_missing=c("forty").is_null().cast(pl.Float64), height=c("height").fill_null(c("hm")), weight=c("weight").fill_null(c("wm")),
        forty=c("forty").fill_null(c("fm"))).drop("hm", "wm", "fm")
    return out


OO = [f"oo_{d}" for d in DIMS]
ADJ = [f"adj_{d}" for d in DIMS]
OFF_USAGE = ["tgt_per_pass", "adot", "deep", "behind", "middle", "car_per_run", "outside"]
DEF_USAGE = ["tkl_per_snap", "solo_share", "tkl_depth", "rush_per_pass", "pd_per_pass"]
MEAS = ["height", "weight", "forty", "forty_missing"]
ROLE_TABLE = {
    "WR": ["adot", "tgt_per_pass", "middle", "oo_run", "snap_share"],
    "TE": ["oo_run", "tgt_per_pass", "adot", "snap_share"],
    "RB": ["car_per_run", "tgt_per_pass", "oo_late", "snap_share", "outside"],
    "DL": ["rush_per_pass", "tkl_per_snap", "oo_run", "snap_share"],
    "OLB": ["rush_per_pass", "pd_per_pass", "oo_run", "tkl_per_snap", "snap_share"],
    "ILB": ["tkl_per_snap", "tkl_depth", "oo_late", "pd_per_pass", "snap_share"],
    "CB": ["pd_per_pass", "tkl_depth", "oo_p11", "tkl_per_snap", "snap_share"],
    "S": ["tkl_depth", "tkl_per_snap", "pd_per_pass", "oo_heavy", "snap_share"],
}


def full_set(group: str, meas: bool = False) -> list[str]:
    us = OFF_USAGE if group in OFFENSE else DEF_USAGE
    return ["snap_share", *ADJ, *OO, *us, *(MEAS if meas else [])]


CELL_SET = [f"cell_{x}" for x in CELLS]
