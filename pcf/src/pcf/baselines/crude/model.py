"""The crude forecaster (crude-forecaster brief): a deliberately simple forecast of yards that any
expert's saved output can be added to, so every expert, hunch and idea is scored the same way.

Variants are `<target>_<horizon>_<method>`:
- **targets:** `passing` (QBs), `rushing` (RBs), `receiving` (WRs, TEs, RBs), `team` (a team's
  yards gained; its opponent's yards allowed is the same forecast, `outputs.allowed`);
- **horizons:** `next` (the next game), `next3` (yards per game over the team's next 3 games),
  `rest` (per game over the rest of the regular season);
- **methods:** `season` (the season-so-far average), `lasso`, `trees`, `mix` (their average).

Rows: regular-season games. Players only when participation's saved chance of a snap is at least
50% (the CEO's call 3). Run: Saturday, the experts' moment, so every input is lined up to it.
An expert is added with `with_experts(cls, ("elo",))`: the same rows, more columns.
"""

from __future__ import annotations

from typing import Any, ClassVar

import polars as pl

from pcf.baselines.crude import features as F
from pcf.baselines.crude import fitting
from pcf.config import get_config
from pcf.core.contract import Expert

c = pl.col
HORIZONS = {"next": 1, "next3": 3, "rest": None}
PLAYER_POSITIONS = ("QB", "RB", "WR", "TE")
INPUTS: dict[str, Any] = {
    "player_game": ("roster", "stats", "snaps"),
    "team_game": ("schedule", "stats"),
    **F.EXPERT_INPUTS,
}
DEPTH_INPUTS: dict[str, Any] = {**INPUTS, "player_game": ("roster", "stats", "snaps", "depth")}


