"""The traits and the ladder (skill-over-expected brief, "Goals for a build"; decision 0051).

Each trait is a rate (sum of `num` over sum of `den`) per player-season, for one position group,
with a volume floor. Every rate is read **centred**: less its group's mean that season (the
brief's "plain rates with each season's level taken out"; stabilization centres the same way).

The ladder, for next season's same rate (centred by next season's group mean):
- **0, the position's average:** 0.
- **1, the raw rate:** last season's centred rate (the no-noise target's base).
- **2, shrunk toward the position (M1):** n / (n + k) of the raw, one k per trait: k = sigma2 /
  tau2, the noise per chance over the true spread between players (stabilization's method 1,
  `components`), fit on seasons up to the input season only.
- **2b, the second pull (I156, stabilization's):** M1 times one slope fit on earlier season
  pairs (the drift between seasons a season's reliability can't see).
- **3, the owner's part split:** one fit, on earlier pairs, of next season's rate on his own M1
  and the **team part**: the shrunk centred rate last season of his next team's other players
  in his group (for a mover, the team he joins; for a stayer, his teammates). A player-owned
  trait puts its weight on his own M1; a team-owned one moves toward the team he plays for.

Fits are weighted by next season's chances, without an intercept (rates are centred).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

c = pl.col
GROUPS = {"DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "OLB": "OLB", "ILB": "ILB",
          "MLB": "ILB", "LB": "ILB", "CB": "DB", "FS": "DB", "SS": "DB", "S": "DB", "DB": "DB",
          "WR": "WR", "TE": "TE", "RB": "RB", "QB": "QB", "C": "OL", "LT": "OL", "RT": "OL",
          "LG": "OL", "RG": "OL", "G": "OL", "T": "OL", "OL": "OL"}  # fmt: skip


@dataclass(frozen=True)
class Trait:
    name: str
    label: str
    groups: tuple[str, ...]
    floor_trait: str  # the volume floor's trait: a rate's den, or a count's num
    floor: float
    unit: str  # what the rate is per
    first: int = 2016
    side_floor: float = 0.0  # a second floor on the trait's own den (rush share's 10)

    @property
    def floor_on_den(self) -> bool:
        return self.floor_trait == self.name


TRAITS = (
    Trait("press_rate", "pressures per dropback on the field", ("DL", "OLB", "ILB"),
          "on_dropbacks", 150, "dropback on the field", 2018),
    Trait("rush_share", "role: pressures / (pressures + coverage targets)", ("OLB", "ILB"),
          "on_dropbacks", 150, "pressure or target", 2018, 10),
    Trait("catch_rate", "plain catch rate (catches / targets)", ("WR",), "catch_rate", 40,
          "target"),
    Trait("qb_sack_rate", "sacks per dropback", ("QB",), "qb_sack_rate", 150, "dropback"),
    Trait("qb_depth", "throw depth (air yards per attempt)", ("QB",), "qb_sack_rate", 150,
          "attempt"),
    Trait("qb_ttt", "time to throw (seconds)", ("QB",), "qb_sack_rate", 150, "timed dropback"),
    Trait("rb_yac", "yards after contact per carry", ("RB",), "rb_carries", 80, "carry", 2018),
    Trait("rb_bt", "broken tackles per carry", ("RB",), "rb_carries", 80, "carry", 2018),
    Trait("rb_multi_after", "tackled after the line: share needing 2+ tacklers", ("RB",),
          "rb_carries", 80, "tackle after the line"),
    Trait("catch_allowed", "catch rate allowed", ("DB",), "catch_allowed", 30, "target", 2018),
    Trait("int_rate", "interceptions per target", ("DB",), "catch_allowed", 30, "target", 2018),
    Trait("depth_against", "throw depth against (air yards per target)", ("DB",),
          "catch_allowed", 30, "target", 2018),
)  # fmt: skip
# Targets and comparisons, not shipped traits (the brief's "ignore" column).
EXTRA = (
    Trait("def_sack_rate", "sacks per dropback on the field (the noisier outcome)",
          ("DL", "OLB", "ILB"), "on_dropbacks", 150, "dropback on the field", 2018),
    Trait("qb_press_rate", "pressures per dropback (a sack counted)", ("QB",), "qb_sack_rate",
          150, "dropback"),
    Trait("qb_sack_per_press", "sacks per pressure (a sack counted)", ("QB",), "qb_sack_rate",
          150, "pressure"),
    Trait("ol_press_rate", "his team's pressure on his dropbacks", ("OL",), "ol_press_rate",
          300, "dropback on the field"),
    Trait("ol_sack_rate", "his team's sacks on his dropbacks", ("OL",), "ol_press_rate", 300,
          "dropback on the field"),
)  # fmt: skip
BY_NAME = {t.name: t for t in TRAITS + EXTRA}


# ---------------------------------------------------------------- season rows
def season_rows(games: pl.DataFrame, teams: pl.DataFrame, trait: Trait) -> pl.DataFrame:
    """Per player-season (all his teams summed): num, den, n_games, the floor count, his main
    team and group, his rate and centred rate (less the group's mean that season, over the rows
    that pass the floor). Only rows that pass the floors."""
    g = games.filter(c("trait") == trait.name)
    s = g.group_by("gsis_id", "season").agg(c("num").sum(), c("den").sum(), n_games=pl.len())
    if trait.floor_on_den:
        s = s.with_columns(volume=c("den"))
    else:
        # a rate trait's chances (its den), or a count's total (on_dropbacks, rb_carries)
        col = "den" if trait.floor_trait in BY_NAME else "num"
        f = games.filter(c("trait") == trait.floor_trait).group_by("gsis_id", "season").agg(
            volume=c(col).sum()
        )
        s = s.join(f, on=["gsis_id", "season"], how="left")
    t = teams.select(gsis_id="pid", season="season", team="team",
                     group=c("position").replace_strict(GROUPS, default=None))  # fmt: skip
    s = s.join(t, on=["gsis_id", "season"], how="inner")
    s = s.filter(c("group").is_in(trait.groups) & (c("volume") >= trait.floor)
                 & (c("den") >= max(trait.side_floor, 1e-9)) & (c("season") >= trait.first))  # fmt: skip
    s = s.with_columns(rate=c("num") / c("den"))
    mu = (c("num").sum() / c("den").sum()).over("group", "season")
    return s.with_columns(mu=mu).with_columns(x=c("rate") - c("mu"), trait=pl.lit(trait.name))


def game_rows(games: pl.DataFrame, rows: pl.DataFrame, trait: Trait) -> pl.DataFrame:
    """His games of this trait, for the noise: num, den per game, with his season's rate."""
    g = games.filter((c("trait") == trait.name) & (c("den") > 0))
    return g.join(rows.select("gsis_id", "season", "rate", "n_games"), on=["gsis_id", "season"])


