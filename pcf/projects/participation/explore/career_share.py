"""CEO question (2026-11-03): does career snap share help, especially for players coming off an
injury or recently traded? Compares Saturday's inputs with and without longer-memory inputs, on
every row and on the rows the question is about.
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/career_share.py

Why the current inputs may struggle: an inactive game counts as share 0, so a starter back from a
four-game absence has a last-3 average of 0. Rows, split and model as profile_participation.py.
Snap counts start in 2013, so "career" means since 2013; scored seasons have 8+ years of it.
"""

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).parent))
from profile_participation import POS, SATURDAY, TEST, TRAIN, design, frame  # noqa: E402

c = pl.col
CAREER = ["career_avg", "career_active_avg", "career_games"]
ACTIVE = ["active_prev", "active_avg3", "active_avg8", "missed_streak"]
LAST_SEASON = ["last_season_active_avg"]
NEW_TEAM = ["changed_team", "games_on_team"]
SETS = {
    "career share": CAREER,
    "share when active": ACTIVE,
    "last season": LAST_SEASON,
    "all of them": [*CAREER, *ACTIVE, *LAST_SEASON, *NEW_TEAM],
}


def with_memory(df: pl.DataFrame) -> pl.DataFrame:
    """Every input is shifted one game: only earlier games count. `played` keeps the share only
    for active games, so an absence doesn't drag the average down."""
    g = ["gsis_id"]
    df = df.sort("gsis_id", "kickoff").with_columns(
        played=pl.when(c("active")).then(c("share")),
        absent=(~c("active")).cast(pl.Int32),
        prev_team=c("team").shift(1).over(g),
    )
    # Consecutive games missed before this one: reset by each active game
    df = df.with_columns(
        run=c("active").cum_sum().over(g),
        stint=(c("team") != c("prev_team")).fill_null(False).cum_sum().over(g),
    ).with_columns(streak=c("absent").cum_sum().over([*g, "run"]))
    # Averages over the last active games, skipping absences, carried to the rows after them
    played = df.filter(c("active")).select(
        "gsis_id", "game_id",
        a3=c("share").rolling_mean(3, min_samples=1).over(g),
        a8=c("share").rolling_mean(8, min_samples=1).over(g),
    )  # fmt: skip
    df = df.join(played, on=["gsis_id", "game_id"], how="left").sort("gsis_id", "kickoff")
    df = df.with_columns(
        missed_streak=c("streak").shift(1).over(g),
        career_avg=c("share").shift(1).cum_sum().over(g) / c("share").shift(1).cum_count().over(g),
        career_games=c("share").cum_count().over(g) - 1,
        # cum_sum is null where `played` is null, which is every game after an absence
        career_active_avg=c("played").fill_null(0.0).shift(1).cum_sum().over(g)
        / c("played").shift(1).cum_count().over(g),
        games_on_team=c("share").cum_count().over([*g, "stint"]) - 1,
        active_prev=c("played").forward_fill().shift(1).over(g),
        active_avg3=c("a3").forward_fill().shift(1).over(g),
        active_avg8=c("a8").forward_fill().shift(1).over(g),
        changed_team=(c("team") != c("prev_team")).fill_null(False).cast(pl.Float64),
    )
    last = (
        df.group_by("gsis_id", "season")
        .agg(last_season_active_avg=c("played").mean())
        .with_columns(season=c("season") + 1)
    )
    return df.join(last, on=["gsis_id", "season"], how="left")


def r2(y, p) -> float:
    return float(1 - ((y - p) ** 2).mean() / y.var())


def fit(a: pl.DataFrame, b: pl.DataFrame, cols: list[str]) -> np.ndarray:
    m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=0)
    m.fit(a.select(cols).to_numpy(), a["share"].to_numpy())
    return m.predict(b.select(cols).to_numpy()).clip(0, 1)


