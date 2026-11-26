"""`vacated-live`'s walk-forward (decision 0050): each week of a season, with what the Saturday
run knows.

For every team-game g in week w of season s:

- **The top players** are his team's top k in each group by snaps in games before g, with 2+ of
  them played (the exploration's rule).
- **His expected absence** is (1 - his chance of playing) x his share to date (decision 0046,
  call 10). The chance (`p_play`): 0 if he isn't on the team's roster that week (`roster_week`,
  2016 on); else availability's walk-forward chance (`next_logit`, 2017 on); else the injury
  report's status at fixed rates measured on 2013-2016's top players (the brief's fallback).
  The hindsight version (1 if he missed it) is walked beside it as the ceiling.
- **No change** (the bar): a teammate's mean share over his earlier games in which every current
  top group-mate played (all his earlier games if there are none).
- **The pooled part:** the transfer rates from completed seasons (`rates`), times each top
  teammate's expected absence.
- **The pair part** (I49): fit on this season's games before g, on what the pooled part leaves,
  for each penalty in the grid (the penalty is chosen walk-forward, from earlier seasons).
- **The structured part** (H37): team or head-coach same-group rates, from completed seasons.

Rows: every player in the five groups (skill groups for targets and carries) with 1+ earlier game
for the team that season, forecast whether or not he then plays (`played`; `y` is null if he
didn't). Whether he plays is participation's; the share is the share if he plays, and only games
he played are scored.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

from pcf.experts.vacated_opportunity import common as K
from pcf.experts.vacated_opportunity import data as D
from pcf.experts.vacated_opportunity import rates as R

c = pl.col
FALLBACK_SEASONS = (2013, 2014, 2015, 2016)
VAL = {"snap": "share", "target": "tgt_share", "carry": "car_share"}


# ---------------------------------------------------------------- the grid of who has played
def grid(pg: pl.DataFrame, tg: pl.DataFrame, season: int) -> pl.DataFrame:
    """Every team-game of `season` crossed with every player who played for that team before it:
    his games, snaps and mean shares to date, his latest group, whether he played this game and
    his shares in it."""
    p = pg.filter(c("season") == season).sort("gsis_id", "team", "week")
    cum = p.select(
        "gsis_id", "team", "week",
        n=c("week").cum_count().over("gsis_id", "team"),
        cs=c("snaps").cum_sum().over("gsis_id", "team"),
        c_share=c("share").cum_sum().over("gsis_id", "team"),
        c_tgt=c("tgt_share").cum_sum().over("gsis_id", "team"),
        c_car=c("car_share").cum_sum().over("gsis_id", "team"),
        q_share=(c("share") ** 2).cum_sum().over("gsis_id", "team"),
        q_tgt=(c("tgt_share") ** 2).cum_sum().over("gsis_id", "team"),
        q_car=(c("car_share") ** 2).cum_sum().over("gsis_id", "team"),
        g_last="group",
    ).with_columns(c("n").cast(pl.Int64))  # fmt: skip
    games = tg.filter(c("season") == season).select("game_id", "team", "week", "kickoff", "coach")
    first = p.group_by("gsis_id", "team").agg(first_wk=c("week").min())
    g = first.join(games, on="team").filter(c("week") > c("first_wk")).sort("week")
    g = g.join_asof(
        cum.sort("week"), on="week", by=["gsis_id", "team"], strategy="backward",
        allow_exact_matches=False,
    )  # fmt: skip
    g = g.with_columns(
        share_td=c("c_share") / c("n"), tgt_td=c("c_tgt") / c("n"), car_td=c("c_car") / c("n"),
        group=c("g_last"),
    ).with_columns(
        sd_share=(c("q_share") / c("n") - c("share_td") ** 2).clip(0).sqrt(),
        sd_tgt=(c("q_tgt") / c("n") - c("tgt_td") ** 2).clip(0).sqrt(),
        sd_car=(c("q_car") / c("n") - c("car_td") ** 2).clip(0).sqrt(),
    ).drop("c_share", "c_tgt", "c_car", "q_share", "q_tgt", "q_car", "g_last", "first_wk")  # fmt: skip
    now = p.select("gsis_id", "game_id", "team", y_share="share", y_tgt="tgt_share",
                   y_car="car_share", played=pl.lit(True))  # fmt: skip
    g = g.join(now, on=["gsis_id", "game_id", "team"], how="left").with_columns(c("played").fill_null(False))
    k = c("group").replace_strict(K.TOPK, return_dtype=pl.Int64)
    g = g.with_columns(rank=c("cs").rank("ordinal", descending=True).over("game_id", "team", "group"))
    return g.with_columns(top=(c("rank") <= k) & (c("n") >= 2), season=pl.lit(season, pl.Int32))


# ---------------------------------------------------------------- the chance a top player plays
def fallback_rates(pg: pl.DataFrame, tg: pl.DataFrame, rep: pl.DataFrame) -> dict[str, float]:
    """The share of top players who played, by the report's status, on 2013-2016 (never scored)."""
    rows = []
    for s in FALLBACK_SEASONS:
        g = grid(pg, tg, s).filter(c("top"))
        rows.append(g.join(rep, on=["gsis_id", "game_id", "team"], how="left")
                    .select(status=c("status").fill_null("none"), played="played"))  # fmt: skip
    t = pl.concat(rows).group_by("status").agg(rate=c("played").cast(pl.Float64).mean())
    out = dict(zip(t["status"], t["rate"], strict=True))
    out["Out"] = 0.0  # the brief: Out means 0
    return out


