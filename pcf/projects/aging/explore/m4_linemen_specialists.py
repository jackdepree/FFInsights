"""Aging, a quick look before the brief (2026-11-27): offensive linemen and specialists, and how open careers are.

The CEO, 2026-11-27: "This should forecast for all players not just offense." The exploration covered QB, RB, WR, TE,
DL, LB and DB. Here, the same question for offensive linemen (OL) and specialists (K, P, LS), on snaps:
- **Usage:** his share of his team's snaps on his side (offense for OL, special teams for K, P, LS) over the games he
  was on its roster, from weekly snap counts (2013-2024). A player out of the league next season has a share of 0.
- **The no-age baseline:** his share this season and the two before (0 and a flag when missing) and his years in the
  league; **the age model** adds a cubic in age (standardized at 27). One least-squares fit per position, walk-forward,
  targets 2016-2024; the gain is the share of the baseline's squared error removed, 90% interval from 1,000 resamples
  of players.
- **Still playing:** a logistic on the same inputs, scored by log loss.
- **How open careers are** (all positions, for the rest-of-career target): of the players on a roster in a season, the
  share still on one in 2024, which says how much of each origin's remaining career is still unseen.
Discovery only; the 2025 vault is closed.

Odds, written before the run (Claude, 2026-11-27):
- OL: age adds clearly to next season's snap share: 80%; about +4%, 80% between +1% and +7%. To still playing: 80%.
- Specialists (K, P, LS): age adds clearly to snap share for at least one: 50%; about +2%, 80% between 0 and +5%.
  To still playing for at least one: 55%.

Run from pcf/:  python projects/aging/explore/m4_linemen_specialists.py   (writes m4_linemen_specialists.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent))
from aging_common import Say, _part  # noqa: E402

c = pl.col
RNG = np.random.default_rng(4)
say = Say(Path(__file__).with_suffix(".txt"))
POS = {"OL": "OL", "T": "OL", "G": "OL", "C": "OL", "OT": "OL", "OG": "OL", "K": "K", "P": "P", "LS": "LS"}
SIDE = {"OL": "offense", "K": "st", "P": "st", "LS": "st"}


def table() -> pl.DataFrame:
    S = range(2013, 2025)
    ros = _part("player_game", "roster", ["gsis_id", "game_id", "season", "team", "position", "birth_date", "entry_year"], S).unique(["gsis_id", "game_id"])
    sn = _part("player_game", "snaps", ["gsis_id", "game_id", "offense_snaps", "offense_pct", "st_snaps", "st_pct"], S).unique(["gsis_id", "game_id"])
    g = ros.join(sn, on=["gsis_id", "game_id"], how="left")
    tm = g.group_by("team", "game_id").agg(t_off=(c("offense_snaps") / c("offense_pct")).filter(c("offense_pct") > 0.5).median().round(),
                                           t_st=(c("st_snaps") / c("st_pct")).filter(c("st_pct") > 0.2).median().round())
    g = g.join(tm, on=["team", "game_id"], how="left").with_columns(pos=c("position").replace_strict(POS, default=None))
    g = g.with_columns(num=pl.when(c("pos") == "OL").then(c("offense_snaps")).otherwise(c("st_snaps")).fill_null(0),
                       den=pl.when(c("pos") == "OL").then(c("t_off")).otherwise(c("t_st")))
    s = g.group_by("gsis_id", "season").agg(pos=c("pos").mode().first(), num=c("num").sum(), den=c("den").sum(),
                                            birth=c("birth_date").drop_nulls().first(), entry=c("entry_year").drop_nulls().first())
    s = s.with_columns(age=((pl.date(c("season"), 9, 1) - c("birth")).dt.total_days() / 365.25), u=c("num") / c("den"))
    return s


def design(x, age):
    cols = [np.ones(x.height), x["u"].to_numpy(), x["l1"].fill_null(0).to_numpy(), x["l2"].fill_null(0).to_numpy(),
            x["l1"].is_null().to_numpy().astype(float), x["l2"].is_null().to_numpy().astype(float),
            (x["season"] - x["entry"]).fill_null(0).to_numpy().astype(float)]
    if age:
        z = (x["age"].clip(21, 40).to_numpy() - 27) / 5
        cols += [z, z**2, z**3]
    return np.column_stack(cols).astype(float)


def boot(err0, err1, ids):
    u, inv = np.unique(ids, return_inverse=True)
    a, b = np.bincount(inv, err1), np.bincount(inv, err0)
    idx = RNG.integers(0, len(u), (1000, len(u)))
    g = 1 - a[idx].sum(1) / b[idx].sum(1)
    return 1 - a.sum() / b.sum(), np.quantile(g, 0.05), np.quantile(g, 0.95)


def main() -> None:
    s = table()
    allp = s.select("gsis_id", "season")
    lag = s.select("gsis_id", "season", "u")
    p = (s.filter(c("pos").is_not_null() & c("age").is_not_null() & (c("num") > 0) & (c("season") < 2024))
         .join(lag.select("gsis_id", season=c("season") + 1, l1="u"), on=["gsis_id", "season"], how="left")
         .join(lag.select("gsis_id", season=c("season") + 2, l2="u"), on=["gsis_id", "season"], how="left")
         .join(s.select("gsis_id", season=c("season") - 1, y="u"), on=["gsis_id", "season"], how="left")
         .join(allp.with_columns(on=pl.lit(True)).select("gsis_id", season=c("season") - 1, on="on"), on=["gsis_id", "season"], how="left")
         .with_columns(gone=c("on").is_null(), y=c("y").fill_null(0).fill_nan(0), T=c("season") + 1))
    say("# Linemen and specialists, and how open careers are (2026-11-27)", "",
        f"Player-seasons with snaps on their side, 2013-2023 origins: {p.height:,}.", "",
        "| Position | Pairs | Next-season share: age against no age | Still playing (log loss): age against no age | Still playing next season, under 30 / 30+ |",
        "|---|---|---|---|---|")
    res = {}
    for pos in ["OL", "K", "P", "LS"]:
        x = p.filter(c("pos") == pos)
        e0, e1, l0, l1, ids = [], [], [], [], []
        for T in range(2016, 2025):
            tr, te = x.filter(c("T") < T), x.filter(c("T") == T)
            if te.height == 0:
                continue
            for age, eo, lo in ((False, e0, l0), (True, e1, l1)):
                A, B = design(tr, age), design(te, age)
                mu, sd = A[:, 1:].mean(0), A[:, 1:].std(0) + 1e-9
                A[:, 1:], B[:, 1:] = (A[:, 1:] - mu) / sd, np.clip((B[:, 1:] - mu) / sd, -5, 5)
                b = np.linalg.lstsq(A, tr["y"].to_numpy(), rcond=None)[0]
                eo.append((te["y"].to_numpy() - B @ b) ** 2)
                m = LogisticRegression(C=1.0, max_iter=2000).fit(A[:, 1:], tr["gone"].to_numpy())
                q = np.clip(m.predict_proba(B[:, 1:])[:, 1], 1e-4, 1 - 1e-4)
                gz = te["gone"].to_numpy().astype(float)
                lo.append(-(gz * np.log(q) + (1 - gz) * np.log(1 - q)))
            ids.append(te["gsis_id"].to_numpy())
        ids = np.concatenate(ids)
        gu = boot(np.concatenate(e0), np.concatenate(e1), ids)
        gs = boot(np.concatenate(l0), np.concatenate(l1), ids)
        res[pos] = (gu, gs)
        young, old = x.filter(c("age") < 30), x.filter(c("age") >= 30)
        say(f"| {pos} | {x.height:,} | {gu[0]:+.2%} ({gu[1]:+.2%} to {gu[2]:+.2%}) | {gs[0]:+.2%} ({gs[1]:+.2%} to {gs[2]:+.2%}) | "
            f"{1 - young['gone'].mean():.0%} / {1 - old['gone'].mean():.0%} |")

    # how open careers are, all positions (rosters 2002-2024)
    r = _part("player_game", "roster", ["gsis_id", "season"], range(2002, 2025)).unique(["gsis_id", "season"])
    last = r.group_by("gsis_id").agg(last=c("season").max())
    say("", "**How open careers are** (every rostered player): the share of a season's players still on a roster in 2024, and their mean seasons seen after it.", "",
        "| Origin season | Players | Still on a roster in 2024 | Seasons seen after it, mean |", "|---|---|---|---|")
    for o in (2006, 2010, 2014, 2016, 2018, 2020, 2022):
        x = r.filter(c("season") == o).join(last, on="gsis_id")
        seen = r.join(x.select("gsis_id"), on="gsis_id").filter(c("season") > o).group_by("gsis_id").agg(n=pl.len())
        mean_seen = x.select("gsis_id").join(seen, on="gsis_id", how="left")["n"].fill_null(0).mean()
        say(f"| {o} | {x.height:,} | {(x['last'] == 2024).mean():.1%} | {mean_seen:.2f} |")

    ol, sp = res["OL"], [res[k] for k in ("K", "P", "LS")]
    say("", f"Bets: OL share {'held' if ol[0][1] > 0 else 'failed'}; OL still playing {'held' if ol[1][1] > 0 else 'failed'}; "
        f"specialists' share (1+) {'held' if any(v[0][1] > 0 for v in sp) else 'failed'}; specialists still playing (1+) {'held' if any(v[1][1] > 0 for v in sp) else 'failed'}.")
    say.save()


if __name__ == "__main__":
    main()
