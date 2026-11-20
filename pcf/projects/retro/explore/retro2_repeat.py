# ruff: noqa: E501
"""Retro 2's backlog (2026-11-20), the "does it repeat?" group: IDEAS I44, I53 and I16.

Discovery only, 2016-2024 (the 2025 vault and 2026 left out). Each is a season-to-season
question about a player, with a shuffled null, so they share one script.

- I44 clutch: a player's EPA on high-stakes plays (snap-leverage's flag) minus his EPA on the
  rest, season to season; the null shuffles the flag within each player-season.
- I53 which usage rates travel with a player: target share, target depth (air yards per target),
  carry share and goal-line share (carries inside the 5), for players who changed teams against
  those who stayed; the new team's slot (its top player at the position the season before) as
  the control.
- I16 script tendencies: within a player-season, the slope of his snap share on his team's
  final margin; season to season, with a null that shuffles margins within team-seasons.

Run from pcf/:  python projects/retro/explore/retro2_repeat.py > projects/retro/explore/retro2_repeat.txt
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
FIRST, LAST = 2016, 2024
SHUFFLES = 200


def r(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    return float(np.corrcoef(x[ok], y[ok])[0, 1]) if ok.sum() > 10 else float("nan")


def pairs(d: pl.DataFrame, key: str, val: str) -> pl.DataFrame:
    """Season s and s+1 values for the same key."""
    nxt = d.select(key, (c("season") - 1).alias("season"), c(val).alias("next"))
    return d.join(nxt, on=[key, "season"])


def player_team(src) -> pl.DataFrame:
    """Each player-season's main team and position (most games)."""
    ro = src.part("player_game", "roster").filter(c("season").is_between(FIRST, LAST))
    snaps = src.part("player_game", "snaps").select("gsis_id", "game_id", "offense_snaps")
    ro = ro.join(snaps, on=["gsis_id", "game_id"]).filter(c("offense_snaps") > 0)
    return (
        ro.group_by("gsis_id", "season", "team", "position")
        .agg(n=pl.len())
        .sort("n", descending=True)
        .group_by("gsis_id", "season", maintain_order=True)
        .first()
        .drop("n")
    )