def chances(top: pl.DataFrame, rep: pl.DataFrame, ros: pl.DataFrame, avail: pl.DataFrame,
            fb: dict[str, float]) -> pl.DataFrame:  # fmt: skip
    """`p_play` for each top player-game (Saturday knowledge) and where it came from."""
    t = top.join(rep, on=["gsis_id", "game_id", "team"], how="left")
    t = t.join(ros.select("gsis_id", "team", "season", "week", on=pl.lit(True), reserve="reserve"),
               on=["gsis_id", "team", "season", "week"], how="left")  # fmt: skip
    a = avail.select("gsis_id", "game_id", "p_play", a_as_of="as_of")
    t = t.join(a, on=["gsis_id", "game_id"], how="left")
    known = c("a_as_of").is_not_null() & (c("a_as_of") <= c("kickoff"))
    rep_p = c("status").fill_null("none").replace_strict(fb, default=fb.get("none", 1.0), return_dtype=pl.Float64)
    off = (c("season") >= 2016) & c("on").is_null()
    res = c("reserve").fill_null(False)
    return t.with_columns(
        p_play=pl.when(off | res).then(0.0).when(known).then(c("p_play")).otherwise(rep_p),
        p_src=pl.when(off).then(pl.lit("off_roster")).when(res).then(pl.lit("reserve"))
        .when(known).then(pl.lit("availability")).otherwise(pl.lit("report")),
    ).drop("on", "a_as_of")


# ---------------------------------------------------------------- the walk
def shuffle_map(tg: pl.DataFrame, seed: int) -> pl.DataFrame:
    """For the shuffled null: each team-season's games permuted (game_id -> src_game)."""
    rng = np.random.default_rng(seed)
    out = []
    for (_team, _s), d in tg.group_by("team", "season", maintain_order=True):
        ids = d["game_id"].to_list()
        out.append(pl.DataFrame({"team": d["team"], "game_id": ids,
                                 "src_game": [ids[i] for i in rng.permutation(len(ids))]}))  # fmt: skip
    return pl.concat(out)


class Inputs:
    """Everything the walk reads, loaded once."""

    def __init__(self):
        self.pg = D.player_games()
        tg = D.team_games()
        self.tg = tg.with_columns(c("coach").fill_null(strategy="forward").over("team", "season"))
        self.rep = D.report()
        self.ros = D.on_roster()
        self.avail = D.chances()
        self.ab = R.absences(self.pg, self.tg)
        self.fb = fallback_rates(self.pg, self.tg, self.rep)
        self.grids = {s: grid(self.pg, self.tg, s) for s in range(K.FIRST, K.LAST + 1)}
        self.tops = {}
        for s, g in self.grids.items():
            if s == K.FIRST:
                continue
            t = g.filter(c("top")).select("gsis_id", "game_id", "team", "season", "week", "kickoff",
                                         "group", "share_td", "tgt_td", "car_td", "played")  # fmt: skip
            self.tops[s] = chances(t, self.rep, self.ros, self.avail, self.fb)


