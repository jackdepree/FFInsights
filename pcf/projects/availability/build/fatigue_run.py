"""Availability: the fatigue backlog, I29, I30 and I50 (REVIEW.md section 3, written before this ran).

Data: every on-field player on every regular-season run and pass, 2016-2024 (true participation,
`interim/availability/player_plays.parquet`, built by the exploration's build_events.py), with the
play-by-play's drive, half, EPA and dropback fields.

- I29 (real?): defensive injuries per player-play by the play's number in the drive (1-3, 4-6, 7+),
  play type only, then with the controls; a Poisson fit per play (injured defenders, offset: the
  defenders on the field), errors clustered by game. The offense as the check.
- I29 (pays?): a defender's long-drive snaps (drive play 7+) in his last game beside next_logit's
  log-odds on next game's health absence, walk-forward by season, 2018-2024, with 19 copies.
- I30: second-half dropbacks' EPA on the defense's first-half snaps faced (per +10), without and
  with the day's matchup (the offense's first-half EPA per play against this defense); pass rush
  (sack or hit) and coverage (EPA on non-sack dropbacks) apart; runs as the check.
- I50: the share of the defenders on the field who aren't the team's regulars (under 60% of its
  defensive snaps that season), by play in the drive and first-half snaps faced, with the score,
  quarter and win probability held; by group. Then I30 with that share held fixed.

Run from pcf/: <venv python> projects/availability/build/fatigue_run.py
"""

# ruff: noqa: E501
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.experts.availability import checks as K
from pcf.experts.availability import experts as X

c = pl.col
CFG = get_config()
T = CFG.zone("tables")
OUT = Path(__file__).with_name("fatigue.txt")
SEASONS = range(2016, 2025)
lines: list[str] = []
T0 = time.time()


def log(*parts) -> None:
    s = " ".join(str(p) for p in parts)
    print(f"[{time.time() - T0:5.0f}s] {s}", flush=True)
    lines.append(s)


# ---------------------------------------------------------------- fits with errors clustered by game
def _cluster_cov(score: np.ndarray, bread: np.ndarray, groups: np.ndarray) -> np.ndarray:
    _, g = np.unique(groups, return_inverse=True)
    s = np.zeros((g.max() + 1, score.shape[1]))
    np.add.at(s, g, score)
    meat = s.T @ s
    inv = np.linalg.pinv(bread)
    return inv @ meat @ inv


def ols(x: np.ndarray, y: np.ndarray, groups: np.ndarray):
    xtx = x.T @ x
    b = np.linalg.solve(xtx, x.T @ y)
    r = y - x @ b
    return b, np.sqrt(np.diag(_cluster_cov(x * r[:, None], xtx, groups)))


def poisson(x: np.ndarray, y: np.ndarray, offset: np.ndarray, groups: np.ndarray, iters: int = 30):
    b = np.zeros(x.shape[1])
    b[0] = np.log(y.sum() / np.exp(offset).sum())
    for _ in range(iters):
        mu = np.exp(np.clip(x @ b + offset, -30, 30))
        h = x.T @ (x * mu[:, None])
        step = np.linalg.solve(h, x.T @ (y - mu))
        b += step
        if np.abs(step).max() < 1e-8:
            break
    mu = np.exp(x @ b + offset)
    return b, np.sqrt(np.diag(_cluster_cov(x * (y - mu)[:, None], h, groups)))


def design(df: pl.DataFrame, cats: list[str], nums: list[str]) -> tuple[np.ndarray, list[str]]:
    """An intercept, one-hot of each category (first level dropped) and numeric columns."""
    cols, names = [np.ones(df.height)], ["const"]
    for k in cats:
        v = df[k].cast(pl.Utf8).fill_null("NA").to_numpy()
        for lev in sorted(set(v))[1:]:
            cols.append((v == lev).astype(float))
            names.append(f"{k}={lev}")
    for k in nums:
        cols.append(df[k].cast(pl.Float64).fill_null(0.0).to_numpy())
        names.append(k)
    return np.column_stack(cols), names


def show(b, se, names, keep, scale=1.0, exp=False, unit=""):
    out = []
    for k in keep:
        i = names.index(k)
        est, lo, hi = b[i], b[i] - 1.645 * se[i], b[i] + 1.645 * se[i]
        if exp:
            out.append(f"{k} {np.exp(est):.3f} ({np.exp(lo):.3f} to {np.exp(hi):.3f})")
        else:
            out.append(f"{k} {scale * est:+.4f}{unit} ({scale * lo:+.4f} to {scale * hi:+.4f})")
    return "; ".join(out)


