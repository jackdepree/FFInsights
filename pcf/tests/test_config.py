from pathlib import Path

import pytest

from pcf.config import (
    DATA_ZONES,
    PCF_DIR,
    get_secret,
    load_config,
    read_env_file,
    secret_values,
)


def test_data_dir_defaults_inside_pcf():
    cfg = load_config(env={})
    assert cfg.data_dir == (PCF_DIR / "data").resolve()
    assert cfg.pcf_dir.name == "pcf"


def test_pcf_data_dir_override(tmp_path):
    cfg = load_config(env={"PCF_DATA_DIR": str(tmp_path)})
    assert cfg.data_dir == tmp_path.resolve()


def test_relative_override_resolves_from_pcf():
    cfg = load_config(env={"PCF_DATA_DIR": "elsewhere"})
    assert cfg.data_dir == (PCF_DIR / "elsewhere").resolve()


def test_zones(tmp_path):
    cfg = load_config(env={"PCF_DATA_DIR": str(tmp_path)})
    assert cfg.zone("raw") == tmp_path.resolve() / "raw"
    with pytest.raises(ValueError):
        cfg.zone("scratch")
    cfg.ensure_dirs()
    assert all((tmp_path / z).is_dir() for z in DATA_ZONES)


def test_seasons_match_validation_doc():
    s = load_config(env={}).seasons
    assert (s.first_train, s.first_report, s.vault, s.live) == (2006, 2016, 2025, 2026)


def test_read_env_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        '# comment\nODDS_API_KEY="abc123secret"\n\nEMPTY=\nnot a pair\n', encoding="utf-8"
    )
    assert read_env_file(env) == {"ODDS_API_KEY": "abc123secret", "EMPTY": ""}
    assert read_env_file(tmp_path / "missing.env") == {}


def test_get_secret_prefers_environment(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("PCF_TEST_KEY=from_file\n", encoding="utf-8")
    assert get_secret("PCF_TEST_KEY", env) == "from_file"
    monkeypatch.setenv("PCF_TEST_KEY", "from_env")
    assert get_secret("PCF_TEST_KEY", env) == "from_env"
    assert get_secret("PCF_NOT_SET", env) is None


def test_config_never_holds_secrets(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("ODDS_API_KEY=supersecretvalue\n", encoding="utf-8")
    monkeypatch.setenv("ODDS_API_KEY", "supersecretvalue")
    cfg = load_config(env={})
    assert "supersecretvalue" not in repr(cfg)
    assert "supersecretvalue" in secret_values(env)


def test_secret_values_include_actions_secrets(tmp_path, monkeypatch):
    # On Actions there's no .env file; secrets arrive as environment variables.
    monkeypatch.setenv("PCF_DATA_TOKEN", "token_from_actions")
    assert "token_from_actions" in secret_values(Path(tmp_path / "missing.env"))