def _status(tops: pl.DataFrame, smap: pl.DataFrame | None) -> pl.DataFrame:
    """Each top player-game's absence, hindsight (`absent`) and Saturday (`q`, 1 - p_play), with
    the shuffled null's statuses moved from another game of the team-season."""
    t = tops.with_columns(absent=(~c("played")).cast(pl.Float64), q=1 - c("p_play"))
    if smap is None:
        return t
    src = t.select("gsis_id", "team", src_game="game_id", absent2="absent", q2="q")
    t = t.join(smap, on=["team", "game_id"], how="left").join(src, on=["gsis_id", "team", "src_game"], how="left")
    return t.with_columns(absent=c("absent2").fill_null(0.0), q=c("q2").fill_null(0.0)).drop(
        "src_game", "absent2", "q2")


def _base(rows: pl.DataFrame, earlier: pl.DataFrame, tops: pl.DataFrame, pool: str, val: str) -> pl.DataFrame:
    """No change: his mean over earlier games where every current top pool-mate played."""
    key = c("group") if pool == "group" else pl.lit("skill")
    J = tops.select("game_id", "team", j="gsis_id", pk=key)
    r = rows.select("gsis_id", "game_id", "team", "week", pk=key)
    x = r.join(J, on=["game_id", "team", "pk"]).filter(c("j") != c("gsis_id"))
    e = earlier.select("gsis_id", "team", g2="game_id", w2="week", v=c(val))
    xx = x.join(e, on=["gsis_id", "team"]).filter(c("w2") < c("week"))
    played = earlier.select(j="gsis_id", g2="game_id", jp=pl.lit(True))
    xx = xx.join(played, on=["j", "g2"], how="left")
    ok = xx.group_by("gsis_id", "game_id", "g2").agg(all_=c("jp").is_not_null().all(), v=c("v").first())
    b = ok.filter(c("all_")).group_by("gsis_id", "game_id").agg(base=c("v").mean(), n_with=pl.len())
    return rows.join(b, on=["gsis_id", "game_id"], how="left")


