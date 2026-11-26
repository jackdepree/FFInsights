"""I156: the second pull in other experts' shrinks (decision 0052).

Skill-over-expected's build already tested it (2 of 15 shipped trait-groups). Here: opportunity-
quality's method B (a per-player partial-pooling shrink, k_B = tau2 / (tau2 + V)), the one other
shipped shrink by sample size alone whose forecast is scored on its own target. Its walk-forward
backtest rows (2016-2024, its own cache: the realised future gap is not in the saved history) get
the shared second pull: mu + b (mean_B - mu), one slope b per position fit on earlier seasons
only, scored on the future gap over the rest of the season, weighted by its chances, players
resampled. VOE's values and opportunity-quality's feature shrinks (PRIOR = 30) feed linear or
tree models downstream, where a one-slope rescale is absorbed (decision 0051 call 28), so they
aren't tested.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.experts.stabilization import evaluate as E
from pcf.validation import stabilize as S

c = pl.col


def frame() -> pl.DataFrame:
    path = get_config().zone("interim") / "opportunity_quality" / "regression_backtest.parquet"
    d = pl.read_parquet(path).filter(c("scorable"))
    out = []
    for pos in sorted(d["position"].unique().to_list()):
        a = d.filter(c("position") == pos).sort("season")
        x = (a["mean_B"] - a["mu"]).to_numpy()
        y = (a["future"] - a["mu"]).to_numpy()
        fc, b = S.second_pull(x, y, a["m"].to_numpy(), a["season"].to_numpy())
        out.append(a.with_columns(pull_B=pl.Series(fc) + c("mu"), b=pl.Series(b)))
    f = pl.concat(out).with_columns(c("pull_B", "b").fill_nan(None)).drop_nulls("pull_B")
    return f.with_columns(y=c("future"), w=c("m"))


def report(out, seed: int) -> dict:
    f = frame()
    out("", "== I156: the second pull on opportunity-quality's method B (its backtest rows, "
        f"seasons {f['season'].min()}-{f['season'].max()} with an earlier season to fit on)")
    res = {}
    for label, g in (("everyone", f), ("week 1 (next season)", f.filter(c("week") == 1)),
                     *((p, f.filter(c("position") == p)) for p in ("RB", "WR", "TE"))):  # fmt: skip
        gB = E.gain(g, "pull_B", "mean_B", seed=seed)
        gA = E.gain(g, "pull_B", "mean_A", seed=seed)
        out(f"- {label} ({g.height} player-games): B with the second pull vs B {gB.fmt()}; vs A "
            f"{gA.fmt()}; slope {float(np.nanmean(g['b'].to_numpy())):.2f}")
        res[label] = {"vs_B": gB, "vs_A": gA}
    return res


# ---------------------------------------------------------------- I174 (routed by the build chat)
def _by_position(st: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """I174: vacated-offseason's I165 shrink with one slope per skill group (TE, WR, RB) for the
    stayers left empty, fit on earlier pairs only, the shared slope where a group has fewer than
    30 earlier rows. Every other row keeps the shipped forecast (`f_shr`)."""
    from pcf.experts.vacated_opportunity import common as VK
    from pcf.experts.vacated_opportunity import report as V

    st = st.with_columns(f_pos=c("f_shr"))
    counts = {}
    for grp in VK.SKILL:
        d = st.filter((c("group") == grp) & ~c("intake") & c("season").is_in(V.PAIRS_ALL))
        d = d.with_columns(dlt=c("f_pm") - c("f0"))
        fr = d.filter(c("y").is_not_null())
        s_arr, x = fr["season"].to_numpy(), fr["dlt"].to_numpy()
        y = (fr["y"] - fr["f0"]).to_numpy()
        b, n = {}, {}
        for s in V.OSC:
            tr = s_arr < s
            n[s] = int(tr.sum())
            b[s] = float((x[tr] * y[tr]).sum() / max((x[tr] ** 2).sum(), 1e-12)) if tr.sum() >= 30 \
                else None  # fmt: skip
        d = d.with_columns(b_pos=c("season").replace_strict(b, default=None, return_dtype=pl.Float64))
        d = d.with_columns(f_pos=pl.when(c("b_pos").is_not_null())
                           .then((c("f0") + c("b_pos") * c("dlt")).clip(0, 1)).otherwise(c("f_shr")))
        st = st.update(d.select("gsis_id", "team", "season", "f_pos"), on=["gsis_id", "team", "season"])
        counts[grp] = {"slopes": b, "rows": n}
    return st, counts


def i174(out, copies: int = 19, seed: int = 0) -> dict:
    from pcf.experts.vacated_opportunity import common as VK
    from pcf.experts.vacated_opportunity import offseason as O
    from pcf.experts.vacated_opportunity import report as V

    m = "target"
    fits = V.offseason_fits(m)
    st, deps = O.build(m, fits)
    st, _ = V.shrink(st, m)
    st, counts = _by_position(st)
    sc = V._off_rows(st, m, "all")
    out("", "== I174: vacated-offseason's target shrink with a slope per position (TE, WR, RB) for "
        "stayers left empty, against its one shared slope (I165, shipped); stayers 2017-2024, "
        "90% team bootstrap")  # fmt: skip
    for grp, v in counts.items():
        out(f"- {grp}: earlier rows by target season " + ", ".join(
            f"{s + 1} {v['rows'][s]}" for s in V.OSC) + "; slopes " + ", ".join(
            f"{s + 1} {v['slopes'][s]:.2f}" if v["slopes"][s] is not None else f"{s + 1} shared"
            for s in V.OSC))  # fmt: skip
    res = {"all": V._gain(sc, "f_shr", "f_pos")}
    out(f"- every stayer ({sc.height}): per position vs shared {V._g(sc, 'f_shr', 'f_pos')}")
    for grp in VK.SKILL:
        d = sc.filter(c("group") == grp)
        res[grp] = V._gain(d, "f_shr", "f_pos")
        out(f"- {grp} ({d.height}): per position vs shared {V._g(d, 'f_shr', 'f_pos')}")
    nulls = []
    for k in range(copies):
        s2 = V._reforecast(st, O.shuffled_departures(deps, seed + 900 + k), fits, m)
        s2, _ = V.shrink(s2, m)
        s2, _ = _by_position(s2)
        nulls.append(V._gain(V._off_rows(s2, m, "all"), "f_shr", "f_pos")[0])
    beats = sum(res["all"][0] > v for v in nulls)
    out(f"- {copies} copies (each season's departures moved to another team, both shrinks refit): "
        f"best {100 * max(nulls):+.2f}%; the real gain beats {beats} of {copies}")
    res["beats"], res["nulls"] = beats, nulls
    return res
