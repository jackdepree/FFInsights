# ruff: noqa: E501
"""The CEO's spot-check (a), 2026-11-23: I114's honest number (ESPN's opening line, known at the
Saturday run) against the ceiling (the schedule's near-closing line, known at kickoff), on team
yards next game, 2023-2024 (the seasons with openers). The batch read +5.19% (+2.28 to +8.18)
for the opener and +8.37% for the ceiling on the same 900 team-games.

**Written before any spot-check number was looked at (2026-11-23).**

What is checked:
1. **Is the opener really an opener?** How often ESPN's opening spread and total both equal
   ESPN's own close, and the schedule's line; how far the line moved from open to kickoff.
2. **By season:** opener and ceiling on 2023 and on 2024 apart.
3. **By line movement:** games split by how far the line moved from open to kickoff
   (|spread move| + |total move| / 2, in points: under 1, 1 to 2.5, over 2.5). Football sense:
   where the line didn't move the two inputs are nearly the same, so the gap should sit in the
   games that moved (injury news, weather, sharp money).
4. **How many games it rests on:** the weeks, the best single week's share of the gain, and the
   gain with the best 1 and 3 weeks left out.
5. **Just Elo or form under another name?** The opener beside every team input on the board
   (Elo, efficiency, pace, schemes), with 19 shuffled copies; the batch had beside Elo only.
6. **Is the line's weight biased?** The lasso learns the line's weight mostly from kickoff lines
   and applies it to openers. The slope of the outcome's surprise (y minus the crude forecast) on
   what the line moved the forecast (the line forecast minus the crude), on opener rows, with a
   90% interval from resampled weeks; 1 means the weight was right, under 1 that it leaned on
   the opener too much. The gain with the slope applied is in-sample (an upper bound).
7. **Is 2023-2024 a typical pair of seasons for the line?** The ceiling by season, 2019-2024,
   and the honest number scaled by (the ceiling on all seasons / the ceiling on 2023-2024).

What changes the teams verdict (held: the opener counts and adds 2%+ alone):
- **failed** if the opener isn't an opener: its spread and total both equal ESPN's close in more
  than half the games (then it is a closing line under another name, known only at kickoff).
- **unclear** if either season alone has a gain at or below zero, or if the gain with the best
  single week left out falls under +2% or its interval reaches zero.
- Not verdict-changing, reported for F58's size and the use note: the gain beside every team
  input (if its interval reaches zero, "the market adds little beyond our team inputs at the
  Saturday run"); the weight's slope; the typical-season scaling; where the gap sits.

Expected (Claude, before looking): the opener is a real opener (equal to the close in under 30%
of games); both seasons positive (70%); the gap sits mostly in games that moved over 2.5 points
(65%); beside every team input the opener adds 1-3% with an interval reaching zero (55%); the
slope under 1 (55%): openers carry less than closers, so a weight learned on closers leans too
hard on them; 2023-2024 within a point of the other seasons' ceiling (60%).

Run from pcf/ (PCF_DATA_DIR set): python projects/crude-forecaster/explore/yardstick_batch/spotcheck_i114.py > projects/crude-forecaster/explore/yardstick_batch/spotcheck_i114.txt
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.baselines.crude import inputs as I
from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway

c = pl.col
COPIES = 19


def pct(x: float) -> str:
    return f"{100 * x:+.2f}%"


def g_str(g: Y.Gain) -> str:
    return (f"{pct(g.share)} ({pct(g.lo)} to {pct(g.hi)}); range {pct(g.range_share)} "
            f"({pct(g.range_lo)} to {pct(g.range_hi)}); {g.rows} team-games, {g.weeks} weeks")


def with_cols(b: Y.Board, frame: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    cols = [x for x in frame.columns if x not in b.keys]
    feats = b.features.join(frame, on=b.keys, how="left").with_columns(
        c(x).fill_null(c(x).median()) for x in cols)
    return feats, cols


def main() -> None:
    b = Y.load_board("team", "next")
    keys = b.keys
    rows = b.features.select("game_id", "team", "season", "week")
    openers = I.espn_openers()
    kick = I.lines(rows, "kickoff")
    opn = I.lines(rows, "open", openers=openers)
    orows = I.opener_rows(b.features.filter(c("step_season") >= 2023), openers)
    print(f"I114 spot-check (a): team yards next game. Opener rows: {orows.height} team-games, "
          f"{orows['game_id'].n_unique()} games.\n")

    # 1. is the opener an opener?
    raw = pl.read_parquet(get_config().zone("interim") / "espn_odds" / "game_lines.parquet").filter(
        (c("seasontype") == 2) & ~c("provider_name").str.contains("(?i)live"))
    close = raw.group_by("game_id").agg(close_home_spread=c("close_home_spread").median(),
                                        close_total=c("close_total").median())
    sched = (Gateway().view(END_OF_TIME, "retrospective", {"team_game": ("schedule", "pregame")})
             .table("team_game", seasons=[2023, 2024])
             .filter(c("home")).select("game_id", k_home_spread="spread", k_total="total_line"))
    m = (openers.join(close, on="game_id").join(sched, on="game_id")
         .join(orows.select("game_id").unique(), on="game_id", how="semi")
         .with_columns(season=c("game_id").str.slice(0, 4).cast(pl.Int32)))
    eq_close = ((c("open_home_spread") == c("close_home_spread")) & (c("open_total") == c("close_total")))
    eq_kick = ((c("open_home_spread") == c("k_home_spread")) & (c("open_total") == c("k_total")))
    m = m.with_columns(
        move=(c("open_home_spread") - c("k_home_spread")).abs() + (c("open_total") - c("k_total")).abs() / 2,
        spread_move=(c("open_home_spread") - c("k_home_spread")).abs(),
        total_move=(c("open_total") - c("k_total")).abs())
    print("1. Is the opener an opener?")
    for s, d in [("both", m), *[(str(y), m.filter(c("season") == y)) for y in (2023, 2024)]]:
        print(f"  {s}: {d.height} games; opener = ESPN's close on spread and total in "
              f"{d.select(eq_close.mean()).item():.0%}; = the schedule's line in "
              f"{d.select(eq_kick.mean()).item():.0%}; spread moved (median) "
              f"{d['spread_move'].median():.1f} pts, mean {d['spread_move'].mean():.2f}; total moved "
              f"median {d['total_move'].median():.1f}, mean {d['total_move'].mean():.2f}; "
              f"r(open, kickoff spread) {np.corrcoef(d['open_home_spread'], d['k_home_spread'])[0, 1]:.3f}")
    print()

    # forecasts: crude, kickoff, opener, and the opener's 19 shuffled copies
    f_kick, cols = with_cols(b, kick)
    f_open, _ = with_cols(b, opn)
    crude = b.forecast(())
    p_kick = b.forecast((), extra=cols, feats=f_kick)
    p_open = b.forecast((), extra=cols, feats=f_open)
    seed0 = get_config().seed + 1000
    p_null = [b.forecast((), extra=cols, feats=Y.shuffle_within_weeks(f_open, cols, seed=seed0 + k))
              for k in range(1, COPIES + 1)]

    def both(sub: pl.DataFrame, label: str) -> None:
        go = Y.gain(p_open, crude, keys, sub)
        gk = Y.gain(p_kick, crude, keys, sub)
        nmax = max(Y.gain(p, crude, keys, sub).share for p in p_null)
        print(f"  {label}\n    opener  {g_str(go)}; copies max {pct(nmax)}\n    ceiling {g_str(gk)}"
              f"\n    the opener's share of the ceiling: {go.share / gk.share:.0%}" if gk.share > 0 else "")

    print("2. By season (opener rows)")
    both(orows, "2023-2024")
    for y in (2023, 2024):
        both(orows.filter(c("game_id").str.starts_with(str(y))), str(y))
    print()

    print("3. By how far the line moved, open to kickoff (|spread move| + |total move| / 2)")
    mv = m.select("game_id", "move")
    for lo, hi, lab in ((-1, 0.999, "under 1 point"), (1, 2.5, "1 to 2.5 points"), (2.501, 99, "over 2.5 points")):
        ids = mv.filter((c("move") >= lo) & (c("move") <= hi)).select("game_id")
        sub = orows.join(ids, on="game_id", how="semi")
        print(f"  {lab}: {ids.height} games")
        both(sub, lab)
    print()

    print("4. How many games it rests on")
    w = Y._weekly(p_open, crude, keys, orows)
    gain_w = (w["se_b"] - w["se_a"]).to_numpy()
    den = w["se_b"].to_numpy()
    order = np.argsort(-gain_w)
    print(f"  {w.height} weeks; the best week carries {gain_w[order[0]] / gain_w.sum():.0%} of the gain; "
          f"weeks with a positive gain {np.mean(gain_w > 0):.0%}")
    for k in (1, 3):
        keep = np.ones(len(gain_w), bool)
        keep[order[:k]] = False
        draws = Y._draws(int(keep.sum()), get_config().seed)
        s, lo_, hi_ = Y._interval(gain_w[keep], den[keep], draws)
        print(f"  without the best {k} week(s): {pct(s)} ({pct(lo_)} to {pct(hi_)})")
    print()

    print("5. Beside every team input (Elo, efficiency, pace, schemes), 19 copies")
    groups = tuple(b.base.expert_groups())
    for frame, name, sub in ((opn, "opening line (honest)", orows), (kick, "kickoff line (ceiling)", orows)):
        r = Y.score_input(b, frame, name, rows=sub, beside=groups, copies=COPIES)
        print(f"  {name}: {pct(r['alone'])} ({pct(r['alone_lo'])} to {pct(r['alone_hi'])}); range "
              f"{pct(r['range_alone'])} ({pct(r['range_lo'])} to {pct(r['range_hi'])}); copies max "
              f"{pct(r['copies_max'])}; counts {'yes' if r['counts'] else 'no'}")
    all_crude = b.forecast(groups)
    print(f"  (every team input together vs the plain crude forecast, opener rows: {g_str(Y.gain(all_crude, crude, keys, orows))})")
    print()

    print("6. Is the line's weight biased? (slope of the surprise on the line's push, opener rows)")
    for p, lab in ((p_open, "opener"), (p_kick, "kickoff line")):
        d = (p.select(*keys, "step", m_new="mean").join(crude.select(*keys, m0="mean", y="y"), on=keys)
             .join(orows, on=keys, how="semi").with_columns(push=c("m_new") - c("m0"), surprise=c("y") - c("m0")))
        wk = d.group_by("step").agg(sxy=(c("push") * c("surprise")).sum(), sxx=(c("push") ** 2).sum()).sort("step")
        draws = Y._draws(wk.height, get_config().seed)
        slope, lo_, hi_ = Y._interval(wk["sxy"].to_numpy(), wk["sxx"].to_numpy(), draws)
        se0 = ((d["surprise"]) ** 2).sum()
        se1 = ((d["y"] - (d["m0"] + slope * d["push"])) ** 2).sum()
        print(f"  {lab}: slope {slope:.2f} ({lo_:.2f} to {hi_:.2f}); push sd {d['push'].std():.1f} yards; "
              f"gain with the slope applied (in-sample, an upper bound) {pct(1 - se1 / se0)}")
    print()

    print("7. The ceiling by season, 2019-2024 (all rows)")
    allrows = b.features.select(*keys, "step_season")
    for y in range(2019, 2025):
        print(f"  {y}: {g_str(Y.gain(p_kick, crude, keys, allrows.filter(c('step_season') == y).select(keys)))}")
    g_all = Y.gain(p_kick, crude, keys).share
    g_23 = Y.gain(p_kick, crude, keys, orows).share
    g_open = Y.gain(p_open, crude, keys, orows).share
    print(f"  ceiling all seasons {pct(g_all)}; on the opener rows {pct(g_23)}; the honest number scaled to a typical season: {pct(g_open * g_all / g_23)}")


if __name__ == "__main__":
    main()
