"""Did the injury rule fix work? (2026-11-06) Reports at the Saturday run by season, each input
against the backtest, and the new rule against what our own pulls of nflverse's file really held.
Run from pcf/: .venv/Scripts/python.exe projects/prediction-ledger/explore/injury_fix_check.py [pcf-data clone]

Nothing is scored, so the 2025 vault stays closed: its rows are only counted.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.data.sources.store import ChangeLog
from pcf.data.tables.build import _schedules
from pcf.data.timeline.calendar import calendar
from pcf.data.timeline.known_at import _injury_fallback
from pcf.validation import backtest
from pcf.validation.inputs import input_check
from pcf.validation.splits import steps

c = pl.col
NOW = datetime.now(UTC)
SEASON = 2026


def after_fix(variant: str = "trees_week") -> None:
    e = find("participation", variant)()
    gw = Gateway()
    every = steps(gw.calendar, e.cadence, range(2022, SEASON + 1), e.run, e.event)
    use = [s for s in every if s.week in (6, 7, 8) and s.at <= NOW]
    feats = backtest.feature_history(e, gw, use).with_columns(season=c("game_id").str.slice(0, 4))
    print("Rows with a report, weeks 6-8, at their moments")
    with pl.Config(tbl_rows=10, float_precision=1):
        print(
            feats.group_by("season")
            .agg(rows=pl.len(), with_report=(c("report") > 0).sum(),
                 per_100=(c("report") > 0).mean() * 100)
            .sort("season")
        )  # fmt: skip
    check = input_check(
        feats.filter(c("season") == "2024"), feats.filter(c("season") == str(SEASON)), e.columns
    )
    print(f"Input check, 2024 against {SEASON}: flagged {check['flag'].sum()} of {check.height}")
    with pl.Config(tbl_rows=10, float_precision=1, tbl_width_chars=120):
        print(check.head(8))


def against_pulls(clone: str) -> None:
    """Week 8 in our change logs: each row's first status in a pull, and the rule's time."""
    log = ChangeLog(Path(clone) / "raw/nflverse/_changes/injuries/injuries_2026")
    pulls = [(t, log.state(t)) for t, _, _ in log.entries()]
    cal = calendar(_schedules())
    kick = pl.concat(
        [
            cal.games.filter(c("season") == SEASON).select("week", team=c(t), kickoff="kickoff")
            for t in ("home_team", "away_team")
        ]
    ).with_columns(c("week").cast(pl.Int32))
    first = None
    for t, state in pulls:
        got = state.filter(c("report_status").is_not_null() & (c("week") == 8)).select(
            "team", "gsis_id", seen=pl.lit(t).cast(pl.Datetime("us", "UTC"))
        )
        first = (
            got
            if first is None
            else pl.concat([first, got]).group_by("team", "gsis_id").agg(c("seen").min())
        )
    d = first.join(kick.filter(c("week") == 8), on="team").with_columns(
        rule=_injury_fallback(c("kickoff"))
    )
    print("\nWeek 8 statuses: when our pulls first held them, and the rule's time")
    with pl.Config(tbl_rows=30, tbl_width_chars=120):
        print(
            d.group_by("kickoff", "rule", "seen")
            .agg(rows=pl.len(), teams=c("team").n_unique())
            .sort("kickoff")
        )


if __name__ == "__main__":
    after_fix()
    if len(sys.argv) > 1:
        against_pulls(sys.argv[1])
