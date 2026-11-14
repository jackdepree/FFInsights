"""snap-leverage exploration (2026-11-14): H48 (which positions carry the variance in high-stakes
plays) and H49 (does a team's scheme change that).

H48, two readings, high-stakes plays (top fifth by leverage) against ordinary ones, 2016-2024:
(a) Where the ball goes: the spread of WPA (percentage points of win chance) on plays thrown to,
    or run by, each offensive position (the passer for every pass).
(b) Who is on the field: how much a play's WPA depends on *which player* holds each position.
    Ridge regression of each play's WPA on every player on the field (offense and defense
    columns apart) plus each team-season's offense and defense, fitted separately on odd and
    even weeks. A position's player spread is the square root of the covariance of its players'
    two estimates (noise doesn't repeat across halves), less the same from a null that shuffles
    WPA among each offense team-season's plays (5 shuffles). Players with 150+ snaps of the kind
    in each half. Ordinary plays are subsampled to the high-stakes count, so both kinds have the
    same noise.
H49: (b) on high-stakes plays, offense positions, split by the offense's pass rate over expected
    (each team-season's passes less pace's expected pass chance) above and below the median;
    the difference in each position's spread against 10 random splits of team-seasons.
Writes positions.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/positions.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
from scipy import sparse
from scipy.sparse.linalg import lsqr

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
HERE = Path(__file__).parent
SEASONS = list(range(2016, 2025))
GROUP = {"QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE", "C": "OL", "LT": "OL", "RT": "OL",
         "LG": "OL", "RG": "OL", "T": "OL", "G": "OL", "DE": "DL", "DT": "DL", "NT": "DL", "ILB": "LB",
         "OLB": "LB", "MLB": "LB", "CB": "CB", "FS": "S", "SS": "S"}
ORDER = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S"]
ALPHA = 200.0
MIN_SNAPS = 150


def load() -> tuple[pl.DataFrame, pl.DataFrame]:
    zone = get_config().zone("interim") / "snap-leverage"
    plays = pl.read_parquet(zone / "plays.parquet").select(
        "game_id", "play_id", "season", "week", "posteam", "defteam", "li", "hi", "wpa", "pass", "rush",
        "pcf_xpass", "receiver_player_id", "rusher_player_id", "passer_player_id",
    )
    of = read_part("player_play", "on_field", seasons=SEASONS).select("game_id", "play_id", "side", "gsis_id", "position").collect()
    of = of.unique(["game_id", "play_id", "gsis_id"]).with_columns(group=c("position").replace_strict(GROUP, default=None)).filter(c("group").is_not_null())
    return plays, of


def fit(pl_plays: pl.DataFrame, of: pl.DataFrame) -> pl.DataFrame:
    """Ridge estimates per (player, side), with the snaps behind each."""
    p = pl_plays.with_row_index("r")
    x = of.join(p.select("game_id", "play_id", "r", "posteam", "defteam", "season"), on=["game_id", "play_id"])
    x = x.with_columns(key=pl.concat_str("gsis_id", "side", separator="|"))
    keys = x["key"].unique().sort()
    kid = pl.DataFrame({"key": keys, "j": np.arange(len(keys))})
    x = x.join(kid, on="key")
    ts_o = p.select(k=pl.concat_str("posteam", "season", separator="o")).to_series()
    ts_d = p.select(k=pl.concat_str("defteam", "season", separator="d")).to_series()
    tks = pl.concat([ts_o, ts_d]).unique().sort()
    tid = {k: i for i, k in enumerate(tks.to_list())}
    n, J, T = p.height, len(keys), len(tks)
    rows = np.concatenate([x["r"].to_numpy(), np.arange(n), np.arange(n)])
    cols = np.concatenate([x["j"].to_numpy(), J + np.array([tid[k] for k in ts_o.to_list()]), J + np.array([tid[k] for k in ts_d.to_list()])])
    A = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, J + T))
    y = p["wpa"].to_numpy() * 100
    b = lsqr(A, y - y.mean(), damp=np.sqrt(ALPHA), atol=1e-8, btol=1e-8, iter_lim=3000)[0]
    snaps = x.group_by("key").agg(snaps=pl.len(), group=c("group").mode().first())
    return kid.with_columns(b=pl.Series(b[:J])).join(snaps, on="key")


def spread(odd: pl.DataFrame, even: pl.DataFrame, groups: list[str]) -> dict[str, float]:
    j = odd.join(even.select("key", b2="b", s2="snaps"), on="key").filter((c("snaps") >= MIN_SNAPS) & (c("s2") >= MIN_SNAPS))
    out = {}
    for g in groups:
        a = j.filter(c("group") == g)
        out[g] = float(np.cov(a["b"].to_numpy(), a["b2"].to_numpy())[0, 1]) if a.height >= 20 else float("nan")
        out[g + "_n"] = a.height
    return out


def halves(plays: pl.DataFrame, of: pl.DataFrame, groups: list[str], shuffle: int | None = None) -> dict[str, float]:
    if shuffle is not None:
        rng = np.random.default_rng(shuffle)
        plays = plays.with_columns(k=pl.concat_str("posteam", "season")).with_columns(
            wpa=pl.Series(np.empty(plays.height)) if False else c("wpa")
        )
        parts = []
        for _, d in plays.group_by("k"):
            parts.append(d.with_columns(wpa=pl.Series(rng.permutation(d["wpa"].to_numpy()))))
        plays = pl.concat(parts).drop("k")
    o = fit(plays.filter(c("week") % 2 == 1), of)
    e = fit(plays.filter(c("week") % 2 == 0), of)
    return spread(o, e, groups)


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    plays, of = load()
    hi = plays.filter(c("hi") == 1)
    lo = plays.filter(c("hi") == 0).sample(n=hi.height, seed=0)
    pos = of.select("game_id", "play_id", "gsis_id", "group")
    say("H48 (a): where the ball goes. Spread (sd) of WPA, points of win chance, per play")
    say("kind | high-stakes sd (plays) | ordinary sd (plays) | ratio")
    for nm, idc, filt in (("pass, by the passer (QB)", "passer_player_id", c("pass") == 1),
                          ("target WR", "receiver_player_id", c("pass") == 1), ("target TE", "receiver_player_id", c("pass") == 1),
                          ("target RB", "receiver_player_id", c("pass") == 1), ("run by RB", "rusher_player_id", c("rush") == 1),
                          ("run by QB", "rusher_player_id", c("rush") == 1)):
        want = nm.split()[-1].strip("()")
        res = []
        for d in (hi, plays.filter(c("hi") == 0)):
            z = d.filter(filt).join(pos, left_on=["game_id", "play_id", idc], right_on=["game_id", "play_id", "gsis_id"]).filter(c("group") == want)
            res.append((z["wpa"].std() * 100, z.height))
        say(f"  {nm:26s} | {res[0][0]:.2f} ({res[0][1]:,}) | {res[1][0]:.2f} ({res[1][1]:,}) | {res[0][0] / res[1][0]:.2f}")
    say(f"  every high-stakes play: sd {hi['wpa'].std() * 100:.2f}; every ordinary play: {plays.filter(c('hi') == 0)['wpa'].std() * 100:.2f}")
    say("")
    say("H48 (b): how much a play's WPA depends on which player holds each position (sd of player")
    say(f"effects, points of win chance per snap; split-half covariance less a shuffled null; ridge alpha {ALPHA:.0f}, {MIN_SNAPS}+ snaps per half)")
    out = {}
    for nm, d in (("high-stakes", hi), ("ordinary", lo)):
        real = halves(d, of, ORDER)
        nulls = [halves(d, of, ORDER, shuffle=k) for k in range(5)]
        out[nm] = (real, nulls)
    say("group | high-stakes: sd (players) | null sd | ordinary: sd (players) | null sd")
    for g in ORDER:
        cells = []
        for nm in ("high-stakes", "ordinary"):
            real, nulls = out[nm]
            nv = float(np.nanmean([z[g] for z in nulls]))
            sig = real[g] - nv
            cells.append(f"{np.sign(sig) * np.sqrt(abs(sig)):+.3f} ({real[g + '_n']}) | {np.sign(nv) * np.sqrt(abs(nv)):.3f}")
        say(f"  {g:2s} | " + " | ".join(cells))
    say("  (a negative value means the players' two halves agree less than the null's: no player signal)")
    say("")
    # H49: scheme split, offense positions, high-stakes plays
    say("H49: high-stakes plays, offense positions, by the offense's pass rate over expected (team-season)")
    poe = plays.group_by("posteam", "season").agg(poe=(c("pass") - c("pcf_xpass")).mean())
    med = poe["poe"].median()
    heavy = poe.filter(c("poe") > med).select("posteam", "season")
    off = ["QB", "RB", "WR", "TE", "OL"]

    def split(teams: pl.DataFrame) -> dict[str, float]:
        a = hi.join(teams, on=["posteam", "season"], how="semi")
        b = hi.join(teams, on=["posteam", "season"], how="anti")
        ra, rb = halves(a, of, off), halves(b, of, off)
        return {g: (np.sign(ra[g]) * np.sqrt(abs(ra[g]))) - (np.sign(rb[g]) * np.sqrt(abs(rb[g]))) for g in off} | {f"{g}_a": ra[g] for g in off} | {f"{g}_b": rb[g] for g in off}

    real = split(heavy)
    rng = np.random.default_rng(1)
    null = []
    for _ in range(10):
        pick = poe.sample(n=heavy.height, seed=int(rng.integers(1e9))).select("posteam", "season")
        null.append(split(pick))
    say("group | pass-heavy sd | run-heavy sd | difference | random splits: 90% range of the difference")
    for g in off:
        dist = np.array([z[g] for z in null])
        lo5, hi95 = np.nanpercentile(dist, [5, 95])
        ra, rb = real[f"{g}_a"], real[f"{g}_b"]
        say(f"  {g:2s} | {np.sign(ra) * np.sqrt(abs(ra)):+.3f} | {np.sign(rb) * np.sqrt(abs(rb)):+.3f} | {real[g]:+.3f} | {lo5:+.3f} to {hi95:+.3f}")
    say("  (raw split-half spreads, no shuffled-WPA null subtracted; the random splits are the null)")
    (HERE / "positions.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
