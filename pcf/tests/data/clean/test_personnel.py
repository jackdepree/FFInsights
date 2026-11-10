"""Personnel strings in both of participation's formats (2016-2022 groups, 2023 on positions)."""

import polars as pl

from pcf.data.clean import personnel

OFFENSE = [
    "1 RB, 1 TE, 3 WR",  # 2016-2022: 11
    "6 OL, 2 RB, 0 TE, 2 WR",  # 2016-2022: 20, an extra lineman
    "1 C, 1 FB, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 2 WR",  # 2023 on: a fullback makes it 21
    "1 C, 2 G, 1 QB, 1 RB, 2 T, 2 TE, 2 WR",  # 2023 on: 12
    "",
    None,
]
DEFENSE = [
    "4 DL, 2 LB, 5 DB",
    "3 CB, 2 DE, 2 DT, 1 FS, 1 MLB, 1 OLB, 1 SS",
    "2 CB, 1 S, 2 SS",
    None,
]


def _off(expr):
    return pl.DataFrame({"p": OFFENSE}).select(expr(pl.col("p")))[:, 0].to_list()


def test_backs_include_fullbacks_and_unknown_strings_are_null():
    assert _off(lambda p: personnel.count(p, personnel.BACKS)) == [1, 2, 2, 1, None, None]
    assert _off(personnel.offense_group) == ["11", "20", "21", "12", None, None]
    # the old reading, `(\d) RB` alone, called the fullback look light
    assert _off(personnel.heavy) == [False, False, True, True, False, False]


def test_defensive_backs_in_both_formats():
    dbs = pl.DataFrame({"p": DEFENSE}).select(
        personnel.count(pl.col("p"), personnel.DEFENSIVE_BACKS)
    )
    assert dbs[:, 0].to_list() == [5, 5, 5, None]