# ---------------------------------------------------------------- I44
def clutch(src, rng) -> pl.DataFrame:
    p = src.part("play", "pbp").filter(c("season_type") == "REG").select(
        "game_id", "play_id", "epa", "qb_dropback", "rush_attempt", "pass_attempt", "sack",
        "passer_player_id", "rusher_player_id", "receiver_player_id", "qb_scramble",
    )  # fmt: skip
    lev = src.part("play", "leverage").filter(c("season").is_between(FIRST, LAST))
    p = p.join(lev.select("game_id", "play_id", "season", "high_stakes"), on=["game_id", "play_id"])
    p = p.drop_nulls("epa").with_columns(hs=c("high_stakes").cast(pl.Boolean))
    roles = {
        "QB dropbacks": (p.filter(c("qb_dropback") == 1), "passer_player_id", 40),
        "RB carries": (p.filter((c("rush_attempt") == 1) & (c("qb_scramble") == 0)), "rusher_player_id", 20),
        "targets": (p.filter((c("pass_attempt") == 1) & (c("sack") == 0)), "receiver_player_id", 15),
    }  # fmt: skip
    out = []
    for name, (d, who, min_hs) in roles.items():
        d = d.drop_nulls(who).select(c(who).alias("pid"), "season", "epa", "hs")
        enough = d.group_by("pid", "season").agg(nh=c("hs").sum(), nn=(~c("hs")).sum())
        enough = enough.filter((c("nh") >= min_hs) & (c("nn") >= 3 * min_hs))
        d = d.join(enough.select("pid", "season"), on=["pid", "season"])

        def score(dd: pl.DataFrame) -> pl.DataFrame:
            s = dd.group_by("pid", "season").agg(
                cl=c("epa").filter(c("hs")).mean() - c("epa").filter(~c("hs")).mean(),
                ordinary=c("epa").filter(~c("hs")).mean(),
            )
            return pairs(s.with_columns(key=c("pid")), "pid", "cl").join(
                pairs(s, "pid", "ordinary").select(
                    "pid", "season", ord_next="next", ord=c("ordinary")
                ),
                on=["pid", "season"],
            )

        s = score(d)
        real = r(s["cl"], s["next"])
        null = []
        for _ in range(SHUFFLES // 2):
            # the flag shuffled within each player-season
            null.append(r(*_shuffled_pairs(d, rng, score)))
        null = np.array(null)
        out.append({"role": name, "player_seasons_paired": s.height, "clutch_r": real,
                    "null_95th": float(np.nanquantile(null, 0.95)), "beats_null": f"{(null < real).mean():.0%}",
                    "ordinary_r (for scale)": r(s["ord"], s["ord_next"])})  # fmt: skip
    return pl.DataFrame(out)


def _shuffled_pairs(d: pl.DataFrame, rng, score):
    g = d.sort("pid", "season")
    keys = (g["pid"] + "_" + g["season"].cast(pl.Utf8)).to_numpy()
    hs = g["hs"].to_numpy().copy()
    bounds = np.flatnonzero(keys[1:] != keys[:-1]) + 1
    for idx in np.split(np.arange(len(hs)), bounds):
        hs[idx] = rng.permutation(hs[idx])
    s = score(g.with_columns(hs=pl.Series(hs)))
    return s["cl"], s["next"]


# ---------------------------------------------------------------- I53
def usage(src) -> pl.DataFrame:
    pt = player_team(src)
    p = src.part("play", "pbp").filter(c("season_type") == "REG").select(
        "game_id", "posteam", "yardline_100", "rush_attempt", "qb_scramble", "pass_attempt", "sack",
        "air_yards", "rusher_player_id", "receiver_player_id",
    )  # fmt: skip
    sch = src.part("game", "schedule").select("game_id", "season")
    p = p.join(sch, on="game_id").filter(c("season").is_between(FIRST, LAST))
    runs = p.filter((c("rush_attempt") == 1) & (c("qb_scramble") == 0))
    tg = p.filter((c("pass_attempt") == 1) & (c("sack") == 0))
    # team totals per game, so a share counts only the games he played
    team_g = (
        runs.group_by("game_id", "posteam")
        .agg(t_car=pl.len(), t_gl=(c("yardline_100") <= 5).sum())
        .join(tg.group_by("game_id", "posteam").agg(t_tgt=pl.len()), on=["game_id", "posteam"], how="full", coalesce=True)
        .fill_null(0)
    )  # fmt: skip
    pl_car = (
        runs.drop_nulls("rusher_player_id")
        .group_by("game_id", "posteam", pid="rusher_player_id")
        .agg(car=pl.len(), gl=(c("yardline_100") <= 5).sum())
    )
    pl_tgt = (
        tg.drop_nulls("receiver_player_id")
        .group_by("game_id", "posteam", pid="receiver_player_id")
        .agg(tgt=pl.len(), air=c("air_yards").sum())
    )
    g = pl_car.join(pl_tgt, on=["game_id", "posteam", "pid"], how="full", coalesce=True).fill_null(
        0
    )
    g = g.join(team_g, on=["game_id", "posteam"]).join(sch, on="game_id")
    s = g.group_by("pid", "season", team="posteam").agg(
        c("car").sum(), c("gl").sum(), c("tgt").sum(), c("air").sum(),
        c("t_car").sum(), c("t_gl").sum(), c("t_tgt").sum(), games=pl.len(),
    )  # fmt: skip
    s = s.join(pt.rename({"gsis_id": "pid"}), on=["pid", "season", "team"])  # his main team only
    s = s.with_columns(
        target_share=c("tgt") / c("t_tgt"),
        target_depth=c("air") / c("tgt"),
        carry_share=c("car") / c("t_car"),
        goal_line_share=c("gl") / c("t_gl"),
    )
    rates = {
        "target share (WR, TE, RB; 40+ targets)": (
            "target_share",
            ["WR", "TE", "RB"],
            c("tgt") >= 40,
        ),
        "target depth (WR, TE; 40+ targets)": ("target_depth", ["WR", "TE"], c("tgt") >= 40),
        "carry share (RB; 50+ carries)": ("carry_share", ["RB"], c("car") >= 50),
        "goal-line share (RB; 50+ carries)": ("goal_line_share", ["RB"], c("car") >= 50),
    }
    out = []
    for name, (col, pos, vol) in rates.items():
        d = s.filter(c("position").is_in(pos) & vol & (c("games") >= 6))
        # the slot: the team's top-volume player at the position, his rate that season
        slot = (
            d.with_columns(vol_=c("tgt") + c("car"))
            .sort("vol_", descending=True)
            .group_by("team", "season", "position", maintain_order=True)
            .first()
            .select("team", "position", (c("season") + 1).alias("season"), slot=c(col))
        )
        nxt = d.select("pid", (c("season") - 1).alias("season"), next=c(col), new_team=c("team"))
        x = d.join(nxt, on=["pid", "season"]).with_columns(moved=c("team") != c("new_team"))
        x = x.join(slot.rename({"team": "new_team", "season": "season_next"}),
                   left_on=["new_team", "position", (c("season") + 1)],
                   right_on=["new_team", "position", "season_next"], how="left")  # fmt: skip
        mv, st = x.filter(c("moved")), x.filter(~c("moved"))
        row = {"rate": name, "movers": mv.height, "stayers": st.height,
               "stayers_r": r(st[col], st["next"]), "movers_r": r(mv[col], mv["next"])}  # fmt: skip
        row["share_kept"] = row["movers_r"] / row["stayers_r"]
        m = mv.drop_nulls(["slot", col, "next"])
        if m.height > 30:
            z = lambda v: (v - v.mean()) / v.std()  # noqa: E731
            X = np.column_stack([np.ones(m.height), z(m[col].to_numpy()), z(m["slot"].to_numpy())])
            b = np.linalg.lstsq(X, z(m["next"].to_numpy()), rcond=None)[0]
            row |= {"movers_with_slot": m.height, "own_weight": b[1], "slot_weight": b[2]}
        out.append(row)
    return pl.DataFrame(out)


# ---------------------------------------------------------------- I16
def script(src, rng) -> pl.DataFrame:
    pt = player_team(src)
    sn = src.part("player_game", "snaps").filter(c("season").is_between(FIRST, LAST))
    ro = src.part("player_game", "roster").select("gsis_id", "game_id", "team")
    res = src.part("team_game", "result").select("game_id", "team", "margin")
    typ = src.part("game", "schedule").select("game_id", "game_type")
    d = (
        sn.join(ro, on=["gsis_id", "game_id"])
        .join(res, on=["game_id", "team"])
        .join(typ, on="game_id")
        .filter((c("game_type") == "REG") & (c("offense_snaps") > 0))
        .join(pt, on=["gsis_id", "season", "team"])
        .filter(c("position").is_in(["RB", "WR", "TE"]))
    )

    def tend(dd: pl.DataFrame) -> pl.DataFrame:
        t = dd.group_by("gsis_id", "season", "position").agg(
            n=pl.len(),
            slope=pl.cov("offense_pct", "margin") / c("margin").var(),
            share=c("offense_pct").mean(),
        )
        t = t.filter((c("n") >= 8) & (c("share") >= 0.25))
        return pairs(t, "gsis_id", "slope")

    out = []
    base = tend(d)
    for pos in ["RB", "WR", "TE"]:
        b = base.filter(c("position") == pos)
        real = r(b["slope"], b["next"])
        null = []
        for _ in range(SHUFFLES // 2):
            # shuffle margins among the team-season's games (same for every teammate)
            m = d.select("team", "season", "game_id", "margin").unique()
            m = m.with_columns(
                margin=c("margin").shuffle(seed=int(rng.integers(1 << 30))).over("team", "season")
            )
            dd = d.drop("margin").join(
                m.select("game_id", "team", "margin"), on=["game_id", "team"]
            )
            bb = tend(dd).filter(c("position") == pos)
            null.append(r(bb["slope"], bb["next"]))
        null = np.array(null)
        out.append({"position": pos, "player_seasons_paired": b.height, "tendency_r": real,
                    "null_95th": float(np.nanquantile(null, 0.95)), "beats_null": f"{(null < real).mean():.0%}"})  # fmt: skip
    return pl.DataFrame(out)


def main() -> None:
    src = Gateway().source
    rng = np.random.default_rng(get_config().seed)
    pl.Config.set_tbl_rows(50)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(240)
    pl.Config.set_fmt_str_lengths(50)
    pl.Config.set_float_precision(3)
    print(f"Seasons {FIRST}-{LAST}, regular season; r = season-to-season correlation\n")
    print("== I44 clutch: EPA on high-stakes plays minus the rest, season to season")
    print(clutch(src, rng))
    print("\n== I53 usage rates: movers against stayers (share_kept = movers_r / stayers_r);")
    print(
        "   own_weight and slot_weight: standardized weights on the mover's old rate and the new team's slot"
    )
    print(usage(src))
    print("\n== I16 script tendencies: slope of snap share on the final margin, season to season")
    print(script(src, rng))


if __name__ == "__main__":
    main()
