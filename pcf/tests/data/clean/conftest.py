import polars as pl
import pytest

from pcf.config import PCF_DIR
from pcf.data.clean.players import plays_with_players

FIXTURES = PCF_DIR / "tests" / "fixtures" / "cleaning_port"


def fixture(name: str) -> pl.DataFrame:
    return pl.read_parquet(FIXTURES / f"{name}.parquet")


@pytest.fixture(scope="session")
def plays_2024() -> pl.DataFrame:
    """Two 2024 week-10 games (DET at HOU, DEN at KC), with their player lists."""
    return plays_with_players(fixture("pbp_2024"), fixture("participation_2024"))


@pytest.fixture(scope="session")
def depth_2024() -> pl.DataFrame:
    """The four teams' weekly depth charts for all of 2024, as published."""
    return fixture("depth_charts_2024")