def if_active(tr: pl.DataFrame, te: pl.DataFrame) -> None:
    """The expert's second part (D3): the share if active, fit and judged on active rows only, so
    the chance of sitting out doesn't blur the comparison. Mean absolute error, with a 90%
    interval on the change from a bootstrap of players."""
    tr, te = tr.filter(c("active")), te.filter(c("active"))
    preds = {name: [] for name in ["now", *SETS]}
    frames = []
    for pos in POS:
        a, b = tr.filter(c("position") == pos), te.filter(c("position") == pos)
        frames.append(b)
        preds["now"].append(fit(a, b, SATURDAY))
        for name, cols in SETS.items():
            preds[name].append(fit(a, b, [*SATURDAY, *cols]))
    b = pl.concat(frames)
    p = {k: np.concatenate(v) for k, v in preds.items()}
    y = b["share"].to_numpy()
    miss = b["missed_streak"].fill_null(0).to_numpy()
    career = b["career_active_avg"].fill_null(0).fill_nan(0).to_numpy()
    new = (b["games_on_team"].to_numpy() <= 3) & (b["stint"].to_numpy() >= 1)
    groups = {
        "every active row": np.ones(len(y), dtype=bool),
        "back, missed 1-3": (miss >= 1) & (miss <= 3),
        "back, missed 4+": miss >= 4,
        "regular, back, missed 1-3": (miss >= 1) & (miss <= 3) & (career >= 0.5),
        "regular, back, missed 4+": (miss >= 4) & (career >= 0.5),
        "first 4 games on a new team": new,
        "same, regular": new & (career >= 0.5),
    }
    ids = b["gsis_id"].to_numpy()
    rng = np.random.default_rng(0)
    print("\nShare if active, on active rows: MAE in share points, and the change from each set")
    rows = []
    for g, mask in groups.items():
        row = {"group": g, "rows": int(mask.sum()), "mean share": y[mask].mean() * 100,
               "bias now": (p["now"][mask] - y[mask]).mean() * 100,
               "MAE now": np.abs(y[mask] - p["now"][mask]).mean() * 100}  # fmt: skip
        for name in SETS:
            row[name] = (np.abs(y[mask] - p[name][mask]) - np.abs(y[mask] - p["now"][mask])).mean() * 100
        # The best-looking set's interval, resampling whole players
        best = min(SETS, key=lambda n: row[n])
        d = (np.abs(y[mask] - p[best][mask]) - np.abs(y[mask] - p["now"][mask])) * 100
        people = pl.DataFrame({"id": ids[mask], "d": d}).group_by("id").agg(s=c("d").sum(), n=pl.len())
        s, n = people["s"].to_numpy(), people["n"].to_numpy()
        draws = rng.integers(0, len(s), (1000, len(s)))
        vals = s[draws].sum(1) / n[draws].sum(1)
        row["best"] = best
        row["best lo"], row["best hi"] = np.quantile(vals, [0.05, 0.95])
        rows.append(row)
    with pl.Config(float_precision=2, tbl_width_chars=250, tbl_cols=20, tbl_rows=20,
                   fmt_str_lengths=40):  # fmt: skip
        print(pl.DataFrame(rows))


def main() -> None:
    d = design(with_memory(frame())).with_columns(
        [c(x).cast(pl.Float64).fill_nan(None) for x in [*CAREER, *ACTIVE, *LAST_SEASON, *NEW_TEAM]]
    )
    extra = [*CAREER, *ACTIVE, *LAST_SEASON, *NEW_TEAM]
    # Trees take missing values as they are; the design's zeros stay for the existing inputs
    tr, te = d.filter(c("season").is_in(list(TRAIN))), d.filter(c("season").is_in(list(TEST)))
    preds = {name: [] for name in ["now", *SETS]}
    frames = []
    for pos in POS:
        a, b = tr.filter(c("position") == pos), te.filter(c("position") == pos)
        frames.append(b)
        preds["now"].append(fit(a, b, SATURDAY))
        for name, cols in SETS.items():
            preds[name].append(fit(a, b, [*SATURDAY, *cols]))
    b = pl.concat(frames)
    p = {k: np.concatenate(v) for k, v in preds.items()}
    y = b["share"].to_numpy()
    # The rows the question is about. Missing the last game doesn't mean back: `played` splits
    # those who returned (known only after the game: it judges the share if active)
    miss = b["missed_streak"].fill_null(0).to_numpy()
    career = b["career_active_avg"].fill_null(0).fill_nan(0).to_numpy()
    played = b["active"].to_numpy()
    on_team = b["games_on_team"].to_numpy()
    groups = {
        "every row": np.ones(len(y), dtype=bool),
        "missed last game (back or not)": miss >= 1,
        "back, missed 1-3": played & (miss >= 1) & (miss <= 3),
        "back, missed 4+": played & (miss >= 4),
        "regular (career 50%+), missed last": (miss >= 1) & (career >= 0.5),
        "regular, back, missed 1-3": played & (miss >= 1) & (miss <= 3) & (career >= 0.5),
        "regular, back, missed 4+": played & (miss >= 4) & (career >= 0.5),
        "first game on a new team": b["changed_team"].to_numpy() == 1,
        "first 4 games on a new team": (on_team <= 3) & (b["stint"].to_numpy() >= 1),
        "same, regular": (on_team <= 3) & (b["stint"].to_numpy() >= 1) & (career >= 0.5),
        "week 1": b["week"].to_numpy() == 1,
    }
    print(f"Fit {TRAIN.start}-{TRAIN.stop - 1}, scored {TEST.start}-{TEST.stop - 1}, "
          "R2 by group (each group's own variance)")  # fmt: skip
    rows = []
    for g, mask in groups.items():
        row = {"group": g, "rows": int(mask.sum()), "mean share": float(y[mask].mean()) * 100}
        for name, v in p.items():
            row[name] = r2(y[mask], v[mask])
        row["bias now"] = float((p["now"][mask] - y[mask]).mean()) * 100
        row["bias all"] = float((p["all of them"][mask] - y[mask]).mean()) * 100
        row["MAE now"] = float(np.abs(y[mask] - p["now"][mask]).mean()) * 100
        row["MAE all"] = float(np.abs(y[mask] - p["all of them"][mask]).mean()) * 100
        rows.append(row)
    with pl.Config(float_precision=3, tbl_width_chars=250, tbl_cols=20, tbl_rows=20,
                   fmt_str_lengths=40):  # fmt: skip
        print(pl.DataFrame(rows))
    if_active(tr, te)
    print("\nBy position, every row")
    for pos in POS:
        m = b["position"].to_numpy() == pos
        print(f"   {pos}: " + "  ".join(f"{k} {r2(y[m], v[m]):.3f}" for k, v in p.items()))
    assert all(x in d.columns for x in extra)


if __name__ == "__main__":
    main()
