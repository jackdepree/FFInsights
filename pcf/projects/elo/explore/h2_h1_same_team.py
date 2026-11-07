"""H2 and H1: is it the same team? Snap counts (2013-) and the injury report.

H2, turnover between seasons. A team's returning share is the share of its offense and defense
snaps last regular season played by players on its roster for its first game this season (known
before that game). Each team's pull toward average is 0.5 + b x (the league's average returning
share - the team's), kept between 0 and 1. b = 0 is rung 1. Tuned on 2014-2019, reported on
2020-2024.

H1, the same team this week. A player's usual share is their average snap share in the team's
previous (up to 4) games this season, offense and defense. They're missing from this game if
they're not on the roster for it, or the injury report lists them Out or Doubtful (both known by
the Saturday run, decision 0016). Week 1 has no usual shares, so no adjustment.
- `qb`: the usual starting quarterback (the QB with the highest usual offense share) is missing.
- `share`: the team's same-team share, the usual shares of available players over all usual
  shares, offense and defense averaged.
The pre-game margin moves by c_qb x (away QB missing - home QB missing) and c x (home share -
away share). Sizes are tuned on 2013-2015 and reported on 2016-2024 (rung 1's step and pull
are kept).

The vault (2025) isn't read. Run from pcf/:
.venv/Scripts/python.exe projects/elo/explore/h2_h1_same_team.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import ladder as L  # noqa: E402

from pcf.data.tables.store import read_part  # noqa: E402

c = pl.col
SNAP_SEASONS = list(range(2013, L.LAST + 1))
USUAL_GAMES = 4


def player_games() -> pl.DataFrame:
    """Every rostered player-game (2013-2024): team, position, snap shares, injury status."""
    roster = read_part("player_game", "roster", seasons=SNAP_SEASONS).select(
        "gsis_id", "game_id", "season", "week", "team", "position"
    )
    snaps = read_part("player_game", "snaps", seasons=SNAP_SEASONS).select(
        "gsis_id", "game_id", "offense_pct", "defense_pct"
    )
    inj = read_part("player_game", "injury", seasons=SNAP_SEASONS).select(
        "gsis_id", "game_id", "report_status"
    )
    return (
        roster.join(snaps, on=["gsis_id", "game_id"], how="left")
        .join(inj, on=["gsis_id", "game_id"], how="left")
        .with_columns(c("offense_pct", "defense_pct").fill_null(0.0))
        .collect()
    )


def returning_share(pg: pl.DataFrame, g: pl.DataFrame) -> dict[tuple[int, str], float]:
    """(season, team) -> share of last regular season's snaps by players on the week-1 roster."""
    reg = g.filter(c("game_type") == "REG").select("game_id")
    last = (
        pg.join(reg, on="game_id")
        .group_by("season", "team", "gsis_id")
        .agg(snaps=(c("offense_pct") + c("defense_pct")).sum())
    )
    first = (
        pg.with_columns(first_week=c("week").min().over("season", "team"))
        .filter(c("week") == c("first_week"))
        .select("season", "team", "gsis_id")
        .unique()
    )
    out = {}
    for s in SNAP_SEASONS[1:]:
        prev = last.filter(c("season") == s - 1)
        now = first.filter(c("season") == s).with_columns(back=pl.lit(True)).drop("season")
        j = prev.join(now, on=["team", "gsis_id"], how="left").with_columns(
            c("back").fill_null(False)
        )
        t = j.group_by("team").agg(share=(c("snaps") * c("back")).sum() / c("snaps").sum())
        out |= {(s, row["team"]): row["share"] for row in t.iter_rows(named=True)}
    return out


