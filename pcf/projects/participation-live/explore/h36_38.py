"""The CEO's hunches of 2026-11-12, tested on the answer key (2019-2024), plus two checks for the
CEO's other asks.

- **H36, tandems:** "maybe Steve and Jerry both tend to leave the field at the same intervals or
  same time". Per pair of part-timers in a team-game-side: the correlation of their changes
  between consecutive snaps of a drive (+1 = they come on and go off together, -1 = one replaces
  the other). Against a null (one player's changes shifted in time), and whether a pair's value
  repeats (odd weeks against even weeks; next season, same team). Beyond the model: the same for
  their misses (on minus the sequence model's chance), which the model doesn't know.
- **H37, a coach's paired swaps:** "maybe a specific coach prefers to substitute the tight end at
  the same time as substituting the second string wide receiver". Per role pair (group and rank by
  snaps in the game: TE1, TE2, WR3...), per team-season: the mean change correlation, beyond the
  league's for that role pair. Does it repeat (odd/even weeks; next season with the same head coach
  and with a new one)?
- **H38, schemes and substitution:** "if schemes influence the coaches choices to substitute
  varying players or positions". Each team-season's players changed per snap (offense, defense)
  against its scheme: the charted traits (personnel, nickel and dime, man, blitz; post-season) and
  traits the play-by-play gives live (shotgun, no-huddle, pass rate).
- **Personnel's worth:** the likeliest lineup with each play's true counts of each group (an
  oracle: what knowing the personnel the morning after would add).
- **Per-play certainty:** for the likeliest lineup, the expected share of its 11 that are right
  (the sum of the chances of the players it picks, / 11), against the share actually right.

Writes h36_38.txt.
"""

# ruff: noqa: E501
from pathlib import Path

import numpy as np
import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.participation_live import reconstruct

c = pl.col
HERE = Path(__file__).parent
SEASONS = list(range(2019, 2025))
SCORED = reconstruct.cache_dir() / "scored_2019_2024.parquet"
rng = np.random.default_rng(0)
out_lines: list[str] = []


def say(*xs):
    s = " ".join(str(x) for x in xs)
    print(s, flush=True)
    out_lines.append(s)


