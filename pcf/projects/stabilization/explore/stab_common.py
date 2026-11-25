"""Stabilization's exploration: the shared measure tables (EXPLORATION.md, "What is measured").

Builds, once, and caches outside git (the scratch folder under the data directory's interim zone):
- `player_game`: one row per player-game-measure: gsis_id, season, week, game_id, team, group,
  measure, num, den. A rate is num / den; den is its attempts.
- `team_game`: the same for teams (side: off or def), and `team_quarter` by quarter.
- `cond`: the teammates' conditions per player-game (H113), as num and den.

Regular season only, two-point tries left out, 2006-2024 (the 2025 vault is closed).
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import read_part

c = pl.col
FIRST, LAST = 2006, 2024
SEASONS = list(range(FIRST, LAST + 1))
CACHE = get_config().zone("interim") / "stabilization_explore"

GROUP = {
    "WR": "receiver", "TE": "receiver", "RB": "back", "QB": "qb",
    "DE": "rusher", "DT": "rusher", "NT": "rusher", "DL": "rusher", "OLB": "rusher",
    "CB": "coverage", "S": "coverage", "SS": "coverage", "FS": "coverage", "DB": "coverage",
    "LB": "coverage", "ILB": "coverage", "MLB": "coverage",
}  # fmt: skip
# which group each measure belongs to (backs also run routes: receiver measures are for WR, TE and RB)
MEASURES = {
    "tprr": "receiver", "yprr": "receiver", "adot": "receiver", "catch_oe": "receiver", "yac_oe": "receiver",
    "car_per_run": "back", "yaco": "back", "broken_per_touch": "back",
    "hitsack": "qb", "sack": "qb", "scramble": "qb", "qb_adot": "qb", "cpoe": "qb", "pressured": "qb",
    "press_per_snap": "rusher", "hits_per_snap": "rusher",
    "tgt_per_cov": "coverage", "catch_allowed": "coverage", "adot_allowed": "coverage", "missed_tackle": "coverage",
}  # fmt: skip
TEAM_MEASURES = ["hitsack", "proe", "shotgun", "no_huddle", "explosive", "success", "adot"]


def _part(name: str, part: str, cols: list[str], seasons=SEASONS) -> pl.DataFrame:
    lf = read_part(name, part, seasons, None)
    have = lf.collect_schema().names()
    return lf.select([x for x in cols if x in have]).collect()


def _plays() -> pl.DataFrame:
    cols = ["game_id", "play_id", "season", "week", "season_type", "posteam", "defteam", "qtr", "play_type",
            "two_point_attempt", "qb_dropback", "qb_scramble", "sack", "qb_hit", "pass_attempt", "rush_attempt",
            "complete_pass", "air_yards", "cp", "cpoe", "yards_after_catch", "xyac_mean_yardage", "receiving_yards",
            "yards_gained", "receiver_player_id", "passer_player_id", "rusher_player_id", "shotgun", "no_huddle",
            "success", "pass_oe", "qb_hit_1_player_id", "qb_hit_2_player_id", "sack_player_id",
            "half_sack_1_player_id", "half_sack_2_player_id"]  # fmt: skip
    p = _part("play", "pbp", cols)
    p = p.filter((c("season_type") == "REG") & (c("two_point_attempt").fill_null(0) == 0)
                 & c("play_type").is_in(["pass", "run"]) & c("posteam").is_not_null())  # fmt: skip
    return p.with_columns(
        dropback=c("qb_dropback").fill_null(0) == 1,
        run=(c("play_type") == "run") & (c("qb_scramble").fill_null(0) == 0),
        target=(c("pass_attempt").fill_null(0) == 1) & (c("sack").fill_null(0) == 0) & c("receiver_player_id").is_not_null(),
    )


def _roster() -> pl.DataFrame:
    r = _part("player_game", "roster", ["gsis_id", "game_id", "season", "week", "team", "position"])
    return r.unique(["gsis_id", "game_id"]).with_columns(group=c("position").replace_strict(GROUP, default=None))


def _long(d: pl.DataFrame, measure: str, num, den) -> pl.DataFrame:
    return d.select("gsis_id", "game_id", measure=pl.lit(measure), num=num.cast(pl.Float64), den=den.cast(pl.Float64))


def build() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = _plays()
    ros = _roster()
    out = []

    # receivers, from play-by-play (every target)
    t = p.filter(c("target")).rename({"receiver_player_id": "gsis_id"})
    g = t.group_by("gsis_id", "game_id").agg(
        n_tgt=pl.len(), yds=c("receiving_yards").fill_null(0).sum(),
        ay=c("air_yards").sum(), n_ay=c("air_yards").is_not_null().sum(),
        coe=(c("complete_pass") - c("cp")).sum(), n_cp=c("cp").is_not_null().sum(),
        yoe=(c("yards_after_catch") - c("xyac_mean_yardage")).filter(c("complete_pass") == 1).sum(),
        n_yac=(c("xyac_mean_yardage").is_not_null() & c("yards_after_catch").is_not_null() & (c("complete_pass") == 1)).sum(),
    )
    out += [_long(g, "adot", c("ay"), c("n_ay")), _long(g, "catch_oe", c("coe"), c("n_cp")), _long(g, "yac_oe", c("yoe"), c("n_yac"))]

    # routes and run snaps (participation, 2016+)
    of = _part("player_play", "on_field", ["game_id", "play_id", "season", "side", "gsis_id"], range(2016, LAST + 1))
    of = of.unique(["game_id", "play_id", "gsis_id"])
    kinds = p.select("game_id", "play_id", "dropback", "run")
    off = of.filter(c("side") == "offense").join(kinds, on=["game_id", "play_id"])
    oc = off.group_by("gsis_id", "game_id").agg(routes=c("dropback").sum(), run_snaps=c("run").sum())
    rg = oc.join(g.select("gsis_id", "game_id", "n_tgt", "yds"), on=["gsis_id", "game_id"], how="left").fill_null(0)
    out += [_long(rg, "tprr", c("n_tgt"), c("routes")), _long(rg, "yprr", c("yds"), c("routes"))]
    car = p.filter(c("run")).group_by(c("rusher_player_id").alias("gsis_id"), "game_id").agg(car=pl.len())
    cg = oc.join(car, on=["gsis_id", "game_id"], how="left").fill_null(0)
    out.append(_long(cg, "car_per_run", c("car"), c("run_snaps")))
    deff = of.filter(c("side") == "defense").join(kinds, on=["game_id", "play_id"])
    dc = deff.group_by("gsis_id", "game_id").agg(pass_snaps=c("dropback").sum())
    hits = pl.concat([
        p.filter(c("dropback")).select("game_id", gsis_id=c(k)) for k in
        ("qb_hit_1_player_id", "qb_hit_2_player_id", "sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id")
    ]).drop_nulls("gsis_id").group_by("gsis_id", "game_id").agg(hits=pl.len())  # fmt: skip
    hg = dc.join(hits, on=["gsis_id", "game_id"], how="left").fill_null(0)
    out.append(_long(hg, "hits_per_snap", c("hits"), c("pass_snaps")))

    # QBs (every dropback: the passer, or the scrambler)
    db = p.filter(c("dropback")).with_columns(
        gsis_id=pl.when(c("qb_scramble").fill_null(0) == 1).then(pl.coalesce("passer_player_id", "rusher_player_id"))
        .otherwise(pl.coalesce("passer_player_id", "rusher_player_id"))
    ).drop_nulls("gsis_id")
    q = db.group_by("gsis_id", "game_id").agg(
        n=pl.len(), hs=((c("qb_hit").fill_null(0) == 1) | (c("sack").fill_null(0) == 1)).sum(),
        sk=c("sack").fill_null(0).sum(), sc=c("qb_scramble").fill_null(0).sum(),
        ay=c("air_yards").filter(c("pass_attempt") == 1).sum(), n_ay=(c("air_yards").is_not_null() & (c("pass_attempt") == 1)).sum(),
        cp=c("cpoe").sum() / 100, n_cp=c("cpoe").is_not_null().sum(),
    )
    out += [_long(q, "hitsack", c("hs"), c("n")), _long(q, "sack", c("sk"), c("n")), _long(q, "scramble", c("sc"), c("n")),
            _long(q, "qb_adot", c("ay"), c("n_ay")), _long(q, "cpoe", c("cp"), c("n_cp"))]  # fmt: skip

    # PFR (2018+)
    pfr = _part("player_game", "pfr", ["gsis_id", "game_id", "pfr_pass_times_pressured", "pfr_rush_carries",
                "pfr_rush_rushing_yards_after_contact", "pfr_rush_rushing_broken_tackles", "pfr_rec_receiving_broken_tackles",
                "pfr_def_def_pressures", "pfr_def_def_targets", "pfr_def_def_completions_allowed", "pfr_def_def_adot",
                "pfr_def_def_missed_tackles", "pfr_def_def_tackles_combined"], range(2018, LAST + 1))  # fmt: skip
    f = pfr.join(q.select("gsis_id", "game_id", "n"), on=["gsis_id", "game_id"], how="left")
    out.append(_long(f.drop_nulls(["pfr_pass_times_pressured", "n"]), "pressured", c("pfr_pass_times_pressured"), c("n")))
    rec = g.select("gsis_id", "game_id", catches=c("n_yac"))
    f = f.join(rec, on=["gsis_id", "game_id"], how="left")
    b = f.drop_nulls("pfr_rush_carries")
    out += [_long(b, "yaco", c("pfr_rush_rushing_yards_after_contact").fill_null(0), c("pfr_rush_carries")),
            _long(b, "broken_per_touch", c("pfr_rush_rushing_broken_tackles").fill_null(0) + c("pfr_rec_receiving_broken_tackles").fill_null(0),
                  c("pfr_rush_carries") + c("catches").fill_null(0))]  # fmt: skip
    dd = f.join(dc, on=["gsis_id", "game_id"], how="left")
    out += [_long(dd.drop_nulls(["pfr_def_def_pressures", "pass_snaps"]), "press_per_snap", c("pfr_def_def_pressures"), c("pass_snaps")),
            _long(dd.drop_nulls(["pfr_def_def_targets", "pass_snaps"]), "tgt_per_cov", c("pfr_def_def_targets"), c("pass_snaps")),
            _long(dd.drop_nulls("pfr_def_def_targets"), "catch_allowed", c("pfr_def_def_completions_allowed").fill_null(0), c("pfr_def_def_targets")),
            _long(dd.drop_nulls(["pfr_def_def_adot", "pfr_def_def_targets"]), "adot_allowed", c("pfr_def_def_adot") * c("pfr_def_def_targets"), c("pfr_def_def_targets")),
            _long(dd.drop_nulls("pfr_def_def_tackles_combined"), "missed_tackle", c("pfr_def_def_missed_tackles").fill_null(0),
                  c("pfr_def_def_tackles_combined").fill_null(0) + c("pfr_def_def_missed_tackles").fill_null(0))]  # fmt: skip

    long = pl.concat(out).filter(c("den") > 0)
    long = long.join(ros.select("gsis_id", "game_id", "season", "week", "team", "group"), on=["gsis_id", "game_id"], how="inner")
    want = pl.DataFrame({"measure": list(MEASURES), "need": list(MEASURES.values())})
    long = long.join(want, on="measure").filter(
        (c("group") == c("need")) | ((c("need") == "receiver") & (c("group") == "back"))
    ).drop("need")
    long.write_parquet(CACHE / "player_game.parquet")
    print(f"player_game: {long.height:,} rows")
    print(long.group_by("measure").agg(rows=pl.len(), players=c("gsis_id").n_unique(), first=c("season").min(),
                                       att=c("den").sum()).sort("measure"))  # fmt: skip

    # teams, by game and by quarter
    tm = []
    for side, key in (("off", "posteam"), ("def", "defteam")):
        for by, name in ((["game_id"], "team_game"), (["game_id", "qtr"], "team_quarter")):
            a = p.group_by(c(key).alias("team"), "season", "week", *by).agg(
                hitsack_n=((c("qb_hit").fill_null(0) == 1) | (c("sack").fill_null(0) == 1)).filter(c("dropback")).sum(), hitsack_d=c("dropback").sum(),
                proe_n=c("pass_oe").sum() / 100, proe_d=c("pass_oe").is_not_null().sum(),
                shotgun_n=c("shotgun").fill_null(0).sum(), shotgun_d=pl.len(),
                no_huddle_n=c("no_huddle").fill_null(0).sum(), no_huddle_d=pl.len(),
                explosive_n=(((c("pass_attempt") == 1) & (c("yards_gained") >= 20)) | (c("run") & (c("yards_gained") >= 10))).sum(), explosive_d=pl.len(),
                success_n=c("success").fill_null(0).sum(), success_d=pl.len(),
                adot_n=c("air_yards").filter(c("pass_attempt") == 1).sum(), adot_d=(c("air_yards").is_not_null() & (c("pass_attempt") == 1)).sum(),
            )  # fmt: skip
            rows = [a.select("team", "season", "week", *by, side=pl.lit(side), measure=pl.lit(m),
                             num=c(f"{m}_n").cast(pl.Float64), den=c(f"{m}_d").cast(pl.Float64)) for m in TEAM_MEASURES]  # fmt: skip
            tm.append((name, pl.concat(rows).filter(c("den") > 0)))
    for name in ("team_game", "team_quarter"):
        d = pl.concat([x for n, x in tm if n == name])
        d.write_parquet(CACHE / f"{name}.parquet")
        print(f"{name}: {d.height:,} rows")

    # teammates' conditions per player-game (H113)
    tg = pl.read_parquet(CACHE / "team_game.parquet")
    team_hs = tg.filter((c("side") == "off") & (c("measure") == "hitsack")).select("team", "game_id", hs_n="num", hs_d="den")
    team_pr = tg.filter((c("side") == "off") & (c("measure") == "proe")).select("team", "game_id", pr_n="num", pr_d="den")
    tcp = p.filter(c("target") & c("cpoe").is_not_null()).group_by(c("posteam").alias("team"), "game_id").agg(tcp_n=(c("cpoe") / 100).sum(), tcp_d=pl.len())
    mine = t.filter(c("cpoe").is_not_null()).group_by("gsis_id", "game_id").agg(my_n=(c("cpoe") / 100).sum(), my_d=pl.len())
    base = ros.select("gsis_id", "game_id", "team", "group")
    cond = (base.join(team_hs, on=["team", "game_id"], how="left").join(team_pr, on=["team", "game_id"], how="left")
            .join(tcp, on=["team", "game_id"], how="left").join(mine, on=["gsis_id", "game_id"], how="left")
            .with_columns(c("my_n", "my_d").fill_null(0))
            .with_columns(oc_n=c("tcp_n") - c("my_n"), oc_d=c("tcp_d") - c("my_d")))  # fmt: skip
    # the rest of the defense's pressures, and the rest of the coverage's catches allowed (PFR)
    dpf = pfr.join(ros.select("gsis_id", "game_id", "team", "group"), on=["gsis_id", "game_id"])
    tdp = dpf.group_by("team", "game_id").agg(tp=c("pfr_def_def_pressures").fill_null(0).sum(),
                                             tt=c("pfr_def_def_targets").fill_null(0).sum(), tc=c("pfr_def_def_completions_allowed").fill_null(0).sum())  # fmt: skip
    faced = tg.filter((c("side") == "def") & (c("measure") == "hitsack")).select("team", "game_id", db_d="den")
    cond = (cond.join(tdp, on=["team", "game_id"], how="left").join(faced, on=["team", "game_id"], how="left")
            .join(pfr.select("gsis_id", "game_id", mp=c("pfr_def_def_pressures").fill_null(0), mt=c("pfr_def_def_targets").fill_null(0),
                             mc=c("pfr_def_def_completions_allowed").fill_null(0)), on=["gsis_id", "game_id"], how="left")
            .with_columns(c("mp", "mt", "mc").fill_null(0))
            .with_columns(op_n=c("tp") - c("mp"), op_d=c("db_d"), ocat_n=c("tc") - c("mc"), ocat_d=c("tt") - c("mt")))  # fmt: skip
    cond.select("gsis_id", "game_id", "team", "hs_n", "hs_d", "pr_n", "pr_d", "oc_n", "oc_d", "op_n", "op_d", "ocat_n", "ocat_d").write_parquet(CACHE / "cond.parquet")
    print(f"cond: {cond.height:,} rows")


def load(name: str) -> pl.DataFrame:
    path = CACHE / f"{name}.parquet"
    if not path.exists():
        build()
    return pl.read_parquet(path)


# ---------------------------------------------------------------- shared statistics


def components(season_rows: pl.DataFrame, game_rows: pl.DataFrame, min_den: float = 1.0):
    """Noise per attempt (sigma2) and the true spread (tau2) from player-seasons, weighted.
    sigma2: the weighted scatter of a player's games around his season rate; tau2: the spread of
    season rates less the average noise. Returns (mu, sigma2, tau2)."""
    s = season_rows.filter(c("den") >= min_den)
    x, n = (s["num"] / s["den"]).to_numpy(), s["den"].to_numpy()
    mu = np.average(x, weights=n)
    gr = game_rows.join(s.select("key", rate=c("num") / c("den"), G="games"), on="key")
    gr = gr.filter(c("G") >= 2)
    dev = (gr["den"] * (gr["num"] / gr["den"] - gr["rate"]) ** 2).to_numpy()
    per = gr.with_columns(dev=pl.Series(dev)).group_by("key").agg(ss=c("dev").sum(), G=c("G").first())
    sigma2 = float((per["ss"] / (per["G"] - 1)).mean())
    # tau2 by moments: var of x around mu (weights n) minus mean noise
    w = n / n.sum()
    tau2 = float(np.sum(w * (x - mu) ** 2) - sigma2 * np.sum(w / n))
    return mu, sigma2, max(tau2, 1e-12)


def seasons_of(pg: pl.DataFrame, keys=("gsis_id", "season", "measure")) -> pl.DataFrame:
    return pg.group_by(*keys).agg(num=c("num").sum(), den=c("den").sum(), games=pl.len(),
                                  team=c("team").mode().first(), group=c("group").mode().first())  # fmt: skip


class Say:
    def __init__(self, path: Path) -> None:
        self.path, self.lines = path, []

    def __call__(self, *t: str) -> None:
        for x in t:
            self.lines.append(x)
            print(x, flush=True)

    def save(self) -> None:
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()


POS = {"WR": "WR", "TE": "TE", "RB": "RB", "QB": "QB", "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL",
       "OLB": "OLB", "CB": "CB", "S": "S", "SS": "S", "FS": "S", "DB": "S", "LB": "LB", "ILB": "LB", "MLB": "LB"}  # fmt: skip


def player_seasons(min_den: float = 1.0) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(season rows, game rows), each with `key` (player-season-measure) and `pos`."""
    pg = load("player_game")
    pos = _roster().select("gsis_id", "game_id", pos=c("position").replace_strict(POS, default=None))
    pg = pg.join(pos, on=["gsis_id", "game_id"], how="left")
    pg = pg.with_columns(key=pl.concat_str("gsis_id", pl.lit("|"), c("season").cast(pl.Utf8), pl.lit("|"), "measure"))
    s = pg.group_by("key", "gsis_id", "season", "measure").agg(
        num=c("num").sum(), den=c("den").sum(), games=pl.len(), team=c("team").mode().first(),
        pos=c("pos").mode().first(), teams=c("team").n_unique())
    return s.filter(c("den") >= min_den), pg


