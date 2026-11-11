"""pace exploration (2026-11-10): H19, H20, H21, on pass rate over expected (PROE).

PROE on a play is pass (a dropback: passes, sacks, scrambles) minus nflverse's expected pass
chance `xpass`. Regular-season scrimmage plays with an `xpass`, 2006-2024; xpass is in-sample
before 2020 (tag-tables#F4), so the key numbers are repeated on 2020-2024.

H19: is a team's PROE the same across situations? Per team-season, PROE in each slice of a family
(downs, score, win chance, field position, quarter). For two slices, the correlation across
team-seasons, divided by the most it could be given each slice's own noise (the square root of
the two slices' split-half reliabilities, odd against even weeks, Spearman-Brown). 1.0 means the
same trait; 0 means unrelated.

H20: does the odds of winning move pass rate? (a) Play level: mean PROE by win chance band (if
xpass already uses win chance, flat). (b) Game level: a team's dropbacks and pass rate in a game
against its pre-game win chance from the close (no-vig moneyline), beyond its season-to-date PROE.

H21: does recent pass success raise the next game's PROE? Pass success = EPA per dropback and
success rate, last 4 games and season to date, each net of the opponents' season-to-date
average allowed. Against next game's PROE (all plays and neutral), beyond the team's own
season-to-date and last-4 PROE; and beyond schemes-v2's pass_oe_rung2 forecast (2016-2024).

Run from pcf/: PYTHONUTF8=1 .venv/Scripts/python.exe projects/pace/explore/h19_h21_pass.py
"""

# ruff: noqa: E501
from __future__ import annotations

import itertools

import numpy as np
import polars as pl
from common import boot, plays, prior_mean, r2

from pcf.config import get_config

c = pl.col


def slices(p: pl.DataFrame) -> dict[str, pl.Expr]:
    return {
        "downs": pl.when(c("down") == 1).then(pl.lit("1st")).when(c("down") == 2).then(pl.lit("2nd")).when(c("down") == 3).then(pl.lit("3rd")),
        "score": pl.when(c("score_differential") <= -9).then(pl.lit("down 9+")).when(c("score_differential") >= 9).then(pl.lit("up 9+")).otherwise(pl.lit("within 8")),
        "win chance": pl.when(c("wp") < 0.2).then(pl.lit("<20%")).when(c("wp") > 0.8).then(pl.lit(">80%")).otherwise(pl.lit("20-80%")),
        "field": pl.when(c("yardline_100") > 50).then(pl.lit("own half")).when(c("yardline_100") > 20).then(pl.lit("their 21-50")).otherwise(pl.lit("red zone")),
        "quarter": pl.when(c("qtr") <= 4).then(c("qtr").cast(pl.Utf8)),
        "clock": pl.when(c("half_seconds_remaining") <= 120).then(pl.lit("last 2 min")).otherwise(pl.lit("rest of half")),
    }


def h19(p: pl.DataFrame, label: str) -> None:
    print(f"\n=== H19 ({label}): PROE across situations, disattenuated r between slices (1 = same trait)")
    out = []
    for fam, expr in slices(p).items():
        x = p.with_columns(sl=expr).drop_nulls("sl")
        agg = x.group_by("team", "season", "sl", odd=c("week") % 2 == 1).agg(v=c("pass_oe").mean(), n=pl.len())
        half = agg.pivot(on="odd", index=["team", "season", "sl"], values="v")
        rel = {}
        for sl in half["sl"].unique().sort().to_list():
            h = half.filter(c("sl") == sl).drop_nulls()
            r = np.corrcoef(h["true"], h["false"])[0, 1]
            rel[sl] = 2 * r / (1 + r) if r > 0 else np.nan
        full = x.group_by("team", "season", "sl").agg(v=c("pass_oe").mean(), n=pl.len())
        wide = full.pivot(on="sl", index=["team", "season"], values="v")
        n_typ = full.group_by("sl").agg(c("n").median()).sort("sl")
        for a, b in itertools.combinations(sorted(rel), 2):
            w = wide.select(a, b).drop_nulls()
            r = np.corrcoef(w[a], w[b])[0, 1]
            dis = r / np.sqrt(rel[a] * rel[b]) if rel[a] > 0 and rel[b] > 0 else np.nan
            out.append({"family": fam, "a": a, "b": b, "r": round(r, 2), "rel_a": round(rel[a], 2), "rel_b": round(rel[b], 2), "disattenuated": round(dis, 2), "team_seasons": w.height})
        print(fam, "plays per team-season:", dict(zip(n_typ["sl"], n_typ["n"], strict=True)))
    with pl.Config(tbl_rows=60, tbl_width_chars=200):
        print(pl.DataFrame(out))


