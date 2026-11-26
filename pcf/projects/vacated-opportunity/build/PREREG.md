# The build's odds, written before each result (2026-11-25)

Committed before the runs they describe. The ladder's first numbers (rungs 1-5 of `vacated-live`) were seen before this file; everything below was not.

## Backlog ideas (their odds are already in IDEAS.md; restated here)

| Idea | The test here | Odds (where they were written) |
|---|---|---|
| I49 | The pair part beside the pooled part, weekly, Saturday knowledge | IDEAS.md, 2026-11-15: medium, 0.5-1.5 points of share. Already seen in the ladder: +18.8% of the pooled part's error on snaps |
| I55 | First game back: participation's miss, and whether his own healthy mean to date fixes it | IDEAS.md, 2026-11-15: high, 1.5-2.5 points of share on ~150 rows a season |
| I143 | COVID-list absences' same-group rates against the rest | IDEAS.md, 2026-11-25: 65% they agree (interval covers 0); 25% the COVID rate is higher |
| I14 | Ranges widened by his own swing | IDEAS.md (held for stabilization): high, coverage evens out by 5+ points across swing bands. Already seen in the ladder (it evens out; range score better for targets and carries, slightly worse for snaps) |
| I126 | Role distance against same position, where the group was left empty | IDEAS.md, 2026-11-24: 25% Z beats P on target share; about 2% if so |
| I136 / I122 | The role table's like-for-like in the offseason (the vacancy blend) | Claude, now: 35% that weighting the departed player's share by role-table closeness beats the group-only pooled rate for stayers where the group was left empty, on target share, interval above 0; about 1-3% if so |
| I9 | A mover's first games: the team's unclaimed share as an input | Claude, now: 40% the offseason unclaimed share at his new group lowers participation's error on movers' first 4 games (interval above 0); about 0.2-0.5 points of share |

## New ideas (Claude's, this build; numbered I160-I169)

| # | Idea | Odds before the test |
|---|---|---|
| I160 | **Recalibrate the forecast change:** scale the plus-minus's change by a slope fit walk-forward on earlier seasons (target share's slope is 0.79) | 55% it gains on target share with an interval above 0, about 0.3% of the squared error; 20% on snap share (its slope is 0.95) |
| I161 | **The trees' absence part beside participation:** the trees' extra over trees without the absence inputs (+3.2% snaps, +1.0% targets in the ladder) still adds once participation and the plus-minus's change are in | 40% on snap share with an interval above 0, about 0.5%; 25% on targets |
| I162 | **The choice model beats the plus-minus on targets in season** (method 3, nested logit with groups as nests, fit on completed seasons' plays with who was on the field) | 25% it beats the plus-minus's target-share change on the scored rows with an interval above 0; 20% on carries; 80% it beats no change |
| I164 | **A sudden absence transfers more than a long one** (written after I143's result, which found COVID-list absences transfer more than injury ones): the same-group rate in the first game of an absence spell is higher than in its later games, when the team has signed or promoted a replacement | 60% for WR, RB and OL together with an interval above 0; the first game's rate about 0.03-0.06 higher |
| I163 | **The nests matter:** the choice model's same-group nest parameters are below 1 (closer substitutes within a group), with an interval clear of 1 | 75% for WR and TE together; 60% for RB |
| I165 | **Shrink the offseason change** (written after the offseason's first results, which put the calibration slopes at 0.63 for skill snaps left empty, 0.77 for the lines, 0.46 for targets and 0.45 for carries): scale the plus-minus's change by a slope fit on earlier pairs (per measure, skill groups left empty and the lines apart) | 60% the shrunk forecast beats the unshrunk one on skill snap share left empty with an interval above 0, about 2-4% of the squared error; 55% it then beats no change on target share where left empty (interval above 0), about 2-3%; 35% on carry share |

## The brief's tests (pass rules from BRIEF.md; Claude's odds now)

- **No noise, `vacated-live`:** beats 19 of 19 shuffled copies on each share: 95% each.
- **The obvious-input check:** the plus-minus's change still lowers the squared error beside participation's share (snaps) with an interval above 0: 85%; beside opportunity-quality's expected points (targets): 80%; carries 80%.
- **The yardstick, next game:** the change counts on receiving yards beside participation (interval above 0, beats 19 copies): 45%; rushing: 45%. Expected size 0.1-0.3% of the squared error.
- **`vacated-offseason`, where the group was left empty:** beats no change on skill snap share with the week-1 roster's intake flag (interval above 0): 60%; on target share 55%; carry share 40%; the lines' snap share 75%. The gated forecast beats no change over all stayers: 55%.
- **The offseason yardstick (season yards):** counts on receiving or rushing: 25%.

## The CEO's spot-check: the shrink on target share (asked 2026-11-26; odds written before the check)

The result being checked: over all stayers, the shrunk target-share forecast beats no change by +2.8% (90% +0.5% to +4.7%); where the group was left empty, +5.1% (+0.9% to +8.4%).

- **The slope is known before each season** (fit only on pairs whose next season had finished by that season's week 1): a design check, not a bet; it either holds or there's a leak.
- **No noise:** the shrunk forecast, rebuilt end to end with each season's departures moved to another team (the slope refit on the shuffled rows), loses to the real one in 19 of 19 copies: 85%.
- **Steady by season:** the shrunk forecast beats no change in at least 6 of the 8 scored seasons: 55%.
- **Where it comes from:** tight ends carry the largest gain of the three groups (the unshrunk plus-minus was already +8.0% for TEs left empty): 55%.
- **How close to zero:** dropping any one season, the gain over all stayers keeps an interval above 0 in all 8 drops: 40%.
- **What the slope costs:** a slope fit in hindsight on all seasons gains no more than 1 point over the walk-forward one: 70%.
- **Verdict:** it still ships after the check: 75%.

**Results (2026-11-26, `spot_target_shrink.txt`):**
- The slope is known before each season: held (by design).
- 19 of 19 shuffles: held (85%).
- 6 or more of 8 seasons positive: held, 8 of 8 (55%).
- TEs carry the largest gain: held (55%), TE +5.4% against WR +2.0% and RB +2.1%; by share of the error removed 45% against 42%.
- All 8 drops above 0: failed (40%), 7 of 8; without 2021 the interval reaches −0.3%.
- The hindsight slope within 1 point: held (70%), +0.18%.
- Still ships: yes (75%).

