"""Do four more inputs earn a place (CEO question, 2026-11-05)? Age, how much a player's share
swings, game script, and teams resting starters in the season's last week. Discovery only: each is
offered to all three parts of `trees_top`, on the same rows, against `trees_top` as it is.
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/new_inputs.py

Everything goes through the gateway, so it's known at the prediction moment, except `close`: the
closing spread is known only at kickoff (validation-harness#F3), so a Saturday run can't use it. It
is here only as the most a pregame view of game script could add.
- age: at kickoff.
- swing: the standard deviation of the player's share over their last 8 active games.
- form: teams' point difference per game so far this season, this team's minus the opponent's, and
  its size. A stand-in for game script from earlier results.
- final: the last regular-season week, and that times the team's win rate so far. A stand-in for
  "has clinched": seeding isn't in our tables.
"""

import numpy as np
import polars as pl

from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.experts.participation.common import known_shares
from pcf.experts.participation.features import FEATURES, INPUTS
from pcf.experts.participation.twopart import FULL, TreesTop, calibrated
from pcf.validation import backtest, calibration, scores
from pcf.validation.compare import compare

c = pl.col
KEYS = ["gsis_id", "game_id"]
SEASONS = list(range(2016, 2025))
FORM = ["form", "form_size"]
FINAL = ["final_week", "final_wins"]
CLOSE = ["close", "close_size"]
OFFERS = {
    "as it is": [],
    "+ age": ["age"],
    "+ swing": ["swing"],
    "+ form": FORM,
    "+ final week": FINAL,
    "+ all four": ["age", "swing", *FORM, *FINAL],
    "+ closing spread (can't ship)": CLOSE,
}


def _teams(view, season: int) -> pl.DataFrame:
    """Each team's win rate and point difference per game, from the games known at this moment."""
    g = view.table("game", seasons=[season]).filter(c("game_type") == "REG")
    if "home_score" not in g.columns:
        return pl.DataFrame(schema={"team": pl.String, "win_rate": pl.Float64, "diff": pl.Float64})
    g = g.filter(c("home_score").is_not_null())
    sides = [
        g.select(team="home_team", margin=(c("home_score") - c("away_score")).cast(pl.Float64)),
        g.select(team="away_team", margin=(c("away_score") - c("home_score")).cast(pl.Float64)),
    ]
    won = c("margin").gt(0).cast(pl.Float64) + 0.5 * c("margin").eq(0).cast(pl.Float64)
    return pl.concat(sides).group_by("team").agg(win_rate=won.mean(), diff=c("margin").mean())


class Offered(TreesTop):
    """`trees_top`, with the candidates worked out from what's known at the prediction moment."""

    inputs = {**INPUTS, "game": ("schedule", "result")}

    def features(self, view, games):
        rows = super().features(view, games)
        season = int(games["season"].max())
        known = known_shares(view.table("player_game", seasons=[season - 1, season]))
        swing = known.filter(c("active")).group_by("gsis_id").agg(swing=c("share").tail(8).std())
        sched = view.table("game", seasons=[season])
        last = sched.filter(c("game_type") == "REG")["week"].max()
        this = sched.filter(c("game_id").is_in(games["game_id"].implode())).select(
            "game_id", "home_team", "away_team", "week", "game_type"
        )
        teams = _teams(view, season)
        them = c("away_team")
        rows = (
            rows.join(swing, on="gsis_id", how="left")
            .join(this, on="game_id", how="left")
            .with_columns(
                opponent=pl.when(c("team") == c("home_team")).then(them).otherwise(c("home_team"))
            )
            .join(teams, on="team", how="left")
            .join(teams.select(opponent="team", them_diff="diff"), on="opponent", how="left")
        )
        final = ((c("week") == last) & (c("game_type") == "REG")).cast(pl.Float64)
        form = c("diff").fill_null(0.0) - c("them_diff").fill_null(0.0)
        return rows.with_columns(
            swing=c("swing").fill_null(0.0).fill_nan(0.0),
            win_rate=c("win_rate").fill_null(0.5),
            form=form,
            form_size=form.abs(),
            final_week=final,
            final_wins=final * c("win_rate").fill_null(0.5),
        )


def option(extra: list[str]):
    class Option(Offered):
        columns = [*FEATURES, *extra]
        said: list[pl.DataFrame] = []

        def predict(self, model, rows):
            qb = rows.filter(c("position") == "QB")
            if qb.height and "QB" in model["parts"]:
                x = qb.select(self.columns).to_numpy().astype(float)
                t = model["parts"]["QB"][1].predict_proba(x)[:, 1]
                t = calibrated(model["calibrators"].get("QB"), t)
                self.said.append(qb.select(*KEYS).with_columns(t=pl.Series(t)))
            return super().predict(model, rows)

    return Option


def with_close(feats: pl.DataFrame) -> pl.DataFrame:
    """The closing spread for this player's team. Not known on Saturday."""
    g = load("game", parts=["pregame"], seasons=SEASONS).select(
        "game_id", "home_team", spread="spread_line"
    )
    home = feats.drop("home_team", strict=False).join(g, on="game_id", how="left")
    close = pl.when(c("team") == c("home_team")).then(c("spread")).otherwise(-c("spread"))
    return home.with_columns(close=close.fill_null(0.0), close_size=close.abs().fill_null(0.0))


