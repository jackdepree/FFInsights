"""Availability's fitted pieces, shared by the variants (decision 0047).

- `TableModel`: rung 0, a rate per cell with each cell shrunk toward its parent.
- `fit_logistic`, `fit_lasso_logistic`, `fit_trees`: rung 1 and 3 classifiers.
- `TwoPart`: method 1 for a window's health absences: the chance of any, times the games if any,
  with the games' spread read from the training rows' own (by size of prediction).
- `Chain`: method 2, a weekly health-state chain: one multinomial model per state for the next
  game's state, an emission model for "absent given the state", rolled forward exactly.
- `Hmm`: method 3, a hidden health state read from the report, practice and snaps.
- `distribution_summary`: mean, quantiles and the spike parts of a count's distribution.

Training rows are a walk's pool: every row predicted before the cutoff with its outcome known.
The chain and the hidden state learn moves from consecutive rows of one player (`next_pairs`):
a row's next state is the state shown by his row at his team's next game, which was predicted
(and so known) before the cutoff, or `f` if he was on no roster that week.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

c = pl.col
HOLDOUT = 0.2  # the latest share of a training pool, for choosing a penalty or a spread
C_GRID = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0)
TREES = {"max_iter": 200, "learning_rate": 0.06, "max_leaf_nodes": 15, "min_samples_leaf": 80,
         "random_state": 0}  # fmt: skip
LEVELS = np.linspace(0.01, 0.99, 99)
BINS = np.array([0.05, 0.15, 0.3, 0.5, 0.75])
MIN_BIN = 40
NEXT_STATES = ("h", "l", "o", "r", "f")
D_MAX = 4  # weeks-in-state buckets: 1, 2, 3, 4+
EPS = 1e-6


# ---------------------------------------------------------------- small pieces
class Constant:
    def __init__(self, p: float):
        self.p = float(p)

    def predict_proba(self, x):
        return np.column_stack([np.full(len(x), 1 - self.p), np.full(len(x), self.p)])


def fit_logistic(x: np.ndarray, y: np.ndarray, w: np.ndarray, C: float = 1.0):
    if len(np.unique(y)) < 2:
        return Constant(float(y.mean()) if len(y) else 0.0)
    m = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000))
    return m.fit(x, y, logisticregression__sample_weight=w)


def _holdout(order: np.ndarray) -> np.ndarray:
    """The latest HOLDOUT share of rows by `order` (e.g. as_of): a time-ordered inner split."""
    cut = np.quantile(order, 1 - HOLDOUT)
    return order >= cut


def log_loss(p: np.ndarray, y: np.ndarray, w: np.ndarray | None = None) -> float:
    p = np.clip(p, EPS, 1 - EPS)
    ll = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    return float(np.average(ll, weights=w))


def fit_lasso_logistic(x: np.ndarray, y: np.ndarray, w: np.ndarray, order: np.ndarray):
    """An L1 logistic whose penalty is chosen on the pool's latest 20% (fit on the rest), then
    refit on all of it (feature selection inside the fold, rule k)."""
    if len(np.unique(y)) < 2:
        return Constant(float(y.mean()) if len(y) else 0.0), None
    late = _holdout(order)
    best, best_c = np.inf, C_GRID[-1]
    for C in C_GRID:
        m = make_pipeline(StandardScaler(), LogisticRegression(
            C=C, l1_ratio=1.0, solver="liblinear", max_iter=2000))  # fmt: skip
        if len(np.unique(y[~late])) < 2:
            break
        m.fit(x[~late], y[~late], logisticregression__sample_weight=w[~late])
        loss = log_loss(m.predict_proba(x[late])[:, 1], y[late], w[late])
        if loss < best:
            best, best_c = loss, C
    m = make_pipeline(StandardScaler(), LogisticRegression(
        C=best_c, l1_ratio=1.0, solver="liblinear", max_iter=2000))  # fmt: skip
    return m.fit(x, y, logisticregression__sample_weight=w), best_c


def fit_trees(x: np.ndarray, y: np.ndarray, w: np.ndarray, seed: int = 0):
    if len(np.unique(y)) < 2:
        return Constant(float(y.mean()) if len(y) else 0.0)
    return HistGradientBoostingClassifier(**{**TREES, "random_state": seed}).fit(
        x, y, sample_weight=w
    )


# ---------------------------------------------------------------- rung 0: a shrunk table
@dataclass
class TableModel:
    """A rate per cell of `levels` (finest last), each shrunk toward its parent cell by `m`
    pseudo-rows: cell rate = (sum + m × parent) / (n + m)."""

    levels: Sequence[Sequence[str]]
    m: float = 20.0
    tables: list[pl.DataFrame] = field(default_factory=list)
    overall: float = 0.0

    def fit(self, df: pl.DataFrame, y: str = "y", w: str = "weight") -> TableModel:
        self.overall = float((df[y] * df[w]).sum() / df[w].sum())
        self.tables = []
        for cols in self.levels:
            self.tables.append(
                df.group_by(list(cols)).agg(s=(c(y) * c(w)).sum(), n=c(w).sum())
            )
        return self

    def predict(self, df: pl.DataFrame) -> np.ndarray:
        rate = np.full(df.height, self.overall)
        for cols, t in zip(self.levels, self.tables, strict=True):
            j = df.select(list(cols)).join(t, on=list(cols), how="left")
            s, n = j["s"].fill_null(0.0).to_numpy(), j["n"].fill_null(0.0).to_numpy()
            rate = (s + self.m * rate) / (n + self.m)
        return rate


# ---------------------------------------------------------------- a count's distribution
def distribution_summary(dist: np.ndarray) -> dict[str, np.ndarray]:
    """Rows of P(k), k = 0..K → mean, q10, q50, q90 (the smallest k whose chance up to it
    reaches the level), and the spike parts: the chance of 1+ and the forecast given 1+."""
    k = np.arange(dist.shape[1])
    dist = dist / dist.sum(axis=1, keepdims=True)
    cdf = np.cumsum(dist, axis=1)
    out = {"mean": dist @ k}
    for name, lvl in (("q10", 0.1), ("q50", 0.5), ("q90", 0.9)):
        out[name] = (cdf < lvl - 1e-12).sum(axis=1).astype(float)
    p0 = dist[:, 0]
    pn = np.clip(1 - p0, 0.0, 1.0)
    out["p_nonzero"] = pn
    cond = dist[:, 1:] / np.clip(pn, EPS, None)[:, None]
    ccdf = np.cumsum(cond, axis=1)
    out["if_nonzero_mean"] = np.where(pn > EPS, cond @ k[1:], 1.0)
    for name, lvl in (("if_nonzero_q10", 0.1), ("if_nonzero_q50", 0.5), ("if_nonzero_q90", 0.9)):
        out[name] = np.where(pn > EPS, 1 + (ccdf < lvl - 1e-12).sum(axis=1), 1.0).astype(float)
    return out


def empirical_dist(frac_rows: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Training rows' fractions of a window absent (k/n) → per predicted row with window `n`, a
    distribution over 0..max(n): each training fraction mapped to round(frac × n)."""
    kmax = int(n.max()) if len(n) else 0
    out = np.zeros((len(n), kmax + 1))
    for i, ni in enumerate(n):
        ks = np.clip(np.round(frac_rows * ni).astype(int), 0, ni)
        out[i] = np.bincount(ks, minlength=kmax + 1)[: kmax + 1]
    return out


