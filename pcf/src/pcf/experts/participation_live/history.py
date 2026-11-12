"""History from the answer key of completed seasons (H32, H33, H35): what each player and team
did beyond the snap share, summed per season so a season's features use only earlier seasons.

Per player and season (part-timers: on some snaps but not every one):
- `res_<flag>`, `n_<flag>`: his on-field minus his snap share, summed over snaps with the flag,
  and the count (his own situational habits, H32);
- `stay_res`, `stay_n`: the same over snaps whose snap before (same drive) he was on (H35);
- `ret_res`, `ret_n`: over snaps whose snap before (same drive) he was off (H35);
- `cells`: all his part-time snaps.
Per team, side, position group and season: `tres_<flag>`, `tn_<flag>` (the team's habits, H33),
and the team's most common head coach that season.
Per pair of part-timers on the same team and season (`pair_sums`, H36, H37): over the snaps the
partner was on, how often the player was on too, and his expected rate there (his snap share).
`partner` turns them into `pn`: on a snap, the sum over his teammates named on it of how much
more (or less) often he was on with each of them than his share says (log-odds, shrunk by 50
snaps). A swap partner (RB1 and RB2) pushes him off; a package partner pulls him on.

`features(...)` turns them into a season's features, shrunk toward 0 by fixed prior counts
(the exploration's: 100 snaps for players, 300 for teams, 50 for stay and return).
"""

from __future__ import annotations

import polars as pl

from pcf.experts.participation_live.grid import FLAG_COLUMNS, FLAGS

c = pl.col
PLAYER_PRIOR = 100.0
TEAM_PRIOR = 300.0
RHYTHM_PRIOR = 50.0
PAIR_PRIOR = 50.0
PLAYER_COLUMNS = [f"ph_{k}" for k in FLAGS] + ["ph_n", "stay", "ret"]
TEAM_COLUMNS = [f"th_{k}" for k in FLAGS]