def walk(inp: Inputs, measure: str, seasons: Sequence[int], smap: pl.DataFrame | None = None,
         fits: dict | None = None, structured: bool = False, pair_grid=R.GRID) -> pl.DataFrame:  # fmt: skip
    """The walk for one measure. Returns one row per scored player-game with every rung's parts.
    `fits` (season -> rates.Fit) may be passed in to reuse the pooled refits; `smap` shuffles."""
    ycol, pool = K.MEASURES[measure]
    groups = K.GROUPS if pool == "group" else K.SKILL
    td = {"snap": "share_td", "target": "tgt_td", "carry": "car_td"}[measure]
    yname = {"snap": "y_share", "target": "y_tgt", "carry": "y_car"}[measure]
    sd = {"snap": "sd_share", "target": "sd_tgt", "carry": "sd_car"}[measure]
    ab = inp.ab if smap is None else _shuffle_ab(inp.ab, smap)
    if fits is None:
        fits = pooled_fits(inp, measure, seasons, ab)
    sfits = structured_fits(inp, measure, seasons, ab) if structured else {}
    out = []
    for s in seasons:
        g = inp.grids[s].filter(c("group").is_in(list(groups)))
        tops = _status(inp.tops[s].filter(c("group").is_in(list(groups))), smap)
        tops = tops.with_columns(e_sat=c("q") * c(td), e_hind=c("absent") * c(td))
        # every player with an earlier game: forecast on Saturday whether or not he then plays
        rows = g.select(
            "gsis_id", "game_id", "team", "season", "week", "group", "coach", "n", "rank",
            "top", "played", td, y=yname, sd=sd)  # fmt: skip
        if s >= 2016:  # only players on the team's roster or reserve lists that week
            rows = rows.join(inp.ros.select("gsis_id", "team", "season", "week"),
                             on=["gsis_id", "team", "season", "week"], how="semi")  # fmt: skip
        rows = rows.sort("played", descending=True).unique(["gsis_id", "game_id"], keep="first")
        earlier = inp.pg.filter((c("season") == s) & c("group").is_in(list(groups)))
        rows = _base(rows, earlier, tops, pool, ycol)
        rows = rows.with_columns(base=c("base").fill_null(c(td)), n_with=c("n_with").fill_null(0))
        pooled = fits[s - 1].pooled(groups)
        rate = pl.DataFrame({"gk": list(pooled), "rate": list(pooled.values())})
        J = tops.select("game_id", "team", j="gsis_id", group_j="group", e_sat="e_sat",
                        e_hind="e_hind", p_src="p_src", q="q", absent="absent")  # fmt: skip
        x = rows.select("gsis_id", "game_id", "team", "group", "coach").join(J, on=["game_id", "team"])
        x = x.filter(c("j") != c("gsis_id")).with_columns(gk=c("group") + ">" + c("group_j"))
        x = x.join(rate, on="gk", how="left").with_columns(c("rate").fill_null(0.0))
        same_pool = (c("group") == c("group_j")) if pool == "group" else pl.lit(True)
        same = c("group") == c("group_j")
        if structured:
            for kind in ("team", "coach"):
                cf = sfits[kind][s - 1].coef
                who = c("team") if kind == "team" else c("coach").fill_null("?")
                tab = pl.DataFrame({"sk": [k for k in cf if k.startswith(kind + "|")],
                                    f"r_{kind}": [v for k, v in cf.items() if k.startswith(kind + "|")]})  # fmt: skip
                sp_pool = sfits[kind][s - 1].pooled(groups)
                x = x.with_columns(sk=pl.lit(kind + "|") + who + "|" + c("group")).join(tab, on="sk", how="left")
                x = x.with_columns((pl.when(same).then(c(f"r_{kind}").fill_null(0.0)).otherwise(0.0)
                                    + c("gk").replace_strict(sp_pool, default=0.0, return_dtype=pl.Float64))
                                   .alias(f"rate_{kind}")).drop("sk", f"r_{kind}")  # fmt: skip
        agg = [
            (c("rate") * c("e_sat")).sum().alias("d_pool"),
            (c("rate") * c("e_hind")).sum().alias("d_pool_h"),
            c("e_sat").filter(same_pool).sum().alias("e_pool"),
            c("e_hind").filter(same_pool).sum().alias("e_pool_h"),
            c("e_sat").filter(same).sum().alias("e_same"),
            c("e_sat").filter(~same).sum().alias("e_cross"),
            (c("absent").filter(same_pool) > 0).any().alias("absent_pool"),
            (c("absent").filter(same) > 0).any().alias("absent_same"),
            (c("q").filter(same_pool) >= 0.5).any().alias("flag_pool"),
            c("p_src").filter(same_pool & (c("q") > 0.05)).first().alias("p_src"),
            c("j").filter(c("e_sat") > 0.02).str.join(",").alias("drivers"),
        ]
        if structured:
            agg += [(c("rate_team") * c("e_sat")).sum().alias("d_team"),
                    (c("rate_coach") * c("e_sat")).sum().alias("d_coach")]
        dx = x.group_by("gsis_id", "game_id").agg(agg)
        rows = rows.join(dx, on=["gsis_id", "game_id"], how="left")
        fill = ["d_pool", "d_pool_h", "e_pool", "e_pool_h", "e_same", "e_cross"] + (
            ["d_team", "d_coach"] if structured else [])
        rows = rows.with_columns([c(f).fill_null(0.0) for f in fill]).with_columns(
            c("absent_pool").fill_null(False), c("absent_same").fill_null(False), c("flag_pool").fill_null(False))
        rows = rows.join(_pair_part(inp, s, tops, measure, groups, pooled, pair_grid, x), on=["gsis_id", "game_id"], how="left")
        pcols = [col for col in rows.columns if col.startswith("d_pair")]
        rows = rows.with_columns([c(p).fill_null(0.0) for p in pcols])
        out.append(rows.with_columns(measure=pl.lit(measure), alpha=pl.lit(fits[s - 1].alpha)))
    return pl.concat(out, how="diagonal_relaxed")


