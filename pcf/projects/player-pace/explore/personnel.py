"""Is a player's plus-minus his, or his package's? (H28, H29, H31; Claude's check, 2026-11-11)

The play-level plus-minus of tight ends, backs and receivers repeats strongly. The usual reason
would be personnel: a coach puts his second tight end in for heavy sets and runs from them, his
third-down back in when he means to pass, his nickel back in against three receivers. Then the
plus-minus is the coach's use of the player (his role), not something the player does.

So each play's PROE and pace over expected are taken relative to the same offense's average on
plays with the same personnel grouping that season (`offense_personnel`, from participation), and
the plus-minus is recomputed on that. What's left is the player within his package.
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from common import SEASONS, _part, plays, with_group  # noqa: E402
from h26_h28_h29_h31 import r_ci, season_pairs, split_half  # noqa: E402

c = pl.col


def main() -> None:
    p = plays()
    pers = _part("play", "participation", SEASONS, ["game_id", "play_id", "offense_personnel"])
    p = p.join(pers, on=["game_id", "play_id"], how="left").with_columns(c("offense_personnel").fill_null("unknown"))
    by = ["posteam", "season", "offense_personnel"]
    p = p.with_columns(
        proe_adj=c("pcf_pass_oe") - c("pcf_pass_oe").mean().over(by),
        pace_adj=c("pace_oe") - c("pace_oe").mean().over(by),
    )
    print("plays", p.height, "personnel known", round(float((p["offense_personnel"] != "unknown").mean()), 3))
    print("share of play-level PROE variance the team-season personnel means explain:",
          round(1 - float(p["proe_adj"].var()) / float(p.select(c("pcf_pass_oe") - c("pcf_pass_oe").mean().over(["posteam", "season"])).to_series().var()), 3))
    on = _part("player_play", "on_field", SEASONS, ["game_id", "play_id", "side", "team", "gsis_id", "position"])
    rows = on.join(p.select("game_id", "play_id", "season", "week", "posteam", "proe_adj", "pace_adj"), on=["game_id", "play_id"])
    keys = ["gsis_id", "side", "game_id", "season", "week"]
    per = rows.group_by(*keys).agg(team=c("team").mode().first(), off_team=c("posteam").mode().first(), position=c("position").drop_nulls().mode().first(),
                                   n_on=pl.len(), s_on=c("proe_adj").sum(), np_on=c("pace_adj").count(), sp_on=c("pace_adj").sum())
    team = p.group_by("game_id", off_team=c("posteam")).agg(n_team=pl.len(), s_team=c("proe_adj").sum(), np_team=c("pace_adj").count(), sp_team=c("pace_adj").sum())
    d = per.join(team, on=["game_id", "off_team"]).with_columns(n_off=c("n_team") - c("n_on"), np_off=c("np_team") - c("np_on"))
    d = d.with_columns(
        d_proe=c("s_on") / c("n_on") - (c("s_team") - c("s_on")) / c("n_off"),
        h_proe=pl.when(c("n_off") > 0).then(c("n_on") * c("n_off") / c("n_team")).otherwise(0.0),
        d_pace=c("sp_on") / c("np_on") - (c("sp_team") - c("sp_on")) / c("np_off"),
        h_pace=pl.when((c("np_off") > 0) & (c("np_on") > 0)).then(c("np_on") * c("np_off") / c("np_team")).otherwise(0.0),
    )
    d = with_group(d).filter(c("group").is_in(["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]))
    out = []
    for (side, grp), x in d.group_by("side", "group", maintain_order=True):
        if (side == "offense") != (grp in ("QB", "RB", "WR", "TE", "OL")):
            continue
        for m in ("proe", "pace"):
            wr, wlo, whi, wn = split_half(x, f"d_{m}", f"h_{m}")
            sp = season_pairs(x, f"d_{m}", f"h_{m}")
            sr, slo, shi, sn = r_ci(sp["m"].to_numpy(), sp["m_next"].to_numpy())
            nt = sp.filter(c("team") != c("team_next"))
            tr, tlo, thi, tn = r_ci(nt["m"].to_numpy(), nt["m_next"].to_numpy())
            out.append({"side": side, "group": grp, "measure": m, "week_r": wr, "week_lo": wlo, "week_hi": whi, "season_r": sr, "season_lo": slo, "season_hi": shi, "new_team_r": tr, "nt_lo": tlo, "nt_hi": thi, "nt_pairs": tn})
    print("\n=== plus-minus by play within the personnel grouping: split-half, season to season, movers")
    print(pl.DataFrame(out).sort("side", "measure", "group").with_columns(pl.selectors.float().round(3)))


if __name__ == "__main__":
    pl.Config.set_tbl_rows(40)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(250)
    main()