def main() -> None:
    bt = backtest.run(Offered(), Gateway(), SEASONS, refit="season")
    feats = with_close(bt.features)
    print(f"Features: {feats.height:,} rows", flush=True)
    context = feats.select(
        *KEYS, "position", "depth1", "age", "swing", "form", "final_week", "win_rate", "close"
    )
    runs = {}
    for name, extra in OFFERS.items():
        e = option(extra)()
        pred = backtest.walk(e, feats, bt.targets, bt.steps, bt.test, bt.refit, bt.half_life)
        h = backtest.standard(e, pred).join(bt.targets.select(*KEYS, "y"), on=KEYS, how="left")
        h = scores.row_losses(h, e.kind).filter(c("y").is_not_null())
        runs[name] = (
            h.join(context, on=KEYS)
            .join(pl.concat(e.said), on=KEYS, how="left")
            .with_columns(step=c("game_id").str.slice(0, 7))
        )
        print(f"done: {name}", flush=True)

    last = (c("final_week") == 1) & (c("depth1") == 1)
    groups = {
        "all": c("y").is_not_null(),
        **{p: c("position") == p for p in ("QB", "RB", "WR", "TE")},
        "last week, starters": last,
        "last week, starters, 65%+ wins": last & (c("win_rate") >= 0.65),
    }
    print("\nPaired by week against `as it is`, pinball x100 (90% interval)")
    base = runs["as it is"]
    for k, v in runs.items():
        if k == "as it is":
            continue
        print(k)
        for g, e in groups.items():
            r = compare(v.filter(e), base.filter(e), KEYS, "step", (k, "as it is"))
            print(f"  {g:<32} {r.diff * 100:+.3f} ({r.lo * 100:+.3f} to {r.hi * 100:+.3f}): "
                  f"{r.verdict}, {r.rows:,} rows")  # fmt: skip

    rows = []
    for k, v in runs.items():
        on = v.filter((c("position") == "QB") & (c("y") > 0) & c("t").is_not_null())
        x = on.select(y=(c("y") >= FULL).cast(pl.Float64), mean="t")
        st = on.filter(c("depth1") == 1).select(y=(c("y") >= FULL).cast(pl.Float64), mean="t")
        one, two = calibration.probability_report(x), calibration.probability_report(st)
        rows.append({
            "offer": k, "QB MAE": (on["y"] - on["if_nonzero_mean"]).abs().mean() * 100,
            "error": one["error"], "slope": one["slope"], "starter slope": two["slope"],
        })  # fmt: skip
    print("\nChance of every snap, QB games played")
    with pl.Config(float_precision=3, tbl_width_chars=160, fmt_str_lengths=40):
        print(pl.DataFrame(rows))

    # Plain looks, from `as it is`: what do the groups do, and does the forecast already know?
    b = base.with_columns(
        wins=pl.when(c("win_rate") >= 0.65).then(pl.lit("65%+ wins"))
        .when(c("win_rate") >= 0.4).then(pl.lit("40-65%")).otherwise(pl.lit("under 40%")),
        age_band=pl.when(c("age") < 25).then(pl.lit("under 25"))
        .when(c("age") < 30).then(pl.lit("25-29"))
        .when(c("age") < 35).then(pl.lit("30-34")).otherwise(pl.lit("35+")),
        swing_band=pl.when(c("swing") < 0.05).then(pl.lit("a under 5"))
        .when(c("swing") < 0.1).then(pl.lit("b 5-10"))
        .when(c("swing") < 0.2).then(pl.lit("c 10-20")).otherwise(pl.lit("d 20+")),
        script=pl.when(c("close").abs() >= 10).then(pl.lit("spread 10+"))
        .when(c("close").abs() >= 4).then(pl.lit("spread 4-10"))
        .otherwise(pl.lit("spread under 4")),
    )  # fmt: skip
    look = dict(
        n=pl.len(),
        was=c("y").mean() * 100,
        said=c("mean").mean() * 100,
        zero=(c("y") == 0).mean() * 100,
        said_zero=(1 - c("p_nonzero")).mean() * 100,
        every=(c("y") >= FULL).mean() * 100,
        inside=((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean() * 100,
    )
    with pl.Config(float_precision=1, tbl_rows=40, tbl_width_chars=160):
        print("\nStarters by week type and team wins (y includes games at 0)")
        print(b.filter(c("depth1") == 1).group_by("position", "final_week", "wins").agg(**look)
              .sort("position", "final_week", "wins"))  # fmt: skip
        print("\nBy age, played recently or not, by position")
        print(b.group_by("position", "age_band").agg(**look).sort("position", "age_band"))
        print("\nBy swing, by position: are ranges right where shares swing?")
        print(b.group_by("position", "swing_band").agg(**look).sort("position", "swing_band"))
        print("\nQB starters by closing spread (can't be an input; shows what a known script does)")
        print(b.filter((c("position") == "QB") & (c("depth1") == 1)).group_by("script").agg(**look)
              .sort("script"))  # fmt: skip

    # After the game: how much does the actual score explain? Never an input.
    res = load("game", parts=["result"], seasons=SEASONS).select("game_id", "result")
    q = b.filter((c("position") == "QB") & (c("depth1") == 1) & (c("y") > 0)).join(
        res, on="game_id"
    )
    q = q.with_columns(m=c("result").abs()).with_columns(
        band=pl.when(c("m") >= 21).then(pl.lit("won or lost by 21+"))
        .when(c("m") >= 14).then(pl.lit("14-20")).otherwise(pl.lit("under 14"))
    )  # fmt: skip
    print("\nQB starters who played, by final margin (known only afterward)")
    with pl.Config(float_precision=1):
        print(q.group_by("band").agg(n=pl.len(), every=(c("y") >= FULL).mean() * 100,
                                     said=c("t").mean() * 100, share=c("y").mean() * 100)
              .sort("band"))  # fmt: skip
    print(f"Rows at the mean of swing: {float(np.round(b['swing'].mean(), 3))}")


if __name__ == "__main__":
    main()
