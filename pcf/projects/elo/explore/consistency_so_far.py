"""The second test for every measure the Elo exploration built: is it consistent? (CLAUDE.md, "Two
tests for every new measure"; `pcf.validation.consistency`.)

Per team per regular-season game, 1999-2024 (snap and injury measures from 2013):
- scoring: margin, points scored, points allowed
- H4's plays, split by side: return TDs scored and allowed; fumble-recovery luck; field-goal and
  extra-point luck (own kicker) and the opponent's; interceptions caught (defense) and thrown
  (offense); long TDs scored and allowed
- H3: average win probability; "finishing", the result (1, 0.5, 0) minus average win probability,
  which is large for the CEO's late underdog win
- H7: EPA per pass and per run, on offense and allowed on defense
- H1: same-team share and the usual QB missing

The vault (2025) isn't read. Run from pcf/:
.venv/Scripts/python.exe projects/elo/explore/consistency_so_far.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import h2_h1_same_team as H1  # noqa: E402
import h3_winprob as H3  # noqa: E402
import h4_luck as H4  # noqa: E402
import h7_parts as H7  # noqa: E402
import ladder as L  # noqa: E402

from pcf.validation.consistency import consistency  # noqa: E402

c = pl.col


def team_games() -> pl.DataFrame:
    g = L.games().filter(c("game_type") == "REG")
    g = H4.by_game(g, H4.credits(H4.plays()))
    g = g.join(H3.avg_wp(), on="game_id", how="left")
    te = H7.team_epa()
    for side in ("home", "away"):
        g = g.join(
            te.rename({"posteam": f"{side}_team"} | {x: f"{side[0]}_epa_{x}" for x in H7.PARTS}),
            on=["game_id", f"{side}_team"],
            how="left",
        )
    st = H1.same_team(H1.player_games())
    for side in ("home", "away"):
        g = g.join(
            st.rename(
                {"team": f"{side}_team", "share": f"{side[0]}_same", "qb_out": f"{side[0]}_qbout"}
            ),
            on=["game_id", f"{side}_team"],
            how="left",
        )

    def side(me: str, op: str, sign: int) -> pl.DataFrame:
        res = pl.when(c("margin") * sign > 0).then(1.0).when(c("margin") * sign < 0).then(0.0)
        wp = c("wp") if sign == 1 else 1 - c("wp")
        return g.select(
            "season",
            "week",
            team=c(f"{'home' if me == 'h' else 'away'}_team"),
            margin=c("margin") * sign,
            points_scored=c(f"{'home' if me == 'h' else 'away'}_pts"),
            points_allowed=c(f"{'home' if op == 'h' else 'away'}_pts"),
            return_td_scored=c(f"{me}_return_td"),
            return_td_allowed=c(f"{op}_return_td"),
            fumble_luck=c(f"{me}_fumble") - c(f"{op}_fumble"),
            kick_luck_own=c(f"{me}_kick"),
            kick_luck_opponent=c(f"{op}_kick"),
            interceptions_caught=c(f"{me}_interception"),
            interceptions_thrown=c(f"{op}_interception"),
            long_td_scored=c(f"{me}_long_td"),
            long_td_allowed=c(f"{op}_long_td"),
            avg_win_prob=wp,
            finishing=res.otherwise(0.5) - wp,
            pass_epa_offense=c(f"{me}_epa_pass"),
            pass_epa_allowed=c(f"{op}_epa_pass"),
            rush_epa_offense=c(f"{me}_epa_rush"),
            rush_epa_allowed=c(f"{op}_epa_rush"),
            same_team_share=c(f"{me}_same"),
            usual_qb_missing=c(f"{me}_qbout"),
        )

    return pl.concat([side("h", "a", 1), side("a", "h", -1)])


def main() -> None:
    tg = team_games()
    measures = [m for m in tg.columns if m not in ("season", "week", "team")]
    out = consistency(tg, measures)
    with pl.Config(tbl_rows=40, tbl_cols=10, float_precision=3, tbl_width_chars=160):
        print(out.drop("week_hi", "season_hi").sort("week_r", descending=True))


if __name__ == "__main__":
    main()