class Crude(Expert):
    """One target, horizon and rung; `added` names the expert groups added as inputs."""

    id = "crude-forecaster"
    cadence = "in_season"
    kind = "amount"
    run = "saturday"
    inputs = INPUTS
    first_train = 2016  # the experts' histories start in 2016 (the brief: fit from 2016)
    target_spec: ClassVar[F.Target]
    horizon: ClassVar[str] = "next"
    method: ClassVar[str] = "mix"
    added: ClassVar[tuple[str, ...]] = ()
    extra: ClassVar[tuple[str, ...]] = ()  # any other columns joined onto the features (a scorer's)
    keep: ClassVar[tuple[str, ...] | None] = None  # only these crude inputs (the hunch checks)
    seed: ClassVar[int | None] = None  # the trees' seed; config's when None
    row_rule: ClassVar[str] = "participation"  # which players are rows (ROW_RULES)
    baseline = True  # the base class isn't a model `find` returns

    # ------------------------------------------------------------ what it predicts
    @classmethod
    def players(cls) -> bool:
        return cls.target_spec.name != "team"

    @classmethod
    def dummies(cls) -> list[str]:
        positions = cls.target_spec.positions
        return [f"is_{p}" for p in positions[1:]] if len(positions) > 1 else []

    @classmethod
    def crude_columns(cls) -> list[str]:
        if cls.players():
            return [*F.CRUDE, *cls.dummies()]
        return [f"{side}_{k}" for side in ("off", "def") for k in F.CRUDE]

    @classmethod
    def expert_groups(cls) -> dict[str, list[str]]:
        return F.experts(cls.horizon, cls.players())

    @property
    def columns(self) -> list[str]:
        groups = self.expert_groups()
        unknown = set(self.added) - set(groups)
        if unknown:
            raise ValueError(f"{self.label()}: no expert group {sorted(unknown)}")
        added = [col for g in self.added for col in groups[g]]
        crude = [col for col in self.crude_columns() if self.keep is None or col in self.keep]
        return [*crude, *added, *self.extra]

    @property
    def by(self) -> tuple[str, ...]:
        return ("position",) if self.players() else ()

    # ------------------------------------------------------------ features
    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        season = int(games["season"].max())
        seasons = [season - 1, season]
        tg = view.table("team_game", seasons=seasons)
        sides = tg.filter(c("game_type") == "REG").select("game_id", "team", "opponent", "home")
        mine = sides.filter(c("game_id").is_in(games["game_id"].implode()))
        if self.players():
            rows = self._player_rows(view, seasons, season, mine, sides)
        else:
            rows = self._team_rows(tg, season, mine)
        if rows.is_empty():
            return rows
        team = F.team_expert_inputs(view, mine)
        rows = rows.join(team.drop("opponent", "home"), on=["game_id", "team"], how="left")
        return F.fill_missing(rows, F.columns(self.expert_groups()))

    def _player_rows(self, view, seasons, season, mine, sides) -> pl.DataFrame:
        spec = self.target_spec
        pg = view.table("player_game", seasons=seasons)
        rows = (
            pg.filter(
                c("game_id").is_in(mine["game_id"].implode())
                & c("position").is_in(list(spec.positions))
            )
            .select("gsis_id", "game_id", "season", "week", "team", "position")
            .join(mine.select("game_id", "team"), on=["game_id", "team"], how="inner")
        )
        rows = F.player_expert_inputs(view, rows)
        if self.row_rule == "depth":
            # the depth chart going into the game (known at the week's start): a starter or the
            # first backup at his listed position (I70), whatever participation expects
            depth = pg.filter(c("game_id").is_in(mine["game_id"].implode())).select(
                "gsis_id", "game_id", "depth"
            )
            rows = rows.join(depth, on=["gsis_id", "game_id"], how="inner").filter(
                c("depth") <= F.DEPTH_ROWS
            ).drop("depth")  # fmt: skip
        else:
            rows = rows.filter(c("part_play") >= F.EXPECTED_TO_PLAY)
        known = played_games(pg).join(sides.select("game_id", "team"), on=["game_id", "team"])
        crude = F.crude_inputs(F.unit_games(known, spec), "gsis_id", season)
        rows = F.with_crude(rows, crude, "gsis_id", "gsis_id")
        return rows.with_columns(
            (c("position") == p).cast(pl.Float64).alias(f"is_{p}") for p in spec.positions[1:]
        )

    def _team_rows(self, tg, season, mine) -> pl.DataFrame:
        stats = F.team_stats(tg.filter(c("game_type") == "REG"))
        off = F.crude_inputs(F.unit_games(stats, F.TEAM, "team"), "team", season)
        allowed = stats.with_columns(team=c("opponent"))  # what each defense allowed
        dfn = F.crude_inputs(F.unit_games(allowed, F.TEAM, "team"), "team", season)
        rows = mine.select("game_id", "team", "opponent").join(
            tg.select("game_id", "team", "season", "week"), on=["game_id", "team"]
        )
        rows = F.with_crude(rows, off, "team", "team", "off_")
        rows = F.with_crude(rows, dfn, "opponent", "team", "def_")
        return rows.drop("opponent")

    # ------------------------------------------------------------ outcomes
    def target(self, view) -> pl.DataFrame:
        tg = view.table("team_game")
        sched = tg.filter(c("game_type") == "REG").select("game_id", "team", "season", "week")
        windows = team_windows(sched, HORIZONS[self.horizon])
        if self.players():
            return self._player_target(view.table("player_game"), sched, windows)
        stats = F.team_stats(tg.filter(c("game_type") == "REG")).select(
            "game_id", "team", y="yards", known_at="known_at"
        )
        out = windows.join(
            stats.rename({"game_id": "w_game_id"}), on=["w_game_id", "team"], how="left"
        )
        return _window_mean(out, ["game_id", "team"])

    def _player_target(self, pg, sched, windows) -> pl.DataFrame:
        spec = self.target_spec
        game_known = pg.group_by("game_id").agg(
            known_at=pl.max_horizontal(c("stats_known_at").max(), c("snaps_known_at").max())
        )
        # his yards each week, on any team (a week with no row, or no stats, is 0)
        weekly = pg.group_by("gsis_id", "season", "week").agg(c(spec.yards).fill_null(0).sum())
        rows = pg.filter(c("position").is_in(list(spec.positions))).select(
            "gsis_id", "game_id", "team"
        ).join(sched.select("game_id", "team"), on=["game_id", "team"])  # fmt: skip
        out = (
            rows.join(windows, on=["game_id", "team"], how="inner")
            .join(game_known.rename({"game_id": "w_game_id"}), on="w_game_id", how="left")
            .join(
                weekly.rename({"season": "w_season", "week": "w_week", spec.yards: "y"}),
                on=["gsis_id", "w_season", "w_week"],
                how="left",
            )
            .with_columns(c("y").fill_null(0).cast(pl.Float64))
        )
        return _window_mean(out, ["gsis_id", "game_id"])

    # ------------------------------------------------------------ the model
    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        seed = get_config().seed if self.seed is None else self.seed
        season = "y_s" if self.players() else "off_y_s"  # rung 0: the season-so-far average
        return fitting.fit(self.method, train, self.columns, self.by, seed, season)

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = fitting.predict(model, rows, self.columns, self.by)
        return out.select(*self.keys(), "mean", "q10", "q50", "q90")

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {"method": model["method"], "alpha": model["alpha"]}
        if "lasso" in model:
            coef = model["lasso"]["coef"]
            out |= {
                f"lasso_{k}": round(float(v), 4) for k, v in zip(self.columns, coef, strict=True)
            }
        if "trees" in model:
            gain = model["trees"].get_booster().get_score(importance_type="gain")
            out |= {f"gain_{self.columns[int(k[1:])]}": round(v, 2) for k, v in gain.items()}
        return out

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        lower = fitting.METHODS[: fitting.METHODS.index(cls.method)]
        return [variant(cls.target_spec.name, cls.horizon, m, cls.row_rule) for m in lower]


def played_games(pg: pl.DataFrame) -> pl.DataFrame:
    """A view's player-games he played (a stats row, or an offensive snap), known by then."""
    return pg.filter(
        c("stats_known_at").is_not_null()
        | (c("snaps_known_at").is_not_null() & (c("offense_snaps").fill_null(0) > 0))
    )


