"""Method 3, exploratory: diversion ratios from a nested-logit choice model (decision 0050).

**The fit** (completed seasons only, rule m: it reads who was on the field, `player_play.on_field`,
known the day after the Super Bowl). Every regular-season target (and, apart, every carry) is a
choice among the offense's WR, TE and RB on the field that play, plus an outside option (a target
to anyone else, a QB's run). A player's utility is his pull for that season, `alpha`; the nests are
the groups (WR, TE, RB), each with a nest parameter `lam` in (0, 1]: below 1, players of a group
are closer substitutes for each other than for the other groups. The outside option has utility 0.
Pulls are shrunk toward each nest's constant by a ridge penalty.

**In season** (the diversion): the completed seasons' nest parameters are a prior. Each skill
player's pull is backed out from his no-change target (carry) share and snap share (a contraction,
as in BLP's inversion of market shares), on a representative play where a player is on the field
with probability equal to his snap share. The expected on-field change (the plus-minus's snap
forecast, and the absent top player's chance of playing) then gives each player's new share.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import polars as pl
from scipy.optimize import minimize

from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.vacated_opportunity import common as K

c = pl.col
NESTS = ("WR", "TE", "RB")
OUT = len(NESTS)  # the outside option's index
LAM_GRID = (0.25, 0.4, 0.55, 0.7, 0.85, 1.0)
TAU = 1.0  # the pulls' ridge penalty (per player-season)


def plays(season: int, kind: str, groups: pl.DataFrame) -> pl.DataFrame:
    """One row per (play, skill player on the field) for a season's targets or carries: play
    key, his player-season index, nest, and whether he was the choice; plays whose choice was
    outside the set keep their members with `chosen` all false."""
    v = Gateway(TableSource(seasons=[season])).view(END_OF_TIME, "retrospective",
                                                      {"play": ("pbp",), "player_play": ("on_field",)})  # fmt: skip
    pbp = v.table("play", seasons=[season]).filter(c("season_type") == "REG")
    if kind == "target":
        pbp = pbp.filter(
            (c("pass_attempt") == 1) & c("receiver_player_id").is_not_null() & (c("sack") != 1)
        )
        who = "receiver_player_id"
    else:
        pbp = pbp.filter((c("rush_attempt") == 1) & c("rusher_player_id").is_not_null()
                         & (c("qb_scramble") != 1))  # fmt: skip
        who = "rusher_player_id"
    pbp = pbp.filter(c("two_point_attempt").fill_null(0) == 0).select("game_id", "play_id", team="posteam",
                                                                      choice=who)  # fmt: skip
    of = (
        v.table("player_play", seasons=[season])
        .filter(c("side") == "offense")
        .select("game_id", "play_id", "team", "gsis_id")
    )
    of = of.join(groups.filter(c("season") == season).select("gsis_id", "team", "group"),
                 on=["gsis_id", "team"], how="inner").filter(c("group").is_in(list(NESTS)))  # fmt: skip
    x = pbp.join(of, on=["game_id", "play_id", "team"], how="inner")
    return x.with_columns(chosen=c("gsis_id") == c("choice"), season=pl.lit(season, pl.Int32))


@dataclass
class Arrays:
    play: np.ndarray  # play index per member
    ps: np.ndarray  # player-season index per member
    nest: np.ndarray  # nest index per member
    chosen: np.ndarray  # bool per member
    out_chosen: np.ndarray  # bool per play: the choice was outside the set
    n_plays: int
    n_ps: int


def arrays(x: pl.DataFrame) -> tuple[Arrays, pl.DataFrame]:
    x = x.with_columns(pk=pl.concat_str("game_id", c("play_id").cast(pl.Utf8), separator="|"),
                       psk=pl.concat_str("gsis_id", "team", c("season").cast(pl.Utf8), separator="|"))  # fmt: skip
    pid = x.select("pk").unique(maintain_order=True).with_row_index("p")
    sid = (
        x.select("psk", "gsis_id", "team", "season", "group")
        .unique("psk", maintain_order=True)
        .with_row_index("s")
    )
    x = x.join(pid, on="pk").join(sid.select("psk", "s"), on="psk")
    nest = (
        x["group"]
        .replace_strict({g: i for i, g in enumerate(NESTS)}, return_dtype=pl.Int64)
        .to_numpy()
    )
    any_in = x.group_by("p").agg(a=c("chosen").any()).sort("p")["a"].to_numpy()
    arr = Arrays(x["p"].to_numpy().astype(np.int64), x["s"].to_numpy().astype(np.int64), nest,
                 x["chosen"].to_numpy(), ~any_in, pid.height, sid.height)  # fmt: skip
    return arr, sid


def _loglik(theta: np.ndarray, a: Arrays, lam: np.ndarray, tau: float) -> tuple[float, np.ndarray]:
    """Minus the nested logit's log likelihood (plus the pulls' penalty) and its gradient in
    (alpha per player-season, beta per nest)."""
    alpha, beta = theta[: a.n_ps], theta[a.n_ps :]
    lm = lam[a.nest]
    u = alpha[a.ps] / lm
    key = a.play * OUT + a.nest
    m = np.full(a.n_plays * OUT, -np.inf)
    np.maximum.at(m, key, u)
    eu = np.exp(u - m[key])
    s = np.bincount(key, weights=eu, minlength=a.n_plays * OUT)
    with np.errstate(divide="ignore"):
        inc = np.where(s > 0, m + np.log(np.where(s > 0, s, 1.0)), -np.inf)  # I per (play, nest)
    inc = inc.reshape(a.n_plays, OUT)
    V = np.where(np.isfinite(inc), beta[None, :] + lam[None, :] * inc, -np.inf)
    vmax = np.maximum(V.max(1), 0.0)
    den = np.exp(-vmax) + np.exp(V - vmax[:, None]).sum(1)
    logden = vmax + np.log(den)
    Pn = np.exp(V - logden[:, None])  # P(nest) per play
    pk = eu / s[key]  # P(k | nest)
    ch = a.chosen
    cp, cn = a.play[ch], a.nest[ch]
    ll = (u[ch] - inc[cp, cn] + V[cp, cn] - logden[cp]).sum() - (logden[a.out_chosen]).sum()
    # gradient in alpha (the derivation is in the module docstring's spirit; see decision 0050)
    chosen_nest = np.full(a.n_plays, -1)
    chosen_nest[cp] = cn
    in_chosen = chosen_nest[a.play] == a.nest
    g_k = ch / lm + in_chosen * pk * (1 - 1 / lm) - Pn[a.play, a.nest] * pk
    g_alpha = np.bincount(a.ps, weights=g_k, minlength=a.n_ps) - tau * alpha
    onehot = np.zeros((a.n_plays, OUT))
    onehot[cp, cn] = 1.0
    g_beta = (onehot - Pn).sum(0)
    pen = 0.5 * tau * (alpha**2).sum()
    return -(ll - pen), -np.concatenate([g_alpha, g_beta])


def fit_given(a: Arrays, lam: np.ndarray, start: np.ndarray | None = None, tau: float = TAU):
    theta0 = np.zeros(a.n_ps + OUT) if start is None else start
    r = minimize(_loglik, theta0, args=(a, lam, tau), jac=True, method="L-BFGS-B",
                 options={"maxiter": 500, "gtol": 1e-5})  # fmt: skip
    return r.x, -r.fun


def fit(a: Arrays, passes: int = 2) -> tuple[np.ndarray, np.ndarray, float]:
    """The nest parameters by coordinate search over `LAM_GRID` (each nest in turn), the pulls
    and nest constants by maximum likelihood at each. Returns (lam, theta, log likelihood)."""
    lam = np.ones(OUT)
    theta, best = fit_given(a, lam)
    for _ in range(passes):
        for g in range(OUT):
            for v in LAM_GRID:
                if v == lam[g]:
                    continue
                trial = lam.copy()
                trial[g] = v
                th, ll = fit_given(a, trial, theta)
                if ll > best + 1e-6:
                    best, lam, theta = ll, trial, th
    return lam, theta, best


# ---------------------------------------------------------------- the diversion in season
def shares(alpha: np.ndarray, snap: np.ndarray, nest: np.ndarray, lam: np.ndarray) -> np.ndarray:
    """A representative play's choice probabilities: each player on the field with probability
    his snap share (the inclusive value of a nest is the log of its snap-weighted pulls)."""
    lm = lam[nest]
    w = snap * np.exp(alpha / lm)
    P = np.zeros_like(alpha)
    S = np.zeros(OUT)
    for g in range(OUT):
        S[g] = w[nest == g].sum()
    V = np.where(S > 0, lam * np.log(np.where(S > 0, S, 1.0)), -np.inf)
    den = 1.0 + np.exp(V).sum()
    Pn = np.exp(V) / den
    for g in range(OUT):
        idx = nest == g
        if S[g] > 0:
            P[idx] = Pn[g] * w[idx] / S[g]
    return P


def invert(target: np.ndarray, snap: np.ndarray, nest: np.ndarray, lam: np.ndarray,
           iters: int = 300) -> np.ndarray:  # fmt: skip
    """The pulls that reproduce the target shares (floored at 1e-4) on the representative play."""
    t = np.clip(target, 1e-4, None)
    if t.sum() > 0.98:
        t = t * 0.98 / t.sum()
    alpha = np.log(t) - np.log(np.clip(snap, 1e-3, None))
    lm = lam[nest]
    for _ in range(iters):
        P = shares(alpha, np.clip(snap, 1e-3, None), nest, lam)
        step = lm * (np.log(t) - np.log(np.clip(P, 1e-12, None)))
        alpha = alpha + step
        if np.abs(step).max() < 1e-7:
            break
    return alpha


def divert(target: np.ndarray, snap0: np.ndarray, snap1: np.ndarray, nest: np.ndarray,
           lam: np.ndarray) -> np.ndarray:  # fmt: skip
    """New shares when the expected on-field shares move from snap0 to snap1."""
    s0 = np.clip(snap0, 1e-3, None)
    alpha = invert(target, s0, nest, lam)
    base = shares(alpha, s0, nest, lam)
    new = shares(alpha, np.clip(snap1, 0.0, None), nest, lam)
    return np.clip(target + (new - base), 0, 1)


def lam_table(fits: dict[int, np.ndarray]) -> pl.DataFrame:
    return pl.DataFrame([{"season": s, **{f"lam_{g}": float(v[i]) for i, g in enumerate(NESTS)}}
                         for s, v in sorted(fits.items())])  # fmt: skip


def walk_lams(fits: dict[int, np.ndarray], seasons: Sequence[int]) -> dict[int, np.ndarray]:
    """Each walked season's prior: the mean of the nest parameters fit on completed seasons."""
    out = {}
    for s in seasons:
        prior = [v for k, v in fits.items() if k < s]
        out[s] = np.mean(prior, axis=0) if prior else np.ones(OUT)
    return out
