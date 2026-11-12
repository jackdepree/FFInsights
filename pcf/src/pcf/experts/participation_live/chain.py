"""Reconstructing a game: the on-field chances along each team's snaps, and the best guess.

**The chances** (`infer`). Each part-time player's on/off along his side's snaps is a chain with
two snaps of memory (the model's transition chances). The pins are evidence: a named player was
on. Every play must have 11 and every player his snap count, so each snap gets an offset `a_t`
and each player an offset `b_j`, added to the log-odds of being on. Given the offsets the
players' chains are independent, and forward-backward gives each cell's chance; the offsets are
then moved until both totals hold (the closest distribution to the model's that meets them:
iterative proportional fitting with a sequence in it, the brief's two analogies at once).
Players on every snap are fixed at 1 and left out.

**The best guess** (`best_guess`). The 11 per play that make the chances most likely, with
each player's total within a play of his snap target (participation-live#F7: each play's top
picks miss the totals by 7.8 plays), and each play's count of backs, tight ends, receivers and
the rest at what its chances add to. It's an assignment over the whole game, solved exactly as a
linear program (the constraints are a network, so the answer is whole players). `likeliest` is
the same without the totals: each play's own likeliest 11.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy.optimize import linprog, minimize
from scipy.sparse import csr_matrix, hstack, identity, vstack

from pcf.experts.participation_live.grid import SIDE_KEYS
from pcf.experts.participation_live.model import OnFieldModel, cell_arrays, memory

c = pl.col
TOLERANCE = 1e-3  # players: how far a total may be from its target
MAX_STEPS = 500
CHUNK = 120  # team-game-sides solved together
SLACK_COST = 50.0  # per play a best-guess total is off its snap target (rare: infeasible tables)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(x, -30, 30)))


def _forward_backward(p1: np.ndarray, theta: np.ndarray, allow_off: np.ndarray, real: np.ndarray):
    """(marginals of on (B, T, J), log normalisers (B, J)). p1: (B, T, J, 2, 2) chance on given
    (u, v); theta: (B, T, J) offsets; allow_off: (B, T, J) False where the cell is pinned on;
    real: (B, T, J) True for real cells. Padded players are forced off; padded snaps add nothing."""
    B, T, J = theta.shape
    e = np.exp(np.clip(theta, -30, 30))
    psi = np.empty((B, T, J, 2, 2, 2))
    psi[..., 1] = p1 * e[..., None, None]
    psi[..., 0] = (1 - p1) * allow_off[..., None, None]
    pad_t = ~real.any(axis=2)  # (B, T): snaps past this table's end
    psi[pad_t] = 1.0
    alpha = np.empty((B, T, J, 2, 2))
    a = np.zeros((B, J, 2, 2))
    a[:, :, 0, :] = psi[:, 0, :, 0, 0, :]  # before the game: (u, v) = (0, 0), start flags on
    z = a.sum(axis=(2, 3), keepdims=True) + 1e-300
    log_z = np.log(z[..., 0, 0])
    a /= z
    alpha[:, 0] = a
    for t in range(1, T):
        a = np.einsum("bjuv,bjuvw->bjvw", a, psi[:, t])
        z = a.sum(axis=(2, 3), keepdims=True) + 1e-300
        log_z += np.where(pad_t[:, t, None], 0.0, np.log(z[..., 0, 0]))
        a /= z
        alpha[:, t] = a
    marg = np.empty((B, T, J))
    b = np.ones((B, J, 2, 2))
    for t in range(T - 1, -1, -1):
        if t < T - 1:
            b = np.einsum("bjuvw,bjvw->bjuv", psi[:, t + 1], b)
            b /= b.sum(axis=(2, 3), keepdims=True) + 1e-300
        g = alpha[:, t] * b
        marg[:, t] = g[..., 1].sum(-1) / (g.sum(axis=(2, 3)) + 1e-300)
    return np.where(real, marg, 0.0), log_z


def _solve(p1, allow_off, real, rows, cols, tol=TOLERANCE):
    """Offsets so each snap's chances add to `rows` (B, T) and each player's to `cols` (B, J):
    the minimum of the convex dual (the players' log normalisers minus the offsets times the
    targets), whose gradient is the chances' totals minus the targets. Offsets are kept within
    ±20, so a target that can't be met (more pins than his snaps) is met as nearly as it can be."""
    B, T, J = real.shape
    col_real = real.any(axis=1)

    def dual(x):
        a = x[: B * T].reshape(B, T)
        b = x[B * T :].reshape(B, J)
        m, log_z = _forward_backward(p1, a[:, :, None] + b[:, None, :], allow_off, real)
        f = log_z[col_real].sum() - (a * rows).sum() - (b * cols).sum()
        grad = np.concatenate([(m.sum(2) - rows).ravel(), (m.sum(1) - cols).ravel()])
        return f, grad

    res = minimize(
        dual,
        np.zeros(B * (T + J)),
        jac=True,
        method="L-BFGS-B",
        bounds=[(-20, 20)] * (B * (T + J)),
        options={"maxiter": MAX_STEPS, "gtol": tol, "maxcor": 20},
    )
    a = res.x[: B * T].reshape(B, T)
    b = res.x[B * T :].reshape(B, J)
    return _forward_backward(p1, a[:, :, None] + b[:, None, :], allow_off, real)[0]


