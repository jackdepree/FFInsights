"""Team yards allowed: file each saved team-yards-gained history under the defense.

The same numbers seen from the other side (exploration F2, decision 0037): for every run saved
under outputs/crude-forecaster/team_*/, writes allowed.parquet next to its history.parquet.

    .venv/Scripts/python.exe projects/crude-forecaster/build/allowed_run.py
"""

import polars as pl

from pcf.baselines.crude.yardstick import allowed
from pcf.config import get_config


def main() -> None:
    root = get_config().zone("outputs") / "crude-forecaster"
    for history in sorted(root.glob("team_*/*/history.parquet")):
        h = pl.read_parquet(history)
        a = allowed(h)
        a.write_parquet(history.with_name("allowed.parquet"))
        print(f"{history.parent.parent.name}/{history.parent.name}: {a.height} rows, quantities {a['quantity'].unique().to_list()}")


if __name__ == "__main__":
    main()
