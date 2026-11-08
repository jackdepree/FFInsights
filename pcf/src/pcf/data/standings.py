"""Standings, playoff seeds and seed locks from regular-season results (I19; the CEO, 2026-11-07:
"seed locked").

- **Seeds** follow the NFL's tiebreakers: division winners first (division tiebreakers), seeded
  above the wild cards (conference tiebreakers). From 2020, 7 seeds per conference (one bye);
  before, 6. Tiebreakers run through strength of schedule; ties the points-based steps would
  decide are `Unresolved`.
- **Seed locked:** before the final regular-season week, a team's seed is the same whatever that
  week's games do. Every outcome of the week's games involving the conference's teams is tried
  (wins and losses; ties ignored). A scenario left unresolved counts as "could differ", so a
  lock is never claimed on a guess. Other-conference results in the final week count as unplayed
  inside strength of victory and schedule, a rare and small approximation.
- **Eliminated:** out of the playoffs in every outcome.

Pure functions on results; models pass in the `game` table from their view, so the point-in-time
rule is the caller's: only results known by the moment.

Divisions are fixed since the 2002 realignment, with today's team codes (the tables rename
relocated teams: LV, LAC, LA).
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

import polars as pl

c = pl.col
DIVISIONS: dict[str, tuple[str, ...]] = {
    "AFC East": ("BUF", "MIA", "NE", "NYJ"),
    "AFC North": ("BAL", "CIN", "CLE", "PIT"),
    "AFC South": ("HOU", "IND", "JAX", "TEN"),
    "AFC West": ("DEN", "KC", "LAC", "LV"),
    "NFC East": ("DAL", "NYG", "PHI", "WAS"),
    "NFC North": ("CHI", "DET", "GB", "MIN"),
    "NFC South": ("ATL", "CAR", "NO", "TB"),
    "NFC West": ("ARI", "LA", "SEA", "SF"),
}
DIVISION = {t: d for d, teams in DIVISIONS.items() for t in teams}
CONFERENCE = {t: d[:3] for t, d in DIVISION.items()}
FIRST_SEASON = 2002
MAX_LOCK_GAMES = 12  # outcomes tried per conference: 2^12 at most


class Unresolved(Exception):  # noqa: N818
    """A tie that only the points-based steps (or a coin toss) would break."""


def playoff_spots(season: int) -> int:
    return 7 if season >= 2020 else 6


@dataclass(frozen=True)
class Game:
    home: str
    away: str
    home_result: float  # 1 home win, 0 away win, 0.5 tie


class Record:
    """Each team's games: (opponent, result 1/0.5/0)."""

    def __init__(self, games: Iterable[Game]):
        self.games: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for g in games:
            self.games[g.home].append((g.away, g.home_result))
            self.games[g.away].append((g.home, 1 - g.home_result))
        self._pct = {t: _pct(r for _, r in gs) for t, gs in self.games.items()}

    def pct(self, team: str) -> float:
        return self._pct.get(team, 0.0)

    def pct_vs(self, team: str, opponents: set[str]) -> float | None:
        rs = [r for o, r in self.games[team] if o in opponents]
        return _pct(rs) if rs else None

    def n_vs(self, team: str, opponents: set[str]) -> int:
        return sum(1 for o, _ in self.games[team] if o in opponents)

    def opponents(self, team: str) -> set[str]:
        return {o for o, _ in self.games[team]}

    def sov(self, team: str) -> float:
        beaten = [o for o, r in self.games[team] if r == 1]
        return self._combined(beaten)

    def sos(self, team: str) -> float:
        return self._combined([o for o, _ in self.games[team]])

    def _combined(self, teams: list[str]) -> float:
        won = sum(sum(r for _, r in self.games[t]) for t in teams)
        played = sum(len(self.games[t]) for t in teams)
        return won / played if played else 0.0


def _pct(results: Iterable[float]) -> float:
    rs = list(results)
    return round(sum(rs) / len(rs), 9) if rs else 0.0


