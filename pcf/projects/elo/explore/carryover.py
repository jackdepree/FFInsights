"""The CEO's three questions of 2026-11-07, on the walk as built (pcf.experts.elo).

1. Carryover: how much of a team's strength carries into next season? Year-to-year slopes of
   three measures (mean margin, schedule-adjusted margin, the end-of-season rating), then the
   walk's own forecasts for pulls 0.2 to 0.8 (rating-only: gap + home field).
2. Strength of schedule: does beating good teams raise the rating? The end-of-season rating
   against the team's mean margin and its opponents' mean rating at game time.
3. Resting starters: in the final regular-season week, how often is the usual QB healthy, on the
   roster, not listed Out or Doubtful, and yet plays under half the snaps? By the team's rating
   rank and wins going in, against the same rate in weeks 5 to the second-last.

Regular-season games only for the measures. The vault (2025) isn't read.
Run from pcf/: .venv/Scripts/python.exe projects/elo/explore/carryover.py
"""

# ruff: noqa: E501
from __future__ import annotations

from dataclasses import replace

import numpy as np
import polars as pl

from pcf.data.gateway import Gateway
from pcf.data.tables.store import read_part
from pcf.experts.elo.features import results
from pcf.experts.elo.ratings import DEFAULT, Walk, season_priors

c = pl.col
LAST = 2024


def games() -> pl.DataFrame:
    s = Gateway().source
    sched = s.part("game", "schedule").filter(c("season") <= LAST)
    res = s.part("game", "result").select(
        "game_id", "home_score", "away_score", result_known_at="known_at"
    )
    return sched.join(res, on="game_id", how="left")


def walk_all(g: pl.DataFrame, settings=DEFAULT):
    """Each game's pre-game gap and home field, and each team's rating at the end of each regular
    season (before any playoff result)."""
    res = results(g).join(g.select("game_id", "game_type", "week"), on="game_id")
    w = Walk(season_priors(res, settings), settings)
    pre, ends = [], {}
    for x in res.iter_rows(named=True):
        if x["game_type"] != "REG" and (x["season"], "end") not in ends:
            ends[(x["season"], "end")] = True
            for t, r in w.r.items():
                ends[(x["season"], t)] = r
        e = w.edges(x["season"], x["home_team"], x["away_team"], x["neutral"])
        pre.append({"game_id": x["game_id"], "season": x["season"], "week": x["week"],
                    "game_type": x["game_type"], "home_team": x["home_team"], "away_team": x["away_team"],
                    "r_home": w.r[x["home_team"]], "r_away": w.r[x["away_team"]],
                    "fc": e["gap"] + e["hfa"], "margin": x["margin"]})  # fmt: skip
        w.add(x)
    end = pl.DataFrame(
        [{"season": s, "team": t, "end": v} for (s, t), v in ends.items() if t != "end"]
    )
    return pl.DataFrame(pre), end


def team_seasons(pre: pl.DataFrame) -> pl.DataFrame:
    reg = pre.filter(c("game_type") == "REG")
    rows = pl.concat([
        reg.select("season", "game_id", team="home_team", opp="away_team", m="margin", opp_r="r_away"),
        reg.select("season", "game_id", team="away_team", opp="home_team", m=-c("margin"), opp_r="r_home"),
    ])  # fmt: skip
    out = rows.group_by("season", "team").agg(
        mean_margin=c("m").mean(), opp_rating=c("opp_r").mean()
    )
    # schedule-adjusted margin (SRS): margin = hfa + s_home - s_away, least squares, ratings sum to 0
    srs = []
    for s in reg["season"].unique().sort():
        d = reg.filter(c("season") == s)
        teams = sorted(set(d["home_team"]) | set(d["away_team"]))
        ix = {t: i for i, t in enumerate(teams)}
        x = np.zeros((d.height + 1, len(teams) + 1))
        for j, r in enumerate(d.iter_rows(named=True)):
            x[j, ix[r["home_team"]]], x[j, ix[r["away_team"]]], x[j, -1] = 1, -1, 1
        x[-1, :-1] = 1
        y = np.append(d["margin"].to_numpy(), 0)
        b = np.linalg.lstsq(x, y, rcond=None)[0]
        srs += [{"season": s, "team": t, "srs": b[ix[t]]} for t in teams]
    return out.join(pl.DataFrame(srs), on=["season", "team"])


def slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    b = np.polyfit(x, y, 1)[0]
    return b, float(np.corrcoef(x, y)[0, 1])


def carryover(ts: pl.DataFrame) -> None:
    nxt = ts.with_columns(season=c("season") - 1)
    d = ts.join(nxt, on=["season", "team"], suffix="_next").filter(c("season") >= 2002)
    print("== 1a. How much carries into next season (slope = share kept; 1 - slope = pull)")
    print(f"   {'this season -> next season':<52}{'seasons':<12}{'slope':>7}{'corr':>7}")
    pairs = [
        ("mean margin -> mean margin", "mean_margin", "mean_margin_next"),
        ("schedule-adjusted margin -> schedule-adjusted margin", "srs", "srs_next"),
        ("end-of-season rating -> next schedule-adjusted margin", "end", "srs_next"),
        ("end-of-season rating -> next end-of-season rating", "end", "end_next"),
    ]
    for name, a, b in pairs:
        for lo, hi in ((2002, 2014), (2015, 2023), (2002, 2023)):
            e = d.filter(c("season").is_between(lo, hi))
            s, r = slope(e[a].to_numpy(), e[b].to_numpy())
            print(f"   {name:<52}{lo}-{hi + 1:<7}{s:>7.2f}{r:>7.2f}")


def pull_grid(g: pl.DataFrame) -> None:
    print(
        "\n== 1b. The walk's own forecasts by pull: mean miss on the home margin, points (rating only)"
    )
    print(
        f"   {'pull':<6}{'2002-15 wk1-4':>14}{'2002-15 all':>12}{'2016-24 wk1-4':>14}{'2016-24 all':>12}"
    )
    for p in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        pre, _ = walk_all(g, replace(DEFAULT, pull=p))
        pre = pre.filter(c("game_type") == "REG").with_columns(err=(c("margin") - c("fc")).abs())
        cells = []
        for lo, hi in ((2002, 2015), (2016, 2024)):
            e = pre.filter(c("season").is_between(lo, hi))
            cells += [e.filter(c("week") <= 4)["err"].mean(), e["err"].mean()]
        print(
            f"   {p:<6}"
            + "".join(f"{v:>14.3f}" if i % 2 == 0 else f"{v:>12.3f}" for i, v in enumerate(cells))
        )


def schedule_strength(ts: pl.DataFrame) -> None:
    d = ts.filter(c("season").is_between(2002, LAST))
    x = np.column_stack(
        [d["mean_margin"].to_numpy(), d["opp_rating"].to_numpy(), np.ones(d.height)]
    )
    b = np.linalg.lstsq(x, d["end"].to_numpy(), rcond=None)[0]
    print(
        "\n== 2. Strength of schedule: end-of-season rating = a x mean margin + b x opponents' mean rating"
    )
    print(
        f"   a = {b[0]:.2f} per point of margin, b = {b[1]:.2f} per point of opponent rating ({d.height} team-seasons, 2002-2024)"
    )
    print(
        f"   corr(end rating, schedule-adjusted margin) = {np.corrcoef(d['end'], d['srs'])[0, 1]:.2f}; with plain mean margin = {np.corrcoef(d['end'], d['mean_margin'])[0, 1]:.2f}"
    )
    print(
        f"   opponents' mean rating ranges {d['opp_rating'].min():.1f} to {d['opp_rating'].max():.1f} points (sd {d['opp_rating'].std():.1f})"
    )


def qb_rest(g: pl.DataFrame) -> pl.DataFrame:
    """Per regular-season team-game, 2013-2024, for teams with a clear usual QB (75%+ of offense
    snaps over the previous 4 games): `sat` (on the roster, not listed Out or Doubtful, under half
    the snaps), `listed_out`, and `final` (the season's last regular-season week)."""
    seasons = list(range(2013, LAST + 1))
    roster = (
        read_part("player_game", "roster", seasons=seasons)
        .select("gsis_id", "game_id", "season", "week", "team", "position")
        .collect()
    )
    snaps = (
        read_part("player_game", "snaps", seasons=seasons)
        .select("gsis_id", "game_id", "offense_pct")
        .collect()
    )
    inj = (
        read_part("player_game", "injury", seasons=seasons)
        .select("gsis_id", "game_id", "report_status")
        .collect()
    )
    reg = g.filter((c("game_type") == "REG") & c("season").is_in(seasons)).select(
        "game_id", "season", "week", "kickoff", "home_team", "away_team", "home_score", "away_score"
    )
    last_week = reg.group_by("season").agg(last=c("week").max())
    pg = (
        roster.join(reg.select("game_id", "kickoff"), on="game_id")
        .join(snaps, on=["gsis_id", "game_id"], how="left")
        .join(inj, on=["gsis_id", "game_id"], how="left")
        .with_columns(c("offense_pct").fill_null(0.0))
        .with_columns(n=c("kickoff").rank("dense").over("season", "team"))
    )
    # usual QB: top offense share over the team's previous 4 games
    qb = pg.filter(c("position") == "QB")
    games_n = pg.select("season", "team", "game_id", "week", "n").unique()
    hist = games_n.join(
        qb.select("season", "team", "gsis_id", "offense_pct", past="n"), on=["season", "team"]
    ).filter(c("past").is_between(c("n") - 4, c("n") - 1))
    usual = (
        hist.group_by("season", "team", "game_id", "week", "n", "gsis_id")
        .agg(share=c("offense_pct").sum() / 4)
        .sort(["share", "gsis_id"], descending=[True, False])
        .group_by("season", "team", "game_id", maintain_order=True)
        .first()
    )
    now = qb.select("gsis_id", "game_id", "offense_pct", "report_status")
    u = (
        usual.filter(c("share") >= 0.75)  # a clear starter
        .join(now, on=["gsis_id", "game_id"], how="left")
        .join(last_week, on="season")
        .with_columns(
            on_roster=c("offense_pct").is_not_null(),
            listed_out=c("report_status").is_in(["Out", "Doubtful"]).fill_null(False),
        )
        .with_columns(
            sat=c("on_roster") & ~c("listed_out") & (c("offense_pct") < 0.5),
            final=c("week") == c("last"),
        )
    )
    return u


def resting(g: pl.DataFrame, pre: pl.DataFrame) -> None:
    u = qb_rest(g)
    reg = g.filter((c("game_type") == "REG") & c("season").is_in(list(range(2013, LAST + 1)))).select(
        "game_id", "season", "week", "kickoff", "home_team", "away_team", "home_score", "away_score"
    )
    last_week = reg.group_by("season").agg(last=c("week").max())
    base = u.filter(~c("final") & (c("n") >= 5))
    fin = u.filter(c("final"))
    print(
        "\n== 3. Resting starters: the usual QB (75%+ of snaps) on the roster, not listed Out or Doubtful, under half the snaps"
    )
    print(
        f"   weeks 5 to second-last: {base['sat'].mean():.1%} of {base.height:,} team-games (injuries in the game, benchings)"
    )
    print(
        f"   final week:             {fin['sat'].mean():.1%} of {fin.height} team-games ({fin['sat'].sum()} QBs); listed Out or Doubtful: {fin['listed_out'].mean():.1%} (other weeks {base['listed_out'].mean():.1%})"
    )

    # context going into the final week: rating rank (pre-game) and wins so far
    side = pl.concat([
        pre.select("game_id", team="home_team", r="r_home"), pre.select("game_id", team="away_team", r="r_away"),
    ])  # fmt: skip
    res = pl.concat([
        reg.select("game_id", "season", "week", team="home_team", m=c("home_score") - c("away_score")),
        reg.select("game_id", "season", "week", team="away_team", m=c("away_score") - c("home_score")),
    ]).with_columns(win=pl.when(c("m") > 0).then(1.0).when(c("m") == 0).then(0.5).otherwise(0.0))  # fmt: skip
    wins = (
        res.join(last_week, on="season")
        .filter(c("week") < c("last"))
        .group_by("season", "team")
        .agg(wins=c("win").sum(), played=pl.len())
    )
    f = (
        fin.select("season", "team", "game_id", "sat", "listed_out")
        .join(side, on=["game_id", "team"])
        .join(wins, on=["season", "team"])
        .with_columns(rank=c("r").rank("ordinal", descending=True).over("season"))
        .with_columns(rested=c("sat") | c("listed_out"))
    )
    print(
        "\n   final week by rating rank going in (rested = under half the snaps healthy, or listed Out/Doubtful)"
    )
    print(f"   {'rank':<10}{'rating':>14}{'team-games':>12}{'played <50%':>13}{'listed out':>12}")
    for lo, hi in ((1, 2), (3, 4), (5, 8), (9, 16), (17, 24), (25, 32)):
        e = f.filter(c("rank").is_between(lo, hi))
        print(
            f"   {lo}-{hi:<8}{e['r'].min():>6.1f} to {e['r'].max():>4.1f}{e.height:>12}{e['sat'].mean():>13.1%}{e['listed_out'].mean():>12.1%}"
        )
    print(
        f"\n   {'wins going in (of 15-16)':<26}{'team-games':>12}{'played <50%':>13}{'listed out':>12}"
    )
    for lo, hi in ((0, 5.5), (6, 8.5), (9, 10.5), (11, 11.5), (12, 12.5), (13, 17)):
        e = f.filter(c("wins").is_between(lo, hi))
        print(
            f"   {lo:g}-{hi:g}{'':<22}{e.height:>12}{e['sat'].mean():>13.1%}{e['listed_out'].mean():>12.1%}"
        )
    print("\n   the QBs who sat healthy in the final week:")
    print(
        f.filter(c("sat"))
        .sort("season", "rank")
        .select("season", "team", "rank", r=c("r").round(1), wins="wins")
    )


def rest_flag(g: pl.DataFrame, pre: pl.DataFrame) -> None:
    """Would a flag help? Elo's miss (rating only) for flagged teams, final week against other weeks,
    2002-2024. Flags known before the final week: wins going in, rating rank going in."""
    reg = pre.filter(c("game_type") == "REG").join(
        g.select("game_id", "home_score", "away_score"), on="game_id"
    )
    last = reg.group_by("season").agg(last=c("week").max())
    rows = pl.concat([
        reg.select("game_id", "season", "week", team="home_team", r="r_home", miss=c("margin") - c("fc")),
        reg.select("game_id", "season", "week", team="away_team", r="r_away", miss=-(c("margin") - c("fc"))),
    ]).join(last, on="season").with_columns(final=c("week") == c("last"))  # fmt: skip
    rows = rows.join(
        pl.concat([
            reg.select("season", "week", team="home_team", w=(c("margin") > 0).cast(pl.Float64) + 0.5 * (c("margin") == 0)),
            reg.select("season", "week", team="away_team", w=(c("margin") < 0).cast(pl.Float64) + 0.5 * (c("margin") == 0)),
        ]).join(rows.select("season", "team", "week").rename({"week": "at"}), on=["season", "team"])
        .filter(c("week") < c("at")).group_by("season", "team", "at").agg(wins=c("w").sum(), played=pl.len())
        .rename({"at": "week"}),
        on=["season", "team", "week"], how="left",
    ).with_columns(rank=c("r").rank("ordinal", descending=True).over("season", "week"),
                   pct=c("wins") / c("played"))  # fmt: skip
    rows = rows.filter(c("season").is_between(2002, LAST))
    print(
        "\n== 3b. Would a flag help? The team's points against Elo's rating-only forecast (+ = did better), 2002-2024"
    )
    print(
        f"   {'flag (known before the game)':<34}{'final week':>22}{'weeks 10 to second-last':>26}"
    )
    flags = {
        "win rate .800+ going in": c("pct") >= 0.8,
        "win rate .700-.799": c("pct").is_between(0.7, 0.7999),
        "rating rank 1-4": c("rank") <= 4,
        "win rate .600-.699": c("pct").is_between(0.6, 0.6999),
        "win rate under .300 (out of it)": c("pct") < 0.3,
        "everyone else": (c("pct").is_between(0.3, 0.5999)),
    }
    for name, f in flags.items():
        cells = []
        for part in (c("final"), ~c("final") & (c("week") >= 10)):
            e = rows.filter(part & f)
            se = e["miss"].std() / np.sqrt(e.height)
            cells.append(f"{e['miss'].mean():+5.1f} ± {1.64 * se:3.1f} ({e.height:>4})")
        print(f"   {name:<34}{cells[0]:>22}{cells[1]:>26}")


def main() -> None:
    pl.Config.set_tbl_rows(80)
    pl.Config.set_tbl_hide_dataframe_shape(True)
    g = games()
    pre, end = walk_all(g)
    ts = team_seasons(pre).join(end, on=["season", "team"])
    carryover(ts)
    schedule_strength(ts)
    resting(g, pre)
    rest_flag(g, pre)
    pull_grid(g)


if __name__ == "__main__":
    main()