# ---------------------------------------------------------------- the noise and the true spread
def components(rows: pl.DataFrame, games: pl.DataFrame) -> tuple[float, float]:
    """(sigma2, tau2): the noise per chance (each player's games scattered around his season
    rate, `den`-weighted, per degree of freedom) and the true spread of centred season rates
    (their `den`-weighted variance less the average noise; stabilization's `components`)."""
    gg = games.filter(c("n_games") >= 2).with_columns(
        dev=c("den") * (c("num") / c("den") - c("rate")) ** 2
    )
    per = gg.group_by("gsis_id", "season").agg(ss=c("dev").sum(), G=c("n_games").first())
    sigma2 = float((per["ss"] / (per["G"] - 1)).mean())
    n, x = rows["den"].to_numpy(), rows["x"].to_numpy()
    w = n / n.sum()
    xm = float(np.sum(w * x))
    tau2 = float(np.sum(w * (x - xm) ** 2) - sigma2 * np.sum(w / n))
    return sigma2, max(tau2, 1e-12)


def team_parts(rows: pl.DataFrame) -> pl.DataFrame:
    """Per team, group and season: its players' summed num and den (to leave a player out)."""
    return rows.group_by("team", "group", "season").agg(t_num=c("num").sum(),
                                                        t_den=c("den").sum())  # fmt: skip


def team_components(rows: pl.DataFrame, sigma2: float) -> float:
    """The true spread of team-group-season centred rates (k for the team part = sigma2 / it)."""
    t = rows.group_by("team", "group", "season").agg(
        num=(c("num") - c("mu") * c("den")).sum(), den=c("den").sum()
    )
    n, x = t["den"].to_numpy(), (t["num"] / t["den"]).to_numpy()
    w = n / n.sum()
    xm = float(np.sum(w * x))
    tau2 = float(np.sum(w * (x - xm) ** 2) - sigma2 * np.sum(w / n))
    return max(tau2, 1e-12)


