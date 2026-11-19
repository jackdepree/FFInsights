"""Plays like this one (the brief's method C): for each play, the `K` most similar earlier plays
of the same population and what happened on them. A second, non-default output beside the main
models (the CEO, 2026-11-19: "should be shown. It doesn't have to be the default... I think that
can be very powerful in the future for a feature for downstream models. So I would say keep it").

It is weaker than one model per outcome for every outcome tried (RESULTS R8: 0.3 to 3.5 points of
share behind), but every outcome comes from the same plays, so the outcomes agree with each other
and the forecast can be said out loud: "on the 300 plays most like this one, the back was stuffed
31% of the time" (decision 0036, call 20).

- **Similar:** the live call fields (the situation fields for the situation-only outcomes), each
  on one standardized scale from the training plays, a missing value filled with the training
  median plus a column saying it was missing; plain distance.
- **Earlier plays:** the population's plays from the seasons before the test season, known before
  its first `as_of` (the same rule as the models). An outcome's forecast is the average over the
  neighbours whose result is recorded (pressure and time to throw: only from 2023).
- **Output:** the standard schema, `model_version` `plays-like-this-k300`, beside the main history:
  `neighbours_history.parquet` (walk-forward) and `neighbours_live.parquet` in the champion's
  outputs folder.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import numpy as np
import polars as pl

from pcf.experts.context_live import plays
from pcf.experts.context_live.models import LEVELS, matrix
from pcf.experts.context_live.outcomes import OUTCOMES, Outcome

c = pl.col
K = 300
VERSION = f"plays-like-this-k{K}"


def design(train: pl.DataFrame, test: pl.DataFrame, fields: list[str]) -> tuple[np.ndarray, ...]:
    """Both frames on the training plays' standardized scale, with a missing-value column for
    every field that has any missing value in training."""
    xa, xb = matrix(train, fields), matrix(test, fields)
    miss_a, miss_b = np.isnan(xa), np.isnan(xb)
    keep = miss_a.any(axis=0)
    med = np.nanmedian(np.where(miss_a.all(axis=0), 0.0, xa), axis=0)
    xa, xb = np.where(miss_a, med, xa), np.where(miss_b, med, xb)
    mu, sd = xa.mean(axis=0), xa.std(axis=0)
    sd[sd == 0] = 1.0
    xa, xb = (xa - mu) / sd, (xb - mu) / sd
    return (
        np.hstack([xa, miss_a[:, keep].astype(float)]),
        np.hstack([xb, miss_b[:, keep].astype(float)]),
    )


def neighbours(train: pl.DataFrame, test: pl.DataFrame, fields: list[str], k: int = K):
    """Row numbers in `train` of each test play's `k` nearest plays."""
    from sklearn.neighbors import NearestNeighbors

    xa, xb = design(train, test, fields)
    k = min(k, xa.shape[0])
    return NearestNeighbors(n_neighbors=k).fit(xa).kneighbors(xb, return_distance=False)


def _summary(y: np.ndarray, idx: np.ndarray, kind: str) -> dict[str, np.ndarray]:
    near = y[idx]  # test plays x k, NaN where the neighbour's result isn't recorded
    out = {"mean": np.nanmean(near, axis=1)}
    if kind == "amount":
        for q, level in LEVELS.items():
            out[q] = np.nanquantile(near, level, axis=1)
    else:
        out.update({q: out["mean"] for q in LEVELS})
    return out


def _groups(names: Sequence[str] | None) -> dict[tuple[str, int, bool], list[Outcome]]:
    """Outcomes sharing a population, first season and field set share their neighbours."""
    out: dict[tuple[str, int, bool], list[Outcome]] = {}
    for o in OUTCOMES:
        if names is None or o.name in names:
            out.setdefault((o.population, o.first_season, o.situation_only), []).append(o)
    return out


def forecast(
    data: pl.DataFrame, season: int, train_end_at: datetime, run_id: str,
    names: Sequence[str] | None = None, test: pl.DataFrame | None = None, k: int = K,
) -> pl.DataFrame:  # fmt: skip
    """Every outcome's plays-like-this forecast for `season`'s plays (or `test`), from the
    population's plays of earlier seasons, in the standard schema."""
    from pcf.experts.context_live.run import ID, UTC_TIME, known

    test_all = data.filter(c("season") == season) if test is None else test
    first_as_of = data.filter(c("season") == season)["as_of"].min()
    rows = []
    for (_, _first, sit_only), group in _groups(names).items():
        o = group[0]
        train = o.rows(data.filter(c("season") < season), scored=False)
        tst = o.rows(test_all, scored=False)
        if train.is_empty() or tst.is_empty():
            continue
        late = train.filter(known(train) > first_as_of).height
        if late:
            raise ValueError(
                f"{o.population}: {late} neighbour plays weren't known by {first_as_of}"
            )
        fields = plays.FIELD_SETS["situation" if sit_only else "live"]
        idx = neighbours(train, tst, fields, k)
        for out in group:
            col = (
                train[out.column].cast(pl.Float64).to_numpy()
                if out.column in train.columns
                else None
            )
            if col is None or np.isnan(col).all():
                continue
            with np.errstate(all="ignore"):
                s = _summary(col, idx, out.kind)
            rows.append(tst.select(*plays.KEYS, "season", "week", "as_of").with_columns(
                as_of=c("as_of").cast(UTC_TIME), quantity=pl.lit(out.name),
                **{x: pl.Series(v) for x, v in s.items()},
                model=pl.lit(ID), model_version=pl.lit(VERSION), run_id=pl.lit(run_id),
                train_end=pl.lit(train_end_at).cast(UTC_TIME), cadence=pl.lit("in_season"),
            ))  # fmt: skip
    return pl.concat(rows, how="vertical") if rows else pl.DataFrame()


def write(version: int, seasons: Sequence[int], live: int) -> dict[str, str]:
    """The walk-forward history for `seasons` and the live season's plays known now, written beside
    the registered champion's outputs (outputs/context-live/<run_id>/neighbours_*.parquet)."""
    from pcf.config import get_config
    from pcf.core import tracking
    from pcf.experts.context_live.run import ID, known, load, prepare, train_end

    run_id = tracking.version_run(ID, version)
    prepare(range(plays.FIRST_SEASON, live + 1))
    data = load(range(plays.FIRST_SEASON, live + 1))
    folder = get_config().zone("outputs") / ID / run_id
    folder.mkdir(parents=True, exist_ok=True)
    hist = []
    for s in seasons:
        end = train_end(data.filter(c("season") < s))
        hist.append(forecast(data, s, end, run_id))
    pl.concat(hist, how="vertical").write_parquet(folder / "neighbours_history.parquet")
    now = datetime.now(UTC)
    test = data.filter(c("season") == live, c("as_of") <= now)
    end = data.filter(c("season") < live).select(known(data).max()).item()
    forecast(data, live, end, run_id, test=test).write_parquet(folder / "neighbours_live.parquet")
    return {"history": str(folder / "neighbours_history.parquet"),
            "live": str(folder / "neighbours_live.parquet")}  # fmt: skip
