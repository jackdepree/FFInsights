"""Aging's exploration: the shared player-season table (EXPLORATION.md, "What is measured").

Builds once and caches outside git (the interim zone's `aging_explore` folder):
- `game`: one row per player-game with his team, position, his opportunities, his team's, and his
  efficiency's num and den.
- `season`: one row per player-season, 2002-2024: age, position, draft, usage (share of his team's
  opportunities over his roster weeks), efficiency (EPA per opportunity), PPR points and rank,
  mileage (cumulative passing and rushing involvements from play-by-play, 1999+).

Regular season only; the 2025 vault is closed.
"""

# ruff: noqa: E501
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import read_part

c = pl.col
FIRST, LAST = 2002, 2024
CACHE = get_config().zone("interim") / "aging_explore"
POS = {"QB": "QB", "RB": "RB", "FB": "RB", "HB": "RB", "WR": "WR", "TE": "TE",
       "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "OLB": "LB", "ILB": "LB", "MLB": "LB", "LB": "LB",
       "CB": "DB", "S": "DB", "SS": "DB", "FS": "DB", "DB": "DB", "SAF": "DB"}  # fmt: skip  (the roster calls corners DB from 2016)
OFF = ["QB", "RB", "WR", "TE"]
DEF = ["DL", "LB", "DB"]


def _part(name, part, cols, seasons):
    return read_part(name, part, list(seasons), None).select(cols).collect()


def pass_plays(seasons, ros: pl.DataFrame | None = None) -> pl.DataFrame:
    """Regular-season pass attempts (no sacks, no two-point tries) with the target's gsis_id. Play-by-play names the
    receiver of an incompletion without an id in 2003-2008 (and the stats table has almost no targets those years), so
    a missing id is filled from the game's roster by team and jersey number."""
    pbp = read_part("play", "pbp", list(seasons), None).select(
        "game_id", "play_id", "season", "season_type", "posteam", "pass_attempt", "sack", "two_point_attempt", "receiver_player_id", "receiver_jersey_number", "epa"
    ).collect().filter((c("season_type") == "REG") & (c("pass_attempt") == 1) & (c("sack") == 0) & (c("two_point_attempt").fill_null(0) == 0))  # fmt: skip
    if ros is None:
        ros = read_part("player_game", "roster", [s for s in seasons if s >= FIRST], None).select("gsis_id", "game_id", "team", "jersey_number").collect()
    jr = (ros.select("game_id", posteam="team", receiver_jersey_number=c("jersey_number").cast(pl.Int32, strict=False), rid_j="gsis_id")
          .drop_nulls().unique(["game_id", "posteam", "receiver_jersey_number"], keep="none"))  # fmt: skip
    pbp = pbp.join(jr, on=["game_id", "posteam", "receiver_jersey_number"], how="left")
    return pbp.with_columns(rid=pl.coalesce("receiver_player_id", "rid_j")).select("game_id", "play_id", "season", "posteam", "rid", "epa")


