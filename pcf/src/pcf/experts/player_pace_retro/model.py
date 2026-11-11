"""The `player-pace-retro` variants: per player-season, his plus-minus next season.

Features at a season's retrospective moment, from the finished seasons before it only (the
gateway hides the rest): per measure `<m>`, his last season's plus-minus and its weight
(`<m>_last`, `<m>_last_w`), and his earlier seasons' weighted sums decayed by `DECAY` per season
of age (`<m>_wd`, `<m>_w`); his position group last season (`group`). Rows: every player with an
earlier season. The outcome: that season's plus-minus, for players it measures on at least
`MIN_WEIGHT` (n_on * n_off / n_team summed over his games).

Ranges are the prediction plus the training misses' q10, q50, q90 per position group.
"""

from __future__ import annotations

from typing import Any, ClassVar

import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.core.contract import Expert

c = pl.col
KEYS = ["gsis_id", "season"]
INPUTS = {"player_season": ("on_field_pace",)}
DECAY = 0.7  # each earlier season counts 0.7 as much as the next
MIN_WEIGHT = 20.0
LOOKBACK = 4  # seasons
SHRINK_GRID = (5.0, 10.0, 25.0, 50.0, 100.0, 200.0, 400.0)
# measure → (the plus-minus column, its weight)
MEASURES: dict[str, tuple[str, str]] = {
    "proe": ("onf_pm_proe", "onf_w_proe"),
    "proe_pers": ("onf_pm_proe_pers", "onf_w_proe"),
    "pace": ("onf_pm_pace", "onf_w_pace"),
}


def season_features(ps: pl.DataFrame, season: int) -> pl.DataFrame:
    """Every player with a season in the `LOOKBACK` before `season`: his history features."""
    past = ps.filter(c("season").is_between(season - LOOKBACK, season - 1))
    if past.is_empty():
        return pl.DataFrame()
    past = past.with_columns(decay=DECAY ** (season - 1 - c("season")).cast(pl.Float64))
    last_season = past.group_by("gsis_id").agg(c("season").max().alias("last"))
    past = past.join(last_season, on="gsis_id")
    aggs: list[pl.Expr] = [
        c("onf_group").sort_by("season").last().alias("group"),
        c("season").n_unique().cast(pl.Int32).alias("seasons_seen"),
    ]
    for m, (value, weight) in MEASURES.items():
        w = pl.when(c(value).is_not_null()).then(c(weight)).otherwise(0.0)
        prev = c("season") == season - 1
        aggs += [
            (c(value).fill_null(0.0) * w * c("decay")).sum().alias(f"{m}_wd"),
            (w * c("decay")).sum().alias(f"{m}_w"),
            c(value).filter(prev).first().alias(f"{m}_last"),
            w.filter(prev).sum().alias(f"{m}_last_w"),
        ]
    return (
        past.group_by("gsis_id")
        .agg(aggs)
        .with_columns(season=pl.lit(season, pl.Int32))
        .select(*KEYS, pl.all().exclude(KEYS))
        .sort("gsis_id")
    )


