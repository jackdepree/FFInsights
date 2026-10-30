"""Light exploration for data-layer: size and update history of every nflverse file we pull.

nflreadpy downloads GitHub release assets, so the GitHub API tells us each file's size and
when it was last re-uploaded. That shows how often each source changes, and whether past
seasons get revised (which decides what a refresh must re-download and what needs snapshots).

Run from pcf/:  uv run python projects/data-layer/explore/profile_releases.py > out.md
No API key needed (about 25 unauthenticated requests; GitHub allows 60 an hour).
"""

import re
from datetime import UTC, datetime

import requests

API = "https://api.github.com/repos/{repo}/releases/tags/{tag}"
ASSETS = "https://api.github.com/repos/{repo}/releases/{id}/assets?per_page=100&page={page}"

RELEASES = [
    ("nflverse/nflverse-data", t)
    for t in [
        "pbp",
        "pbp_participation",
        "stats_player",
        "stats_team",
        "schedules",
        "snap_counts",
        "nextgen_stats",
        "pfr_advstats",
        "ftn_charting",
        "depth_charts",
        "injuries",
        "rosters",
        "weekly_rosters",
        "players",
        "combine",
        "draft_picks",
        "trades",
        "contracts",
        "officials",
        "teams",
    ]
] + [("ffverse/ffopportunity", "latest-data")]

SEASON = re.compile(r"(19|20)\d\d")


def assets(repo: str, tag: str) -> list[dict]:
    release = requests.get(API.format(repo=repo, tag=tag), timeout=30)
    release.raise_for_status()
    rid, out, page = release.json()["id"], [], 1
    while True:
        r = requests.get(ASSETS.format(repo=repo, id=rid, page=page), timeout=30)
        r.raise_for_status()
        batch = r.json()
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def when(a: dict) -> datetime:
    return datetime.fromisoformat(a["updated_at"].replace("Z", "+00:00"))


def main() -> None:
    now = datetime.now(UTC)
    print(f"Pulled {now:%Y-%m-%d %H:%M} UTC. Parquet assets only.\n")
    print("| Release | Files | Total MB | Largest file MB | Newest upload | Oldest upload "
          "| Past seasons re-uploaded in the last 60 days |")
    print("|---|---|---|---|---|---|---|")
    detail = []
    for repo, tag in RELEASES:
        files = [a for a in assets(repo, tag) if a["name"].endswith(".parquet")]
        if not files:
            print(f"| {tag} | 0 | | | | | |")
            continue
        mb = [a["size"] / 1e6 for a in files]
        recent_past = sorted(
            {
                m.group(0)
                for a in files
                if (m := SEASON.search(a["name"]))
                and int(m.group(0)) < now.year
                and (now - when(a)).days <= 60
            }
        )
        print(
            f"| {tag} | {len(files)} | {sum(mb):,.0f} | {max(mb):,.0f} "
            f"| {max(map(when, files)):%Y-%m-%d} | {min(map(when, files)):%Y-%m-%d} "
            f"| {', '.join(recent_past) or 'none'} |"
        )
        for a in sorted(files, key=lambda a: a["name"]):
            detail.append(f"{tag}\t{a['name']}\t{a['size'] / 1e6:.1f}\t{when(a):%Y-%m-%d %H:%M}")
    print("\n<details><summary>Every file</summary>\n\n```")
    print("release\tfile\tMB\tlast upload (UTC)")
    print("\n".join(detail))
    print("```\n</details>")


if __name__ == "__main__":
    main()
