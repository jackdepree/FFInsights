# ruff: noqa: E501
"""skill-over-expected's build: the backlog ideas run beside the ladder (decision 0051, calls 26-27).

- I76, the movers model: a player part and a team part of each trait (two-way fixed effects on
  player-seasons, weighted by chances; players and franchises, identified by the movers). The
  plain fit overstates the parts' spread (noise), so each part's spread is read as the covariance
  of the parts fit on odd weeks and on even weeks apart (a split-sample correction: the halves'
  noise is independent). Shares of the rate's true spread: player, team, and twice their
  covariance.
- I112, the QB's after-pressure part as a forecast of next season's sacks per dropback
  (context-retro's walk-forward player_game, run 7ca46aa8), on the old provider's seasons only
  (inputs 2017-2022; context-retro#R13), against his plain (shrunk) sack rate.

Run from pcf/:  python projects/skill-over-expected/build/ideas.py > projects/skill-over-expected/build/ideas.txt
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy.sparse import csr_matrix, hstack
from scipy.sparse.linalg import lsqr

from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.skill_over_expected import data as D
from pcf.experts.skill_over_expected import evaluate as E
from pcf.experts.skill_over_expected import run as R
from pcf.experts.skill_over_expected import traits as T

c = pl.col
SEED = get_config().seed
CTX = get_config().zone("outputs") / "context-retro" / "7ca46aa82fe344b98e6fd1e0c534260c" / "player_game.parquet"


def qb_cpoe() -> pl.DataFrame:
    """QB completion over expected per attempt, per game (for I76's first bet), long format."""
    out = []
    for s in D.SEASONS:
        v = Gateway(TableSource(seasons=[s])).view(END_OF_TIME, "retrospective", {"play": ("pbp",)})
        p = v.table("play", seasons=[s]).filter((c("season_type") == "REG") & (c("pass_attempt") == 1)
                                                 & (c("sack") == 0) & c("cp").is_not_null())
        g = p.drop_nulls("passer_player_id").group_by(
            gsis_id="passer_player_id", game_id="game_id", season="season", week="week", team="posteam"
        ).agg(num=(c("complete_pass") - c("cp")).sum(), den=pl.len().cast(pl.Float64))
        out.append(g.with_columns(trait=pl.lit("qb_cpoe")).select(D.COLS))
    return pl.concat(out)


def fe_parts(rows: pl.DataFrame) -> dict | None:
    """Two-way fixed effects on centred rates (x), weighted by den: player and team effects."""
    pid, pinv = np.unique(rows["gsis_id"].to_numpy(), return_inverse=True)
    tid, tinv = np.unique(rows["team"].to_numpy(), return_inverse=True)
    n = rows.height
    P = csr_matrix((np.ones(n), (np.arange(n), pinv)), shape=(n, len(pid)))
    Tm = csr_matrix((np.ones(n), (np.arange(n), tinv)), shape=(n, len(tid)))
    X = hstack([P, Tm]).tocsr()
    w = np.sqrt(rows["den"].to_numpy())
    y = rows["x"].to_numpy()
    b = lsqr(X.multiply(w[:, None]).tocsr(), y * w, atol=1e-10, btol=1e-10, iter_lim=5000)[0]
    a, psi = b[: len(pid)], b[len(pid):]
    return {"alpha": dict(zip(pid, a, strict=True)), "psi": dict(zip(tid, psi, strict=True))}


def connected(rows: pl.DataFrame) -> pl.DataFrame:
    """Rows of players and teams in the largest set linked by movers (union-find)."""
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p, t in rows.select("gsis_id", "team").iter_rows():
        ra, rb = find("p" + p), find("t" + t)
        if ra != rb:
            parent[ra] = rb
    roots = rows.select(root=pl.Series([find("t" + t) for t in rows["team"]]))
    r = rows.with_columns(roots)
    big = r["root"].value_counts().sort("count", descending=True)["root"][0]
    return r.filter(c("root") == big).drop("root")


def halves_rows(games: pl.DataFrame, rows: pl.DataFrame, trait: str, parity: int) -> pl.DataFrame:
    g = games.filter((c("trait") == trait) & (c("week") % 2 == parity))
    h = g.group_by("gsis_id", "season").agg(c("num").sum(), c("den").sum()).filter(c("den") > 0)
    h = h.join(rows.select("gsis_id", "season", "team", "mu"), on=["gsis_id", "season"])
    return h.with_columns(x=c("num") / c("den") - c("mu"))


def movers_model(games: pl.DataFrame, rows: pl.DataFrame, trait: str) -> dict:
    rows = connected(rows)
    full = fe_parts(rows)
    odd = fe_parts(halves_rows(games, rows, trait, 1))
    even = fe_parts(halves_rows(games, rows, trait, 0))
    r = rows.with_columns(
        a_o=c("gsis_id").replace_strict(odd["alpha"], default=None),
        a_e=c("gsis_id").replace_strict(even["alpha"], default=None),
        t_o=c("team").replace_strict(odd["psi"], default=None),
        t_e=c("team").replace_strict(even["psi"], default=None),
        a=c("gsis_id").replace_strict(full["alpha"], default=None),
        t=c("team").replace_strict(full["psi"], default=None),
    ).drop_nulls(["a_o", "a_e", "t_o", "t_e"])
    w = r["den"].to_numpy() / r["den"].sum()

    def cov(u, v):
        u, v = r[u].to_numpy(), r[v].to_numpy()
        return float(np.sum(w * (u - np.sum(w * u)) * (v - np.sum(w * v))))

    va, vt = cov("a_o", "a_e"), cov("t_o", "t_e")
    cat = (cov("a_o", "t_e") + cov("a_e", "t_o")) / 2
    tot = va + vt + 2 * cat
    plain = cov("a", "a") / (cov("a", "a") + cov("t", "t") + 2 * cov("a", "t"))
    return {"rows": r.height, "players": r["gsis_id"].n_unique(), "teams": r["team"].n_unique(),
            "movers": int(rows.group_by("gsis_id").agg(c("team").n_unique())["team"].gt(1).sum()),
            "player": va / tot, "team": vt / tot, "both": 2 * cat / tot, "plain_player": plain,
            "va": va, "vt": vt}


def i76(d: dict) -> None:
    print("== I76, the movers model (two-way fixed effects, players and franchises; split-sample corrected shares of the true spread)")
    games = pl.concat([d["games"], qb_cpoe()])
    cp = T.Trait("qb_cpoe", "completion over expected per attempt", ("QB",), "qb_sack_rate", 150, "attempt")
    T.BY_NAME["qb_cpoe"] = cp
    todo = [(cp, "QB"), *[(T.BY_NAME[n], g) for n, g in (
        ("qb_sack_rate", "QB"), ("qb_depth", "QB"), ("qb_ttt", "QB"), ("press_rate", "DL"), ("press_rate", "OLB"),
        ("catch_rate", "WR"), ("rb_yac", "RB"), ("rb_multi_after", "RB"), ("depth_against", "DB"),
        ("catch_allowed", "DB"), ("ol_press_rate", "OL"), ("ol_sack_rate", "OL"))]]
    for t, g in todo:
        rows = T.season_rows(games, d["teams"], t).filter(c("group") == g)
        m = movers_model(games, rows, t.name)
        print(f"  {t.name:15} {g:3}: {m['rows']} player-seasons, {m['players']} players ({m['movers']} who moved), {m['teams']} teams; "
              f"shares of the true spread: player {100 * m['player']:.0f}%, team {100 * m['team']:.0f}%, together {100 * m['both']:+.0f}%; "
              f"the plain fit's player share {100 * m['plain_player']:.0f}%")


def i112(d: dict) -> None:
    print("\n== I112: the QB's after-pressure part (context-retro, walk-forward) against his plain sack rate, next season's sacks per dropback; inputs 2017-2022")
    ctx = pl.read_parquet(CTX).filter((c("role") == "passer") & (c("season_type") == "REG"))
    ap = ctx.group_by("gsis_id", "season").agg(after=c("after_part").sum() / c("dropbacks").sum())
    rows = T.season_rows(d["games"], d["teams"], T.BY_NAME["qb_sack_rate"]).filter(c("group") == "QB")
    p = T.rungs(T.pairs(rows, d["games"])).join(ap, on=["gsis_id", "season"], how="inner")
    p = p.filter(c("season").is_between(2017, 2022)).with_columns(c("after") - c("after").mean().over("season"))
    s, y, w = p["season"].to_numpy(), p["y"].to_numpy(), p["w"].to_numpy()
    fc = {k: np.full(p.height, np.nan) for k in ("plain", "after", "both")}
    X = {"plain": [p["m1"].to_numpy()], "after": [p["after"].to_numpy()], "both": [p["m1"].to_numpy(), p["after"].to_numpy()]}
    for t in np.unique(s):
        tr = s < t
        if tr.sum() < 30:
            continue
        for k, cols in X.items():
            M = np.column_stack(cols)
            fc[k][s == t] = M[s == t] @ T._wls(M[tr], y[tr], w[tr])
    p = p.with_columns(**{k: pl.Series(v).fill_nan(None) for k, v in fc.items()}).drop_nulls("plain")
    for label, q in (("all", p), ("movers", p.filter(c("moved"))), ("stayers", p.filter(~c("moved")))):
        print(f"  {label} ({q.height} QB-seasons, targets {q['season'].min() + 1}-{q['season'].max() + 1}): the after-pressure part alone against the plain rate "
              f"{E.fmt(E.gain(q, 'after', 'plain', SEED))}; both against the plain rate {E.fmt(E.gain(q, 'both', 'plain', SEED))}")


def main() -> None:
    d = D.load()
    d["teams"] = T.regroup(d["teams"], R.roles())  # decision 0051 call 31
    i76(d)
    i112(d)


if __name__ == "__main__":
    main()
