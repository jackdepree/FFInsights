"""The rating walk (elo brief; exploration F2-F4): team ratings in points, folded over results
in the order they became known. Nothing here reads data; `features.py` feeds it.

- **Margin rating:** a team's strength in points against an average team on a neutral field.
  After each result both teams move by `k` times the miss on the home margin (rung 1, F2).
- **Offense and defense ratings:** points scored and allowed against the league average, each
  moved by `k_points` times the miss on that team's points (F4). They give the total.
- **Between seasons:** every rating is pulled toward 0, by `pull` (margin, F3) and `pull_points`.
  The pull happens once per season, before the season's first result or forecast.
- **Home field:** the mean home margin of the 3 seasons before, non-neutral games (F6). League
  points per team: last season's mean. Both known before the season starts.

The order is fixed (when the result became known, then kickoff, then game_id), so a walk over
the results known at any moment gives the same ratings whichever way it's computed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import polars as pl

c = pl.col


@dataclass(frozen=True)
class Settings:
    """Chosen on 2002-2015 in the exploration (F3, F4), fixed before the backtest. The margin pull
    is 0.4 since 2026-11-07 (the CEO's carryover question, decision 0021): Elo's end-of-season
    rating keeps 0.60-0.68 of itself into next season, and 0.4 ties 0.5 in the forecast test."""

    k: float = 0.06
    pull: float = 0.4
    k_points: float = 0.05
    pull_points: float = 1 / 3
    hfa_seasons: int = 3
    default_hfa: float = 2.5  # before any history (1999)
    default_points: float = 20.5  # per team, before any history


DEFAULT = Settings()


@dataclass
class SeasonPriors:
    """Known before each season: home field and league points per team."""

    hfa: dict[int, float]
    points: dict[int, float]


def season_priors(results: pl.DataFrame, settings: Settings | None = None) -> SeasonPriors:
    """From finished results (season, neutral, margin, total): each season's home field (mean home
    margin of the previous `hfa_seasons` seasons) and points per team (last season's mean)."""
    settings = settings or DEFAULT
    by = (
        results.group_by("season")
        .agg(
            margin_sum=c("margin").filter(~c("neutral")).sum(),
            home_games=(~c("neutral")).sum(),
            points=c("total").mean() / 2,
        )
        .sort("season")
    )
    rows = {r["season"]: r for r in by.iter_rows(named=True)}
    hfa, points = {}, {}
    seasons = sorted(rows)
    for s in range(min(seasons, default=0), max(seasons, default=-1) + 2):
        past = [rows[x] for x in range(s - settings.hfa_seasons, s) if x in rows]
        n = sum(r["home_games"] for r in past)
        hfa[s] = sum(r["margin_sum"] for r in past) / n if n else settings.default_hfa
        points[s] = rows[s - 1]["points"] if s - 1 in rows else settings.default_points
    return SeasonPriors(hfa, points)


@dataclass
class Walk:
    """Ratings so far. `add` folds in one result; `edges` gives a game's pre-game numbers."""

    priors: SeasonPriors
    settings: Settings = field(default_factory=Settings)
    season: int | None = None
    r: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    o: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    d: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def roll_to(self, season: int) -> None:
        """Pull every rating toward 0 once for each new season."""
        if self.season is None:
            self.season = season
            return
        while self.season < season:
            for t in self.r:
                self.r[t] *= 1 - self.settings.pull
            for t in self.o:
                self.o[t] *= 1 - self.settings.pull_points
                self.d[t] *= 1 - self.settings.pull_points
            self.season += 1

    def hfa(self, season: int, neutral: bool) -> float:
        if neutral:
            return 0.0
        return self.priors.hfa.get(season, self.settings.default_hfa)

    def edges(self, season: int, home: str, away: str, neutral: bool) -> dict[str, float]:
        """A game's pre-game numbers: the rating gap, home field, the offense/defense margin and
        total, and each team's own ratings (published for higher layers)."""
        self.roll_to(season)
        h = self.hfa(season, neutral)
        mu = self.priors.points.get(season, self.settings.default_points)
        ph = mu + self.o[home] - self.d[away] + h / 2
        pa = mu + self.o[away] - self.d[home] - h / 2
        return {
            "gap": self.r[home] - self.r[away],
            "hfa": h,
            "od_margin": ph - pa,
            "od_total": ph + pa,
            "home_rating": self.r[home],
            "away_rating": self.r[away],
            "home_offense": self.o[home],
            "home_defense": self.d[home],
            "away_offense": self.o[away],
            "away_defense": self.d[away],
        }

    def add(self, x: dict) -> None:
        """Fold in one result: season, home_team, away_team, neutral, home_pts, away_pts."""
        s, h, a = x["season"], x["home_team"], x["away_team"]
        e = self.edges(s, h, a, x["neutral"])
        miss = (x["home_pts"] - x["away_pts"]) - (e["gap"] + e["hfa"])
        self.r[h] += self.settings.k * miss
        self.r[a] -= self.settings.k * miss
        mu = self.priors.points.get(s, self.settings.default_points)
        eh = x["home_pts"] - (mu + self.o[h] - self.d[a] + e["hfa"] / 2)
        ea = x["away_pts"] - (mu + self.o[a] - self.d[h] - e["hfa"] / 2)
        kp = self.settings.k_points
        self.o[h] += kp * eh
        self.d[a] -= kp * eh
        self.o[a] += kp * ea
        self.d[h] -= kp * ea

    def ratings(self) -> pl.DataFrame:
        """Each team's current ratings: margin, offense, defense."""
        teams = sorted(set(self.r) | set(self.o))
        return pl.DataFrame(
            {
                "team": teams,
                "rating": [self.r[t] for t in teams],
                "offense": [self.o[t] for t in teams],
                "defense": [self.d[t] for t in teams],
            }
        )


def result_order(results: pl.DataFrame) -> pl.DataFrame:
    """Results in the walk's fixed order."""
    return results.sort("known_at", "kickoff", "game_id")