# ---------------------------------------------------------------- plays
pbp = pl.concat([
    pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet",
                    columns=["game_id", "play_id", "season", "week", "season_type", "posteam", "defteam", "fixed_drive", "game_half", "qtr", "down", "ydstogo", "yardline_100", "score_differential", "wp", "epa", "play_type", "qb_dropback", "sack", "qb_hit"])
    for s in SEASONS
]).filter((c("season_type") == "REG") & c("play_type").is_in(["run", "pass"]) & c("posteam").is_not_null())
pbp = pbp.with_columns(c("play_id").cast(pl.Int64)).sort("game_id", "play_id")
pbp = pbp.with_columns(drive_play=pl.int_range(1, pl.len() + 1).over("game_id", "fixed_drive"))
pbp = pbp.with_columns(dp=pl.when(c("drive_play") <= 3).then(pl.lit("1-3")).when(c("drive_play") <= 6).then(pl.lit("4-6")).otherwise(pl.lit("7+")),
                       dp4=pl.when(c("drive_play") <= 3).then(pl.lit("1-3")).when(c("drive_play") <= 6).then(pl.lit("4-6")).when(c("drive_play") <= 9).then(pl.lit("7-9")).otherwise(pl.lit("10+")))
# snaps since the defense last rested: its plays since its offense last had a 4+ play drive, or the half began
drives = pbp.group_by("game_id", "fixed_drive").agg(c("posteam").first(), c("defteam").first(), c("game_half").first(), n=pl.len(), first=c("play_id").min()).sort("game_id", "first")
rows = []
for (gid,), g in drives.partition_by("game_id", as_dict=True, maintain_order=True).items():
    run = {}
    half = None
    for d in g.iter_rows(named=True):
        if d["game_half"] != half:
            half, run = d["game_half"], {}
        rows.append((gid, d["fixed_drive"], run.get(d["defteam"], 0)))
        run[d["defteam"]] = run.get(d["defteam"], 0) + d["n"]
        if d["n"] >= 4:
            run[d["posteam"]] = 0
stint = pl.DataFrame(rows, schema=["game_id", "fixed_drive", "rest0"], orient="row").with_columns(c("fixed_drive").cast(pbp["fixed_drive"].dtype))
pbp = pbp.join(stint, on=["game_id", "fixed_drive"], how="left").with_columns(since_rest=c("rest0") + c("drive_play") - 1)
pbp = pbp.with_columns(sr=pl.when(c("since_rest") < 6).then(pl.lit("00-05")).when(c("since_rest") < 12).then(pl.lit("06-11")).when(c("since_rest") < 18).then(pl.lit("12-17")).otherwise(pl.lit("18+")))
# each side's strength in its other games (EPA per play), and the first half
by = pbp.group_by("season", "defteam").agg(d_sum=c("epa").sum(), d_n=c("epa").count())
bg = pbp.group_by("season", "game_id", "defteam").agg(dg_sum=c("epa").sum(), dg_n=c("epa").count())
ob = pbp.group_by("season", "posteam").agg(o_sum=c("epa").sum(), o_n=c("epa").count())
og = pbp.group_by("season", "game_id", "posteam").agg(og_sum=c("epa").sum(), og_n=c("epa").count())
fh = pbp.filter(c("game_half") == "Half1").group_by("game_id", "defteam").agg(fh_snaps=pl.len(), fh_epa=c("epa").mean())
pbp = (pbp.join(by, on=["season", "defteam"]).join(bg, on=["season", "game_id", "defteam"]).join(ob, on=["season", "posteam"]).join(og, on=["season", "game_id", "posteam"])
       .with_columns(def_str=(c("d_sum") - c("dg_sum")) / (c("d_n") - c("dg_n")), off_str=(c("o_sum") - c("og_sum")) / (c("o_n") - c("og_n")))
       .join(fh, on=["game_id", "defteam"], how="left"))
