"""Is the data there? The answer key's size, how well it matches the next-morning snap counts, how
many of each play's 22 are already pinned by the snap counts or the play-by-play, and who's left
to estimate. 2016-2024 regular season."""

# ruff: noqa: E501
import polars as pl

from common import lineups, named, plays, snaps

c = pl.col
p, L, N, S = plays(), lineups(), named(), snaps()
print(f"plays with 11 a side: {p.height:,}; lineup rows {L.height:,}; games {p['game_id'].n_unique():,}")
print(p.group_by("season").agg(plays=pl.len(), games=c("game_id").n_unique()).sort("season"))
print("play types:", dict(p["play_type"].value_counts().iter_rows()))

# 1. the answer key against the snap counts
on = L.group_by("game_id", "side", "team", "gsis_id").agg(on=pl.len(), position=c("position").first())
team_plays = p.group_by("game_id", "posteam").agg(n_team=pl.len())
on = on.join(
    pl.concat([team_plays.rename({"posteam": "team"}).with_columns(side=pl.lit("offense")),
               p.group_by("game_id", "defteam").agg(n_team=pl.len()).rename({"defteam": "team"}).with_columns(side=pl.lit("defense"))]),
    on=["game_id", "team", "side"],
)  # fmt: skip
sn = S.select("gsis_id", "game_id", "offense_snaps", "defense_snaps")
on = on.join(sn, on=["gsis_id", "game_id"], how="left").with_columns(
    snap=pl.when(c("side") == "offense").then(c("offense_snaps")).otherwise(c("defense_snaps"))
)
m = on.filter(c("snap").is_not_null())
print(f"\nplayer-game-sides in the answer key: {on.height:,}; with a snap count: {m.height / on.height:.1%}")
# snap counts include penalty plays and 2-point tries our play set may lack: compare shares
m = m.with_columns(share_on=c("on") / c("n_team"))
team_snaps = m.group_by("game_id", "team", "side").agg(tot=c("snap").sum())
m = m.join(team_snaps, on=["game_id", "team", "side"]).with_columns(share_snap=c("snap") * 11 / c("tot"))
m = m.with_columns(err=(c("share_snap") - c("share_on")).abs())
print("snap share (snaps x 11 / team's snaps) against the true on-field share:")
print(m.group_by("side").agg(
    rows=pl.len(), r=pl.corr("share_snap", "share_on"), mean_abs_err=c("err").mean(),
    within_2pts=(c("err") <= 0.02).mean(), within_5pts=(c("err") <= 0.05).mean(),
))  # fmt: skip

# players in the game with snaps but never in the answer key (or the reverse)
roster_sides = S.filter((c("offense_snaps") > 0) | (c("defense_snaps") > 0))
print(f"players with offensive or defensive snaps: {roster_sides.height:,}")

# 2. how much is already pinned: players on every play or no play, and named players
m = m.with_columns(full=c("share_on") >= 0.999)
print("\nshare of each side's 11 slots filled by a player on every snap of the game (pinned by the snap count):")
slots = m.group_by("side").agg(pinned=(c("full") * c("on")).sum(), all=c("on").sum())
print(slots.with_columns(pinned_share=c("pinned") / c("all")))
print("by position, players on every snap / part-timers (share of the position's on-field rows):")
pos = m.with_columns(pt=~c("full")).group_by("side", "position").agg(
    rows=c("on").sum(), part_time_rows=(c("pt") * c("on")).sum(), players=pl.len(), mean_share=c("share_on").mean()
).with_columns(part_time_share=c("part_time_rows") / c("rows")).sort("side", "rows", descending=[False, True])
with pl.Config(tbl_rows=40):
    print(pos.filter(c("rows") > 20000))

# named players: how many per play, and are they in the true lineup?
key = ["game_id", "play_id", "side", "gsis_id"]
nk = N.join(L.select(key).with_columns(on=pl.lit(True)), on=key, how="left").with_columns(c("on").fill_null(False))
print(f"\nnamed player-plays: {N.height:,}; in the true lineup: {nk['on'].mean():.1%}")
per_play = N.group_by("game_id", "play_id", "side").len()
print(per_play.group_by("side").agg(named_per_play=c("len").mean()))
# the share of part-timer slots a name pins
pt = m.filter(~c("full")).select("game_id", "team", "side", "gsis_id")
Lp = L.join(pt, on=["game_id", "team", "side", "gsis_id"], how="semi")
Lp = Lp.join(N.select(key).with_columns(named=pl.lit(True)), on=key, how="left").with_columns(c("named").fill_null(False))
print("part-timer on-field rows that a name pins:")
print(Lp.group_by("side").agg(rows=pl.len(), named=c("named").mean()))
print("\nopen slots per play (part-timers not named), by side:")
open_ = Lp.filter(~c("named")).group_by("game_id", "play_id", "side").len()
allplays = p.select("game_id", "play_id").join(pl.DataFrame({"side": ["offense", "defense"]}), how="cross")
open_ = allplays.join(open_, on=["game_id", "play_id", "side"], how="left").with_columns(c("len").fill_null(0))
print(open_.group_by("side").agg(mean=c("len").mean(), median=c("len").median(), p90=c("len").quantile(0.9)))
cand = m.filter(~c("full")).group_by("game_id", "team", "side").agg(part_timers=pl.len())
print("part-timers per team-game-side (the candidates for the open slots):")
print(cand.group_by("side").agg(mean=c("part_timers").mean(), p90=c("part_timers").quantile(0.9)))