# ---------------------------------------------------------------- method 1: two parts
@dataclass
class TwoPart:
    """The chance of any health absence in the window (lasso logistic) × the share of the window
    absent if any (ridge on the share), whose spread comes from the latest training rows' own
    shares in the same size of prediction. Counts are the share × the window's games."""

    columns: Sequence[str]
    trees: bool = False
    any_model: Any = None
    size_model: Any = None
    shares: dict[int, np.ndarray] = field(default_factory=dict)

    def fit(self, train: pl.DataFrame) -> TwoPart:
        x = train.select(self.columns).to_numpy().astype(float)
        n = train["n_window"].to_numpy().astype(float)
        y = train["y"].to_numpy().astype(float)
        w = train["weight"].to_numpy().astype(float)
        order = train["as_of"].dt.epoch("s").to_numpy()
        anyy = (y > 0).astype(int)
        if self.trees:
            self.any_model = fit_trees(x, anyy, w)
        else:
            self.any_model, _ = fit_lasso_logistic(x, anyy, w, order)
        on = anyy == 1
        share = y[on] / n[on]
        late = _holdout(order[on])
        reg = (HistGradientBoostingRegressor(**{**TREES, "loss": "squared_error"})
               if self.trees else make_pipeline(StandardScaler(), Ridge(alpha=10.0)))  # fmt: skip
        if late.sum() >= MIN_BIN and (~late).sum() >= MIN_BIN:
            early = reg.fit(x[on][~late], share[~late], **_sw(reg, w[on][~late]))
            pred = np.clip(early.predict(x[on][late]), 0.0, 1.0)
            bins = np.digitize(pred, BINS)
            for b in range(len(BINS) + 1):
                rows = share[late][bins == b]
                self.shares[b] = rows if len(rows) >= MIN_BIN else share[late]
        else:
            self.shares = {b: share for b in range(len(BINS) + 1)}
        self.size_model = reg.fit(x[on], share, **_sw(reg, w[on]))
        return self

    def distribution(self, rows: pl.DataFrame) -> np.ndarray:
        x = rows.select(self.columns).to_numpy().astype(float)
        n = rows["n_window"].to_numpy().astype(int)
        p_any = self.any_model.predict_proba(x)[:, 1]
        size = np.clip(self.size_model.predict(x), 0.0, 1.0)
        bins = np.digitize(size, BINS)
        kmax = int(n.max())
        out = np.zeros((len(n), kmax + 1))
        for b in np.unique(bins):
            idx = np.where(bins == b)[0]
            d = empirical_dist(self.shares[b], n[idx])
            d[:, 0] = 0.0
            # a window with an absence has at least one absent game
            for j, i in enumerate(idx):
                if d[j, 1:].sum() == 0:
                    d[j, 1] = 1.0
            d = d / d.sum(axis=1, keepdims=True)
            out[idx, : d.shape[1]] = d * p_any[idx, None]
        out[:, 0] = 1 - p_any
        return out