# ---------------------------------------------------------------- the walk
def walk(rows: pl.DataFrame, games: pl.DataFrame, shuffle_seed: int | None = None,
         shuffle: tuple[str, ...] = ()) -> pl.DataFrame:  # fmt: skip
    """Every season pair (input season s, target s + 1) with each rung's forecast, fit only on
    seasons up to s (k) and on pairs whose target is s or earlier (the slopes).

    Columns: gsis_id, season (input), group, team, team_next, moved, x, n (chances), y and w
    (next season's centred rate and chances), k, sigma2, tau2, m1, team_part, and the rungs
    `avg`, `raw`, `m1`, `pull` (2b) and `split` (3), null where not yet fittable.
    `shuffle`: columns of the input season moved together to another player of the same season
    and group (a shuffled copy, for the null tests)."""
    seasons = sorted(rows["season"].unique().to_list())
    parts = team_parts(rows)
    nxt = rows.select("gsis_id", season=c("season") - 1, y=c("x"), w=c("den"),
                      team_next=c("team"))  # fmt: skip
    pairs = []
    for s in seasons[:-1]:
        tr = rows.filter(c("season") <= s)
        sigma2, tau2 = components(tr, game_rows(games, tr, BY_TRAIT[rows["trait"][0]]))
        k = sigma2 / tau2
        k_team = sigma2 / team_components(tr, sigma2)
        a = rows.filter(c("season") == s).join(nxt, on=["gsis_id", "season"], how="inner")
        if a.height == 0:
            continue
        # the next team's other players in his group, last season (him left out)
        a = a.join(parts.rename({"team": "team_next"}), on=["team_next", "group", "season"],
                   how="left").with_columns(c("t_num", "t_den").fill_null(0.0))  # fmt: skip
        own = pl.when(c("team_next") == c("team")).then(1.0).otherwise(0.0)
        a = a.with_columns(o_num=c("t_num") - own * c("num"), o_den=c("t_den") - own * c("den"))
        a = a.with_columns(
            tp_x=pl.when(c("o_den") > 0).then(c("o_num") / c("o_den") - c("mu")).otherwise(0.0),
            tp_n=c("o_den").clip(0, None),
        )
        a = a.with_columns(
            k=pl.lit(k), k_team=pl.lit(k_team), sigma2=pl.lit(sigma2), tau2=pl.lit(tau2),
            n=c("den"), moved=(c("team_next") != c("team")),
        )
        pairs.append(a)
    p = pl.concat(pairs, how="diagonal_relaxed")
    if shuffle:
        p = shuffled(p, shuffle, shuffle_seed or 0)
    p = p.with_columns(
        avg=pl.lit(0.0), raw=c("x"), m1=c("n") / (c("n") + c("k")) * c("x"),
        team_part=c("tp_n") / (c("tp_n") + c("k_team")) * c("tp_x"),
    )
    return fit_slopes(p)


def shuffled(p: pl.DataFrame, cols: tuple[str, ...], seed: int) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    key = (p["season"].cast(pl.String) + p["group"]).to_numpy()
    order = np.arange(p.height)
    for kk in np.unique(key):
        idx = np.flatnonzero(key == kk)
        order[idx] = idx[rng.permutation(len(idx))]
    return p.with_columns(p.select(cols)[order])


def _wls(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    sw = np.sqrt(w)
    return np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]


def fit_slopes(p: pl.DataFrame) -> pl.DataFrame:
    """Rungs 2b and 3, each target season's slopes fit on pairs with earlier targets only."""
    s = p["season"].to_numpy()
    y, w = p["y"].to_numpy(), p["w"].to_numpy()
    m1, tp = p["m1"].to_numpy(), p["team_part"].to_numpy()
    pull, split = np.full(p.height, np.nan), np.full(p.height, np.nan)
    b_pull, b_own, b_team = (np.full(p.height, np.nan) for _ in range(3))
    for t in np.unique(s):
        tr, te = s < t, s == t
        if tr.sum() < 30:
            continue
        b = _wls(m1[tr, None], y[tr], w[tr])
        pull[te], b_pull[te] = b[0] * m1[te], b[0]
        b2 = _wls(np.column_stack([m1[tr], tp[tr]]), y[tr], w[tr])
        split[te] = b2[0] * m1[te] + b2[1] * tp[te]
        b_own[te], b_team[te] = b2
    out = p.with_columns(pull=pl.Series(pull), split=pl.Series(split), b_pull=pl.Series(b_pull),
                         b_own=pl.Series(b_own), b_team=pl.Series(b_team))  # fmt: skip
    return out.with_columns(c("pull", "split", "b_pull", "b_own", "b_team").fill_nan(None))


BY_TRAIT = BY_NAME
