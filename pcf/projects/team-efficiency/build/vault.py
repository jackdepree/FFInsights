"""team-efficiency: the vault (2025), opened once on the champion (VALIDATION.md section 1).

The champion's four forecasts were validated with `--open-vault` (offense from `change`, defense
from `ridge`), so their latest histories hold 2025. This scores 2025 alone, the way summary.py
scores 2016-2024: skill against each baseline (whose 2025 predictions are made here by the same
walk-forward backtest, trained only on the seasons before), the q10-q90 coverage, and the same
numbers for 2016-2024 beside it. Reported as-is.
Writes vault.txt beside this file. Run from pcf/ after the four vault runs:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/build/vault.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import summary as S  # noqa: E402

from pcf.data.tables.store import read_part  # noqa: E402
from pcf.experts.team_efficiency import features as F  # noqa: E402
from pcf.experts.team_efficiency.model import VARIANTS  # noqa: E402
from pcf.validation import backtest  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
VAULT = 2025
CHAMPION = ("off_next3_change", "off_rest_change", "def_next3_ridge", "def_rest_ridge")


def _weeks(seasons: list[int]) -> pl.DataFrame:
    return read_part("team_game", "schedule", seasons=seasons).select(
        "game_id", "team", "week"
    ).collect()  # fmt: skip


def _prep(h: pl.DataFrame, y: pl.DataFrame, weeks: pl.DataFrame) -> pl.DataFrame:
    if "y" not in h.columns:
        h = h.join(y, on=["game_id", "team"], how="inner")
    h = h.join(weeks, on=["game_id", "team"], how="left")
    return h.with_columns(season=c("game_id").str.slice(0, 4).cast(pl.Int32)).drop_nulls("y")


def main() -> None:
    lines = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    tg = S.load("team_game", parts=["schedule", "efficiency"])
    weeks = _weeks(list(range(2016, VAULT + 1)))
    say(f"The vault ({VAULT}), opened once on the champion, against 2016-2024. Skill = share of")
    say("squared error removed against the baseline; 90% interval from resampling weeks.")
    for v in CHAMPION:
        side, horizon, _ = v.split("_")
        y = F.targets(tg, side, horizon).select("game_id", "team", "y")
        champ = S.latest(v)
        if champ is None or champ.filter(c("game_id").str.starts_with(str(VAULT))).is_empty():
            say(f"\n{v}: no {VAULT} rows yet (run it with --open-vault)")
            continue
        champ = _prep(champ, y, weeks)
        say("")
        say(f"{v}: baseline | {VAULT} | 2016-2024 | {VAULT} weeks 1-4")
        for b in VARIANTS[v].baselines():
            bh = backtest.run(b(), seasons=[VAULT], open_vault=True).history
            past = S.latest(b.variant)
            bh = _prep(bh, y, weeks)
            past = _prep(past, y, weeks).filter(c("season") < VAULT) if past is not None else None
            now = champ.filter(c("season") == VAULT)
            before = champ.filter(c("season") < VAULT)
            old = S.fmt(S.skill(before, past)) if past is not None else "n/a"
            say(f"  {b.variant:18s} {S.fmt(S.skill(now, bh))} | {old} | "
                f"{S.fmt(S.skill(now.filter(c('week') <= 4), bh))}")  # fmt: skip
        for nm, x in (("2025", champ.filter(c("season") == VAULT)),
                      ("2016-2024", champ.filter(c("season") < VAULT))):  # fmt: skip
            cover = x.select(((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean()).item()
            say(f"  q10-q90 holds, {nm}: {cover:.1%} of {x.height:,} rows")
    (HERE / "vault.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
