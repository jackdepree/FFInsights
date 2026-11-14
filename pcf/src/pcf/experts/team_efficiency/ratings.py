"""The ratings walk (team-efficiency exploration, `explore/common.py` and `h42_dml.py`, ported).

Before each week of a season, a ridge regression on that season's games known so far:
value = league + home + offense + defense. Each game counts by its weight `W` (plays, or series)
times a recency weight (`half_life` in weeks), and the team effects are pulled toward a prior with
strength `lam` games' worth of `W`. The prior is last season's final rating times `pull`
(centred), walked from the first season the data has (whose prior is 0).

Two kinds of measure:
- **ridge** (`MEASURES`): one value per offense and game, `W` and `WY` columns of
  `team_game.efficiency`;
- **DML** (`DML`): Robinson's partialled-out regression (team-efficiency#F7). Per situation bin, the
  leftover of EPA after the outcome model is regressed on the team indicators less their
  situation propensity, cross-fitted by game halves (`fold`), propensities smoothed toward the
  fold's overall shares by `ALPHA` plays.

Ratings are in EPA per play (or series success) above the league: offense `o` (higher is better),
defense `d` (what it allows; lower is better). `sd` is the ridge's own posterior sd under its prior,
with plays as independent (it leaves out the prior's own error, so it's a floor).

**P3, the weaker pull** (`change`; team-efficiency#F16, the CEO's pick 2026-11-13): on offense,
a team's prior is pull x (1 - a x new QB - b x new coach) x last season's final, with each flag
of `changes.season_changes` counted only once it is known (each has its own known-at).
a = b = 0.25 on offense, none on defense, as round two tuned them on 2007-2015.

Settings are the exploration's, tuned on 2007-2015 (team-efficiency#F8, explore/*.txt). Final
ratings are cached by the content of the rows they're fit on, so a perturbed world (leakage checks
3 and 4) recomputes them.
"""

from __future__ import annotations

import hashlib
import zlib
from dataclasses import dataclass

import numpy as np
import polars as pl

c = pl.col
# DML's situation cells in `team_game.efficiency` (win-chance band x half). Experts read data
# only through the gateway (leakage check 1), so the count is repeated here; a test keeps the two
# equal.
BINS = 14
ALPHA = 50.0  # propensity smoothing, in plays (exploration)


@dataclass(frozen=True)
class Settings:
    half_life: float  # weeks; 1000 is no recency
    lam: float  # games' worth of W
    pull: float  # share of last season's final rating kept


@dataclass(frozen=True)
class Measure:
    name: str
    kind: str  # "ridge" or "dml"
    w: str  # ridge: the weight column; dml: the cell prefix of plays (eff_n)
    wy: str  # ridge: the weighted-sum column; dml: the cell prefix of leftovers
    scale: float  # mean W per team-game, 2006-2015: lam is in these units
    off: Settings
    defn: Settings
    change: tuple[float, float] = (0.0, 0.0)  # offense's pull cut for a new QB, a new coach (P3)


_EQUAL = Settings(16.0, 5.0, 0.7)  # all plays, equal (exploration rung 1; also DML)
MEASURES: dict[str, Measure] = {
    m.name: m
    for m in (
        Measure(
            "usual",
            "ridge",
            "eff_usual_plays",
            "eff_usual_epa",
            42.9,
            Settings(16.0, 10.0, 0.5),
            Settings(16.0, 10.0, 0.5),
        ),
        Measure("ridge", "ridge", "eff_plays", "eff_epa", 62.6, _EQUAL, _EQUAL),
        Measure("change", "ridge", "eff_plays", "eff_epa", 62.6, _EQUAL, _EQUAL, (0.25, 0.25)),
        Measure("dml", "dml", "eff_n", "eff_r", 62.6, _EQUAL, _EQUAL),
        Measure("combo", "dml", "eff_n", "eff_rwo", 62.6, _EQUAL, Settings(1000.0, 10.0, 0.5)),
        Measure("pass", "ridge", "eff_pass_plays", "eff_pass_epa", 36.1, _EQUAL, _EQUAL),
        Measure("run", "ridge", "eff_run_plays", "eff_run_epa", 26.5, _EQUAL, _EQUAL),
        Measure("ssr", "ridge", "eff_series", "eff_series_success", 27.6, _EQUAL, _EQUAL),
    )  # fmt: skip
}
# The combination's defense uses the defense's weights (team-efficiency#F8)
DEF_CELLS = {"combo": "eff_rwd"}
EPA_VARIANCE = 1.93  # per play, 2006-2015: the sd's scale for EPA measures
SSR_VARIANCE = 0.25  # a series' success is 0/1


