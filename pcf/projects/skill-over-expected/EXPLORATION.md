# Exploration: skills over expected (`skill-over-expected`)

> The first look, 2026-11-20, at the CEO's direction (lower-noise outcomes over expected, BRIEF.md) and hunch H77. H78 is recorded and waits for the next look. One script, regular seasons 2016-2024 (PFR measures 2018-2024); the 2025 vault wasn't read.
> - [`explore/first_look.py`](explore/first_look.py) (output [`first_look.txt`](explore/first_look.txt))
>
> The technical calls, pass rules, the CEO's odds and Claude's expectations were written into BRIEF.md before the run.

**How to read the numbers:**
- **Repeats** is a season-to-season correlation of a player's per-play rate, from 0 (luck or surroundings) to 1 (all him), with its 90% interval in brackets (players resampled).
- **Reliability** is the same rate in odd weeks against even weeks, stepped up to a full season. It's the noise ceiling: how much a season can agree with itself.
- **Kept** is movers' repeat as a share of stayers'. Near 100% means the measure goes with the player when he changes teams; near 0, it stays with the team.

**Verdict: GO.** Some lower-noise outcomes carry clear player skill, and they differ by position, as the CEO expected:
- **Pass rushers are the clearest player skill PCF has found.** Pressures per dropback repeat 0.63 for defensive linemen and 0.72 for outside linebackers, and movers keep 81% and 97% of it. Sacks repeat only 0.40 and 0.35.
- **Runners own their yards after contact, and part of their yards over expected.** Rushing yards over expected (Next Gen Stats) repeat 0.28, kept 73%, against EPA per carry's 0.14. Yards after contact repeat 0.37 (kept 78%); yards before contact 0.23 (kept 54%). That is the CEO's reading of I53.
- **Offensive linemen can't be credited this way.** The team's pressure over expected while a lineman plays repeats 0.28, but movers keep none of it (0%). It belongs to the line, the QB and the scheme, not to the lineman (L2).
- **For QBs, completion over expected is real but no better than EPA** (0.41 against 0.46), and movers keep only 35% of it (41 movers).

## The noise ceiling (measured first)

Reliability within a season against the season-to-season repeat. For most measures the repeat is close to the ceiling, so they're stable traits, and the limit is how many chances a season gives.

| Group | Measure | Reliability | Repeats | Pairs (movers) |
|---|---|---|---|---|
| Defensive linemen (DE, DT, NT) | Pressures per dropback on the field | 0.65 | **0.63** (0.57-0.67) | 761 (189) |
| Outside linebackers | Pressures per dropback | 0.76 | **0.72** (0.65-0.77) | 283 (80) |
| Inside linebackers | Pressures per dropback | 0.68 | 0.57 (0.32-0.73) | 295 (71) |
| Offensive linemen | Team's pressure over expected on his dropbacks | 0.72 | 0.28 (0.21-0.35) | 814 (133) |
| QBs | Completion over expected per pass (nflfastR) | 0.57 | 0.41 (0.30-0.51) | 221 (41) |
| Receivers (WR) | Catches over expected per target | 0.32 | 0.26 (0.17-0.34) | 547 (114) |
| Tight ends | Catches over expected per target | 0.36 | 0.28 (0.17-0.38) | 170 (30) |
| Running backs, catching | Catches over expected per target | 0.06 | -0.02 | 140 (19) |
| Running backs | Rushing yards over expected per carry (NGS) | 0.34 | 0.28 (0.13-0.40) | 191 (37) |
| Running backs | Yards after contact per carry (PFR) | 0.39 | 0.37 (0.24-0.49) | 212 (47) |
| Running backs | Yards before contact per carry (PFR) | **0.49** | 0.23 (0.13-0.32) | 212 (47) |

One pattern stands out. Yards before contact agree with themselves within a season more than yards after contact do (0.49 against 0.39), and repeat across seasons less (0.23 against 0.37). A measure that is steady within a season and changes between seasons belongs to something that changes between seasons: the line in front of him. A measure that is equally steady both ways belongs to the runner.

## Findings

**F1. Pass rushers' pressures are a skill, and the player's.** Defensive linemen: repeats 0.63, kept 81%. Outside linebackers: 0.72, kept 97%. Both beat sacks clearly (by 0.22, 0.17 to 0.28; and 0.37, 0.27 to 0.48). Inside linebackers' pressures repeat 0.57 but movers keep only 36% (71 movers): for them it's more the role (how often a defense sends them) than the skill. Sacks are pressures plus luck at the finish; for a rusher's skill, ignore sacks and use pressures.

**F2. A lineman's pressure numbers are his line's.** The team's pressure over expected (a situation expectation, net of the defense's habit) while he plays repeats 0.28 for stayers and 0.00 for movers (133). The raw pressure rate is the same (0.30). So a lineman one by one can't be credited from who was on the field. The natural experiment (I81, his whole games missed) is the next way to try.

**F3. Completion over expected is a QB trait, but no better than EPA, and partly his team's.** It repeats 0.41 (0.30 to 0.51) against EPA per dropback's 0.46 (the difference -0.06, -0.16 to +0.03). Movers keep 35% (41 movers, so a wide interval). Over context-live's own expectation (2023 to 2024, 29 QBs): 0.39, the same. Who owns the rest (his receivers, his line, his play caller) is the movers model's question (I76).

