"""context-live's back-history: the provider rule, the editions and the outcomes (no data)."""

from pcf.experts.context_live import back, plays


def test_provider_rule_keeps_pressure_and_time_to_throw_apart():
    # through 2023 everything trains from 2016; 2024's participation outcomes on 2023 alone
    assert back.train_seasons("pressure_prob", 2023) == (2016, 2022)
    assert back.train_seasons("pressure_prob", 2024) == (2023, 2023)
    assert back.train_seasons("time_to_throw_exp", 2024) == (2023, 2023)
    assert back.train_seasons("sack_prob", 2024) == (2016, 2023)


def test_editions_and_cadence():
    assert back.EDITIONS["situation"] == plays.SITUATION
    assert set(back.CALLS16) <= set(back.EDITIONS["calls16"])
    # participation's calls are published after the season: never an in-season input
    assert back.CADENCE["calls16"] == "retrospective"
    assert back.CADENCE["situation"] == "in_season"
    assert not set(back.EDITIONS["situation"]) & set(plays.FTN_COLUMNS)


def test_outcomes_start_in_2016_and_never_reach_the_vault():
    for name in back.OUTCOMES:
        assert back.outcome(name).first_season == back.FIRST
        assert name in back.SITUATION_METHOD and name in back.CALLS_METHOD
    assert max(back.TEST) == 2024