def fit_m1(s: pl.DataFrame, game: pl.DataFrame, measure: str, before: int, min_den: float = 10.0):
    """Method 1 fit on seasons before `before`. The noise and the true spread are pooled over
    positions and seasons around each position-season's own mean (league rates shift by season:
    charting and model changes). The pull-back target is each position's mean in the latest
    training season. Returns {pos: mu}, sigma2, tau2, k."""
    tr = s.filter((c("measure") == measure) & (c("season") < before) & (c("den") >= min_den) & c("pos").is_not_null())
    ps = tr.group_by("pos", "season").agg(mu=(c("num").sum() / c("den").sum()), m=pl.len()).filter(c("m") >= 20)
    tr = tr.join(ps.select("pos", "season", "mu"), on=["pos", "season"])
    last = tr["season"].max()
    mus = {p: float(m) for p, m in ps.filter(c("season") == last).select("pos", "mu").iter_rows()}
    adj = tr.with_columns(num=c("num") - c("mu") * c("den"))
    gm = game.filter(c("key").is_in(adj["key"].implode())).join(tr.select("key", "mu"), on="key").with_columns(num=c("num") - c("mu") * c("den"))
    _, sigma2, tau2 = components(adj, gm, min_den)
    return mus, sigma2, tau2, sigma2 / tau2