class _Retro(Expert):
    id = "player-pace-retro"
    cadence = "retrospective"
    grain = "player_season"
    inputs = INPUTS
    groups = ("group",)
    first_train = 2017  # the first season with an earlier one to learn from (2016 on)
    measure: ClassVar[str]

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        season = int(games["season"].max())
        ps = view.table("player_season", seasons=list(range(season - LOOKBACK, season)))
        return season_features(ps, season)

    def target(self, view) -> pl.DataFrame:
        value, weight = MEASURES[self.measure]
        ps = view.table("player_season").filter(c(value).is_not_null() & (c(weight) >= MIN_WEIGHT))
        return ps.select(*KEYS, y=c(value), known_at="known_at")

    # shared: each group's weighted average outcome in training
    @staticmethod
    def _group_means(train: pl.DataFrame) -> dict[str, float]:
        g = train.group_by("group").agg(m=(c("y") * c("weight")).sum() / c("weight").sum())
        overall = float((train["y"] * train["weight"]).sum() / train["weight"].sum())
        return {"groups": dict(g.iter_rows()), "overall": overall}

    @staticmethod
    def _gm(rows: pl.DataFrame, means: dict) -> pl.Expr:
        return c("group").replace_strict(
            means["groups"], default=means["overall"], return_dtype=pl.Float64
        )

    def _point(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.Series:
        raise NotImplementedError

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        model = self._fit_point(train)
        point = self._point(model, train)
        resid = train.select("weight", "group").with_columns(resid=train["y"] - point)
        model["offsets"] = fit_offsets(resid, ["group"])
        return model

    def _fit_point(self, train: pl.DataFrame) -> dict[str, Any]:
        return {"means": self._group_means(train)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = rows.select(*KEYS, "group").with_columns(mean=self._point(model, rows))
        return with_ranges(out, model["offsets"], ["group"]).drop("group")

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in model.items() if k != "offsets"} | {
            "offsets": model["offsets"].to_dicts()
        }


class _Group(_Retro):
    """Rung 0: his position group's average."""

    def _point(self, model, rows):
        return rows.select(self._gm(rows, model["means"])).to_series()


class _Last(_Retro):
    """Rung 0: his plus-minus last season (his group's average if he has none)."""

    def _point(self, model, rows):
        m = self.measure
        return rows.select(
            pl.when(c(f"{m}_last_w") > 0)
            .then(c(f"{m}_last"))
            .otherwise(self._gm(rows, model["means"]))
        ).to_series()


class _Shrunk(_Retro):
    """Rung 1: his decayed earlier seasons shrunk toward his group's average by `k` (the weight
    an average player's history is worth), then a slope per group fit by weighted least
    squares; `k` is the grid value with the smallest training miss."""

    def _prior(self, rows: pl.DataFrame, means: dict, k: float) -> pl.Expr:
        m = self.measure
        gm = self._gm(rows, means)
        return (c(f"{m}_wd") - gm * c(f"{m}_w")) / (c(f"{m}_w") + k)

    def _slopes(self, train: pl.DataFrame, means: dict, k: float) -> tuple[dict, float]:
        d = train.select(
            "group", "weight", x=self._prior(train, means, k), r=c("y") - self._gm(train, means)
        )
        slopes, sse = {}, 0.0
        for (g,), part in d.group_by("group"):
            x, r, w = (part[col].to_numpy() for col in ("x", "r", "weight"))
            b = float((w * x * r).sum() / max((w * x * x).sum(), 1e-12))
            slopes[g] = b
            sse += float((w * (r - b * x) ** 2).sum())
        return slopes, sse

    def _fit_point(self, train: pl.DataFrame) -> dict[str, Any]:
        means = self._group_means(train)
        best = min(SHRINK_GRID, key=lambda k: self._slopes(train, means, k)[1])
        slopes, _ = self._slopes(train, means, best)
        return {"means": means, "k": best, "slopes": slopes}

    def _point(self, model, rows):
        slope = c("group").replace_strict(model["slopes"], default=0.0, return_dtype=pl.Float64)
        gm = self._gm(rows, model["means"])
        return rows.select(gm + slope * self._prior(rows, model["means"], model["k"])).to_series()


def _make(name: str, base: type, attrs: dict[str, Any]) -> type[Expert]:
    return type(name, (base,), {"__module__": __name__, **attrs})


def _variants(m: str) -> list[type[Expert]]:
    title = "".join(w.title() for w in m.split("_"))
    common = {"measure": m, "quantity": f"pm_{m}"}
    group = _make(f"Retro{title}Group", _Group, {**common, "variant": f"{m}_group"})
    last = _make(
        f"Retro{title}Last",
        _Last,
        {**common, "variant": f"{m}_last", "baselines": classmethod(lambda cls: [group])},
    )
    shrunk = _make(
        f"Retro{title}Shrunk",
        _Shrunk,
        {**common, "variant": f"{m}_shrunk", "baselines": classmethod(lambda cls: [group, last])},
    )
    return [group, last, shrunk]


VARIANTS: dict[str, type[Expert]] = {}
for _cls in [k for m in MEASURES for k in _variants(m)]:
    VARIANTS[_cls.variant] = _cls
    globals()[_cls.__name__] = _cls
del _cls