def _sw(model, w):
    """The sample-weight keyword for a model or a pipeline's last step."""
    if hasattr(model, "steps"):
        return {f"{model.steps[-1][0]}__sample_weight": w}
    return {"sample_weight": w}


# ---------------------------------------------------------------- consecutive rows
def next_pairs(train: pl.DataFrame) -> pl.DataFrame:
    """Each pool row with what his row at his team's next game showed: `n_state` (or `f`, on no
    roster that week, when that week's rows are in the pool) and `absent_now` (whether this game
    was a health absence, from the next row's record; null when unknown)."""
    nxt = train.select(
        "gsis_id", "season", next_week="week", n_state="state",
        n_last_absent="last_absent", n_last_week="last_week",
    ).unique(["gsis_id", "season", "next_week"], keep="first")  # fmt: skip
    weeks = train.select("season", next_week="week").unique().with_columns(seen=pl.lit(True))
    out = train.join(nxt, on=["gsis_id", "season", "next_week"], how="left").join(
        weeks, on=["season", "next_week"], how="left"
    )
    return out.with_columns(
        n_state=pl.when(c("n_state").is_not_null()).then(c("n_state"))
        .when(c("seen").fill_null(False)).then(pl.lit("f")),
        absent_now=pl.when(c("n_last_week") == c("week")).then(c("n_last_absent")),
    )  # fmt: skip


def d_bucket(d: np.ndarray) -> np.ndarray:
    return np.clip(d, 1, D_MAX).astype(int)


