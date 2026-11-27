# ruff: noqa: E501
"""Retro 5, step 9 (the CEO, 2026-11-27: "I would be interested to see the how much usage or tokens each project and
exploration or each idea costs"): a first baseline of what each branch's work cost, in tokens, from Claude Code's
local session transcripts (never committed; only these totals are). Every assistant message records its usage; one
message can appear on several lines, so each is counted once (by message id). A message is charged to the git branch
its session was on when it was written (`gitBranch`): build sessions sit on their project's branch, and the strategy
chat's work is charged to whichever branch it had checked out, so its explorations land on their project's branch.
Subagents' transcripts count too. Tokens: fresh input (input plus cache writes), cached input re-read, and output.
Run from pcf/:  python projects/retro/explore/retro5_costs.py > projects/retro/explore/retro5_costs.txt
(CLAUDE_TRANSCRIPTS overrides the transcripts folder; the default is ~/.claude/projects.)
"""

import json
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_TRANSCRIPTS", Path.home() / ".claude" / "projects"))
seen = set()
tot = defaultdict(lambda: [0, 0, 0, 0, None, None])
for d in ROOT.iterdir():
    if "FFInsights" not in d.name:
        continue
    for f in d.rglob("*.jsonl"):
        for line in f.open(encoding="utf-8", errors="replace"):
            if '"usage"' not in line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            m = r.get("message") or {}
            u, mid = m.get("usage"), m.get("id")
            if not u or not mid or mid in seen:
                continue
            seen.add(mid)
            b = r.get("gitBranch") or "(none)"
            t = tot[b]
            t[0] += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            t[1] += u.get("cache_read_input_tokens", 0)
            t[2] += u.get("output_tokens", 0)
            t[3] += 1
            ts = r.get("timestamp", "")[:10]
            t[4] = min(t[4] or ts, ts)
            t[5] = max(t[5] or ts, ts)
rows = sorted(tot.items(), key=lambda kv: -(kv[1][0] + kv[1][1] + kv[1][2]))
print(f"{'branch':<34}{'messages':>9}{'fresh in (M)':>14}{'cached in (M)':>15}{'output (M)':>12}  dates")
for b, (fi, ci, o, n, a, z) in rows:
    print(f"{b:<34}{n:>9}{fi / 1e6:>14.1f}{ci / 1e6:>15.1f}{o / 1e6:>12.2f}  {a} to {z}")
s = [sum(v[i] for v in tot.values()) for i in range(4)]
print(f"{'all':<34}{s[3]:>9}{s[0] / 1e6:>14.1f}{s[1] / 1e6:>15.1f}{s[2] / 1e6:>12.2f}")