**F4. Receivers' catches over expected are a modest skill that travels.** Wide receivers: 0.26, kept 78%, against EPA per target's 0.19 (the difference +0.08, -0.00 to +0.15). Tight ends repeat 0.28 but movers keep almost none (30 movers: unclear). Running backs' catching is noise (0.06 reliability).

**F5. Runners: yards over expected with tracking repeat; with the situation alone, much less.** Next Gen Stats' version, whose expectation comes from tracking at the handoff (so it already holds part of the blocking), repeats 0.28 (0.13 to 0.40) and movers keep 73%. EPA per carry repeats 0.14. The difference is +0.14 (-0.02 to +0.29): better, not clearly by the bar. Over context-live's expectation, which knows the situation and the calls but nothing about the blocking, 2023 to 2024 (37 backs): 0.11. Taking out the teammates' rate (the line, by subtraction) leaves 0.10 (-0.04 to 0.23, 99 pairs); that subtraction is noisy, and its reliability is inflated because the teammates' rate uses the whole season. Unclear.

**F6. The CEO's reading of I53 holds in direction.** Yards after contact repeat 0.37 and travel (78%); yards before contact repeat 0.23 and travel less (54%). The CEO: a back "has to thrive within opportunities, and the team around them has to create the opportunities for them." The difference in repeats is +0.14 (-0.03 to +0.30), so not clear on its own; with F5's within-season pattern, it's the best-supported reading we have.

## The hunches

| Hunch | Verdict | Numbers |
|---|---|---|
| **H77**, the CEO: lower-noise outcomes "much better for prediction" for runners and defensive linemen (70%) | **Held in part.** Defensive linemen held; runners just short | Linemen: pressures beat sacks by 0.22 (0.17 to 0.28). Runners: yards over expected beat EPA by 0.14 (-0.02 to 0.29), under the bar of 0.15 with the interval above zero. **Real?** Partly. **Pays?** Not tested: this is repeat, not a forecast |
| **H78**, the CEO: a moving back's share from who is in his new backfield (30%) | Next look | |

Claude's expectations, scored:

| Bet | Claude | Result |
|---|---|---|
| H77 as worded (both groups clear the bar) | 35% | Held in part |
| Defensive linemen clear the bar | 75% | **Held** |
| Runners clear the bar | 35% | Failed, narrowly |
| Pass rushers' pressure repeats 0.3+ | 80% | **Held** (0.63, 0.72) |
| QBs' completion over expected 0.3+ | 70% | **Held** (0.41) |
| Runners' yards over expected 0.3+ | 30% | Failed, narrowly (0.28) |
| Movers keep half: pass rushers | 60% | **Held** (81%, 97%) |
| Movers keep half: QBs | 60% | Failed (35%) |
| Movers keep half: runners | 30% | **Held** (73%) |
| Movers keep half: linemen one by one | 25% | Failed (0%) |
| Yards after contact repeat and travel more than before contact | 65% | Held in direction |

## What it means for the per-position map (I79, started)

| Position | Use | Ignore |
|---|---|---|
| Edge rushers and defensive linemen | Pressures per dropback (his, and they travel) | Sacks, as a skill (pressures plus luck) |
| Inside linebackers | Pressures, as his role more than his skill | |
| Offensive linemen | The line's pressure over expected, as the **line's** trait | Any lineman's on-field pressure number as his own |
| QBs | Completion over expected and EPA per dropback, both traits, both partly the team's | Neither is the QB alone yet (I76) |
| Wide receivers | Catches over expected per target (modest, travels) | |
| Tight ends | | Catches over expected, until more movers |
| Running backs | Yards after contact; yards over expected with tracking | Yards before contact (his line's); EPA per carry; his catching over expected |

## Limitations and assumptions

- **Repeat is not prediction.** H77's word was "prediction"; this look measures whether a skill is real and his. Whether it helps a forecast (the yardstick, or a team's pressure next season) is the next test.
- **Volume floors pick survivors.** Players with enough chances in both seasons are mostly starters; a player who lost his job isn't in the pairs.
- **Few movers** at QB (41) and TE (30): their "kept" numbers are wide.
- **PFR's pressures are charted by people**, and charting may differ by team or season. The same charting for both seasons of a mover would hide it; a mover's new team charts him fresh, which is a partial check.
- **The OL expectation is simple** (season, down, distance band, rushers, the defense's habit), fit on the same seasons. A better one (context-live's `pressure_prob`, 2024 only) can't give a season pair yet.
- **Next Gen Stats' expected rushing yards hold part of the blocking**, so its yards over expected flatter runners against a situation-only version (F5).

## Next steps (for the CEO's direction)

- **(a) H78**, as designed in BRIEF.md: a moving back's new share from who is in the new backfield.
- **(b) Does it pay?** The measures that held, as inputs: pass rushers' pressures for next season's team pressure and sacks; runners' yards after contact and over expected for next season's rushing yards (the yardstick, I80's group).
- **(c) Who owns the QB's completion over expected:** the movers model with its correction (I76).
- **(d) Linemen one by one:** whole games missed, on pressure (I81).
