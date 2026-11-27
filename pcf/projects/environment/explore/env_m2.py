"""Environment, method 2 (pre-registered in EXPLORATION.md before this ran; discovery only).

1. H124 (plays 2017-2024): the base model (situation, conditions, the offense's and defense's role mix from their
   previous season, the targeted receiver's own previous-season coordinates on passes) against the base plus the
   roles x wind and roles x rain terms. Walk-forward (train on 2017 to the season before), tested 2019-2024, scored on
   plays in 10+ mph wind or rain. Four kinds: passing (air yards, completion, EPA a dropback), rushing (EPA a run),
   pressure (a sack or QB hit on a dropback), defensive (EPA a play and pressure, through the defense's role mix).
2. H125 (team-games 2017-2024): pace (plays, seconds a play), and the schemes' tendencies, base (previous-8 means and
   the conditions) against the base plus role mix x conditions and the previous season's tendencies x conditions.
3. The spread of play outcomes: the SD of each play's EPA less the situation model's, in 15+ mph wind, rain and cold,
   against calm, dry and mild outdoor plays; 90% intervals from resampling games.
Roles are read from the team's previous season (a team's mix) and the receiver's previous season, so no part of the
game's own season is used (the mix misses players who joined: a stated limit).

Run from pcf/:  python projects/environment/explore/env_m2.py   (writes env_m2.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from env_common import Say, _part, games, team_games  # noqa: E402

from pcf.config import get_config

c = pl.col
RNG = np.random.default_rng(11)
say = Say(Path(__file__).with_name("env_m2_tuned.txt") if "--tuned" in sys.argv else Path(__file__).with_suffix(".txt"))
Z = [f"z{i}" for i in range(6)]
ROLES = get_config().zone("outputs") / "roles-archetypes/696a3f0b827f48549dfc9e3393655df1/history.parquet"


def role_mix() -> tuple[pl.DataFrame, pl.DataFrame]:
    r = pl.read_parquet(ROLES)
    mix = (r.group_by("team", "season", "side").agg([(c(z) * c("snaps")).sum() / c("snaps").sum() for z in Z])
           .with_columns(season=c("season") + 1))  # known for the next season
    own = r.filter(c("side") == "offense").sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first").select("gsis_id", season=c("season") + 1, **{f"r{z}": c(z) for z in Z})
    return mix, own


def plays(g: pl.DataFrame) -> pl.DataFrame:
    S = list(range(2017, 2025))
    p = _part("play", "pbp", ["game_id", "season", "season_type", "posteam", "defteam", "down", "ydstogo", "yardline_100", "score_differential", "qtr",
                               "qb_dropback", "pass_attempt", "rush_attempt", "sack", "qb_hit", "air_yards", "complete_pass", "epa", "receiver_player_id", "two_point_attempt"], S)
    p = p.filter((c("season_type") == "REG") & c("down").is_not_null() & c("epa").is_not_null() & (c("two_point_attempt").fill_null(0) == 0)
                 & ((c("qb_dropback") == 1) | (c("rush_attempt") == 1)))
    mix, own = role_mix()
    off = mix.filter(c("side") == "offense").select("team", "season", **{f"o{z}": c(z) for z in Z})
    de = mix.filter(c("side") == "defense").select("team", "season", **{f"d{z}": c(z) for z in Z})
    p = (p.join(g.select("game_id", "wind", "temp", "precip", "dome"), on="game_id", how="inner")
         .join(off, left_on=["posteam", "season"], right_on=["team", "season"], how="inner")
         .join(de, left_on=["defteam", "season"], right_on=["team", "season"], how="inner")
         .join(own, left_on=["receiver_player_id", "season"], right_on=["gsis_id", "season"], how="left"))
    return p.with_columns(cold=(50 - c("temp")).clip(0, None), wet=c("precip"), pressure=((c("sack") == 1) | (c("qb_hit") == 1)).cast(pl.Float64),
                          bad=(~c("dome") & ((c("wind") >= 10) | (c("precip") >= 0.02))).fill_null(False))


def design(x: pl.DataFrame, side: str, recv: bool, inter: bool) -> np.ndarray:
    f = lambda k: x[k].cast(pl.Float64).fill_null(0).to_numpy()  # noqa: E731
    cols = [np.ones(x.height)]
    cols += [(x["down"] == d).cast(pl.Float64).to_numpy() for d in (2, 3, 4)] + [f("ydstogo"), f("yardline_100"), np.clip(f("score_differential"), -21, 21)]
    cols += [(x["qtr"] == q).cast(pl.Float64).to_numpy() for q in (2, 3, 4)]
    cond = [f("wind"), f("cold"), f("wet"), f("dome")]
    cols += cond
    cols += [f(f"o{z}") for z in Z] + [f(f"d{z}") for z in Z]
    if recv:
        cols += [f(f"r{z}") for z in Z] + [x["rz0"].is_null().cast(pl.Float64).to_numpy()]
    if inter:
        base = [f(f"{side}{z}") for z in Z] + ([f(f"r{z}") for z in Z] if recv else [])
        cols += [b * w for b in base for w in (f("wind"), f("wet"))]
    return np.column_stack(cols)


TUNED = "--tuned" in sys.argv  # after the first run (2026-11-27): the penalty chosen inside the training seasons


def ridge_tuned(A, y, seas):
    """Pick the penalty on the last training season, then refit on all of them."""
    if not TUNED:
        return ridge(A, y)
    last = seas == seas.max()
    best = min((np.mean((y[last] - ridge(A[~last], y[~last], lam)(A[last])) ** 2), lam) for lam in (1.0, 10.0, 100.0, 1e3, 1e4, 1e5))[1]
    return ridge(A, y, best)


def ridge(A, y, lam=1.0):
    m, s = A[:, 1:].mean(0), A[:, 1:].std(0) + 1e-9
    B = np.column_stack([A[:, 0], (A[:, 1:] - m) / s])
    w = np.linalg.solve(B.T @ B + lam * np.eye(B.shape[1]), B.T @ y)
    return lambda X: np.column_stack([X[:, 0], (X[:, 1:] - m) / s]) @ w


def walk(x: pl.DataFrame, y: str, side: str, recv: bool) -> tuple[float, float, float, int]:
    e0, e1, gid = [], [], []
    for s in range(2019, 2025):
        tr, te = x.filter(c("season") < s), x.filter((c("season") == s) & c("bad"))
        if te.height == 0:
            continue
        for inter, acc in ((False, e0), (True, e1)):
            fit = ridge_tuned(design(tr, side, recv, inter), tr[y].cast(pl.Float64).to_numpy(), tr["season"].to_numpy())
            acc.append((te[y].cast(pl.Float64).to_numpy() - fit(design(te, side, recv, inter))) ** 2)
        gid.append(te["game_id"].to_numpy())
    if not e0:
        return np.nan, np.nan, np.nan, 0
    e0, e1, gid = np.concatenate(e0), np.concatenate(e1), np.concatenate(gid)
    u, inv = np.unique(gid, return_inverse=True)
    A, B = np.bincount(inv, e1), np.bincount(inv, e0)
    idx = RNG.integers(0, len(u), (1000, len(u)))
    gb = 1 - A[idx].sum(1) / B[idx].sum(1)
    return 1 - e1.sum() / e0.sum(), np.quantile(gb, 0.05), np.quantile(gb, 0.95), len(e0)


def fmt(r) -> str:
    return f"{r[0]:+.3%} ({r[1]:+.3%} to {r[2]:+.3%}; {r[3]:,} plays)"


def main() -> None:
    g = games()
    p = plays(g)
    say("# Environment, method 2 (2026-11-27)", "", f"Plays 2017-2024 with both sides' role mix: {p.height:,}; in 10+ mph wind or rain (outdoor): {p['bad'].mean():.1%}.", "")
    say("## H124: roles x wind and rain, beyond the conditions' average effects (tested 2019-2024, bad-weather plays)", "", "| Kind | Outcome | Gain from the role x weather terms (90%) |", "|---|---|---|")
    db = p.filter(c("qb_dropback") == 1)
    att = p.filter((c("pass_attempt") == 1) & (c("sack") == 0))
    run = p.filter(c("rush_attempt") == 1)
    spec = [("passing", "air yards an attempt", att.filter(c("air_yards").is_not_null()), "air_yards", "o", True),
            ("passing", "completion", att.filter(c("air_yards").is_not_null()), "complete_pass", "o", True),
            ("passing", "EPA a dropback", db, "epa", "o", False),
            ("rushing", "EPA a run", run, "epa", "o", False),
            ("pressure", "sack or QB hit a dropback", db, "pressure", "o", False),
            ("defensive", "EPA a play (defense's mix)", p, "epa", "d", False),
            ("defensive", "pressure (defense's mix)", db, "pressure", "d", False)]
    kinds = {}
    for kind, lab, x, y, side, recv in spec:
        r = walk(x, y, side, recv)
        kinds.setdefault(kind, []).append(r[1] > 0)
        say(f"| {kind} | {lab} | {fmt(r)} |")
    n = sum(any(v) for v in kinds.values())
    say("", f"Kinds with a clear gain: {n} of 4. H124 as worded (all four): {'held' if n == 4 else 'failed'}; side (any one): {'held' if n >= 1 else 'failed'}.", "")

    # H125: pace and schemes
    t_all = team_games()
    t = t_all.filter(c("season") >= 2017)
    mix, _ = role_mix()
    off = mix.filter(c("side") == "offense").select("team", "season", *Z)
    prev = t_all.group_by("team", "season").agg(p_oe=c("neutral_pass_oe").mean(), p_sg=c("shotgun_rate").mean()).with_columns(season=c("season") + 1)
    t = t.join(off, on=["team", "season"], how="inner").join(prev, on=["team", "season"], how="left").with_columns(
        cold=(50 - c("temp")).clip(0, None), bad=(~c("dome") & ((c("wind") >= 10) | (c("precip") >= 0.02) | (c("temp") <= 40))).fill_null(False))
    say("## H125: pace and schemes, roles and tendencies x conditions (tested 2019-2024, bad-weather games)", "", "| Outcome | Gain (90%) |", "|---|---|")
    COND = ["wind", "cold", "precip", "dome", "turf", "short_rest", "long_rest", "altitude", "primetime"]
    res125 = {}
    for o, lab in (("plays", "plays a game"), ("tempo_seconds", "seconds a play"), ("neutral_pass_oe", "neutral pass rate over expected"), ("shotgun_rate", "shotgun rate")):
        x = t.drop_nulls([o]).with_columns(c(f"{o}_prior").fill_null(c(o).mean()) if f"{o}_prior" in t.columns else pl.lit(0.0).alias(f"{o}_prior"),
                                           c(f"{o}_opp").fill_null(c(o).mean()) if f"{o}_opp" in t.columns else pl.lit(0.0).alias(f"{o}_opp"))
        if f"{o}_prior" not in t.columns:  # tendencies: build the previous-8 means here
            x = x.sort("team", "kickoff").with_columns(c(o).shift(1).rolling_mean(8, min_samples=3).over("team").fill_null(c(o).mean()).alias(f"{o}_prior"))
        f = lambda d, k: d[k].cast(pl.Float64).fill_null(0).to_numpy()  # noqa: E731
        e0, e1, gid = [], [], []
        for s in range(2019, 2025):
            tr, te = x.filter(c("season") < s), x.filter((c("season") == s) & c("bad"))
            for inter, acc in ((False, e0), (True, e1)):
                def D(d, inter=inter, o=o, f=f):
                    cols = [np.ones(d.height), f(d, f"{o}_prior"), f(d, f"{o}_opp")] + [f(d, k) for k in COND]
                    if inter:
                        cols += [f(d, z) * f(d, w) for z in [*Z, "p_oe", "p_sg"] for w in ("wind", "precip", "cold")] + [f(d, z) for z in [*Z, "p_oe", "p_sg"]]
                    return np.column_stack(cols)
                fit = ridge_tuned(D(tr), f(tr, o), tr["season"].to_numpy())
                acc.append((f(te, o) - fit(D(te))) ** 2)
            gid.append(te["game_id"].to_numpy())
        e0, e1, gid = np.concatenate(e0), np.concatenate(e1), np.concatenate(gid)
        u, inv = np.unique(gid, return_inverse=True)
        A, B = np.bincount(inv, e1), np.bincount(inv, e0)
        idx = RNG.integers(0, len(u), (1000, len(u)))
        gb = 1 - A[idx].sum(1) / B[idx].sum(1)
        res125[o] = (1 - e1.sum() / e0.sum(), np.quantile(gb, 0.05), np.quantile(gb, 0.95), len(e0))
        say(f"| {lab} | {res125[o][0]:+.3%} ({res125[o][1]:+.3%} to {res125[o][2]:+.3%}; {len(e0):,} team-games) |")
    h125 = res125["plays"][1] > 0 or res125["tempo_seconds"][1] > 0
    say("", f"H125 (pace's gain clear): {'held' if h125 else 'failed'}. Schemes (either tendency clear): {'held' if max(res125['neutral_pass_oe'][1], res125['shotgun_rate'][1]) > 0 else 'failed'}.", "")

    # the spread of play outcomes
    say("## The spread of play outcomes: the SD of EPA less the situation model's, against calm, dry, mild outdoor plays", "")
    x = p.filter(~c("dome"))
    fit = ridge(design(x, "o", False, False)[:, :11], x["epa"].to_numpy())
    res = x["epa"].to_numpy() - fit(design(x, "o", False, False)[:, :11])
    x = x.with_columns(res=pl.Series(res))
    calm = (c("wind") < 10) & (c("precip") <= 0) & (c("temp") >= 50)
    out = []
    for lab, cond in (("15+ mph wind", c("wind") >= 15), ("rain or snow (0.02+ in/h)", c("precip") >= 0.02), ("32°F or colder", c("temp") <= 32)):
        a, b = x.filter(cond), x.filter(calm)
        ga, gb_ = a.group_by("game_id").agg(s=(c("res") ** 2).sum(), n=pl.len()), b.group_by("game_id").agg(s=(c("res") ** 2).sum(), n=pl.len())
        sa, na, sb, nb = ga["s"].to_numpy(), ga["n"].to_numpy(), gb_["s"].to_numpy(), gb_["n"].to_numpy()
        ia, ib = RNG.integers(0, len(sa), (1000, len(sa))), RNG.integers(0, len(sb), (1000, len(sb)))
        ratio = np.sqrt((sa[ia].sum(1) / na[ia].sum(1)) / (sb[ib].sum(1) / nb[ib].sum(1))) - 1
        r0 = np.sqrt((sa.sum() / na.sum()) / (sb.sum() / nb.sum())) - 1
        out.append(abs(r0) >= 0.03 and (np.quantile(ratio, 0.05) > 0 or np.quantile(ratio, 0.95) < 0))
        say(f"- {lab}: SD {r0:+.1%} against calm (90%: {np.quantile(ratio, 0.05):+.1%} to {np.quantile(ratio, 0.95):+.1%}; {a.height:,} plays, {len(sa)} games)")
    say("", f"The spread bet (15+ mph wind differs from calm by 3%+, clearly): {'held' if out[0] else 'failed'}.")
    say.save()


if __name__ == "__main__":
    main()
