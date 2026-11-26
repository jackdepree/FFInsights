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
  and the **change in team part**: the shrunk centred rate last season of the team he joins'
  other players in his group, less his old team's (him left out). It is zero for a stayer, whose
  own rate already holds his team's part. A player-owned trait puts its weight on his own M1; a
  team-owned one moves with the change of team. (As first built, `split0`, the team part was
  the next team's level for everyone, stayers included: decision 0051, call 22.)
- **Beside the ladder, `flat`:** one slope on the raw rate (no chances): does a player's number
  of chances matter beyond one pull per trait?

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
# The line's pressure over expected: a team row keyed by the team (`gsis_id` = team); "QB" is
# only the placeholder group its team rows are read under.
LINE = Trait("line_poe", "the line's pressure over expected", ("QB",), "line_poe", 1, "dropback")
BY_NAME = {t.name: t for t in (*TRAITS, *EXTRA, LINE)}

# Rung 2, the shrink (decision 0051 call 30). "m1" (ships): each player pulled toward his
# position by his own reliability n / (n + k), with his own interval. "flat" (the revert): one
# pull per trait, the same slope for every player, fit on earlier season pairs, and no
# per-player interval. They tie for 14 of 15 trait-groups (F111); rule k's exception is
# recorded in the decision.
SHRINK = "m1"

# The role table's off-ball fine roles (roles-archetypes, I113): an OLB player-season in one of
# them counts as an inside linebacker (the CEO, 2026-11-26: "Yes we can count those linebackers
# as middle/inside linebackers"; decision 0051 call 31).
OFF_BALL = ("box linebacker", "base defensive back")


def regroup(teams: pl.DataFrame, roles: pl.DataFrame) -> pl.DataFrame:
    """Main teams and positions with 4-3 off-ball outside linebackers moved to ILB, by rule:
    roster or on-field position OLB and the role table's fine role that season off-ball. The
    old label is kept as `roster_position`. Seasons with no role row keep OLB."""
    r = roles.select(pid="gsis_id", season="season", role="role")
    t = teams.join(r, on=["pid", "season"], how="left")
    off = (c("position") == "OLB") & c("role").is_in(OFF_BALL)
    return t.with_columns(
        roster_position=c("position"),
        position=pl.when(off).then(pl.lit("ILB")).otherwise(c("position")),
    ).drop("role")


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
        f = (
            games.filter(c("trait") == trait.floor_trait)
            .group_by("gsis_id", "season")
            .agg(volume=c(col).sum())
        )
        s = s.join(f, on=["gsis_id", "season"], how="left")
    t = teams.select(gsis_id="pid", season="season", team="team",
                     group=c("position").replace_strict(GROUPS, default=None))  # fmt: skip
    s = s.join(t, on=["gsis_id", "season"], how="inner")
    s = s.filter(
        c("group").is_in(trait.groups)
        & (c("volume") >= trait.floor)
        & (c("den") >= max(trait.side_floor, 1e-9))
        & (c("season") >= trait.first)
    )
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
def pairs(rows: pl.DataFrame, games: pl.DataFrame,
          k_rows: pl.DataFrame | None = None) -> pl.DataFrame:  # fmt: skip
    """Every season pair (input season s, target s + 1), with k fit on seasons up to s.

    `k_rows`: the rows k (and k_team) are fit on, if not `rows`: all the trait's groups, so a
    trait has one k (the brief's "one stabilization constant per trait"; I172 tied, rule k).

    Columns: gsis_id, season (input), group, team, team_next, moved, x and n (his centred rate
    and chances), y and w (next season's centred rate and chances), k, k_team, sigma2, tau2,
    and the team part's raw pieces: tp_x, tp_n (his next team's other players in his group
    this season) and tpo_x, tpo_n (his own team's, him left out; the same for a stayer)."""
    seasons = sorted(rows["season"].unique().to_list())
    parts = team_parts(rows)
    trait = BY_NAME[rows["trait"][0]]
    nxt = rows.select("gsis_id", season=c("season") - 1, y=c("x"), w=c("den"),
                      team_next=c("team"))  # fmt: skip
    out = []
    k_rows = rows if k_rows is None else k_rows
    for s in seasons[:-1]:
        tr = k_rows.filter(c("season") <= s)
        sigma2, tau2 = components(tr, game_rows(games, tr, trait))
        k_team = sigma2 / team_components(tr, sigma2)
        a = rows.filter(c("season") == s).join(nxt, on=["gsis_id", "season"], how="inner")
        if a.height == 0:
            continue
        a = a.join(parts.rename({"team": "team_next"}), on=["team_next", "group", "season"],
                   how="left").with_columns(c("t_num", "t_den").fill_null(0.0))  # fmt: skip
        own = pl.when(c("team_next") == c("team")).then(1.0).otherwise(0.0)
        a = a.with_columns(o_num=c("t_num") - own * c("num"), o_den=c("t_den") - own * c("den"))
        # his own team's other players in his group this season (him left out)
        a = a.drop("t_num", "t_den").join(parts, on=["team", "group", "season"], how="left")
        a = a.with_columns(q_num=c("t_num").fill_null(0.0) - c("num"),
                           q_den=c("t_den").fill_null(0.0) - c("den"))  # fmt: skip
        a = a.with_columns(
            tp_x=pl.when(c("o_den") > 0).then(c("o_num") / c("o_den") - c("mu")).otherwise(0.0),
            tp_n=c("o_den").clip(0, None),
            tpo_x=pl.when(c("q_den") > 0).then(c("q_num") / c("q_den") - c("mu")).otherwise(0.0),
            tpo_n=c("q_den").clip(0, None),
            k=pl.lit(sigma2 / tau2),
            k_team=pl.lit(k_team),
            sigma2=pl.lit(sigma2),
            tau2=pl.lit(tau2),
            n=c("den"),
            moved=(c("team_next") != c("team")),
        )
        out.append(a)
    if not out:
        raise ValueError(f"{trait.name}: no season pairs")
    return pl.concat(out, how="diagonal_relaxed")


def rungs(p: pl.DataFrame, shuffle: tuple[str, ...] = (), seed: int = 0) -> pl.DataFrame:
    """Each rung's forecast on `pairs`: `avg`, `raw`, `m1`, and the fitted ones (null where not
    yet fittable): `flat` (one slope on the raw rate, no chances), `pull` (2b), `split0` (3 as
    first built: his M1 and his next team's part) and `split` (3: his M1 and the **change** in
    team part, next team's less his old team's, which is zero for a stayer).
    `shuffle`: columns (inputs, or `team_change`) moved together to another player of the same
    season and group before the rungs are made (a shuffled copy, for the null tests)."""
    shrink = lambda x, n: c(n) / (c(n) + c("k_team")) * c(x)  # noqa: E731
    p = p.with_columns(team_new=shrink("tp_x", "tp_n"), team_old=shrink("tpo_x", "tpo_n"))
    p = p.with_columns(team_change=pl.when(c("moved")).then(c("team_new") - c("team_old"))
                       .otherwise(0.0))  # fmt: skip
    if shuffle:
        p = shuffled(p, shuffle, seed)
    p = p.with_columns(avg=pl.lit(0.0), raw=c("x"), m1=c("n") / (c("n") + c("k")) * c("x"))
    return fit_slopes(p)


def walk(rows: pl.DataFrame, games: pl.DataFrame, shuffle_seed: int | None = None,
         shuffle: tuple[str, ...] = ()) -> pl.DataFrame:  # fmt: skip
    """`pairs` then `rungs`: every season pair with each rung's walk-forward forecast."""
    return rungs(pairs(rows, games), shuffle, shuffle_seed or 0)


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
    """The fitted rungs, each target season's slopes fit on pairs with earlier targets only."""
    s = p["season"].to_numpy()
    y, w = p["y"].to_numpy(), p["w"].to_numpy()
    x, m1 = p["x"].to_numpy(), p["m1"].to_numpy()
    designs = {"flat": [x], "pull": [m1], "split0": [m1, p["team_new"].to_numpy()],
               "split": [m1, p["team_change"].to_numpy()]}  # fmt: skip
    fc = {k: np.full(p.height, np.nan) for k in designs}
    b_pull, b_own, b_team = (np.full(p.height, np.nan) for _ in range(3))
    for t in np.unique(s):
        tr, te = s < t, s == t
        if tr.sum() < 30:
            continue
        for k, cols in designs.items():
            X = np.column_stack(cols)
            b = _wls(X[tr], y[tr], w[tr])
            fc[k][te] = X[te] @ b
            if k == "pull":
                b_pull[te] = b[0]
            if k == "split":
                b_own[te], b_team[te] = b
    out = p.with_columns(**{k: pl.Series(v) for k, v in fc.items()}, b_pull=pl.Series(b_pull),
                         b_own=pl.Series(b_own), b_team=pl.Series(b_team))  # fmt: skip
    cols = [*designs, "b_pull", "b_own", "b_team"]
    return out.with_columns(c(cols).fill_nan(None))


BY_TRAIT = BY_NAME