pbp = pbp.with_columns(
    yl=(c("yardline_100") // 20).cast(pl.Int32).clip(0, 4), sd=c("score_differential").clip(-21, 21) // 7,
    pas=c("play_type"), dn=c("down").fill_null(1).cast(pl.Int32), q=c("qtr").clip(1, 5).cast(pl.Int32),
    wpb=(c("wp").fill_null(0.5) * 5).cast(pl.Int32).clip(0, 4),
)
log(f"plays {pbp.height:,} (regular-season runs and passes, {SEASONS.start}-{SEASONS.stop - 1})")

# ---------------------------------------------------------------- player-plays
pp = pl.read_parquet(CFG.zone("interim") / "availability" / "player_plays.parquet",
                     columns=["game_id", "play_id", "side", "team", "gsis_id", "season", "group", "injured", "n_tacklers", "tfl", "yards_gained"])
pp = pp.filter(c("season").is_in(list(SEASONS)))
per = pp.group_by("game_id", "play_id", "side").agg(n=pl.len(), inj=c("injured").sum(), tk=c("n_tacklers").first(), tfl=c("tfl").first(), yds=c("yards_gained").first())
log(f"player-plays {pp.height:,}; plays with a defense on record {per.filter(c('side') == 'defense').height:,}")

# ================================================================ I29 real?
log("\nI29 (real?): injuries per player-play by play in the drive, a Poisson fit per play (offset: players on the field), 90% intervals clustered by game")
for side in ("defense", "offense"):
    d = per.filter(c("side") == side).join(pbp, on=["game_id", "play_id"], how="inner")
    d = d.with_columns(tkb=c("tk").fill_null(0).clip(0, 3), ydb=(c("yds").fill_null(0).clip(-5, 30) // 5))
    y, off, grp = d["inj"].to_numpy().astype(float), np.log(d["n"].to_numpy().astype(float)), d["game_id"].to_numpy()
    rate = d.group_by("dp4").agg(r=1000 * c("inj").sum() / c("n").sum()).sort("dp4")
    log(f"  {side}: player-plays {int(d['n'].sum()):,}, injuries {int(y.sum()):,}; raw per 1,000 by drive play: " + ", ".join(f"{a} {b:.2f}" for a, b in zip(rate["dp4"], rate["r"], strict=True)))
    specs = {
        "play type only": (["dp", "pas"], []),
        "+ play (tacklers, loss, yards, down)": (["dp", "pas", "tkb", "tfl", "ydb", "dn"], []),
        "+ field position, quarter, score": (["dp", "pas", "tkb", "tfl", "ydb", "dn", "yl", "q", "sd"], []),
        "+ the defense's strength": (["dp", "pas", "tkb", "tfl", "ydb", "dn", "yl", "q", "sd"], ["def_str"]),
        "+ snaps since the defense rested": (["dp", "pas", "tkb", "tfl", "ydb", "dn", "yl", "q", "sd", "sr"], ["def_str"]),
    }
    for name, (cats, nums) in specs.items():
        x, names = design(d, cats, nums)
        b, se = poisson(x, y, off, grp)
        keep = ["dp=4-6", "dp=7+"] + ([k for k in names if k.startswith("sr=")] if "sr" in cats else [])
        log(f"    {name:<38} rate ratio against plays 1-3: {show(b, se, names, keep, exp=True)}")
        if side == "defense" and name == "play type only":
            raw = np.exp(b[names.index("dp=7+")])
        if side == "defense" and name == "+ field position, quarter, score":
            ctl = np.exp(b[names.index("dp=7+")])
            log(f"    -> the rise at 7+ with play type and field position held: {100 * (ctl - 1):+.1f}% against {100 * (raw - 1):+.1f}% with play type only; kept {100 * (ctl - 1) / (raw - 1):.0f}% of it (the bet: under 50%)")
    # snaps since rest alone (the idea's measure), with the play controls
    x, names = design(d, ["sr", "pas", "tkb", "tfl", "ydb", "dn", "yl", "q", "sd"], ["def_str"])
    b, se = poisson(x, y, off, grp)
    log(f"    snaps since rest alone (+ every control but drive play): {show(b, se, names, [k for k in names if k.startswith('sr=')], exp=True)}")

# ================================================================ I29 pays?
log("\nI29 (pays?): a defender's long-drive snaps last game beside next_logit, next game's health absence, walk-forward 2018-2024")
dpp = pp.filter(c("side") == "defense").join(pbp.select("game_id", "play_id", "drive_play", "week"), on=["game_id", "play_id"], how="inner")
pg = dpp.group_by("gsis_id", "game_id", "season", "week").agg(n_def=pl.len(), n_long=(c("drive_play") >= 7).sum()).sort("gsis_id", "season", "week")
hist = pl.read_parquet(K.cache_dir() / "hist_next_logit.parquet").filter(c("y").is_not_null() & c("grp").is_in(["DL", "LB", "DB"]))
feats = pl.read_parquet(K.cache_dir() / "features.parquet", columns=["gsis_id", "game_id", "season", "week"])
hist = hist.drop("season").join(feats, on=K.KEYS, how="left")
# his last game before this one: the latest player-game with an earlier (season, week)
pg = pg.with_columns(sw=c("season") * 100 + c("week")).sort("sw")
h = hist.with_columns(sw=c("season") * 100 + c("week")).sort("sw")
h = h.join_asof(pg.select("gsis_id", "sw", "n_def", "n_long").with_columns(sw=c("sw") + 0), on="sw", by="gsis_id", strategy="backward", allow_exact_matches=False)
h = h.with_columns(c("n_long").fill_null(0), c("n_def").fill_null(0)).with_columns(
    lp=pl.Series(X._logit(h["mean"].to_numpy())), long=np.log1p(c("n_long")), share_long=pl.when(c("n_def") > 0).then(c("n_long") / c("n_def")).otherwise(0.0))
log(f"  defender rows {h.height:,}; mean long-drive snaps last game {h['n_long'].mean():.1f} of {h['n_def'].mean():.1f}")


def walk_stack(df: pl.DataFrame, cols: list[str]) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression

    p = np.full(df.height, np.nan)
    s = df["season"].to_numpy()
    xa = df.select(cols).to_numpy().astype(float)
    ya = df["y"].to_numpy().astype(int)
    for season in range(2018, 2025):
        tr, te = s < season, s == season
        m = LogisticRegression(C=1e4, max_iter=2000).fit(xa[tr], ya[tr])
        p[te] = m.predict_proba(xa[te])[:, 1]
    return p


def ll(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def paired(la: np.ndarray, lb: np.ndarray, steps: np.ndarray, seed: int = 0):
    """Share of b's loss a removes, with a 90% interval from resampled weeks."""
    u, g = np.unique(steps, return_inverse=True)
    da = np.bincount(g, lb - la)
    db = np.bincount(g, lb)
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(len(u), np.full(len(u), 1 / len(u)), size=2000)
    boot = (draws @ da) / (draws @ db)
    return da.sum() / db.sum(), *np.quantile(boot, [0.05, 0.95])


h = h.filter(c("season") >= 2017)
sc = h["season"].to_numpy() >= 2018
y = h["y"].to_numpy().astype(int)
base = walk_stack(h, ["lp"])
for cols in (["lp", "long"], ["lp", "long", "share_long"]):
    new = walk_stack(h, cols)
    r, lo, hi = paired(ll(new, y)[sc], ll(base, y)[sc], h["step"].to_numpy()[sc])
    null = []
    extra = [x for x in cols if x != "lp"]
    for k in range(1, 20):
        sh = h.with_columns(pl.struct(extra).shuffle(seed=CFG.seed + k).over("step").struct.unnest())
        null.append(paired(ll(walk_stack(sh, cols), y)[sc], ll(base, y)[sc], h["step"].to_numpy()[sc])[0])
    log(f"  next_logit + {', '.join(extra):<20} against next_logit recalibrated: {100 * r:+.3f}% of the log loss ({100 * lo:+.3f} to {100 * hi:+.3f}); copies' max {100 * max(null):+.3f}%; counts: {lo > 0 and r > max(null)}")

# ================================================================ I30
log("\nI30: second-half plays, the defense's first-half snaps faced (per +10), errors clustered by game")
sh2 = pbp.filter((c("game_half") == "Half2") & c("fh_snaps").is_not_null() & c("epa").is_not_null())
off_fh = pbp.filter(c("game_half") == "Half1").group_by("game_id", "posteam").agg(off_fh_epa=c("epa").mean(), off_fh_n=pl.len())
sh2 = sh2.join(off_fh, on=["game_id", "posteam"], how="left").with_columns(c("off_fh_epa").fill_null(0.0), fh10=c("fh_snaps") / 10,
                                                                                ydst=c("ydstogo").clip(1, 20).cast(pl.Float64))
drop = sh2.filter(c("qb_dropback") == 1)
runs = sh2.filter(c("play_type") == "run")
CTL_C = ["dn", "yl", "q", "sd", "wpb"]
for name, d, yname in (("dropbacks, EPA", drop, "epa"), ("dropbacks, sack or hit (pass rush)", drop.with_columns(rush_hit=((c("sack") == 1) | (c("qb_hit") == 1)).cast(pl.Float64)), "rush_hit"),
                       ("non-sack dropbacks, EPA (coverage)", drop.filter(c("sack") != 1), "epa"), ("runs, EPA (the check)", runs, "epa")):
    yv, gv = d[yname].to_numpy().astype(float), d["game_id"].to_numpy()
    for spec, nums in (("situation only", ["fh10", "ydst"]), ("+ both sides' strength", ["fh10", "ydst", "def_str", "off_str"]),
                       ("+ the day's matchup (offense's first-half EPA)", ["fh10", "ydst", "def_str", "off_str", "off_fh_epa"])):
        x, names = design(d, CTL_C, nums)
        b, se = ols(x, yv, gv)
        log(f"  {name:<38} {spec:<48} per +10 first-half snaps: {show(b, se, names, ['fh10'])} [{d.height:,} plays]")

# ================================================================ I50
log("\nI50: the share of the defenders on the field who aren't the team's regulars (under 60% of its defensive snaps that season)")
dfp = pp.filter(c("side") == "defense")
team_n = dfp.select("game_id", "play_id", "team", "season").unique().group_by("team", "season").agg(team_plays=pl.len())
reg = dfp.group_by("gsis_id", "team", "season").agg(n=pl.len()).join(team_n, on=["team", "season"]).with_columns(regular=(c("n") / c("team_plays")) >= 0.6)
dfp = dfp.join(reg.select("gsis_id", "team", "season", "regular"), on=["gsis_id", "team", "season"], how="left")
grp_map = {"DL": "line", "LB": "linebackers", "DB": "backs"}
bs = dfp.group_by("game_id", "play_id").agg(backup=1 - c("regular").cast(pl.Float64).mean(),
                                             **{f"backup_{v}": 1 - c("regular").filter(c("group") == k).cast(pl.Float64).mean() for k, v in grp_map.items()})
d = bs.join(pbp, on=["game_id", "play_id"], how="inner")
log(f"  defensive plays {d.height:,}; mean backup share {d['backup'].mean():.3f}; by drive play: " + ", ".join(
    f"{r['dp4']} {r['b']:.3f}" for r in d.group_by("dp4").agg(b=c("backup").mean()).sort("dp4").iter_rows(named=True)))
for col in ("backup", "backup_line", "backup_linebackers", "backup_backs"):
    dd = d.filter(c(col).is_not_null())
    x, names = design(dd, ["dp4", "pas", *CTL_C], ["def_str"])
    b, se = ols(x, dd[col].to_numpy().astype(float), dd["game_id"].to_numpy())
    log(f"  {col:<20} points of share against plays 1-3, situation held: {show(b, se, names, ['dp4=4-6', 'dp4=7-9', 'dp4=10+'], scale=100, unit=' pts')}")
d2 = d.filter((c("game_half") == "Half2") & c("fh_snaps").is_not_null()).with_columns(fh10=c("fh_snaps") / 10)
x, names = design(d2, ["pas", *CTL_C], ["fh10", "def_str"])
b, se = ols(x, d2["backup"].to_numpy().astype(float), d2["game_id"].to_numpy())
log(f"  second half, backup share per +10 first-half snaps faced, situation held: {show(b, se, names, ['fh10'], scale=100, unit=' pts')}")
dropb = drop.join(bs.select("game_id", "play_id", "backup"), on=["game_id", "play_id"], how="inner")
for spec, nums in (("I30 with the matchup", ["fh10", "ydst", "def_str", "off_str", "off_fh_epa"]), ("I30 with the matchup + backup share", ["fh10", "ydst", "def_str", "off_str", "off_fh_epa", "backup"])):
    x, names = design(dropb, CTL_C, nums)
    b, se = ols(x, dropb["epa"].to_numpy().astype(float), dropb["game_id"].to_numpy())
    keep = ["fh10"] + (["backup"] if "backup" in nums else [])
    log(f"  {spec:<40} dropback EPA: {show(b, se, names, keep)}")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
