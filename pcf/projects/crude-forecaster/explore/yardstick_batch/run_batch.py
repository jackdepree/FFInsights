# ruff: noqa: E501
"""The yardstick batch (crude-forecaster/YARDSTICK_BATCH.md): eight ideas scored against the crude
forecaster, each through `pcf.baselines.crude.yardstick.score_input` with 19 copies shuffled
within each week. Lasso champion, fit from 2016, scored 2019-2024 (the boards' seasons); the 2025
vault is never read.

**The rule** (R7, I69): a gain counts when its 90% interval (resampled weeks) clears zero AND it
beats all 19 shuffled copies; the largest copy's gain is printed beside every row.

**How each bet is read** (written before any result, 2026-11-23; the odds are IDEAS.md's):
- The verdict uses the added-alone number (the yardstick's headline, method A) unless the bet
  names what it's beside. Beside participation (players) or beside Elo (teams: participation has
  no team rows; Elo is the obvious team input, R5) is reported as the obvious-input check.
- "Share" is the share of the crude forecast's squared error removed; "range" the range score's.
- I48 holds if the split doesn't count on a board and its range-score change is under +0.2%, and
  the garbage yard's weight is at least 0.8 of the rest's (an OLS read of y on the split's
  this-season and last-season averages, resampled weeks). Judged per board (passing, rushing,
  receiving, next game).
- I59 survives on a board if the input (pace's PROE and schemes-v2's traits) counts and adds 1%+
  beside participation and team efficiency (the offense's quality), on WR and TE rows; the bet
  (30%) holds if it survives on either board (next game, rest of season).
- I60 holds if the games-played forecast counts and adds 2+ points on at least one rest-of-season
  board (passing, rushing, receiving, team).
- I67: the crude forecast's share of the error removed is `removed()` (around the scored rows'
  average, the exploration's unit), next game; participation's gain on QB rushing against RB
  rushing's, same run, next game (and next 3 reported).
- I70 holds if participation's added-alone passing gain on depth-chart rows is above its R3
  number on the board's own rows (same run) AND rushing and receiving move under 1 point.
- I75: defense (50%) holds if the opposing defense's pre-season continuity counts and adds 2%+ on
  team yards, rest of season; offense (30%) the same with the offense's own.
- I84: receivers (80%) hold if the own-share prior beats the slot prior head to head on movers'
  rows (paired, the interval's middle above zero); running backs (75%) if the slot wins or ties
  (the head-to-head interval reaches zero or the slot is ahead). Size: the better prior's gain on
  movers' rows in 2-5%, and under 0.3% overall.
- I114: judged on the honest number (ESPN's openers, the rows that have one: 2023-2024); teams
  (75%) hold if it counts and adds 2%+ on team yards next game; players (40%) if it does on at
  least one of passing, rushing and receiving. The kickoff line is the ceiling, reported beside.

Run from pcf/ (PCF_DATA_DIR set), one idea at a time, detached:
    python projects/crude-forecaster/explore/yardstick_batch/run_batch.py I48 > projects/crude-forecaster/explore/yardstick_batch/I48.txt
Progress: data/logs/yardstick-batch-progress.txt. Tables: data/outputs/crude-forecaster/yardstick_batch/.
"""

from __future__ import annotations

import sys
import time

import numpy as np
import polars as pl

from pcf.baselines.crude import inputs as I
from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config
from pcf.validation.consistency import consistency

c = pl.col
COPIES = 19
OUT = get_config().zone("outputs") / "crude-forecaster" / "yardstick_batch"
PROGRESS = get_config().zone("logs") / "yardstick-batch-progress.txt"
START = time.time()
ROWS: list[dict] = []
R3 = {"passing": 0.106, "rushing": 0.033, "receiving": 0.037}  # R3, next game, for reference


def log(*parts) -> None:
    with PROGRESS.open("a", encoding="utf-8") as f:
        f.write(f"[{time.time() - START:7.0f}s] batch " + " ".join(str(p) for p in parts) + "\n")


def pct(x: float) -> str:
    return f"{100 * x:+.2f}%"


HEADER = f"  {'input':<26}{'board':<20}{'beside':<26}{'rows':>7}  {'share (90%)':<30}{'range (90%)':<30}{'copies max':<12}{'p':<6}counts"


def show(r: dict) -> None:
    share = f"{pct(r['alone'])} ({pct(r['alone_lo'])} to {pct(r['alone_hi'])})"
    rng = f"{pct(r['range_alone'])} ({pct(r['range_lo'])} to {pct(r['range_hi'])})"
    print(f"  {r['input']:<26}{r['board']:<20}{r['beside']:<26}{r['rows']:>7}  {share:<30}{rng:<30}"
          f"{pct(r['copies_max']):<12}{r['p']:<6.2f}{'yes' if r['counts'] else 'no'}")


