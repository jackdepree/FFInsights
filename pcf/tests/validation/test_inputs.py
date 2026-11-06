import polars as pl

from pcf.validation.inputs import MIN_ROWS, input_check


def frame(n: int, nonzero: int, name: str = "x") -> pl.DataFrame:
    return pl.DataFrame({name: [1.0] * nonzero + [0.0] * (n - nonzero)})


def test_same_data_raises_no_flag():
    out = input_check(frame(1000, 80), frame(1000, 80), ["x"])
    assert out["gap"].item() == 0
    assert not out["flag"].item()


def test_an_input_that_goes_quiet_is_flagged():
    # The injury report from 2025: about 8 rows in 100 in the backtest, none live
    out = input_check(frame(1000, 78), frame(1000, 0), ["x"])
    assert out["flag"].item()
    assert out["used_backtest"].item() == 7.8
    assert out["used_live"].item() == 0


def test_a_large_gap_is_flagged_only_with_enough_rows():
    backtest = frame(1000, 500)
    assert input_check(backtest, frame(MIN_ROWS, 40), ["x"])["flag"].item()
    assert not input_check(backtest, frame(MIN_ROWS - 1, 40), ["x"])["flag"].item()


def test_a_quiet_input_needs_enough_rows_to_have_shown():
    # One Thursday game: at 8 in 100, about 2 of 30 rows would be filled, so none is no surprise
    assert not input_check(frame(1000, 78), frame(30, 0), ["x"])["flag"].item()
    # A common input going quiet in that same game is worth a look
    assert input_check(frame(1000, 500), frame(30, 0), ["x"])["flag"].item()


def test_missing_values_count_in_the_gap():
    backtest = pl.DataFrame({"x": [1.0] * 100})
    live = pl.DataFrame({"x": [1.0] * 800 + [None] * 200})
    out = input_check(backtest, live, ["x"])
    assert out["missing_live"].item() == 20
    assert out["flag"].item()


def test_text_inputs_are_skipped_and_gaps_sort_first():
    backtest = pl.DataFrame({"a": [1.0, 0.0] * 150, "b": [0.0, 1.0] * 150, "t": ["z"] * 300})
    live = pl.DataFrame({"a": [1.0, 0.0] * 150, "b": [0.0] * 300, "t": ["z"] * 300})
    out = input_check(backtest, live, ["a", "b", "t"])
    assert out["input"].to_list() == ["b", "a"]


def test_empty_sides_give_an_empty_result():
    assert input_check(frame(0, 0), frame(10, 1), ["x"]).is_empty()