def _top(teams: list[str], value) -> list[str]:
    vals = {t: value(t) for t in teams}
    if any(v is None for v in vals.values()):
        return teams  # the step doesn't apply
    best = max(vals.values())
    return [t for t in teams if round(vals[t], 9) == round(best, 9)]


def best(teams: list[str], rec: Record, kind: str) -> str:
    """The team that wins a tie among `teams` (same record): `kind` is "division" or
    "conference" (wild cards and seeding division winners)."""
    teams = sorted(teams)
    if len(teams) == 1:
        return teams[0]
    div = {t: set(DIVISIONS[DIVISION[t]]) - {t} for t in teams}
    conf = {t: {o for o in DIVISION if CONFERENCE[o] == CONFERENCE[t]} - {t} for t in teams}
    group = set(teams)

    def common(ts: list[str]) -> set[str]:
        return set.intersection(*[rec.opponents(t) for t in ts]) - set(ts)

    def h2h(t):
        return rec.pct_vs(t, group - {t})

    def sweep(ts):
        """Conference ties of 3+: only a team that beat, or lost to, each of the others."""
        for t in ts:
            others = set(ts) - {t}
            res = {o: [r for opp, r in rec.games[t] if opp == o] for o in others}
            if all(res[o] and all(r == 1 for r in res[o]) for o in others):
                return [t]

        def lost_to_all(t):
            for o in set(ts) - {t}:
                rs = [r for opp, r in rec.games[t] if opp == o]
                if not rs or any(r != 0 for r in rs):
                    return False
            return True

        losers = [t for t in ts if lost_to_all(t)]
        return [t for t in ts if t not in losers] if losers else ts

    if kind == "division":
        steps = [
            lambda ts: _top(ts, h2h),
            lambda ts: _top(ts, lambda t: rec.pct_vs(t, div[t])),
            lambda ts: _top(ts, lambda t, cm=common(ts): rec.pct_vs(t, cm)),  # noqa: B008
            lambda ts: _top(ts, lambda t: rec.pct_vs(t, conf[t])),
            lambda ts: _top(ts, rec.sov),
            lambda ts: _top(ts, rec.sos),
        ]
    else:

        def common4(ts):
            cm = common(ts)
            if any(rec.n_vs(t, cm) < 4 for t in ts):
                return ts
            return _top(ts, lambda t: rec.pct_vs(t, cm))

        def head(ts):
            if len(ts) == 2:
                played = rec.n_vs(ts[0], {ts[1]})
                return _top(ts, h2h) if played else ts
            return sweep(ts)

        steps = [
            head,
            lambda ts: _top(ts, lambda t: rec.pct_vs(t, conf[t])),
            common4,
            lambda ts: _top(ts, rec.sov),
            lambda ts: _top(ts, rec.sos),
        ]
    for step in steps:
        left = step(teams)
        if len(left) == 1:
            return left[0]
        if len(left) < len(teams):
            # two left: start over with the two-club steps; more: carry on with the rest
            if len(left) == 2:
                return best(left, rec, kind)
            teams, group = left, set(left)
    raise Unresolved(", ".join(teams))


def _order(teams: list[str], rec: Record, kind: str) -> list[str]:
    """Teams ranked by record, ties broken one place at a time (the procedure restarts after
    each place)."""
    out, left = [], list(teams)
    while left:
        top = max(rec.pct(t) for t in left)
        tied = [t for t in left if rec.pct(t) == top]
        first = best(tied, rec, kind)
        out.append(first)
        left.remove(first)
    return out


def conference_seeds(rec: Record, conf: str, season: int) -> dict[str, int]:
    """Seeds 1..n for one conference."""
    divs = [d for d in DIVISIONS if d.startswith(conf)]
    ranked = {d: _order(list(DIVISIONS[d]), rec, "division") for d in divs}
    winners = _order([ranked[d][0] for d in divs], rec, "conference")
    seeds = {t: i + 1 for i, t in enumerate(winners)}
    rest = {d: ranked[d][1:] for d in divs}
    while len(seeds) < playoff_spots(season):
        # only the highest-ranked remaining team of each division is considered at a time
        cands = [rest[d][0] for d in divs if rest[d]]
        top = max(rec.pct(t) for t in cands)
        first = best([t for t in cands if rec.pct(t) == top], rec, "conference")
        seeds[first] = len(seeds) + 1
        rest[DIVISION[first]].remove(first)
    return seeds


