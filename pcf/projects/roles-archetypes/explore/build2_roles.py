"""Round 2, the backlog ideas on the build's own pieces (odds in BUILD.md, round 2, and IDEAS.md,
written before this ran):

- I134: a hysteresis band for the fine roles. Season s's label keeps season s-1's (his main-team
  full-season label) unless his features move past one of that role's cuts by more than `b` times
  his sampling sd at his snaps. Both halves of a season use the same anchor, so the flip test
  (odd against even weeks) measures the published label's sampling noise. `b` is chosen on
  2017-2020 (the smallest that brings the median flip under 14%) and 2021-2024 is scored once.
  Then: do the banded labels forecast next season's per-snap rates as well as the plain ones?
- I135: the role table without targets per pass snap and carries per run snap (and without the
  named-role dummies, which read carries per run snap): test 2 (over labels) and test 3 (beyond
  his own rates). The yardstick half is in build2_yardstick.py.
- I136: like-for-like substitutes (H101's test) on the standardized role table instead of the
  pooled space.

Run from pcf/: .venv/Scripts/python.exe projects/roles-archetypes/explore/build2_roles.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import build2_common as bc  # noqa: E402

from pcf.experts.roles_archetypes import data as D  # noqa: E402
from pcf.experts.roles_archetypes import evaluate as V  # noqa: E402
from pcf.experts.roles_archetypes import named as N  # noqa: E402
from pcf.experts.roles_archetypes import space as S  # noqa: E402
from pcf.experts.roles_archetypes.counts import SIDES  # noqa: E402

c = pl.col
say = bc.Say(Path(__file__).with_suffix(".txt"))
cnt, games = D.counts()
fe = D.walk_features(cnt)
fit = fe.filter((c("half") == "all") & (c("snaps") >= S.MIN_SNAPS) & c("season").is_in(D.FIT))
cuts = N.fit_cuts(fit)
noise = N.feature_noise(fe, fit, sorted({x.feature for x in cuts.values()}))
plain = N.name_roles(fe, cuts, noise)
TESTS = {r: tests for r, _, tests in N.RULES}


def banded(b: float) -> pl.DataFrame:
    """Labels with the band: anchor = last season's main-team full-season plain label."""
    anchor = (bc.main_rows(plain.filter(c("half") == "all").with_columns(snaps=c("snaps")))
              .select("gsis_id", "side", season=c("season") + 1, anchor=c("role")))
    j = fe.select(*N.PAIR, "half", "snaps", *{x.feature for x in cuts.values()}).join(
        plain.select(*N.PAIR, "half", "role", "coarse", "sure"), on=[*N.PAIR, "half"]).join(
        anchor, on=["gsis_id", "side", "season"], how="left")
    n = np.maximum(j["snaps"].to_numpy().astype(float), 1)
    role = j["role"].to_numpy().astype(object)
    anc = j["anchor"].to_numpy().astype(object)
    keep = np.zeros(j.height, dtype=bool)
    for a in set(x for x in anc if x is not None):
        idx = anc == a
        ok = idx & (role != a)
        for cut, above in TESTS[a]:
            ct = cuts[cut]
            x = j[ct.feature].to_numpy().astype(float)
            sd = np.sqrt(noise[ct.feature] / n)
            # within the band of the anchor's side of the cut (or on it)
            ok &= (x >= ct.value - b * sd) if above else (x < ct.value + b * sd)
        keep |= ok
    new = np.where(keep, anc, role)
    return j.select(*N.PAIR, "half", "snaps").with_columns(
        role=pl.Series(new.tolist(), dtype=pl.String),
        coarse=pl.Series([N.COARSE.get(r) for r in new], dtype=pl.String),
        kept=pl.Series(keep))


def med_flip(lab: pl.DataFrame, seasons) -> tuple[float, str]:
    f = V.flips(lab, seasons, "role")
    return float(f["flip"].median()), ", ".join(f"{g} {v:.0%}" for g, v in zip(f["group"], f["flip"], strict=True))


say("Round 2: I134, I135, I136 on the build's pieces (run 696a3f0b's counts and features)")
say("\n== I134: a hysteresis band for the fine roles")
early, late = tuple(range(2017, 2021)), D.SCORED
m0, g0 = med_flip(plain, early)
m1, g1 = med_flip(plain, late)
say(f"  plain labels: median flip 2017-2020 {m0:.1%}; 2021-2024 {m1:.1%} ({g1})")
choice = None
labs = {}
for b in (0.5, 1.0, 1.5, 2.0, 3.0):
    lab = banded(b)
    labs[b] = lab
    e, _ = med_flip(lab, early)
    say(f"  band {b:.1f} sd: median flip 2017-2020 {e:.1%}; kept the anchor on {lab.filter(c('half') == 'all')['kept'].mean():.1%} of full-season rows")
    if choice is None and e < 0.14:
        choice = b
