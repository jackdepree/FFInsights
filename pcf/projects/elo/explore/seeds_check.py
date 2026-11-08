"""Check `pcf.data.standings` against the real playoffs, 2002-2024: seeds from every regular-season
result must give the actual wild-card games (the higher seed at home), the actual byes, and the
1 seed hosting the lowest seed left in the divisional round. Then: how many teams were seed
locked or eliminated going into the final week.

Run from pcf/: .venv/Scripts/python.exe projects/elo/explore/seeds_check.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import carryover as C  # noqa: E402

from pcf.data import standings as S  # noqa: E402

c = pl.col


def main() -> None:
    g = C.games()
    bad, locked, elim = [], 0, 0
    for season in range(2002, C.LAST + 1):
        reg = g.filter(
            (c("season") == season) & (c("game_type") == "REG") & c("home_score").is_not_null()
        )
        try:
            sd = S.seeds(S._games(reg), season)
        except S.Unresolved as e:
            bad.append(f"{season}: unresolved tie {e}")
            continue
        wc = g.filter((c("season") == season) & (c("game_type") == "WC"))
        for h, a in wc.select("home_team", "away_team").iter_rows():
            n = S.playoff_spots(season)
            if (
                sd.get(h) is None
                or sd.get(a) is None
                or sd[h] + sd[a] != n + (2 if n == 6 else 2) + (1 if n == 6 else 0)
                or sd[h] > sd[a]
            ):
                bad.append(f"{season} WC {a}@{h}: seeds {sd.get(a)}@{sd.get(h)}")
        byes = {t for t, s in sd.items() if s <= (2 if season < 2020 else 1)}
        in_wc = set(wc["home_team"]) | set(wc["away_team"])
        if byes & in_wc or len(set(sd) - in_wc) != len(byes):
            bad.append(f"{season}: byes {sorted(byes)}, not in WC {sorted(set(sd) - in_wc)}")
        div = g.filter((c("season") == season) & (c("game_type") == "DIV"))
        for conf in ("AFC", "NFC"):
            one = next(t for t, s in sd.items() if s == 1 and S.CONFERENCE[t] == conf)
            row = div.filter((c("home_team") == one) | (c("away_team") == one))
            if row.height == 1:
                opp = row["away_team"][0] if row["home_team"][0] == one else row["home_team"][0]
                left = [
                    t
                    for t in set(div["home_team"]) | set(div["away_team"])
                    if S.CONFERENCE[t] == conf
                ]
                if row["home_team"][0] != one or sd[opp] != max(sd[t] for t in left):
                    bad.append(
                        f"{season} {conf}: 1 seed {one} hosted {opp} (seed {sd[opp]}); left {sorted((sd[t], t) for t in left)}"
                    )
        # locks going into the final week
        moment = g.filter(
            (c("season") == season) & (c("game_type") == "REG") & (c("week") == reg["week"].max())
        )["kickoff"].min()
        lk = S.final_week_locks(g, season, moment)
        locked += int(lk["seed_locked"].sum())
        elim += int(lk["eliminated"].sum())
        names = lk.filter(c("seed_locked") == 1)["team"].to_list()
        print(f"   {season}: locked {', '.join(names) or '-'}")
    print(f"\n== {len(bad)} mismatches with the real playoffs, 2002-2024")
    for b in bad:
        print("   " + b)
    print(f"== going into the final week: {locked} seed-locked team-seasons, {elim} eliminated")


if __name__ == "__main__":
    main()
