"""The player-pace features at a moment (brief: projects/player-pace/BRIEF.md; decision 0029).

Every row is a team's next game, with team pace's features (`pcf.experts.pace.features`, reused)
plus what the players expected to play add, from what's known by the Saturday run:

**The expected starting QB** (`qb_id_expected`): the team's starter in its last game known by the
moment (`team_game.pregame.qb_id`, known at that game's kickoff), unless this week's injury
report lists him Out or Doubtful or he isn't on this game's roster; then the team's rostered QB
not listed Out or Doubtful with the most offensive snaps this season (weekly snap counts), then
last season.

**His own history** (exploration F5, F6): over his starts for any team in the last
`QB_SEASONS` seasons, known by the moment, the team's PROE and pace over expected in them, each
less its season's league level, shrunk toward 0 by `QB_PRIOR` plays (`qb_proe_gap`,
`qb_pace_gap`), and how many starts that is (`qb_starts`).
- `qb_share`: his share of the team's starts this season so far (last season's before week 1).
  The team's own habits already carry a regular starter; `qb_<m>_other` = gap × (1 − share) is
  the part they don't.
- `qb_change`: 1 when he isn't the team's last starter.
- `qb_rookie`: 1 in his first season (roster `years_exp` 0, F7).

**Who's out** (`lineup_out`, F3, F4): the pass lean of the backs, receivers and tight ends this
week's report lists Out or Doubtful, each his share of the team's snaps in its last game times
his plus-minus on PROE over the `PM_SEASONS` earlier finished seasons
(`player_season.on_field_pace`, shrunk by `PM_PRIOR`), summed and negated: a missing pass-tell
lowers the team's lean.

`at_moment` gives one moment's rows; `history` every moment's in one pass from a view that sees
everything (the leakage checks compare the two).
"""

from __future__ import annotations

import polars as pl

from pcf.experts.pace import features as P

c = pl.col
KEYS = P.KEYS
MOMENT = P.MOMENT
INPUTS = {
    "team_game": P.INPUTS["team_game"],
    "player_game": ("roster", "injury", "snaps"),
    "player_season": ("on_field_pace",),
}
QB_SEASONS = 3
QB_PRIOR = {"proe": 600.0, "pace": 500.0}  # plays (snaps for pace) the league's 0 is worth
PM_PRIOR = 50.0  # weight (n_on * n_off / n_team) the league's 0 is worth in a plus-minus
PM_DECAY = 0.7
PM_SEASONS = 4  # earlier finished seasons of plus-minus `lineup_out` reads
OUT = ("Out", "Doubtful")
SKILL = ("RB", "WR", "TE")
QB_COLUMNS = [
    "qb_proe_gap", "qb_pace_gap", "qb_starts", "qb_share", "qb_change", "qb_rookie",
    "qb_proe_other", "qb_pace_other",
]  # fmt: skip


def _starts(tg: pl.DataFrame) -> pl.DataFrame:
    """Every team-game with a known starter and pace measures: the starter, its rates and
    their weights, and when they became known."""
    g = tg.filter(
        c("qb_id").is_not_null() & c("pace_known_at").is_not_null() & c("proe").is_not_null()
    )
    return g.select(
        "team", "season", "kickoff", "qb_id",
        known=pl.max_horizontal("pace_known_at", "pregame_known_at"),
        proe=c("proe"), plays=c("plays").cast(pl.Float64),
        pace=c("pace_oe").fill_null(0.0),
        pace_snaps=pl.when(c("pace_oe").is_not_null()).then(c("pace_snaps")).otherwise(0)
        .cast(pl.Float64),
    )  # fmt: skip


