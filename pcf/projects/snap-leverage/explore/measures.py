"""snap-leverage exploration (2026-11-14), step 2: the per-player measures, and their consistency.

Per player-game, from who was on the field (nflverse participation, `player_play.on_field`) and
step 1's leverage, 2016-2024 regular season:
- snap share: his share of his side's scored plays (passes, runs, kneels, spikes);
- leverage share: his share of the side's leverage (each snap weighted by its leverage index);
- high-stakes share: his share of the side's top-fifth plays by leverage;
- trust gap: high-stakes share minus snap share (raw: the situation not taken out);
- trust over expected: his high-stakes snaps minus the snaps his on-field rate in each kind of
  situation predicts, as a share of the side's high-stakes plays. The kind of situation is the
  offense's expected pass chance (pace's pcf_xpass, in fifths), so a third-down back or a nickel
  corner isn't counted as trusted just for playing the passing downs he always plays (H47).
Position groups: QB, RB (with FB), WR, TE, OL, DL, LB, CB, S. Starter = listed first at his
depth-chart spot that week (player_game.depth).

Consistency (`pcf.validation.consistency`) for every measure, on players with at least one
snap in a game, and on part-timers (snap share 10-90%) where the trust measures can move.
Writes `<interim>/snap-leverage/player_game.parquet` and measures.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/measures.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.data.tables.store import read_part
from pcf.validation.consistency import consistency

c = pl.col
HERE = Path(__file__).parent
SEASONS = list(range(2016, 2025))
GROUP = {"QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE", "C": "OL", "LT": "OL", "RT": "OL",
         "LG": "OL", "RG": "OL", "T": "OL", "G": "OL", "DE": "DL", "DT": "DL", "NT": "DL", "ILB": "LB",
         "OLB": "LB", "MLB": "LB", "CB": "CB", "FS": "S", "SS": "S"}
MEASURES = ["snap_share", "lev_share", "hi_share", "trust_gap", "trust_oe"]


def build() -> pl.DataFrame:
    zone = get_config().zone("interim") / "snap-leverage"
    plays = pl.read_parquet(zone / "plays.parquet").select(
        "game_id", "play_id", "season", "week", "posteam", "defteam", "li", "hi", "pcf_xpass"
    ).with_columns(cell=(c("pcf_xpass").fill_null(0.5) * 5).floor().clip(0, 4).cast(pl.Int8))
    of = read_part("player_play", "on_field", seasons=SEASONS).select(
        "game_id", "play_id", "side", "gsis_id", "position"
    ).collect().unique(["game_id", "play_id", "gsis_id"])
    x = of.join(plays, on=["game_id", "play_id"]).with_columns(
        team=pl.when(c("side") == "offense").then(c("posteam")).otherwise(c("defteam"))
    )
    side = plays.unpivot(index=["game_id", "play_id", "li", "hi", "cell"], on=["posteam", "defteam"], variable_name="s", value_name="team")
    side = side.with_columns(side=pl.when(c("s") == "posteam").then(pl.lit("offense")).otherwise(pl.lit("defense"))).drop("s")
    team = side.group_by("game_id", "team", "side").agg(t_snaps=pl.len(), t_lev=c("li").sum(), t_hi=c("hi").sum())
    cells = side.group_by("game_id", "team", "side", "cell").agg(c_n=pl.len(), c_hi=c("hi").sum())
    # the player's on-field rate in each kind of situation, then the high-stakes snaps it predicts
    pc = x.group_by("game_id", "team", "side", "gsis_id", "cell").agg(p_n=pl.len())
    pc = pc.join(cells, on=["game_id", "team", "side", "cell"]).with_columns(exp_hi=c("p_n") / c("c_n") * c("c_hi"))
    exp = pc.group_by("game_id", "team", "side", "gsis_id").agg(exp_hi=c("exp_hi").sum())
    pg = x.group_by("game_id", "season", "week", "team", "side", "gsis_id").agg(
        snaps=pl.len(), lev=c("li").sum(), hi_snaps=c("hi").sum(), position=c("position").mode().first()
    )
    pg = (
        pg.join(team, on=["game_id", "team", "side"])
        .join(exp, on=["game_id", "team", "side", "gsis_id"])
        .with_columns(
            group=c("position").replace_strict(GROUP, default=None),
            snap_share=c("snaps") / c("t_snaps"),
            lev_share=c("lev") / c("t_lev"),
            hi_share=pl.when(c("t_hi") > 0).then(c("hi_snaps") / c("t_hi")),
            trust_oe=pl.when(c("t_hi") > 0).then((c("hi_snaps") - c("exp_hi")) / c("t_hi")),
        )
        .with_columns(trust_gap=c("hi_share") - c("snap_share"))
    )
    depth = read_part("player_game", "depth", seasons=SEASONS).select("gsis_id", "game_id", "depth").collect()
    depth = depth.group_by("gsis_id", "game_id").agg(c("depth").min())
    pg = pg.join(depth, on=["gsis_id", "game_id"], how="left").with_columns(starter=(c("depth") == 1).fill_null(False))
    pg.write_parquet(zone / "player_game.parquet")
    return pg


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    pg = build().filter(c("group").is_not_null())
    say(f"Player-games 2016-2024: {pg.height:,}; players {pg['gsis_id'].n_unique():,}; team-games with a high-stakes play: {pg.filter(c('hi_share').is_not_null())['game_id'].n_unique():,} games")
    say(f"High-stakes plays per team side per game: mean {pg.group_by('game_id', 'team', 'side').agg(c('t_hi').first())['t_hi'].mean():.1f}")
    say("")
    say("By position group: player-games | mean snap share | mean trust gap | sd trust gap | sd trust over expected (part-timers 10-90%)")
    for g in ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S"]:
        a = pg.filter(c("group") == g)
        b = a.filter(c("snap_share").is_between(0.1, 0.9) & c("t_hi").ge(5))
        say(f"  {g:2s} | {a.height:7,} | {a['snap_share'].mean():.3f} | {a['trust_gap'].mean():+.4f} | {b['trust_gap'].std():.4f} | {b['trust_oe'].std():.4f}")
    say("")
    say("Consistency (pcf.validation.consistency: odd against even weeks; season to next season)")
    for nm, rows in (("all player-games with a snap", pg), ("part-timers, snap share 10-90%", pg.filter(c("snap_share").is_between(0.1, 0.9)))):
        rows = rows.filter(c("t_hi") >= 5)
        say(f"  {nm} ({rows.height:,} rows, games with 5+ high-stakes plays on his side)")
        t = consistency(rows, MEASURES, unit="gsis_id")
        for r in t.iter_rows(named=True):
            vals = {k: r[k] for k in r if k != "measure"}
            say(f"    {r['measure']:10s} " + " ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}" for k, v in vals.items()))
    say("")
    say("By position group, part-timers: trust over expected, week to week and season to season")
    for g in ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S"]:
        rows = pg.filter((c("group") == g) & c("snap_share").is_between(0.1, 0.9) & (c("t_hi") >= 5))
        t = consistency(rows, ["trust_oe", "trust_gap"], unit="gsis_id")
        out = []
        for r in t.iter_rows(named=True):
            ks = [k for k in r if k != "measure"]
            out.append(f"{r['measure']}: " + ", ".join(f"{k}={r[k]:.2f}" if isinstance(r[k], float) else f"{k}={r[k]}" for k in ks[:6]))
        say(f"  {g:2s} " + " | ".join(out))
    (HERE / "measures.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
