"""Environment's exploration: the shared game and team-game tables (discovery only; the 2025 vault is closed).

- `weather(kind)`: one row a game from the saved Open-Meteo JSON (`env_fetch_weather.py`): the mean of the three hours
  from kickoff (UTC) for temperature (°F), precipitation (inches an hour), wind and gusts (mph), and the elevation (m).
- `games()`: every regular-season game 1999-2024 with the eight conditions (dome games get calm, dry, 70°F weather).
- `team_games()`: per team-game (2000-2024: pace and efficiency start there), the outcomes, the conditions, the team's
  rest, home, the closing spread and total, and the team's and opponent's means of each outcome over their previous
  8 games (known before kickoff).
Cached under data/interim/environment/.
"""

# ruff: noqa: E501
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import read_part

c = pl.col
SEASONS = list(range(1999, 2025))
CACHE = get_config().zone("interim") / "environment"
OUTCOMES = ["plays", "tempo_seconds", "dropbacks", "proe", "runs", "epa_per_play", "yards_per_play", "sack_rate", "int_rate",
            "epa_sd", "points", "game_total", "home_margin", "fg_rate"]
LABEL = {"plays": "plays a game", "tempo_seconds": "seconds a play", "dropbacks": "dropbacks", "proe": "pass rate over expected",
         "runs": "runs", "epa_per_play": "EPA a play", "yards_per_play": "yards a play", "sack_rate": "sack rate",
         "int_rate": "interception rate", "epa_sd": "spread of play outcomes (SD of EPA)", "points": "points scored",
         "game_total": "game total points", "home_margin": "home margin", "fg_rate": "field goal make rate"}
COND = ["wind", "temp", "precip", "dome", "turf", "short_rest", "long_rest", "altitude", "primetime"]


class Say:
    def __init__(self, path: Path):
        self.path, self.lines = path, []

    def __call__(self, *lines: str) -> None:
        for s in lines:
            print(s, flush=True)
            self.lines.append(s)

    def save(self) -> None:
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def _part(name, part, cols=None, seasons=SEASONS):
    x = read_part(name, part, list(seasons), None).collect()
    return x if cols is None else x.select(cols)


def weather(kind: str = "archive") -> pl.DataFrame:
    d = get_config().zone("raw") / "open_meteo" / kind
    g = _part("game", "schedule", ["game_id", "kickoff"]).with_columns(k=c("kickoff").dt.replace_time_zone(None))
    k = dict(zip(g["game_id"], g["k"], strict=True))
    rows = []
    for f in d.glob("*.json"):
        j = json.loads(f.read_text(encoding="utf-8"))
        h = j.get("hourly")
        if not h:
            continue
        t = np.array(h["time"], dtype="datetime64[m]")
        k0 = np.datetime64(k[f.stem], "m")
        m = (t >= k0 - np.timedelta64(59, "m")) & (t < k0 + np.timedelta64(180, "m"))

        def mean(v, m=m, h=h):
            a = np.array([np.nan if x is None else x for x in h[v]], dtype=float)[m]
            return float(np.nanmean(a)) if np.isfinite(a).any() else None

        rows.append({"game_id": f.stem, "temp": mean("temperature_2m"), "precip": mean("precipitation"), "rain": mean("rain"),
                     "snow": mean("snowfall"), "wind": mean("wind_speed_10m"), "gust": mean("wind_gusts_10m"),
                     "elevation": j.get("elevation")})
    return pl.DataFrame(rows)


def games(kind: str = "archive") -> pl.DataFrame:
    p = CACHE / f"games_{kind}.parquet"
    if p.exists():
        return pl.read_parquet(p)
    s = _part("game", "schedule").filter(c("game_type") == "REG")
    r = _part("game", "result", ["game_id", "home_score", "away_score", "temp", "wind"]).rename({"temp": "temp_reading", "wind": "wind_reading"})
    w = weather(kind)
    et = c("kickoff").dt.convert_time_zone("America/New_York")
    g = (s.join(r, on="game_id", how="left").join(w, on="game_id", how="left")
         .with_columns(dome=c("roof").is_in(["dome", "closed"]).fill_null(False),
                       turf=~c("surface").str.strip_chars().is_in(["grass", "dessograss", ""]).fill_null(True),
                       primetime=(et.dt.hour() >= 19) | (c("weekday") != "Sunday"),
                       game_total=c("home_score") + c("away_score"), home_margin=c("home_score") - c("away_score")))
    g = g.with_columns(wind=pl.when(c("dome")).then(0.0).otherwise(c("wind")), temp=pl.when(c("dome")).then(70.0).otherwise(c("temp")),
                       precip=pl.when(c("dome")).then(0.0).otherwise(c("precip")),
                       altitude=pl.when(c("dome")).then(False).otherwise(c("elevation") > 1000).fill_null(False))
    CACHE.mkdir(parents=True, exist_ok=True)
    g.write_parquet(p)
    return g