def expected_qb(targets: pl.DataFrame, starts: pl.DataFrame, pg: pl.DataFrame) -> pl.DataFrame:
    """KEYS → `qb_id_expected`, `qb_last` (the team's last starter known by the moment)."""
    seen = targets.join(starts.select("team", "kickoff", "qb_id", "known"), on="team")
    seen = seen.filter(c("known") <= c("moment"))
    last = seen.sort("kickoff").group_by(KEYS).agg(qb_last=c("qb_id").last())
    out = targets.join(last, on=KEYS, how="left")
    # this game's QBs on the roster, and who the report rules out, as known by the moment
    rows = pg.join(targets.select(KEYS + ["moment"]), on=["game_id", "team"], how="inner")
    rostered = rows.filter((c("position") == "QB") & (c("known_at") <= c("moment")))
    ruled_out = rows.filter(
        c("report_status").is_in(OUT) & (c("injury_known_at") <= c("moment"))
    ).select(*KEYS, "gsis_id", out=pl.lit(True))
    rostered = rostered.join(ruled_out, on=[*KEYS, "gsis_id"], how="left").with_columns(
        c("out").fill_null(False)
    )
    # each candidate's offensive snaps for this team, this season then last, known by the moment
    snaps = pg.filter(c("offense_snaps").is_not_null()).select(
        "gsis_id", "team", s_season="season", s_known="snaps_known_at", s="offense_snaps"
    )
    cand = (
        rostered.filter(~c("out"))
        .select(*KEYS, "season", "moment", "gsis_id")
        .join(snaps, on=["gsis_id", "team"], how="left")
        .with_columns(
            ok=(c("s_known") <= c("moment")).fill_null(False)
            & c("s_season").is_between(c("season") - 1, c("season"))
        )
        .group_by(*KEYS, "gsis_id")
        .agg(
            now=c("s").filter(c("ok") & (c("s_season") == c("season"))).sum(),
            before=c("s").filter(c("ok") & (c("s_season") < c("season"))).sum(),
        )
        .sort("now", "before", "gsis_id", descending=[True, True, False])
        .group_by(KEYS, maintain_order=True)
        .agg(best=c("gsis_id").first())
    )
    gone = ruled_out.select(*KEYS, qb_last="gsis_id", last_out=pl.lit(True))
    on_roster = rostered.select(*KEYS, qb_last="gsis_id", last_listed=pl.lit(True))
    has_roster = rostered.select(KEYS).unique().with_columns(roster_known=pl.lit(True))
    out = (
        out.join(gone, on=[*KEYS, "qb_last"], how="left")
        .join(on_roster, on=[*KEYS, "qb_last"], how="left")
        .join(has_roster, on=KEYS, how="left")
        .join(cand, on=KEYS, how="left")
    )
    keep = (
        c("qb_last").is_not_null()
        & ~c("last_out").fill_null(False)
        & (c("last_listed").fill_null(False) | ~c("roster_known").fill_null(False))
    )
    return out.select(
        *KEYS, "qb_last", qb_id_expected=pl.when(keep).then(c("qb_last")).otherwise(c("best"))
    )


def qb_features(targets: pl.DataFrame, tg: pl.DataFrame, pg: pl.DataFrame) -> pl.DataFrame:
    """KEYS → `qb_id_expected` and `QB_COLUMNS` (0 where there's no expected starter)."""
    starts = _starts(tg)
    exp = expected_qb(targets, starts, pg)
    t = targets.join(exp, on=KEYS, how="left")
    window = (c("known") <= c("moment")) & (c("h_season") > c("season") - QB_SEASONS)
    sums = [
        (c("proe") * c("plays")).sum().alias("s_px"), c("plays").sum().alias("s_p"),
        (c("pace") * c("pace_snaps")).sum().alias("s_qx"), c("pace_snaps").sum().alias("s_q"),
    ]  # fmt: skip
    # the league's level over the same seasons, as known by the moment
    league = (
        t.select("season", "moment").unique()
        .join(starts.rename({"season": "h_season"}), how="cross")
        .filter(window)
        .group_by("season", "moment")
        .agg(sums)
        .select("season", "moment", lp=c("s_px") / c("s_p"), lq=c("s_qx") / c("s_q"))
    )  # fmt: skip
    hist = (
        t.select(*KEYS, "season", "moment", qb="qb_id_expected")
        .drop_nulls("qb")
        .join(
            starts.rename({"season": "h_season", "team": "h_team"}), left_on="qb", right_on="qb_id"
        )
        .filter(window)
        .group_by(*KEYS, "season", "moment")
        .agg(*sums, qb_starts=pl.len().cast(pl.Float64))
        .join(league, on=["season", "moment"], how="left")
        .select(
            *KEYS, "qb_starts",
            qb_proe_gap=(c("s_px") - c("lp") * c("s_p")) / (c("s_p") + QB_PRIOR["proe"]),
            qb_pace_gap=(c("s_qx") - c("lq") * c("s_q")) / (c("s_q") + QB_PRIOR["pace"]),
        )
    )  # fmt: skip
    # the team's starts by the moment: this season, or last season before its first game
    team = (
        t.select(*KEYS, "season", "moment", "qb_id_expected")
        .join(starts.select("team", "qb_id", "known", h_season="season"), on="team")
        .filter(
            (c("known") <= c("moment")) & c("h_season").is_between(c("season") - 1, c("season"))
        )
        .with_columns(latest=c("h_season").max().over(KEYS))
        .filter(c("h_season") == c("latest"))
        .group_by(KEYS)
        .agg(qb_share=(c("qb_id") == c("qb_id_expected").first()).mean())
    )
    rookie = pg.filter(c("position") == "QB").select(
        "game_id", "team", qb_id_expected="gsis_id",
        qb_rookie=(c("years_exp") == 0).cast(pl.Float64), r_known="known_at",
    )  # fmt: skip
    out = (
        t.join(hist, on=KEYS, how="left")
        .join(team, on=KEYS, how="left")
        .join(rookie, on=["game_id", "team", "qb_id_expected"], how="left")
        .with_columns(
            qb_rookie=pl.when(c("r_known") <= c("moment")).then(c("qb_rookie")),
            qb_change=(
                c("qb_id_expected").is_not_null()
                & c("qb_last").is_not_null()
                & (c("qb_id_expected") != c("qb_last"))
            ).cast(pl.Float64),
        )
        .with_columns(
            [
                c(x).fill_null(0.0)
                for x in ("qb_proe_gap", "qb_pace_gap", "qb_starts", "qb_share", "qb_rookie")
            ]
        )  # fmt: skip
        .with_columns(
            qb_proe_other=c("qb_proe_gap") * (1 - c("qb_share")),
            qb_pace_other=c("qb_pace_gap") * (1 - c("qb_share")),
        )
    )
    return out.select(*KEYS, "qb_id_expected", *QB_COLUMNS)