def score(idea: str, board: Y.Board, frame, name: str, rows=None, beside=(), existing=(), note="") -> dict:
    r = Y.score_input(board, frame, name, rows=rows, beside=beside, existing=existing, copies=COPIES)
    r |= {"idea": idea, "board": f"{board.base.target_spec.name}_{board.base.horizon}" + (
        "" if board.base.row_rule == "participation" else f"_{board.base.row_rule}rows"), "note": note}
    ROWS.append(r)
    show(r)
    log(idea, name, r["board"], r["beside"], "done")
    return r


def save(idea: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if ROWS:
        pl.DataFrame(ROWS).write_parquet(OUT / f"{idea}.parquet")


def board_rows(board: Y.Board) -> pl.DataFrame:
    return board.features.select(*{*board.keys, "team", "season", "week", "as_of", "step", "position", "n_games", "ypa_ls", "y_s"} & set(board.features.columns))


def player_beside(board: Y.Board) -> tuple[tuple, str]:
    return (("participation",), "participation") if board.base.players() else (("elo",), "elo")


# ---------------------------------------------------------------- I48
def i48() -> None:
    print("I48: garbage-time yards split from the rest, next game. Inputs gt_y_s, gt_y_ls (garbage yards per game this season so far, last season) beside the board's pooled averages.")
    print(HEADER)
    for target in ("passing", "rushing", "receiving"):
        board = Y.load_board(target, "next")
        rows = board_rows(board)
        g = I.player_game_garbage(target, sorted({*rows["season"].unique().to_list(), 2015}))
        frame = I.garbage_split(rows, target, garbage=g)
        score("I48", board, frame, "garbage split")
        score("I48", board, frame, "garbage split", beside=("participation",))
        # the weight per garbage yard against the rest's: OLS of y on the split averages
        both = I.prior_average(rows, g, "gsis_id", ["gt", "rest"])
        d = both.join(board.outcomes, on=board.keys).drop_nulls(["y"])
        x = np.column_stack([np.ones(d.height), d["rest_s"], d["gt_s"], d["rest_ls"], d["gt_ls"]])
        y = d["y"].to_numpy()
        steps = d["step"].to_numpy()
        coef = np.linalg.lstsq(x, y, rcond=None)[0]
        blocks = [np.flatnonzero(steps == s) for s in np.unique(steps)]
        rng = np.random.default_rng(get_config().seed)
        boot = []
        for _ in range(300):
            idx = np.concatenate([blocks[j] for j in rng.integers(0, len(blocks), len(blocks))])
            boot.append(np.linalg.lstsq(x[idx], y[idx], rcond=None)[0])
        boot = np.array(boot)
        def ratio(b):
            return (b[..., 2] + b[..., 4]) / (b[..., 1] + b[..., 3])
        lo, hi = np.quantile(ratio(boot), [0.05, 0.95])
        share = float(d["gt_s"].sum() / (d["gt_s"].sum() + d["rest_s"].sum()))
        print(f"  {target}: garbage time is {100 * share:.1f}% of past yards. OLS weights per yard: rest this season {coef[1]:.3f}, garbage {coef[2]:.3f}; rest last season {coef[3]:.3f}, garbage {coef[4]:.3f}. Garbage over rest (both seasons): {ratio(coef):.2f} (90% {lo:.2f} to {hi:.2f})")
        ROWS[-1] |= {"weight_ratio": float(ratio(coef)), "ratio_lo": float(lo), "ratio_hi": float(hi), "garbage_share": share}
        ROWS[-2] |= {"weight_ratio": float(ratio(coef)), "ratio_lo": float(lo), "ratio_hi": float(hi), "garbage_share": share}
    save("I48")


# ---------------------------------------------------------------- I59
def i59() -> None:
    print("I59: a pass-heavy team's WRs and TEs. Input: pace's pass rate over expected (pace_proe) and schemes-v2's 4 traits (sch_*), WR and TE rows only.")
    print(HEADER)
    cols = ["pace_proe", "sch_pass_oe", "sch_shotgun", "sch_depth", "sch_tempo"]
    for horizon in ("next", "rest"):
        board = Y.load_board("receiving", horizon)
        rows = board.features.filter(c("position").is_in(["WR", "TE"])).select(*board.keys)
        score("I59", board, None, "proe + schemes", rows=rows, existing=cols)
        score("I59", board, None, "proe + schemes", rows=rows, existing=cols, beside=("participation",))
        score("I59", board, None, "proe + schemes", rows=rows, existing=cols, beside=("participation", "efficiency"))
        score("I59", board, None, "proe alone", rows=rows, existing=["pace_proe"], beside=("participation", "efficiency"))
    save("I59")


# ---------------------------------------------------------------- I60
def i60() -> None:
    print("I60: availability over the rest of the season. Forecast: av_rate (games played so far shrunk toward last season's rate), av_y = y_s x av_rate, this week's report (av_q, av_dnp), weeks listed out or doubtful (av_out_s). Hindsight (ceiling): the share of the window's games he did play.")
    print(HEADER)
    for target in ("passing", "rushing", "receiving"):
        board = Y.load_board(target, "rest")
        rows = board_rows(board)
        fc = I.availability(rows)
        hs = I.availability(rows, hindsight=True)
        score("I60", board, fc, "games-played forecast")
        score("I60", board, fc, "games-played forecast", beside=("participation",))
        score("I60", board, hs, "hindsight (ceiling)")
        score("I60", board, hs, "hindsight (ceiling)", beside=("participation",))
    board = Y.load_board("team", "rest")
    rows = board_rows(board)
    fc = I.team_availability(rows)
    hs = I.team_availability(rows, hindsight=True)
    score("I60", board, fc, "starters' games forecast")
    score("I60", board, fc, "starters' games forecast", beside=("elo",))
    score("I60", board, hs, "hindsight (ceiling)")
    save("I60")


# ---------------------------------------------------------------- I67
def i67() -> None:
    print("I67: QB rushing yards as a yardstick target (QBs expected to play). removed = share of squared error around the scored rows' average.")
    for horizon in ("next", "next3"):
        qb = Y.load_board("qb_rushing", horizon)
        rb = Y.load_board("rushing", horizon)
        for name, b in (("QB rushing", qb), ("RB rushing", rb)):
            lasso = b.forecast()
            print(f"\n== {name}, {horizon}: rows {lasso.height}; crude forecast removes {100 * Y.removed(lasso):.1f}% of the error around the average")
            sv = Y.variant(b.base.target_spec.name, horizon, "season")
            sea = Y.Board(sv, b.features, b.outcomes, b.steps, b.test).forecast()
            g = Y.gain(lasso, sea, b.keys)
            print(f"  against the season-so-far average: {pct(g.share)} ({pct(g.lo)} to {pct(g.hi)}); the average removes {100 * Y.removed(sea):.1f}%")
            ROWS.append({"idea": "I67", "board": f"{b.base.target_spec.name}_{horizon}", "input": "crude forecast", "beside": "season average", "alone": g.share, "alone_lo": g.lo, "alone_hi": g.hi, "range_alone": g.range_share, "range_lo": g.range_lo, "range_hi": g.range_hi, "rows": g.rows, "removed": Y.removed(lasso), "removed_season": Y.removed(sea)})
            print(HEADER)
            members = {k: v for k, v in b.members().items() if k != Y.SHUFFLED}
            for m, (groups, _) in members.items():
                score("I67", b, None, m, existing=b.base.expert_groups()[m])
            if horizon == "next":
                t = Y.shapley(b, members)
                print("  fair shares: " + ", ".join(f"{r['member']} {pct(r['share'])}" for r in t.iter_rows(named=True)) + f"; all together {pct(t['all_members'][0])}")
    save("I67")


# ---------------------------------------------------------------- I70
def i70() -> None:
    print("I70: participation's added-alone gain on rows it didn't choose (depth chart: a starter or first backup), against the same on its own rows (R3's rule), next game.")
    print(HEADER)
    for target in ("passing", "rushing", "receiving", "qb_rushing"):
        for rule in ("participation", "depth"):
            b = Y.load_board(target, "next", rows=rule)
            score("I70", b, None, "participation", existing=b.base.expert_groups()["participation"])
    save("I70")


# ---------------------------------------------------------------- I75
def i75() -> None:
    print("I75: roster continuity. pre = share of week-1 depth-chart starters with no NFL snap last season (known at week 1); hindsight = share of the season's snaps to such players (a ceiling). Offense: the team's own; defense: the opponent's (this row's yards allowed).")
    cont = I.continuity()
    print(HEADER)
    for horizon in ("rest", "next"):
        b = Y.load_board("team", horizon)
        rows = board_rows(b)
        f = I.team_continuity(rows, cont)
        for side in ("off", "def"):
            for kind in ("pre", "hindsight"):
                col = f"{side}_new_{kind}"
                fr = f.select(*b.keys, col)
                score("I75", b, fr, f"{side} continuity {kind}")
                score("I75", b, fr, f"{side} continuity {kind}", beside=("elo",))
    # the second test: does it repeat season to season (a pre-season measure: week to week it's constant)
    weekly = cont.with_columns(week=pl.lit(1)).vstack(cont.with_columns(week=pl.lit(2)))
    t = consistency(weekly, ["off_new_pre", "def_new_pre", "off_new_hindsight", "def_new_hindsight"], unit="team")
    print("\n  consistency (season to season; week to week is 1 by construction):")
    for r in t.iter_rows(named=True):
        print(f"  {r['measure']:<20} season r {r['season_r']:+.2f} ({r['season_lo']:+.2f} to {r['season_hi']:+.2f}), {r['season_pairs']} pairs, mean {r['mean_abs']:.3f}")
    OUT.mkdir(parents=True, exist_ok=True)
    t.write_parquet(OUT / "I75_consistency.parquet")
    save("I75")


# ---------------------------------------------------------------- I84
def i84() -> None:
    print("I84: movers' first 4 games with a new team. own = his old-team share x new team's volume; slot = the new team's share at his depth-chart slot last season x the same volume; both x his own yards per target or carry. mv_flag marks the rows.")
    print(HEADER)
    for target, positions in (("receiving", ["WR", "TE"]), ("rushing", ["RB"])):
        b = Y.load_board(target, "next")
        rows = board_rows(b)
        mv = I.mover_priors(rows, target)
        movers = mv.filter(c("mv_flag") > 0).select(*b.keys)
        test_movers = movers.join(b.features.filter(c("step_season") >= 2019).select(*b.keys), on=b.keys, how="semi")
        print(f"  {target}: {test_movers.height} mover rows scored (2019-2024)")
        own = mv.select(*b.keys, "mv_flag", "mv_own_y")
        slot = mv.select(*b.keys, "mv_flag", "mv_slot_y")
        for beside in ((), ("participation",)):
            score("I84", b, own, "own share", rows=movers, beside=beside)
            score("I84", b, slot, "slot share", rows=movers, beside=beside)
            score("I84", b, own, "own share (all rows)", beside=beside)
            score("I84", b, slot, "slot share (all rows)", beside=beside)
            # head to head on movers' rows
            feats = b.features.join(mv, on=b.keys, how="left").with_columns(c("mv_flag", "mv_own_y", "mv_slot_y").fill_null(0.0))
            p_own = b.forecast(tuple(beside), extra=["mv_flag", "mv_own_y"], feats=feats)
            p_slot = b.forecast(tuple(beside), extra=["mv_flag", "mv_slot_y"], feats=feats)
            h = Y.gain(p_own, p_slot, b.keys, movers)
            print(f"  head to head, own over slot, movers' rows, beside {'+'.join(beside) or 'crude'}: {pct(h.share)} ({pct(h.lo)} to {pct(h.hi)}); range {pct(h.range_share)} ({pct(h.range_lo)} to {pct(h.range_hi)})")
            ROWS.append({"idea": "I84", "board": f"{target}_next", "input": "own over slot", "beside": "+".join(beside) or "crude", "alone": h.share, "alone_lo": h.lo, "alone_hi": h.hi, "range_alone": h.range_share, "range_lo": h.range_lo, "range_hi": h.range_hi, "rows": h.rows})
    save("I84")


# ---------------------------------------------------------------- I114
def i114() -> None:
    print("I114: the betting lines (the team's expected margin, the total, its implied points). kickoff = the schedule's near-closing line, a CEILING (known at kickoff, not at the Saturday run). open = ESPN's openers (known at the run), scored only on games that have one (2023: 194 games, 2024: all; 2022 has none in ESPN's history).")
    openers = I.espn_openers()
    print(f"  openers: {openers.height} games")
    print(HEADER)
    for target in ("team", "passing", "rushing", "receiving"):
        b = Y.load_board(target, "next")
        rows = board_rows(b)
        beside = ("elo",) if target == "team" else ("participation",)
        kick = I.lines(rows, "kickoff")
        opn = I.lines(rows, "open", openers=openers)
        orows = I.opener_rows(b.features.filter(c("step_season") >= 2023), openers)
        for bs in ((), beside):
            score("I114", b, kick, "kickoff line (ceiling)", beside=bs)
            score("I114", b, kick, "kickoff line (ceiling)", rows=orows, beside=bs, note="opener rows")
            score("I114", b, opn, "opening line (honest)", rows=orows, beside=bs, note="opener rows")
    save("I114")


IDEAS = {"I48": i48, "I59": i59, "I60": i60, "I67": i67, "I70": i70, "I75": i75, "I84": i84, "I114": i114}

if __name__ == "__main__":
    for idea in sys.argv[1:]:
        log(idea, "start")
        IDEAS[idea]()
        log(idea, "end")
        ROWS.clear()