def seeds(games: Iterable[Game], season: int) -> dict[str, int]:
    """Every playoff team's seed (AFC and NFC each 1..n)."""
    rec = Record(games)
    return conference_seeds(rec, "AFC", season) | conference_seeds(rec, "NFC", season)


def locks(played: list[Game], remaining: list[Game], season: int) -> dict[str, dict]:
    """Per team: `seed` if it's the same in every outcome of `remaining` (else None), `locked`
    (in the playoffs with that seed fixed), `eliminated` (out in every outcome)."""
    out = {}
    for conf in ("AFC", "NFC"):
        mine = [g for g in remaining if CONFERENCE[g.home] == conf or CONFERENCE[g.away] == conf]
        teams = [t for t in DIVISION if CONFERENCE[t] == conf]
        seen: dict[str, set] = {t: set() for t in teams}
        if len(mine) > MAX_LOCK_GAMES:
            out |= {t: {"seed": None, "locked": False, "eliminated": False} for t in teams}
            continue
        for outcome in itertools.product((1.0, 0.0), repeat=len(mine)):
            world = played + [Game(g.home, g.away, r) for g, r in zip(mine, outcome, strict=True)]
            try:
                s = conference_seeds(Record(world), conf, season)
            except Unresolved:
                for t in teams:
                    seen[t].add("?")
                continue
            for t in teams:
                seen[t].add(s.get(t))
        for t in teams:
            only = next(iter(seen[t])) if len(seen[t]) == 1 else None
            out[t] = {
                "seed": only,
                "locked": only is not None,
                "eliminated": seen[t] == {None},
            }
    return out


def _games(frame: pl.DataFrame) -> list[Game]:
    m = c("home_score") - c("away_score")
    rows = frame.select(
        "home_team", "away_team",
        r=pl.when(m > 0).then(1.0).when(m < 0).then(0.0).otherwise(0.5),
    ).iter_rows()  # fmt: skip
    return [Game(h, a, r) for h, a, r in rows]


def final_week_locks(game: pl.DataFrame, season: int, moment) -> pl.DataFrame:
    """season, team, seed_locked, eliminated at `moment`, from a view of `game` (schedule and
    result). Empty unless the moment is in the final regular-season week, before any of its
    results (a game from an earlier week with no result, like 2022's cancelled BUF-CIN, counts as
    not played), and the teams are the NFL's."""
    schema = {"season": pl.Int32, "team": pl.String, "seed_locked": pl.Float64,
              "eliminated": pl.Float64}  # fmt: skip
    reg = game.filter((c("season") == season) & (c("game_type") == "REG"))
    if season < FIRST_SEASON or reg.is_empty():
        return pl.DataFrame(schema=schema)
    if not set(reg["home_team"]) | set(reg["away_team"]) <= set(DIVISION):
        return pl.DataFrame(schema=schema)  # not the NFL's 32 teams (a synthetic league)
    known = (
        c("result_known_at").is_not_null()
        & (c("result_known_at") <= moment)
        & c("home_score").is_not_null()
    )
    last = reg["week"].max()
    played = reg.filter(known)
    remaining = reg.filter((c("week") == last) & ~known)
    if remaining.is_empty() or reg.filter((c("week") == last) & known).height > 0:
        return pl.DataFrame(schema=schema)  # not before the final week
    lk = locks(_games(played), _games(remaining.with_columns(home_score=0, away_score=0)), season)
    return pl.DataFrame(
        [{"season": season, "team": t, "seed_locked": float(v["locked"]),
          "eliminated": float(v["eliminated"])} for t, v in sorted(lk.items())],
        schema=schema,
    )  # fmt: skip