def build() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    S = range(FIRST, LAST + 1)
    ros = _part("player_game", "roster", ["gsis_id", "game_id", "season", "week", "team", "position", "birth_date", "entry_year", "draft_number", "jersey_number"], S)
    ros = ros.with_columns(pos=c("position").replace_strict(POS, default=None)).unique(["gsis_id", "game_id"])
    st = _part("player_game", "stats", ["gsis_id", "game_id", "season", "attempts", "sacks_suffered", "carries", "targets", "receptions",
                                        "passing_epa", "rushing_epa", "receiving_epa", "passing_yards", "passing_tds", "passing_interceptions",
                                        "rushing_yards", "rushing_tds", "receiving_yards", "receiving_tds",
                                        "rushing_fumbles_lost", "receiving_fumbles_lost", "sack_fumbles_lost"], S)  # fmt: skip
    st = st.fill_null(0).unique(["gsis_id", "game_id"])
    # targets and receiving EPA a target from play-by-play (the stats table lacks targets in 2003-2008, and its receiving EPA leaves out incompletions there)
    pp = pass_plays(S, ros.select("gsis_id", "game_id", "team", "jersey_number"))
    print("pass attempts with a target found:", pp.group_by("season").agg(f=c("rid").is_not_null().mean()).sort("season")["f"].round(3).to_list())
    tg = pp.drop_nulls("rid").group_by(gsis_id="rid", game_id="game_id").agg(targets_p=pl.len(), repa_p=c("epa").fill_null(0).sum())
    st = st.join(tg, on=["gsis_id", "game_id"], how="left").with_columns(targets=c("targets_p").fill_null(0), receiving_epa=c("repa_p").fill_null(0)).drop("targets_p", "repa_p")
    st = st.join(ros.select("gsis_id", "game_id", "team"), on=["gsis_id", "game_id"], how="inner")
    team = st.group_by("team", "game_id").agg(t_db=(c("attempts") + c("sacks_suffered")).sum(), t_car=c("carries").sum(), t_tgt=c("targets").sum())
    # defensive snaps (2013+): the team's snaps from any player's count over his share
    sn = _part("player_game", "snaps", ["gsis_id", "game_id", "season", "defense_snaps", "defense_pct"], range(2013, LAST + 1)).unique(["gsis_id", "game_id"])
    sn = sn.join(ros.select("gsis_id", "game_id", "team"), on=["gsis_id", "game_id"], how="inner")
    tds = sn.filter(c("defense_pct") > 0.2).group_by("team", "game_id").agg(t_dsn=(c("defense_snaps") / c("defense_pct")).median().round())
    g = (ros.join(st.drop("team", "season"), on=["gsis_id", "game_id"], how="left").join(team, on=["team", "game_id"], how="left")
         .join(sn.select("gsis_id", "game_id", "defense_snaps"), on=["gsis_id", "game_id"], how="left").join(tds, on=["team", "game_id"], how="left"))  # fmt: skip
    num_cols = ["attempts", "sacks_suffered", "carries", "targets", "receptions", "passing_epa", "rushing_epa", "receiving_epa", "passing_yards",
                "passing_tds", "passing_interceptions", "rushing_yards", "rushing_tds", "receiving_yards", "receiving_tds",
                "rushing_fumbles_lost", "receiving_fumbles_lost", "sack_fumbles_lost", "defense_snaps"]  # fmt: skip
    g = g.with_columns([c(x).fill_null(0) for x in num_cols])
    g = g.with_columns(
        u_num=pl.when(c("pos") == "QB").then(c("attempts") + c("sacks_suffered")).when(c("pos") == "RB").then(c("carries") + c("targets"))
        .when(c("pos").is_in(["WR", "TE"])).then(c("targets")).otherwise(c("defense_snaps")),
        u_den=pl.when(c("pos") == "QB").then(c("t_db")).when(c("pos") == "RB").then(c("t_car") + c("t_tgt"))
        .when(c("pos").is_in(["WR", "TE"])).then(c("t_tgt")).otherwise(c("t_dsn")),
        e_num=pl.when(c("pos") == "QB").then(c("passing_epa")).when(c("pos") == "RB").then(c("rushing_epa"))
        .when(c("pos").is_in(["WR", "TE"])).then(c("receiving_epa")).otherwise(None),
        e_den=pl.when(c("pos") == "QB").then(c("attempts") + c("sacks_suffered")).when(c("pos") == "RB").then(c("carries"))
        .when(c("pos").is_in(["WR", "TE"])).then(c("targets")).otherwise(None),
        ppr=c("passing_yards") * 0.04 + c("passing_tds") * 4 - c("passing_interceptions") * 2 + c("rushing_yards") * 0.1 + c("rushing_tds") * 6
        + c("receptions") + c("receiving_yards") * 0.1 + c("receiving_tds") * 6 - 2 * (c("rushing_fumbles_lost") + c("receiving_fumbles_lost") + c("sack_fumbles_lost")),
    ).filter(c("pos").is_not_null())  # fmt: skip
    g = g.select("gsis_id", "game_id", "season", "week", "team", "pos", "u_num", "u_den", "e_num", "e_den", "ppr",
                 "birth_date", "entry_year", "draft_number", "jersey_number")  # fmt: skip
    g.write_parquet(CACHE / "game.parquet")

    s = g.group_by("gsis_id", "season").agg(
        pos=c("pos").mode().first(), team=c("team").mode().first(), weeks=pl.len(),
        u_num=c("u_num").sum(), u_den=c("u_den").sum(), e_num=c("e_num").sum(), e_den=c("e_den").sum(), ppr=c("ppr").sum(),
        birth=c("birth_date").drop_nulls().first(), entry=c("entry_year").drop_nulls().first(), pick=c("draft_number").drop_nulls().first(),
    )  # fmt: skip
    s = s.with_columns(age=((pl.date(c("season"), 9, 1) - c("birth")).dt.total_days() / 365.25))
    s = s.with_columns(rank=c("ppr").rank("ordinal", descending=True).over("pos", "season"))

    # mileage from play-by-play (1999+): passing involvements (targets; dropbacks for passers) and rushing (carries)
    pbp = read_part("play", "pbp", list(range(1999, LAST + 1)), None).select(
        "season", "season_type", "passer_player_id", "receiver_player_id", "rusher_player_id", "pass_attempt", "sack", "rush_attempt", "qb_scramble", "two_point_attempt"
    ).collect().filter((c("season_type") == "REG") & (c("two_point_attempt").fill_null(0) == 0))  # fmt: skip
    pas = pl.concat([
        pbp.filter((c("pass_attempt") == 1) | (c("sack") == 1)).select("season", gsis_id="passer_player_id"),
        pass_plays(range(1999, LAST + 1), ros.select("gsis_id", "game_id", "team", "jersey_number")).select("season", gsis_id="rid"),
    ]).drop_nulls().group_by("gsis_id", "season").agg(m_pass=pl.len())  # fmt: skip
    rus = pbp.filter((c("rush_attempt") == 1)).select("season", gsis_id="rusher_player_id").drop_nulls().group_by("gsis_id", "season").agg(m_rush=pl.len())
    mil = pas.join(rus, on=["gsis_id", "season"], how="full", coalesce=True).fill_null(0).sort("gsis_id", "season")
    mil = mil.with_columns(cm_pass=c("m_pass").cum_sum().over("gsis_id"), cm_rush=c("m_rush").cum_sum().over("gsis_id"), first_pbp=c("season").min().over("gsis_id"))
    s = s.join(mil.select("gsis_id", "season", "cm_pass", "cm_rush", "first_pbp"), on=["gsis_id", "season"], how="left")
    s = s.with_columns(c("cm_pass", "cm_rush").forward_fill().over("gsis_id", order_by="season").fill_null(0))
    s.write_parquet(CACHE / "season.parquet")
    print(f"game {g.height:,}, season {s.height:,}")
    print(s.group_by("pos").agg(n=pl.len(), age=c("age").median(), share=(c("u_num") / c("u_den")).median()).sort("pos"))