def _shuffle_ab(ab: pl.DataFrame, smap: pl.DataFrame) -> pl.DataFrame:
    """Completed seasons' absences moved to another game of the same team-season."""
    inv = smap.select("team", src_game="game_id", game_id="src_game")
    return ab.rename({"game_id": "src_game"}).join(inv, on=["team", "src_game"], how="inner").drop("src_game")


def pooled_fits(inp: Inputs, measure: str, seasons: Sequence[int], ab: pl.DataFrame | None = None) -> dict:
    """The pooled refits each walked season reads (fit on every completed season before it)."""
    ab = inp.ab if ab is None else ab
    blocks = R.blocks_for(inp.pg, ab, measure, range(K.FIRST, max(seasons)))
    return {s - 1: R.fit_through(blocks, s - 1) for s in seasons}


def structured_fits(inp: Inputs, measure: str, seasons: Sequence[int], ab: pl.DataFrame) -> dict:
    out = {}
    for kind in ("team", "coach"):
        blocks = R.blocks_for(inp.pg, ab, measure, range(K.FIRST, max(seasons)), extra=kind, tg=inp.tg)
        out[kind] = {s - 1: R.fit_through(blocks, s - 1) for s in seasons}
    return out


def _pair_part(inp: Inputs, s: int, tops: pl.DataFrame, measure: str, groups, pooled: dict,
               grid_: Sequence[float], x: pl.DataFrame) -> pl.DataFrame:  # fmt: skip
    """Each week: the pair part fit on this season's earlier games (absences known by then: a
    top-to-date player who missed one), on what the pooled part leaves; applied to the expected
    absences of this week's top players. One column per penalty."""
    ycol, _ = K.MEASURES[measure]
    td = {"snap": "share_td", "target": "tgt_td", "carry": "car_td"}[measure]
    played = inp.pg.filter((c("season") == s) & c("group").is_in(list(groups))).select(
        "gsis_id", "team", "season", "week", "game_id", "group", ycol)
    ab_s = tops.filter(c("absent") > 0).select(
        j="gsis_id", team="team", game_id="game_id", week="week", group_j="group", w=c(td))
    pk = R.pool_keys(groups)
    out = []
    xx = x.filter(c("group") == c("group_j")).select("gsis_id", "game_id", "j", "e_sat", "e_hind")
    weeks = sorted(x.join(tops.select("game_id", "week").unique(), on="game_id")["week"].unique().to_list())
    for w in weeks:
        before = played.filter(c("week") < w)
        a_b = ab_s.filter(c("week") < w)
        now = xx.join(tops.filter(c("week") == w).select("game_id").unique(), on="game_id")
        if a_b.height == 0 or now.height == 0:
            continue
        d = R.design(before.drop("week"), a_b, ycol, "w", groups)
        npool = len(pk)
        beta = np.array([pooled.get(k, 0.0) for k in d.keys[:npool]])
        r = d.y - d.X[:, :npool] @ beta
        ip = np.arange(npool, len(d.keys))
        if not len(ip):
            continue
        Xp = d.X[:, ip]
        keys = [d.keys[i] for i in ip]
        now = now.with_columns(pk_=c("gsis_id") + ">" + c("j") + ">" + pl.lit(str(s)))
        cols = {}
        for a in grid_:
            b = R.ridge(Xp, r, a)
            tab = dict(zip(keys, b.tolist(), strict=True))
            cols[a] = now["pk_"].replace_strict(tab, default=0.0, return_dtype=pl.Float64).to_numpy()
        res = now.select("gsis_id", "game_id", "e_sat", "e_hind")
        for a, v in cols.items():
            res = res.with_columns(pl.Series(f"_b{a}", v))
        agg = []
        for a in grid_:
            agg += [(c(f"_b{a}") * c("e_sat")).sum().alias(f"d_pair_{a}"),
                    (c(f"_b{a}") * c("e_hind")).sum().alias(f"d_pairh_{a}")]
        out.append(res.group_by("gsis_id", "game_id").agg(agg))
    if not out:
        return pl.DataFrame(schema={"gsis_id": pl.Utf8, "game_id": pl.Utf8})
    return pl.concat(out)
