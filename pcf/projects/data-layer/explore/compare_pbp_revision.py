"""Light exploration for data-layer: does a play-by-play re-upload change past values?

Compares an earlier pull of 2023 play-by-play kept in old/data/ (read only) with the current
nflverse file, which was re-uploaded on 2026-02-12. Prints row counts and, for every shared
column, how many plays changed.

Run from pcf/:  uv run python projects/data-layer/explore/compare_pbp_revision.py
"""

import nflreadpy as nfl
import polars as pl

from pcf.config import PCF_DIR

OLD_FILE = PCF_DIR.parent / "old" / "data" / "play_by_play_2023.csv"
KEYS = ["game_id", "play_id"]


def main() -> None:
    old = pl.read_csv(OLD_FILE, infer_schema_length=0, null_values=["NA", ""])
    new = nfl.load_pbp(2023)
    new = new.with_columns(pl.all().cast(pl.String))
    # play_id is "1" in the CSV but "1.0" once the parquet float becomes text.
    pid = pl.col("play_id").cast(pl.Float64).cast(pl.Int64)
    old, new = old.with_columns(pid), new.with_columns(pid)
    print(f"old copy: {old.height:,} plays x {old.width} cols | current: {new.height:,} x {new.width}")
    print(f"columns only in old: {sorted(set(old.columns) - set(new.columns))}")
    print(f"columns only in current: {sorted(set(new.columns) - set(old.columns))}")

    both = old.join(new, on=KEYS, how="inner", suffix="__new")
    print(f"plays in both: {both.height:,} | only old: {old.height - both.height:,} "
          f"| only current: {new.height - both.height:,}")

    rows = []
    for c in sorted((set(old.columns) & set(new.columns)) - set(KEYS)):
        a, b = pl.col(c), pl.col(f"{c}__new")
        # Numbers compare as floats (CSV text vs parquet text); everything else as text.
        num = a.cast(pl.Float64, strict=False), b.cast(pl.Float64, strict=False)
        is_num = both.select(num[0].is_not_null().sum()).item() > 0
        if is_num:
            diff = ((num[0] - num[1]).abs() > 1e-6) | (num[0].is_null() != num[1].is_null())
        else:
            diff = (a != b) | (a.is_null() != b.is_null())
        n = both.select(diff.fill_null(False).sum()).item()
        if n:
            rows.append((c, n))
    rows.sort(key=lambda r: -r[1])
    print(f"\nshared columns that changed on at least one play: {len(rows)}")
    for c, n in rows[:40]:
        print(f"  {c:<32} {n:>7,} plays ({n / both.height:.1%})")


if __name__ == "__main__":
    main()
