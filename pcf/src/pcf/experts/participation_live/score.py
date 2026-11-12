"""Scores for a reconstructed season (the brief's tests), on play-sides whose true lineup has 11.

- **Per play:** the share of the true open-spot players the best guess names (`open_right`),
  of all 11 (`of_11`), plays with all 11 right (`all_11`).
- **Chances:** log loss on open cells, calibration error (10 bins, weighted, in points) and slope.
- **Sanity:** chances add to 11 a play, best guesses have 11, each player's totals against his
  snap target and his true total.
- **Fit for use:** players changed between consecutive snaps of a drive, per team-game, from the
  best guess against the truth.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.experts.participation_live.grid import SIDE_KEYS

c = pl.col
EPS = 1e-4


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, EPS, 1 - EPS)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def calibration(p: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """(error in points, slope): the bins' weighted gap between chance and rate, and the slope
    of the rate's log-odds on the chance's (1 is right; below 1 is overconfident)."""
    bins = np.clip((p * 10).astype(int), 0, 9)
    err = 0.0
    for b in range(10):
        m = bins == b
        if m.any():
            err += m.mean() * abs(p[m].mean() - y[m].mean())
    z = np.log(np.clip(p, EPS, 1 - EPS) / (1 - np.clip(p, EPS, 1 - EPS)))
    # one Newton fit of y on (1, z)
    w = np.array([0.0, 1.0])
    x = np.column_stack([np.ones_like(z), z])
    for _ in range(25):
        q = 1 / (1 + np.exp(-(x @ w)))
        h = x.T @ (x * (q * (1 - q))[:, None]) + 1e-9 * np.eye(2)
        w += np.linalg.solve(h, x.T @ (y - q))
    return 100 * err, float(w[1])


def scored(test: pl.DataFrame) -> pl.DataFrame:
    return test.filter(c("full_truth"))


def per_play(test: pl.DataFrame, kind: str, best: str | None = None) -> dict[str, float]:
    """The per-play scores for one rung, by side (`best`: the lineup column, `best_<kind>`)."""
    t = scored(test)
    out: dict[str, float] = {}
    best = best or f"best_{kind}"
    for side in ("offense", "defense"):
        s = t.filter(c("side") == side)
        if s.is_empty():
            continue
        y = s["on"].to_numpy().astype(float)
        op = ~s["pinned"].to_numpy()
        p = s[f"p_{kind}"].to_numpy().astype(float)
        out[f"{side}_log_loss"] = log_loss(p[op], y[op])
        err, slope = calibration(p[op], y[op])
        out[f"{side}_calibration_pts"] = err
        out[f"{side}_calibration_slope"] = slope
        if best in s.columns:
            b = s[best].to_numpy()
            out[f"{side}_open_right"] = float(
                (b & op & (y == 1)).sum() / max((op & (y == 1)).sum(), 1)
            )
            per = s.group_by("game_id", "play_id").agg(hit=(c(best) & (c("on") == 1)).sum())
            out[f"{side}_of_11"] = float(per["hit"].sum() / (per.height * 11))
            out[f"{side}_all_11"] = float((per["hit"] == 11).mean())
    return out


def certainty(test: pl.DataFrame, kind: str, lineup: str | None = None) -> pl.DataFrame:
    """Is each play's `certainty` (the lineup's expected share right, `chain.lineup_certainty`)
    honest? Per side and tenth of plays by certainty: plays, mean certainty, mean share right."""
    from pcf.experts.participation_live.chain import lineup_certainty

    lineup = lineup or f"top_{kind}"
    t = lineup_certainty(scored(test).with_columns(p=c(f"p_{kind}")), lineup)
    per = t.group_by("game_id", "play_id", "side").agg(
        certainty=c("certainty").first(), right=(c(lineup) & (c("on") == 1)).sum() / 11
    )
    per = per.with_columns(
        tenth=(c("certainty").rank("ordinal").over("side") * 10 / pl.len().over("side"))
        .ceil()
        .clip(1, 10)
        .cast(pl.Int8)
    )
    return (
        per.group_by("side", "tenth")
        .agg(plays=pl.len(), certainty=c("certainty").mean(), right=c("right").mean())
        .sort("side", "tenth")
    )


def by_group(test: pl.DataFrame, kind: str, best: str | None = None) -> pl.DataFrame:
    """Open-spot accuracy and log loss per position group."""
    t = scored(test).filter(~c("pinned"))
    best = best or f"best_{kind}"
    aggs = [pl.len().alias("open_cells")]
    if best in t.columns:
        aggs.append(((c(best) & (c("on") == 1)).sum() / (c("on") == 1).sum()).alias("open_right"))
    p = c(f"p_{kind}").clip(EPS, 1 - EPS)
    aggs.append((-(c("on") * p.log() + (1 - c("on")) * (1 - p).log())).mean().alias("log_loss"))
    return t.group_by("side", "group").agg(aggs).sort("side", "group")


def sanity(test: pl.DataFrame, kind: str, best: str | None = None) -> dict[str, float]:
    """Totals: chances per play against 11, best guesses with 11, players' totals."""
    best = best or f"best_{kind}"
    p = f"p_{kind}"
    plays = test.group_by("game_id", "play_id", "side").agg(sp=c(p).sum(), sb=c(best).sum())
    cols = test.group_by(*SIDE_KEYS, "gsis_id").agg(
        sp=c(p).sum(),
        sb=c(best).sum(),
        target=c("share").first() * c("n_plays").first(),
    )
    # the targets as the model used them: scaled so each side's add to 11 a snap
    scale = cols.join(
        test.group_by(SIDE_KEYS).agg(n=c("play_id").n_unique()), on=SIDE_KEYS
    ).with_columns(target=c("target") * 11 * c("n") / c("target").sum().over(SIDE_KEYS))
    out = {
        "plays_chance_off_11": float((plays["sp"] - 11).abs().mean()),
        "plays_best_has_11": float((plays["sb"] == 11).mean()),
        "players_chance_off_target": float((scale["sp"] - scale["target"]).abs().mean()),
        "players_best_off_target": float((scale["sb"] - scale["target"]).abs().mean()),
        "players_best_within_1": float(((scale["sb"] - scale["target"]).abs() <= 1.0).mean()),
    }
    t = scored(test)
    if t.height:
        tc = t.group_by(*SIDE_KEYS, "gsis_id").agg(
            sb=c(best).sum(), sp=c(p).sum(), true=c("on").sum()
        )
        out["players_best_off_true"] = float((tc["sb"] - tc["true"]).abs().mean())
        out["players_chance_off_true"] = float((tc["sp"] - tc["true"]).abs().mean())
    return out


