# ruff: noqa: E501
"""crude-forecaster spot-check of R7 (the CEO's pick, 2026-11-19): how small a gain can the
yardstick read?

R7 read a gain only above a "noise floor" built from one shuffled copy (participation's columns
for players, Elo's for teams) refit a few ways. The alternative here is a permutation null per
member: each expert's own columns shuffled together within each week, 19 times, each refit
through the same walk. An expert's gain counts at the 5% level only if it beats all 19 of its
shuffled selves (p = 1/20). Three readings are then compared, member by member:

  week interval   the 90% interval from resampled weeks clears zero (the table's verdict)
  R7 floor        the gain is above the table's floor (the shuffled copy's largest gain across
                  the refits in yardstick.txt §3)
  permutation     the gain beats all 19 of the member's own shuffled copies

Run from pcf/ (PCF_DATA_DIR set):
    python projects/crude-forecaster/build/spotcheck_r7.py > projects/crude-forecaster/build/spotcheck_r7.txt
"""

from __future__ import annotations

import time

import numpy as np
import polars as pl

from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config

c = pl.col
TABLES = [("passing", "next"), ("rushing", "next"), ("receiving", "next"), ("team", "next"), ("team", "next3"), ("passing", "next3")]
SHUFFLES = 19
OUT = get_config().zone("outputs") / "crude-forecaster" / "spotcheck_r7"
PROGRESS = get_config().zone("logs") / "crude-forecaster-progress.txt"
START = time.time()


def log(*parts) -> None:
    with PROGRESS.open("a", encoding="utf-8") as f:
        f.write(f"[{time.time() - START:7.0f}s] spotcheck " + " ".join(str(p) for p in parts) + "\n")


def shuffle_within_weeks(feats: pl.DataFrame, cols: list[str], seed: int) -> pl.DataFrame:
    """These columns shuffled together within each week (the rows keep everything else)."""
    order = feats.select("step").with_columns(
        row=pl.int_range(pl.len()), r=pl.int_range(pl.len()).shuffle(seed=seed).over("step")
    )
    perm = order.sort("step", "row")["row"].to_numpy()
    src = order.sort("step", "r")["row"].to_numpy()
    values = feats.select(cols).to_numpy()
    out = np.empty_like(values)
    out[perm] = values[src]
    return feats.with_columns(pl.Series(col, out[:, i]) for i, col in enumerate(cols))


def floor_from_noise(target: str, horizon: str) -> tuple[float, float]:
    """R7's floor for a table: the shuffled copy's largest added-alone gain (share, range score)
    across the refits of yardstick.txt §3, when §3 was run for it (next game only)."""
    path = get_config().zone("outputs") / "crude-forecaster" / "yardstick" / f"{target}_{horizon}" / "noise.parquet"
    if not path.exists():
        return float("nan"), float("nan")
    n = pl.read_parquet(path).filter(c("member") == Y.SHUFFLED)
    return float(n["alone"].max()), float(n["range_alone"].max())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    print("crude-forecaster spot-check of R7: each member against 19 shuffled copies of itself (within each week), lasso champion, rows expected to play, 2019-2024.")
    print("share = share of the crude forecast's squared error removed, added alone; range = range-score change. p = (1 + copies at least as good) / 20.")
    for target, horizon in TABLES:
        board = Y.load_board(target, horizon)  # the lasso (the champion everywhere)
        crude = board.forecast()
        groups = board.base.expert_groups()
        floor_share, floor_range = floor_from_noise(target, horizon)
        name = f"{target}_{horizon}"
        print(f"\n== {name} (R7 floor: share {100 * floor_share:+.2f}%, range {100 * floor_range:+.2f}%)")
        print(f"  {'member':<14}{'share (week 90%)':<30}{'copies: max / 2nd':<22}{'p':<7}{'range (week 90%)':<30}{'copies max':<12}{'p':<6} readings: week / R7 floor / permutation")
        for member, cols in groups.items():
            real = Y.gain(board.forecast((member,)), crude, board.keys)
            null_share, null_range = [], []
            for k in range(1, SHUFFLES + 1):
                feats = shuffle_within_weeks(board.features, cols, seed=1000 + k)
                g = Y.gain(board.forecast((member,), feats=feats), crude, board.keys)
                null_share.append(g.share)
                null_range.append(g.range_share)
            ns, nr = np.sort(null_share), np.sort(null_range)
            p_share = (1 + int((ns >= real.share).sum())) / (SHUFFLES + 1)
            p_range = (1 + int((nr >= real.range_share).sum())) / (SHUFFLES + 1)
            week = real.lo > 0
            r7 = bool(np.isfinite(floor_share) and real.share > floor_share)
            perm = p_share <= 0.05
            rows.append({
                "table": name, "member": member, "share": real.share, "lo": real.lo, "hi": real.hi,
                "range": real.range_share, "range_lo": real.range_lo, "range_hi": real.range_hi,
                "null_max": ns[-1], "null_2nd": ns[-2], "null_mean": ns.mean(), "null_sd": ns.std(ddof=1),
                "null_range_max": nr[-1], "p_share": p_share, "p_range": p_range,
                "floor_share": floor_share, "floor_range": floor_range,
                "week_reading": week, "r7_reading": r7, "perm_reading": perm,
            })  # fmt: skip
            print(f"  {member:<14}{100 * real.share:+.2f}% ({100 * real.lo:+.2f} to {100 * real.hi:+.2f}){'':<6}"
                  f"{100 * ns[-1]:+.2f} / {100 * ns[-2]:+.2f}{'':<9}{p_share:<7.2f}"
                  f"{100 * real.range_share:+.2f}% ({100 * real.range_lo:+.2f} to {100 * real.range_hi:+.2f}){'':<6}"
                  f"{100 * nr[-1]:+.2f}{'':<7}{p_range:<6.2f} {'yes' if week else 'no'} / {'yes' if r7 else ('n/a' if not np.isfinite(floor_share) else 'no')} / {'yes' if perm else 'no'}")
            log(name, member, "done")
        all_null = [r for r in rows if r["table"] == name]
        spread = np.mean([r["null_sd"] for r in all_null])
        print(f"  the copies' own spread (sd of a shuffled member's gain): {100 * spread:.2f} points on average")
    t = pl.DataFrame(rows)
    t.write_parquet(OUT / "permutation.parquet")
    print("\n== Where the readings disagree")
    for r in t.filter((c("week_reading") != c("perm_reading")) | (c("r7_reading") != c("perm_reading"))).iter_rows(named=True):
        print(f"  {r['table']:<16}{r['member']:<14} share {100 * r['share']:+.2f}%: week {'yes' if r['week_reading'] else 'no'}, R7 floor {'yes' if r['r7_reading'] else 'no'}, permutation {'yes' if r['perm_reading'] else 'no'} (p {r['p_share']:.2f}; copies up to {100 * r['null_max']:+.2f}%)")
    log("all done")


if __name__ == "__main__":
    main()
