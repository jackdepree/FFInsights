"""Vacated opportunity exploration: I125, H109's stayers scored apart by intake (IDEAS.md, odds written first).

Re-runs H109's tables and method 2 fits (h109_plus_minus.py's code, up to its fitting-noise step), then splits the
stayers by whether the team brought in a top player at the group (snap share: his group; target share: any of WR,
TE, RB). Also, reported: H110's "he left" side bet without the count of departures (the two overlap).

Run from pcf/projects/vacated-opportunity/explore: PYTHONIOENCODING=utf-8 <venv python> i125_intake_split.py
"""

# ruff: noqa: E501
from __future__ import annotations

src = open("h109_plus_minus.py", encoding="utf-8").read()
exec(src.split("# fitting noise")[0].replace('print("\\n=== 0. the noise ceiling")', 'print("(H109 re-run for I125)")'))

nxt_ps = ps.select("gsis_id", "team", "group", "rank", season=c("season") - 1)
on_team = ps.select("gsis_id", "team", "season").unique()
new = nxt_ps.join(on_team, on=["gsis_id", "team", "season"], how="anti").with_columns(top=c("rank") <= c("group").replace_strict(vc.TOPK, return_dtype=pl.Int64))
gi = new.group_by("team", "season", "group").agg(intake=c("top").any())
si = new.filter(c("group").is_in(vc.SKILL)).group_by("team", "season").agg(intake=c("top").any())


def split(df, label):
    for flag, nm in ((True, "a top player brought in"), (False, "the group left empty")):
        s_ = df.filter(c("intake") == flag)
        y = s_["y_next"].to_numpy()
        e = {k: (y - s_[k].to_numpy()) ** 2 for k in ("m0", "m1a", "m2")}
        tm = s_["team"].to_numpy()
        g2, lo2, hi2 = boot_gain(e["m0"], e["m2"], tm)
        g1, lo1, hi1 = boot_gain(e["m0"], e["m1a"], tm)
        print(f"  {label}, {nm}: n {s_.height}; mean change {(y - s_['m0'].to_numpy()).mean():+.3f}; method 2 against no change {g2:+.1%} (90% {lo2:+.1%} to {hi2:+.1%}); 1a against no change {g1:+.1%} (90% {lo1:+.1%} to {hi1:+.1%})")


print("\n=== I125: H109's stayers split by intake")
sn = st.join(gi, on=["team", "season", "group"], how="left").with_columns(c("intake").fill_null(False))
split(sn.filter(c("group").is_in(vc.SKILL)), "skill snap share")
split(sn.filter(~c("group").is_in(vc.SKILL)), "the lines' snap share")
f2, _, _, _ = pm_fits(vc.SKILL, vc.SKILL, "tgt_share", "w_tgt", "target share")
s2 = pm_predict(stayer_table("tgt_share", "skill"), f2, "tgt_share", vc.SKILL)
s2 = s2.join(si, on=["team", "season"], how="left").with_columns(c("intake").fill_null(False))
split(s2, "target share")

# reported (added after I125's first result): the intake flag above uses next season's snaps (a newcomer among the
# group's top), which is hindsight and partly the target. A flag known in the offseason: a newcomer at the group
# who was a top player at his group elsewhere last season, or a rookie drafted in rounds 1-2 (pick 64 or earlier).
print("\n=== I125 with an offseason-known intake flag (a top player elsewhere last season, or a pick 1-64 rookie)")
ros = vc._read("player_game/roster", columns=["gsis_id", "season", "draft_number", "entry_year"]).unique(["gsis_id", "season"])
prev_top = ps.filter(c("top")).select("gsis_id", season=c("season") + 1, was_top=pl.lit(True)).unique(["gsis_id", "season"])
nw = new.with_columns(season_n=c("season") + 1).join(prev_top, left_on=["gsis_id", "season_n"], right_on=["gsis_id", "season"], how="left")
nw = nw.join(ros, left_on=["gsis_id", "season_n"], right_on=["gsis_id", "season"], how="left").with_columns(
    pit=c("was_top").fill_null(False) | ((c("entry_year") == c("season_n")) & (c("draft_number") <= 64)).fill_null(False))
gi2 = nw.group_by("team", "season", "group").agg(intake=c("pit").any())
si2 = nw.filter(c("group").is_in(vc.SKILL)).group_by("team", "season").agg(intake=c("pit").any())
sn2 = st.join(gi2, on=["team", "season", "group"], how="left").with_columns(c("intake").fill_null(False))
both = sn.select("gsis_id", "team", "season", "group", h=c("intake")).join(sn2.select("gsis_id", "team", "season", p=c("intake")), on=["gsis_id", "team", "season"])
print(both.filter(c("group").is_in(vc.SKILL)).group_by("h", "p").len().sort("h", "p").to_dicts())
split(sn2.filter(c("group").is_in(vc.SKILL)), "skill snap share (offseason flag)")
split(sn2.filter(~c("group").is_in(vc.SKILL)), "the lines' snap share (offseason flag)")
s3 = s2.drop("intake").join(si2, on=["team", "season"], how="left").with_columns(c("intake").fill_null(False))
split(s3, "target share (offseason flag)")
