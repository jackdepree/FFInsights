"""context-live's back-history: its expectations for 2017-2024, walk-forward, from fields every
season since 2016 has (decision 0038; skill-over-expected's H84).

The shipped context-live reads FTN's call fields, which start in 2022, so its history starts in
2023. The back-history keeps the method (one model per outcome, fit once per test season on the
earlier seasons, recency-weighted) and changes only the fields, in two editions:

- **situation:** the situation fields alone (`plays.SITUATION`), each outcome on the situation rung
  the 2023-2024 backtest chose (linear or trees). In-season: everything is known after the game.
- **calls16:** the situation plus the calls charted since 2016: the play-by-play's shotgun and
  no-huddle, and participation's pass rushers and defenders in the box. Participation is published
  after the season, so this edition is **retrospective** (rule m) and never feeds an in-season
  model. Method as the shipped live rung (linear for pressure and sack, trees for the rest).

Training seasons start in 2016, the first season of participation. Pressure and time to throw
changed provider in 2023 (`context-live#R12`): test seasons through 2023 train on 2016 onwards (so
2023 trains on the old provider only); 2024 trains on 2023 alone. A user of these rows takes each
season's league level out before comparing seasons. The 2025 vault is never read.

    python -m pcf.experts.context_live.back --edition situation
    python -m pcf.experts.context_live.back --edition calls16
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Sequence
from datetime import datetime

import polars as pl

from pcf.config import get_config
from pcf.core.log import get_logger
from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.context_live import models, plays, run
from pcf.experts.context_live.outcomes import BY_NAME, Outcome
from pcf.validation.backtest import check_seasons

log = get_logger(__name__)
c = pl.col
FIRST = 2016  # participation's first season
TEST = tuple(range(2017, 2025))
NEW_PROVIDER = 2023  # participation's pressure and time to throw (context-live#R12)
OUTCOMES = ("pressure_prob", "sack_prob", "completion_prob", "time_to_throw_exp",
            "air_yards_exp", "rush_yards_exp")  # fmt: skip
PARTICIPATION_OUTCOMES = ("pressure_prob", "time_to_throw_exp")
CALLS16 = ["shotgun", "no_huddle", "rushers_p", "box_p"]
EDITIONS = {"situation": plays.SITUATION, "calls16": plays.SITUATION + CALLS16}
CADENCE = {"situation": "in_season", "calls16": "retrospective"}
# The 2023-2024 backtest's choices (projects/context-live/RESULTS.md): the situation rung, and
# the shipped live rung's method.
SITUATION_METHOD = {"pressure_prob": "linear", "sack_prob": "linear", "completion_prob": "linear",
                    "time_to_throw_exp": "trees", "air_yards_exp": "trees",
                    "rush_yards_exp": "trees"}  # fmt: skip
CALLS_METHOD = {"pressure_prob": "linear", "sack_prob": "linear", "completion_prob": "trees",
                "time_to_throw_exp": "trees", "air_yards_exp": "trees",
                "rush_yards_exp": "trees"}  # fmt: skip


def cache_dir():
    return run.cache_dir() / "back"


def season_table(season: int, as_of: pl.DataFrame) -> pl.DataFrame:
    """One season's plays: the play-by-play frame (no FTN), participation's pressure and time to
    throw from 2016, and its pass rushers and box count; `as_of` the game's, and the later of it
    and participation's known_at for the retrospective edition (`as_of_retro`)."""
    gw = Gateway(TableSource(seasons=[season - 1, season]))
    view = gw.view(END_OF_TIME, "in_season", {"play": ("pbp",)})
    out = plays.frame(view.table("play", seasons=[season]))
    part = gw.view(END_OF_TIME, "retrospective", plays.TARGETS).table("play", seasons=[season])
    known = "participation_known_at" if "participation_known_at" in part.columns else "known_at"
    part = part.select(
        c("game_id"),
        c("play_id").cast(pl.Int64),
        pressure_y=c("was_pressure").cast(pl.Float64),
        time_to_throw_y=c("time_to_throw").cast(pl.Float64),
        rushers_p=c("number_of_pass_rushers").cast(pl.Float64),
        box_p=c("defenders_in_box").cast(pl.Float64),
        known_at_targets=c(known),
    )
    out = out.join(part, on=plays.KEYS, how="left").join(as_of, on="game_id", how="left")
    if out["as_of"].null_count():
        raise ValueError(f"{season}: {out['as_of'].null_count()} plays have no as_of")
    return out.with_columns(
        as_of_retro=pl.max_horizontal("as_of", "known_at_targets"),
        known_at_targets=c("known_at_targets").fill_null(c("known_at")),
    )


def prepare(seasons: Sequence[int], rebuild: bool = False) -> None:
    cache_dir().mkdir(parents=True, exist_ok=True)
    as_of = None
    for s in seasons:
        path = cache_dir() / f"plays_{s}.parquet"
        if path.exists() and not rebuild:
            continue
        if as_of is None:
            as_of = run.moments(Gateway())
        season_table(s, as_of).write_parquet(path)
        log.info("context-live back: season %d", s)


