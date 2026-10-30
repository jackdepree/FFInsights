"""The one place PCF resolves paths and settings (rule f).

Settings come from `pcf/config.toml`. API keys come from the environment or `pcf/.env` and are
read only on demand, by `get_secret`. They are never stored on the config object.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path

# src/pcf/config.py -> pcf/. Works because uv installs the package in editable mode.
PCF_DIR = Path(__file__).resolve().parents[2]
CONFIG_FILE = PCF_DIR / "config.toml"
ENV_FILE = PCF_DIR / ".env"

# The storage zones under the data folder (docs/ARCHITECTURE.md, "Storage").
DATA_ZONES = ("raw", "interim", "tables", "features", "outputs", "mlflow", "ledger", "logs")

# Secrets that may arrive as environment variables (GitHub Actions secrets, pcf/.env.example).
KNOWN_SECRET_NAMES = ("ODDS_API_KEY", "CFBD_API_KEY", "PCF_DATA_TOKEN", "GITHUB_TOKEN")


@dataclass(frozen=True)
class Seasons:
    first_train: int
    first_report: int
    vault: int
    live: int


@dataclass(frozen=True)
class Config:
    pcf_dir: Path
    config_file: Path
    data_dir: Path
    seasons: Seasons
    seed: int
    log_level: str

    def zone(self, name: str) -> Path:
        """The folder for one storage zone, e.g. `zone("raw")`."""
        if name not in DATA_ZONES:
            raise ValueError(f"Unknown data zone {name!r}. Zones: {', '.join(DATA_ZONES)}")
        return self.data_dir / name

    def ensure_dirs(self) -> None:
        """Create the data folder and every zone in it."""
        for name in DATA_ZONES:
            self.zone(name).mkdir(parents=True, exist_ok=True)


def load_config(path: Path = CONFIG_FILE, env: Mapping[str, str] | None = None) -> Config:
    """Read `config.toml`, applying the `PCF_DATA_DIR` override from `env` (default: os.environ)."""
    env = os.environ if env is None else env
    raw = tomllib.loads(path.read_text(encoding="utf-8"))

    data_dir = Path(env.get("PCF_DATA_DIR") or raw["paths"]["data_dir"])
    if not data_dir.is_absolute():
        data_dir = PCF_DIR / data_dir

    return Config(
        pcf_dir=PCF_DIR,
        config_file=path,
        data_dir=data_dir.resolve(),
        seasons=Seasons(**raw["seasons"]),
        seed=int(raw["random"]["seed"]),
        log_level=str(raw["logging"]["level"]).upper(),
    )


@cache
def get_config() -> Config:
    """The project config, loaded once per process."""
    return load_config()


def read_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """Parse `KEY=value` lines from a .env file. Missing file -> empty dict."""
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def get_secret(name: str, path: Path = ENV_FILE) -> str | None:
    """An API key from the environment first, then `.env`. None when unset. Never log the result."""
    return os.environ.get(name) or read_env_file(path).get(name) or None


def secret_values(path: Path = ENV_FILE) -> list[str]:
    """Every non-empty key value we know of, so logging can mask them.

    Covers `.env` and, on GitHub Actions (no .env), the secrets set as environment variables.
    """
    from_file = read_env_file(path)
    names = set(from_file) | set(KNOWN_SECRET_NAMES)
    values = {v for v in from_file.values() if v}
    values |= {os.environ[n] for n in names if os.environ.get(n)}
    return sorted(values, key=len, reverse=True)
