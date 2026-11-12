"""H34 (fatigue on a drive and consecutive touches) and H35 (a player's own patterns across
consecutive plays: "one player often will play two more snaps after they make a reception").

Measured on the answer key, on part-timers only (players on some but not all of a side's snaps in
a game). One row per part-timer and team snap. Train 2016-2021, test 2022-2024."""

# ruff: noqa: E501
import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from common import panel
from pcf.validation.consistency import consistency

c = pl.col
X = panel()
print(f"part-timer games (player-game-sides): {X.select('game_id', 'side', 'gsis_id').n_unique():,}")
print(f"part-timer snaps (rows): {X.height:,}; on the field in {X['on'].mean():.1%}")

# ---------------- H34: on now, off on the next snap of the same drive ----------------
H = X.filter((c("on") == 1) & (c("drive_1") == c("fixed_drive"))).with_columns(off_next=1 - c("on_1"))
print(f"\nH34 rows (on now, next snap in the same drive): {H.height:,}; off next: {H['off_next'].mean():.1%}")
H = H.with_columns(
    drive_bin=pl.when(c("nx_drive_n") <= 2).then(pl.lit("a 1-2")).when(c("nx_drive_n") <= 4).then(pl.lit("b 3-4"))
    .when(c("nx_drive_n") <= 7).then(pl.lit("c 5-7")).when(c("nx_drive_n") <= 10).then(pl.lit("d 8-10")).otherwise(pl.lit("e 11+")),
    streak_bin=pl.when(c("streak") <= 1).then(pl.lit("a 1")).when(c("streak") <= 2).then(pl.lit("b 2")).when(c("streak") <= 4).then(pl.lit("c 3-4"))
    .when(c("streak") <= 7).then(pl.lit("d 5-7")).when(c("streak") <= 12).then(pl.lit("e 8-12")).otherwise(pl.lit("f 13+")),
    tstreak_bin=pl.when(c("touch_streak") == 0).then(pl.lit("0")).when(c("touch_streak") == 1).then(pl.lit("1"))
    .when(c("touch_streak") == 2).then(pl.lit("2")).otherwise(pl.lit("3+")),
)  # fmt: skip
with pl.Config(tbl_rows=60, tbl_cols=12):
    print("\nOff next snap, by the next snap's place in the drive (plays in the drive so far) and position group:")
    print(H.group_by("drive_bin").agg(off=c("off_next").mean(), n=pl.len()).sort("drive_bin"))
    print(H.group_by("group", "drive_bin").agg(off=c("off_next").mean()).sort("group", "drive_bin").pivot(on="drive_bin", index="group", values="off"))
    print("\nOff next snap, by his consecutive snaps so far (this one included):")
    print(H.group_by("group", "streak_bin").agg(off=c("off_next").mean()).sort("group", "streak_bin").pivot(on="streak_bin", index="group", values="off"))
    print("\nOff next snap, by his consecutive touches (offense: carries or targets; defense: named on the play):")
    print(H.group_by("group", "tstreak_bin").agg(off=c("off_next").mean(), n=pl.len()).sort("group", "tstreak_bin").pivot(on="tstreak_bin", index="group", values="off"))


def design(df: pl.DataFrame, fatigue: bool, seq: bool = False) -> np.ndarray:
    """Baseline: his game snap share (the snap count, known the morning after) and the next snap's
    situation. Fatigue adds the drive, his streak and his touches. Seq adds the snap before."""
    f = [
        c("share"), c("share") ** 2,
        (c("nx_down") == 1), (c("nx_down") == 2), (c("nx_down") == 3), (c("nx_down") == 4),
        c("nx_ydstogo").clip(0, 20) / 10, (c("nx_qtr") == 4), (c("nx_yardline_100") <= 20), (c("nx_yardline_100") <= 5),
        (c("nx_half_seconds_remaining") <= 120), c("nx_score_differential").abs().clip(0, 28) / 14,
        c("nx_no_huddle").fill_null(0), c("nx_shotgun").fill_null(0),
    ]  # fmt: skip
    if fatigue:
        f += [c("nx_drive_n").clip(0, 15) / 5, (c("nx_drive_n").clip(0, 15) / 5) ** 2, c("streak").clip(0, 20) / 5,
              (c("streak").clip(0, 20) / 5) ** 2, c("drive_on").clip(0, 15) / 5, c("touch_streak").clip(0, 4),
              c("touch"), c("carry"), c("reception"), c("big"), c("yards_gained").clip(-10, 40) / 10]  # fmt: skip
    if seq:
        f += [c("prev_on").fill_null(1), c("prev2_on").fill_null(1)]
    return df.select([x.cast(pl.Float64).fill_null(0).alias(f"x{i}") for i, x in enumerate(f)]).to_numpy()