def season_sums(gt: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """One season's grid with truth (`with_truth`) → (player sums, team sums)."""
    pt = gt.filter(~c("full")).sort("game_id", "side", "gsis_id", "n")
    prev = c("on").shift(1).over("game_id", "side", "gsis_id")
    pt = pt.with_columns(res=c("on").cast(pl.Float64) - c("share"), prev_on=prev)
    stay = c("sd") & (c("prev_on") == 1)
    ret = c("sd") & (c("prev_on") == 0)
    player = pt.group_by("gsis_id", "season").agg(
        *[(c("res") * c(f)).sum().alias(f"res_{f[2:]}") for f in FLAG_COLUMNS],
        *[c(f).sum().alias(f"n_{f[2:]}") for f in FLAG_COLUMNS],
        stay_res=(c("res") * stay).sum(),
        stay_n=stay.sum(),
        ret_res=(c("res") * ret).sum(),
        ret_n=ret.sum(),
        cells=pl.len(),
    )
    team = pt.group_by("team", "side", "group", "season").agg(
        *[(c("res") * c(f)).sum().alias(f"tres_{f[2:]}") for f in FLAG_COLUMNS],
        *[c(f).sum().alias(f"tn_{f[2:]}") for f in FLAG_COLUMNS],
    )
    return player, team


def pair_sums(gt: pl.DataFrame) -> pl.DataFrame:
    """One season's grid with truth → per (player, partner, season), over the snaps the partner
    (a part-timer) was on and the player was a part-time candidate: `k` (the player on too),
    `nj` (snaps), `s` (the player's snap share summed: his expected count)."""
    keys = ["game_id", "side", "team", "n"]
    pt = gt.filter(~c("full")).select(*keys, "gsis_id", "season", "on", "share")
    j = pt.filter(c("on") == 1).select(*keys, partner=c("gsis_id"))
    pairs = pt.join(j, on=keys).filter(c("gsis_id") != c("partner"))
    return pairs.group_by("gsis_id", "partner", "season").agg(
        k=c("on").cast(pl.Float64).sum(), nj=pl.len().cast(pl.Float64), s=c("share").sum()
    )


def partner(g: pl.DataFrame, pairs: pl.DataFrame) -> pl.DataFrame:
    """`pn` per cell: the sum, over his part-time teammates named on the snap, of his pair lift
    with each (log-odds of his rate with the partner on, shrunk toward his share, minus his
    share's). `pairs`: `pair_sums` rows of the seasons to use."""
    keys = ["game_id", "side", "team", "n"]
    lift = pairs.group_by("gsis_id", "partner").agg(c("k").sum(), c("nj").sum(), c("s").sum())
    r = (c("s") / c("nj")).clip(0.02, 0.98)
    q = ((c("k") + PAIR_PRIOR * r) / (c("nj") + PAIR_PRIOR)).clip(0.01, 0.99)
    lift = lift.select("gsis_id", "partner", lift=(q / (1 - q)).log() - (r / (1 - r)).log())
    named = g.filter(c("named") & ~c("full")).select(*keys, partner=c("gsis_id"))
    x = (
        g.select(*keys, "gsis_id")
        .join(named, on=keys)
        .filter(c("gsis_id") != c("partner"))
        .join(lift, on=["gsis_id", "partner"])
        .group_by(*keys, "gsis_id")
        .agg(pn=c("lift").sum())
    )
    return g.join(x, on=[*keys, "gsis_id"], how="left").with_columns(c("pn").fill_null(0.0))


def features(
    g: pl.DataFrame,
    player_sums: pl.DataFrame,
    team_sums: pl.DataFrame,
    coaches: pl.DataFrame,
    pairs: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """The grid with its history columns: each row's season uses the player sums of every earlier
    season and the team sums of the season before, counted only when the head coach is the same
    as that season's (H33: the habits are the coach's; participation-live#F3), and `pn` from the
    pair sums of every earlier season (`partner`; 0 without `pairs` or `named`). `coaches`:
    game_id, team, coach, season."""
    seasons = g["season"].unique().to_list()
    ph, th = [], []
    for s in seasons:
        past = player_sums.filter(c("season") < s)
        agg = past.group_by("gsis_id").agg(
            *[
                (c(f"res_{k}").sum() / (c(f"n_{k}").sum() + PLAYER_PRIOR)).alias(f"ph_{k}")
                for k in FLAGS
            ],
            ph_n=c("cells").sum(),
            stay=c("stay_res").sum() / (c("stay_n").sum() + RHYTHM_PRIOR),
            ret=c("ret_res").sum() / (c("ret_n").sum() + RHYTHM_PRIOR),
        )
        ph.append(agg.with_columns(season=pl.lit(s, pl.Int32)))
        last = team_sums.filter(c("season") == s - 1)
        tagg = last.select(
            "team",
            "side",
            "group",
            *[(c(f"tres_{k}") / (c(f"tn_{k}") + TEAM_PRIOR)).alias(f"th_{k}") for k in FLAGS],
        )
        th.append(tagg.with_columns(season=pl.lit(s, pl.Int32)))
    out = g.join(pl.concat(ph), on=["gsis_id", "season"], how="left")
    out = out.join(pl.concat(th), on=["team", "side", "group", "season"], how="left")
    main = (
        coaches.group_by("team", "season")
        .agg(main_coach=c("coach").drop_nulls().mode().first())
        .with_columns(c("season") + 1)
    )
    this = coaches.select("game_id", "team", "coach")
    out = out.join(this, on=["game_id", "team"], how="left").join(
        main, on=["team", "season"], how="left"
    )
    same = (c("coach") == c("main_coach")).fill_null(False)
    out = out.with_columns(
        *[pl.when(same).then(c(x)).otherwise(0.0).alias(x) for x in TEAM_COLUMNS],
        same_coach=same,
    ).drop("coach", "main_coach")
    out = out.with_columns(
        [c(x).fill_null(0.0) for x in PLAYER_COLUMNS + TEAM_COLUMNS],
    )
    if pairs is None or "named" not in out.columns:
        return out.with_columns(pn=pl.lit(0.0))
    parts = [partner(out.filter(c("season") == s), pairs.filter(c("season") < s)) for s in seasons]
    return pl.concat(parts, how="vertical_relaxed")
