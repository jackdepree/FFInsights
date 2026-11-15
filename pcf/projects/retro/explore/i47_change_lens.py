"""IDEAS I47 (retro 1, 2026-11-15): one "games since a change" lens on every expert's misses.

Discovery only: saved walk-forward histories, 2016-2024 (the 2025 vault is left out), outcomes
read again through each expert's own target. For each expert and each kind of change, the average
miss (result minus forecast) on the rows just after the change, minus the average miss of every
other row in the same week, with an interval from resampling whole weeks. Nothing here is a model
beating anything.

Run from pcf/:  python projects/retro/explore/i47_change_lens.py > projects/retro/explore/i47_change_lens.txt
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.validation.backtest import targets

c = pl.col
DRAWS = 4000
LAST_SEASON = 2024
MIN_ROWS = 150

TEAM = [
    ("elo", "margin"),
    ("team-efficiency", "off_next3_ridge"),
    ("team-efficiency", "def_next3_ridge"),
    ("pace", "plays_full"),
    ("pace", "dropbacks_full"),
    ("pace", "runs_full"),
    ("pace", "proe_shrunk"),
    ("pace", "pace_oe_shrunk"),
    ("schemes-v2", "shotgun_shrunk"),
    ("schemes-v2", "tempo_shrunk"),
    ("schemes-v2", "depth_shrunk"),
]
PLAYER = [("participation", "trees_week"), ("baselines", "lasso"), ("baselines", "ecr")]


def history(project: str, variant: str, gateway: Gateway) -> pl.DataFrame:
    """The latest saved run with its outcomes: keys, mean, y, miss."""
    cls = find(project, variant)
    folder = get_config().zone("outputs") / project / variant
    runs = sorted(
        (p for p in folder.iterdir() if (p / "history.parquet").exists()),
        key=lambda p: p.stat().st_mtime,
    )
    expert = cls()
    # the latest run that covers the backtest seasons (some latest runs are the 2025 vault only)
    for run in reversed(runs):
        h = pl.read_parquet(run / "history.parquet")
        if h["game_id"].min() < f"{LAST_SEASON}":
            break
    y = targets(expert, gateway).select(*expert.keys(), "y")
    return h.join(y, on=expert.keys()).with_columns(miss=c("y") - c("mean"))


def team_events(source) -> pl.DataFrame:
    """One row per team-game: its number in the team's season and the change flags."""
    s = source.part("team_game", "schedule").select(
        "game_id", "team", "season", "week", "game_type", "home"
    )
    p = source.part("team_game", "pregame").select("game_id", "team", "qb_id", "coach")
    t = source.part("team_game", "tags").select("game_id", "team", "tag_off_bye")
    x = s.join(p, on=["game_id", "team"], how="left").join(t, on=["game_id", "team"], how="left")
    x = x.sort("team", "season", "week").with_columns(
        game_no=c("week").rank("ordinal").over("team", "season"),
        prev_qb=c("qb_id").shift(1).over("team", "season"),
        prev_coach=c("coach").shift(1).over("team", "season"),
    )
    # last season's most-started QB and final coach
    reg = x.filter(c("game_type") == "REG")
    last_qb = (
        reg.drop_nulls("qb_id")
        .group_by("season", "team", "qb_id")
        .agg(n=pl.len(), last=c("week").max())
        .sort("n", "last", descending=True)
        .group_by("season", "team", maintain_order=True)
        .first()
        .select(c("season") + 1, "team", last_qb="qb_id")
    )
    last_coach = (
        reg.drop_nulls("coach")
        .sort("week")
        .group_by("season", "team")
        .last()
        .select(c("season") + 1, "team", last_coach="coach")
    )
    first = (
        x.filter(c("game_no") == 1)
        .select("season", "team", open_qb="qb_id", open_coach="coach")
        .join(last_qb, on=["season", "team"], how="left")
        .join(last_coach, on=["season", "team"], how="left")
        .select(
            "season",
            "team",
            new_qb=(c("open_qb") != c("last_qb")).fill_null(False),
            new_coach=(c("open_coach") != c("last_coach")).fill_null(False),
        )
    )
    x = x.join(first, on=["season", "team"], how="left")
    # games since the latest change of starter or coach within the season (1 = the change game)
    for who, prev in (("qb_id", "prev_qb"), ("coach", "prev_coach")):
        ch = (c(who) != c(prev)).fill_null(False)
        x = x.with_columns(_ch=ch).with_columns(
            _grp=c("_ch").cast(pl.Int32).cum_sum().over("team", "season")
        )
        x = x.with_columns(
            pl.when(c("_grp") > 0)
            .then(c("game_no").rank("ordinal").over("team", "season", "_grp"))
            .alias(f"since_{who}")
        ).drop("_ch", "_grp")
    early, late = c("game_no") <= 4, c("game_no") > 4
    return x.select(
        "game_id", "team", "season", "week", "home",
        **{
            "new head coach, games 1-4": c("new_coach") & early,
            "new head coach, games 5 on": c("new_coach") & late,
            "new starting QB at season start, games 1-4": c("new_qb") & early,
            "new starting QB at season start, games 5 on": c("new_qb") & late,
            "starting QB changed in season, games 1-4 after": c("since_qb_id").is_between(1, 4),
            "starting QB changed in season, games 5 on after": c("since_qb_id") > 4,
            "head coach changed in season, games 1-4 after": c("since_coach").is_between(1, 4),
            "first game after a bye": c("tag_off_bye").fill_null(False),
        },
    )  # fmt: skip


