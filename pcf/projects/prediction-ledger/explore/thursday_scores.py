"""What moving the run to Thursday noon did to the scores (2026-11-06), 2016-2024 only: the vault
stays closed. Each champion's backtest after the move against the same model before it.
Run from pcf/: .venv/Scripts/python.exe projects/prediction-ledger/explore/thursday_scores.py

A negative difference means the score got better. Every later forecast can change a little, since
the models also train on the moved rows, so all rows are shown as well as the moved ones.
"""

import polars as pl

from pcf.config import get_config
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.data.timeline.calendar import ET
from pcf.validation import scores
from pcf.validation.backtest import targets
from pcf.validation.compare import compare

c = pl.col
KEYS = ["gsis_id", "game_id"]
# The latest runs before the move
BEFORE = {
    "last_game": "83781e55355d4a2e8b6a8246d6c45eac",
    "trees_week": "5a1155eaf7a94883a265e6d62b407e00",
    "active": "870a5bd627e449a39dfcce141e40d00e",
    "lasso_h3": "bec70f2c10e1441ea1bfeedea7b9075a",
    "lasso_rest": "8367568c3f5b4426be20bd4192d93d8f",
}
DAYS = {"Thursday": [4], "Wednesday and Friday": [3, 5], "other days": [1, 2, 6, 7]}


def main() -> None:
    gw = Gateway()
    base = get_config().zone("outputs") / "participation"
    days = gw.calendar.games.select(
        "game_id",
        day=c("kickoff").dt.convert_time_zone(ET).dt.weekday(),
        step=c("game_id").str.slice(0, 7),
    )
    for variant, before in BEFORE.items():
        e = find("participation", variant)()
        y = targets(e, gw).select(*KEYS, "y")
        folder = base / variant
        runs = sorted(
            (p for p in folder.iterdir() if (p / "history.parquet").exists()),
            key=lambda p: p.stat().st_mtime,
        )
        after = runs[-1].name
        loss = {}
        for name, run in (("before", before), ("after", after)):
            h = pl.read_parquet(folder / run / "history.parquet")
            loss[name] = (
                scores.row_losses(h.join(y, on=KEYS), e.kind)
                .filter(c("y").is_not_null())
                .join(days, on="game_id")
            )
        print(f"\n{variant}: run {after}, rows {loss['after'].height:,}")
        a, b = loss["after"], loss["before"]
        moved = a.join(b.select(*KEYS, was="as_of"), on=KEYS).filter(c("as_of") != c("was"))
        print(f"  rows whose as_of moved: {moved.height:,}")
        groups = {"all": c("y").is_not_null()}
        groups.update({k: c("day").is_in(v) for k, v in DAYS.items()})
        for g, f in groups.items():
            x, z = a.filter(f), b.filter(f)
            r = compare(x, z, KEYS, "step", ("after", "before"))
            print(
                f"  {g:<22} {z['loss'].mean() * 100:.3f} -> {x['loss'].mean() * 100:.3f}, "
                f"{r.diff * 100:+.3f} ({r.lo * 100:+.3f} to {r.hi * 100:+.3f}): "
                f"{r.verdict}, {r.rows:,} rows"
            )


if __name__ == "__main__":
    main()