def load(name: str) -> pl.DataFrame:
    p = CACHE / f"{name}.parquet"
    if not p.exists():
        build()
    return pl.read_parquet(p)


def k_of(game: pl.DataFrame, s: pl.DataFrame, kind: str, pos: str, before: int, min_den=10.0):
    """Noise per attempt over the true spread for a rate (kind 'u' or 'e'), around each position-season mean,
    on seasons before `before`. Returns (sigma2, tau2, k)."""
    ss = s.filter((c("pos") == pos) & (c("season") < before) & (c(f"{kind}_den") >= min_den))
    ps = ss.group_by("season").agg(mu=c(f"{kind}_num").sum() / c(f"{kind}_den").sum())
    ss = ss.join(ps, on="season").with_columns(x=c(f"{kind}_num") / c(f"{kind}_den") - c("mu"), n=c(f"{kind}_den"))
    gg = game.filter((c("pos") == pos) & (c("season") < before) & (c(f"{kind}_den") > 0)).join(ss.select("gsis_id", "season", "mu", rate=c("x") + c("mu"), G="weeks"), on=["gsis_id", "season"])
    gg = gg.with_columns(dev=c(f"{kind}_den") * (c(f"{kind}_num") / c(f"{kind}_den") - c("rate")) ** 2)
    per = gg.group_by("gsis_id", "season").agg(ss_=c("dev").sum(), G=pl.len()).filter(c("G") >= 2)
    sigma2 = float((per["ss_"] / (per["G"] - 1)).mean())
    x, n = ss["x"].to_numpy(), ss["n"].to_numpy()
    w = n / n.sum()
    tau2 = float(np.sum(w * x**2) - sigma2 * np.sum(w / n))
    return sigma2, max(tau2, 1e-12), sigma2 / max(tau2, 1e-12)


