"""The build's own checks (decision 0043), on the touchdown parts and on saved feature histories.

- `facts`: expected touchdowns calibrated by tenth on held-out seasons and against a shuffled
  copy; the drive model's calibration; the ceilings (players, thrown, teams; the team's measured
  first, with the drive-aware hindsight); the luck measure; near misses; consistency.
- `walks`: every rung of one family and horizon walked on the validated run's saved features
  (`pcf.validation.backtest.walk`: each row predicted by a model fit only on earlier rows), A
  against B, rung 0, trees and the side tests (I58, H67, H68), with 90% intervals by week.
- `ideas`: I61, the throw's expected touchdowns knowing the passer and his offense.

Reading saved files lives in the harness (`pcf.validation.backtest.load_features`), not here.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.experts.td_expert import features as F
from pcf.experts.td_expert import model as M
from pcf.validation import backtest, calibration
from pcf.validation.compare import block_interval, compare
from pcf.validation.consistency import consistency
from pcf.validation.scores import row_losses

c = pl.col
SEASONS = list(range(2016, 2025))  # the reported backtest
FACT_INPUTS = {
    "play": ("xtd",),
    "drive": ("td_chance",),
    "player_game": ("touchdowns",),
    "team_game": ("touchdowns",),
}


def _view(inputs=None):
    return Gateway().view(END_OF_TIME, "in_season", inputs or FACT_INPUTS)


PLAY_COLUMNS = ["season", "week", "game_id", "play_id", "tdx_gsis_id", "tdx_kind", "tdx_position",
                "tdx_passer_id", "tdx_team", "tdx_yardline", "tdx_air", "tdx_xtd", "tdx_td",
                "tdx_source", "qb_scramble"]  # fmt: skip


def plays_of(view, seasons: Sequence[int]) -> pl.DataFrame:
    """The chances (`play.xtd`), a season at a time: the play spine is wide."""
    return pl.concat([view.table("play", seasons=[s]).select(PLAY_COLUMNS).filter(
        c("tdx_xtd").is_not_null()) for s in seasons])  # fmt: skip


def pct(x: float) -> str:
    return f"{100 * x:+.2f}%"


# ---------------------------------------------------------------- gains with intervals
def gain(new: pl.DataFrame, base: pl.DataFrame, keys: Sequence[str], block: str = "step",
         seed: int = 0) -> dict:  # fmt: skip
    """What `new` removes from `base`'s error on the rows both scored, as shares of `base`'s:
    the Poisson log loss (`loss`) and the squared error (`readable`), each with its 90% interval
    from whole weeks resampled."""
    p = new.select(*keys, block, "loss", "readable").join(
        base.select(*keys, loss_b="loss", readable_b="readable"), on=list(keys), how="inner"
    )
    out = {"rows": p.height}
    for col in ("loss", "readable"):
        per = p.group_by(block).agg(d=(c(f"{col}_b") - c(col)).sum(), b=c(f"{col}_b").sum())
        d, b = per["d"].to_numpy(), per["b"].to_numpy()
        lo, hi = block_interval(d, b, seed=seed)
        out[col] = (float(d.sum() / b.sum()), lo, hi)
    return out


def gain_line(label: str, g: dict) -> str:
    ll, se = g["loss"], g["readable"]
    verdict = "better" if ll[1] > 0 else ("worse" if ll[2] < 0 else "tie")
    return (f"  {label:<44} log loss {pct(ll[0])} ({pct(ll[1])} to {pct(ll[2])}); squared error "
            f"{pct(se[0])} ({pct(se[1])} to {pct(se[2])}): {verdict}; {g['rows']:,} rows")  # fmt: skip


def removed(pred: pl.DataFrame) -> float:
    """Share of squared error around the scored rows' own average the forecast removes."""
    y, m = pred["y"].to_numpy(), pred["mean"].to_numpy()
    return float(1 - ((m - y) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def removed_line(label: str, pred: pl.DataFrame, by: str | None = None) -> str:
    text = f"  {label:<30} removes {100 * removed(pred):5.1f}% ({pred.height:,} rows)"
    if by and by in pred.columns:
        parts = [f"{g} {100 * removed(d):.1f}%" for (g,), d in
                 sorted(pred.group_by(by), key=lambda t: str(t[0]))]  # fmt: skip
        text += "; " + ", ".join(parts)
    return text


def calibration_line(label: str, pred: pl.DataFrame) -> str:
    rep = calibration.count_report(pred)
    one, two = rep["one"], rep["two"]
    return (f"  {label:<30} 1+: error {one['error']:.2f} points, slope {one['slope']:.2f}; "
            f"2+: error {two['error']:.2f}, slope {two['slope']:.2f}; said {pred['mean'].mean():.3f}"
            f" a row, got {pred['y'].mean():.3f}")  # fmt: skip


# ---------------------------------------------------------------- walks on saved features
def walk_saved(expert, feats: pl.DataFrame, outs: pl.DataFrame, seasons: Sequence[int],
               first: int, transform=None) -> pl.DataFrame:  # fmt: skip
    """`expert` walked on saved features, testing `seasons`; `first` is the season the saved
    run's steps start at. Returns its scored rows with `step` and `season`."""
    every = backtest.steps(Gateway().calendar, expert.cadence, range(first, max(seasons) + 1),
                           expert.run)  # fmt: skip
    test = [s.index for s in every if s.season in set(seasons)]
    pred = backtest.walk(expert, feats, outs, every, test, "season", backtest.HALF_LIFE,
                         train_transform=transform)  # fmt: skip
    season = {s.index: s.season for s in every}
    keys = expert.keys()
    pred = pred.join(outs.select(*keys, "y"), on=keys, how="inner")
    extra = [x for x in ("position",) if x in feats.columns]
    pred = pred.join(feats.select(*keys, *extra).unique(keys), on=keys, how="left")
    return row_losses(pred, expert.kind).with_columns(season=c("step").replace_strict(season))


def _shuffled(seed: int):
    return lambda pool: backtest.shuffle_within_steps(pool, seed)


def walks(family: str, horizon: str, tag: str = "", shuffles: int = 20,
          seasons: Sequence[int] = SEASONS) -> list[str]:  # fmt: skip
    """Every rung of one family and horizon on the saved features of its validated run."""
    from pcf.experts.td_expert.run import saved_dir

    feats, outs = backtest.load_features(saved_dir(family, horizon, tag))
    first = int(feats["step_season"].min())
    keys = M.VARIANTS[f"{family}_{horizon}_rate"].keys()
    names = [n for n in M.VARIANTS if n.startswith(f"{family}_{horizon}_")]
    preds = {n: walk_saved(M.VARIANTS[n](), feats, outs, seasons, first) for n in names}
    rate, vol, ch = (preds[f"{family}_{horizon}_{r}"] for r in ("rate", "volume", "chances"))
    by = "position" if family != "team" else None
    lines = [f"td-expert walks: {family}, {horizon} game{'s' if horizon == 'rest' else ''}; "
             f"seasons {seasons[0]}-{seasons[-1]}; saved features from {first}", "",
             "Share of squared error removed against the scored rows' own average:"]  # fmt: skip
    for n, p in preds.items():
        lines.append(removed_line(n.split("_", 2)[2], p, by))
    lines += ["", "Calibration (Poisson around the mean):"]
    for n, p in preds.items():
        lines.append(calibration_line(n.split("_", 2)[2], p))
    lines += ["", "Gains (positive: the first is better; log loss decides, 90% by week):"]
    lines.append(gain_line("A (chances) against B (volume)", gain(ch, vol, keys)))
    lines.append(gain_line("B (volume) against rung 0 (rate)", gain(vol, rate, keys)))
    lines.append(gain_line("A (chances) against rung 0 (rate)", gain(ch, rate, keys)))
    if by:
        for pos in ("QB", "RB", "WR", "TE"):
            a, b = ch.filter(c("position") == pos), vol.filter(c("position") == pos)
            if a.height:
                lines.append(gain_line(f"  A against B, {pos}", gain(a, b, keys)))
    for n, p in preds.items():
        rung = n.split("_", 2)[2]
        if rung == "volume_trees":
            lines.append(gain_line("trees against B (O22)", gain(p, vol, keys)))
        elif rung.startswith("volume+qb_rz"):
            qb = c("position") == "QB"
            lines.append(gain_line("I58: + QB red-zone carries, QBs", gain(
                p.filter(qb), vol.filter(qb), keys)))  # fmt: skip
            lines.append(gain_line("I58: + QB red-zone carries, everyone", gain(p, vol, keys)))
        elif rung.startswith("volume+red_zone"):
            nq = c("position") != "QB"
            lines.append(gain_line("H68: + red-zone chances, non-QBs", gain(
                p.filter(nq), vol.filter(nq), keys)))  # fmt: skip
            for pos in ("RB", "WR", "TE"):
                lines.append(gain_line(f"  H68, {pos}", gain(
                    p.filter(c("position") == pos), vol.filter(c("position") == pos), keys)))  # fmt: skip
        elif rung.startswith("volume-calling"):
            lines.append(gain_line("H67: the calling (B against B without it)",
                                   gain(vol, p, keys)))  # fmt: skip
            for pos in ("QB", "RB", "WR", "TE"):
                lines.append(gain_line(f"  H67, {pos}", gain(
                    vol.filter(c("position") == pos), p.filter(c("position") == pos), keys)))  # fmt: skip
    if shuffles:
        lines += ["", f"Signal on the saved features ({shuffles} shuffled copies each):"]
        for r in ("volume", "chances"):
            n = f"{family}_{horizon}_{r}"
            real = preds[n]["loss"].mean()
            nulls = [walk_saved(M.VARIANTS[n](), feats, outs, seasons, first,
                                _shuffled(s))["loss"].mean() for s in range(shuffles)]  # fmt: skip
            lines.append(f"  {r:<10} log loss {real:.4f}; shuffled {min(nulls):.4f} to "
                         f"{max(nulls):.4f}; beats {sum(real < x for x in nulls)} of {shuffles}")  # fmt: skip
    lines += ["", "By season, A against B (log loss, positive: A better):"]
    for s in seasons:
        g = gain(ch.filter(c("season") == s), vol.filter(c("season") == s), keys)
        lines.append(f"  {s}: {pct(g['loss'][0])} ({pct(g['loss'][1])} to {pct(g['loss'][2])})")
    for n, p in preds.items():
        from pcf.experts.td_expert.run import cache_dir

        p.write_parquet(cache_dir() / f"walk_{n}{'_' + tag if tag else ''}.parquet")
    return lines


# ---------------------------------------------------------------- facts
def _tenths(p: np.ndarray, y: np.ndarray) -> tuple[float, float, list[str]]:
    t = calibration.probability_table(pl.DataFrame({"mean": p, "y": y}))
    err = calibration.calibration_error(t)
    slope = calibration.calibration_slope(pl.DataFrame({"mean": p, "y": y}))
    rows = [f"{int(r['bin'])}: {r['rows']:,} said {100 * r['predicted']:.1f}% got "
            f"{100 * r['actual']:.1f}%" for r in t.iter_rows(named=True)]  # fmt: skip
    return err, slope, rows


def _log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def facts() -> list[str]:
    view = _view()
    seasons = list(range(2012, 2025))
    plays = plays_of(view, seasons)
    lines = ["td-expert facts (2026-11-24): the touchdown parts, regular season and playoffs, "
             "2012-2024 unless said; the vault (2025) not read", ""]  # fmt: skip
    # 1. expected touchdowns, calibrated and against a shuffled copy
    lines.append("1. Expected touchdowns per chance, by tenth, 2016-2024 (fit on earlier seasons):")
    held = plays.filter(c("season").is_between(2016, 2024))
    rng = np.random.default_rng(0)
    groups = {
        "every chance": held,
        "targets (RB, WR, TE)": held.filter((c("tdx_kind") == "target")
                                            & c("tdx_position").is_in(["RB", "WR", "TE"])),
        "carries (RB, WR, TE)": held.filter((c("tdx_kind") == "carry")
                                            & c("tdx_position").is_in(["RB", "WR", "TE"])),
        "QB carries": held.filter(c("tdx_source") == "qb"),
        "throws (by passer)": held.filter((c("tdx_kind") == "target")
                                          & c("tdx_passer_id").is_not_null()),
    }  # fmt: skip
    for name, d in groups.items():
        p, y = d["tdx_xtd"].to_numpy(), d["tdx_td"].to_numpy()
        err, slope, _ = _tenths(p, y)
        shuffled = np.array([_log_loss(rng.permutation(p), y) for _ in range(20)])
        lines.append(f"  {name:<22} {d.height:>8,} chances, {y.sum():,.0f} touchdowns, "
                     f"{p.sum():,.0f} expected; error {err:.2f} points, slope {slope:.2f}; log "
                     f"loss {_log_loss(p, y):.4f} vs shuffled {shuffled.min():.4f}+ (beats 20 "
                     f"of 20: {bool(_log_loss(p, y) < shuffled.min())})")  # fmt: skip
    _, _, tenth_rows = _tenths(held["tdx_xtd"].to_numpy(), held["tdx_td"].to_numpy())
    lines += ["    every chance by tenth: " + "; ".join(tenth_rows)]
    by_season = held.group_by("season").agg(td=c("tdx_td").sum(), x=c("tdx_xtd").sum()).sort(
        "season")  # fmt: skip
    lines.append("    by season (touchdowns / expected): " + ", ".join(
        f"{r['season']} {r['td'] / r['x']:.3f}" for r in by_season.iter_rows(named=True)))  # fmt: skip
    # 2. the drive model
    drives = view.table("drive", seasons=seasons).filter(c("tdx_p_start").is_not_null())
    dh = drives.filter(c("season").is_between(2016, 2024))
    err, slope, _ = _tenths(dh["tdx_p_start"].to_numpy(), dh["tdx_td"].to_numpy())
    rz = dh.filter(c("tdx_reached_rz") == 1)
    err2, slope2, _ = _tenths(rz["tdx_p_rz"].to_numpy(), rz["tdx_td"].to_numpy())
    lines += ["", "2. The drive model (2016-2024): at the first snap, "
              f"{dh.height:,} drives, error {err:.2f} points, slope {slope:.2f}; at the first snap "
              f"inside the 20, {rz.height:,} drives ({100 * rz.height / dh.height:.0f}%), "
              f"scored {100 * rz['tdx_td'].mean():.1f}% against {100 * rz['tdx_p_rz'].mean():.1f}%"
              f" said, error {err2:.2f}, slope {slope2:.2f}"]  # fmt: skip
    fg = dh.filter(c("tdx_fg_try") == 1)
    fgr = fg.filter(c("tdx_reached_rz") == 1)
    lines.append(f"   near misses: {fg.height:,} field-goal drives came closest at "
                 f"{100 * fg['tdx_p_peak'].mean():.1f}% on average; the {fgr.height:,} that "
                 f"reached the 20 at {100 * fgr['tdx_p_peak'].mean():.1f}% "
                 f"({100 * (fgr['tdx_p_peak'] > 0.5).mean():.0f}% passed 50%); touchdown drives "
                 f"peaked at {100 * dh.filter(c('tdx_td') == 1)['tdx_p_peak'].mean():.1f}%")  # fmt: skip
    lines += ["", *ceilings(view), "", *luck_lines(view, plays), "", *consistency_lines(view)]
    return lines


def _team_rows(view, seasons) -> pl.DataFrame:
    tg = view.table("team_game", seasons=seasons).filter(c("touchdowns_known_at").is_not_null())
    return tg.filter(c("game_type") == "REG")


def ceilings(view) -> list[str]:
    """How much room there is: what hindsight would remove from the next game's and the rest of
    the season's error, against the plain average (the brief: the team's measured first)."""
    seasons = list(range(2016, 2025))
    t = _team_rows(view, seasons)
    lines = ["3. The ceilings (2016-2024, regular season; share of squared error removed "
             "against the plain average):", "  Teams, next game (every team-game):"]  # fmt: skip
    y = t["tdx_tds"].to_numpy()
    mse = ((y - y.mean()) ** 2).mean()

    def share(x):
        return 100 * (1 - ((x - y) ** 2).mean() / mse)

    lines.append(f"    {t.height:,} team-games, {y.mean():.2f} touchdowns a game (spread "
                 f"{y.std():.2f})")  # fmt: skip
    lines.append(f"    knowing where every drive started (drive model, first snap): "
                 f"{share(t['tdx_start_sum'].to_numpy()):.1f}%")  # fmt: skip
    lines.append(f"    knowing how many drives and red-zone trips (a straight line): "
                 f"{_fit_share(t, ['tdx_drives', 'tdx_rz_trips'], 'tdx_tds'):.1f}%")  # fmt: skip
    lines.append(f"    **drive-aware hindsight** (each red-zone trip's chance at the 20, every long "
                 f"touchdown): {share(t['tdx_hind'].to_numpy()):.1f}%; the dice left on those "
                 f"trips {100 * t['tdx_hind_var'].mean() / mse:.1f}% of the error")  # fmt: skip
    lines.append(f"    every chance's expected touchdowns summed (F21's, not fair): "
                 f"{share(t['tdx_xtd'].to_numpy()):.1f}%")  # fmt: skip
    # rest of season: sums over the team's remaining regular-season games, after weeks 4, 8, 12
    tw = t.select("team", "season", "week", "tdx_tds", "tdx_hind", "tdx_xtd", "tdx_hind_var",
                  "tdx_start_sum")  # fmt: skip
    rest = []
    for cut in (4, 8, 12):
        rest.append(tw.filter(c("week") > cut).group_by("team", "season").agg(
            c("tdx_tds", "tdx_hind", "tdx_xtd", "tdx_hind_var", "tdx_start_sum").sum(),
            games=pl.len()).with_columns(cut=pl.lit(cut)))  # fmt: skip
    r = pl.concat(rest)
    yr = r["tdx_tds"].to_numpy()
    mser = ((yr - yr.mean()) ** 2).mean()
    lines.append(f"  Teams, rest of season (after weeks 4, 8, 12; {r.height:,} rows, "
                 f"{yr.mean():.1f} touchdowns, spread {yr.std():.1f}):")  # fmt: skip
    for name, col in (("drive starts", "tdx_start_sum"), ("**drive-aware hindsight**", "tdx_hind"),
                      ("chances summed", "tdx_xtd")):  # fmt: skip
        x = r[col].to_numpy()
        lines.append(f"    {name}: {100 * (1 - ((x - yr) ** 2).mean() / mser):.1f}%")
    lines.append(f"    dice left under the drive-aware hindsight: "
                 f"{100 * r['tdx_hind_var'].mean() / mser:.1f}%")  # fmt: skip
    # players and thrown, next game: knowing that game's chances
    pg = view.table("player_game", seasons=seasons).filter(
        c("touchdowns_known_at").is_not_null())  # fmt: skip
    played = pg.filter((c("tdx_carries") + c("tdx_targets")) > 0)
    yp = played["tdx_td"].to_numpy()
    xp = played["tdx_xtd"].to_numpy()
    msep = ((yp - yp.mean()) ** 2).mean()
    lines.append(f"  Players with a chance, next game ({played.height:,}): knowing that game's "
                 f"chances {100 * (1 - ((xp - yp) ** 2).mean() / msep):.1f}%; dice "
                 f"{100 * played['tdx_var'].mean() / msep:.1f}%")  # fmt: skip
    qb = pg.filter(c("tdx_throws") >= 10)
    yq, xq = qb["tdx_thrown_td"].to_numpy(), qb["tdx_thrown_xtd"].to_numpy()
    mseq = ((yq - yq.mean()) ** 2).mean()
    lines.append(f"  QBs with 10+ throws, thrown touchdowns next game ({qb.height:,}): knowing "
                 f"every throw {100 * (1 - ((xq - yq) ** 2).mean() / mseq):.1f}%; dice "
                 f"{100 * qb['tdx_thrown_var'].mean() / mseq:.1f}%")  # fmt: skip
    return lines


def _fit_share(df: pl.DataFrame, cols: list[str], y: str) -> float:
    x = np.column_stack([np.ones(df.height), *[df[col].to_numpy() for col in cols]])
    yy = df[y].to_numpy()
    beta, *_ = np.linalg.lstsq(x, yy, rcond=None)
    return 100 * (1 - ((x @ beta - yy) ** 2).mean() / ((yy - yy.mean()) ** 2).mean())


def luck_lines(view, plays: pl.DataFrame) -> list[str]:
    """The luck measure, looking back (the CEO's idea; EXPLORATION F19)."""
    seasons = list(range(2016, 2025))
    plays = plays.filter(c("season").is_between(2016, 2024))
    pg = view.table("player_game", seasons=seasons).filter(c("touchdowns_known_at").is_not_null())
    lines = ["4. The luck measure (2016-2024):"]
    tds = plays.filter(c("tdx_td") == 1)
    lines.append(f"  the average touchdown came on a chance worth {100 * tds['tdx_xtd'].mean():.1f}% "
                 f"(median {100 * tds['tdx_xtd'].median():.1f}%); "
                 f"{100 * (tds['tdx_xtd'] < 0.1).mean():.0f}% on chances under 10%")  # fmt: skip
    scored = pg.filter(c("tdx_td") >= 1)
    lines.append(f"  player-games with a touchdown: median chance of at least that many "
                 f"{100 * scored['tdx_p_atleast'].median():.0f}%; "
                 f"{100 * (scored['tdx_p_atleast'] < 0.1).mean():.0f}% under 10%")  # fmt: skip
    season = pg.group_by("gsis_id", "season").agg(
        td=c("tdx_td").sum(), xtd=c("tdx_xtd").sum(), var=c("tdx_var").sum(),
        thrown=c("tdx_thrown_td").sum(), thrown_x=c("tdx_thrown_xtd").sum(),
        thrown_var=c("tdx_thrown_var").sum()).filter(c("var") > 0.5)  # fmt: skip
    z = ((season["td"] - season["xtd"]) / season["var"].sqrt()).to_numpy()
    lines.append(f"  player-seasons (dice spread over 0.7; {season.height:,}): touchdowns over "
                 f"expected in dice spreads have a spread of {z.std():.2f} (pure dice 1.00); "
                 f"{100 * (np.abs(z) > 2).mean():.1f}% beyond 2 (dice about 5%)")  # fmt: skip
    for lo, hi in ((2, 4), (4, 7), (7, 99)):
        b = season.filter(c("xtd").is_between(lo, hi, closed="left"))
        if b.height > 20:
            share = (b["var"].mean()) / b["td"].var()
            lines.append(f"    expecting {lo} to {hi if hi < 99 else 'more'}: {b.height} seasons, "
                         f"luck is {100 * min(share, 9.99):.0f}% of the spread in their totals")  # fmt: skip
    qs = season.filter(c("thrown_var") > 2)
    zq = ((qs["thrown"] - qs["thrown_x"]) / qs["thrown_var"].sqrt()).to_numpy()
    lines.append(f"  QB-seasons' thrown touchdowns ({qs.height}): spread {zq.std():.2f} in dice "
                 f"spreads; {100 * (np.abs(zq) > 2).mean():.1f}% beyond 2")  # fmt: skip
    # one season's exact chance for the extremes
    pos = plays.filter(c("tdx_position").is_in(["QB", "RB", "WR", "TE"]))
    ids = season.sort("td", descending=True).head(1)
    if ids.height:
        r = ids.row(0, named=True)
        mine = pos.filter((c("tdx_gsis_id") == r["gsis_id"]) & (c("season") == r["season"]))
        p = _at_least(mine["tdx_xtd"].to_numpy(), int(r["td"]))
        lines.append(f"  e.g. the most touchdowns in a season ({r['gsis_id']}, {r['season']}): "
                     f"{r['td']:.0f} on {r['xtd']:.1f} expected; chance of {r['td']:.0f}+ from "
                     f"those chances {100 * p:.2f}%")  # fmt: skip
    return lines


def _at_least(p: np.ndarray, k: int) -> float:
    """The chance these chances score k or more (Poisson-binomial). The parts' own vectorized
    version lives in the table builders, which an expert may not import (leakage check 1)."""
    dist = np.zeros(k + 1)
    dist[0] = 1.0
    for q in p:
        dist[1:] = dist[1:] * (1 - q) + dist[:-1] * q
        dist[0] *= 1 - q
    return float(1 - dist[:k].sum())


def consistency_lines(view) -> list[str]:
    """The second test for every new measure (CONSISTENCY.md)."""
    seasons = list(range(2012, 2025))
    pg = view.table("player_game", seasons=seasons).filter(c("touchdowns_known_at").is_not_null())
    reg = pg.filter(c("week") <= 18)
    played = reg.filter((c("tdx_carries") + c("tdx_targets")) > 0).with_columns(
        chances=c("tdx_carries") + c("tdx_targets"),
        i10=c("tdx_i10_carries") + c("tdx_i10_targets"),
        tdoe=c("tdx_td") - c("tdx_xtd"),
    )  # fmt: skip
    lines = ["5. Consistency (pcf.validation.consistency; odd against even weeks, then season to "
             "season; regular season 2012-2024):"]  # fmt: skip
    p = consistency(played, ["tdx_xtd", "tdx_td", "tdoe", "tdx_luck_z"], unit="gsis_id")
    lines += _cons_rows(p, "players with a chance, a game")
    for pos in ("QB", "RB", "WR", "TE"):
        p = consistency(played.filter(c("position") == pos), ["tdx_xtd", "tdoe"], unit="gsis_id")
        lines += _cons_rows(p, f"  {pos}")
    qb = reg.filter(c("tdx_throws") >= 10).with_columns(
        thrown_tdoe=(c("tdx_thrown_td") - c("tdx_thrown_xtd")) / c("tdx_throws"),
        thrown_xtd_per=c("tdx_thrown_xtd") / c("tdx_throws"),
    )
    lines += _cons_rows(consistency(qb, ["tdx_thrown_xtd", "thrown_xtd_per", "thrown_tdoe"],
                                    unit="gsis_id"), "QBs with 10+ throws")  # fmt: skip
    tg = _team_rows(view, seasons).with_columns(
        tdoe=c("tdx_tds") - c("tdx_xtd"),
        hind_oe=c("tdx_tds") - c("tdx_hind"),
        rz_rate=pl.when(c("tdx_rz_trips") > 0).then(c("tdx_rz_tds") / c("tdx_rz_trips")),
        near_miss_per=pl.when(c("tdx_fg_drives") > 0).then(c("tdx_near_miss") / c("tdx_fg_drives")),
        i10_pass=pl.when((c("tdx_i10_targets") + c("tdx_i10_carries")) > 0).then(
            c("tdx_i10_targets") / (c("tdx_i10_targets") + c("tdx_i10_carries"))),
    )  # fmt: skip
    lines += _cons_rows(consistency(tg, ["tdx_tds", "tdx_xtd", "tdx_hind", "tdoe", "hind_oe",
                                         "rz_rate", "tdx_near_miss", "near_miss_per", "i10_pass"],
                                    unit="team"), "teams, a game")  # fmt: skip
    return lines


def _cons_rows(df: pl.DataFrame, label: str) -> list[str]:
    out = [f"  {label}:"]
    for r in df.iter_rows(named=True):
        out.append(f"    {r['measure']:<16} week to week {r['week_r']:.2f} ({r['week_lo']:.2f} to "
                   f"{r['week_hi']:.2f}), season to season {r['season_r']:.2f} "
                   f"({r['season_lo']:.2f} to {r['season_hi']:.2f}); {r['unit_seasons']:,} "
                   f"unit-seasons; {r['verdict']}")  # fmt: skip
    return out


# ---------------------------------------------------------------- I61
def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _logistic(x: np.ndarray, y: np.ndarray, offset: np.ndarray, steps: int = 30) -> np.ndarray:
    """A logistic fit of `y` on `x` with a fixed offset (Newton steps; a tiny ridge)."""
    d = np.column_stack([np.ones(len(y)), x])
    beta = np.zeros(d.shape[1])
    for _ in range(steps):
        mu = 1 / (1 + np.exp(-(offset + d @ beta)))
        w = mu * (1 - mu)
        step = np.linalg.solve(d.T @ (d * w[:, None]) + 1e-6 * np.eye(d.shape[1]),
                               d.T @ (y - mu))  # fmt: skip
        beta += step
        if np.abs(step).max() < 1e-9:
            break
    return beta


def passer_aware(view, seasons: Sequence[int]) -> pl.DataFrame:
    """I61: each throw's expected touchdowns refit knowing the passer (his thrown touchdowns over
    expected per throw through last season, shrunk with 300 throws of the league's 0) and his
    offense (last season's EPA per play), beside the situation's own expected touchdowns (as a
    fixed offset). Fit on the seasons before each tested one. Prior seasons only: nothing from
    the tested season, so every value is known before its first game."""
    plays = plays_of(view, range(2012, max(seasons) + 1)).filter(
        (c("tdx_kind") == "target") & c("tdx_passer_id").is_not_null())  # fmt: skip
    per = plays.group_by("tdx_passer_id", "season").agg(
        n=pl.len(), oe=(c("tdx_td") - c("tdx_xtd")).sum()).sort("season")  # fmt: skip
    per = per.with_columns(
        n_before=c("n").cum_sum().over("tdx_passer_id") - c("n"),
        oe_before=c("oe").cum_sum().over("tdx_passer_id") - c("oe"),
    ).with_columns(passer=c("oe_before") / (c("n_before") + F.THROWN_PRIOR))
    eff = Gateway().view(END_OF_TIME, "in_season", {"team_game": ("efficiency",)}).table(
        "team_game", seasons=list(range(2011, max(seasons) + 1)))  # fmt: skip
    off = eff.filter(c("game_type") == "REG").group_by("team", "season").agg(
        offense=c("eff_epa").sum() / c("eff_plays").sum()).with_columns(c("season") + 1)  # fmt: skip
    rows = plays.join(per.select("tdx_passer_id", "season", "passer"),
                      on=["tdx_passer_id", "season"], how="left").join(
        off.rename({"team": "tdx_team"}), on=["tdx_team", "season"], how="left").with_columns(
        c("passer", "offense").fill_null(0.0))  # fmt: skip
    out = []
    for s in seasons:
        tr = rows.filter(c("season").is_between(2013, s - 1))
        te = rows.filter(c("season") == s)
        x = ["passer", "offense"]
        beta = _logistic(tr.select(x).to_numpy(), tr["tdx_td"].to_numpy().astype(float),
                         _logit(tr["tdx_xtd"].to_numpy()))  # fmt: skip
        z = _logit(te["tdx_xtd"].to_numpy()) + beta[0] + te.select(x).to_numpy() @ beta[1:]
        out.append(te.with_columns(xtd_pa=pl.Series(1 / (1 + np.exp(-z))),
                                   b_passer=pl.lit(beta[1]), b_offense=pl.lit(beta[2])))  # fmt: skip
    return pl.concat(out)


def _rest_rows(games: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """After weeks 4, 8 and 12: each QB's per-game averages so far and last season's, and his
    thrown touchdowns over the games he played after (the exploration's F22 rows)."""
    out = []
    for cut in (4, 8, 12):
        a = games.filter(c("week") <= cut).group_by("gsis_id", "season").agg(
            g_s=pl.len(), *[c(x).mean().alias(f"{x}_s") for x in cols])  # fmt: skip
        b = games.filter(c("week") > cut).group_by("gsis_id", "season").agg(
            y=c("ptd").sum(), g_after=pl.len())  # fmt: skip
        out.append(a.join(b, on=["gsis_id", "season"]).with_columns(cut=pl.lit(cut)))
    last = games.group_by("gsis_id", "season").agg(
        *[c(x).mean().alias(f"{x}_ls") for x in cols]).with_columns(c("season") + 1)  # fmt: skip
    df = pl.concat(out).filter((c("g_s") >= 2) & (c("att_s") >= 10))
    return df.join(last, on=["gsis_id", "season"], how="left").with_columns(
        c(f"{x}_ls").fill_null(c(f"{x}_s")) for x in cols)  # fmt: skip


def _walk_linear(df: pl.DataFrame, x: list[str], seasons: Sequence[int]) -> np.ndarray:
    """Per-game rate after the cut, a straight line on `x` weighted by games after, fit on
    earlier seasons (2013 on); times the games after."""
    out = np.full(df.height, np.nan)
    s_ = df["season"].to_numpy()
    X = np.column_stack([np.ones(df.height), df.select(x).to_numpy().astype(float)])
    g = df["g_after"].to_numpy().astype(float)
    r = df["y"].to_numpy() / g
    for s in seasons:
        tr = (s_ < s) & (s_ >= 2013)
        w = np.sqrt(g[tr])
        beta, *_ = np.linalg.lstsq(X[tr] * w[:, None], r[tr] * w, rcond=None)
        out[s_ == s] = (X[s_ == s] @ beta) * g[s_ == s]
    return out


def _gain_np(y, new, base, blocks) -> tuple[float, float, float]:
    d = pl.DataFrame({"b": blocks, "d": (base - y) ** 2 - (new - y) ** 2, "e": (base - y) ** 2})
    per = d.group_by("b").agg(c("d").sum(), c("e").sum())
    lo, hi = block_interval(per["d"].to_numpy(), per["e"].to_numpy())
    return float(per["d"].sum() / per["e"].sum()), lo, hi


def ideas(seasons: Sequence[int] = SEASONS) -> list[str]:
    view = _view({"play": ("xtd",), "player_game": ("touchdowns",)})
    pa = passer_aware(view, seasons)
    y = pa["tdx_td"].to_numpy().astype(float)
    ll0, ll1 = _log_loss(pa["tdx_xtd"].to_numpy(), y), _log_loss(pa["xtd_pa"].to_numpy(), y)
    lines = ["td-expert ideas (2026-11-24): I61, the throw's expected touchdowns knowing the passer "
             "and his offense; seasons 2016-2024, each fit on the seasons before", "",
             f"1. Per throw ({pa.height:,} throws): log loss {ll0:.5f} situation only, {ll1:.5f} "
             f"knowing the passer and offense ({pct((ll0 - ll1) / ll0)} of it)"]  # fmt: skip
    last = pa.filter(c("season") == max(seasons)).row(0, named=True)
    lines.append(f"   the fit for {max(seasons)}: passer {last['b_passer']:.1f} a unit of over-"
                 f"expected per throw (on the log-odds), offense {last['b_offense']:.3f} a unit "
                 f"of EPA per play")  # fmt: skip
    games = pa.group_by("tdx_passer_id", "game_id").agg(pxtd_pa=c("xtd_pa").sum()).rename(
        {"tdx_passer_id": "gsis_id"})  # fmt: skip
    pg = view.table("player_game", seasons=list(range(2012, max(seasons) + 1))).filter(
        (c("position") == "QB") & (c("tdx_throws") > 0) & (c("week") <= 18))  # fmt: skip
    g = pg.join(games, on=["gsis_id", "game_id"], how="left").select(
        "gsis_id", "season", "week", ptd="tdx_thrown_td", pxtd="tdx_thrown_xtd",
        att="tdx_throws", pxtd_pa=c("pxtd_pa").fill_null(c("tdx_thrown_xtd")))  # fmt: skip
    df = _rest_rows(g, ["ptd", "pxtd", "pxtd_pa", "att"]).sort("season", "cut", "gsis_id")
    in_test = df["season"].is_in(list(seasons)).to_numpy()
    test = df.filter(in_test)
    blk = (test["season"].cast(pl.String) + test["gsis_id"]).to_numpy()
    yy = test["y"].to_numpy().astype(float)

    def fc(cols):
        x = [f"{k}_{s}" for k in cols for s in ("s", "ls")] + ["cut"]
        return _walk_linear(df, x, seasons)[in_test]

    old, new = fc(["pxtd", "att"]), fc(["pxtd_pa", "att"])
    old_b, new_b = fc(["pxtd", "ptd", "att"]), fc(["pxtd_pa", "ptd", "att"])
    lines += ["", f"2. F22 rerun, QBs' rest-of-season thrown touchdowns ({test.height:,} rows: after "
              "weeks 4, 8, 12; a straight line per game left, not the exploration's lasso and "
              "trees):"]  # fmt: skip
    for label, a, b in (("past thrown touchdowns beyond expected (situation only)", old_b, old),
                        ("past thrown touchdowns beyond expected (passer-aware)", new_b, new),
                        ("passer-aware expected against situation only", new, old)):  # fmt: skip
        gg = _gain_np(yy, a, b, blk)
        lines.append(f"  {label}: {pct(gg[0])} ({pct(gg[1])} to {pct(gg[2])})")
    return lines
