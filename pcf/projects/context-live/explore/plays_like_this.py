# ruff: noqa: E501
"""Method C, "plays like this one", as a check on method A (BRIEF "Plan" step 6; decision 0036).

For each held-out play, the k most similar earlier plays (same population, every field of the live set on one
standardized scale, a missing value its own column) and what happened on them. Scored like the build: walk-forward
by season (train on the seasons before, test 2023 and 2024; pressure only 2024), the share of the base rate's
squared error removed, and log loss or the mean pinball of q10-q90 against the shipped rung of the backtest.

Claude's expectation, written before the run: C is weaker than A on every outcome (a plain distance weighs the
hash as much as the down), by 0.5 to 2 points of share on the strong outcomes (depth of target, time to throw)
and about level on the weak ones; 70% that it never beats A's shipped rung.

Run: .venv/Scripts/python.exe projects/context-live/explore/plays_like_this.py > projects/context-live/explore/plays_like_this.txt
"""

import json

import numpy as np
import polars as pl
from sklearn.neighbors import NearestNeighbors

from pcf.experts.context_live import plays, run
from pcf.experts.context_live.models import LEVELS, matrix
from pcf.experts.context_live.outcomes import get

c = pl.col
NAMES = ["run_success_prob", "rush_yards_exp", "pressure_prob", "sack_prob", "time_to_throw_exp", "dropback_success_prob", "air_yards_exp", "completion_prob"]
KS = (100, 300, 1000)


def design(train: pl.DataFrame, test: pl.DataFrame, fields: list[str]) -> tuple[np.ndarray, np.ndarray]:
    xa, xb = matrix(train, fields), matrix(test, fields)
    miss_a, miss_b = np.isnan(xa), np.isnan(xb)
    keep = miss_a.any(axis=0)
    med = np.nanmedian(np.where(miss_a.all(axis=0), 0, xa), axis=0)
    xa, xb = np.where(miss_a, med, xa), np.where(miss_b, med, xb)
    mu, sd = xa.mean(axis=0), xa.std(axis=0)
    sd[sd == 0] = 1
    xa, xb = (xa - mu) / sd, (xb - mu) / sd
    return (np.hstack([xa, miss_a[:, keep].astype(float)]), np.hstack([xb, miss_b[:, keep].astype(float)]))


def main():
    data = run.load([2022, 2023, 2024])
    shipped = json.loads((run.cache_dir() / "backtest" / "results.json").read_text())
    fields = plays.FIELD_SETS["live"]
    out = {}
    for name in NAMES:
        o = get(name)
        top = shipped[name]["choice"]["shipped"]
        scored = pl.read_parquet(run.cache_dir() / "backtest" / f"{name}.parquet")
        rows = []
        for s in run.test_seasons_for(o, [2023, 2024]):
            train, test = run.training_rows(data, o, s), o.rows(data.filter(c("season") == s))
            xa, xb = design(train, test, fields)
            nn = NearestNeighbors(n_neighbors=max(KS)).fit(xa)
            _, idx = nn.kneighbors(xb)
            y = train["y"].to_numpy().astype(float)
            frame = test.select("game_id", "play_id", "season", "week", "y")
            for k in KS:
                near = y[idx[:, :k]]
                frame = frame.with_columns(pl.Series(f"k{k}:mean", near.mean(axis=1)))
                if o.kind == "amount":
                    for q, level in LEVELS.items():
                        frame = frame.with_columns(pl.Series(f"k{k}:{q}", np.quantile(near, level, axis=1)))
            rows.append(frame)
        f = pl.concat(rows).join(scored.select("game_id", "play_id", c(f"{top}:mean").alias("A:mean"), c(f"{top}:loss").alias("A:loss"), *([c(f"{top}:{q}").alias(f"A:{q}") for q in LEVELS] if o.kind == "amount" else [])), on=["game_id", "play_id"])
        base = float(((f["y"] - scored["0-base:mean"].mean()) ** 2).mean())
        res = {"shipped": top, "rows": f.height, "A_share": 100 * (1 - float(((f["y"] - f["A:mean"]) ** 2).mean()) / base), "A_loss": float(f["A:loss"].mean())}
        for k in KS:
            p = f[f"k{k}:mean"]
            res[f"k{k}_share"] = 100 * (1 - float(((f["y"] - p) ** 2).mean()) / base)
            if o.kind == "probability":
                pc = p.clip(1e-4, 1 - 1e-4)
                res[f"k{k}_loss"] = float(-(f["y"] * pc.log() + (1 - f["y"]) * (1 - pc).log()).mean())
            else:
                pin = sum(((f["y"] - f[f"k{k}:{q}"]) * (lv - (f["y"] < f[f"k{k}:{q}"]).cast(float))).mean() for q, lv in LEVELS.items()) / 3
                res[f"k{k}_loss"] = float(pin)
        # agreement between the two methods: how alike their forecasts are, play by play
        res["corr_A_k300"] = float(np.corrcoef(f["A:mean"].to_numpy(), f["k300:mean"].to_numpy())[0, 1])
        out[name] = res
        print(f"{o.label:28} A ({top}) share {res['A_share']:6.2f} loss {res['A_loss']:.4f} | " + " | ".join(f"k={k} share {res[f'k{k}_share']:6.2f} loss {res[f'k{k}_loss']:.4f}" for k in KS) + f" | corr(A, k300) {res['corr_A_k300']:.2f}", flush=True)
    (run.cache_dir() / "backtest" / "plays_like_this.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
