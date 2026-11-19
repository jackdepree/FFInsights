"""Each player's and team's context per game: the average expected outcome of the plays they were
on the field for, minus the league's (BRIEF, "Terms"; the CEO's H66).

- **A play's context** for success: the walk-forward chance that the play succeeds (a run's or a
  dropback's) from the shipped model, minus the league's success rate on the training seasons
  (point in time). The same from the situation-only model gives the part down and distance
  explain; the difference is what the calls add.
- **Who was on the field:** participation-late's in-season map (its walk-forward history, known
  14 days after the game, like FTN), each player counted by his chance of being on the play.
- **Teams:** the offense's and the defense's plays, counted once each.
"""

from __future__ import annotations

import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway

c = pl.col
MAP = "participation-late"
MAP_VERSION = 1
MAP_INPUTS = {MAP: MAP_VERSION, "player_game": ("roster",)}
MEASURES = ["ctx_success", "ctx_success_sit", "ctx_calls"]
MIN_PLAYS = 200  # a player-season counts for the spread and the consistency from 200 plays


def play_context(scored: dict[str, pl.DataFrame], shipped: dict[str, str],
                 league: dict[int, float]) -> pl.DataFrame:  # fmt: skip
    """Per play: the expected success from the shipped rung and from the situation-only rung,
    each minus the league's rate for that season (`league`), and the actual result. `scored`
    holds the backtest's frames for run_success_prob and dropback_success_prob; `shipped` their
    shipped rung and their situation-only rung (keys `<name>` and `<name>:situation`)."""
    out = []
    for name in ("run_success_prob", "dropback_success_prob"):
        f = scored[name]
        live, sit = shipped[name], shipped[f"{name}:situation"]
        out.append(
            f.select(
                "game_id",
                "play_id",
                "season",
                "week",
                "y",
                exp=c(f"{live}:mean"),
                exp_sit=c(f"{sit}:mean"),
                kind=pl.lit("run" if name.startswith("run") else "dropback"),
            )  # fmt: skip
        )
    d = pl.concat(out)
    lg = pl.DataFrame({"season": list(league), "league": list(league.values())},
                      schema={"season": pl.Int32, "league": pl.Float64})  # fmt: skip
    d = d.join(lg, on="season", how="left")
    if d["league"].null_count():
        raise ValueError("a season has no league rate")
    return d.with_columns(
        ctx_success=c("exp") - c("league"),
        ctx_success_sit=c("exp_sit") - c("league"),
        ctx_calls=c("exp") - c("exp_sit"),
        actual=c("y") - c("league"),
    )


def league_rates(data: pl.DataFrame, seasons: list[int]) -> dict[int, float]:
    """The success rate of runs and dropbacks on every season before each one (unweighted)."""
    rows = data.filter(c("is_run") | c("is_dropback"), c("success_y").is_not_null())
    return {s: float(rows.filter(c("season") < s)["success_y"].mean()) for s in seasons}


def on_field(seasons: list[int], gateway: Gateway | None = None) -> pl.DataFrame:
    """participation-late's chances per player and play, with the player's roster position."""
    view = (gateway or Gateway()).view(END_OF_TIME, "in_season", MAP_INPUTS)
    m = view.output(MAP).filter(c("season").is_in(seasons))
    m = m.select("game_id", "play_id", "gsis_id", "side", "team", "season", "week",
                 chance=c("mean"))  # fmt: skip
    pos = (
        view.table("player_game", seasons=seasons)
        .select("gsis_id", "game_id", "position")
        .unique(["gsis_id", "game_id"])
    )
    return m.join(pos, on=["gsis_id", "game_id"], how="left")