def player_events(source, h: pl.DataFrame, te: pl.DataFrame) -> pl.DataFrame:
    """The history's rows with player flags, and the team's flags for non-QBs."""
    roster = source.part("player_game", "roster").select("gsis_id", "game_id", "team", "position")
    tags = source.part("player_game", "tags").select(
        "gsis_id", "game_id", "tag_rookie", "tag_new_team", "tag_first_game_back"
    )
    x = h.join(roster, on=["gsis_id", "game_id"], how="left").join(
        tags, on=["gsis_id", "game_id"], how="left"
    )
    x = x.join(te.select("game_id", "team", "season", "week", "game_no"), on=["game_id", "team"])
    x = x.sort("gsis_id", "season", "week").with_columns(
        own_no=c("week").rank("ordinal").over("gsis_id", "season", "team"),
        back=c("tag_first_game_back").fill_null(False),
    )
    x = x.with_columns(_g=c("back").cast(pl.Int32).cum_sum().over("gsis_id", "season")).with_columns(
        since_back=pl.when(c("_g") > 0).then(c("week").rank("ordinal").over("gsis_id", "season", "_g"))
    )
    new, rook = c("tag_new_team").fill_null(False), c("tag_rookie").fill_null(False)
    flags = {
        "player new to the team, his games 1-4": new & ~rook & (c("own_no") <= 4),
        "player new to the team, his games 5 on": new & ~rook & (c("own_no") > 4),
        "rookie, his games 1-4": rook & (c("own_no") <= 4),
        "rookie, his games 5 on": rook & (c("own_no") > 4),
        "first game back from injury": c("since_back") == 1,
        "games 2-4 after coming back": c("since_back").is_between(2, 4),
    }
    x = x.with_columns(**flags)
    team_cols = [k for k in te.columns if k not in ("game_id", "team", "season", "week", "home", "game_no")]
    x = x.join(te.select("game_id", "team", *team_cols), on=["game_id", "team"], how="left")
    not_qb = c("position") != "QB"
    x = x.with_columns(**{k: c(k) & not_qb for k in team_cols})
    return x, [*flags, *[f"{k}" for k in team_cols]]