def infer(g: pl.DataFrame, model: OnFieldModel) -> pl.DataFrame:
    """The grid (with the model's cell columns) plus `p`, each cell's on-field chance."""
    g = g.sort(*SIDE_KEYS, "gsis_id", "n")
    part = g.filter(~c("full"))
    full = g.filter(c("full")).select(*SIDE_KEYS, "gsis_id", "play_id").with_columns(p=pl.lit(1.0))
    base = model.base_logit(part)
    wm = model.memory_weights(part)
    cells = cell_arrays(part)
    logits = {}
    for u in (0, 1):
        for v in (0, 1):
            logits[(u, v)] = base + (memory(cells, u, v) * wm).sum(1)
    part = part.with_columns(
        tb=pl.struct(SIDE_KEYS).rank("dense") - 1,
    )
    part = part.with_columns(j=c("gsis_id").rank("dense").over("tb") - 1)
    nfull = g.group_by(SIDE_KEYS).agg(nfull=c("gsis_id").filter(c("full")).n_unique())
    part = part.join(nfull, on=SIDE_KEYS, how="left")
    tb = part["tb"].to_numpy()
    jj = part["j"].to_numpy().astype(np.int64)
    tt = part["n"].to_numpy().astype(np.int64)
    named = part["named"].to_numpy()
    share = part["share"].to_numpy()
    nf = part["nfull"].to_numpy()
    n_plays = part["n_plays"].to_numpy()
    p_out = np.zeros(part.height)
    tables = np.unique(tb)
    for lo in range(0, len(tables), CHUNK):
        chunk = tables[lo : lo + CHUNK]
        sel = np.where((tb >= chunk[0]) & (tb <= chunk[-1]))[0]
        bi = tb[sel] - chunk[0]
        B, T, J = len(chunk), int(tt[sel].max()) + 1, int(jj[sel].max()) + 1
        real = np.zeros((B, T, J), bool)
        real[bi, tt[sel], jj[sel]] = True
        allow_off = np.ones((B, T, J), bool)
        allow_off[bi, tt[sel], jj[sel]] = ~named[sel]
        p1 = np.zeros((B, T, J, 2, 2))
        for (u, v), lg in logits.items():
            p1[bi, tt[sel], jj[sel], u, v] = _sigmoid(lg[sel])
        snaps_real = real.any(axis=2)
        rows = np.zeros((B, T))
        rows[bi, tt[sel]] = np.maximum(11 - nf[sel], 0)
        rows = np.where(snaps_real, rows, 0.0)
        cols = np.zeros((B, J))
        cols[bi, jj[sel]] = share[sel] * n_plays[sel]
        # the part-timers' targets add to the snaps' (the snap counts can be a play or two off)
        pinned_col = np.zeros((B, J))
        np.add.at(pinned_col, (bi, jj[sel]), named[sel].astype(float))
        n_real = np.zeros((B, J))
        np.add.at(n_real, (bi, jj[sel]), 1.0)
        scale = rows.sum(1) / np.maximum(cols.sum(1), 1e-9)
        cols = np.clip(cols * scale[:, None], pinned_col, n_real)
        m = _solve(p1, allow_off, real, rows, cols)
        p_out[sel] = m[bi, tt[sel], jj[sel]]
    part = part.with_columns(p=pl.Series(p_out)).select(*SIDE_KEYS, "gsis_id", "play_id", "p")
    out = pl.concat([part, full])
    return g.join(out, on=[*SIDE_KEYS, "gsis_id", "play_id"], how="left")


