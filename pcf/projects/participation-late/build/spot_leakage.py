"""The CEO's spot-check (2026-11-12): the leakage check, in depth. Writes spot_leakage.txt here.

1. One game through time: what a view holds at each moment (FTN rows; each edition's rows as a
   higher layer would see them).
2. The 14-day line, every game of 2023-2024: at every weekly run, no game's FTN rows are visible
   before kickoff + 14 days, and at each game's late `as_of` all of them are.
3. Rebuilds: sample games of both seasons (the Super Bowl included) rebuilt from a view at their
   late `as_of` must match the season run (gap 0), and the same games rebuilt from a view a moment
   too early must not (the check can fail).
4. Training: each season's late model sees only earlier seasons, all known before its first game.
5. The answer key: the inputs view refuses `player_play`; the morning-after map never reads FTN.

    python projects/participation-late/build/spot_leakage.py
"""

# ruff: noqa: E501
from datetime import timedelta
from pathlib import Path

import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.data.timeline.moments import runs
from pcf.experts.participation_late import ftn
from pcf.experts.participation_late import reconstruct as late
from pcf.experts.participation_live import chain, grid, model
from pcf.experts.participation_live import reconstruct as live

c = pl.col
HERE = Path(__file__).parent
SEASONS = (2023, 2024)
LIVE_RUN, LATE_RUN = "6f13a56965644245a9c06384f0959448", "2a30b3e5b03d43b1b80ee7e82d8c4e69"
lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def histories(pid: str, version: int) -> pl.DataFrame:
    from pcf.config import get_config

    run = {"participation-live": LIVE_RUN, "participation-late": LATE_RUN}[pid]
    return pl.read_parquet(get_config().zone("outputs") / pid / run / "history.parquet")


def ftn_rows(view, season: int) -> pl.DataFrame:
    """FTN-charted plays per game in a view."""
    p = view.table("play", seasons=[season])
    return p.filter(c("n_offense_backfield").is_not_null()).group_by("game_id").len("rows")


gw = Gateway(TableSource(seasons=list(SEASONS)), outputs=histories)
cal = gw.calendar
whole = Gateway()  # the full calendar: a season's last games wait for the next season's first run
late_at = late.moments(whole)
live_at, ends = live.moments(whole)
kick = cal.games.select("game_id", "season", "week", "kickoff").filter(c("season").is_in(SEASONS))
FTN_ONLY = {"play": ("ftn",)}

# 1. One game through time
gid = kick.filter((c("season") == 2024) & (c("week") == 10)).sort("kickoff")["game_id"][-1]
k = kick.filter(c("game_id") == gid)["kickoff"].item()
m_at = live_at.filter(c("game_id") == gid)["as_of"].item()
l_at = late_at.filter(c("game_id") == gid)["as_of"].item()
say(f"1. One game through time: {gid}, kickoff {k:%a %Y-%m-%d %H:%M} UTC")
say(
    f"   morning-after edition as_of {m_at:%a %Y-%m-%d %H:%M}; late edition as_of {l_at:%a %Y-%m-%d %H:%M} ({(l_at - k).days} days after kickoff); late model train_end {live.train_end_of(2024, ends):%Y-%m-%d}"
)
say(
    "   moment                              FTN plays visible   morning-after rows   late rows   (a higher layer's view)"
)
reader = {"participation-live": 1, "participation-late": 1}
moments = [("kickoff", k), ("morning-after as_of", m_at), ("kickoff + 7 days", k + timedelta(days=7)),
           ("kickoff + 14 days - 1 second", k + timedelta(days=14, seconds=-1)), ("kickoff + 14 days", k + timedelta(days=14)),
           ("late as_of", l_at)]  # fmt: skip
for name, at in moments:
    f = ftn_rows(gw.view(at, "in_season", FTN_ONLY), 2024).filter(c("game_id") == gid)
    v = gw.view(at, "in_season", reader)
    a = v.output("participation-live").filter(c("game_id") == gid).height
    b = v.output("participation-late").filter(c("game_id") == gid).height
    say(f"   {name:34s}  {f['rows'].sum() if f.height else 0:>8}            {a:>9,}        {b:>9,}")
full = (
    ftn_rows(gw.view(END_OF_TIME, "in_season", FTN_ONLY), 2024)
    .filter(c("game_id") == gid)["rows"]
    .item()
)
say(f"   all of the game's FTN plays, end of time: {full}")

# 2. The 14-day line, every game
say("")
say("2. The 14-day line, every game of 2023-2024, at every weekly run:")
r = runs(cal).filter(c("season").is_in(SEASONS)).select("at").unique().sort("at")
r = (
    pl.concat([r, late_at.join(kick.select("game_id"), on="game_id").select(at="as_of").unique()])
    .unique()
    .sort("at")
)
known = kick.select("game_id", "season", ftn_known=c("kickoff") + timedelta(days=14)).join(
    late_at, on="game_id"
)
ever = {s: ftn_rows(gw.view(END_OF_TIME, "in_season", FTN_ONLY), s) for s in SEASONS}
early = incomplete = checked_games = 0
for at in r["at"].to_list():
    for s in SEASONS:
        vis = ftn_rows(gw.view(at, "in_season", FTN_ONLY), s)
        j = (
            known.filter(c("season") == s)
            .join(vis, on="game_id", how="left")
            .join(ever[s].rename({"rows": "all"}), on="game_id", how="left")
        )
        early += j.filter(c("rows").is_not_null() & (c("ftn_known") > at)).height
        due = j.filter(c("as_of") == at)
        checked_games += due.height
        incomplete += due.filter(
            c("all").is_not_null() & (c("rows").fill_null(0) != c("all"))
        ).height
