"""The no-noise test (D6): the lasso's weekly fantasy points at Saturday, with and without the
expert's snap share, and the same question for ECR.
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/no_noise.py [variant]

The share comes from the expert's own walk-forward history (rule e), made here for 2014-2024, so
every row was predicted by a model trained only on earlier seasons. Both lassos train from 2014,
so they see the same seasons. `points x share` is offered too: a player's points scale with their
playing time (idea I7). The lasso picks what to keep.

ECR is a rank curve, so its question is asked as a correction learned on earlier seasons: points
from ECR's projection, with and without the share. The first ECR season is 2022, so this scores
2023 and 2024 only.
"""

import sys

import numpy as np
import polars as pl
from pcf.baselines.common import fit_offsets, with_ranges
from pcf.baselines.lasso import FEATURES, Lasso
from pcf.config import get_config
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.validation import backtest
from pcf.validation.compare import compare
from pcf.validation.nulls import no_noise
from pcf.validation.scores import row_losses
from sklearn.linear_model import LinearRegression

c = pl.col
KEYS = ["gsis_id", "game_id"]
FIRST = 2014
SEASONS = list(range(FIRST, 2025))
REPORT = list(range(2016, 2025))
ECR_RUN = "d2c338c7ece64eada6de0874beb85d11"


class Without(Lasso):
    """The lasso at Saturday, on the seasons the expert's history covers."""

    variant = "lasso_saturday"
    run = "saturday"
    first_train = FIRST


class With(Without):
    variant = "lasso_saturday_share"
    columns = [*FEATURES, "share", "share_x_points"]
    shares: pl.DataFrame

    def features(self, view, games):
        rows = super().features(view, games).join(self.shares, on=KEYS, how="left")
        share = c("share").fill_null(c("l4_points") * 0)
        return rows.with_columns(share=share, share_x_points=share * c("l4_points"))


def main(variant: str) -> None:
    gw = Gateway()
    print(f"expert: participation/{variant}, walk-forward {FIRST}-{SEASONS[-1]}")
    bt = backtest.run(find("participation", variant)(), gw, SEASONS, refit="season")
    shares = bt.history.select(*KEYS, share="mean")
    print(f"   {shares.height:,} predictions")

    With.shares = shares
    without = backtest.run(Without(), gw, REPORT, refit="season").scored
    with_ = backtest.run(With(), gw, REPORT, refit="season").scored
    verdict, comp = no_noise(with_, without, KEYS)
    print(f"\n== The lasso's fantasy points, {REPORT[0]}-{REPORT[-1]}: {verdict}")
    print(f"   pinball with - without {comp.diff:+.4f} ({comp.lo:+.4f} to {comp.hi:+.4f}), "
          f"{comp.rows:,} rows, {comp.blocks} weeks")  # fmt: skip
    a = with_.join(without.select(*KEYS), on=KEYS)
    b = without.join(with_.select(*KEYS), on=KEYS)
    print(f"   pinball {a['loss'].mean():.4f} vs {b['loss'].mean():.4f}; "
          f"MAE {a['readable'].mean():.3f} vs {b['readable'].mean():.3f}")  # fmt: skip
    for s in (2021, 2022, 2023, 2024):
        x, y = a.filter(c("step_season") == s) if "step_season" in a.columns else a, b
        if "step_season" in a.columns:
            y = b.filter(c("step_season") == s)
            print(f"   {s}: pinball {x['loss'].mean():.4f} vs {y['loss'].mean():.4f}")
    gap(gw, without, with_)
    ecr(gw, shares)


def gap(gw: Gateway, without: pl.DataFrame, with_: pl.DataFrame) -> None:
    """How much of the lasso's gap to ECR the share closes, on the rows ECR ranks (2022-2024)."""
    folder = get_config().zone("outputs") / "baselines" / "ecr" / ECR_RUN
    e = find("baselines", "ecr")()
    y = backtest.targets(e, gw).select(*KEYS, "y")
    h = row_losses(pl.read_parquet(folder / "history.parquet").join(y, on=KEYS), "amount")
    rows = h.select(KEYS).join(without.select(KEYS), on=KEYS).join(with_.select(KEYS), on=KEYS)
    print(f"\n== Against ECR, on the {rows.height:,} rows all three score, 2022-2024")
    for name, d in [("ECR", h), ("lasso", without), ("lasso + share", with_)]:
        d = d.join(rows, on=KEYS)
        print(f"   {name:<14} pinball {d['loss'].mean():.4f}, MAE {d['readable'].mean():.3f}")


def _correct(d: pl.DataFrame, cols: list[str], test: int) -> pl.DataFrame:
    """Per position: points from `cols`, learned on earlier seasons, scored on `test`."""
    out = []
    for (pos,), g in d.group_by("position"):
        fit, app = g.filter(c("season") < test), g.filter(c("season") == test)
        m = LinearRegression().fit(fit.select(cols).to_numpy(), fit["y"].to_numpy())
        resid = fit.select("position", weight=pl.lit(1.0), resid=c("y") - pl.Series(
            m.predict(fit.select(cols).to_numpy())))  # fmt: skip
        pred = app.select(*KEYS, "position", "y", "step").with_columns(
            mean=pl.Series(m.predict(app.select(cols).to_numpy()))
        )
        out.append(with_ranges(pred, fit_offsets(resid, ("position",)), ("position",)))
    return pl.concat(out)


def ecr(gw: Gateway, shares: pl.DataFrame) -> None:
    folder = get_config().zone("outputs") / "baselines" / "ecr" / ECR_RUN
    e = find("baselines", "ecr")()
    h = pl.read_parquet(folder / "history.parquet")
    y = backtest.targets(e, gw).select(*KEYS, "y")
    pos = gw.source.part("player_game", "roster").select(*KEYS, "position", "season")
    d = (
        h.with_columns(step=c("game_id").str.slice(0, 7))
        .join(y, on=KEYS).join(pos, on=KEYS).join(shares, on=KEYS)
        .rename({"mean": "ecr"})
        .with_columns(share_x_ecr=c("share") * c("ecr"))
    )  # fmt: skip
    plain, more = [], []
    for test in (2023, 2024):
        plain.append(_correct(d, ["ecr"], test))
        more.append(_correct(d, ["ecr", "share", "share_x_ecr"], test))
    a = row_losses(pl.concat(more), "amount")
    b = row_losses(pl.concat(plain), "amount")
    verdict = compare(a, b, KEYS, "step", ("with", "without"))
    print("\n== ECR's points, with and without the share, 2023-2024 (recalibrated on earlier seasons)")
    print(f"   pinball with - without {verdict.diff:+.4f} ({verdict.lo:+.4f} to {verdict.hi:+.4f}): "
          f"{verdict.verdict}, {verdict.rows:,} rows")  # fmt: skip
    print(f"   pinball {a['loss'].mean():.4f} vs {b['loss'].mean():.4f}; "
          f"MAE {a['readable'].mean():.3f} vs {b['readable'].mean():.3f}")  # fmt: skip
    np.seterr(all="ignore")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "trees")