def team_windows(sched: pl.DataFrame, k: int | None) -> pl.DataFrame:
    """For each regular-season team-game, the team's games in its window: this one and the next
    k - 1 (`k` None: the rest of the regular season). Only complete windows. Columns game_id,
    team, w_game_id, w_season, w_week, n (games in the window)."""
    s = sched.sort("team", "season", "week").with_columns(
        i=pl.int_range(pl.len()).over("team", "season"), left=pl.len().over("team", "season")
    )
    games = s.group_by("team", "season").agg(c("i"), w_game_id=c("game_id"), w_week=c("week"))
    out = (
        s.select("game_id", "team", "season", "i", "left")
        .join(games, on=["team", "season"], suffix="_w")
        .explode("i_w", "w_game_id", "w_week")
        .filter(c("i_w") >= c("i"))
    )
    if k is not None:
        out = out.filter((c("i_w") < c("i") + k) & (c("left") - c("i") >= k))
    out = out.with_columns(w_season=c("season"), n=pl.len().over("game_id", "team"))
    return out.select("game_id", "team", "w_game_id", "w_season", "w_week", "n")


def _window_mean(out: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    """Yards per game over each window, known when its last game is (a window with a game not
    yet known isn't an outcome yet)."""
    return (
        out.group_by(keys)
        .agg(
            y=c("y").mean(),
            known_at=c("known_at").max(),
            unknown=c("known_at").is_null().any() | c("y").is_null().any(),
        )
        .filter(~c("unknown"))
        .drop("unknown")
    )


# ---------------------------------------------------------------- the variants
TARGETS = {**F.PLAYER_TARGETS, "team": F.TEAM}
QUANTITIES = {
    "passing": "passing_yards",
    "rushing": "rushing_yards",
    "receiving": "receiving_yards",
    "team": "team_yards_gained",
    "qb_rushing": "qb_rushing_yards",
}
# Targets and row rules the yardstick can score on but doesn't publish (no champion, no history):
# QBs' rushing (I67); the depth chart's starters and first backups as rows (I70).
EXTRA_TARGETS = {"qb_rushing": F.QB_RUSHING}
ROW_RULES = ("participation", "depth")
VARIANTS: dict[str, type[Crude]] = {}
_EXTRA: dict[str, type[Crude]] = {}


def variant(
    target: str, horizon: str = "next", method: str = "mix", rows: str = "participation"
) -> type[Crude]:
    """The class for one target, horizon and rung: the module-level (published) one, or, for an
    extra target or another row rule, one made on first use and kept out of `find`."""
    if rows not in ROW_RULES:
        raise ValueError(f"no row rule {rows!r} (one of {ROW_RULES})")
    name = f"{target}_{horizon}_{method}"
    if rows == "participation" and name in VARIANTS:
        return VARIANTS[name]
    if target not in TARGETS and target not in EXTRA_TARGETS:
        raise KeyError(name)
    tag = name if rows == "participation" else f"{name}_{rows}rows"
    if tag not in _EXTRA:
        cls = _make(target, horizon, method, rows)
        _EXTRA[tag] = type(cls.__name__, (cls,), {"baseline": True, "__module__": __name__})
    return _EXTRA[tag]


def with_experts(
    cls: type[Crude],
    added: tuple[str, ...] = (),
    seed: int | None = None,
    extra: tuple[str, ...] = (),
    name: str = "",
    keep: tuple[str, ...] | None = None,
) -> type[Crude]:
    """The same forecaster with expert groups (and any `extra` columns) added as inputs, and a
    seed for the trees: same rows and features, so one feature history serves every combination."""
    tag = name or "+".join([*added, *extra])
    tag = f"{tag}-keep{len(keep)}" if keep is not None else tag
    attrs = {"added": tuple(added), "extra": tuple(extra), "seed": seed, "keep": keep,
             "variant": f"{cls.variant}+{tag}" if tag else cls.variant,
             "__module__": cls.__module__}  # fmt: skip
    return type(f"{cls.__name__}_{tag or 'crude'}_{seed}", (cls,), attrs)


def _make(target: str, horizon: str, method: str, rows: str = "participation") -> type[Crude]:
    spec = {**TARGETS, **EXTRA_TARGETS}[target]
    grain = "player_game" if target != "team" else "team_game"
    suffix = "" if horizon == "next" else f"_{horizon}"
    rule = "" if rows == "participation" else f"_{rows}rows"
    attrs = {
        "variant": f"{target}_{horizon}_{method}{rule}",
        "row_rule": rows,
        "inputs": INPUTS if rows == "participation" else DEPTH_INPUTS,
        "target_spec": spec,
        "horizon": horizon,
        "method": method,
        "grain": grain,
        "quantity": f"{QUANTITIES[target]}{suffix}",
        "groups": ("position",) if grain == "player_game" else (),
        "baseline": False,
        "__module__": __name__,
    }
    name = f"Crude_{target}_{horizon}_{method}"
    return type(name, (Crude,), attrs)


for _t in TARGETS:
    for _h in HORIZONS:
        for _m in fitting.METHODS:
            _cls = _make(_t, _h, _m)
            VARIANTS[_cls.variant] = _cls
            globals()[_cls.__name__] = _cls
