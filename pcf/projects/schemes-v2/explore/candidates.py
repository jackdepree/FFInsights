"""Scheme against scheme, option E (CEO, 2026-11-09): the CEO's own candidate matchups (H16).

Four pairings, each with its direction fixed before running (in the offense's EPA per play beyond
both units' strength, F20's residual):
- E1. A two-high (cover-2 family) defense against an offense that throws deep often: the defense
      does well, so the product (two-high × deep rate) has a NEGATIVE coefficient.
- E2. An offense that spreads the ball across players against a defense that loads the box: the
      offense does well, so (target spread × box over expected) is POSITIVE.
- E3. A blitz-heavy defense against a short-throwing offense: the defense does poorly, so the
      offense gains when blitz is high and depth is low: (blitz × throw depth) is NEGATIVE.
- E4. A heavy defensive line against an offense that runs more than expected: the defense does
      well, so the offense loses when weight is high and pass rate over expected is low:
      (DL weight × pass rate over expected) is POSITIVE.
Variants (reported, not counted): E1 with throw depth instead of deep rate; E2 with the spread
across position groups (WR, TE, RB) instead of players.

Measures, per team-game, 2016-2024 regular season:
- deep rate, throw depth, pass rate over expected, two-high, blitz, box over expected: F2's
  tendencies (interim team_game; two-high from 2018);
- target spread: the effective number of receivers, 1 / sum of squared target shares (all targets);
  the position version uses `players.position_group`;
- DL weight: the mean listed weight of the defensive linemen on the field (participation's
  `defense_players` joined to `players`, position group DL), averaged over the game's plays. The
  weight is the player's current listing, not dated: fine for a discovery look.
Each unit's measure comes from its earlier games that season (3+), standardized within the season;
a ceiling version uses the season's other games.
The test per pairing: residual ~ offense measure + defense measure + their product (t), and a null
from defenses shuffled within the week (1,000 times), one-sided in the stated direction. With four
pairings the bar is 1.25% one-sided each (5% overall). Also one combined score: the four products,
signed as stated, summed.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/candidates.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from matchups import residuals

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
RNG = np.random.default_rng(20261112)
SHUFFLES = 1000
SEASONS = range(2016, 2025)
RAW = get_config().zone("raw") / "nflverse"
# name: (offense measure, defense measure, expected sign, counted)
PAIRS = {
    "E1 two-high × deep rate": ("deep_rate", "d_two_high", -1, True),
    "E2 target spread × box": ("spread", "d_box_oe", +1, True),
    "E3 blitz × throw depth": ("adot", "d_blitz", -1, True),
    "E4 DL weight × pass over expected": ("proe", "dl_weight", +1, True),
    "  E1 variant: two-high × throw depth": ("adot", "d_two_high", -1, False),
    "  E2 variant: position spread × box": ("pos_spread", "d_box_oe", +1, False),
}


def measures() -> pl.DataFrame:
    tg = pl.read_parquet(get_config().zone("interim") / "schemes_v2" / "team_game.parquet").filter(
        c("season") >= 2016
    )
    players = pl.read_parquet(RAW / "players" / "players.parquet").select(
        "gsis_id", "position_group", "weight"
    )
    spread, dl = [], []
    for s in SEASONS:
        p = (
            read_part("play", "pbp", [s])
            .select("game_id", "season_type", "posteam", "receiver_player_id", "pass_attempt")
            .collect()
            .filter(
                (c("season_type") == "REG")
                & (c("pass_attempt") == 1)
                & c("receiver_player_id").is_not_null()
            )
        )
        p = p.join(
            players.select(c("gsis_id").alias("receiver_player_id"), "position_group"),
            on="receiver_player_id",
            how="left",
        )

        def eff(key, p=p):
            return (
                p.group_by("game_id", "posteam", key)
                .len()
                .with_columns(sh=c("len") / c("len").sum().over("game_id", "posteam"))
                .group_by("game_id", "posteam")
                .agg((1 / (c("sh") ** 2).sum()).alias("v"))
            )

        spread.append(
            eff("receiver_player_id")
            .rename({"v": "spread"})
            .join(eff("position_group").rename({"v": "pos_spread"}), on=["game_id", "posteam"])
            .rename({"posteam": "team"})
        )
        part = (
            read_part("play", "participation", [s])
            .select("game_id", "play_id", "defense_players")
            .collect()
            .filter(c("defense_players").is_not_null() & (c("defense_players") != ""))
        )
        side = (
            read_part("play", "pbp", [s])
            .select("game_id", "play_id", "defteam", "season_type")
            .collect()
            .filter(c("season_type") == "REG")
        )
        w = (
            part.join(side, on=["game_id", "play_id"])
            .with_columns(pid=c("defense_players").str.split(";"))
            .explode("pid")
            .join(
                players.filter(c("position_group") == "DL").select(
                    c("gsis_id").alias("pid"), "weight"
                ),
                on="pid",
            )
            .group_by("game_id", "play_id", "defteam")
            .agg(c("weight").mean())
            .group_by("game_id", "defteam")
            .agg(dl_weight=c("weight").mean())
            .rename({"defteam": "team"})
        )
        dl.append(w)
    return (
        tg.select(
            "game_id",
            "season",
            "week",
            "team",
            "deep_rate",
            "adot",
            "proe",
            "d_two_high",
            "d_blitz",
            "d_box_oe",
        )
        .join(pl.concat(spread), on=["game_id", "team"], how="left")
        .join(pl.concat(dl), on=["game_id", "team"], how="left")
    )


def windows(m: pl.DataFrame, cols: list[str]) -> dict[str, pl.DataFrame]:
    m = m.sort("team", "season", "week")
    grp = ["team", "season"]
    out = {}
    for w in ("pre", "lo"):
        ex = []
        for x in cols:
            v = c(x).fill_nan(None)
            k = v.is_not_null().cast(pl.Int32)
            if w == "pre":
                sm, n = (
                    v.fill_null(0).cum_sum().over(grp) - v.fill_null(0),
                    k.cum_sum().over(grp) - k,
                )
                ex.append(pl.when(n >= 3).then(sm / n).alias(x))
            else:
                sm, n = v.fill_null(0).sum().over(grp) - v.fill_null(0), k.sum().over(grp) - k
                ex.append(pl.when(n >= 3).then(sm / n).alias(x))
        t = m.select("game_id", "season", "team", *ex)
        out[w] = t.with_columns(
            *[((c(x) - c(x).mean().over("season")) / c(x).std().over("season")) for x in cols]
        )
    return out


def ols_t(y, cols):
    X = np.column_stack([np.ones(len(y)), *cols])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    cov = np.linalg.inv(X.T @ X) * (e @ e) / (len(y) - X.shape[1])
    return b, b / np.sqrt(np.diag(cov))


def run(sides: pl.DataFrame, label: str) -> None:
    wk = (sides["season"] * 100 + sides["week"]).to_numpy()
    idx = np.arange(sides.height)
    perms = []
    for _ in range(SHUFFLES):
        p = idx.copy()
        for k in np.unique(wk):
            w = idx[wk == k]
            p[w] = RNG.permutation(w)
        perms.append(p)
    y = sides["resid"].to_numpy()
    print(f"\n== {label}: {sides.height:,} sides")
    print(
        f"   {'pairing':<38} {'expected':>8} {'per sd²':>9} {'t':>6} {'n':>6}  shuffled as far in the expected direction"
    )
    combo, combo_null = np.zeros(len(y)), np.zeros((SHUFFLES, len(y)))
    for name, (o, d, sign, counted) in PAIRS.items():
        zo, zd = sides[f"o_{o}"].to_numpy(), sides[f"d_{d}"].to_numpy()
        ok = ~(np.isnan(zo) | np.isnan(zd) | np.isnan(y))
        b, t = ols_t(y[ok], [zo[ok], zd[ok], zo[ok] * zd[ok]])
        nt = []
        for p in perms[:SHUFFLES]:
            zdp = zd[p]
            ok2 = ~(np.isnan(zo) | np.isnan(zdp) | np.isnan(y))
            nt.append(ols_t(y[ok2], [zo[ok2], zdp[ok2], zo[ok2] * zdp[ok2]])[1][3])
        nt = np.array(nt)
        pv = np.mean(sign * nt >= sign * t[3])
        flag = "  ← past the bar (1.25%)" if counted and pv <= 0.0125 else ""
        print(
            f"   {name:<38} {'+' if sign > 0 else '−':>8} {b[3]:>+9.4f} {t[3]:>6.1f} {ok.sum():>6}  {pv:.1%}{flag}"
        )
        if counted:
            combo += sign * np.nan_to_num(zo * zd)
            for k, p in enumerate(perms):
                combo_null[k] += sign * np.nan_to_num(zo * zd[p])
    r = float(np.corrcoef(combo, y)[0, 1])
    rn = np.array([np.corrcoef(combo_null[k], y)[0, 1] for k in range(SHUFFLES)])
    print(
        f"   combined (the four, signed as the CEO expects): r {r:+.3f}; shuffled at or above {np.mean(rn >= r):.1%}; share of F20's ceiling (9.2%): {max(r, 0) ** 2 / 0.092:.1%}"
    )


def main() -> None:
    m = measures()
    off_cols = ["deep_rate", "adot", "proe", "spread", "pos_spread"]
    def_cols = ["d_two_high", "d_blitz", "d_box_oe", "dl_weight"]
    print(
        "coverage per measure (team-games with a value):",
        {x: int(m[x].is_not_null().sum()) for x in off_cols + def_cols},
    )
    w = windows(m, off_cols + def_cols)
    res = residuals()
    for key, label in (
        ("pre", "Earlier games only, 3+ (what a forecast could know)"),
        ("lo", "The season's other games (ceiling version)"),
    ):
        t = w[key]
        o = t.select("game_id", c("team").alias("off"), *[c(x).alias(f"o_{x}") for x in off_cols])
        d = t.select("game_id", c("team").alias("dfn"), *[c(x).alias(f"d_{x}") for x in def_cols])
        sides = res.join(o, on=["game_id", "off"]).join(d, on=["game_id", "dfn"])
        run(sides, label)


if __name__ == "__main__":
    main()