def player_game(plays: pl.DataFrame, field: pl.DataFrame) -> pl.DataFrame:
    """Per player-game and side: expected plays (the sum of his chances on the scored plays) and
    his chance-weighted average of each measure and of the actual result."""
    j = field.join(plays.select("game_id", "play_id", *MEASURES, "actual"),
                   on=["game_id", "play_id"], how="inner")  # fmt: skip
    w = c("chance")
    return (
        j.group_by("gsis_id", "game_id", "season", "week", "side", "team")
        .agg(
            position=c("position").drop_nulls().first(),
            plays=w.sum(),
            **{m: (c(m) * w).sum() / w.sum() for m in [*MEASURES, "actual"]},
        )
        .filter(c("plays") > 0)
        .sort("season", "week", "game_id", "side", "gsis_id")
    )


def team_game(plays: pl.DataFrame, table: pl.DataFrame) -> pl.DataFrame:
    """Per team-game, the offense's average context (side offense) and the defense's (side
    defense, the same plays from the other side)."""
    j = plays.join(table.select("game_id", "play_id", "posteam", "defteam"),
                   on=["game_id", "play_id"], how="left")  # fmt: skip
    agg = dict(plays=pl.len(), **{m: c(m).mean() for m in [*MEASURES, "actual"]})
    off = j.group_by("game_id", "season", "week", team=c("posteam")).agg(**agg)
    dfn = j.group_by("game_id", "season", "week", team=c("defteam")).agg(**agg)
    return pl.concat(
        [off.with_columns(side=pl.lit("offense")), dfn.with_columns(side=pl.lit("defense"))]
    ).sort("season", "week", "game_id", "side", "team")


def player_seasons(pg: pl.DataFrame) -> pl.DataFrame:
    """Per player-season and side, weighted by expected plays; those with `MIN_PLAYS` or more."""
    w = c("plays")
    return (
        pg.group_by("gsis_id", "season", "side")
        .agg(
            position=c("position").drop_nulls().mode().first(),
            plays=w.sum(),
            **{m: (c(m) * w).sum() / w.sum() for m in [*MEASURES, "actual"]},
        )
        .filter(c("plays") >= MIN_PLAYS)
    )


# Roster positions grouped the way personnel is counted (the CEO's "3 wide receivers").
GROUPS = {
    "RB": "n_rb_map", "FB": "n_rb_map", "TE": "n_te_map", "WR": "n_wr_map",
    "DL": "n_dl_map", "LB": "n_lb_map", "DB": "n_db_map",
}  # fmt: skip
PERSONNEL = sorted(set(GROUPS.values()))


def personnel(field: pl.DataFrame) -> pl.DataFrame:
    """Per play, the expected count of each position group on the field (the sum of the map's
    chances): in-season personnel, from positions and counts only (no names)."""
    g = field.with_columns(group=c("position").replace_strict(GROUPS, default=None)).filter(
        c("group").is_not_null()
    )
    wide = (
        g.group_by("game_id", "play_id", "group")
        .agg(c("chance").sum())
        .pivot(on="group", index=["game_id", "play_id"], values="chance")
    )
    for col in PERSONNEL:
        if col not in wide.columns:
            wide = wide.with_columns(pl.lit(0.0).alias(col))
    return wide.select("game_id", "play_id", *[c(x).fill_null(0.0) for x in PERSONNEL])


