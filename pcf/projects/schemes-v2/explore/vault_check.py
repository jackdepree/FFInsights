"""The vault (2025), opened once on 2026-11-10 for schemes-v2's final models: each against the
league's level (rung 0) on the same rows, intervals by week. Reads the vault runs' saved histories
(`pcf backtest schemes-v2 --variant <v> --seasons 2025 --open-vault`).

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/vault_check.py
"""

# ruff: noqa: E501
from __future__ import annotations

import polars as pl
from rung2_check import history, line, scored

from pcf.data.tables import load

c = pl.col
FINAL = {"pass_oe_rung2": "pass_oe_league", "shotgun_rung2": "shotgun_league", "depth_rung2": "depth_league",
         "tempo_shrunk": "tempo_league", "pass_gain_blend": "pass_gain_league"}  # fmt: skip


def main() -> None:
    tg = load("team_game", parts=["pregame", "tendencies"])
    for final, league in FINAL.items():
        a = scored(history(final, vault=True), tg).filter(c("game_id").str.starts_with("2025"))
        b = scored(history(league, vault=True), tg).filter(c("game_id").str.starts_with("2025"))
        inside = a.select(((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean()).item()
        print(f"== {final} against {league}, 2025 (ranges hold {inside:.1%})")
        print(line("vault", a, b))
        print(f"   prediction against result r: {a.select(pl.corr('mean', 'y')).item():+.3f}")


if __name__ == "__main__":
    main()
