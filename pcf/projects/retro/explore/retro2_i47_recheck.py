# ruff: noqa: E501
"""Retro 2's backlog (2026-11-20): I47's in-season flags against every other team-game.

I47's `gap` drops rows whose flag is null, and its two in-season flags ("starting QB changed in
season", "head coach changed in season") are null for every team-game before any change in that
season. So those two rows were compared only with the same teams' other games after a change,
not with every team. Here the nulls are False and the same gap is computed against all team-games
in the same weeks. Discovery only, 2016-2024.

Run from pcf/:  python projects/retro/explore/retro2_i47_recheck.py > projects/retro/explore/retro2_i47_recheck.txt
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
spec = importlib.util.spec_from_file_location("i47", Path(__file__).with_name("i47_change_lens.py"))
i47 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i47)
INSEASON = [
    "starting QB changed in season, games 1-4 after",
    "starting QB changed in season, games 5 on after",
    "head coach changed in season, games 1-4 after",
]


def main() -> None:
    gateway = Gateway()
    te = i47.team_events(gateway.source)
    rng = np.random.default_rng(get_config().seed)
    rows = []
    for project, variant in [
        ("team-efficiency", "off_next3_ridge"),
        ("team-efficiency", "def_next3_ridge"),
        ("elo", "margin"),
        ("pace", "dropbacks_full"),
    ]:
        h = i47.history(project, variant, gateway)
        if "team" not in h.columns:
            h = h.join(te.select("game_id", "team", "home"), on="game_id").with_columns(
                miss=pl.when(c("home")).then(c("miss")).otherwise(-c("miss"))
            )
        d = h.join(te.drop("home"), on=["game_id", "team"]).filter(c("season") <= i47.LAST_SEASON)
        for f in INSEASON:
            for base, dd in (
                ("I47's (teams after a change)", d),
                ("every team-game", d.with_columns(c(f).fill_null(False))),
            ):
                r = i47.gap(dd, f, rng)
                if r:
                    rows.append({"expert": f"{project}/{variant}", "change": f, "compared with": base,
                                 **{k: r[k] for k in ("rows", "gap", "lo90", "hi90", "seasons_same_sign", "clear99")}})  # fmt: skip
    pl.Config.set_tbl_rows(50)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(240)
    pl.Config.set_fmt_str_lengths(60)
    pl.Config.set_float_precision(4)
    print(pl.DataFrame(rows))


if __name__ == "__main__":
    main()