def pairs(min_share=0.02, min_def_snaps=100) -> pl.DataFrame:
    """Season s to s+1 rows: centred and pulled usage and efficiency at s (k fit on all seasons up to 2024; the walk-forward
    fits refit k where it matters), next season's centred raw rates, his age, stars, mileage."""
    s = load("season")
    g = load("game")
    allp, curs = [], []
    for pos in OFF + DEF:
        p = s.filter(c("pos") == pos).with_columns(u=pl.when(c("u_den") > 0).then(c("u_num") / c("u_den")), e=pl.when(c("e_den") > 0).then(c("e_num") / c("e_den")))
        inc = p.filter(c("u").is_not_null() & (((c("u") >= min_share) & c("pos").is_in(OFF)) | ((c("u_num") >= min_def_snaps) & c("pos").is_in(DEF))))
        mu_u = inc.group_by("season").agg(mu_u=c("u").mean())
        mu_e = p.filter(c("e_den") >= 10).group_by("season").agg(mu_e=c("e_num").sum() / c("e_den").sum())
        ku = k_of(g, s, "u", pos, LAST + 1)[2]
        ke = k_of(g, s, "e", pos, LAST + 1)[2] if pos in OFF else np.nan
        p = p.join(mu_u, on="season", how="left").join(mu_e, on="season", how="left")
        p = p.with_columns(cu=c("u") - c("mu_u"), ce=c("e") - c("mu_e"),
                           pu=c("u_den") / (c("u_den") + ku) * (c("u") - c("mu_u")),
                           pe=(c("e_den") / (c("e_den") + ke) * (c("e") - c("mu_e"))) if pos in OFF else pl.lit(None, pl.Float64),
                           ku=pl.lit(ku), ke=pl.lit(ke))  # fmt: skip
        allp.append(p)
        curs.append(p.join(inc.select("gsis_id", "season"), on=["gsis_id", "season"]).with_columns(mu_u_next=pl.lit(None, pl.Float64)))
        # next season's mean, for a player who leaves (his usage 0, centred on his position's mean)
        curs[-1] = curs[-1].drop("mu_u_next").join(mu_u.select(season=c("season") - 1, mu_u_next="mu_u"), on="season", how="left")
    P = pl.concat(allp, how="diagonal_relaxed")
    cur = pl.concat(curs, how="diagonal_relaxed").filter(c("season") < LAST)
    # next season, matched by player only (a changed position label isn't a departure); defense usage exists 2013+
    nxt = P.select("gsis_id", season=c("season") - 1, pos2="pos", team2="team", u2=c("u"), cu2=c("cu"), pu2=c("pu"), ce2=c("ce"), pe2=c("pe"), n2="e_den", ud2="u_den")
    d = cur.join(nxt, on=["gsis_id", "season"], how="left")
    d = d.with_columns(gone=c("pos2").is_null(), cu2=pl.coalesce("cu2", -c("mu_u_next")), u2=c("u2").fill_null(0))
    out = [d]
    d = pl.concat(out, how="diagonal_relaxed")
    d = d.with_columns([c(x).fill_nan(None) for x, tp in d.schema.items() if tp == pl.Float64])
    # stars: a top-5 PPR season at his position up to s; never: no top-24 (top-12 QB, TE) season up to s
    s2 = s.sort("gsis_id", "season").with_columns(
        top5=(c("rank") <= 5).cast(pl.Int32).cum_max().over("gsis_id"),
        top24=(c("rank") <= pl.when(c("pos").is_in(["QB", "TE"])).then(12).otherwise(24)).cast(pl.Int32).cum_max().over("gsis_id"))
    d = d.join(s2.select("gsis_id", "season", "top5", "top24"), on=["gsis_id", "season"], how="left")
    d = d.with_columns(star=pl.when(c("top5") == 1).then(pl.lit("star")).when(c("top24") == 0).then(pl.lit("never")).otherwise(pl.lit("middle")),
                       a=c("age").floor().clip(21, 35).cast(pl.Int32))  # fmt: skip
    return d


class Say:
    def __init__(self, path: Path) -> None:
        self.path, self.lines = path, []

    def __call__(self, *t: str) -> None:
        for x in t:
            self.lines.append(x)
            print(x, flush=True)

    def save(self) -> None:
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def boot_gain(f: pl.DataFrame, a: str, b: str, rng, draws: int = 1000, cluster: str = "gsis_id"):
    """Share of b's weighted squared error (y, w) that a removes; players resampled. (gain, 5%, 95%)"""
    e = f.with_columns(ea=c("w") * (c("y") - c(a)) ** 2, eb=c("w") * (c("y") - c(b)) ** 2)
    p = e.group_by(cluster).agg(ea=c("ea").sum(), eb=c("eb").sum())
    ea, eb = p["ea"].to_numpy(), p["eb"].to_numpy()
    idx = rng.integers(0, len(ea), (draws, len(ea)))
    g = 1 - ea[idx].sum(1) / eb[idx].sum(1)
    return float(1 - ea.sum() / eb.sum()), float(np.quantile(g, 0.05)), float(np.quantile(g, 0.95))


def wls(X: np.ndarray, y: np.ndarray, w: np.ndarray, ridge: float = 1e-6) -> np.ndarray:
    W = w / w.sum()
    A = X.T @ (X * W[:, None]) + ridge * np.eye(X.shape[1])
    return np.linalg.solve(A, X.T @ (W * y))


if __name__ == "__main__":
    build()
