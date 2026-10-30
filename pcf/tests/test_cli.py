from pcf.cli import main
from pcf.config import secret_values


def test_info_runs_and_shows_paths(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "data folder:" in out
    assert "vault 2025" in out


def test_info_never_prints_key_values(capsys, monkeypatch):
    monkeypatch.setenv("ODDS_API_KEY", "cli_secret_value_42")
    main(["info"])
    out = capsys.readouterr().out
    assert "ODDS_API_KEY" in out
    for value in secret_values() + ["cli_secret_value_42"]:
        assert value not in out


def test_no_command_prints_help(capsys):
    assert main([]) == 0
    assert "usage: pcf" in capsys.readouterr().out