def h20(p: pl.DataFrame, g: pl.DataFrame, label: str) -> None:
    print(f"\n=== H20 ({label}) (a) play level: mean PROE by win chance band (after xpass)")
    band = (c("wp") * 10).floor().clip(0, 9) / 10
    with pl.Config(tbl_rows=12):
        print(p.filter(c("qtr") <= 4).group_by(band=band).agg(proe=c("pass_oe").mean(), xpass=c("xpass").mean(), plays=pl.len()).sort("band"))
    print(f"\n=== H20 ({label}) (b) game level: dropbacks and pass rate against pre-game win chance")
    d = g.drop_nulls(["win_close", "proe_prior", "dropbacks"])
    for y in ("dropbacks", "pass_rate", "proe_game"):
        base = r2(d[y].to_numpy(), d.select("proe_prior").to_numpy())
        both = r2(d[y].to_numpy(), d.select("proe_prior", "win_close").to_numpy())
        X = np.column_stack([np.ones(d.height), d["proe_prior"], d["win_close"]])
        b = np.linalg.lstsq(X, d[y].to_numpy(), rcond=None)[0]
        print(f"{y}: R2 trait only {base:.3f}, + win chance {both:.3f}; per +10 pts of win chance: {b[2] / 10:+.3f} ({d.height} team-games)")
    q = d.with_columns(wq=(c("win_close") * 5).floor().clip(0, 4) / 5).group_by("wq").agg(
        dropbacks=c("dropbacks").mean(), runs=c("runs").mean(), plays=c("plays").mean(), pass_rate=c("pass_rate").mean(), n=pl.len()).sort("wq")
    print(q)


def h21(g: pl.DataFrame, label: str) -> None:
    print(f"\n=== H21 ({label}): recent pass success against next game's PROE, beyond own PROE history")
    d = g.drop_nulls(["epa_db_adj_last4", "epa_db_adj_prior", "proe_prior", "proe_last4", "proe_game"])
    for y in ("proe_game", "proe_neutral_game"):
        dd = d.drop_nulls(y)
        base = ["proe_prior", "proe_last4"]
        yv = dd[y].to_numpy()
        r0 = r2(yv, dd.select(base).to_numpy())
        for extra in (["epa_db_adj_last4"], ["epa_db_adj_prior"], ["epa_db_adj_last4", "epa_db_adj_prior"], ["sr_db_adj_last4"]):
            r1 = r2(yv, dd.select(*base, *extra).to_numpy())

            def coef(df, extra=extra, y=y):
                X = np.column_stack([np.ones(df.height), *[df[b] for b in base], *[(df[e] - df[e].mean()) / df[e].std() for e in extra]])
                return float(np.linalg.lstsq(X, df[y].to_numpy(), rcond=None)[0][len(base) + 1])

            est, lo, hi = boot(dd.with_columns(blk=c("team") + c("season").cast(pl.Utf8)), coef, by="blk", n=150)
            print(f"{y} + {extra}: R2 {r0:.4f} -> {r1:.4f}; first extra per sd {est * 100:+.2f} pts of PROE (90% {lo * 100:+.2f} to {hi * 100:+.2f})")