def wls_r(x, y, w):
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    return cov / np.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w))


GROUP_MEASURES = {
    "receiver": ["tprr", "yprr", "adot", "catch_oe", "yac_oe"],
    "back": ["car_per_run", "yaco", "broken_per_touch"],
    "qb": ["hitsack", "sack", "scramble", "qb_adot", "cpoe", "pressured"],
    "rusher": ["press_per_snap", "hits_per_snap"],
    "coverage": ["tgt_per_cov", "catch_allowed", "adot_allowed", "missed_tackle"],
}


def next_season_frame(s: pl.DataFrame, game: pl.DataFrame, measure: str, first_target: int) -> pl.DataFrame | None:
    """For each target season T: the player's season T-1 (x, n, team, pos), M1's fit before T,
    M1's forecast, and season T's rate (y) and attempts (w)."""
    out = []
    m = s.filter(c("measure") == measure)
    for T in range(first_target, 2025):
        mus, s2, t2, k = fit_m1(s, game, measure, T)
        a = m.filter(c("season") == T - 1).select("gsis_id", "pos", "team", x=c("num") / c("den"), n="den")
        b = m.filter(c("season") == T).select("gsis_id", team_next="team", y=c("num") / c("den"), w="den")
        d = a.join(b, on="gsis_id").filter(c("pos").is_in(list(mus)))
        if d.height == 0:
            continue
        d = d.with_columns(T=pl.lit(T), mu=c("pos").replace_strict(mus), k=pl.lit(k), s2=pl.lit(s2), t2=pl.lit(t2))
        out.append(d.with_columns(m1=c("mu") + c("n") / (c("n") + c("k")) * (c("x") - c("mu"))))
    return pl.concat(out) if out else None


def boot_gain(f: pl.DataFrame, a: str, b: str, rng, draws: int = 1000, cluster: str = "gsis_id"):
    """Share of b's weighted squared error that a removes (y, w); clusters resampled."""
    e = f.with_columns(ea=c("w") * (c("y") - c(a)) ** 2, eb=c("w") * (c("y") - c(b)) ** 2)
    p = e.group_by(cluster).agg(ea=c("ea").sum(), eb=c("eb").sum())
    ea, eb = p["ea"].to_numpy(), p["eb"].to_numpy()
    idx = rng.integers(0, len(ea), (draws, len(ea)))
    g = 1 - ea[idx].sum(1) / eb[idx].sum(1)
    return float(1 - ea.sum() / eb.sum()), float(np.quantile(g, 0.05)), float(np.quantile(g, 0.95))