def _assign(
    logit: np.ndarray,
    rows: np.ndarray,
    lo: np.ndarray | None,
    hi: np.ndarray | None,
    group: np.ndarray | None = None,
    glo: np.ndarray | None = None,
    ghi: np.ndarray | None = None,
) -> np.ndarray:
    """0/1 on an (T, J) table of open cells (logit = -inf where not open), the sum of logits
    most, with:
    - each row adding to `rows`;
    - each column between `lo` and `hi` (with a costly slack), unless they're None;
    - each row's count of each group (`group[j]` in 0..G-1) between `glo` and `ghi` (T, G).
    The play and play-group sums nest, and the column sums are disjoint, so the matrix is a
    network's and the answer is whole players."""
    T, J = logit.shape
    ti, ji = np.where(np.isfinite(logit))
    n = len(ti)
    cols = lo is not None
    ns = 2 * J if cols else 0
    cost = np.concatenate([-logit[ti, ji], np.full(ns, SLACK_COST)])
    a_row = csr_matrix((np.ones(n), (ti, np.arange(n))), shape=(T, n))
    a_eq = hstack([a_row, csr_matrix((T, ns))])
    ub, b_ub = [], []
    if cols:
        a_col = csr_matrix((np.ones(n), (ji, np.arange(n))), shape=(J, n))
        eye = identity(J, format="csr")
        # col + s_minus - s_plus within [lo, hi]
        upper = hstack([a_col, eye, -eye])
        ub += [upper, -upper]
        b_ub += [hi, -lo]
    if group is not None:
        G = glo.shape[1]
        r = ti * G + group[ji]
        a_g = hstack([csr_matrix((np.ones(n), (r, np.arange(n))), shape=(T * G, n)),
                      csr_matrix((T * G, ns))])  # fmt: skip
        ub += [a_g, -a_g]
        b_ub += [ghi.ravel(), -glo.ravel()]
    bounds = [(0, 1)] * n + [(0, None)] * ns
    res = linprog(
        cost,
        A_ub=vstack(ub) if ub else None,
        b_ub=np.concatenate(b_ub) if b_ub else None,
        A_eq=a_eq,
        b_eq=rows,
        bounds=bounds,
        method="highs",
    )
    out = np.zeros((T, J), bool)
    if res.status != 0:
        # each snap's most likely open players (only if the program can't be solved)
        for t in range(T):
            k = int(rows[t])
            if k > 0:
                out[t, np.argsort(-np.where(np.isfinite(logit[t]), logit[t], -1e9))[:k]] = True
        return out & np.isfinite(logit)
    out[ti, ji] = res.x[:n] > 0.5
    return out


def _apportion(expect: np.ndarray, rows: np.ndarray, avail: np.ndarray) -> np.ndarray:
    """Whole counts per (play, group): each the floor or the ceiling of its expected count
    (never above the players available), each play's adding to `rows`, and each group's game
    total its expected total, rounded (controlled rounding). Rounding each play alone would put
    a team's only tight end, 60% likely on every snap, on all of them. Among the roundings that
    meet both, the cells rounded up are the ones with the largest fractions. It's a transport
    problem (plays by groups), so the answer is whole."""
    T, G = expect.shape
    base = np.minimum(np.floor(expect + 1e-6), avail)
    frac = expect - base
    up_ok = base < avail
    ti, gi = np.where(up_ok)
    n = len(ti)
    need = rows - base.sum(1)
    col = np.round(expect.sum(0)) - base.sum(0)
    if n == 0:
        return base
    # rounding a cell up costs 1 - its fraction (whole cells cost more), group totals have slack
    cost = np.concatenate([1.0 - np.where(frac[ti, gi] > 1e-6, frac[ti, gi], -1.0),
                           np.full(2 * G, SLACK_COST)])  # fmt: skip
    a_row = csr_matrix((np.ones(n), (ti, np.arange(n))), shape=(T, n))
    a_col = csr_matrix((np.ones(n), (gi, np.arange(n))), shape=(G, n))
    eye = identity(G, format="csr")
    a_eq = vstack([hstack([a_row, csr_matrix((T, 2 * G))]), hstack([a_col, eye, -eye])])
    b_eq = np.concatenate([np.clip(need, 0, None), col])
    res = linprog(
        cost, A_eq=a_eq, b_eq=b_eq, bounds=[(0, 1)] * n + [(0, None)] * (2 * G), method="highs"
    )
    if res.status != 0:
        return np.minimum(np.round(expect), avail)
    out = base.copy()
    out[ti, gi] += res.x[:n] > 0.5
    return out