def fold(game_id: pl.Expr) -> pl.Expr:
    """DML's cross-fitting half for a game: a fixed checksum of its id, 0 or 1."""
    return game_id.map_elements(lambda g: zlib.crc32(g.encode()) % 2, return_dtype=pl.Int8)


def teams(tg: pl.DataFrame) -> list[str]:
    """Every team on the schedule, sorted: the ratings' index. A team with no games in a season
    is rated by its prior alone and left out of the season's centring, so extra teams change
    nothing."""
    return sorted(set(tg["team"].unique().to_list()) | set(tg["opponent"].unique().to_list()))


def prepare(tg: pl.DataFrame, names: list[str]) -> pl.DataFrame:
    """Regular-season team-game rows (schedule + efficiency, offense view) → the walk's inputs:
    season, week, a (offense index into `names`), b (defense index), home, fold, known_at and
    the measures' columns."""
    tix = {t: i for i, t in enumerate(names)}
    cells = [f"{p}_{k}" for p in ("eff_n", "eff_r", "eff_rwo", "eff_rwd") for k in range(BINS)]
    cols = {m.w for m in MEASURES.values() if m.kind == "ridge"}
    cols |= {m.wy for m in MEASURES.values() if m.kind == "ridge"}
    x = tg.filter((c("game_type") == "REG") & c("efficiency_known_at").is_not_null())
    return x.select(
        "game_id",
        c("season").cast(pl.Int32),
        c("week").cast(pl.Int32),
        c("team").replace_strict(tix, return_dtype=pl.Int32).alias("a"),
        c("opponent").replace_strict(tix, return_dtype=pl.Int32).alias("b"),
        c("home").cast(pl.Float64),
        fold(c("game_id")).alias("fold"),
        c("efficiency_known_at").alias("known_at"),
        *[c(k).cast(pl.Float64) for k in sorted(cols) + cells],
    ).sort("season", "week", "game_id", "a")