print("\nHeld-out log loss of 'off next snap' (train 2016-2021, test 2022-2024), by position group:")
print("baseline = his game snap share + the next snap's situation; + fatigue = plays in the drive, his streak, his snaps this drive, his touches, the last play's result")
res = []
for g in sorted(H["group"].unique()):
    d = H.filter(c("group") == g)
    tr, te = d.filter(c("season") <= 2021), d.filter(c("season") >= 2022)
    if tr.height < 5000:
        continue
    ytr, yte = tr["off_next"].to_numpy(), te["off_next"].to_numpy()
    row = {"group": g, "rows_test": te.height, "off_rate": float(yte.mean())}
    p0 = np.full(len(yte), ytr.mean())
    row["ll_constant"] = log_loss(yte, p0)
    for name, fat in (("baseline", False), ("fatigue", True)):
        m = LogisticRegression(max_iter=400, C=1.0).fit(design(tr, fat), ytr)
        row[f"ll_{name}"] = log_loss(yte, m.predict_proba(design(te, fat))[:, 1])
    # shuffled null: the fatigue features shuffled within the test rows' training set
    rng = np.random.default_rng(0)
    Xs = design(tr, True)
    nb = design(tr, False).shape[1]
    Xs[:, nb:] = Xs[rng.permutation(len(Xs)), nb:]
    ms = LogisticRegression(max_iter=400).fit(Xs, ytr)
    Xt = design(te, True)
    Xt[:, nb:] = Xt[rng.permutation(len(Xt)), nb:]
    row["ll_shuffled"] = log_loss(yte, ms.predict_proba(Xt)[:, 1])
    row["gain_pct"] = 100 * (row["ll_baseline"] - row["ll_fatigue"]) / row["ll_baseline"]
    res.append(row)
with pl.Config(tbl_cols=12, float_precision=4):
    print(pl.DataFrame(res))

# ---------------- H35: after his event, does he stay on for 1, 2, 3 more snaps? ----------------
print("\nH35: on now; share still on for the next k snaps (all in the same drive), after an event on this snap against the same player's snaps without it")
S = X.filter((c("on") == 1))
for k in (1, 2, 3):
    S = S.with_columns(**{f"stay_{k}": pl.when(c(f"drive_{k}") == c("fixed_drive")).then(pl.min_horizontal([c(f"on_{j}") for j in range(1, k + 1)]))})
events = {"reception": c("reception"), "carry": c("carry"), "target_incomplete": c("target") & ~c("reception"),
          "big_play_20plus": c("big"), "defense_named": (c("side") == "defense") & c("involved")}  # fmt: skip
rows = []
for ev, e in events.items():
    s = S.with_columns(ev=e)
    for g in sorted(s.filter(c("ev"))["group"].unique()):
        d = s.filter(c("group") == g)
        r = {"event": ev, "group": g, "events": d.filter(c("ev")).height}
        for k in (1, 2, 3):
            a = d.filter(c("ev"))[f"stay_{k}"].drop_nulls().mean()
            # his own baseline: same player-games, snaps without the event, matched on the play type
            b = d.filter(~c("ev") & (c("pass") == 1 if ev in ("reception", "target_incomplete") else (c("rush") == 1 if ev == "carry" else pl.lit(True))))[f"stay_{k}"].drop_nulls().mean()
            r[f"after_{k}"], r[f"usual_{k}"] = a, b
        if r["events"] >= 2000:
            rows.append(r)
with pl.Config(tbl_rows=40, tbl_cols=12, float_precision=3):
    print(pl.DataFrame(rows).with_columns(lift_1=c("after_1") - c("usual_1"), lift_2=c("after_2") - c("usual_2"), lift_3=c("after_3") - c("usual_3")).select("event", "group", "events", "after_1", "usual_1", "lift_1", "after_2", "usual_2", "lift_2", "lift_3"))

# within the player-game, controlled for the player: lift = stay after event - stay without, same game
print("\nThe same, as each player-game's own difference (controls for who he is and how much he played that day):")
out = []
for ev in ("reception", "carry", "big_play_20plus", "defense_named"):
    s = S.with_columns(ev=events[ev]).filter(c("stay_2").is_not_null())
    pgd = s.group_by("game_id", "side", "gsis_id", "group", "season", "week").agg(
        a=c("stay_2").filter(c("ev")).mean(), b=c("stay_2").filter(~c("ev")).mean(), ne=c("ev").sum()
    ).filter(c("ne") > 0).with_columns(lift2=c("a") - c("b"))
    for g in sorted(pgd["group"].unique()):
        d = pgd.filter(c("group") == g)
        if d.height < 1000:
            continue
        cons = consistency(d.rename({"lift2": f"{ev}_{g}"}), [f"{ev}_{g}"], unit="gsis_id")
        out.append(cons.with_columns(mean_lift=pl.lit(d["lift2"].mean()), se=pl.lit(d["lift2"].std() / d.height**0.5), player_games=pl.lit(d.height)))
with pl.Config(tbl_rows=40, tbl_cols=12, float_precision=3):
    print(pl.concat(out).select("measure", "player_games", "mean_lift", "se", "week_r", "week_lo", "season_r", "season_lo", "verdict"))

# ---------------- sequences: does the snap before last add to the last? (the shape of the model) ----------------
print("\nSequence memory, part-timers, next snap in the same drive: on next, by on now and on the snap before (same drive):")
Q = X.filter((c("drive_1") == c("fixed_drive")) & (c("prev_drive") == c("fixed_drive")))
with pl.Config(tbl_rows=40):
    print(Q.group_by("group", "prev_on", "on").agg(on_next=c("on_1").mean(), n=pl.len()).sort("group", "prev_on", "on").pivot(on=["prev_on", "on"], index="group", values="on_next"))
print("\nAcross a drive break: on at the first snap of a drive, by on at the last snap of the previous drive:")
first = X.filter(c("prev_drive") != c("fixed_drive"))
print(first.group_by("group", "prev_on").agg(on=c("on").mean(), n=pl.len()).sort("group", "prev_on").pivot(on="prev_on", index="group", values="on"))
print("within a drive, the same:")
inner = X.filter(c("prev_drive") == c("fixed_drive"))
print(inner.group_by("group", "prev_on").agg(on=c("on").mean()).sort("group", "prev_on").pivot(on="prev_on", index="group", values="on"))
