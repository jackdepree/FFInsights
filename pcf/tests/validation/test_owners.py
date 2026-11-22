"""owners: the main team's tie-break, season pairs and share kept (synthetic)."""

import numpy as np
import polars as pl

from pcf.validation import owners

c = pl.col


def test_main_team_breaks_ties_the_same_way_every_time():
    roster = pl.DataFrame({
        "gsis_id": ["p"] * 4 + ["q"] * 3, "season": [2020] * 7,
        "team": ["NYJ", "BUF", "NYJ", "BUF", "KC", "KC", "LV"], "position": ["QB"] * 4 + ["WR"] * 3,
    })  # fmt: skip
    field = pl.DataFrame({"gsis_id": ["q", "q"], "season": [2020, 2020], "position": ["SWR"] * 2})
    for order in (np.arange(7), np.arange(7)[::-1], np.array([3, 0, 5, 1, 6, 2, 4])):
        out = owners.main_team(roster[order], field)
        # two games each: the code first in the alphabet
        assert out.filter(c("pid") == "p")["team"].item() == "BUF"
        assert out.filter(c("pid") == "q")["team"].item() == "KC"
        assert out.filter(c("pid") == "q")["position"].item() == "SWR"
        assert out.filter(c("pid") == "p")["position"].item() == "QB"


def synthetic_pairs(n: int = 400, kept_by_movers: float = 1.0, seed: int = 0) -> pl.DataFrame:
    """Players with a true trait over two seasons; movers keep `kept_by_movers` of it."""
    rng = np.random.default_rng(seed)
    trait = rng.normal(0, 1, n)
    moved = rng.random(n) < 0.3
    rows = []
    for i in range(n):
        for s in (2020, 2021):
            t = trait[i] if (s == 2020 or not moved[i]) else kept_by_movers * trait[i]
            team = "A" if (s == 2020 or not moved[i]) else "B"
            rows.append({"pid": f"p{i}", "season": s, "team": team, "n": 100.0,
                         "x": 100 * (t + rng.normal(0, 0.7))})  # fmt: skip
    return pl.DataFrame(rows)


def test_share_kept_tells_a_players_trait_from_a_teams():
    for keep, lo, hi in ((1.0, 0.7, 1.3), (0.0, -0.5, 0.4)):
        g = synthetic_pairs(kept_by_movers=keep)
        teams = g.select("pid", "season", "team")
        p = owners.season_pairs(g, ["x", "n"], "n", 50, {"rate": ("x", "n")}, teams)
        assert p["moved"].sum() > 50
        k = owners.kept(p, "rate", draws=200)
        assert k["repeat"] > 0.3
        assert lo < k["share_kept"] < hi
        assert k["passes"] == (keep == 1.0)


def test_the_floor_and_the_next_season():
    g = pl.DataFrame({"pid": ["a", "a", "b", "b"], "season": [2020, 2021, 2020, 2021],
                      "team": ["X", "Y", "X", "X"], "n": [200.0, 200.0, 10.0, 200.0],
                      "x": [20.0, 30.0, 1.0, 2.0]})  # fmt: skip
    p = owners.season_pairs(g, ["x", "n"], "n", 150, {"rate": ("x", "n")},
                            g.select("pid", "season", "team"))  # fmt: skip
    assert p.height == 1  # b's 2020 is under the floor; nobody has a 2022
    assert p["moved"].item() is True
    assert p["rate_n"].item() == 0.15
