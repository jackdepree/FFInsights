"""Availability's variants (decision 0047): one `Expert` per rung and method, by family.

| Family | Rows | Outcome | Variants |
|---|---|---|---|
| next | the 53-man roster, every position | a health absence this game | `next_table` (rung 0), `next_logit`, `next_lasso` (method 1), `next_trees` (rung 3) |
| active | QB, RB, WR, TE with participation's `active` | active on game day | `active_part` (participation's own), `active_recal` (it, recalibrated), `active_stack` (it beside availability's inputs) |
| next3, rest | the roster and the reserve lists | games of health absence in the window | `<h>_table` (rung 0), `<h>_two` (method 1), `<h>_chain` (method 2), `<h>_chain_trees` (rung 3), `<h>_hmm` (method 3) |
| kept | QB, RB, WR, TE listed this week | his offensive share when he plays | `kept_part` (participation's share alone), `kept_model` |

Every variant reads the same features (`features.features`), so a walk over saved features
scores them all.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

from pcf.core.contract import Expert
from pcf.experts.availability import models as M
from pcf.experts.availability import targets as T
from pcf.experts.availability.common import FIRST_TRAIN, INPUTS, SKILL
from pcf.experts.availability.features import NUMERIC, features

c = pl.col
QUANTS = ("q10", "q50", "q90")
SPIKE = ("p_nonzero", "if_nonzero_mean", "if_nonzero_q10", "if_nonzero_q50", "if_nonzero_q90")
# The next game's inputs for listed players: everything but the window
NEXT_COLS = [x for x in NUMERIC if x not in ("left", "st_r")]
# What the chain holds fixed for a player along the window: who he is and his load, and the
# current injury's body part (it lasts while the spell does)
TRAITS = [
    "proneness", "credibility", "absent17", "listed17", "absent_rate_c", "recovery", "spells_c",
    "age", "age2", "log_snaps4", "ewma_snaps", "last_share", "week_no",
    "part_soft", "part_hamstring", "part_knee", "part_ankle", "part_concussion", "part_shoulder",
    "part_not_injury", "repeat_part", "part_before",
    "g_QB", "g_RB", "g_WR", "g_TE", "g_OL", "g_DL", "g_LB", "g_DB",
]  # fmt: skip
HORIZON_COLS = [*NUMERIC, "n_window"]


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


class Availability(Expert):
    id = "availability"
    cadence = "in_season"
    grain = "roster_week"
    inputs = INPUTS
    run = "saturday"
    first_train = FIRST_TRAIN
    groups = ("grp", "state")
    family: ClassVar[str] = ""

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return features(view, games, self.keys())

    def explain(self, model: Any) -> dict[str, Any]:
        return {}


# ---------------------------------------------------------------- next game
class Next(Availability):
    """The chance of a health absence this game. Unlisted players can't have one (the
    definition), so they get their training rows' rate (about 0); the model is fit on listed
    rows (Questionable, Doubtful, Out, or limited or out of practice)."""

    family = "next"
    kind = "probability"

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        f = features(view, games, self.keys())
        return f.filter(~c("reserve")) if f.height else f

    def target(self, view) -> pl.DataFrame:
        return T.next_absent(view)

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        listed = train.filter(c("state") != "h")
        healthy = train.filter(c("state") == "h")
        h_rate = float((healthy["y"] * healthy["weight"]).sum() / max(healthy["weight"].sum(), 1))
        return {"h": max(h_rate, 1e-5), "m": self.fit_listed(listed)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        p = np.full(rows.height, model["h"])
        on = (rows["state"] != "h").to_numpy()
        if on.any():
            p[on] = np.clip(self.predict_listed(model["m"], rows.filter(c("state") != "h")),
                            1e-5, 1 - 1e-5)  # fmt: skip
        return rows.select(self.keys()).with_columns(mean=pl.Series(p))

    def fit_listed(self, train: pl.DataFrame) -> Any:
        raise NotImplementedError

    def predict_listed(self, model: Any, rows: pl.DataFrame) -> np.ndarray:
        raise NotImplementedError


def _cells(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        practice_c=pl.when(c("no_practice") > 0).then(-1.0).otherwise(c("practice")),
        part_c=c("part").fill_null("none"),
    )


class NextTable(Next):
    """Rung 0: the status-by-body-part table, by position (each cell shrunk to its parent)."""

    variant = "next_table"
    quantity = "p_health_absent"
    LEVELS = (("status",), ("status", "practice_c"), ("status", "practice_c", "part_c"),
              ("grp", "status", "practice_c", "part_c"))  # fmt: skip

    def fit_listed(self, train):
        return M.TableModel(self.LEVELS).fit(_cells(train))

    def predict_listed(self, model, rows):
        return model.predict(_cells(rows))


class NextLogit(Next):
    """Method 1, the next game: a logistic on every input (L2, standardized)."""

    variant = "next_logit"
    quantity = "p_health_absent"
    columns: ClassVar[list[str]] = NEXT_COLS

    def fit_listed(self, train):
        x = train.select(self.columns).to_numpy().astype(float)
        return M.fit_logistic(x, train["y"].to_numpy().astype(int),
                              train["weight"].to_numpy(), C=0.3)  # fmt: skip

    def predict_listed(self, model, rows):
        return model.predict_proba(rows.select(self.columns).to_numpy().astype(float))[:, 1]


class NextLasso(NextLogit):
    """Method 1 with the lasso's penalty chosen on the pool's latest 20%."""

    variant = "next_lasso"

    def fit_listed(self, train):
        x = train.select(self.columns).to_numpy().astype(float)
        m, _ = M.fit_lasso_logistic(x, train["y"].to_numpy().astype(int),
                                    train["weight"].to_numpy(),
                                    train["as_of"].dt.epoch("s").to_numpy())  # fmt: skip
        return m


class NextTrees(NextLogit):
    """Rung 3: gradient-boosted trees on the same inputs."""

    variant = "next_trees"

    def fit_listed(self, train):
        x = train.select(self.columns).to_numpy().astype(float)
        return M.fit_trees(x, train["y"].to_numpy().astype(int), train["weight"].to_numpy())


# ---------------------------------------------------------------- active, beside participation
class Active(Availability):
    """The chance he's active, on participation's rows, beside participation's `active`
    (`logit_pa`, from its saved walk-forward history: rule e)."""

    family = "active"
    kind = "probability"

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        f = features(view, games, self.keys())
        if f.is_empty():
            return f
        pa = view.output("participation/active").filter(
            c("game_id").is_in(games["game_id"].implode())
        )
        pa = pa.sort("as_of").unique(self.keys(), keep="last").select(*self.keys(), pa="mean")
        f = f.filter(c("position").is_in(list(SKILL)) & ~c("reserve"))
        f = f.join(pa, on=self.keys(), how="inner")
        return f.with_columns(logit_pa=pl.Series(_logit(f["pa"].to_numpy())))

    def target(self, view) -> pl.DataFrame:
        return T.active(view)


class ActivePart(Active):
    """Participation's `active` alone: the incumbent (the brief's simpler side)."""

    variant = "active_part"
    quantity = "p_active"

    def fit(self, train):
        return None

    def predict(self, model, rows):
        return rows.select(self.keys(), mean=c("pa").clip(1e-5, 1 - 1e-5))


class ActiveRecal(Active):
    """Participation's `active`, recalibrated inside the fold (Platt, on its log-odds and a
    listed flag): the fairer bar, since a recalibration needs no availability input."""

    variant = "active_recal"
    quantity = "p_active"

    def fit(self, train):
        x = train.select("logit_pa").to_numpy()
        m = LogisticRegression(C=1e6, max_iter=2000)
        return m.fit(x, train["y"].to_numpy().astype(int), sample_weight=train["weight"])

    def predict(self, model, rows):
        p = model.predict_proba(rows.select("logit_pa").to_numpy())[:, 1]
        return rows.select(self.keys()).with_columns(mean=pl.Series(np.clip(p, 1e-5, 1 - 1e-5)))


class ActiveStack(Active):
    """Participation's log-odds beside availability's inputs, and each listed-state input
    times it (a lasso logistic; the penalty chosen on the pool's latest 20%)."""

    variant = "active_stack"
    quantity = "p_active"
    columns: ClassVar[list[str]] = ["logit_pa", *NEXT_COLS]

    def _x(self, df):
        x = df.select(self.columns).to_numpy().astype(float)
        inter = df.select((c("logit_pa") * c(s)).alias(f"x_{s}") for s in ("st_l", "st_o")).to_numpy()
        return np.column_stack([x, inter])

    def fit(self, train):
        m, _ = M.fit_lasso_logistic(self._x(train), train["y"].to_numpy().astype(int),
                                    train["weight"].to_numpy(),
                                    train["as_of"].dt.epoch("s").to_numpy())  # fmt: skip
        return m

    def predict(self, model, rows):
        p = model.predict_proba(self._x(rows))[:, 1]
        return rows.select(self.keys()).with_columns(mean=pl.Series(np.clip(p, 1e-5, 1 - 1e-5)))


class ActiveGated(ActiveStack):
    """The stack fit and used on listed players only (on the report, or limited or no
    practice); everyone else keeps participation's `active`. Added after the first walk showed
    the stack helping listed players and costing unlisted ones (RESULTS.md R3): availability
    owns the health part, and an unlisted player's health absence is about 0.2%."""

    variant = "active_gated"
    quantity = "p_active"

    @staticmethod
    def _listed(df):
        return ((c("status") > 0) | (c("practice") >= 1)).fill_null(False)

    def fit(self, train):
        return super().fit(train.filter(self._listed(train)))

    def predict(self, model, rows):
        stack = super().predict(model, rows)["mean"].to_numpy()
        on = rows.select(self._listed(rows)).to_series().to_numpy()
        pa = rows["pa"].clip(1e-5, 1 - 1e-5).to_numpy()
        return rows.select(self.keys()).with_columns(mean=pl.Series(np.where(on, stack, pa)))


# ---------------------------------------------------------------- next 3, rest of season
SHUFFLED = ("y", "state", "dur", "last_absent", "last_week", "obs_seq", "prac_seq")


class Window(Availability):
    """Games of health absence over the window (this game on): a count with a spike at 0,
    judged part by part (decision 0014). Every method returns a distribution over 0..n."""

    family = ""
    kind = "amount"
    spike = True
    n: ClassVar[int | None] = None

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        f = features(view, games, self.keys())
        if f.is_empty():
            return f
        n = c("left") if self.n is None else pl.min_horizontal(c("left"), pl.lit(float(self.n)))
        return f.with_columns(n_window=n)

    def target(self, view) -> pl.DataFrame:
        return T.window_absent(view, self.n)

    def shuffle(self, pool: pl.DataFrame, seed: int) -> pl.DataFrame:
        """The signal test's null (decision 0047 call 25): the outcome and the health record the
        chain and the hidden state learn from (state, weeks in it, the last game's absence, the
        sequences) shuffled together across players within each step, so every move a refit
        learns is between two unrelated players."""
        cols = [x for x in SHUFFLED if x in pool.columns]
        return pool.with_columns(
            pl.struct(cols).shuffle(seed=seed).over("step").struct.unnest()
        )

    def fit(self, train: pl.DataFrame) -> Any:
        raise NotImplementedError

    def distribution(self, model: Any, rows: pl.DataFrame) -> np.ndarray:
        return model.distribution(rows)

    def predict(self, model: Any, rows: pl.DataFrame) -> pl.DataFrame:
        d = self.distribution(model, rows)
        s = M.distribution_summary(d)
        return rows.select(self.keys()).with_columns(
            **{k: pl.Series(v.astype(float)) for k, v in s.items()}
        )


class WindowTable:
    """Rung 0 for a window: his cell's (state × weeks in it) training shares of the window
    absent, mapped to his window's games; thin cells (under 200 rows) use the state's."""

    def fit(self, train: pl.DataFrame) -> WindowTable:
        t = train.with_columns(
            frac=c("y") / c("n_window"), dcell=c("dur").clip(1, 4).cast(pl.Int32)
        )
        self.state = {s: g["frac"].to_numpy() for (s,), g in t.partition_by(
            "state", as_dict=True).items()}  # fmt: skip
        self.cell = {
            k: g["frac"].to_numpy()
            for k, g in t.partition_by(["state", "dcell"], as_dict=True).items()
            if g.height >= 200
        }
        self.all = t["frac"].to_numpy()
        return self

    def distribution(self, rows: pl.DataFrame) -> np.ndarray:
        n = rows["n_window"].to_numpy().astype(int)
        out = np.zeros((rows.height, int(n.max()) + 1))
        keys = list(zip(rows["state"].to_list(),
                        rows["dur"].clip(1, 4).cast(pl.Int32).to_list(), strict=True))  # fmt: skip
        for key in set(keys):
            idx = np.array([i for i, k in enumerate(keys) if k == key])
            fr = self.cell.get(key, self.state.get(key[0], self.all))
            d = M.empirical_dist(fr, n[idx])
            out[idx, : d.shape[1]] = d
        return out


def _window_variants() -> dict[str, type[Window]]:
    made = {}
    for horizon, n in (("next3", 3), ("rest", None)):
        quantity = f"games_health_absent_{horizon}"
        common = {"family": horizon, "n": n, "quantity": quantity, "__module__": __name__}
        made[f"{horizon}_table"] = type(f"{horizon.title()}Table", (Window,), {
            **common, "variant": f"{horizon}_table",
            "__doc__": f"Rung 0, {horizon}: the state-by-weeks table.",
            "fit": lambda self, train: WindowTable().fit(train),
        })  # fmt: skip
        made[f"{horizon}_two"] = type(f"{horizon.title()}Two", (Window,), {
            **common, "variant": f"{horizon}_two",
            "__doc__": f"Method 1, {horizon}: two parts, fit on this horizon alone.",
            "fit": lambda self, train: M.TwoPart(HORIZON_COLS).fit(train),
        })  # fmt: skip
        made[f"{horizon}_chain"] = type(f"{horizon.title()}Chain", (Window,), {
            **common, "variant": f"{horizon}_chain",
            "__doc__": f"Method 2, {horizon}: the weekly health-state chain.",
            "fit": lambda self, train: M.Chain(NEXT_COLS, TRAITS).fit(train),
        })  # fmt: skip
        made[f"{horizon}_chain_trees"] = type(f"{horizon.title()}ChainTrees", (Window,), {
            **common, "variant": f"{horizon}_chain_trees",
            "__doc__": f"Rung 3, {horizon}: the chain with trees for its moves.",
            "fit": lambda self, train: M.Chain(NEXT_COLS, TRAITS, trees=True).fit(train),
        })  # fmt: skip
        made[f"{horizon}_hmm"] = type(f"{horizon.title()}Hmm", (Window,), {
            **common, "variant": f"{horizon}_hmm",
            "__doc__": f"Method 3, {horizon}: the hidden health state.",
            "fit": lambda self, train: M.Hmm().fit(train),
        })  # fmt: skip
    return made


WINDOWS = _window_variants()
globals().update({cls.__name__: cls for cls in WINDOWS.values()})


# ---------------------------------------------------------------- kept share
class Kept(Availability):
    """His offensive share when he plays while listed, beside participation's share if he plays
    (`trees_week`'s `if_nonzero_mean`, from its saved history). The kept share is the forecast
    over participation's healthy one."""

    family = "kept"
    kind = "amount"
    inputs = {**INPUTS, "participation/trees_week": 1}

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        f = features(view, games, self.keys())
        if f.is_empty():
            return f
        tw = view.output("participation/trees_week").filter(
            c("game_id").is_in(games["game_id"].implode())
        )
        tw = tw.sort("as_of").unique(self.keys(), keep="last").select(
            *self.keys(), ps="if_nonzero_mean", ps10="if_nonzero_q10", ps50="if_nonzero_q50",
            ps90="if_nonzero_q90",
        )  # fmt: skip
        f = f.filter(c("position").is_in(list(SKILL)) & c("state").is_in(["l", "o"]))
        return f.join(tw, on=self.keys(), how="inner")

    def target(self, view) -> pl.DataFrame:
        return T.side_share(view)


class KeptPart(Kept):
    """Participation's share if he plays, alone (the simpler side)."""

    variant = "kept_part"
    quantity = "share_when_listed"

    def fit(self, train):
        return None

    def predict(self, model, rows):
        return rows.select(self.keys(), mean="ps", q10="ps10", q50="ps50", q90="ps90")


class KeptModel(Kept):
    """A ridge on participation's share and the report (status, practice, body part, weeks
    listed, last game's share), each report input also times participation's share; ranges
    from the latest training rows' residuals."""

    variant = "kept_model"
    quantity = "share_when_listed"
    columns: ClassVar[list[str]] = [
        "ps", "status", "practice", "no_practice", "dur", "last_share", "last_played",
        "part_soft", "part_hamstring", "part_knee", "part_ankle", "part_concussion",
        "part_shoulder", "part_not_injury", "part_other", "proneness", "age",
        "g_QB", "g_RB", "g_WR", "g_TE",
    ]  # fmt: skip

    def _x(self, df):
        x = df.select(self.columns).to_numpy().astype(float)
        inter = df.select((c("ps") * c(s)).alias(f"x_{s}") for s in ("status", "practice", "no_practice")).to_numpy()
        return np.column_stack([x, inter])

    def fit(self, train):
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        x, y, w = self._x(train), train["y"].to_numpy(), train["weight"].to_numpy()
        late = M._holdout(train["as_of"].dt.epoch("s").to_numpy())
        early = make_pipeline(StandardScaler(), Ridge(alpha=10.0)).fit(
            x[~late], y[~late], ridge__sample_weight=w[~late]
        )
        resid = y[late] - early.predict(x[late])
        q = np.quantile(resid, [0.1, 0.5, 0.9]) if len(resid) > 30 else np.zeros(3)
        model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        return model.fit(x, y, ridge__sample_weight=w), q

    def predict(self, model, rows):
        m, q = model
        mean = np.clip(m.predict(self._x(rows)), 0.0, 1.0)
        return rows.select(self.keys()).with_columns(
            mean=pl.Series(mean),
            **{k: pl.Series(np.clip(mean + q[i], 0.0, 1.0)) for i, k in enumerate(QUANTS)},
        )


VARIANTS: dict[str, type[Availability]] = {
    cls.variant: cls
    for cls in [NextTable, NextLogit, NextLasso, NextTrees, ActivePart, ActiveRecal, ActiveStack,
                ActiveGated,
                *WINDOWS.values(), KeptPart, KeptModel]
}  # fmt: skip
