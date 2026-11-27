# ruff: noqa: E501
"""Retro 5, the quick group: I4, players listed Questionable produce less than their history says (playing hurt).

On the yardstick (crude-forecaster's saved boards, next game, receiving and rushing; scored 2019-2024, the boards'
seasons; the 2025 vault is never read). The input: the player's final report status for the game, Questionable (1) or
not (0), and Doubtful as a second column; the same report participation reads (the boards' moment is the Saturday run,
after the final report). Scored through `yardstick.score_input` with 19 copies shuffled within each week, alone and
beside participation (the obvious input: participation's chance and share already read the report).
Then the miss itself: on rows listed Questionable who played (a snap), the crude forecast with participation, actual
less forecast, in yards, 90% interval from resampled weeks.

Odds, written before this script was run (2026-11-26). The row's own odds (2026-11-15, high: about 1 point of fantasy
points against box-score models) are for another target and aren't scored here. Claude, now:
- 30% the Questionable flag counts (interval above 0, beats all 19 copies) beside participation on receiving or
  rushing; 0.05-0.2% of the squared error if so;
- 55% the forecast with participation over-forecasts Questionable players who played (mean miss below 0, interval
  below 0), about 2-5 yards.
Run from pcf/ (PCF_DATA_DIR set), detached:
    python projects/retro/explore/retro5_i4_questionable.py > projects/retro/explore/retro5_i4_questionable.txt
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config

c = pl.col
T = get_config().zone("tables")
rng = np.random.default_rng(4)


def rd(p, cols, seasons):
    return pl.concat([pl.read_parquet(T / p / f"season={s}" / "data.parquet", columns=cols) for s in seasons], how="diagonal_relaxed")


def pct(x):
    return f"{100 * x:+.2f}%"


for target in ("receiving", "rushing"):
    board = Y.load_board(target, "next")
    keys = board.keys
    seasons = sorted(board.features["season"].unique().to_list()) if "season" in board.features.columns else list(range(2016, 2025))
    inj = rd("player_game/injury", ["gsis_id", "game_id", "report_status"], seasons)
    frame = board.features.select(keys).unique().join(inj.unique(["gsis_id", "game_id"]), on=["gsis_id", "game_id"], how="left").with_columns(
        q_flag=(c("report_status") == "Questionable").fill_null(False).cast(pl.Float64),
        d_flag=(c("report_status") == "Doubtful").fill_null(False).cast(pl.Float64),
    ).select(*keys, "q_flag", "d_flag")
    print(f"\n== {target}, next game: rows {frame.height}, Questionable {int(frame['q_flag'].sum())}, Doubtful {int(frame['d_flag'].sum())}")
    for beside in ((), ("participation",)):
        r = Y.score_input(board, frame, "questionable", beside=beside, copies=19)
        print(f"  beside {r['beside']:<14} rows {r['rows']:>6}: share {pct(r['alone'])} ({pct(r['alone_lo'])} to {pct(r['alone_hi'])}); range {pct(r['range_alone'])}; copies max {pct(r['copies_max'])}; counts {'yes' if r['counts'] else 'no'}")
    # the miss on Questionable rows who played
    f = board.forecast(("participation",)).join(frame, on=keys, how="left")
    snaps = rd("player_game/snaps", ["gsis_id", "game_id", "offense_snaps"], seasons)
    f = f.join(snaps, on=["gsis_id", "game_id"], how="left").with_columns(played=c("offense_snaps").fill_null(0) > 0, r=c("y") - c("mean"))
    for name, m in (("Questionable, played", (c("q_flag") == 1) & c("played")), ("not listed, played", (c("q_flag") == 0) & (c("d_flag") == 0) & c("played")), ("Questionable, all", c("q_flag") == 1)):
        sub = f.filter(m)
        steps = sub["step"].to_numpy()
        rr = sub["r"].to_numpy()
        ub = np.unique(steps)
        idx = {s: np.flatnonzero(steps == s) for s in ub}
        v = [rr[np.concatenate([idx[s] for s in rng.choice(ub, len(ub))])].mean() for _ in range(2000)]
        lo, hi = np.percentile(v, [5, 95])
        print(f"  miss (actual less forecast with participation), {name:<22} rows {sub.height:>6}: {rr.mean():+.2f} yards ({lo:+.2f} to {hi:+.2f})")