say(
    f"   moments checked: {r.height}; game-moments where FTN showed before kickoff + 14 days: {early} (0 = none)"
)
say(
    f"   games checked at their own late as_of: {checked_games}; with FTN rows missing there (the backtest would have used rows not yet known): {incomplete} (0 = none)"
)
gaps = known.with_columns(d=(c("as_of") - c("ftn_known")).dt.total_hours())
say(
    f"   hours from FTN's known-at to the late as_of: min {gaps['d'].min()}, median {gaps['d'].median()}, max {gaps['d'].max()} (never negative = never early)"
)
say(
    f"   games with no FTN rows at all: {known.join(pl.concat(list(ever.values())), on='game_id', how='anti').height}"
)

# 3. Rebuilds, with a moment too early as the control
say("")
say(
    "3. Rebuilds from a view at the late as_of (must be 0) and from a view one second before FTN's known-at (the control: must not be 0):"
)
for s in SEASONS:
    feats = late.ftn_features([s])
    m = model.fit(
        late.train_frame(s, late.ftn_features(range(ftn.FIRST_SEASON, s))),
        "sequence",
        seed=s,
        extra=ftn.COLUMNS,
    )
    full_s = late.load(s, feats)
    sb = kick.filter(c("season") == s).sort("kickoff")["game_id"][-1]
    ids = [*full_s["game_id"].unique().sort().sample(5, seed=1).to_list(), sb]
    g2 = Gateway(TableSource(seasons=[s - 1, s]))
    sums = {y: live.season_sums(live.load(y)) for y in range(live.FIRST_KEY, s)}
    for gid in ids:
        kk = kick.filter(c("game_id") == gid)["kickoff"].item()
        q = chain.infer(full_s.filter(c("game_id") == gid), m).select(
            *grid.CELL_KEYS, c("p").alias("q")
        )
        out = []
        for at in (
            late_at.filter(c("game_id") == gid)["as_of"].item(),
            kk + timedelta(days=14, seconds=-1),
        ):
            view = g2.view(at, "in_season", late.INPUTS)
            g = live.season_grid(view, s).filter(c("game_id") == gid)
            f = live.featured(g, sums, live._coaches(view, [s - 1, s]))
            f = ftn.join(f, ftn.features(view.table("play", seasons=[s])))
            a = (
                chain.infer(f, m)
                .select(*grid.CELL_KEYS, "p")
                .join(f.select(*grid.CELL_KEYS, "pinned"), on=grid.CELL_KEYS, how="left")
            )
            j = a.join(q, on=grid.CELL_KEYS, how="full", coalesce=True)
            n_ftn = int((f["fmiss"] == 0).sum())
            op = j.filter(~c("pinned"))
            out.append(
                (
                    float((j["p"] - j["q"]).abs().max()),
                    float((op["p"] - op["q"]).abs().mean()),
                    n_ftn,
                    j["p"].null_count() + j["q"].null_count(),
                )
            )
        (g_ok, _, n_ok, miss_ok), (g_bad, mean_bad, n_bad, _) = out
        say(
            f"   {gid:18s} at late as_of: gap {g_ok:.6f}, charted cells {n_ok:,}, unmatched cells {miss_ok}  |  1 s before known-at: charted cells {n_bad}, gap {g_bad:.3f} (mean {mean_bad:.4f} on open cells)"
        )

# 4. Training
say("")
say(
    "4. Training: each season's late model sees only earlier seasons, all known before its first game:"
)
for s in SEASONS:
    tf = late.train_frame(s, late.ftn_features(range(ftn.FIRST_SEASON, s)))
    by = tf.group_by("season").agg(rows=pl.len(), charted=(c("fmiss") == 0).mean()).sort("season")
    first = whole.calendar.games.filter(c("season") == s)["kickoff"].min()
    last_known = whole.calendar.games.filter(c("season") == s - 1)["kickoff"].max() + timedelta(
        days=14
    )
    say(
        f"   {s}: train seasons {by['season'].to_list()}, share of rows charted by FTN {[round(x, 3) for x in by['charted'].to_list()]}; last training game's FTN known {last_known:%Y-%m-%d}, before the first test kickoff {first:%Y-%m-%d}: {last_known < first}"
    )

# 5. The answer key
say("")
say("5. The answer key:")
try:
    gw.view(l_at, "in_season", late.INPUTS).table("player_play")
    say("   the late edition's inputs view READ player_play: LEAK")
except Exception as e:  # noqa: BLE001
    say(f"   the late edition's inputs view refuses player_play: {type(e).__name__}")
say(
    f"   the morning-after map's inputs declare FTN: {'ftn' in live.INPUTS['play']} (False = it can't read FTN)"
)

text = "\n".join(lines)
(HERE / "spot_leakage.txt").write_text(text, encoding="utf-8")
