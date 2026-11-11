"""H26, H28, H29 and H31 (the CEO, 2026-11-11): which player measures repeat, by condition, and
does a player carry a plus or minus relative to his team?

Units: players, by side and position group, regular seasons 2016-2024.
- **On-field rate:** the team's pass rate over expected (PCF's) and pace over expected on the
  plays he was on the field for. For a defender, the offense's rates on those plays.
- **Plus-minus, by play (retrospective):** on-field minus off-field in the same team-game, each
  game weighted by n_on*n_off/(n_on+n_off), the weight a difference of two means earns. Only
  the plays he sat out measure it.
- **Plus-minus, by game (in season):** the team's rate in games he played most snaps (share
  >= 0.5) minus games he didn't play or barely did (share < 0.1, or absent from the snap table),
  same team-season. What weekly snap counts can tell, before the play-by-play lineups.
Consistency, as `pcf.validation.consistency`: split-half (odd against even weeks) within a
season, and one season against the next, with Fisher 90% intervals; here with the plays-weighted
means each needs. Conditions (H26): position group, snap share, same or new team, same or new
head coach.
"""

# ruff: noqa: E501
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from common import SEASONS, TABLES, player_game, with_group  # noqa: E402

from pcf.validation.consistency import _interval  # noqa: E402

c = pl.col
MIN_W = 5.0  # the least weight a half (or season) needs to be counted


def wmean(v: str, w: str) -> pl.Expr:
    return (c(v) * c(w)).sum() / c(w).sum()


def r_ci(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float, int]:
    ok = ~(np.isnan(x) | np.isnan(y))
    n = int(ok.sum())
    if n < 8:
        return (math.nan, math.nan, math.nan, n)
    r = float(np.corrcoef(x[ok], y[ok])[0, 1])
    lo, hi = _interval(r, n)
    return r, lo, hi, n


def split_half(df: pl.DataFrame, v: str, w: str, unit=("gsis_id", "side")) -> tuple:
    d = df.filter(c(v).is_not_null() & (c(w) > 0))
    h = d.group_by(*unit, "season", odd=c("week") % 2 == 1).agg(m=wmean(v, w), w=c(w).sum()).filter(c("w") >= MIN_W)
    j = h.filter(c("odd")).join(h.filter(~c("odd")), on=[*unit, "season"], suffix="_e")
    return r_ci(j["m"].to_numpy(), j["m_e"].to_numpy())


def season_pairs(df: pl.DataFrame, v: str, w: str, unit=("gsis_id", "side"), extra=()) -> pl.DataFrame:
    d = df.filter(c(v).is_not_null() & (c(w) > 0))
    s = d.group_by(*unit, "season").agg(m=wmean(v, w), w=c(w).sum(), team=c("team").mode().first(), *[c(e).mode().first() for e in extra]).filter(c("w") >= MIN_W)
    nxt = s.with_columns(c("season") - 1)
    return s.join(nxt, on=[*unit, "season"], suffix="_next")


def coaches() -> pl.DataFrame:
    files = [TABLES / "team_game" / "pregame" / f"season={s}" / "data.parquet" for s in SEASONS]
    p = pl.read_parquet(files, columns=["game_id", "team", "season", "coach", "qb_id"])
    from pcf.data.clean import standard

    p = standard.standard_teams(p, "team")
    return p.group_by("team", "season").agg(coach=c("coach").mode().first())


def prep() -> pl.DataFrame:
    pg = with_group(player_game())
    pg = pg.with_columns(
        d_proe=c("proe_on") - c("proe_off"),
        d_pace=c("pace_on") - c("pace_off"),
        h_proe=pl.when(c("n_off") > 0).then(c("n_on") * c("n_off") / c("n_team")).otherwise(0.0),
        h_pace=pl.when((c("n_pace_off") > 0) & (c("n_pace_on") > 0)).then(c("n_pace_on") * c("n_pace_off") / c("n_pace_team")).otherwise(0.0),
    )
    # every row's team is the team he played for: the offense for offense, the defense for defense
    return pg