def best_guess(g: pl.DataFrame, totals: bool = True, mix: bool = True) -> pl.DataFrame:
    """The inferred grid (`p`) plus `best`: the pinned players and, per play, the open players
    of one assignment over the game. Every play gets 11 when it has enough candidates.
    - `totals`: each player's total within a play of his snap target (the snap-matched guess);
      without it, each play's likeliest players (participation-live#R3).
    - `mix`: each play's count of each position group fixed at its expected count (what the
      group's chances on the play add to), rounded by largest remainders so they add to 11.
      Without it, plays come out with no back or no tight end far more often than they really
      do, and the personnel is right on 35% of plays instead of 63% (participation-live#R4).
      Bounds of a step either side (floor and ceiling) reached only 44%."""
    g = g.sort(*SIDE_KEYS, "gsis_id", "n")
    out = []
    for _, d in g.group_by(SIDE_KEYS, maintain_order=True):
        players = d["gsis_id"].unique(maintain_order=True).to_list()
        pj = {p: j for j, p in enumerate(players)}
        t = d["n"].to_numpy().astype(np.int64)
        j = np.array([pj[x] for x in d["gsis_id"].to_list()])
        T, J = int(t.max()) + 1, len(players)
        pinned = np.zeros((T, J), bool)
        pinned[t, j] = d["pinned"].to_numpy()
        p = np.clip(d["p"].to_numpy(), 1e-6, 1 - 1e-6)
        logit = np.full((T, J), -np.inf)
        open_ = ~d["pinned"].to_numpy()
        logit[t[open_], j[open_]] = np.log(p[open_] / (1 - p[open_]))
        n_open = np.isfinite(logit).sum(1)
        rows = np.clip(11 - pinned.sum(1), 0, n_open).astype(float)
        lo = hi = None
        if totals:
            target = np.zeros(J)
            target[j] = d["share"].to_numpy() * d["n_plays"].to_numpy()
            target = target * (11 * T) / max(target.sum(), 1e-9)  # the totals add to 11 a play
            left = target - pinned.sum(0)
            avail = np.isfinite(logit).sum(0)
            lo = np.clip(np.floor(left), 0, avail)
            hi = np.clip(np.ceil(left), 0, avail)
        grp = glo = ghi = None
        if mix:
            names = d.select("gsis_id", c("group").fill_null("OTHER")).unique(
                "gsis_id", maintain_order=True
            )
            gmap = {x: i for i, x in enumerate(sorted(set(names["group"].to_list())))}
            grp = np.zeros(J, np.int64)
            grp[[pj[x] for x in names["gsis_id"].to_list()]] = [gmap[x] for x in names["group"]]
            G = len(gmap)
            expect = np.zeros((T, G))
            avail_g = np.zeros((T, G))
            np.add.at(expect, (t[open_], grp[j[open_]]), p[open_])
            np.add.at(avail_g, (t[open_], grp[j[open_]]), 1.0)
            glo = ghi = _apportion(expect, rows, avail_g)
        pick = _assign(logit, rows, lo, hi, grp, glo, ghi) | pinned
        out.append(
            d.select(*SIDE_KEYS, "gsis_id", "play_id").with_columns(best=pl.Series(pick[t, j]))
        )
    return g.join(pl.concat(out), on=[*SIDE_KEYS, "gsis_id", "play_id"], how="left")


def likeliest(g: pl.DataFrame, mix: bool = True) -> pl.DataFrame:
    """The inferred grid (`p`) plus `likeliest`: each play's likeliest 11 (the pinned players
    and the open ones with the highest chances, within the play's position mix). The most right
    per play on average, but each player's total drifts from his snaps (participation-live#R3)."""
    return best_guess(g, totals=False, mix=mix).rename({"best": "likeliest"})