def r(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 5 else float("nan")


def corr_cols(x: np.ndarray) -> np.ndarray:
    """Pairwise correlations of the columns of x (NaN where a column has no variance)."""
    x = x - x.mean(0)
    sd = np.sqrt((x**2).sum(0))
    with np.errstate(invalid="ignore", divide="ignore"):
        z = x / sd
    return z.T @ z


# ---------- pairs, per season ----------
pair_rows = []
team_rows = []
for season in SEASONS:
    g = reconstruct.load(season).select("game_id", "play_id", "side", "team", "gsis_id", "week", "group", "n", "sd", "full", "on")
    s = pl.scan_parquet(SCORED).filter(c("season") == season).select("game_id", "play_id", "side", "gsis_id", "p_sequence").collect()
    g = g.join(s, on=["game_id", "play_id", "side", "gsis_id"], how="left").sort("game_id", "side", "team", "gsis_id", "n")
    # team-season substitution (truth): players changed per snap within drives
    key = ["game_id", "side", "team", "gsis_id"]
    g = g.with_columns(d=(c("on").cast(pl.Int8) - c("on").shift(1).over(key).cast(pl.Int8)), e=c("on") - c("p_sequence"))
    ch = g.filter(c("sd")).group_by("game_id", "side", "team", "n").agg(ch=c("d").abs().sum() / 2)
    team_rows.append(ch.group_by("side", "team").agg(subs=c("ch").mean()).with_columns(season=pl.lit(season)))
    # roles: group + rank by snaps (on count) in the game
    tot = g.group_by("game_id", "side", "team", "gsis_id", "group").agg(snaps=c("on").sum(), full=c("full").first())
    tot = tot.with_columns(rank=c("snaps").rank("ordinal", descending=True).over("game_id", "side", "team", "group"))
    tot = tot.with_columns(role=c("group") + c("rank").cast(pl.String))
    part = tot.filter(~c("full") & (c("snaps") > 0))
    g = g.join(part.select("game_id", "side", "team", "gsis_id", "role"), on=["game_id", "side", "team", "gsis_id"], how="inner")
    for (gid, side, team), d in g.filter(c("sd") & c("d").is_not_null()).partition_by(["game_id", "side", "team"], as_dict=True).items():
        dw = d.pivot(on="gsis_id", index="n", values="d").sort("n")
        ew = d.pivot(on="gsis_id", index="n", values="e").sort("n")
        ids = [x for x in dw.columns if x != "n"]
        if len(ids) < 2 or dw.height < 20:
            continue
        D = dw.select(ids).fill_null(0).to_numpy().astype(float)
        E = ew.select(ids).fill_null(0).to_numpy().astype(float)
        nch = np.abs(D).sum(0)
        keep = nch >= 2
        if keep.sum() < 2:
            continue
        ids = [i for i, k in zip(ids, keep, strict=True) if k]
        D, E = D[:, keep], E[:, keep]
        # null: each player's changes shifted by a random lag (keeps his own rhythm)
        Dn = np.column_stack([np.roll(D[:, j], rng.integers(5, D.shape[0] - 5)) for j in range(D.shape[1])])
        cd, ce, cn = corr_cols(D), corr_cols(E), corr_cols(Dn)
        iu = np.triu_indices(len(ids), 1)
        u = d.unique("gsis_id")
        roles = dict(zip(u["gsis_id"].to_list(), u["role"].to_list(), strict=True))
        wk = d["week"][0]
        for a, b in zip(*iu, strict=True):
            i, j = sorted((ids[a], ids[b]))
            ri, rj = sorted((roles[i], roles[j]))
            pair_rows.append((season, wk, gid, side, team, i, j, ri, rj, cd[a, b], ce[a, b], cn[a, b], D.shape[0]))
    say(f"season {season}: {len(pair_rows)} pair-games so far")

P = pl.DataFrame(pair_rows, schema=["season", "week", "game_id", "side", "team", "a", "b", "role_a", "role_b", "dcorr", "ecorr", "ncorr", "trans"], orient="row")
P = P.with_columns(role_pair=c("role_a") + "-" + c("role_b"), grp_pair=c("role_a").str.replace(r"\d+", "") + "-" + c("role_b").str.replace(r"\d+", ""))
P = P.filter(c("dcorr").is_finite())
P.write_parquet(reconstruct.cache_dir() / "pairs_2019_2024.parquet")

say("\n== H36 tandems: players' changes between snaps, per pair-game (2019-2024) ==")
say(f"pair-games {P.height}; share with change correlation above +0.5: {(P['dcorr'] > 0.5).mean():.3f} (null {(P['ncorr'] > 0.5).mean():.3f}); below -0.5: {(P['dcorr'] < -0.5).mean():.3f} (null {(P['ncorr'] < -0.5).mean():.3f})")
with pl.Config(tbl_rows=40, tbl_width_chars=300, float_precision=3):
    gp = P.group_by("side", "grp_pair").agg(pairs=pl.len(), dcorr=c("dcorr").mean(), null=c("ncorr").mean(), together=(c("dcorr") > 0.5).mean(), swap=(c("dcorr") < -0.5).mean(), miss_corr=c("ecorr").mean()).filter(c("pairs") > 2000).sort("side", "dcorr")
    say(str(gp))


def repeat(df: pl.DataFrame, unit: list[str], col: str, min_games: int = 3) -> tuple[float, int]:
    """Odd weeks against even weeks: r across units of the unit's mean `col`."""
    h = df.with_columns(half=(c("week") % 2)).group_by(*unit, "half").agg(v=c(col).mean(), k=pl.len()).filter(c("k") >= min_games)
    w = h.pivot(on="half", index=unit, values="v").drop_nulls()
    if w.height < 10 or "0" not in w.columns or "1" not in w.columns:
        return float("nan"), w.height
    return r(w["0"], w["1"]), w.height


say("\nDoes a pair's habit repeat? Odd weeks against even weeks, pairs with 3+ games in each half:")
for side in ("offense", "defense"):
    s = P.filter(c("side") == side)
    rd, n = repeat(s, ["season", "team", "a", "b"], "dcorr")
    re_, _ = repeat(s, ["season", "team", "a", "b"], "ecorr")
    rn, _ = repeat(s, ["season", "team", "a", "b"], "ncorr")
    say(f"  {side}: change correlation r {rd:.2f} ({n} pairs), the model's misses r {re_:.2f}, null r {rn:.2f}")
    for gpair in s["grp_pair"].unique().sort().to_list():
        ss = s.filter(c("grp_pair") == gpair)
        if ss.height < 3000:
            continue
        rd, n = repeat(ss, ["season", "team", "a", "b"], "dcorr")
        re_, _ = repeat(ss, ["season", "team", "a", "b"], "ecorr")
        say(f"    {gpair}: changes r {rd:.2f}, misses r {re_:.2f} ({n} pairs)")

say("\nSeason to season, the same pair on the same team (mean change correlation):")
ps = P.group_by("season", "side", "team", "a", "b").agg(v=c("dcorr").mean(), ve=c("ecorr").mean(), k=pl.len()).filter(c("k") >= 4)
nx = ps.with_columns(season=c("season") - 1)
j = ps.join(nx, on=["season", "side", "team", "a", "b"], suffix="_next")
for side in ("offense", "defense"):
    jj = j.filter(c("side") == side)
    say(f"  {side}: changes r {r(jj['v'], jj['v_next']):.2f}, misses r {r(jj['ve'], jj['ve_next']):.2f} ({jj.height} pairs)")

# ---------- H37: role pairs per team-season ----------
say("\n== H37 a coach's paired swaps: role pairs per team-season, beyond the league's ==")
roles_keep = P.group_by("side", "role_pair").agg(k=pl.len()).filter(c("k") >= 3000)["role_pair"]
R = P.filter(c("role_pair").is_in(roles_keep)).with_columns(
    dres=c("dcorr") - c("dcorr").mean().over("season", "side", "role_pair"),
    eres=c("ecorr") - c("ecorr").mean().over("season", "side", "role_pair"),
)
coach_rows = []
for season in range(2018, 2025):
    gw = Gateway(TableSource(seasons=[season]))
    view = gw.view(END_OF_TIME, "in_season", reconstruct.INPUTS)
    coach_rows.append(reconstruct._coaches(view, [season]).group_by("team").agg(coach=c("coach").drop_nulls().mode().first()).with_columns(season=pl.lit(season)))
coaches = pl.concat(coach_rows)
for side in ("offense", "defense"):
    s = R.filter(c("side") == side)
    rd, n = repeat(s, ["season", "team", "role_pair"], "dres")
    re_, _ = repeat(s, ["season", "team", "role_pair"], "eres")
    ts = s.group_by("season", "team", "role_pair").agg(v=c("dres").mean(), ve=c("eres").mean(), k=pl.len()).filter(c("k") >= 6)
    ts = ts.join(coaches, on=["season", "team"], how="left")
    jn = ts.join(ts.with_columns(season=c("season") - 1), on=["season", "team", "role_pair"], suffix="_next")
    same = jn.filter(c("coach") == c("coach_next"))
    new = jn.filter(c("coach") != c("coach_next"))
    spread = ts.group_by("role_pair").agg(sd=c("v").std())["sd"].mean()
    say(f"  {side}: odd/even weeks r {rd:.2f} ({n} team-role-pairs), misses r {re_:.2f}; next season same coach r {r(same['v'], same['v_next']):.2f} ({same.height}), new coach r {r(new['v'], new['v_next']):.2f} ({new.height}); misses next season same coach r {r(same['ve'], same['ve_next']):.2f}; teams' spread (SD) {spread:.3f}")
    with pl.Config(tbl_rows=30, tbl_width_chars=300, float_precision=3):
        top = s.group_by("role_pair").agg(k=pl.len(), league=c("dcorr").mean()).sort("league")
        say(str(top.head(8)))
        say(str(top.tail(5)))
# the CEO's example: TE and the second-string receivers
ex = R.filter(c("side") == "offense", c("role_pair").is_in(["TE2-WR3", "TE2-WR4", "TE1-WR3", "TE2-WR2"]))
say("\nThe CEO's example, offense TE with WR2-4, league mean change correlation and team spread:")
with pl.Config(tbl_rows=10, float_precision=3):
    tsd = ex.group_by("season", "team", "role_pair").agg(v=c("dres").mean(), k=pl.len()).filter(c("k") >= 6).group_by("role_pair").agg(team_sd=c("v").std())
    say(str(ex.group_by("role_pair").agg(k=pl.len(), league=c("dcorr").mean()).join(tsd, on="role_pair", how="left")))

# ---------- H38: schemes ----------
say("\n== H38 schemes and substitution, per team-season ==")
T = pl.concat(team_rows)
flags = []
for season in SEASONS:
    g = reconstruct.load(season).filter(c("side") == "offense").unique(["game_id", "play_id"]).select("team", "f_shotgun", "f_no_huddle", "f_pass")
    flags.append(g.group_by("team").agg(shotgun=c("f_shotgun").mean(), no_huddle=c("f_no_huddle").mean(), pass_rate=c("f_pass").mean()).with_columns(season=pl.lit(season)))
F = pl.concat(flags)
ch = []
for season in SEASONS:
    gw = Gateway(TableSource(seasons=[season]))
    v = gw.view(END_OF_TIME, "retrospective", {"team_season": ("charted",)})
    ch.append(v.table("team_season", seasons=[season]))
C = pl.concat(ch, how="diagonal_relaxed")
off = T.filter(c("side") == "offense").join(F, on=["team", "season"]).join(C, on=["team", "season"], how="left")
de = T.filter(c("side") == "defense").join(C, on=["team", "season"], how="left")
# the opponent's offense: the defense faces it
say("Same season, r with players changed per snap (team-seasons):")
for col in ["shotgun", "no_huddle", "pass_rate", "off_11_rate", "off_12_rate", "off_21_rate", "off_heavy_rate", "off_pistol_rate"]:
    say(f"  offense ~ {col}: r {r(off['subs'], off[col]):.2f}")
for col in ["def_nickel_rate", "def_dime_rate", "def_man_rate", "def_two_high_rate", "def_blitz_rate", "def_rushers", "def_box"]:
    say(f"  defense ~ {col}: r {r(de['subs'], de[col]):.2f}")
# beyond the team's own last season: residual of subs on last season's subs, against scheme change
for name, d, cols in (("offense", off, ["shotgun", "off_11_rate", "off_12_rate", "off_heavy_rate"]), ("defense", de, ["def_nickel_rate", "def_dime_rate", "def_man_rate", "def_blitz_rate"])):
    last = d.select("team", c("season") + 1, subs_last=c("subs"), **{f"{x}_last": c(x) for x in cols})
    dd = d.join(last, on=["team", "season"]).join(coaches, on=["team", "season"], how="left").join(coaches.with_columns(c("season") + 1).rename({"coach": "coach_last"}), on=["team", "season"], how="left")
    x = dd["subs_last"].to_numpy()
    y = dd["subs"].to_numpy()
    b = np.polyfit(x, y, 1)
    res = y - np.polyval(b, x)
    say(f"  {name}: this season's subs on last season's r {r(x, y):.2f} (same coach {r(dd.filter(c('coach') == c('coach_last'))['subs_last'], dd.filter(c('coach') == c('coach_last'))['subs']):.2f}, new coach {r(dd.filter(c('coach') != c('coach_last'))['subs_last'], dd.filter(c('coach') != c('coach_last'))['subs']):.2f}); what's left against the change in scheme:")
    for col in cols:
        say(f"    change in {col}: r {r(res, dd[col] - dd[f'{col}_last']):.2f}")

# ---------- personnel's worth, and per-play certainty ----------
say("\n== Personnel's worth (oracle) and per-play certainty, likeliest lineup ==")
rows = []
cal = []
for season in SEASONS:
    s = pl.scan_parquet(SCORED).filter(c("season") == season, c("full_truth")).select(
        "game_id", "play_id", "side", "gsis_id", "group", "pinned", "on", "p_sequence", "top_sequence").collect()
    key = ["game_id", "play_id", "side"]
    # oracle: per play-group, the true count; pick pins then the highest chances
    s = s.with_columns(k_true=c("on").sum().over(*key, "group"), pr=pl.when(c("pinned")).then(2.0).otherwise(c("p_sequence")))
    s = s.with_columns(rk=c("pr").rank("ordinal", descending=True).over(*key, "group"))
    s = s.with_columns(oracle=c("rk") <= c("k_true"))
    for side in ("offense", "defense"):
        o = s.filter(c("side") == side, ~c("pinned"), c("on") == 1)
        rows.append({"season": season, "side": side, "likeliest": o["top_sequence"].mean(), "with_true_personnel": o["oracle"].mean()})
    pp = s.group_by(*key).agg(
        cert=(c("p_sequence").clip(0, 1) * c("top_sequence")).sum() / 11,
        right=((c("on") == 1) & c("top_sequence")).sum() / 11,
        open_cert=(c("p_sequence") * c("top_sequence") * ~c("pinned")).sum() / (c("top_sequence") & ~c("pinned")).sum(),
        open_right=((c("on") == 1) & c("top_sequence") & ~c("pinned")).sum() / (c("top_sequence") & ~c("pinned")).sum(),
    )
    cal.append(pp.with_columns(season=pl.lit(season)))
with pl.Config(tbl_rows=20, float_precision=4):
    say(str(pl.DataFrame(rows).group_by("side").agg(pl.exclude("season").mean())))
cal = pl.concat(cal)
for side in ("offense", "defense"):
    cc = cal.filter(c("side") == side)
    say(f"{side}: certainty mean {cc['cert'].mean():.3f}, right {cc['right'].mean():.3f}; r(certainty, right) per play {r(cc['cert'], cc['right']):.2f}; open spots: certainty {cc['open_cert'].mean():.3f}, right {cc['open_right'].mean():.3f}, r {r(cc['open_cert'], cc['open_right']):.2f}")
    b = cc.with_columns(dec=(c("cert").rank("ordinal") * 10 / pl.len()).floor().clip(0, 9)).group_by("dec").agg(plays=pl.len(), certainty=c("cert").mean(), right=c("right").mean(), open_certainty=c("open_cert").mean(), open_right=c("open_right").mean()).sort("dec")
    with pl.Config(tbl_rows=12, float_precision=3):
        say(str(b))
(HERE / "h36_38.txt").write_text("\n".join(out_lines), encoding="utf-8")
