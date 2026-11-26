"""`vacated-offseason` (decision 0050): each stayer's next-season snap, target and carry share after
a top player has left, gated on intake (I125).

At an event (the backtest: the week-1 roster; live: the roster after free agency or the draft):

- **Departures:** last season's top players (season s, by snaps) who aren't on the team's 53 at
  the event (a reserve list at week 1 counts as gone; decision 0050, call 11).
- **Stayers:** players of that group who played for the team in s and are on its 53 at the event.
- **No change** (the bar): his share in season s's games where every departed group-mate played.
- **The plus-minus:** no change plus, over the departed players, (pooled rate + pair part) x the
  departed player's season-s share. The rates are vacated-live's, fit on completed seasons
  through s; the pair part is season s's own (the departure comes after the season).
- **The intake flag** (the CEO, 2026-11-24: "a preseason flag is good enough"): a newcomer on the
  53 at the group who was a top player at his group elsewhere in s, or a rookie picked 1-64.
- **The gate:** the plus-minus where the group was left empty, and for the lines; no change where
  a top player came in at a skill group.

The target: his share over his games for the team in s + 1 (null if he didn't play).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.vacated_opportunity import common as K
from pcf.experts.vacated_opportunity import data as D
from pcf.experts.vacated_opportunity import rates as R

c = pl.col
PAIRS = tuple(range(2015, K.LAST))  # s -> s + 1: 2016 a warm-up for the ranges, 2017-2024 scored
W = {"snap": "share", "target": "tgt_share", "carry": "car_share"}
TOPS = {"snap": K.GROUPS, "target": K.SKILL, "carry": K.SKILL}


def week1(refresh: bool = False) -> pl.DataFrame:
    """Each team's week-1 roster and reserve lists (`roster_week`, 2016 on), with the group."""
    path = K.cache_dir() / "week1.parquet"
    if path.exists() and not refresh:
        return pl.read_parquet(path)
    seasons = list(range(2016, K.LAST + 1))
    v = Gateway(TableSource(seasons=seasons)).view(
        END_OF_TIME, "retrospective", {"roster_week": ("status",)}
    )
    rw = v.table("roster_week", seasons=seasons)
    first = rw.group_by("team", "season").agg(wk=c("week").min())
    rw = rw.join(first, on=["team", "season"]).filter(c("week") == c("wk"))
    rw = rw.with_columns(group=c("position").replace_strict(K.GROUP, default=None))
    out = rw.select(
        "gsis_id", "team", "season", "group", "status", on53=~c("reserve").fill_null(False)
    ).unique(["gsis_id", "team", "season"])
    out.write_parquet(path)
    return out


def table(
    pg: pl.DataFrame, tg: pl.DataFrame, roster: pl.DataFrame, s: int, measure: str
) -> pl.DataFrame:
    """The stayers of season s's teams at the event `roster` (gsis_id, team, group, on53) for
    s + 1: no change, the departed players, the intake flag, and the target (his s + 1 share)."""
    ycol = W[measure]
    groups = TOPS[measure]
    pool = K.MEASURES[measure][1]
    ps = R.season_tops(pg.filter(c("season").is_in([s, s + 1])))
    last = ps.filter(c("season") == s)
    on = roster.filter(c("on53")).select("gsis_id", "team").unique()
    dep = last.filter(c("top") & c("group").is_in(list(groups))).join(
        on, on=["gsis_id", "team"], how="anti"
    )
    stay = last.filter(c("group").is_in(list(groups))).join(on, on=["gsis_id", "team"], how="semi")
    # intake: newcomers on the 53 at the group, a top player elsewhere in s or a pick 1-64 rookie
    new = roster.filter(c("on53") & c("group").is_not_null()).join(
        last.select("gsis_id", "team"), on=["gsis_id", "team"], how="anti"
    )
    top_else = last.filter(c("top")).select("gsis_id", was_group="group").unique("gsis_id")
    draft = pg.filter(c("season") == s + 1).select("gsis_id", dn=c("draft_number").cast(pl.Int64, strict=False),
                                                   ey="entry_year").unique("gsis_id")  # fmt: skip
    new = new.join(top_else, on="gsis_id", how="left").join(draft, on="gsis_id", how="left")
    new = new.with_columns(intake=(c("was_group") == c("group")).fill_null(False)
                           | ((c("ey") == s + 1) & (c("dn") <= 64)).fill_null(False))  # fmt: skip
    intake = new.filter(c("intake")).group_by("team", "group").agg(n_intake=pl.len())
    pk = (lambda e: e) if pool == "group" else (lambda e: pl.lit("skill"))
    dep_k = dep.with_columns(pkey=pk(c("group"))).select(
        "team", "pkey", j="gsis_id", group_j="group", wj=c(ycol)
    )
    stay = stay.with_columns(pkey=pk(c("group")))
    st = stay.join(dep_k.select("team", "pkey").unique(), on=["team", "pkey"], how="semi")
    # no change: his s share in games where every departed pool-mate played
    g = pg.filter(c("season") == s).select("gsis_id", "team", "game_id", v=c(ycol))
    x = g.join(st.select("gsis_id", "team", "pkey"), on=["gsis_id", "team"]).join(dep_k.select("team", "pkey", "j"),
                                                                                     on=["team", "pkey"])  # fmt: skip
    x = x.join(
        g.select(j="gsis_id", game_id="game_id", jp=pl.lit(True)), on=["j", "game_id"], how="left"
    )
    w = x.group_by("gsis_id", "team", "game_id").agg(
        all_=c("jp").is_not_null().all(), v=c("v").first()
    )
    w = w.filter(c("all_")).group_by("gsis_id", "team").agg(with_=c("v").mean(), n_with=pl.len())
    st = st.join(w, on=["gsis_id", "team"], how="left").with_columns(
        with_=c("with_").fill_null(c(ycol))
    )
    nxt = ps.filter(c("season") == s + 1).select("gsis_id", "team", y=c(ycol), games_next="games")
    st = st.join(nxt, on=["gsis_id", "team"], how="left")
    st = st.join(intake, on=["team", "group"], how="left").with_columns(
        intake=c("n_intake").fill_null(0) > 0, season=pl.lit(s, pl.Int32)
    )
    st = st.select("gsis_id", "team", "season", "group", "pkey", "rank", "top", "games", "with_", "y",
                   "games_next", "intake", s_share=c(ycol))  # fmt: skip
    return st, dep_k


