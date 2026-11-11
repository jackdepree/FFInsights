"""The live run (projects/prediction-ledger/BRIEF.md): forecast the games due now with the ledger's
models, check their inputs, and write them to the ledger before kickoff.

It's the backtest's own code pointed at now. `feature_history` builds every step so far, each from
its own moment, `targets` gives the outcomes known so far, and `fit_at` fits at the run's moment on
outcomes known by then. So the model is refit each run, not once a season (brief, assumption 3).

A game is due when its prediction moment (decision 0010) has passed and it hasn't kicked off. So
the Thursday noon run forecasts Thursday's and Friday's games, and Saturday noon the rest of the
week. A run with nothing due writes nothing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import polars as pl

from pcf.config import get_config
from pcf.core import ledger
from pcf.core.contract import Expert, find
from pcf.core.log import get_logger
from pcf.data.gateway import Gateway
from pcf.data.timeline.calendar import ET
from pcf.data.timeline.moments import game_moments
from pcf.validation.backtest import HALF_LIFE, feature_history, fit_at, standard, targets
from pcf.validation.inputs import input_check
from pcf.validation.splits import Step, steps

log = get_logger(__name__)
c = pl.col
EASTERN = ZoneInfo(ET)  # `ET` is the zone's name, for polars; datetimes need the zone itself

# What the ledger forecasts, in run order. Participation first (prediction-ledger brief, decision
# 1): the four champions, one per horizon, and `last_game` as a yardstick; the first is run first,
# so on a tight Thanksgiving it's the one most likely to make kickoff. Then the live-experts brief
# (decision 1A, 2026-11-10): Elo's five finals (scored against the closing line, which needs no
# rows of its own) and schemes-v2's four trait finals, each with its season-to-date average as a
# yardstick. Then pace's 12 finals (2026-11-11), the same way. A new model joins with one line.
MODELS: list[tuple[str, str]] = [
    ("participation", "trees_week"),
    ("participation", "active"),
    ("participation", "lasso_h3"),
    ("participation", "lasso_rest"),
    ("participation", "last_game"),
    ("elo", "margin"),
    ("elo", "total"),
    ("elo", "win"),
    ("elo", "wins_next3"),
    ("elo", "wins_rest"),
    ("schemes-v2", "pass_oe_rung2"),
    ("schemes-v2", "shotgun_rung2"),
    ("schemes-v2", "depth_rung2"),
    ("schemes-v2", "tempo_shrunk"),
    ("schemes-v2", "pass_oe_season"),
    ("schemes-v2", "shotgun_season"),
    ("schemes-v2", "depth_season"),
    ("schemes-v2", "tempo_season"),
    # pace (the CEO, 2026-11-11: "add the 12 forecasts now"): volume first, then the habits,
    # then each one's season-to-date average as its yardstick
    ("pace", "plays_full"),
    ("pace", "dropbacks_full"),
    ("pace", "runs_full"),
    ("pace", "plays_neutral"),
    ("pace", "dropbacks_neutral"),
    ("pace", "runs_neutral"),
    ("pace", "pace_oe_shrunk"),
    ("pace", "proe_shrunk"),
    ("pace", "proe_1st_shrunk"),
    ("pace", "proe_2nd_shrunk"),
    ("pace", "proe_3rd_shrunk"),
    ("pace", "no_huddle_shrunk"),
    ("pace", "plays_season"),
    ("pace", "dropbacks_season"),
    ("pace", "runs_season"),
    ("pace", "pace_oe_season"),
    ("pace", "proe_season"),
    ("pace", "proe_1st_season"),
    ("pace", "proe_2nd_season"),
    ("pace", "proe_3rd_season"),
    ("pace", "no_huddle_season"),
]
# Bookkeeping columns `feature_history` adds: not inputs.
STEP_COLUMNS = ("step", "step_season", "step_week", "as_of")
# The input check compares a run with the same weeks of these many seasons before the live one.
CHECK_SEASONS = 3
# How long a failed refresh waits before its one retry.
RETRY_SECONDS = 60


@dataclass
class Forecast:
    expert: Expert
    rows: pl.DataFrame  # standard output plus kickoff, for the due games
    checks: pl.DataFrame  # the input check
    seconds: dict[str, float]


def due_games(gateway: Gateway, run: str, now: datetime) -> pl.DataFrame:
    """The live season's games whose moment has passed and whose kickoff hasn't: game_id, season,
    week, kickoff, moment."""
    season = get_config().seasons.live
    return (
        game_moments(gateway.calendar, run)
        .filter((c("season") == season) & (c("moment") <= now) & (c("kickoff") > now))
        .select("game_id", "season", "week", "kickoff", "moment")
        .sort("moment", "game_id")
    )


def steps_so_far(expert: Expert, gateway: Gateway, now: datetime) -> list[Step]:
    """Every step from the expert's first training season through now, each holding only the games
    whose moment has passed."""
    cfg = get_config().seasons
    first = max(cfg.first_train, expert.first_train or 0)
    every = steps(gateway.calendar, expert.cadence, range(first, cfg.live + 1), expert.run)
    out = []
    for s in every:
        games = s.games.filter(c("moment") <= now)
        if games.height:
            out.append(replace(s, games=games))
    return out


def forecast(
    expert: Expert,
    gateway: Gateway,
    now: datetime,
    run_id: str,
    feats: pl.DataFrame | None = None,
) -> Forecast | None:
    """The expert's forecasts for the games due at `now`, or None if none are due. Uses data only
    through the gateway, at each game's moment, as the backtest does. `feats` (the replay) is a
    feature history built once for a later moment: a row's features depend only on its own moment,
    so its rows up to `now` are the ones a run at `now` would build."""
    due = due_games(gateway, expert.run, now)
    if due.is_empty():
        return None
    seconds = {}
    start = time.perf_counter()
    if feats is None:
        feats = feature_history(expert, gateway, steps_so_far(expert, gateway, now))
    else:
        feats = feats.filter(c("as_of") <= now)
    seconds["features"] = time.perf_counter() - start
    start = time.perf_counter()
    keys = expert.keys()
    pool = feats.join(targets(expert, gateway), on=keys, how="inner")
    season = get_config().seasons.live
    out = []
    for (moment,), games in due.group_by("moment", maintain_order=True):
        model, train_end = fit_at(expert, pool, moment, season, HALF_LIFE)
        rows = feats.filter(c("game_id").is_in(games["game_id"].implode())).sort(*keys)
        if rows.is_empty():
            continue
        pred = expert.predict(model, rows)
        out.append(
            pred.join(rows.select(*keys, "as_of", "step"), on=keys, how="left").with_columns(
                train_end=pl.lit(train_end).cast(pl.Datetime("us", "UTC"))
            )
        )
    seconds["fit_predict"] = time.perf_counter() - start
    if not out:
        log.warning("%s: games are due but have no rows", expert.label())
        return None
    rows = (
        standard(expert, pl.concat(out, how="diagonal_relaxed"), run_id=run_id, version="live")
        .drop("step")
        .join(due.select("game_id", "kickoff"), on="game_id", how="left")
    )
    live = feats.filter(c("game_id").is_in(due["game_id"].implode()))
    if expert.publishes:  # what higher layers read with the forecast, as in the backtest history
        rows = rows.join(
            live.select(*keys, "as_of", *expert.publishes), on=[*keys, "as_of"], how="left"
        )
    return Forecast(expert, rows, check_inputs(expert, feats, live), seconds)


def check_inputs(expert: Expert, feats: pl.DataFrame, live: pl.DataFrame) -> pl.DataFrame:
    """The input check (VALIDATION.md §9): the due rows against the same weeks and the same run
    day in the seasons just before the live one."""
    season = get_config().seasons.live
    day = lambda: c("as_of").dt.convert_time_zone(ET).dt.weekday()  # noqa: E731
    days = live.select(day().unique())["as_of"].to_list()
    past = feats.filter(
        c("step_season").is_between(season - CHECK_SEASONS, season - 1)
        & c("step_week").is_in(live["step_week"].unique().implode())
        & day().is_in(days)
    )
    columns = getattr(expert, "columns", None) or [
        x for x in live.columns if x not in (*expert.keys(), *STEP_COLUMNS)
    ]
    return input_check(past, live, [x for x in columns if x in live.columns])


# --------------------------------------------------------------------------------- data pull


def pull(live_season: int) -> dict[str, Any]:
    """Refresh nflverse and rebuild the live season's tables. Returns when, and how fresh the
    files that matter most were."""
    from pcf.data.sources.nflverse import refresh
    from pcf.data.tables import build

    try:
        summary = refresh()
    except RuntimeError as err:
        # nflverse sometimes replaces a file while we download it, so its content no longer
        # matches the fingerprint we listed (live-experts, 2026-11-10). Listing again a minute
        # later fixes it; a second failure is real.
        log.warning("refresh failed (%s); trying again in %d seconds", err, RETRY_SECONDS)
        time.sleep(RETRY_SECONDS)
        summary = refresh()
    build(seasons=[live_season])
    pulled_at = datetime.now(UTC)
    return {"pulled_at": pulled_at, "downloaded": summary.downloaded, **freshness(live_season)}


def freshness(live_season: int) -> dict[str, Any]:
    """When nflverse last changed the live season's injury, roster and schedule files, and when we
    fetched them, from the refresh manifest."""
    from pcf.data.sources.store import Manifest

    m = Manifest(get_config().zone("raw") / "nflverse" / "_manifest").read()
    out = {}
    for dataset in ("injuries", "weekly_rosters", "schedules"):
        rows = m.filter(c("dataset") == dataset).filter(
            c("season").is_null() | (c("season") == live_season)
        )
        if rows.is_empty():
            out[dataset] = None
            continue
        last = rows.sort("run_at").row(-1, named=True)
        out[dataset] = {
            "file_updated": last["upstream_updated_at"],
            "fetched": last["run_at"],
        }
    return out


def wait_for_injuries(
    now: datetime, first_kickoff: datetime, live_season: int, every_minutes: int = 10
) -> dict[str, Any]:
    """On a Thursday or Saturday run, wait for the day's injury file if it hasn't landed yet:
    nflverse updates it once each morning (prediction-ledger#F8). Gives up an hour after the run
    starts or 45 minutes before the first kickoff, whichever comes first, and says so in the
    record."""
    if now.astimezone(EASTERN).weekday() not in (3, 5):  # Thursday, Saturday
        return {"waited_minutes": 0, "injury_file_today": None}
    today = now.astimezone(EASTERN).replace(hour=0, minute=0, second=0, microsecond=0)
    deadline = min(now + timedelta(hours=1), first_kickoff - timedelta(minutes=45))
    from pcf.data.sources.nflverse import refresh

    start = datetime.now(UTC)
    while True:
        info = freshness(live_season)["injuries"]
        updated = info["file_updated"] if info else None
        if updated is not None and updated >= today:
            break
        if datetime.now(UTC) + timedelta(minutes=every_minutes) > deadline:
            log.warning("injury file not updated today by %s; running without it", deadline)
            break
        log.info(
            "injury file last updated %s; checking again in %d minutes", updated, every_minutes
        )
        time.sleep(every_minutes * 60)
        refresh(["injuries"], [live_season])
    waited = (datetime.now(UTC) - start).total_seconds() / 60
    if waited > 0.5:
        from pcf.data.tables import build

        build(["player_game"], [live_season])
    return {
        "waited_minutes": round(waited, 1),
        "injury_file_today": updated is not None and updated >= today,
    }


# ------------------------------------------------------------------------------------ one run


def trial(send: bool):
    """Where a run that isn't pushed goes: a local trial folder, never the pcf-data clone, so an
    unpushed run can't be mistaken for a record."""
    return None if send else get_config().zone("ledger") / "trial"


def run(
    record: str = "live",
    now: datetime | None = None,
    models: list[tuple[str, str]] | None = None,
    refresh: bool = True,
    send: bool = True,
    label: str | None = None,
) -> ledger.Run | None:
    """One live run: pull, forecast every model's due games, write them, push. Returns the run, or
    None when nothing is due. A live run refuses to start from code that isn't committed."""
    started = datetime.now(UTC)
    now = now or started
    cfg = get_config()
    season = cfg.seasons.live
    code = ledger.code_state()
    if record == "live" and code["dirty"]:
        raise ledger.LedgerRefused(f"uncommitted code changes: {', '.join(code['dirty'])}")
    experts = [find(i, v)() for i, v in models or MODELS]
    gateway = Gateway()
    runs = {e.run for e in experts}
    due = pl.concat([due_games(gateway, r, now) for r in runs]).unique("game_id")
    if due.is_empty():
        log.info("nothing due at %s", now)
        return None
    pulled: dict[str, Any] = {"pulled_at": None}
    if refresh:
        pulled = pull(season)
        if record == "live":
            pulled.update(wait_for_injuries(now, due["kickoff"].min(), season))
        gateway = Gateway()
    if send:
        ledger.ensure_clone()
    label = label or now.astimezone(EASTERN).strftime("%a").lower()
    out = ledger.open_run(
        season, label, started, code["commit"], pulled["pulled_at"], record, trial(send)
    )
    checks, seconds, failed = {}, {}, {}
    for expert in experts:
        name = expert.label()
        try:
            f = forecast(expert, gateway, now, out.name)
        except Exception as err:  # one model failing mustn't stop the others reaching kickoff
            log.exception("%s failed", name)
            failed[name] = repr(err)
            continue
        if f is None:
            continue
        out.write(name, f.rows, expert.keys(), expert.kind, publishes=expert.publishes)
        flagged = f.checks.filter(c("flag"))
        checks[name] = {
            "flagged": flagged["input"].to_list(),
            "table": f.checks.to_dicts(),
        }
        seconds[name] = {k: round(v, 1) for k, v in f.seconds.items()}
        if flagged.height:
            log.warning("%s: input check flags %s", name, flagged["input"].to_list())
    out.close(
        {
            "now": now.isoformat(),
            "branch": code["branch"],
            "data": pulled,
            "due_games": due.sort("kickoff")["game_id"].to_list(),
            "input_check": checks,
            "seconds": seconds,
            "failed": failed,
        }
    )
    if send:
        sha = ledger.push(out.folder, f"{record} run {out.name}")
        log.info("pushed %s to pcf-data at %s", out.name, sha[:12])
    if failed:
        raise RuntimeError(f"models failed: {failed}")
    return out


def replay(
    weeks: list[int],
    models: list[tuple[str, str]] | None = None,
    send: bool = True,
) -> ledger.Run:
    """Forecasts remade now for the live season's played `weeks`, at each game's own moment, in a
    file marked as a replay (brief, decision 2). Never counted as a record. Uses the data as it is
    now, cut at each moment by the known-at rules, as the backtest does."""
    started = datetime.now(UTC)
    cfg = get_config()
    season = cfg.seasons.live
    code = ledger.code_state()
    experts = [find(i, v)() for i, v in models or MODELS]
    gateway = Gateway()
    if send:
        ledger.ensure_clone()
    label = f"weeks{min(weeks)}-{max(weeks)}"
    out = ledger.open_run(season, label, started, code["commit"], started, "replay", trial(send))
    seconds = {}
    for expert in experts:
        moments = (
            game_moments(gateway.calendar, expert.run)
            .filter((c("season") == season) & c("week").is_in(weeks) & (c("kickoff") <= started))
            .select("moment")
            .unique()
            .sort("moment")["moment"]
            .to_list()
        )
        t = time.perf_counter()
        feats = feature_history(expert, gateway, steps_so_far(expert, gateway, moments[-1]))
        rows = []
        for moment in moments:
            f = forecast(expert, gateway, moment, out.name, feats)
            if f is not None:
                rows.append(f.rows.filter(c("as_of") == moment))
        if not rows:
            continue
        out.write(
            expert.label(),
            pl.concat(rows),
            expert.keys(),
            expert.kind,
            now=started,
            publishes=expert.publishes,
        )
        seconds[expert.label()] = round(time.perf_counter() - t, 1)
    out.close(
        {
            "weeks": weeks,
            "branch": code["branch"],
            "dirty": code["dirty"],
            "seconds": seconds,
            "note": "A replay: remade after the games, never counted as a record.",
        }
    )
    if send:
        ledger.push(out.folder, f"replay {out.name}")
    return out