def substitution(test: pl.DataFrame, kind: str, best: str | None = None) -> dict[str, float]:
    """Players changed between consecutive snaps of a drive, per team-game-side: the best guess's
    against the truth (mean of each, and their correlation across team-games)."""
    best = best or f"best_{kind}"
    t = scored(test).sort(*SIDE_KEYS, "gsis_id", "n")
    key = [*SIDE_KEYS, "gsis_id"]
    t = t.with_columns(
        b_prev=c(best).shift(1).over(key),
        y_prev=c("on").shift(1).over(key),
        n_prev=c("n").shift(1).over(key),
    ).filter(c("sd") & (c("n_prev") == c("n") - 1))
    # a change is a player coming on (each one coming on replaces one going off)
    per = t.group_by(*SIDE_KEYS, "play_id").agg(
        b=(c(best) & ~c("b_prev")).sum(), y=((c("on") == 1) & (c("y_prev") == 0)).sum()
    )
    team = per.group_by(SIDE_KEYS).agg(c("b").mean(), c("y").mean())
    return {
        "subs_per_snap_best": float(per["b"].mean()),
        "subs_per_snap_true": float(per["y"].mean()),
        "subs_team_game_r": float(np.corrcoef(team["b"], team["y"])[0, 1])
        if team.height > 2
        else float("nan"),
    }
