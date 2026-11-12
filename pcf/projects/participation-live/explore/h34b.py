"""H34 taken apart: which piece of 'fatigue' helps say who comes off next (the drive, his streak,
his touches), and H35's broader form: does each player's own persistence (stay on once on, come
back once off) repeat, beyond what his snap share implies? Train 2016-2021, test 2022-2024."""

# ruff: noqa: E501
import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from common import panel
from pcf.validation.consistency import consistency

c = pl.col
X = panel()
H = X.filter((c("on") == 1) & (c("drive_1") == c("fixed_drive"))).with_columns(off_next=1 - c("on_1"))

BASE = [
    c("share"), c("share") ** 2, (c("nx_down") == 1), (c("nx_down") == 2), (c("nx_down") == 3), (c("nx_down") == 4),
    c("nx_ydstogo").clip(0, 20) / 10, (c("nx_qtr") == 4), (c("nx_yardline_100") <= 20), (c("nx_yardline_100") <= 5),
    (c("nx_half_seconds_remaining") <= 120), c("nx_score_differential").abs().clip(0, 28) / 14,
    c("nx_no_huddle").fill_null(0), c("nx_shotgun").fill_null(0),
]  # fmt: skip
PIECES = {
    "drive": [c("nx_drive_n").clip(0, 15) / 5, (c("nx_drive_n").clip(0, 15) / 5) ** 2, c("drive_on").clip(0, 15) / 5],
    "streak": [c("streak").clip(0, 20) / 5, (c("streak").clip(0, 20) / 5) ** 2, c("streak") == 1],
    "touches": [c("touch_streak").clip(0, 4), c("touch"), c("carry"), c("reception")],
    "last_play": [c("big"), c("yards_gained").clip(-10, 40) / 10, c("pass").fill_null(0)],
}


def mat(df, feats):
    return df.select([x.cast(pl.Float64).fill_null(0).alias(f"x{i}") for i, x in enumerate(feats)]).to_numpy()


rows = []
for g in ["DB", "DL", "LB", "RB", "TE", "WR"]:
    d = H.filter(c("group") == g)
    tr, te = d.filter(c("season") <= 2021), d.filter(c("season") >= 2022)
    ytr, yte = tr["off_next"].to_numpy(), te["off_next"].to_numpy()

    def ll(feats):
        m = LogisticRegression(max_iter=400).fit(mat(tr, feats), ytr)
        return log_loss(yte, m.predict_proba(mat(te, feats))[:, 1])

    b = ll(BASE)
    r = {"group": g, "ll_baseline": b}
    for k, f in PIECES.items():
        r[f"+{k}_%"] = 100 * (b - ll(BASE + f)) / b
    allf = BASE + [x for f in PIECES.values() for x in f]
    a = ll(allf)
    r["+all_%"] = 100 * (b - a) / b
    for k in PIECES:
        r[f"all-{k}_%"] = 100 * (b - ll(BASE + [x for kk, f in PIECES.items() if kk != k for x in f])) / b
    rows.append(r)
print("Held-out log loss gain (%) over the baseline (his game snap share + the next snap's situation), off next snap given on now:")
print("+piece = baseline plus that piece alone; all-piece = everything but that piece (its unique part = +all minus all-piece)")
with pl.Config(tbl_cols=14, float_precision=2):
    print(pl.DataFrame(rows))

# a fatigue reading free of the sequence: the off chance by plays in the drive, among players on every snap of the drive so far
print("\nOff next snap by plays in the drive so far, only for players on every snap of the drive so far (streak = drive snaps):")
F = H.filter(c("drive_on") == c("drive_n") + 1)
with pl.Config(tbl_rows=20):
    print(F.with_columns(dn=(c("drive_n") + 1).clip(1, 12)).group_by("group", "dn").agg(off=c("off_next").mean()).sort("group", "dn").pivot(on="dn", index="group", values="off"))

# H35 broader: each player's own persistence, beyond his snap share. Per player-game, his stay rate
# (on next | on now, same drive) and return rate (on next | off now, same drive), minus the
# position's average at the same snap share (a 5% share bin).
I = X.filter(c("drive_1") == c("fixed_drive")).with_columns(sbin=(c("share") * 20).floor())
pg = I.group_by("game_id", "side", "gsis_id", "group", "season", "week", "sbin").agg(
    stay=c("on_1").filter(c("on") == 1).mean(), ret=c("on_1").filter(c("on") == 0).mean(),
    n_on=(c("on") == 1).sum(), n_off=(c("on") == 0).sum(),
)
exp = pg.group_by("group", "sbin").agg(stay_e=c("stay").mean(), ret_e=c("ret").mean())
pg = pg.join(exp, on=["group", "sbin"]).with_columns(stay_x=c("stay") - c("stay_e"), ret_x=c("ret") - c("ret_e"))
pg = pg.filter((c("n_on") >= 5) & (c("n_off") >= 5))
out = []
for g in ["DB", "DL", "LB", "RB", "TE", "WR"]:
    d = pg.filter(c("group") == g).rename({"stay_x": f"stay_{g}", "ret_x": f"return_{g}"})
    out.append(consistency(d, [f"stay_{g}", f"return_{g}"], unit="gsis_id"))
print("\nEach player's persistence beyond his snap share (player-games with 5+ snaps on and 5+ off), consistency by player:")
with pl.Config(tbl_rows=20, tbl_cols=10, float_precision=3):
    print(pl.concat(out).select("measure", "week_r", "week_lo", "season_r", "season_lo", "unit_seasons", "season_pairs", "mean_abs", "verdict"))
print("typical stay and return rates by group:")
print(pg.group_by("group").agg(stay=c("stay").mean(), ret=c("ret").mean(), player_games=pl.len()).sort("group"))
_ = np