def _fg() -> pl.DataFrame:
    x = _part("play", "pbp", ["game_id", "posteam", "season_type", "field_goal_attempt", "field_goal_result", "kick_distance"])
    x = x.filter((c("season_type") == "REG") & (c("field_goal_attempt") == 1))
    return x.group_by("game_id", team="posteam").agg(fg_att=pl.len(), fg_made=(c("field_goal_result") == "made").sum())


def kicks() -> pl.DataFrame:
    x = _part("play", "pbp", ["game_id", "season", "posteam", "season_type", "field_goal_attempt", "field_goal_result", "kick_distance"])
    return (x.filter((c("season_type") == "REG") & (c("field_goal_attempt") == 1) & c("kick_distance").is_not_null())
            .with_columns(made=(c("field_goal_result") == "made").cast(pl.Float64)).rename({"posteam": "team"}))


def team_games(kind: str = "archive") -> pl.DataFrame:
    p = CACHE / f"team_games_{kind}.parquet"
    if p.exists():
        return pl.read_parquet(p)
    S = list(range(2000, 2025))
    g = games(kind)
    ts = _part("team_game", "schedule", ["game_id", "team", "opponent", "home", "rest", "week"], S)
    pace = _part("team_game", "pace", ["game_id", "team", "plays", "dropbacks", "runs", "proe", "epa_per_play"], S)
    ten = _part("team_game", "tendencies", ["game_id", "team", "tempo_seconds", "neutral_pass_oe", "shotgun_rate"], S)
    st = _part("team_game", "stats", ["game_id", "team", "attempts", "passing_yards", "rushing_yards", "carries", "sacks_suffered", "sack_yards_lost", "passing_interceptions"], S)
    ef = _part("team_game", "efficiency", ["game_id", "team", "eff_plays", "eff_epa", "eff_epa_sq"], S)
    res = _part("team_game", "result", ["game_id", "team", "points_for"], S)
    pre = _part("team_game", "pregame", ["game_id", "team", "spread", "total_line"], S)
    t = (ts.join(g.select("game_id", "season", "kickoff", "home_team", "stadium_id", "roof", "game_total", "home_margin", *[x for x in COND if x not in ("short_rest", "long_rest")]), on="game_id", how="inner")
         .join(pace, on=["game_id", "team"], how="left").join(ten, on=["game_id", "team"], how="left").join(st, on=["game_id", "team"], how="left")
         .join(ef, on=["game_id", "team"], how="left").join(res, on=["game_id", "team"], how="left").join(pre, on=["game_id", "team"], how="left")
         .join(_fg(), on=["game_id", "team"], how="left"))
    t = t.with_columns(
        yards_per_play=(c("passing_yards") + c("rushing_yards") - c("sack_yards_lost").fill_null(0)) / (c("attempts") + c("sacks_suffered") + c("carries")),
        sack_rate=c("sacks_suffered") / (c("attempts") + c("sacks_suffered")),
        int_rate=c("passing_interceptions") / c("attempts"),
        epa_sd=((c("eff_epa_sq") / c("eff_plays")) - (c("eff_epa") / c("eff_plays")) ** 2).sqrt(),
        points=c("points_for"),
        fg_rate=pl.when(c("fg_att") >= 2).then(c("fg_made") / c("fg_att")),
        short_rest=c("rest") <= 5, long_rest=c("rest") >= 13,
    ).sort("team", "kickoff")
    team_out = [o for o in OUTCOMES if o not in ("game_total", "home_margin")]
    # the team's and the opponent's means over their previous 8 games (known before kickoff)
    t = t.with_columns([c(o).shift(1).rolling_mean(8, min_samples=3).over("team").alias(f"{o}_prior") for o in team_out])
    opp = t.select("game_id", c("team").alias("opponent"), *[c(f"{o}_prior").alias(f"{o}_opp") for o in team_out])
    t = t.join(opp, on=["game_id", "opponent"], how="left")
    t.write_parquet(p)
    return t