def gap(d: pl.DataFrame, flag: str, rng: np.random.Generator) -> dict | None:
    """Average miss on flagged rows minus the same weeks' other rows, weeks resampled."""
    d = d.filter(c(flag).is_not_null())
    n_flag = int(d[flag].sum())
    if n_flag < MIN_ROWS:
        return None
    w = (
        d.group_by("season", "week")
        .agg(
            sg=c("miss").filter(c(flag)).sum(),
            ng=c(flag).sum(),
            mr=c("miss").filter(~c(flag)).mean(),
        )
        .filter((c("ng") > 0) & c("mr").is_not_null())
    )
    # the same gap season by season: how many seasons share the overall sign
    per = (
        w.with_columns(b=c("ng") * c("mr"))
        .group_by("season")
        .agg(g=(c("sg").sum() - c("b").sum()) / c("ng").sum())
    )
    sg, ng = w["sg"].to_numpy(), w["ng"].to_numpy().astype(float)
    base = ng * w["mr"].to_numpy()
    est = (sg.sum() - base.sum()) / ng.sum()
    draws = rng.multinomial(len(sg), np.full(len(sg), 1 / len(sg)), size=DRAWS)
    boot = (draws @ sg - draws @ base) / np.maximum(draws @ ng, 1)
    q = np.quantile(boot, [0.0005, 0.005, 0.05, 0.95, 0.995, 0.9995])
    return {
        "rows": n_flag, "gap": est,
        "seasons_same_sign": f"{int((np.sign(per['g'].to_numpy()) == np.sign(est)).sum())} of {per.height}", "lo90": q[2], "hi90": q[3], "lo99": q[1], "hi99": q[4],
        "clear99": bool(q[1] > 0 or q[4] < 0), "clear999": bool(q[0] > 0 or q[5] < 0),
    }  # fmt: skip


def main() -> None:
    gateway = Gateway()
    src = gateway.source
    te = team_events(src)
    te_no = te.join(
        src.part("team_game", "schedule")
        .select("game_id", "team", "season", "week")
        .with_columns(game_no=c("week").rank("ordinal").over("team", "season"))
        .select("game_id", "team", "game_no"),
        on=["game_id", "team"],
    )
    rng = np.random.default_rng(get_config().seed)
    rows = []
    for project, variant in TEAM:
        h = history(project, variant, gateway)
        if "team" not in h.columns:  # a game-level forecast of the home margin: one row per side
            sides = te.select("game_id", "team", "home")
            h = h.join(sides, on="game_id").with_columns(
                miss=pl.when(c("home")).then(c("miss")).otherwise(-c("miss"))
            )
        d = h.join(te.drop("home"), on=["game_id", "team"]).filter(c("season") <= LAST_SEASON)
        mae = float(d["miss"].abs().mean())
        flags = [k for k in te.columns if k not in ("game_id", "team", "season", "week", "home")]
        for f in flags:
            r = gap(d, f, rng)
            if r:
                rows.append({"expert": f"{project}/{variant}", "change": f, "typical_miss": mae, **r})
    for project, variant in PLAYER:
        h = history(project, variant, gateway)
        d, flags = player_events(src, h, te_no)
        d = d.filter(c("season") <= LAST_SEASON)
        mae = float(d["miss"].abs().mean())
        for f in flags:
            r = gap(d, f, rng)
            if r:
                rows.append({"expert": f"{project}/{variant}", "change": f, "typical_miss": mae, **r})
    out = pl.DataFrame(rows).with_columns(share=c("gap") / c("typical_miss"))
    pl.Config.set_tbl_rows(400)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(240)
    pl.Config.set_fmt_str_lengths(60)
    pl.Config.set_float_precision(4)
    print(f"tests: {out.height}; expected to clear 99% by chance: {out.height * 0.01:.1f}; "
          f"cleared 99%: {int(out['clear99'].sum())}; cleared 99.9%: {int(out['clear999'].sum())}")
    print("gap = average miss (result minus forecast) after the change, minus the same weeks' other rows;")
    print("share = gap / the expert's typical (mean absolute) miss. Seasons 2016-2024.\n")
    print("== cleared the 99% bar")
    print(out.filter(c("clear99")).sort(c("share").abs(), descending=True))
    print("\n== everything")
    print(out.sort("expert", "change"))


if __name__ == "__main__":
    main()
