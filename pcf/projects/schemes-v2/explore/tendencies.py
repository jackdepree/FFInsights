"""Schemes v2 exploration, parts 2 and 3 (2026-11-08, discovery only).

Builds one row per team-game, 2006-2024 regular season, with the team's offensive and defensive
tendencies in that game, its outcomes, its head coach and its starting QB, and saves it to
`interim/schemes_v2/team_game.parquet` for the later scripts. Then:

1. Consistency of every tendency (`pcf.validation.consistency`, team-seasons), plus split-half
   reliability inside regimes (the CEO's regime: same head coach and same starting QB).
2. Whose is it (H10, I21): season-to-season carryover split by what changed between the
   seasons: nothing, the QB only, the coach only, both.
3. Head coaches who change teams (H10, the movers design): does the new team's first season
   look like the coach's last season elsewhere, or like the new team's previous season?
4. How fast tendencies settle in a new regime, against efficiency (I25).

Tendencies are measured in neutral situations (win chance 20-80%, downs 1-3, not the last two
minutes of a half). Rates that depend on down and distance are taken against the league's rate
for that season, down and distance. Participation tendencies (coverage, blitz, box, personnel)
exist 2016-2024 only, and after the season only (retrospective). The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/tendencies.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.tables.store import read_part
from pcf.validation.consistency import consistency

c = pl.col
SEASONS = range(2006, 2025)
OUT = get_config().zone("interim") / "schemes_v2"

PBP = ["game_id", "play_id", "season", "season_type", "week", "posteam", "defteam", "home_team", "home_coach", "away_coach",
       "play_type", "down", "ydstogo", "yardline_100", "qtr", "half_seconds_remaining", "game_seconds_remaining", "wp",
       "shotgun", "no_huddle", "qb_dropback", "qb_scramble", "qb_kneel", "qb_spike", "pass", "rush", "xpass", "air_yards",
       "pass_location", "run_location", "run_gap", "epa", "success", "passer_player_id", "fixed_drive", "sack", "qb_hit",
       "penalty", "out_of_bounds", "pass_attempt"]

OFF = ["proe", "shotgun_oe", "no_huddle_oe", "adot", "deep_rate", "middle_rate", "outside_run", "scramble_rate", "tempo", "fourth_go"]
DEF = ["d_proe_faced", "d_adot_faced", "d_pressure"]
OFF_P = ["p11", "heavy"]
DEF_P = ["d_man", "d_two_high", "d_blitz", "d_box_oe"]
OUTCOMES = ["off_epa", "off_success", "def_epa"]
ALL = OFF + OFF_P + DEF + DEF_P


def dist_bucket(e: pl.Expr) -> pl.Expr:
    return pl.when(e <= 2).then(0).when(e <= 6).then(1).when(e <= 10).then(2).otherwise(3)


def plays(season: int) -> pl.DataFrame:
    p = read_part("play", "pbp", [season]).select(PBP).collect().filter(c("season_type") == "REG")
    if season >= 2016:
        part = read_part("play", "participation", [season]).select(
            "game_id", "play_id", "offense_personnel", "defenders_in_box", "number_of_pass_rushers",
            "defense_man_zone_type", "defense_coverage_type").collect()
        p = p.join(part, on=["game_id", "play_id"], how="left")
    return p.sort("game_id", "play_id").with_columns(
        dist=dist_bucket(c("ydstogo")),
        neutral=c("wp").is_between(0.2, 0.8) & c("down").is_between(1, 3) & (c("half_seconds_remaining") > 120) & (c("qtr") <= 4),
        scrim=((c("pass") == 1) | (c("rush") == 1)) & (c("qb_kneel") == 0) & (c("qb_spike") == 0),
        coach=pl.when(c("posteam") == c("home_team")).then(c("home_coach")).otherwise(c("away_coach")),
    )


def team_game(p: pl.DataFrame) -> pl.DataFrame:
    s = p.filter(c("scrim") & c("posteam").is_not_null())
    n = s.filter(c("neutral"))
    # league rates by season, down and distance (the "expected" for shotgun, no-huddle, box)
    n = n.with_columns(
        shotgun_oe=c("shotgun") - c("shotgun").mean().over("down", "dist"),
        no_huddle_oe=c("no_huddle") - c("no_huddle").mean().over("down", "dist"),
        att=(c("pass_attempt") == 1) & (c("sack") == 0) & c("air_yards").is_not_null(),
        run=(c("rush") == 1) & (c("qb_scramble") == 0),
    )
    has_p = "offense_personnel" in p.columns
    if has_p:
        n = n.with_columns(
            rb=c("offense_personnel").str.extract(r"(\d) RB").cast(pl.Int32, strict=False),
            te=c("offense_personnel").str.extract(r"(\d) TE").cast(pl.Int32, strict=False),
            box_oe=c("defenders_in_box") - c("defenders_in_box").mean().over("down", "dist", "shotgun"),
        )

    off_aggs = [
        (c("pass") - c("xpass")).mean().alias("proe"),
        c("shotgun_oe").mean(), c("no_huddle_oe").mean(),
        c("air_yards").filter(c("att")).mean().alias("adot"),
        (c("air_yards") >= 20).filter(c("att")).mean().alias("deep_rate"),
        (c("pass_location") == "middle").filter(c("att") & c("pass_location").is_not_null()).mean().alias("middle_rate"),
        (c("run_gap") == "end").fill_null(False).filter(c("run") & c("run_location").is_not_null()).mean().alias("outside_run"),
        c("qb_scramble").filter(c("qb_dropback") == 1).mean().alias("scramble_rate"),
    ]
    if has_p:
        off_aggs += [((c("rb") == 1) & (c("te") == 1)).filter(c("rb").is_not_null()).mean().alias("p11"),
                     ((c("rb") + c("te")) >= 3).filter(c("rb").is_not_null()).mean().alias("heavy")]
    off = n.group_by("game_id", "season", "week", team="posteam", opp="defteam").agg(off_aggs)

    def_aggs = [
        (c("pass") - c("xpass")).mean().alias("d_proe_faced"),
        c("air_yards").filter(c("att")).mean().alias("d_adot_faced"),
        ((c("sack") == 1) | (c("qb_hit") == 1)).filter(c("qb_dropback") == 1).mean().alias("d_pressure"),
    ]
    if has_p:
        cov = c("defense_coverage_type")
        def_aggs += [
            (c("defense_man_zone_type") == "MAN_COVERAGE").filter(c("defense_man_zone_type").is_in(["MAN_COVERAGE", "ZONE_COVERAGE"])).mean().alias("d_man"),
            cov.is_in(["COVER_2", "COVER_4", "COVER_6", "2_MAN"]).filter(cov.is_in(["COVER_0", "COVER_1", "COVER_2", "COVER_3", "COVER_4", "COVER_6", "2_MAN"])).mean().alias("d_two_high"),
            (c("number_of_pass_rushers") >= 5).filter((c("qb_dropback") == 1) & c("number_of_pass_rushers").is_not_null()).mean().alias("d_blitz"),
            c("box_oe").mean().alias("d_box_oe"),
        ]
    dfn = n.group_by("game_id", team="defteam").agg(def_aggs)

    # tempo: game seconds from an in-bounds run to the next snap on the same drive (clock running)
    t = s.with_columns(
        gap=c("game_seconds_remaining").shift(1).over("game_id") - c("game_seconds_remaining"),
        prev_ok=((c("rush").shift(1).over("game_id") == 1) & (c("out_of_bounds").shift(1).over("game_id") == 0)
                 & (c("penalty").shift(1).over("game_id") == 0) & (c("fixed_drive").shift(1).over("game_id") == c("fixed_drive"))),
    ).filter(c("neutral") & c("prev_ok") & c("gap").is_between(5, 60))
    tempo = t.group_by("game_id", team="posteam").agg(tempo=c("gap").mean())

    # fourth downs, short yardage around midfield: went for it (pass or run) against punt or field goal
    f = p.filter((c("down") == 4) & (c("ydstogo") <= 2) & c("yardline_100").is_between(30, 65)
                 & c("wp").is_between(0.1, 0.9) & c("play_type").is_in(["pass", "run", "punt", "field_goal"]))
    fourth = f.group_by("game_id", team="posteam").agg(fourth_go=c("play_type").is_in(["pass", "run"]).mean(), fourth_n=pl.len())

    outc = s.group_by("game_id", team="posteam").agg(off_epa=c("epa").mean(), off_success=c("success").mean(), off_plays=pl.len())
    outd = s.group_by("game_id", team="defteam").agg(def_epa=c("epa").mean())
    qb = (s.filter((c("qb_dropback") == 1) & c("passer_player_id").is_not_null())
          .group_by("game_id", team="posteam", qb="passer_player_id").agg(k=pl.len())
          .sort("k", descending=True).group_by("game_id", "team").first().drop("k"))
    coach = s.group_by("game_id", team="posteam").agg(c("coach").first())
    return (off.join(dfn, on=["game_id", "team"], how="left").join(tempo, on=["game_id", "team"], how="left")
            .join(fourth, on=["game_id", "team"], how="left").join(outc, on=["game_id", "team"], how="left")
            .join(outd, on=["game_id", "team"], how="left").join(qb, on=["game_id", "team"], how="left")
            .join(coach, on=["game_id", "team"], how="left"))


def build() -> pl.DataFrame:
    frames = [team_game(plays(s)) for s in SEASONS]
    tg = pl.concat(frames, how="diagonal_relaxed").sort("team", "season", "week")
    # Every tendency and outcome is taken against its league mean that season, so league-wide
    # trends (more shotgun, more 4th-down attempts) don't pass for consistency.
    tg = tg.with_columns(*[(c(m) - c(m).mean().over("season")) for m in ALL + OUTCOMES])
    # Regimes (the CEO's rule): a new one starts when the head coach or the starting QB (most
    # dropbacks) changes. A QB change counts only if the new QB starts two games in a row, so a
    # one-game fill-in stays inside the regime (flagged `fill_in`).
    team, coach, qb = tg["team"].to_list(), tg["coach"].to_list(), tg["qb"].to_list()
    regime, fill_in, game_in = [], [], []
    k = 0
    cur = (None, None, None)
    for i in range(tg.height):
        nxt_same = i + 1 < tg.height and team[i + 1] == team[i] and coach[i + 1] == coach[i] and qb[i + 1] == qb[i]
        if team[i] != cur[0] or coach[i] != cur[1]:
            k, n, cur = k + 1, 0, (team[i], coach[i], qb[i])
        elif qb[i] != cur[2] and nxt_same:
            k, n, cur = k + 1, 0, (team[i], coach[i], qb[i])
        n += 1
        regime.append(f"{team[i]}-{k}")
        fill_in.append(qb[i] != cur[2])
        game_in.append(n)
    tg = tg.with_columns(regime=pl.Series(regime), fill_in=pl.Series(fill_in), game_in_regime=pl.Series(game_in))
    OUT.mkdir(parents=True, exist_ok=True)
    tg.write_parquet(OUT / "team_game.parquet")
    return tg


def r(x, y) -> tuple[float, int]:
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y))
    return (float(np.corrcoef(x[ok], y[ok])[0, 1]) if ok.sum() > 4 else float("nan")), int(ok.sum())


def main() -> None:
    tg = build()
    print(f"team-games {tg.height}, seasons {tg['season'].min()}-{tg['season'].max()}, regimes {tg['regime'].n_unique()}")
    lens = tg.group_by("regime").len()["len"]
    print(f"regime length: median {lens.median():.0f} games, {(lens >= 8).mean():.0%} have 8+ games, {(lens == 1).mean():.0%} are one game")

    print("\n== 1. Consistency per team-season (pcf.validation.consistency), and split-half inside regimes of 8+ games")
    cons = consistency(tg, ALL + OUTCOMES, unit="team")
    long = tg.join(tg.group_by("regime").len().filter(c("len") >= 8).select("regime"), on="regime")
    print(f"{'measure':<14} {'wk-wk r':>8} {'season r':>9} {'verdict':>8} {'regime split-half':>18}")
    for row in cons.iter_rows(named=True):
        m = row["measure"]
        sh = long.with_columns(odd=c("game_in_regime") % 2).group_by("regime", "odd").agg(c(m).mean()).pivot(on="odd", index="regime", values=m)
        rr, k = r(sh["0"], sh["1"]) if {"0", "1"} <= set(sh.columns) else (float("nan"), 0)
        wk, ss = row["week_r"], row["season_r"]
        print(f"{m:<14} {wk:>8.2f} {ss:>9.2f} {row['verdict']:>8} {rr:>12.2f} (n {k})")

    print("\n== 2. Whose is it: season-to-season r of team-season means, by what changed between seasons")
    ts = tg.group_by("team", "season").agg(
        *[c(m).mean() for m in ALL + OUTCOMES],
        coach=c("coach").mode().first(), qb=c("qb").mode().first())
    nxt = ts.with_columns(season=c("season") - 1)
    pair = ts.join(nxt, on=["team", "season"], suffix="_next").with_columns(
        kind=pl.when((c("coach") == c("coach_next")) & (c("qb") == c("qb_next"))).then(pl.lit("same both"))
        .when(c("coach") == c("coach_next")).then(pl.lit("new QB only"))
        .when(c("qb") == c("qb_next")).then(pl.lit("new coach only")).otherwise(pl.lit("both new")))
    kinds = ["same both", "new QB only", "new coach only", "both new"]
    counts = {k: pair.filter(c("kind") == k).height for k in kinds}
    print(f"{'measure':<14}" + "".join(f"{k + f' ({counts[k]})':>22}" for k in kinds))
    for m in ALL + OUTCOMES:
        cells = []
        for k in kinds:
            q = pair.filter(c("kind") == k)
            rr, nn = r(q[m], q[f"{m}_next"])
            cells.append(f"{rr:>16.2f} n{nn:<4}")
        print(f"{m:<14}" + "".join(cells))

    print("\n== 3. Head coaches who change teams: the new team's first season against the coach's last season elsewhere and the new team's previous season")
    first_last = ts.sort("season").group_by("coach", "team", maintain_order=True).agg(
        first=c("season").min(), last=c("season").max())
    moves = []
    for coach, g in first_last.group_by("coach"):
        g = g.sort("first")
        for a, b in zip(g.iter_rows(named=True), list(g.iter_rows(named=True))[1:]):
            if 1 <= b["first"] - a["last"] <= 4 and a["team"] != b["team"]:
                moves.append((coach[0], a["team"], a["last"], b["team"], b["first"]))
    mv = pl.DataFrame(moves, schema=["coach", "old_team", "old_season", "new_team", "new_season"], orient="row")
    old = ts.select("team", "season", *ALL + OUTCOMES)
    j = (mv.join(old, left_on=["old_team", "old_season"], right_on=["team", "season"])
         .join(old.rename({m: f"{m}_new" for m in ALL + OUTCOMES}), left_on=["new_team", "new_season"], right_on=["team", "season"])
         .join(old.with_columns(season=c("season") + 1).rename({m: f"{m}_prev" for m in ALL + OUTCOMES}), left_on=["new_team", "new_season"], right_on=["team", "season"]))
    print(f"   {j.height} moves (head coach, a different team within 4 seasons), e.g. {', '.join(j['coach'].head(5).to_list())}")
    print(f"{'measure':<14} {'r with coach':>13} {'r with team':>12} {'coach weight':>13} {'team weight':>12} {'n':>4}")
    for m in ALL + OUTCOMES:
        q = j.select(m, f"{m}_new", f"{m}_prev").drop_nulls().drop_nans()
        if q.height < 8:
            continue
        rc, _ = r(q[m], q[f"{m}_new"])
        rt, _ = r(q[f"{m}_prev"], q[f"{m}_new"])
        X = np.column_stack([np.ones(q.height), q[m].to_numpy(), q[f"{m}_prev"].to_numpy()])
        X[:, 1:] = (X[:, 1:] - X[:, 1:].mean(0)) / X[:, 1:].std(0)
        y = q[f"{m}_new"].to_numpy()
        y = (y - y.mean()) / y.std()
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        print(f"{m:<14} {rc:>13.2f} {rt:>12.2f} {b[1]:>13.2f} {b[2]:>12.2f} {q.height:>4}")

    print("\n== 4. How fast a tendency settles in a new regime (I25): r between the first k games' mean and the rest of the regime's mean (regimes of 10+ games)")
    lr = tg.join(tg.group_by("regime").len().filter(c("len") >= 10).select("regime"), on="regime")
    ks = [1, 2, 3, 4, 6, 8]
    print(f"{'measure':<14}" + "".join(f"{'k=' + str(k):>7}" for k in ks))
    for m in ["proe", "shotgun_oe", "no_huddle_oe", "adot", "tempo", "d_man", "d_blitz", "off_epa", "def_epa"]:
        cells = []
        for k in ks:
            a = lr.group_by("regime").agg(head=c(m).filter(c("game_in_regime") <= k).mean(), tail=c(m).filter(c("game_in_regime") > k).mean())
            cells.append(f"{r(a['head'], a['tail'])[0]:>7.2f}")
        print(f"{m:<14}" + "".join(cells))


if __name__ == "__main__":
    main()