def lineup_out(targets: pl.DataFrame, pg: pl.DataFrame, ps: pl.DataFrame) -> pl.DataFrame:
    """KEYS → `lineup_out`: minus the summed pass lean of skill players ruled out this week."""
    rows = pg.join(targets.select(*KEYS, "season", "moment"), on=["game_id", "team"], how="inner")
    gone = rows.filter(
        c("position").is_in(SKILL)
        & c("report_status").is_in(OUT)
        & (c("injury_known_at") <= c("moment"))
    ).select(*KEYS, "season", "moment", "gsis_id")
    # his share of the team's offensive snaps in its latest game known by the moment
    shares = pg.filter(c("offense_pct").is_not_null()).select(
        "gsis_id", "team", s_known="snaps_known_at", s_game="game_id", share="offense_pct"
    )
    share = (
        gone.join(shares, on=["gsis_id", "team"], how="inner")
        .filter(c("s_known") <= c("moment"))
        .sort("s_known")
        .group_by(*KEYS, "gsis_id")
        .agg(share=c("share").last())
    )
    pm = (
        gone.join(
            ps.select("gsis_id", p_season="season", p_known="known_at", d="onf_pm_proe",
                      w="onf_w_proe").drop_nulls("d"),
            on="gsis_id",
        )
        .filter(
            (c("p_known") <= c("moment"))
            & c("p_season").is_between(c("season") - PM_SEASONS, c("season") - 1)
        )
        .with_columns(wd=c("w") * PM_DECAY ** (c("season") - 1 - c("p_season")).cast(pl.Float64))
        .group_by(*KEYS, "gsis_id")
        .agg(pm=(c("d") * c("wd")).sum() / (c("wd").sum() + PM_PRIOR))
    )  # fmt: skip
    total = (
        share.join(pm, on=[*KEYS, "gsis_id"], how="inner")
        .group_by(KEYS)
        .agg(lineup_out=-(c("share") * c("pm")).sum())
    )
    return (
        targets.select(KEYS)
        .join(total, on=KEYS, how="left")
        .with_columns(c("lineup_out").fill_null(0.0))
    )


def player_features(
    targets: pl.DataFrame, tg: pl.DataFrame, pg: pl.DataFrame, ps: pl.DataFrame
) -> pl.DataFrame:
    return qb_features(targets, tg, pg).join(lineup_out(targets, pg, ps), on=KEYS, how="left")


def _targets(tg: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    return tg.select(*KEYS, "season").join(games.select("game_id", "moment"), on="game_id")


def _team_features(tg: pl.DataFrame, targets: pl.DataFrame, kind: str) -> pl.DataFrame:
    return P.habit_features(tg, targets) if kind == "habit" else P.volume_features(tg, targets)


def at_moment(view, games: pl.DataFrame, kind: str) -> pl.DataFrame:
    """The moment's `games` (game_id, season, week, kickoff) from a view at `view.at`. `kind`:
    "habit" or "volume"."""
    season = int(games["season"].max())
    tg = view.table("team_game", seasons=list(range(season - P.COACH_SEASONS, season + 1)))
    pg = view.table("player_game", seasons=[season - 1, season])
    ps = view.table("player_season", seasons=list(range(season - PM_SEASONS, season)))
    targets = _targets(tg, games.with_columns(moment=pl.lit(view.at).cast(MOMENT)))
    team = _team_features(tg, targets, kind)
    return team.join(player_features(targets, tg, pg, ps), on=KEYS, how="left")


def history(view, moments: pl.DataFrame, kind: str) -> pl.DataFrame:
    """Every game in `moments` (game_id, …, moment) at its own moment, in one pass."""
    tg = view.table("team_game")
    pg = view.table("player_game")
    ps = view.table("player_season")
    targets = _targets(tg, moments)
    team = _team_features(tg, targets, kind)
    return team.join(player_features(targets, tg, pg, ps), on=KEYS, how="left")
