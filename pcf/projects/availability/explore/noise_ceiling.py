"""Availability exploration, step 0: the noise ceiling (pre-registered in EXPLORATION.md).

1. How much players really differ in injury rate per snap beyond position: over-dispersion of
   player injury counts against a Poisson with snaps as exposure, the credibility weight, and the
   season-to-season repeat.
2. Time missed given an in-game injury: its spread, and the after-the-fact ceiling (next week's
   report status and body part, known only after the injury).
3. Rest-of-season games for regular QB/RB/WR/TE: severity (games lost to an absence already
   going on at the forecast moment) against frequency (absences that start later).

Run from pcf/: PYTHONIOENCODING=utf-8 <venv python> <this file>
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config

c = pl.col
O = get_config().zone("interim") / "availability"
RNG = np.random.default_rng(get_config().seed)
B = 2000


def pct(a, q=(5, 95)):
    lo, hi = np.percentile(a, q)
    return f"({lo:+.3f} to {hi:+.3f})"


print("=" * 80, "\n1. Players' injury rates per snap beyond position (2016-2024 scrimmage snaps)")
pp = pl.read_parquet(O / "player_plays.parquet", columns=["gsis_id", "season", "group", "injured"]).filter(c("group").is_not_null())
ps = pp.group_by("gsis_id", "season", "group").agg(n=pl.len(), x=c("injured").sum())
car = ps.group_by("gsis_id", "group").agg(n=c("n").sum(), x=c("x").sum())


def tau2(d: pl.DataFrame) -> float:
    lam = d["x"].sum() / d["n"].sum()
    e = d["n"].to_numpy() * lam
    x = d["x"].to_numpy()
    return float(((x - e) ** 2 - x).sum() / (e**2).sum())


print(f"{'group':6} {'players':>7} {'rate/1000':>9} {'tau2 (true spread of rate multiplier)':>40} {'snaps for Z=0.5':>16}")
for g in ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]:
    d = car.filter((c("group") == g) & (c("n") >= 100))
    lam = d["x"].sum() / d["n"].sum()
    t = tau2(d)
    idx = np.arange(d.height)
    bs = [tau2(d[RNG.choice(idx, len(idx))]) for _ in range(500)]
    half = 1 / (t * lam) if t > 0 else float("inf")
    print(f"{g:6} {d.height:7d} {lam * 1000:9.2f} {t:+.3f} {pct(bs):>22} {half:16,.0f}")
d = car.filter(c("n") >= 100)
# pooled across groups, each player's expectation from his group's rate
lam_g = car.group_by("group").agg(lam=c("x").sum() / c("n").sum())
d = d.join(lam_g, on="group").with_columns(e=c("n") * c("lam"))
x, e = d["x"].to_numpy(), d["e"].to_numpy()
t_all = ((x - e) ** 2 - x).sum() / (e**2).sum()
print(f"all groups pooled: tau2 {t_all:+.3f}; a player with 1,000 snaps a season expects about {1000 * d['x'].sum() / d['n'].sum():.2f} injuries, so his own record is half signal after about {1 / t_all if t_all > 0 else float('inf'):.0f} expected injuries")

print("\nSeason-to-season repeat of a player's rate multiplier (injuries over his group's expectation), players with 300+ snaps both seasons")
ps = ps.join(lam_g, on="group").with_columns(e=c("n") * c("lam"))
nx = ps.select("gsis_id", season=c("season") - 1, x2=c("x"), e2=c("e"), n2=c("n"))
rep = ps.join(nx, on=["gsis_id", "season"]).filter((c("n") >= 300) & (c("n2") >= 300))
# weighted correlation of x/e with x2/e2 is dominated by noise; report the cleaner test:
# next season's injuries over expectation, for players above vs below expectation this season
rep = rep.with_columns(hi=c("x") > c("e"))
for k, sub in rep.group_by("hi"):
    print(f"  this season {'above' if k[0] else 'at or below'} expectation: {sub.height} player-seasons; next season's injuries / expected = {sub['x2'].sum() / sub['e2'].sum():.3f}")
xs, es, x2, e2 = (rep[k].to_numpy().astype(float) for k in ("x", "e", "x2", "e2"))
hi = xs > es
bs = []
idx = np.arange(rep.height)
for _ in range(B):
    i = RNG.choice(idx, len(idx))
    h = hi[i]
    bs.append(x2[i][h].sum() / e2[i][h].sum() - x2[i][~h].sum() / e2[i][~h].sum())
print(f"  gap (above minus at-or-below): {x2[hi].sum() / e2[hi].sum() - x2[~hi].sum() / e2[~hi].sum():+.3f} {pct(bs)}")

print("=" * 80, "\n2. Time missed given an in-game injury (2013-2024)")
pg = pl.read_parquet(O / "player_games.parquet")
rost = pg.select("gsis_id", "season", "team", gi=c("gi") - 1, next_rostered=pl.lit(1))
h = pg.filter(c("hurt") == 1).join(rost, on=["gsis_id", "season", "team", "gi"], how="left").with_columns(c("next_rostered").fill_null(0))
h = h.with_columns(y=(c("missed").cast(pl.Float64) + 1).log())
print(f"injuries {h.height}; games missed mean {h['missed'].mean():.2f}, SD {h['missed'].std():.2f}; log(1 + games) SD {h['y'].std():.3f}")
print("share missing 0, 1, 2-3, 4-7, 8+ games:", [round(float(v), 3) for v in (
    (h["missed"] == 0).mean(), (h["missed"] == 1).mean(), h["missed"].is_between(2, 3).mean(), h["missed"].is_between(4, 7).mean(), (h["missed"] >= 8).mean())])
top = h.filter(c("nr_part").is_not_null())["nr_part"].value_counts().sort("count", descending=True).head(12)["nr_part"].to_list()
h = h.with_columns(
    part=pl.when(c("nr_part").is_in(top)).then(c("nr_part")).when(c("nr_part").is_not_null()).then(pl.lit("other part")).otherwise(pl.lit("none")),
    stat=pl.when(c("next_rostered") == 0).then(pl.lit("not rostered next game")).otherwise(c("nr_status").fill_null("not listed")),
)
print(h.group_by("stat").agg(n=pl.len(), mean=c("missed").mean(), zero=(c("missed") == 0).mean()).sort("n", descending=True))


def cell_r2(train, test, keys):
    m = train.group_by(keys).agg(mu=c("y").mean(), k=pl.len())
    g = train["y"].mean()
    t = test.join(m, on=keys, how="left").with_columns(mu=pl.when(c("k") >= 20).then(c("mu")).otherwise(pl.lit(g)))
    return t


out = {"position": [], "status": [], "status x part": []}
for s in range(2016, 2025):
    tr, te = h.filter(c("season") < s), h.filter(c("season") == s)
    base = te.with_columns(mu=pl.lit(tr["y"].mean()))
    for name, keys in (("position", ["position"]), ("status", ["stat"]), ("status x part", ["stat", "part"])):
        t = cell_r2(tr, te, keys)
        out[name].append(t.select(sse=((c("y") - c("mu")) ** 2).sum(), sst=((c("y") - base["mu"][0]) ** 2).sum()))
for name, parts in out.items():
    d = pl.concat(parts)
    print(f"  after-the-fact ceiling, walk-forward 2016-2024, {name:14}: share of log(1 + games) error removed against the overall mean = {1 - d['sse'].sum() / d['sst'].sum():.3f}")

print("=" * 80, "\n3. Rest-of-season games for regular QB/RB/WR/TE (2013-2024): severity against frequency")
sched = pg.select("team", "season", "gi", "n_games").unique()
skill = pg.filter(c("position").is_in(["QB", "RB", "WR", "TE"]))
first = skill.sort("gi").group_by("gsis_id", "season").agg(team=c("team").first())
# his first team's weeks; played, snaps and the report read by week from any team, so a trade isn't an absence
wk = pg.select("team", "season", "gi", "week").unique()
anyteam = skill.group_by("gsis_id", "season", "week").agg(
    played=c("played").max(), offense_snaps=c("offense_snaps").max(), hurt=c("hurt").max(),
    rostered=pl.lit(1), status=c("report_status").first())
seq = first.join(wk, on=["team", "season"]).join(anyteam, on=["gsis_id", "season", "week"], how="left").with_columns(
    c("played").fill_null(0), c("offense_snaps").fill_null(0), c("hurt").fill_null(0), c("rostered").fill_null(0)).sort("gsis_id", "season", "gi")
# a player traded or released stays "missing"; drop his season after his last rostered week with any team
seq = seq.with_columns(last_r=pl.when(c("rostered") == 1).then(c("gi")).otherwise(None).max().over("gsis_id", "season"))
# regulars: 25+ offensive snaps on average over his first three played games
reg = seq.filter(c("played") == 1).group_by("gsis_id", "season").agg(m3=c("offense_snaps").head(3).mean(), n_pl=pl.len()).filter((c("m3") >= 25) & (c("n_pl") >= 3))
seq = seq.join(reg.select("gsis_id", "season"), on=["gsis_id", "season"])
tot_sev = tot_new = tot_games = 0
spell_start_hurt = spell_n = 0
from collections import Counter
cause = Counter()
for (_, _), g in seq.group_by(["gsis_id", "season"]):
    pl_ = g["played"].to_numpy()
    hu = g["hurt"].to_numpy()
    ro_ = g["rostered"].to_numpy()
    st_ = g["status"].to_list()
    n = len(pl_)
    started = np.flatnonzero(pl_ == 1)
    if len(started) == 0:
        continue
    f0 = started[0]
    # spells: runs of missed games after his first played game
    for j in range(f0 + 1, n):
        if pl_[j] == 0 and pl_[j - 1] == 1:
            spell_n += 1
            spell_start_hurt += int(hu[j - 1] == 1)
            cause[("named in-game injury" if hu[j - 1] == 1 else "on the report (Out/Doubtful/Questionable)" if st_[j] in ("Out", "Doubtful", "Questionable") else "off the active roster (reserve lists, released)" if ro_[j] == 0 else "rostered and not on the report (healthy scratch, illness, other)")] += 1
    # forecast moments: before each team game j after his first played game
    for j in range(f0 + 1, n):
        rest = pl_[j:]
        miss = (rest == 0).astype(int)
        tot_games += len(rest)
        if pl_[j - 1] == 0:
            k = np.argmax(rest == 1) if (rest == 1).any() else len(rest)
            sev = miss[:k].sum()
        else:
            sev = 0
        tot_sev += sev
        tot_new += miss.sum() - sev
print(f"regular player-seasons {reg.height}; forecast moments x games ahead: {tot_games:,}")
print(f"games missed ahead: {tot_sev + tot_new:,} ({(tot_sev + tot_new) / tot_games:.3f} of games ahead)")
print(f"  severity (absence going on at the moment): {tot_sev / (tot_sev + tot_new):.3f} of games missed ahead")
print(f"  frequency (absences that start later):     {tot_new / (tot_sev + tot_new):.3f}")
print(f"absence spells {spell_n:,}; share that start right after a game with a named in-game injury: {spell_start_hurt / spell_n:.3f}")
for k, v in cause.most_common():
    print(f"  spells starting {k}: {v / spell_n:.3f}")
print("note: a player released or traded stays in his first team's weeks; weeks he was rostered nowhere count as missed (reserve lists or out of the league)")
