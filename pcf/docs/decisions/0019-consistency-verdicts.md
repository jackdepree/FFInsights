# 0019: How a measure is called consistent

**Date:** 2026-11-07 · **Decided by:** Claude (the CEO asked for the test; how it's measured is a technical call, listed for veto at merge)

**Decision:** `pcf.validation.consistency` gives every measure three numbers and a verdict:
- **Week to week:** split-half. Each team-season's mean in odd weeks against its mean in even weeks, correlated across team-seasons.
- **Season to season:** each team's mean in one season against the next season's.
- **90% intervals** for both, from Fisher's z.
- **Verdict:** `noise` when the week-to-week interval reaches 0; `state` when it repeats within a season but the season-to-season interval reaches 0 (something a team is in for a while, like an injured QB); otherwise `trait`.

**Why:** split-half is the usual way sports analysts measure how fast a stat "stabilizes", it needs no model, and it works for any measure per team per game. Calling something noise only when its interval reaches 0 keeps the label for measures we can't tell from luck, rather than for measures that are merely weak.

**Alternatives:**
- A fixed cutoff on r (say 0.3): simpler to read, but it ignores how many team-seasons stand behind the number.
- Week-to-week autocorrelation (this week against next week): mixes the measure's noise with real changes in a team during a season.
- A variance split (between-team share of the variance, as in the `stabilization` project to come): more exact, and that project may replace this.

**Revisit if:** the `stabilization` project builds a better estimate of how much of a measure is the team.

**Code:** [`src/pcf/validation/consistency.py`](../../src/pcf/validation/consistency.py); the register is [`projects/CONSISTENCY.md`](../../projects/CONSISTENCY.md).
