"""The snap-leverage features at a moment, and the targets (brief: projects/snap-leverage/BRIEF.md,
"What the exploration changes in the brief"; decision 0033).

**Rows:** every rostered player in the moment's regular-season games, QB through DB (kickers,
punters and long snappers left out), keyed gsis_id, game_id. `position` is his group, which also
decides his side.

**Features**, for every rung at once (so a variant's baselines score identical rows), from his
regular-season games this season known by the moment (a rostered game he didn't play counts 0):
- plain (`PLAIN`): his official snap share (snap counts, for his side) in his last game, his last
  3, the season to date, last season's; games so far; his group; first-year player;
- leverage (`LEV`): leverage share, from participation-live's morning-after map (each snap by its
  on-field chance) × `play.leverage`: last game, last 3, season to date, last season's;
- role and trust (`ROLE`): the passing-down role gap and trust over expected, last 3 and season to
  date, over the games he played.
- **Published** (`PUBLISHED`): the leverage, role and trust columns, for higher layers.

**Targets** (`targets`): the mean over a window of the team's games from this one (the next 3,
which needs 3 left, or the rest of the regular season) of his official snap share (`snap`) or his
leverage share from true participation (`lev`, known after the season: rule m). A week he has no
row, on any team, counts 0. Only complete windows.
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from pcf.experts.snap_leverage import usage as U

c = pl.col
MAP = "participation-live"
INPUTS = {
    MAP: 1,
    "play": ("leverage", "pace"),
    "player_game": ("roster", "snaps"),
    "game": ("schedule",),
    "player_play": ("on_field",),
}
KEYS = ["gsis_id", "game_id"]
FIRST_SEASON = 2019  # the map's walk-forward history starts here
HORIZONS = {"next3": 3, "rest": None}
PLAIN = ["snap_last", "snap_l3", "snap_std", "snap_prev", "n_games", "group", "first_year"]
LEV = ["lev_last", "lev_l3", "lev_std", "lev_prev"]
ROLE = ["role_l3", "role_std", "trust_l3", "trust_std"]
PUBLISHED = (*LEV, *ROLE)
GROUP_CODE = {g: float(i) for i, g in enumerate(U.GROUPS)}


def _schedule(view, seasons: Sequence[int]) -> pl.DataFrame:
    """Regular-season games: game_id, season, week, home_team, away_team."""
    return (
        view.table("game", seasons=list(seasons))
        .filter(c("game_type") == "REG")
        .select("game_id", c("season").cast(pl.Int32), c("week").cast(pl.Int32), "home_team",
                "away_team")
    )  # fmt: skip


def _rostered(view, seasons: Sequence[int], reg: pl.DataFrame) -> pl.DataFrame:
    """Rostered regular-season player-games, QB through DB: keys, season, week, team, position,
    side, first_year, `share` (his official snap share for his side, 0 when he has no snap-count
    row) and `snaps_known` (when the game's snap counts were known; empty if not yet)."""
    pg = view.table("player_game", seasons=list(seasons))
    side = c("position").replace_strict(U.SIDE, default=None)
    return (
        pg.filter(c("position").is_in(U.GROUPS) & c("game_id").is_in(reg["game_id"].implode()))
        .unique(KEYS, keep="first", maintain_order=True)
        .with_columns(snaps_known=c("snaps_known_at").max().over("game_id"))
        .select(
            *KEYS,
            c("season").cast(pl.Int32),
            c("week").cast(pl.Int32),
            "team",
            "position",
            side=side,
            first_year=(c("season") == c("rookie_year")).fill_null(False).cast(pl.Float64),
            share=pl.when(side == "offense")
            .then(c("offense_pct"))
            .otherwise(c("defense_pct"))
            .fill_null(0.0),
            snaps_known="snaps_known",
        )  # fmt: skip
    )


def _with_usage(rows: pl.DataFrame, used: pl.DataFrame, known: pl.Series) -> pl.DataFrame:
    """Rostered player-games with their usage measures: 0 shares in a known game he wasn't on the
    field for, empty role and trust; everything empty in a game not yet known."""
    out = rows.join(used.drop("team"), on=[*KEYS, "side"], how="left")
    in_known = c("game_id").is_in(known.implode())
    return out.with_columns(
        [pl.when(in_known).then(c(m).fill_null(0.0)).alias(m) for m in ("lev_share", "hs_share")]
    )


def _map_usage(view, seasons: Sequence[int]) -> tuple[pl.DataFrame, pl.Series]:
    """The map's usage per player-game (as known at the view's moment) and the games it covers."""
    mp = view.output(MAP).filter(c("season").is_in(list(seasons)))
    if mp.is_empty():
        empty = pl.DataFrame(schema={"game_id": pl.String, "gsis_id": pl.String,
                                     "side": pl.String, "team": pl.String,
                                     **dict.fromkeys(U.MEASURES, pl.Float64)})  # fmt: skip
        return empty, pl.Series("game_id", [], pl.String)
    on = mp.select("game_id", "play_id", "gsis_id", "side", "team", p="mean")
    snaps = U.plays(view.table("play", seasons=list(seasons)))
    return U.usage(on, snaps), on["game_id"].unique()


def _player_features(hist: pl.DataFrame, season: int) -> pl.DataFrame:
    """Per player: the season-to-date features from his rostered games (`hist`, with usage)."""
    this = hist.filter(c("season") == season).sort("gsis_id", "week")
    prev = hist.filter(c("season") == season - 1)
    now = this.group_by("gsis_id").agg(
        snap_last=c("share").last(),
        snap_l3=c("share").tail(3).mean(),
        snap_std=c("share").mean(),
        n_games=pl.len().cast(pl.Float64),
        lev_last=c("lev_share").last(),
        lev_l3=c("lev_share").tail(3).mean(),
        lev_std=c("lev_share").mean(),
        role_l3=c("role_gap").drop_nulls().tail(3).mean(),
        role_std=c("role_gap").mean(),
        trust_l3=c("trust_oe").drop_nulls().tail(3).mean(),
        trust_std=c("trust_oe").mean(),
    )
    before = prev.group_by("gsis_id").agg(
        snap_prev=c("share").mean(), lev_prev=c("lev_share").mean()
    )
    return now.join(before, on="gsis_id", how="full", coalesce=True)


def at_moment(view, games: pl.DataFrame) -> pl.DataFrame:
    """The rows predicted at `view.at` for the moment's `games` (game_id, season, week, kickoff)."""
    season = int(games["season"].max())
    seasons = [season - 1, season]
    reg = _schedule(view, seasons)
    rostered = _rostered(view, seasons, reg)
    rows = rostered.filter(c("game_id").is_in(games["game_id"].implode()))
    if rows.is_empty():
        return pl.DataFrame(schema=dict.fromkeys(KEYS, pl.String))
    hist = rostered.filter(c("snaps_known").is_not_null() & ~c("game_id").is_in(
        games["game_id"].implode()))  # fmt: skip
    used, known = _map_usage(view, [s for s in seasons if s >= FIRST_SEASON])
    hist = _with_usage(hist, used, known)
    feats = _player_features(hist, season)
    return (
        rows.select(*KEYS, "season", "position", "first_year")
        .join(feats, on="gsis_id", how="left")
        .with_columns(
            c("n_games").fill_null(0.0),
            group=c("position").replace_strict(GROUP_CODE, return_dtype=pl.Float64),
        )
        .select(*KEYS, "season", "position", *PLAIN, *LEV, *ROLE)
        .sort(KEYS)
    )


def _windows(rostered: pl.DataFrame, reg: pl.DataFrame, horizon: int | None) -> pl.DataFrame:
    """Each rostered row against its team's games from this one: keys, season, g_week, g_game."""
    teams = pl.concat(
        reg.select("season", g_week="week", g_game="game_id", team=c(s))
        for s in ("home_team", "away_team")
    )
    w = (
        rostered.select(*KEYS, "season", "team", "week")
        .join(teams, on=["season", "team"])
        .filter(c("g_week") >= c("week"))
        .with_columns(n=c("g_week").rank("ordinal").over(KEYS))
        .with_columns(left=c("n").max().over(KEYS))
    )
    if horizon is not None:
        w = w.filter((c("n") <= horizon) & (c("left") >= horizon))
    return w.select(*KEYS, "season", "g_week", "g_game")


def window_mean(
    rostered: pl.DataFrame,
    reg: pl.DataFrame,
    values: pl.DataFrame,
    games_known: pl.DataFrame,
    horizon: int | None,
) -> pl.DataFrame:
    """keys, y (the mean of his `value` over the window's games, 0 in a week he has no value) and
    known_at (when the window's last game was known). `values`: gsis_id, season, week, value;
    `games_known`: game_id, known_at. Complete windows only."""
    w = _windows(rostered, reg, horizon)
    v = values.unique(["gsis_id", "season", "week"]).rename({"week": "g_week"})
    w = w.join(v, on=["gsis_id", "season", "g_week"], how="left").join(
        games_known.rename({"game_id": "g_game"}), on="g_game", how="left"
    )
    return (
        w.group_by(KEYS)
        .agg(
            y=c("value").fill_null(0.0).mean(),
            missing=c("known_at").null_count(),
            known_at=c("known_at").max(),
        )
        .filter(c("missing") == 0)
        .select(*KEYS, "y", "known_at")
        .sort(KEYS)
    )


def targets(view, measure: str, horizon: str) -> pl.DataFrame:
    """`measure` `snap` (official snap share) or `lev` (true leverage share), over the horizon."""
    out = []
    seasons = sorted(set(view.table("game")["season"].to_list()))
    for s in [s for s in seasons if s >= FIRST_SEASON]:
        reg = _schedule(view, [s])
        rostered = _rostered(view, [s], reg)
        if rostered.is_empty():
            continue
        if measure == "snap":
            known = rostered.filter(c("snaps_known").is_not_null())
            values = known.select("gsis_id", "season", "week", value="share")
            games_known = known.group_by("game_id").agg(known_at=c("snaps_known").max())
        else:
            of = view.table("player_play", seasons=[s])
            if of.is_empty():
                continue
            on = of.select("game_id", "play_id", "gsis_id", "side", "team", p=pl.lit(1.0))
            used = U.usage(on, U.plays(view.table("play", seasons=[s])))
            games_known = of.group_by("game_id").agg(known_at=c("known_at").max())
            got = _with_usage(rostered, used, games_known["game_id"])
            values = got.filter(c("lev_share").is_not_null()).select(
                "gsis_id", "season", "week", value="lev_share"
            )
        out.append(window_mean(rostered, reg, values, games_known, HORIZONS[horizon]))
    return pl.concat(out) if out else pl.DataFrame(schema={**dict.fromkeys(KEYS, pl.String)})