def load(seasons: Sequence[int]) -> pl.DataFrame:
    return pl.concat([pl.read_parquet(cache_dir() / f"plays_{s}.parquet") for s in seasons])


def outcome(name: str) -> Outcome:
    """The shipped outcome, from 2016 (participation's two from 2016 too)."""
    return dataclasses.replace(BY_NAME[name], first_season=FIRST)


def train_seasons(name: str, season: int) -> tuple[int, int]:
    """The first and last training season for a test season (the provider rule)."""
    if name in PARTICIPATION_OUTCOMES and season > NEW_PROVIDER:
        return NEW_PROVIDER, season - 1
    return FIRST, season - 1


def walk(data: pl.DataFrame, name: str, edition: str, seasons: Sequence[int] = TEST):
    """The edition's held-out expectations for one outcome: keys, season, week, as_of, y, mean (and
    q10-q90 for an amount), with the train_end per season; and each season's share of the
    season rate's squared error the expectation removes."""
    o = outcome(name)
    fields = EDITIONS[edition]
    method = (SITUATION_METHOD if edition == "situation" else CALLS_METHOD)[name]
    out, shares = [], {}
    for s in seasons:
        lo, hi = train_seasons(name, s)
        train = run.training_rows(data.filter(c("season") >= lo), o, s)
        train = train.filter(c("season") <= hi)
        m = models.fit(run.with_weights(train, s), o, fields, method, calibrate=o.recalibrate)
        test = o.rows(data.filter(c("season") == s))
        pred = m.predict(test)
        when = c("as_of_retro") if edition == "calls16" else c("as_of")
        rows = test.select(*plays.KEYS, "season", "week", "y", as_of=when)
        rows = rows.with_columns([pred[x] for x in pred.columns]).with_columns(
            train_end=pl.lit(run.train_end(train)).cast(run.UTC_TIME)
        )
        # with the season's level taken out, as the module note says a user reads these rows
        y, e = rows["y"], rows["mean"]
        base = ((y - y.mean()) ** 2).sum()
        shares[s] = float(100 * (1 - ((y - y.mean() - (e - e.mean())) ** 2).sum() / base))
        out.append(rows)
    return pl.concat(out), shares


def history(edition: str, names: Sequence[str] = OUTCOMES, seasons: Sequence[int] = TEST) -> dict:
    """Every outcome's back-history for an edition, in the standard schema, logged as one MLflow
    attempt and saved as outputs/context-live/<run_id>/back_<edition>.parquet."""
    import mlflow

    from pcf.core import tracking

    check_seasons(list(seasons), False)
    prepare(range(FIRST, max(seasons) + 1))
    data = load(range(FIRST, max(seasons) + 1))
    end = data.filter(c("season") < max(seasons)).select(run.known(data).max()).item()
    params = {"edition": edition, "seasons": f"{min(seasons)}-{max(seasons)}",
              "fields": ",".join(EDITIONS[edition])}  # fmt: skip
    report: dict = {"edition": edition, "cadence": CADENCE[edition], "share_removed": {}}
    frames = []
    with tracking.attempt(run.ID, train_end=end, name=f"back {edition}", params=params) as r:
        for name in names:
            rows, shares = walk(data, name, edition, seasons)
            report["share_removed"][name] = shares
            mlflow.log_metrics({f"{name}.share.{s}": v for s, v in shares.items()})
            q = {x: (c(x) if x in rows.columns else c("mean")) for x in models.LEVELS}
            frames.append(rows.select(
                *plays.KEYS, "season", "week", as_of=c("as_of").cast(run.UTC_TIME),
                quantity=pl.lit(name), mean=c("mean"), **q, model=pl.lit(run.ID),
                model_version=pl.lit(f"back-{edition}"), run_id=pl.lit(r.info.run_id),
                train_end=c("train_end"), cadence=pl.lit(CADENCE[edition]),
            ))  # fmt: skip
            log.info("context-live back %s %s: %s", edition, name, shares)
        path = get_config().zone("outputs") / run.ID / r.info.run_id / f"back_{edition}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        pl.concat(frames).write_parquet(path)
        report["run_id"], report["path"] = r.info.run_id, str(path)
        report["made"] = datetime.now().isoformat(timespec="seconds")
        mlflow.log_text(json.dumps(report, indent=1), "back.json")
    (cache_dir() / f"back_{edition}.json").write_text(json.dumps(report, indent=1))
    return report


def main(argv: Sequence[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m pcf.experts.context_live.back")
    ap.add_argument("--edition", choices=sorted(EDITIONS), required=True)
    ap.add_argument("--outcomes", default=",".join(OUTCOMES))
    a = ap.parse_args(argv)
    rep = history(a.edition, [x for x in a.outcomes.split(",") if x])
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