def build(tag: str = "backtest") -> dict:
    """Player-game and team-game context from a backtest's saved frames (the success models'
    walk-forward chances), saved beside its history (outputs/context-live/<run_id>/), with the
    spread and consistency the brief asks for (H66). Returns the summary and writes
    projects/context-live/build/context_<tag>.txt."""
    import json

    import numpy as np

    from pcf.config import get_config
    from pcf.experts.context_live import run
    from pcf.validation.consistency import consistency

    work = run.cache_dir() / tag
    res = json.loads((work / "results.json").read_text())
    run_id = json.loads((work / "run.json").read_text())["run_id"]
    names = ("run_success_prob", "dropback_success_prob")
    scored = {n: pl.read_parquet(work / f"{n}.parquet") for n in names}
    shipped = {n: res[n]["choice"]["shipped"] for n in names}
    shipped |= {f"{n}:situation": res[n]["choice"]["situation"] for n in names}
    seasons = sorted({s for n in names for s in res[n]["seasons"]})
    data = run.load(range(min(seasons) - 1, max(seasons) + 1))
    plays_ctx = play_context(scored, shipped, league_rates(data, seasons))
    field = on_field(seasons)
    pg = player_game(plays_ctx, field)
    tg = team_game(plays_ctx, data)
    out_dir = get_config().zone("outputs") / run.ID / run_id
    pg.write_parquet(out_dir / "player_game.parquet")
    tg.write_parquet(out_dir / "team_game.parquet")
    reg = c("week") <= 18
    lines = [f"context-live context ({tag}, run {run_id}): points of success rate (x100)", ""]
    summary: dict = {}
    for side in ("offense", "defense"):
        ps = player_seasons(pg.filter(c("side") == side, reg))
        x, a = ps["ctx_success"].to_numpy(), ps["actual"].to_numpy()
        sit = ps["ctx_success_sit"].to_numpy()
        cons = consistency(
            pg.filter(c("side") == side, reg, c("gsis_id").is_in(ps["gsis_id"].implode())),
            MEASURES, unit="gsis_id",
        )  # fmt: skip
        s = {
            "player_seasons": ps.height,
            "spread": float(100 * x.std()),
            "p5": float(100 * np.quantile(x, 0.05)), "p95": float(100 * np.quantile(x, 0.95)),
            "lowest": float(100 * x.min()), "highest": float(100 * x.max()),
            "share_of_actual_variance": float(x.var() / a.var()),
            "share_from_situation": float(np.corrcoef(x, sit)[0, 1] ** 2),
            "spread_calls": float(100 * ps["ctx_calls"].std()),
        }  # fmt: skip
        summary[side] = s | {"consistency": cons.to_dicts()}
        lines.append(f"== {side}: {ps.height} player-seasons with {MIN_PLAYS}+ expected plays")
        lines.append("  " + ", ".join(f"{k} {v:.3f}" for k, v in s.items()))
        for row in cons.iter_rows(named=True):
            lines.append(f"  consistency {row['measure']}: week r {row['week_r']:.2f} "
                         f"({row['week_lo']:.2f} to {row['week_hi']:.2f}), season r "
                         f"{row['season_r']:.2f} ({row['season_lo']:.2f} to "
                         f"{row['season_hi']:.2f}), {row['verdict']}")  # fmt: skip
        by_pos = (
            ps.group_by("position")
            .agg(players=pl.len(), mean=(100 * c("ctx_success")).mean(),
                 spread=(100 * c("ctx_success")).std(), lowest=(100 * c("ctx_success")).min(),
                 highest=(100 * c("ctx_success")).max())
            .filter(c("players") >= 15)
            .sort("mean")
        )  # fmt: skip
        for row in by_pos.iter_rows(named=True):
            lines.append(f"    {row['position']:<4} {row['players']:>4} players: mean "
                         f"{row['mean']:+.2f}, spread {row['spread']:.2f}, range "
                         f"{row['lowest']:+.1f} to {row['highest']:+.1f}")  # fmt: skip
        lines.append("")
    tcons_off = consistency(
        tg.filter(reg, c("side") == "offense"), MEASURES + ["actual"], unit="team"
    )
    tcons_def = consistency(
        tg.filter(reg, c("side") == "defense"), MEASURES + ["actual"], unit="team"
    )
    for label, t in (
        ("offenses", tcons_off),
        ("defenses", tcons_def),
    ):
        for row in t.iter_rows(named=True):
            lines.append(f"  {label} {row['measure']}: week r {row['week_r']:.2f} "
                         f"({row['week_lo']:.2f} to {row['week_hi']:.2f}), season r "
                         f"{row['season_r']:.2f}, typical size {100 * row['mean_abs']:.2f}, "
                         f"{row['verdict']}")  # fmt: skip
    summary["teams"] = {"offense": tcons_off.to_dicts(), "defense": tcons_def.to_dicts()}
    path = run.report_dir() / f"context_{tag}.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    (work / "context.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary
