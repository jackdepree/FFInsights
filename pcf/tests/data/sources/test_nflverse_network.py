"""The catalog against the real nflverse (run with `uv run pytest -m network`).

Reads the local copy kept by `pcf refresh` if there is one. Otherwise downloads about 110 MB
(every dataset's 2025 file plus the single-file datasets) into a temp folder. Listing uses 22
GitHub API calls (60 an hour without GITHUB_TOKEN). Starting from a copy of
the local refresh's cache saves re-sending unchanged listings, and makes them free with a token.
"""

import shutil

import nflreadpy as nfl
import polars as pl
import pytest
from nflreadpy.config import update_config

from pcf.config import get_config
from pcf.data.sources.nflverse import DATASETS, GitHubUpstream, refresh, scan
from pcf.data.sources.store import usable_keys

pytestmark = pytest.mark.network
SEASON = 2025


@pytest.fixture(scope="module")
def upstream(tmp_path_factory):
    # Start from a copy of the local refresh's API cache when there is one, so the real cache is
    # never touched.
    cache = tmp_path_factory.mktemp("cache") / "_api_cache.json"
    local = get_config().zone("raw") / "nflverse" / "_api_cache.json"
    if local.exists():
        shutil.copy(local, cache)
    return GitHubUpstream(cache_file=cache)


@pytest.fixture(scope="module")
def raw(upstream, tmp_path_factory):
    # Check the copy `pcf refresh` keeps when there is one (read only, no API calls): that's the
    # copy everything else reads. Otherwise fetch the 2025 files into a temp folder.
    local = get_config().zone("raw")
    if (local / "nflverse" / "_manifest").exists():
        return local
    folder = tmp_path_factory.mktemp("raw")
    refresh(seasons=[SEASON], upstream=upstream, raw_dir=folder, logs_dir=folder)
    return folder


@pytest.mark.parametrize("name", list(DATASETS))
def test_every_dataset_is_published(upstream, name):
    files = upstream.list_files(DATASETS[name])
    assert files, f"nothing upstream matches {DATASETS[name].pattern}"
    assert all(f.version.startswith(("sha256:", "blob:")) for f in files)
    if DATASETS[name].per_season:
        assert SEASON in {f.season for f in files}


@pytest.mark.parametrize("name", list(DATASETS))
def test_keys_and_watched_columns_exist(raw, name):
    ds = DATASETS[name]
    df = scan(name, [SEASON], raw).collect()
    missing = [c for c in ds.keys + ds.watched if c not in df.columns]
    assert not missing, f"{name}: catalog names columns the file doesn't have: {missing}"
    if ds.keys:
        assert usable_keys(df, ds.keys), f"{name}: keys {ds.keys} aren't unique"


LOADERS = {
    "pbp": lambda: nfl.load_pbp(SEASON),
    "participation": lambda: nfl.load_participation(SEASON),
    "player_stats": lambda: nfl.load_player_stats(SEASON),
    "snap_counts": lambda: nfl.load_snap_counts(SEASON),
    "injuries": lambda: nfl.load_injuries(SEASON),
    "ftn_charting": lambda: nfl.load_ftn_charting(SEASON),
    "players": nfl.load_players,
    "contracts": nfl.load_contracts,
    "ff_opportunity": lambda: nfl.load_ff_opportunity(SEASON),
}


@pytest.mark.parametrize("name", list(LOADERS))
def test_our_copy_matches_nflreadpy(raw, name):
    update_config(cache_mode="off")
    ours = scan(name, [SEASON], raw).collect()
    theirs = LOADERS[name]()
    assert ours.equals(theirs), f"{name}: {ours.shape} vs nflreadpy {theirs.shape}"


def test_schedules_match_nflreadpy_apart_from_its_roof_cleaning(raw):
    # nflreadpy nulls any roof outside these four; the published file has 26 games with "".
    # Raw keeps what was published, so cleaning-port has to apply the same rule.
    update_config(cache_mode="off")
    ours = scan("schedules", raw_dir=raw).collect()
    theirs = nfl.load_schedules(seasons=True)
    valid = pl.col("roof").is_in(["dome", "outdoors", "closed", "open"])
    cleaned = ours.with_columns(pl.when(valid).then(pl.col("roof")).alias("roof"))
    assert cleaned.equals(theirs)