def _ridge_fit(
    rows: np.ndarray, ref_week: float, po: np.ndarray, pd_: np.ndarray, s: Settings,
    scale: float, variance: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:  # fmt: skip
    """rows: week, a, b, home, W, WY. Offense and defense ratings and their sds."""
    lam = s.lam * scale
    nt = len(po)
    if rows.shape[0] == 0:
        sd = np.full(nt, np.sqrt(variance / lam))
        return po.copy(), pd_.copy(), sd, sd.copy()
    wk, a, b, h, w, wy = (rows[:, i] for i in range(6))
    r = 0.5 ** ((ref_week - wk) / s.half_life)
    n = rows.shape[0]
    x = np.zeros((n, 2 + 2 * nt))
    x[:, 0] = 1.0
    x[:, 1] = h
    x[np.arange(n), 2 + a.astype(int)] = 1.0
    x[np.arange(n), 2 + nt + b.astype(int)] = 1.0
    om = r * w
    ybar = np.where(w > 0, wy / np.where(w > 0, w, 1), 0.0)
    m = x.T @ (x * om[:, None])
    rhs = x.T @ (om * ybar)
    pen = np.full(2 + 2 * nt, lam)
    pen[:2] = 1e-6
    m[np.diag_indices_from(m)] += pen
    rhs[2 : 2 + nt] += lam * po
    rhs[2 + nt :] += lam * pd_
    th = np.linalg.solve(m, rhs)
    var = variance * np.diag(np.linalg.inv(m))
    return th[2 : 2 + nt], th[2 + nt :], np.sqrt(var[2 : 2 + nt]), np.sqrt(var[2 + nt :])


def _add(v: np.ndarray, idx: np.ndarray, w: np.ndarray) -> None:
    np.add.at(v, idx, w)


def _dml_fit(
    rows: np.ndarray, ref_week: float, po: np.ndarray, pd_: np.ndarray, s: Settings,
    scale: float, variance: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:  # fmt: skip
    """rows: week, a, b, home, fold, bin, n, sy (one per offense, game and bin with plays).
    Robinson's regression with cross-fitted propensities, ridge toward the prior."""
    nt = len(po)
    nd = 2 * nt + 1
    lam = s.lam * scale
    if rows.shape[0] == 0:
        sd = np.full(nt, np.sqrt(variance / lam))
        return po.copy(), pd_.copy(), sd, sd.copy()
    wk, a, b, h, fo, bn, n, sy = (rows[:, i] for i in range(8))
    a, b, fo, bn = a.astype(int), b.astype(int), fo.astype(int), bn.astype(int)
    r = 0.5 ** ((ref_week - wk) / s.half_life)
    m = n * r
    q = sy * r
    big_a = np.zeros((nd, nd))
    rhs = np.zeros(nd)

    def shares(sel: np.ndarray) -> tuple[np.ndarray, float]:
        v = np.zeros(nd)
        _add(v, a[sel], m[sel])
        _add(v, nt + b[sel], m[sel])
        v[2 * nt] = (m[sel] * h[sel]).sum()
        return v, float(m[sel].sum())

    for f in (0, 1):
        mine = fo == f
        other = ~mine
        v_all, m_all = shares(other)
        e_bar = v_all / m_all if m_all > 0 else np.zeros(nd)
        for k in range(BINS):
            s_k = mine & (bn == k)
            if not s_k.any():
                continue
            v_o, m_o = shares(other & (bn == k))
            e = (v_o + ALPHA * e_bar) / (m_o + ALPHA)
            ms, qs, as_, bs, hs = m[s_k], q[s_k], a[s_k], b[s_k], h[s_k]
            v, mm = shares(s_k)
            qm = np.zeros((nd, nd))
            ib = nt + bs
            ih = np.full(len(ms), 2 * nt)
            for i1, i2, wv in (
                (as_, as_, ms), (ib, ib, ms), (as_, ib, ms), (ib, as_, ms), (as_, ih, ms * hs),
                (ih, as_, ms * hs), (ib, ih, ms * hs), (ih, ib, ms * hs), (ih, ih, ms * hs),
            ):  # fmt: skip
                np.add.at(qm, (i1, i2), wv)
            big_a += qm - np.outer(v, e) - np.outer(e, v) + mm * np.outer(e, e)
            qd = np.zeros(nd)
            _add(qd, as_, qs)
            _add(qd, nt + bs, qs)
            qd[2 * nt] = (qs * hs).sum()
            rhs += qd - e * qs.sum()
    pen = np.full(nd, lam)
    pen[2 * nt] = 1e-6
    big_a[np.diag_indices_from(big_a)] += pen
    rhs[:nt] += lam * po
    rhs[nt : 2 * nt] += lam * pd_
    th = np.linalg.solve(big_a, rhs)
    var = variance * np.diag(np.linalg.inv(big_a))
    return th[:nt], th[nt : 2 * nt], np.sqrt(var[:nt]), np.sqrt(var[nt : 2 * nt])


def _rows(x: pl.DataFrame, m: Measure, side: str) -> np.ndarray:
    """The walk's rows for one measure and side's settings."""
    if m.kind == "ridge":
        return x.select("week", "a", "b", "home", m.w, m.wy).to_numpy().astype(float)
    wy = DEF_CELLS.get(m.name, m.wy) if side == "def" else m.wy
    long = pl.concat(
        x.select(
            "week", "a", "b", "home", "fold", bin=pl.lit(k), n=c(f"{m.w}_{k}"), sy=c(f"{wy}_{k}")
        )  # fmt: skip
        for k in range(BINS)
    ).filter(c("n") > 0)
    return long.to_numpy().astype(float)


def _variance(m: Measure) -> float:
    return SSR_VARIANCE if m.name == "ssr" else EPA_VARIANCE


def _fit(m: Measure, rows: np.ndarray, ref_week: float, po, pd_, s: Settings):
    fit = _ridge_fit if m.kind == "ridge" else _dml_fit
    return fit(rows, ref_week, po, pd_, s, m.scale, _variance(m))


_FINALS: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
_MAX_FINALS = 20_000


def _digest(rows: np.ndarray) -> str:
    return hashlib.blake2b(np.ascontiguousarray(rows).tobytes(), digest_size=16).hexdigest()


class Walk:
    """One measure's ratings for one side's settings, from prepared rows (`prepare`) as known at
    each request's moment."""

    def __init__(self, x: pl.DataFrame, m: Measure, side: str, nt: int, changes: Changes = None):
        self.m, self.side, self.nt = m, side, nt
        self.s = m.off if side == "off" else m.defn
        cut = m.change if side == "off" else (0.0, 0.0)
        self.changes = changes if any(cut) else None
        self.cut = cut
        self.seasons = sorted(x["season"].unique().to_list())
        self.by_season = {
            k[0]: (g["known_at"].to_numpy(), _rows(g, m, side) if g.height else np.zeros((0, 8)),
                   _rows_known(g, m))
            for k, g in x.partition_by("season", as_dict=True).items()
        }  # fmt: skip

    def _season_rows(self, season: int, moment) -> np.ndarray:
        known, rows, idx = self.by_season[season]
        ok = known <= np.datetime64(moment.replace(tzinfo=None), "us")
        return rows[ok[idx]]

    def prior(self, season: int, moment) -> tuple[np.ndarray, np.ndarray]:
        """This season's prior: the walk of every earlier season's final rating, from the rows
        known at `moment`."""
        po, pd_ = np.zeros(self.nt), np.zeros(self.nt)
        chain = (self.m.name, self.side, self.s, self.nt)
        for s in self.seasons:
            if s >= season:
                break
            rows = self._season_rows(s, moment)
            chain = (*chain, s, _digest(rows))
            hit = _FINALS.get(chain)
            if hit is None:
                last = rows[:, 0].max() + 1 if rows.shape[0] else 1.0
                o, d, _, _ = _fit(self.m, rows, last, po, pd_, self.s)
                hit = (_centred(o, rows, self.s.pull), _centred(d, rows, self.s.pull))
                if len(_FINALS) > _MAX_FINALS:
                    _FINALS.clear()
                _FINALS[chain] = hit
            po, pd_ = hit
            f = self._factor(s + 1, moment)
            if f is not None:
                po = po * f
                chain = (*chain, "change", f.tobytes())
        return po, pd_

    def _factor(self, season: int, moment) -> np.ndarray | None:
        """Each team's share of the pull kept for `season` (P3), from the flags known at `moment`;
        None when this measure has no change."""
        if self.changes is None or season not in self.changes:
            return None
        known_qb, known_coach, qb, coach = self.changes[season]
        at = np.datetime64(moment.replace(tzinfo=None), "us")
        a, b = self.cut
        q = np.where(known_qb <= at, qb, 0.0)  # NaT (never known) compares False
        k = np.where(known_coach <= at, coach, 0.0)
        return np.clip(1 - a * q - b * k, 0.0, 1.0)

    def at(self, season: int, week: int, moment) -> tuple[np.ndarray, ...]:
        """Ratings (o, d, o_sd, d_sd) before `week` of `season` from the rows known at `moment`:
        that season's games of earlier weeks, and of this week if already played."""
        po, pd_ = self.prior(season, moment)
        if season not in self.by_season:
            sd = np.full(self.nt, np.sqrt(_variance(self.m) / (self.s.lam * self.m.scale)))
            return po, pd_, sd, sd.copy()
        rows = self._season_rows(season, moment)
        rows = rows[rows[:, 0] <= week]
        return _fit(self.m, rows, float(week), po, pd_, self.s)


# P3's flags per season: (QB known at, coach known at, new QB, new coach), arrays over the teams
Changes = dict[int, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] | None


def change_arrays(ch: pl.DataFrame, team_names: list[str]) -> dict:
    """`changes.season_changes` rows → `Changes` over `team_names` (no row: no change; a null
    known-at: that flag is never counted)."""
    out = {}
    tix = {t: i for i, t in enumerate(team_names)}

    def at(k) -> np.datetime64:
        return np.datetime64(k.replace(tzinfo=None), "us") if k else np.datetime64("NaT", "us")

    for (season,), g in ch.partition_by("season", as_dict=True).items():
        n = len(team_names)
        known_qb = np.full(n, np.datetime64("1900-01-01", "us"))
        known_coach = known_qb.copy()
        qb, coach = np.zeros(n), np.zeros(n)
        for r in g.iter_rows(named=True):
            i = tix.get(r["team"])
            if i is None:
                continue
            known_qb[i], known_coach[i] = at(r["qb_known_at"]), at(r["coach_known_at"])
            qb[i], coach[i] = r["new_qb"], r["new_coach"]
        out[int(season)] = (known_qb, known_coach, qb, coach)
    return out


def _centred(r: np.ndarray, rows: np.ndarray, pull: float) -> np.ndarray:
    """Next season's prior: `pull` x the rating less the mean of the teams that played (a team
    with no games starts the next season at 0)."""
    played = np.zeros(len(r), bool)
    if rows.shape[0]:
        played[rows[:, 1].astype(int)] = True
        played[rows[:, 2].astype(int)] = True
    if not played.any():
        return np.zeros(len(r))
    return np.where(played, pull * (r - r[played].mean()), 0.0)


def _rows_known(g: pl.DataFrame, m: Measure) -> np.ndarray:
    """For each walk row, the index of its team-game in `g` (DML has one row per bin)."""
    if m.kind == "ridge":
        return np.arange(g.height)
    i = np.arange(g.height)
    n = np.column_stack([g[f"{m.w}_{k}"].to_numpy() for k in range(BINS)])
    return np.concatenate([i[n[:, k] > 0] for k in range(BINS)])


def ratings(
    x: pl.DataFrame,
    requests: pl.DataFrame,
    names: list[str],
    team_names: list[str],
    changes: Changes = None,
) -> pl.DataFrame:
    """Every team's ratings for each request (season, week, moment): one row per request and
    team, with `<name>_o`, `<name>_d`, `<name>_o_sd`, `<name>_d_sd` for each measure in `names`
    (offense from the offense's settings, defense from the defense's). `x` is `prepare`d with
    the same `team_names`."""
    nt = len(team_names)
    walks = {
        (n, side): Walk(x, MEASURES[n], side, nt, changes) for n in names for side in ("off", "def")
    }
    out = []
    for req in requests.unique().sort("moment", "season", "week").iter_rows(named=True):
        cols: dict[str, object] = {"team": team_names}
        for n in names:
            o, _, o_sd, _ = walks[(n, "off")].at(req["season"], req["week"], req["moment"])
            _, d, _, d_sd = walks[(n, "def")].at(req["season"], req["week"], req["moment"])
            cols |= {f"{n}_o": o, f"{n}_d": d, f"{n}_o_sd": o_sd, f"{n}_d_sd": d_sd}
        out.append(
            pl.DataFrame(cols).with_columns(
                season=pl.lit(req["season"], pl.Int32),
                week=pl.lit(req["week"], pl.Int32),
                moment=pl.lit(req["moment"]).cast(pl.Datetime("us", "UTC")),
            )
        )
    return pl.concat(out)
