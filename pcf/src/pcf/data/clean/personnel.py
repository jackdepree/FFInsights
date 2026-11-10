"""Personnel strings from participation, as counts.

Participation writes personnel two ways:
- 2016-2022: groups, `"1 RB, 1 TE, 3 WR"` (offense) and `"4 DL, 2 LB, 5 DB"` (defense);
- 2023 on: positions, `"1 C, 1 FB, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 2 WR"` and
  `"3 CB, 2 DE, 2 DT, 1 FS, 2 ILB, 1 SS"`.

So a back is an RB or an FB, and a defensive back is a CB, S, FS, SS or DB, in either format.
Reading only `(\\d) RB` misses the fullback from 2023 on.
"""

import polars as pl

BACKS = ("RB", "FB")
TIGHT_ENDS = ("TE",)
RECEIVERS = ("WR",)
DEFENSIVE_BACKS = ("CB", "S", "FS", "SS", "DB")


def count(personnel: pl.Expr, positions: tuple[str, ...]) -> pl.Expr:
    """How many players of `positions` a personnel string lists: Int32, null when the string is
    null or empty."""
    found = personnel.str.extract_all(rf"\d+ (?:{'|'.join(positions)})\b")
    n = found.list.eval(pl.element().str.extract(r"(\d+)").cast(pl.Int32)).list.sum()
    return pl.when(personnel.is_not_null() & (personnel != "")).then(n.cast(pl.Int32))


def offense_group(personnel: pl.Expr) -> pl.Expr:
    """The usual personnel code, backs then tight ends ("11", "12", "21"); null when unknown."""
    rb, te = count(personnel, BACKS), count(personnel, TIGHT_ENDS)
    return pl.when(rb.is_not_null() & te.is_not_null()).then(
        pl.concat_str(rb.cast(pl.String), te.cast(pl.String))
    )


def heavy(personnel: pl.Expr) -> pl.Expr:
    """Three or more backs and tight ends; False when unknown (as the look's cell)."""
    return (count(personnel, BACKS) + count(personnel, TIGHT_ENDS) >= 3).fill_null(False)
