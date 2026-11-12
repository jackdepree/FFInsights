"""H33: each team or coach has its own substitution habits in certain situations ("switching out
a bunch of players on third down or maybe in the fourth quarter"). Measured on the answer key:
how many of a side's 11 change between consecutive snaps of a drive, by the second snap's
situation, each team's excess over the league's in the same situation and season."""

# ruff: noqa: E501
import polars as pl

from common import coaches, pairs
from pcf.validation.consistency import consistency

c = pl.col
P = pairs()
P = P.with_columns(
    third=(c("next_down") == 3),
    fourth_q=(c("next_qtr") == 4),
    red_zone=(c("next_yardline") <= 20),
    two_minute=(c("next_half_secs") <= 120),
    blowout=(c("next_score").abs() >= 17),
    after_first_down=(c("next_down") == 1),
    no_huddle=(c("next_no_huddle") == 1),
    after_big_play=(c("yards_gained") >= 20),
)
SIT = ["third", "fourth_q", "red_zone", "two_minute", "blowout", "after_first_down", "no_huddle", "after_big_play"]
print(f"pairs of consecutive snaps in a drive: {P.height // 2:,} per side")
print("\nAverage players changed between snaps, by the second snap's situation (league, 2016-2024):")
rows = []
for side in ("offense", "defense"):
    s = P.filter(c("side") == side)
    base = s["changes"].mean()
    rows.append({"side": side, "situation": "all", "changes": base, "share_any_change": (s["changes"] > 0).mean(), "pairs": s.height})
    for x in SIT:
        t = s.filter(c(x))
        rows.append({"side": side, "situation": x, "changes": t["changes"].mean(), "share_any_change": (t["changes"] > 0).mean(), "pairs": t.height})
with pl.Config(tbl_rows=30):
    print(pl.DataFrame(rows))

# each team-game's excess over the league in the same situation and season
lg = []
for x in ["all", *SIT]:
    f = pl.lit(True) if x == "all" else c(x)
    lg.append(P.filter(f).group_by("side", "season").agg(lg=c("changes").mean()).with_columns(sit=pl.lit(x)))
lg = pl.concat(lg)
team_rows = []
for x in ["all", *SIT]:
    f = pl.lit(True) if x == "all" else c(x)
    t = (
        P.filter(f).group_by("side", "team", "season", "week", "game_id").agg(v=c("changes").mean(), n=pl.len())
        .join(lg.filter(c("sit") == x).drop("sit"), on=["side", "season"])
        .with_columns(excess=c("v") - c("lg"), sit=pl.lit(x))
    )  # fmt: skip
    team_rows.append(t)
T = pl.concat(team_rows)
out = []
for side in ("offense", "defense"):
    for x in ["all", *SIT]:
        rows = T.filter((c("side") == side) & (c("sit") == x)).rename({x: x} if False else {})
        r = consistency(rows.rename({"excess": f"{side}_{x}"}), [f"{side}_{x}"], unit="team")
        out.append(r)
res = pl.concat(out).select("measure", "week_r", "week_lo", "season_r", "season_lo", "season_hi", "unit_seasons", "mean_abs", "verdict")
print("\nConsistency of each team's excess changes (players changed per snap, over the league's in the same situation):")
with pl.Config(tbl_rows=30, float_precision=2):
    print(res)

# the spread between teams: a season's excess, sd across team-seasons, in players per snap
ts = T.group_by("side", "sit", "team", "season").agg(excess=(c("excess") * c("n")).sum() / c("n").sum())
print("\nHow big: sd of team-season excess (players changed per snap), and the most and least:")
print(ts.group_by("side", "sit").agg(sd=c("excess").std(), lo=c("excess").min(), hi=c("excess").max()).sort("side", "sit"))

# does it follow the head coach? team-season excess (all snaps, and third downs), offense and defense,
# for coaches who moved: their old team's season before against their new team's season
co = coaches().group_by("team", c("game_id").str.slice(0, 4).cast(pl.Int32).alias("season")).agg(coach=c("coach").mode().first())
tc = ts.join(co, on=["team", "season"], how="left")
for side in ("offense", "defense"):
    for x in ("all", "third", "fourth_q"):
        d = tc.filter((c("side") == side) & (c("sit") == x)).sort("season")
        prev = d.select("coach", "team", season=c("season") + 1, prev_excess="excess", prev_team="team")
        j = d.join(prev, on=["coach", "season"])
        moved = j.filter(c("team") != c("prev_team"))
        same_team = d.join(d.select("team", season=c("season") + 1, prev_excess="excess", prev_coach="coach"), on=["team", "season"])
        new_coach = same_team.filter(c("coach") != c("prev_coach"))
        stay = same_team.filter(c("coach") == c("prev_coach"))
        r = lambda df: (df.height, round(df.select(pl.corr("excess", "prev_excess")).item() or float("nan"), 2))  # noqa: E731
        print(f"{side:8s} {x:9s} same team+coach n,r={r(stay)}  same team, new coach n,r={r(new_coach)}  coach moved n,r={r(moved)}")

# the extremes: team-seasons that changed the most players on third down, offense
print("\nMost and least third-down changes, offense (team-seasons, players per snap over the league):")
o = tc.filter((c("side") == "offense") & (c("sit") == "third")).sort("excess")
print(pl.concat([o.head(5), o.tail(5)]).select("team", "season", "coach", c("excess").round(2)))
d = tc.filter((c("side") == "defense") & (c("sit") == "third")).sort("excess")
print("defense:"); print(pl.concat([d.head(5), d.tail(5)]).select("team", "season", "coach", c("excess").round(2)))
