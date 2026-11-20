# ruff: noqa: E501
"""voe, a quick check of the CEO's idea (2026-11-20): group plays where the same 22 players are on the
field ("stints", as basketball plus-minus does), average their EPA over expected, and fit on those.

Two groupings: consecutive plays in a game with the same 22 (the CEO's example: first and second down of
a drive), and every play anywhere in the season with the same 22 against the same opponent's 11.
Compares plus-minus fit on plays with plus-minus fit on stint averages (weighted by plays), and how much
of a held-out row each explains. Discovery only, 2017 (the season the first look chose the shrinkage on).

Run from pcf/:  python projects/voe/explore/stints.py > projects/voe/explore/stints.txt
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import polars as pl
import scipy.sparse as sp
from scipy.sparse.linalg import lsqr

sys.path.insert(0, str(Path(__file__).parent))
import first_look as fl  # noqa: E402

c = pl.col
ALPHA = 10000.0
SEASON = 2017


def design(rows, keycol, ids):
    """One row per unit of `keycol`: +1 offense, -1 defense; y = the mean leftover; n = plays."""
    # resid repeats over a play's 22 rows: one row per play first, then the group's mean and plays
    u = rows.unique(["pk"]).group_by(keycol).agg(y=c("resid").mean(), n=pl.len())
    u = u.sort(keycol).with_row_index("r")
    members = (
        rows.select(keycol, "gsis_id", "side")
        .unique([keycol, "gsis_id"])
        .join(u.select(keycol, "r"), on=keycol)
    )
    col = {g: i for i, g in enumerate(ids)}
    ci = np.array([col[g] for g in members["gsis_id"].to_list()])
    sign = np.where(members["side"].to_numpy() == "offense", 1.0, -1.0)
    X = sp.csr_matrix((sign, (members["r"].to_numpy(), ci)), shape=(u.height, len(ids)))
    return X, u["y"].to_numpy(), u["n"].to_numpy().astype(float)


def fit(X, y, n, mean):
    w = np.sqrt(n)
    Xw = sp.diags(w) @ X
    return lsqr(Xw, (y - mean) * w, damp=math.sqrt(ALPHA), atol=1e-10, btol=1e-10, iter_lim=5000)[0]


def r2(X, y, n, b, mean):
    return 1 - (n * (y - mean - X @ b) ** 2).sum() / (n * (y - mean) ** 2).sum()


def main():
    p = fl.plays()
    on = fl.on_field(p).filter(c("season") == SEASON)
    on = on.with_columns(pk=c("game_id") + "_" + c("play_id").cast(pl.Utf8))
    lineup = (
        on.sort("gsis_id")
        .group_by("pk")
        .agg(
            key=c("gsis_id").str.join(","),
            game_id=c("game_id").first(),
            play_id=c("play_id").first(),
            nply=pl.len(),
        )
        .filter(c("nply") == 22)
        .sort("game_id", "play_id")
        .with_columns(chg=(c("key") != c("key").shift(1)) | (c("game_id") != c("game_id").shift(1)))
        .with_columns(stint=c("chg").cum_sum().cast(pl.Utf8))
    )
    on = on.join(lineup.select("pk", "key", "stint"), on="pk")
    ids = on["gsis_id"].unique().sort().to_list()
    plays_n = lineup.height
    for name, kc in (
        ("consecutive plays, same 22", "stint"),
        ("anywhere in the season, same 22", "key"),
    ):
        sz = on.unique("pk").group_by(kc).agg(n=pl.len())["n"]
        print(
            f"{name}: {sz.len():,} groups from {plays_n:,} plays (plays with all 22 recorded); mean {sz.mean():.2f} plays a group; plays in groups of 2+: {sz.filter(sz >= 2).sum() / plays_n:.0%}; of 5+: {sz.filter(sz >= 5).sum() / plays_n:.0%}"
        )

    print(
        "\nThe same plus-minus fit on plays and on group averages (weighted by plays), whole season:"
    )
    Xp, yp, np_ = design(on, "pk", ids)
    mean = float((yp * np_).sum() / np_.sum())
    bp = fit(Xp, yp, np_, mean)
    for name, kc in (("consecutive", "stint"), ("anywhere", "key")):
        Xs, ys, ns = design(on, kc, ids)
        bs = fit(Xs, ys, ns, mean)
        print(
            f"  {name}: player values agree {np.corrcoef(bp, bs)[0, 1]:.6f}; largest difference {np.abs(bp - bs).max():.2e} (values' spread {bp.std():.2e})"
        )

    print(
        "\nHeld out (fit on odd weeks, scored on even weeks): the share of a held-out row's leftover explained"
    )
    wk = on.select("pk", "week").unique("pk")
    odd = set(wk.filter(c("week") % 2 == 1)["pk"].to_list())
    tr, te = on.filter(c("pk").is_in(list(odd))), on.filter(~c("pk").is_in(list(odd)))
    Xa, ya, na = design(tr, "pk", ids)
    m0 = float((ya * na).sum() / na.sum())
    b = fit(Xa, ya, na, m0)
    for name, kc in (
        ("a play", "pk"),
        ("a consecutive group", "stint"),
        ("a same-22 group", "key"),
    ):
        Xb, yb, nb = design(te, kc, ids)
        print(f"  per {name:<20} {100 * r2(Xb, yb, nb, b, m0):+.3f}% (rows {len(yb):,})")
    print(
        "\n  For scale: a row's leftover sd, play vs group average (luck shrinks with plays; the players' part doesn't)"
    )
    for name, kc in (("a play", "pk"), ("a consecutive group", "stint")):
        Xb, yb, nb = design(te, kc, ids)
        print(
            f"    {name}: sd {np.sqrt((nb * (yb - m0) ** 2).sum() / nb.sum()):.3f}; the 22 players' fitted part sd {np.sqrt((nb * (Xb @ b) ** 2).sum() / nb.sum()):.4f}"
        )


if __name__ == "__main__":
    main()