choice = choice or 3.0
lab = labs[choice]
m2, g2 = med_flip(lab, late)
say(f"  chosen on 2017-2020: band {choice} sd. Scored once on 2021-2024: median flip {m2:.2%} ({g2}) -> {'PASSES' if m2 < 0.14 else 'FAILS'} the 14% bar")
say("  sensitivity (not the verdict; looked at after the choice): the other bands on 2021-2024: " + ", ".join(f"{b} sd {med_flip(labs[b], late)[0]:.1%}" for b in labs if b != choice))
dl_olb = V.flips(lab, late, "role").filter(c("group").is_in(["DL", "OLB"]))
say("  DL and OLB under 20%: " + ", ".join(f"{g} {v:.1%}" for g, v in zip(dl_olb["group"], dl_olb["flip"], strict=True)))
# do the banded labels still forecast as well? next season's per-snap rates from labels + role dummies
say("  forecasting check: next season's per-snap rates from position labels + role dummies, plain against banded (walk-forward, scored 2021-2024; a tie means the band costs nothing)")
tot = V.season_totals(cnt)


def role_rows(lab: pl.DataFrame, side: str) -> tuple[pl.DataFrame, list[str]]:
    roles = N.ROLES[side]
    base = fe.filter((c("side") == side) & (c("half") == "all"))
    lb = lab.filter(c("half") == "all").select(*N.PAIR, *[(c("role") == r).cast(pl.Float64).alias(f"r_{i}") for i, r in enumerate(roles)])
    rows = V.pairs(V.main_rows(base.join(lb, on=N.PAIR)), tot, side)
    rows = pl.concat([rows, V.position_dummies(rows, side)], how="horizontal")
    return rows, [f"is_{g}" for g in SIDES[side][1:]] + [f"r_{i}" for i in range(len(roles))]


for side in SIDES:
    rp, cols = role_rows(plain, side)
    rb, _ = role_rows(lab, side)
    rb = rp.select(*N.PAIR).join(rb, on=N.PAIR, how="left")
    ids = rp["gsis_id"].to_numpy()
    for tgt in V.TARGETS[side]:
        y = rp[f"y_{tgt}"].to_numpy()
        p0 = V.walk(rp, cols, f"y_{tgt}", V.LASSO, D.SCORED)
        p1 = V.walk(rb, cols, f"y_{tgt}", V.LASSO, D.SCORED)
        say(f"    {side} {V.TARGET_NAMES[tgt]}: banded against plain {V.gain(y, p0, p1, ids).line()}")

say("\n== I135: the role table without his own target rates (offense)")
side = "offense"
T6 = N.TABLE[side]
T4 = [x for x in T6 if x not in ("tgt_per_pass", "car_per_run")]
base = fe.filter((c("side") == side) & (c("half") == "all"))
rows = V.pairs(V.main_rows(base), tot, side)
rows = pl.concat([rows, V.position_dummies(rows, side)], how="horizontal")
P = [f"is_{g}" for g in SIDES[side][1:]]
own = [f"own_{t}" for t in V.TARGETS[side]] + ["snap_share"]
ids = rows["gsis_id"].to_numpy()
say(f"  {rows.filter(c('target_season').is_in(list(D.SCORED))).height} pairs scored 2021-2024; no named-role dummies in either table (they read carries per run snap)")
for tgt in V.TARGETS[side]:
    y = rows[f"y_{tgt}"].to_numpy()
    L = lambda cols, t=tgt: V.walk(rows, cols, f"y_{t}", V.LASSO, D.SCORED)  # noqa: E731
    p = {"P": L(P), "T6": L([*P, *T6]), "T4": L([*P, *T4]), "B": L([*P, *own]), "BT6": L([*P, *own, *T6]), "BT4": L([*P, *own, *T4])}
    g = lambda a, b, y=y, p=p: V.gain(y, p[a], p[b], ids).line()  # noqa: E731
    say(f"  {V.TARGET_NAMES[tgt]}:")
    say(f"    test 2: labels -> + 6-feature table {g('P', 'T6')}; -> + 4-feature table {g('P', 'T4')}")
    say(f"    test 3: labels + own rates -> + 6-feature table {g('B', 'BT6')}; -> + 4-feature table {g('B', 'BT4')}")

say("\n== I136: like-for-like substitutes on the role table (H101's design; chance 0.5)")
for side in SIDES:
    tab = N.TABLE[side]
    full = V.main_rows(fe.filter(c("side") == side))
    ref = full.filter(c("snaps") >= S.MIN_SNAPS)
    mu = {x: ref[x].mean() for x in tab}
    sd = {x: ref[x].std() for x in tab}
    prior = full.select("gsis_id", *[((c(x) - mu[x]) / sd[x]).alias(x) for x in tab], season=c("season") + 1)
    sub = V.substitutes(games.filter(c("side") == side), prior, tab)
    by = ", ".join(f"{g} {v:.2f}" for g, v in sub["by_group"].items())
    say(f"  {side}: rank {sub['rank']:.3f} (90% {sub['lo']:.3f} to {sub['hi']:.3f}), {sub['events']} events; {by} -> {'PASSES' if sub['hi'] < 0.5 else 'FAILS'}")
    # the pooled space's result for comparison is in the build report (0.477 both sides)
say.save()