def game_level(pg: pl.DataFrame) -> pl.DataFrame:
    """With and without by game, from snap shares: per player, team-season, side, the team's
    mean rate (game-weighted) in games he played most of minus games he didn't."""
    team_games = pg.group_by("game_id", "season", "week", "side", "team").agg(
        proe_team=c("proe_team").first(), pace_team=c("pace_team").first()
    )
    players = pg.group_by("gsis_id", "side", "team", "season").agg(c("group").mode().first())
    grid = players.join(team_games, on=["side", "team", "season"])
    share = pg.select("gsis_id", "side", "game_id", "share")
    g = grid.join(share, on=["gsis_id", "side", "game_id"], how="left").with_columns(c("share").fill_null(0.0))
    g = g.with_columns(state=pl.when(c("share") >= 0.5).then(pl.lit("with")).when(c("share") < 0.1).then(pl.lit("without")))
    return g.drop_nulls("state")


def with_without(g: pl.DataFrame, by_half: bool) -> pl.DataFrame:
    keys = ["gsis_id", "side", "team", "season", "group"] + (["odd"] if by_half else [])
    if by_half:
        g = g.with_columns(odd=c("week") % 2 == 1)
    a = g.group_by(*keys, "state").agg(proe=c("proe_team").mean(), pace=c("pace_team").mean(), n=pl.len())
    w = a.filter(c("state") == "with").join(a.filter(c("state") == "without"), on=keys, suffix="_wo")
    return w.with_columns(
        d_proe=c("proe") - c("proe_wo"),
        d_pace=c("pace") - c("pace_wo"),
        k=c("n") * c("n_wo") / (c("n") + c("n_wo")),
    )


