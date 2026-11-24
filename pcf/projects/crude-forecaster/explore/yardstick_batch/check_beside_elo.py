# ruff: noqa: E501
"""The batch's check on two "beside Elo" gains (I60's starters' games, I75's offense continuity) on
team yards over the rest of the season: Elo alone doesn't help that board (-0.86%, not clear), so
a gain beside Elo may only repair Elo. Each is scored here against the plain crude forecast
(crude + Elo + input against crude), with 19 copies of the input shuffled within weeks.

Run from pcf/: python projects/crude-forecaster/explore/yardstick_batch/check_beside_elo.py > projects/crude-forecaster/explore/yardstick_batch/check_beside_elo.txt
"""

import numpy as np
import polars as pl

from pcf.baselines.crude import inputs as I
from pcf.baselines.crude import yardstick as Y

c = pl.col


def main() -> None:
    b = Y.load_board("team", "rest")
    rows = b.features.select("game_id", "team", "season", "week", "as_of")
    crude = b.forecast()
    elo = b.forecast(("elo",))
    g = Y.gain(elo, crude, b.keys)
    print(f"team rest: Elo alone {100 * g.share:+.2f}% ({100 * g.lo:+.2f} to {100 * g.hi:+.2f})")
    cont = I.team_continuity(rows, I.continuity()).select(*b.keys, "off_new_pre")
    av = I.team_availability(rows)
    for name, frame in (("off continuity pre", cont), ("starters' games forecast", av)):
        cols = [x for x in frame.columns if x not in b.keys]
        feats = b.features.join(frame, on=b.keys, how="left").with_columns(c(x).fill_null(c(x).median()) for x in cols)
        new = b.forecast(("elo",), extra=cols, feats=feats)
        g = Y.gain(new, crude, b.keys)
        null = []
        for k in range(1, 20):
            sh = Y.shuffle_within_weeks(feats, cols, seed=1000 + k)
            null.append(Y.gain(b.forecast(("elo",), extra=cols, feats=sh), crude, b.keys).share)
        print(f"  crude + Elo + {name} against crude: {100 * g.share:+.2f}% ({100 * g.lo:+.2f} to {100 * g.hi:+.2f}); range {100 * g.range_share:+.2f}% ({100 * g.range_lo:+.2f} to {100 * g.range_hi:+.2f}); copies (crude + Elo + shuffled) max {100 * max(null):+.2f}%, median {100 * float(np.median(null)):+.2f}%")


if __name__ == "__main__":
    main()