def same_team(pg: pl.DataFrame) -> pl.DataFrame:
    """Per (game, team): the usual QB missing (0/1) and the same-team share, from the previous
    games this season."""
    tg = pg.select("season", "team", "game_id", "week").unique().sort("season", "team", "week")
    tg = tg.with_columns(n=c("week").rank("ordinal").over("season", "team"))
    pgn = pg.join(tg.select("game_id", "team", "n"), on=["game_id", "team"])
    rows = []
    for (season, team), games in tg.group_by("season", "team"):
        mine = pgn.filter((c("season") == season) & (c("team") == team))
        for row in games.iter_rows(named=True):
            n = row["n"]
            if n == 1:
                continue
            past = mine.filter(c("n").is_between(n - USUAL_GAMES, n - 1))
            k = past["n"].n_unique()
            usual = past.group_by("gsis_id").agg(
                off=c("offense_pct").sum() / k,
                de=c("defense_pct").sum() / k,
                qb=(c("position") == "QB").any(),
            )
            now = mine.filter(c("n") == n).select(
                "gsis_id", out=c("report_status").is_in(["Out", "Doubtful"]).fill_null(False)
            )
            u = usual.join(now, on="gsis_id", how="left").with_columns(
                avail=~c("out").fill_null(True)  # not on this game's roster: missing
            )
            off = float((u["off"] * u["avail"]).sum() / max(u["off"].sum(), 1e-9))
            de = float((u["de"] * u["avail"]).sum() / max(u["de"].sum(), 1e-9))
            qbs = u.filter(c("qb")).sort("off", descending=True)
            qb_out = float(qbs.height > 0 and not qbs["avail"][0])
            rows.append(
                {"game_id": row["game_id"], "team": team, "share": (off + de) / 2, "qb_out": qb_out}
            )
    return pl.DataFrame(rows)


def main() -> None:
    g = L.games()
    priors = L.season_priors(g)
    pg = player_games()

    # ---------------------------------------------------------------------------- H2
    ret = returning_share(pg, g)
    vals = pl.Series(list(ret.values()))
    print(
        f"returning share: mean {vals.mean():.3f}, sd {vals.std():.3f}, "
        f"min {vals.min():.3f}, max {vals.max():.3f}"
    )
    mean_by_season = {}
    for (s, _t), v in ret.items():
        mean_by_season.setdefault(s, []).append(v)
    mean_by_season = {s: sum(v) / len(v) for s, v in mean_by_season.items()}

    def pull_for(b):
        def f(s, t):
            if (s, t) not in ret:
                return 0.5
            return min(max(0.5 + b * (mean_by_season[s] - ret[(s, t)]), 0.0), 1.0)

        return f

    print("\nH2: pull set by turnover (b = 0 is rung 1)")
    bs = (0, 0.5, 1, 1.5, 2, 3, 4)
    grid = [{"k": 0.06, "pull": 0.5, "b": b, "pull_fn": pull_for(b)} for b in bs]
    for p in grid:
        r = L.versus_rung1(g, priors, "margin_pull", [p], lo=2016, tune_lo=2014)
        print(f"   b={p['b']}: 2016-2024 gap {r['gap'][0]:+.3f}")
    r = L.versus_rung1(g, priors, "margin_pull", grid, lo=2020, tune_lo=2014)
    L.show("tuned 2014-2019, 2020-2024", r)

    # ---------------------------------------------------------------------------- H1
    st = same_team(pg)
    print(
        f"\nsame-team share: mean {st['share'].mean():.3f}, p10 {st['share'].quantile(0.1):.3f}; "
        f"usual QB missing in {st['qb_out'].mean():.1%} of team-games"
    )
    h = st.rename({"team": "home_team", "share": "h_share", "qb_out": "h_qb"})
    a = st.rename({"team": "away_team", "share": "a_share", "qb_out": "a_qb"})
    g1 = (
        g.join(h, on=["game_id", "home_team"], how="left")
        .join(a, on=["game_id", "away_team"], how="left")
        .with_columns(c("h_share", "a_share").fill_null(1.0), c("h_qb", "a_qb").fill_null(0.0))
    )
    known = g1.filter(c("season") >= 2013)
    print(
        f"games with both teams measured, 2016-2024: "
        f"{known.filter((c('season') >= 2016) & (c('week') > 1)).height}"
    )

    def adj(cq, cs):
        return lambda x: cq * (x["a_qb"] - x["h_qb"]) + cs * (x["h_share"] - x["a_share"])

    print("\nH1: same team this week (sizes tuned 2013-2015, reported 2016-2024)")
    for label, grid in (
        ("qb only (the usual way)", [{"cq": q, "cs": 0} for q in (0, 2, 3, 4, 5, 6, 8)]),
        ("share only", [{"cq": 0, "cs": s} for s in (0, 5, 10, 20, 30, 40, 60)]),
        ("qb and share", [{"cq": q, "cs": s} for q in (2, 4, 6) for s in (0, 10, 20, 40)]),
    ):
        ps = [{"k": 0.06, "pull": 0.5, "adj_fn": adj(x["cq"], x["cs"]), "sizes": x} for x in grid]
        L.show(label, L.versus_rung1(g1, priors, "margin_pull", ps, lo=2016, tune_lo=2013))


if __name__ == "__main__":
    main()