# ---------------------------------------------------------------- method 2: the chain
@dataclass
class Chain:
    """A weekly health-state chain (method 2).

    - **Moves:** for each state (h, l, o, r), a multinomial model (logistic, or trees for rung
      3) of the next game's state (h, l, o, r or f) from the weeks in this state (1, 2, 3, 4+)
      and his traits (`traits`).
    - **Absent given the state:** reserve always, healthy never (by the definition); listed and
      out from a logistic on the state, weeks in it and his traits.
    - **This game:** its state is known (the final report); its chance of absence comes from
      `first`, a logistic on every column (`columns`), fit on the listed rows.
    - **Rolled forward exactly** over (state, weeks in it, games absent so far) for the window.
    """

    columns: Sequence[str]
    traits: Sequence[str]
    trees: bool = False
    moves: dict[str, Any] = field(default_factory=dict)
    emit: dict[str, Any] = field(default_factory=dict)
    first: Any = None

    def _x(self, df: pl.DataFrame, d: np.ndarray | None = None) -> np.ndarray:
        dd = d_bucket(df["dur"].to_numpy() if d is None else d)
        onehot = np.column_stack([(dd == b).astype(float) for b in range(1, D_MAX + 1)])
        return np.column_stack([onehot, df.select(self.traits).to_numpy().astype(float)])

    def fit(self, train: pl.DataFrame) -> Chain:
        pairs = next_pairs(train)
        w_all = pairs["weight"].to_numpy().astype(float)
        for s in ("h", "l", "o", "r"):
            rows = pairs.filter((c("state") == s) & c("n_state").is_not_null())
            y = rows["n_state"].to_numpy()
            classes = sorted(set(y))
            x = self._x(rows)
            w = rows["weight"].to_numpy().astype(float)
            if len(classes) < 2:
                self.moves[s] = ("const", classes[0] if classes else s)
            elif self.trees:
                self.moves[s] = HistGradientBoostingClassifier(**TREES).fit(x, y, sample_weight=w)
            else:
                m = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=3000))
                self.moves[s] = m.fit(x, y, logisticregression__sample_weight=w)
        for s in ("l", "o"):
            rows = pairs.filter((c("state") == s) & c("absent_now").is_not_null())
            y = rows["absent_now"].to_numpy().astype(int)
            self.emit[s] = fit_logistic(self._x(rows), y, rows["weight"].to_numpy(), C=0.3)
        listed = pairs.filter(c("state").is_in(["l", "o"]) & c("absent_now").is_not_null())
        self.first = fit_logistic(
            listed.select(self.columns).to_numpy().astype(float),
            listed["absent_now"].to_numpy().astype(int),
            listed["weight"].to_numpy(), C=0.3,
        )  # fmt: skip
        del w_all
        return self

    def _move_probs(self, rows: pl.DataFrame, s: str, d: int) -> np.ndarray:
        """P(next state) for every row, from state s with d weeks in it: (N, 5)."""
        model = self.moves[s]
        out = np.zeros((rows.height, len(NEXT_STATES)))
        if isinstance(model, tuple):
            out[:, NEXT_STATES.index(model[1])] = 1.0
            return out
        p = model.predict_proba(self._x(rows, np.full(rows.height, d)))
        classes = list(model.classes_ if not hasattr(model, "steps") else model.steps[-1][1].classes_)
        for j, k in enumerate(classes):
            out[:, NEXT_STATES.index(k)] = p[:, j]
        return out

    def _emit_probs(self, rows: pl.DataFrame, s: str, d: int) -> np.ndarray:
        if s == "r":
            return np.ones(rows.height)
        if s == "h":
            return np.zeros(rows.height)
        return self.emit[s].predict_proba(self._x(rows, np.full(rows.height, d)))[:, 1]

    def first_absent(self, rows: pl.DataFrame) -> np.ndarray:
        """This game's chance of a health absence: 0 if not listed, 1 on a reserve list."""
        st = rows["state"].to_numpy()
        p = self.first.predict_proba(rows.select(self.columns).to_numpy().astype(float))[:, 1]
        return np.where(st == "h", 0.0, np.where(st == "r", 1.0, p))

    def distribution(self, rows: pl.DataFrame) -> np.ndarray:
        """P(games absent = k) over each row's window (`n_window` games from this one)."""
        n = rows["n_window"].to_numpy().astype(int)
        N, K = rows.height, int(n.max()) + 1
        live = [(s, d) for s in ("h", "l", "o", "r") for d in range(1, D_MAX + 1)]
        S = len(live) + 1  # + off
        index = {sd: i for i, sd in enumerate(live)}
        # transition (N, S, S) and emission (N, S)
        T = np.zeros((N, S, S))
        E = np.zeros((N, S))
        for (s, d), i in index.items():
            mp = self._move_probs(rows, s, d)
            for j, ns in enumerate(NEXT_STATES):
                if ns == "f":
                    T[:, i, S - 1] += mp[:, j]
                else:
                    nd = min(d + 1, D_MAX) if ns == s else 1
                    T[:, i, index[(ns, nd)]] += mp[:, j]
            E[:, i] = self._emit_probs(rows, s, d)
        T[:, S - 1, S - 1] = 1.0
        # this game: known state, its own chance of absence
        st = rows["state"].to_numpy()
        dd = d_bucket(rows["dur"].to_numpy())
        start = np.array([index[(s, d)] for s, d in zip(st, dd, strict=True)])
        p1 = self.first_absent(rows)
        mass = np.zeros((N, S, K))
        mass[np.arange(N), start, 0] = 1 - p1
        mass[np.arange(N), start, 1] = p1
        out = np.zeros((N, K))
        done = n == 1
        out[done] = mass[done].sum(axis=1)
        for step in range(2, K):
            moved = np.einsum("nsk,nst->ntk", mass, T)
            e = E[:, :, None]
            mass = moved * (1 - e)
            mass[:, :, 1:] += moved[:, :, :-1] * e
            hit = n == step
            out[hit] = mass[hit].sum(axis=1)
        return out