def team_games(p: pl.DataFrame) -> pl.DataFrame:
    sc = p.filter(c("scrimmage"))
    off = sc.group_by("game_id", "season", "week", team=c("posteam"), opp=c("defteam")).agg(
        plays=pl.len(),
        dropbacks=(c("pass") == 1).sum(),
        runs=(c("rush") == 1).sum(),
        proe_game=c("pass_oe").mean(),
        proe_neutral_game=c("pass_oe").filter(c("neutral")).mean(),
        epa_db=c("epa").filter(c("pass") == 1).mean(),
        sr_db=c("success").filter(c("pass") == 1).mean(),
        home=(c("posteam") == c("home_team")).first(),
    ).with_columns(pass_rate=c("dropbacks") / c("plays"))
    # opponents' pass defence, season to date (games before this one)
    dfn = off.select("game_id", "season", "week", team=c("opp"), epa_allowed=c("epa_db"), sr_allowed=c("sr_db"))
    dfn = prior_mean(dfn, "epa_allowed", name="opp_epa_allowed")
    dfn = prior_mean(dfn, "sr_allowed", name="opp_sr_allowed")
    off = off.join(dfn.select("game_id", opp=c("team"), opp_epa=c("opp_epa_allowed"), opp_sr=c("opp_sr_allowed")), on=["game_id", "opp"], how="left")
    off = off.with_columns(epa_db_adj=c("epa_db") - c("opp_epa"), sr_db_adj=c("sr_db") - c("opp_sr"))
    for col in ("proe_game", "epa_db_adj", "sr_db_adj"):
        off = prior_mean(off, col, name={"proe_game": "proe_prior"}.get(col, f"{col}_prior"))
        off = prior_mean(off, col, n=4, name={"proe_game": "proe_last4"}.get(col, f"{col}_last4"))
    # pre-game win chance from the close (no-vig moneyline)
    sched = pl.read_parquet(get_config().zone("raw") / "nflverse" / "schedules" / "games.parquet").select("game_id", "home_moneyline", "away_moneyline")

    def imp(ml):
        return pl.when(ml > 0).then(100 / (ml + 100)).otherwise(-ml / (-ml + 100))

    sched = sched.with_columns(hp=imp(c("home_moneyline")), ap=imp(c("away_moneyline"))).with_columns(home_win=c("hp") / (c("hp") + c("ap")))
    off = off.join(sched.select("game_id", "home_win"), on="game_id", how="left").with_columns(
        win_close=pl.when(c("home")).then(c("home_win")).otherwise(1 - c("home_win")))
    return off


def schemes_forecast() -> pl.DataFrame | None:
    from pcf.validation.ledger_score import BACKTESTS
    path = get_config().zone("outputs") / "schemes-v2" / "pass_oe_rung2" / BACKTESTS["schemes-v2/pass_oe_rung2"] / "history.parquet"
    if not path.exists():
        return None
    h = pl.read_parquet(path)
    return h.select("game_id", "team", schemes=c("mean"))


def main() -> None:
    p = plays().filter(c("scrimmage") & c("xpass").is_not_null())
    g = team_games(plays())
    g.write_parquet(get_config().zone("interim") / "pace" / "team_games.parquet")
    h19(p, "2006-2024")
    h19(p.filter(c("season") >= 2020), "2020-2024")
    h20(p, g, "2006-2024")
    h20(p.filter(c("season") >= 2020), g.filter(c("season") >= 2020), "2020-2024")
    h21(g, "2006-2024")
    h21(g.filter(c("season") >= 2020), "2020-2024")
    s = schemes_forecast()
    if s is not None:
        d = g.join(s, on=["game_id", "team"], how="inner").drop_nulls(["schemes", "epa_db_adj_last4", "epa_db_adj_prior", "proe_neutral_game"])
        print(f"\n=== H21 beyond schemes-v2's pass_oe_rung2 forecast ({d.height} team-games, {d['season'].min()}-{d['season'].max()}); target: next game's neutral PROE (schemes' target)")
        y = d["proe_neutral_game"].to_numpy()
        r0 = r2(y, d.select("schemes").to_numpy())
        for extra in (["epa_db_adj_last4"], ["epa_db_adj_prior"]):
            r1 = r2(y, d.select("schemes", *extra).to_numpy())

            def coef(df, extra=extra):
                X = np.column_stack([np.ones(df.height), df["schemes"], (df[extra[0]] - df[extra[0]].mean()) / df[extra[0]].std()])
                return float(np.linalg.lstsq(X, df["proe_neutral_game"].to_numpy(), rcond=None)[0][2])

            est, lo, hi = boot(d.with_columns(blk=c("team") + c("season").cast(pl.Utf8)), coef, by="blk", n=150)
            print(f"+ {extra}: R2 {r0:.4f} -> {r1:.4f}; per sd {est * 100:+.2f} pts (90% {lo * 100:+.2f} to {hi * 100:+.2f})")


if __name__ == "__main__":
    main()