def forecast(st: pl.DataFrame, dep: pl.DataFrame, fit: R.Fit, groups: Sequence[str],
             pair: bool = True) -> pl.DataFrame:  # fmt: skip
    """No change plus the departed players' shares times (pooled + pair)."""
    pooled = fit.pooled(groups)
    x = st.select("gsis_id", "team", "season", "group", "pkey").join(dep, on=["team", "pkey"])
    x = x.with_columns(
        r=(c("group") + ">" + c("group_j")).replace_strict(pooled, default=0.0, return_dtype=pl.Float64),
        pp=pl.when(c("group") == c("group_j")).then(
            (c("gsis_id") + ">" + c("j") + ">" + c("season").cast(pl.Utf8))
            .replace_strict(fit.coef, default=0.0, return_dtype=pl.Float64)).otherwise(0.0),
    )  # fmt: skip
    inc = x.group_by("gsis_id", "team").agg(
        d_pool=(c("r") * c("wj")).sum(),
        d_pair=(c("pp") * c("wj")).sum(),
        V=c("wj").filter(c("group") == c("group_j")).sum(),
    )
    st = st.join(inc, on=["gsis_id", "team"], how="left").with_columns(
        [c(x).fill_null(0.0) for x in ("d_pool", "d_pair", "V")]
    )
    lines = c("group").is_in(["OL", "DL"])
    st = st.with_columns(
        f0=c("with_").clip(0, 1),
        f_pool=(c("with_") + c("d_pool")).clip(0, 1),
        f_pm=(c("with_") + c("d_pool") + (c("d_pair") if pair else pl.lit(0.0))).clip(0, 1),
    )
    st = st.with_columns(f_gate=pl.when(lines | ~c("intake")).then(c("f_pm")).otherwise(c("f0")))
    # the usual way (reference only): the departed share split in proportion to the stayers' with shares
    st = st.with_columns(sumw=c("with_").sum().over("team", "season", "pkey"))
    vv = dep.group_by("team", "pkey").agg(Vall=c("wj").sum())
    st = st.join(vv, on=["team", "pkey"], how="left").with_columns(
        f_prop=(c("with_") + c("Vall").fill_null(0) * c("with_") / c("sumw").clip(1e-9)).clip(0, 1)
    )
    return st.drop("sumw", "Vall")


def shuffled_departures(dep_by: dict[int, pl.DataFrame], seed: int) -> dict[int, pl.DataFrame]:
    """The null: each season's departure lists moved to another team (the same season and pool)."""
    rng = np.random.default_rng(seed)
    out = {}
    for s, d in dep_by.items():
        teams = sorted(d["team"].unique().to_list())
        perm = dict(zip(teams, [teams[i] for i in rng.permutation(len(teams))], strict=True))
        out[s] = d.with_columns(team=c("team").replace_strict(perm))
    return out


def build(measure: str, fits: dict[int, R.Fit], seasons: Sequence[int] = PAIRS,
          dep_override: dict | None = None, pair: bool = True) -> tuple[pl.DataFrame, dict]:  # fmt: skip
    pg, tg = D.player_games(), D.team_games()
    w1 = week1()
    parts, deps = [], {}
    for s in seasons:
        st, dep = table(pg, tg, w1.filter(c("season") == s + 1), s, measure)
        deps[s] = dep
        d = dep if dep_override is None else dep_override[s]
        parts.append(forecast(st, d, fits[s], TOPS[measure], pair))
    return pl.concat(parts, how="diagonal_relaxed"), deps