def main() -> None:
    pg = prep()
    pg = pg.filter(c("group") != "other")
    hc = coaches()
    pg = pg.join(hc, on=["team", "season"], how="left")
    pd = {"proe": "PROE", "pace": "pace over expected"}

    print("\n=== Spread: how far players' plus-minus (by play) sits from 0, per player-season (shrunk only by sample)")
    print("=== H26: on-field rates, split-half (week) and season to season, by side and group")
    rows = []
    for (side, grp), d in pg.group_by("side", "group", maintain_order=True):
        for m in ("proe", "pace"):
            n = "n_on" if m == "proe" else "n_pace_on"
            wr, wlo, whi, wn = split_half(d, f"{m}_on", n)
            sp = season_pairs(d, f"{m}_on", n, extra=("coach",))
            sr, slo, shi, sn = r_ci(sp["m"].to_numpy(), sp["m_next"].to_numpy())
            same_t = sp.filter(c("team") == c("team_next"))
            new_t = sp.filter(c("team") != c("team_next"))
            new_c = same_t.filter(c("coach") != c("coach_next"))
            same_c = same_t.filter(c("coach") == c("coach_next"))
            r_st = r_ci(same_c["m"].to_numpy(), same_c["m_next"].to_numpy())
            r_nc = r_ci(new_c["m"].to_numpy(), new_c["m_next"].to_numpy())
            r_nt = r_ci(new_t["m"].to_numpy(), new_t["m_next"].to_numpy())
            rows.append({"side": side, "group": grp, "measure": m, "week_r": wr, "week_lo": wlo, "units": wn, "season_r": sr, "season_lo": slo, "pairs": sn,
                         "same_team_coach": r_st[0], "n1": r_st[3], "new_coach": r_nc[0], "n2": r_nc[3], "new_team": r_nt[0], "nt_lo": r_nt[1], "n3": r_nt[3]})
    print(pl.DataFrame(rows).sort("side", "measure", "group").with_columns(pl.selectors.float().round(2)))

    print("\n=== H26 by snap share: on-field PROE and pace, split-half by group and share of the team's plays (season share)")
    seas = pg.group_by("gsis_id", "side", "season").agg(season_share=c("n_on").sum() / c("n_team").sum())
    pgs = pg.join(seas, on=["gsis_id", "side", "season"]).with_columns(
        band=pl.when(c("season_share") < 0.3).then(pl.lit("a <30%")).when(c("season_share") < 0.7).then(pl.lit("b 30-70%")).otherwise(pl.lit("c 70%+"))
    )
    rows = []
    for (side, grp, band), d in pgs.group_by("side", "group", "band", maintain_order=True):
        for m in ("proe", "pace"):
            n = "n_on" if m == "proe" else "n_pace_on"
            wr, wlo, whi, wn = split_half(d, f"{m}_on", n)
            pr, plo, phi, pn = split_half(d, f"d_{m}", f"h_{m}")
            rows.append({"side": side, "group": grp, "band": band, "measure": m, "on_week_r": wr, "on_lo": wlo, "pm_week_r": pr, "pm_lo": plo, "pm_hi": phi, "units": pn})
    print(pl.DataFrame(rows).sort("side", "measure", "group", "band").with_columns(pl.selectors.float().round(2)))

    print("\n=== H28/H29/H31: plus-minus by play (on minus off, same team-game), split-half and season to season")
    rows = []
    for (side, grp), d in pg.group_by("side", "group", maintain_order=True):
        for m in ("proe", "pace"):
            wr, wlo, whi, wn = split_half(d, f"d_{m}", f"h_{m}")
            sp = season_pairs(d, f"d_{m}", f"h_{m}", extra=("coach",))
            sr, slo, shi, sn = r_ci(sp["m"].to_numpy(), sp["m_next"].to_numpy())
            nt = sp.filter(c("team") != c("team_next"))
            tr, tlo, thi, tn = r_ci(nt["m"].to_numpy(), nt["m_next"].to_numpy())
            # the size: player-season plus-minus, weighted sd and the share of it that's not sampling noise
            ps = d.filter(c(f"h_{m}") > 0).group_by("gsis_id", "season").agg(pm=wmean(f"d_{m}", f"h_{m}"), w=c(f"h_{m}").sum()).filter(c("w") >= 20)
            rows.append({"side": side, "group": grp, "measure": m, "week_r": wr, "week_lo": wlo, "week_hi": whi, "units": wn, "season_r": sr, "season_lo": slo, "season_hi": shi, "pairs": sn,
                         "new_team_r": tr, "nt_lo": tlo, "nt_hi": thi, "nt_pairs": tn, "sd_pm": float(ps["pm"].std()) if ps.height > 2 else math.nan})
    print(pl.DataFrame(rows).sort("side", "measure", "group").with_columns(pl.selectors.float().round(3)))

    print("\n=== H28/H29, in season: with and without by game (snap shares), split-half and season to season")
    g = game_level(pg)
    whole = with_without(g, by_half=False)
    half = with_without(g, by_half=True)
    rows = []
    for (side, grp), d in whole.group_by("side", "group", maintain_order=True):
        for m in ("proe", "pace"):
            hd = half.filter((c("side") == side) & (c("group") == grp))
            j = hd.filter(c("odd")).join(hd.filter(~c("odd")), on=["gsis_id", "side", "team", "season"], suffix="_e")
            wr, wlo, whi, wn = r_ci(j[f"d_{m}"].to_numpy(), j[f"d_{m}_e"].to_numpy())
            nxt = d.with_columns(c("season") - 1)
            s = d.join(nxt, on=["gsis_id", "side", "season"], suffix="_next")
            sr, slo, shi, sn = r_ci(s[f"d_{m}"].to_numpy(), s[f"d_{m}_next"].to_numpy())
            rows.append({"side": side, "group": grp, "measure": m, "player_seasons": d.height, "mean_d": float(d[f"d_{m}"].mean()), "week_r": wr, "week_lo": wlo, "week_hi": whi, "units": wn, "season_r": sr, "season_lo": slo, "season_hi": shi, "pairs": sn})
    print(pl.DataFrame(rows).sort("side", "measure", "group").with_columns(pl.selectors.float().round(3)))

    # QBs: the with-without gap, in the market's direction (backups pass less)?
    q = whole.filter((c("side") == "offense") & (c("group") == "QB"))
    print("\nQB with minus without (team-seasons with both):", q.height,
          " PROE mean", round(float(q["d_proe"].mean()), 4), "median", round(float(q["d_proe"].median()), 4),
          " pace mean", round(float(q["d_pace"].mean()), 3))
    pg.write_parquet(Path(player_game.__globals__["CACHE"]) / "player_game_pm.parquet")


if __name__ == "__main__":
    pl.Config.set_tbl_rows(80)
    pl.Config.set_tbl_cols(30)
    pl.Config.set_tbl_width_chars(250)
    main()