# ---------------------------------------------------------------- method 3: hidden health
SYM = 8  # the report-and-snaps symbol (features.SYMBOLS 0-7)
PRAC = 4  # the practice symbol: 0 full, 1 limited, 2 did not, 3 not on the practice report
ABSENT_SYM = (4, 6, 7)  # listed or out with no snap, or reserve
# What this week's known report says the snaps-free symbol can be, by state
STATE_SYMS = {"h": (0, 1, 2), "l": (3, 4), "o": (5, 6), "r": (7,)}


@dataclass
class Hmm:
    """A hidden health state (method 3), one model per position group (and one pooled for the
    rest): K hidden states; each game shows two symbols, conditionally independent given the
    state: the report with the snaps (8 kinds) and the practice (4). Fit by Baum-Welch on each
    training player-season's games. A row's state is filtered from his season so far and this
    week's report and practice (its snaps unknown), then rolled forward like the chain."""

    k: int = 4
    iters: int = 30
    params: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = field(
        default_factory=dict
    )  # group → (start, transitions, report-snaps emissions, practice emissions)

    @staticmethod
    def sequences(train: pl.DataFrame) -> pl.DataFrame:
        """One sequence per player-season: the longest `obs_seq` known in the pool (his latest
        row's), with its practice sequence and position group."""
        return (
            train.with_columns(L=c("obs_seq").str.len_chars())
            .sort("L")
            .group_by("gsis_id", "season")
            .agg(c("obs_seq").last(), c("prac_seq").last(), c("grp").last(), c("weight").last())
            .filter(c("obs_seq").str.len_chars() > 0)
        )

    def fit(self, train: pl.DataFrame, seed: int = 0) -> Hmm:
        seqs = self.sequences(train)
        groups = seqs["grp"].unique().to_list()
        for g in groups:
            part = seqs.filter(c("grp") == g)
            self.params[g] = self._baum_welch(part, seed)
        self.params["_all"] = self._baum_welch(seqs, seed)
        return self

    def _encode(self, seqs: pl.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        lengths = seqs["obs_seq"].str.len_chars().to_numpy()
        T = int(lengths.max())
        O = np.zeros((seqs.height, T), dtype=int)
        P = np.zeros((seqs.height, T), dtype=int)
        mask = np.zeros((seqs.height, T), dtype=bool)
        for i, (o, p) in enumerate(zip(seqs["obs_seq"], seqs["prac_seq"], strict=True)):
            L = len(o)
            O[i, :L] = np.frombuffer(o.encode(), dtype=np.uint8) - 48
            P[i, :L] = np.frombuffer(p.encode(), dtype=np.uint8)[:L] - 48
            mask[i, :L] = True
        return O, P, mask

    def _baum_welch(self, seqs: pl.DataFrame, seed: int):
        rng = np.random.default_rng(seed)
        O, P, mask = self._encode(seqs)
        w = seqs["weight"].to_numpy().astype(float)
        N, T = O.shape
        K = self.k
        # start from a health ladder: state 0 healthy ... K-1 reserve, plus a little noise
        pi = np.full(K, 1.0 / K)
        A = np.full((K, K), 0.1 / (K - 1)) + np.eye(K) * (0.9 - 0.1 / (K - 1))
        B = np.full((K, SYM), 0.02)
        anchors = [(0, 1), (2, 3), (5, 6), (7,)][:K]
        for z, syms in enumerate(anchors):
            for s in syms:
                B[z, s] += 1.0
        B = B * rng.uniform(0.9, 1.1, B.shape)
        B /= B.sum(axis=1, keepdims=True)
        C = np.full((K, PRAC), 1.0 / PRAC) * rng.uniform(0.9, 1.1, (K, PRAC))
        C /= C.sum(axis=1, keepdims=True)
        for _ in range(self.iters):
            em = B[:, O].transpose(1, 2, 0) * C[:, P].transpose(1, 2, 0)  # (N, T, K)
            em = np.where(mask[:, :, None], em, 1.0)
            alpha = np.zeros((N, T, K))
            scale = np.ones((N, T))
            a = pi[None, :] * em[:, 0]
            scale[:, 0] = a.sum(axis=1)
            alpha[:, 0] = a / scale[:, 0, None]
            for t in range(1, T):
                a = (alpha[:, t - 1] @ A) * em[:, t]
                a = np.where(mask[:, t, None], a, alpha[:, t - 1])
                scale[:, t] = a.sum(axis=1)
                alpha[:, t] = a / scale[:, t, None]
            beta = np.ones((N, T, K))
            for t in range(T - 2, -1, -1):
                b = (A @ (em[:, t + 1] * beta[:, t + 1]).T).T / scale[:, t + 1, None]
                beta[:, t] = np.where(mask[:, t + 1, None], b, beta[:, t + 1])
            gamma = alpha * beta
            gamma /= gamma.sum(axis=2, keepdims=True)
            gamma *= (mask * w[:, None])[:, :, None]
            xi = np.zeros((K, K))
            for t in range(T - 1):
                on = mask[:, t + 1]
                if not on.any():
                    continue
                x = (alpha[on, t][:, :, None] * A[None]
                     * (em[on, t + 1] * beta[on, t + 1])[:, None, :]) / scale[on, t + 1, None, None]
                xi += (x * w[on, None, None]).sum(axis=0)  # fmt: skip
            pi = gamma[:, 0].sum(axis=0) + 1e-3
            pi /= pi.sum()
            A = xi + 1e-3
            A /= A.sum(axis=1, keepdims=True)
            for s in range(SYM):
                B[:, s] = gamma[O == s].sum(axis=0)
            B = (B + 1e-3) / (B + 1e-3).sum(axis=1, keepdims=True)
            for s in range(PRAC):
                C[:, s] = gamma[P == s].sum(axis=0)
            C = (C + 1e-3) / (C + 1e-3).sum(axis=1, keepdims=True)
        return pi, A, B, C

    def distribution(self, rows: pl.DataFrame) -> np.ndarray:
        n = rows["n_window"].to_numpy().astype(int)
        N, Kc = rows.height, int(n.max()) + 1
        out = np.zeros((N, Kc))
        grp = rows["grp"].to_numpy()
        for g in np.unique(grp):
            idx = np.where(grp == g)[0]
            params = self.params.get(g, self.params["_all"])
            out[idx] = self._dist(rows[idx], params, n[idx], Kc)
        return out

    def _dist(self, rows: pl.DataFrame, params, n: np.ndarray, Kc: int) -> np.ndarray:
        pi, A, B, C = params
        K = len(pi)
        N = rows.height
        post = np.zeros((N, K))
        for i, (o, p) in enumerate(zip(rows["obs_seq"], rows["prac_seq"], strict=True)):
            f = pi.copy()
            for j, sym in enumerate(o):
                if j:
                    f = f @ A
                f = f * B[:, int(sym)] * C[:, int(p[j]) if j < len(p) else 3]
                f /= f.sum()
            post[i] = f @ A if o else pi
        # this week's evidence: the report's state (snaps unknown) and the practice
        st = rows["state"].to_numpy()
        prac = rows["practice"].to_numpy()
        noprac = rows["no_practice"].to_numpy() > 0
        pcode = np.where(noprac, 3, np.clip(np.round(prac), 0, 2)).astype(int)
        absent_rep = np.zeros((N, K))
        like = np.zeros((N, K))
        for s, syms in STATE_SYMS.items():
            on = st == s
            if not on.any():
                continue
            ls = B[:, list(syms)].sum(axis=1)
            la = B[:, [x for x in syms if x in ABSENT_SYM]].sum(axis=1)
            like[on] = ls[None, :] * C[:, pcode[on]].T
            absent_rep[on] = np.where(ls > 0, la / ls, 0.0)[None, :]
        z1 = post * like
        z1 /= np.clip(z1.sum(axis=1, keepdims=True), 1e-300, None)
        p1 = (z1 * absent_rep).sum(axis=1)
        # roll forward: game 1 split by absence, then the hidden state moves
        b_abs = B[:, list(ABSENT_SYM)].sum(axis=1)
        mass = np.zeros((N, K, Kc))
        m_abs = z1 * absent_rep
        mass[:, :, 0] = z1 - m_abs
        mass[:, :, 1] = m_abs
        out = np.zeros((N, Kc))
        out[n == 1] = mass[n == 1].sum(axis=1)
        for step in range(2, Kc):
            moved = np.einsum("nzk,zy->nyk", mass, A)
            mass = moved * (1 - b_abs)[None, :, None]
            mass[:, :, 1:] += moved[:, :, :-1] * b_abs[None, :, None]
            out[n == step] = mass[n == step].sum(axis=1)
        del p1
        return out
