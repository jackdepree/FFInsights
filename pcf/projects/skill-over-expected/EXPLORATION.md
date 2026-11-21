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

## Second look: does it pay? (written before the run, 2026-11-20)

The CEO, 2026-11-20: "the next test should be the next season or maybe even the next game for runners and sacks and pressures and completion percentage and stuff like that." This is H77's **pays?** question. H79 to H83 were recorded in the same reply, so their tests wait for the next look (CLAUDE.md).

**Technical calls (Claude's, for the CEO to veto):**
1. **Targets the downstream models use**, per player: a running back's yards per carry, a QB's completion rate, a pass rusher's sacks per dropback on the field (and his pressures per dropback).
2. **Two horizons.** *Next season:* this season's numbers against next season's rate (seasons as in the first look). *Next game:* season-to-date numbers through the last game against this game's rate, from the third game on with a minimum of chances to date (runners 30 carries, QBs 60 passes, rushers 60 dropbacks).
3. **The base is the target's own past** (past yards per carry, past completion rate, past sack rate), because that's the obvious input (W1). The test adds the lower-noise measure beside it: yards after contact and yards over expected for runners; completion over expected for QBs; pressure rate for rushers.
4. **Scored held out by season:** a weighted linear fit (weights the target's chances) on every other season, scored on the left-out one; the gain is the share of the base's weighted squared error removed. 90% interval from resampling players, 1,000 draws.
5. The league average alone is shown too, so the past's own worth is visible.

**Pass rule for H77's pays? (the CEO's "much better for prediction" for runners and defensive linemen):** pays for a group if its lower-noise measure removes error beyond the base at the next-season horizon with the interval above zero. Both groups: pays. One: pays in part. The next game is reported beside it, not part of the rule.

**Claude's expectations:**
- Runners, next season: yards after contact adds 1%+ over past yards per carry, 55%; yards over expected adds 1%+, 50%. Next game: anything adds 0.5%+, 30% (a game's yards per carry is mostly luck).
- QBs, next season: completion over expected adds 1%+ over past completion rate, 45%. Next game, 30%.
- Pass rushers (DE, DT, NT, OLB), next season: pressure rate adds 5%+ over past sack rate for next season's sacks, 80%. Next game: 1%+, 60%.
- H77's pays? as worded (both groups): 45%.

### Second look: the results ([`explore/second_look.py`](explore/second_look.py), output [`second_look.txt`](explore/second_look.txt))

"Past alone" is how much of the league average's error the target's own past removes. "Added" is how much of the past-only forecast's error the measure removes on top, held out by season, with its 90% interval.

| Group | Horizon | Target | Past alone | Added measure | Added | Rows |
|---|---|---|---|---|---|---|
| DE, DT, NT | Next season | Sacks per dropback | 18.4% | Pressure rate | **+9.4%** (+6.2 to +12.7) | 761 |
| DE, DT, NT | Next season | Pressures per dropback | 23.8% | Pressure rate (beside past sacks) | **+21.6%** (+16.6 to +26.1) | 761 |
| DE, DT, NT | Next game | Sacks per dropback | 1.3% | Pressure rate to date | **+1.2%** (+0.8 to +1.6) | 15,198 |
| OLB | Next season | Sacks per dropback | 14.3% | Pressure rate | **+15.1%** (+7.3 to +21.9) | 283 |
| OLB | Next season | Pressures per dropback | 27.4% | Pressure rate (beside past sacks) | **+37.5%** (+30.0 to +44.7) | 283 |
| OLB | Next game | Sacks per dropback | 3.4% | Pressure rate to date | **+1.4%** (+0.8 to +2.0) | 5,961 |
| RB | Next season | Yards per carry | 4.7% | Yards after contact | +3.2% (-0.9 to +7.4) | 208 |
| RB | Next season | Yards per carry | 4.7% | Yards over expected (NGS) | **-1.3%** (-2.3 to -0.4) | 208 |
| RB | Next game | Yards per carry | 1.4% | Either, or both | 0.0% (-0.2 to +0.2) | 4,114 |
| QB | Next season | Completion rate | 16.6% | Completion over expected | -1.3% (-3.3 to +0.4) | 222 |
| QB | Next game | Completion rate | 4.1% | Completion over expected | +0.2% (-0.1 to +0.4) | 3,770 |

**F7. For pass rushers, pressures forecast sacks better than sacks do.** Adding a rusher's pressure rate to his past sack rate removes 9.4% more of the error in next season's sacks for defensive linemen and 15.1% for outside linebackers. It also helps a little game to game (+1.2%, +1.4%). This is the lower-noise outcome paying exactly as the CEO bet: the luck at the finish (a sack or not) washes out, and the pressure underneath carries over.

**F8. For runners, a measure that repeats doesn't necessarily pay.** A back's yards per carry next season is barely forecastable: his own past removes 4.7% of the league average's error, and a single game's removes almost none (1.4%). Yards after contact adds +3.2% for next season, but the interval touches zero. Yards over expected makes it worse (-1.3%), even though it repeats 0.28. What repeats in it isn't what next season's yards per carry needs, because next season's yards also depend on next season's line. The CEO's reading still fits. The runner's part (yards after contact) is the only one with a hint of value; the rest is the line, and the line changes.

**F9. For QBs, completion over expected adds nothing to the completion rate itself** (-1.3% next season, +0.2% next game). The plain rate already carries the skill. Completion over expected may still be the better input for a model that also knows the receivers and the depth of the throws, since those are what it removes.

**H77, pays?** **In part.** Defensive linemen yes (+9.4% next season, the interval clear of zero); runners no. Real? Partly, from the first look.

Claude's expectations, scored:

| Bet | Claude | Result |
|---|---|---|
| Runners, next season: yards after contact adds 1%+ | 55% | +3.2%, but the interval touches zero: unclear |
| Runners, next season: yards over expected adds 1%+ | 50% | **Failed** (-1.3%) |
| Runners, next game: anything adds 0.5%+ | 30% | Failed (0.0%), as expected |
| QBs, next season: completion over expected adds 1%+ | 45% | **Failed** (-1.3%) |
| QBs, next game | 30% | Failed (+0.2%) |
| Pass rushers, next season: pressures add 5%+ to sacks | 80% | **Held** (+9.4%, +15.1%) |
| Pass rushers, next game: 1%+ | 60% | **Held** (+1.2%, +1.4%) |
| H77's pays? as worded (both groups) | 45% | In part |

## Third look: H78 to H83 and I89 (written before the run, 2026-11-20)

The CEO, 2026-11-20: "you can run all of those together." The CEO's odds were given before this section (HUNCHES.md). Same seasons and vault rule as the first look; the repeat, reliability and share-kept measures are the first look's. All are discovery.

| # | Design | Pass rule | CEO | Claude |
|---|---|---|---|---|
| H78 | Running backs who change teams (20+ carries in the old season, 2018 on). Target: his share of the new team's running-back carries next season. Three forecasts, held out by season: **habit** (his old share and the new backfield's top back's share last season); **who** (his old share and the share last season of the backs who stay); **who and how good** (who, plus his own and the staying backs' yards after contact per carry, as the CEO chose) | Held if "who and how good" beats "habit" with the interval above zero **and** beats "who" (how good adds) | 30% | 45%; who beats habit 70%; how good adds 30% |
| H79 | Wide receivers' plain catch rate (catches over targets), 40+ targets in both seasons, against catches over expected | Held if it repeats at least as much as catches over expected and movers keep half | 40% | 60% |
| H80 | Outside linebackers' role from their own numbers: **rush share** = pressures / (pressures + coverage targets), per dropback on the field. (a) Two roles: 60%+ of outside-linebacker seasons fall outside the middle third (rush share under 1/3 or over 2/3). (b) Within the rushers (over 2/3), the pressure rate's share kept. (c) The rush share's own share kept for movers, outside against inside linebackers | (a) for the roles; "something because of the roles" held if (b) movers keep under 80% within rushers **or** (c) outside linebackers keep 0.15 less of their role than inside linebackers when they move | 90% roles; 60% something | 85% roles; 65% that rushers still keep 75%+; 60% that outside linebackers' roles move more |
| H81 | Defensive backs (CB, FS, SS on the field map), PFR's coverage charting, 30+ targets in both seasons: catch rate allowed, yards per target, passes defensed per target (play-by-play), interceptions per target, throw depth against | Held if at least three of the five repeat 0.2+ season to season and movers keep half | 50% | 25% |
| H82 | Sacks per pressure (participation's pressure flag, 2016 on) for QBs who move, against the same rate for linemen who move (the team's sacks per pressure on his dropbacks); and QBs' pressure rate against their sacks per pressure | Held if QB movers keep clearly more of sacks per pressure than lineman movers do (0.25+ more), and more than they keep of their pressure rate | 60% | 70% |
| H83 | Running backs, 80+ carries in both seasons: broken tackles per carry (PFR, 2018 on); on runs he's tackled after the line, the share needing two or more tacklers (play-by-play); the same before the line | Held if broken tackles or tacklers needed repeat 0.2+ and movers keep half | 60% | 55% |
| I89 | Time to throw (participation, 2016 on) and throw depth (air yards per attempt): QB movers' share kept against linemen's (the team's time to throw on his dropbacks); for depth, against receivers' (retro 2: receivers keep 85% of their target depth) | Time to throw is the QB's if QB movers keep 60%+ and linemen under 30% | (a question) | 70% time to throw is the QB's; 60% depth is the QB's more than the receivers' |

### Third look: the results ([`explore/third_look.py`](explore/third_look.py), output [`third_look.txt`](explore/third_look.txt))

**One change from the plan, made before reading any verdict:** every repeat and share kept below is computed after taking each season's league average out of both seasons. The first run showed sacks per pressure repeating 0.61 for QBs and 0.63 for linemen, and almost all of that was the league's level moving between seasons: participation's pressure flag changed source in 2023, and charting of tackles drifts too. "Raw" is the old number; the verdicts use the demeaned one. Nothing else moved by more than 0.04.

| # | Measure | Pairs (movers) | Raw repeat | Repeat (90%) | Movers keep |
|---|---|---|---|---|---|
| H79 | WR plain catch rate | 547 (113) | 0.44 | **0.45** (0.38-0.51) | **71%** |
| H79 | WR catches over expected (for comparison) | 547 (113) | 0.26 | 0.27 (0.18-0.35) | 47% |
| H80 | OLB role (rush share) | 283 (80) | 0.85 | 0.86 (0.80-0.90) | **106%** |
| H80 | ILB role (rush share) | 295 (71) | 0.76 | 0.76 (0.37-0.88) | **27%** |
| H80 | OLB pressure rate, all (the first look's 97%) | 283 (80) | 0.72 | 0.72 (0.65-0.77) | 96% |
| H80 | OLB pressure rate, rushers only | 164 (51) | 0.36 | **0.34** (0.21-0.44) | **14%** |
| H81 | DB catch rate allowed | 721 (172) | 0.20 | 0.21 (0.14-0.27) | 59% |
| H81 | DB yards per target | 721 (172) | 0.14 | 0.15 (0.07-0.21) | -22% |
| H81 | DB passes defensed per target | 721 (172) | 0.19 | 0.19 (0.13-0.24) | 199% |
| H81 | DB interceptions per target | 721 (172) | 0.29 | 0.29 (0.22-0.36) | 137% |
| H81 | DB throw depth against | 721 (172) | 0.38 | 0.37 (0.30-0.44) | 64% |
| H82 | QB sacks per pressure | 222 (41) | 0.61 | **0.20** (0.00-0.38) | **-46%** |
| H82 | Lineman (his team's, on his dropbacks) sacks per pressure | 814 (133) | 0.63 | 0.28 (0.17-0.38) | 79% |
| H82 | QB sacks per dropback | 222 (41) | 0.61 | 0.36 (0.22-0.59) | **149%** |
| H82 | Lineman sacks per dropback | 814 (133) | 0.64 | 0.28 (0.17-0.39) | 42% |
| H82 | QB pressures per dropback | 222 (41) | 0.45 | 0.47 (0.35-0.56) | 33% |
| H82 | Lineman pressures per dropback | 814 (133) | 0.30 | 0.28 (0.22-0.35) | 8% |
| I89 | QB time to throw | 222 (41) | 0.57 | 0.61 (0.51-0.68) | **36%** |
| I89 | Lineman time to throw | 814 (133) | 0.38 | 0.38 (0.33-0.43) | **-10%** |
| I89 | QB throw depth | 222 (41) | 0.45 | 0.42 (0.27-0.54) | **79%** |
| I89 | Lineman throw depth | 814 (133) | 0.38 | 0.35 (0.27-0.41) | 16% |
| H83 | RB broken tackles per carry (PFR) | 208 (46) | 0.22 | **0.22** (0.11-0.33) | **168%** |
| H83 | RB tackled after the line: share needing 2+ tacklers | 271 (59) | 0.66 | **0.46** (0.37-0.54) | **65%** |
| H83 | RB tackled at or behind the line: share needing 2+ | 271 (59) | 0.30 | 0.21 (0.10-0.31) | 107% |

"Movers keep" is the movers' repeat over the stayers' repeat. It has no interval here, and with 41 to 59 movers a single number can swing a lot: 149% and -46% for QBs mean "more than stayers" and "nothing", not those exact sizes.

**H78** (154 moving backs, 2019-2024; held out by season; gain = the share of the base forecast's squared error removed):

| Forecast of his new carry share | Against | Gain (90%) |
|---|---|---|
| **Who** (the backs who stay, and their shares) | Habit (the backfield's past split) | **+6.8%** (+1.3 to +12.0) |
| Who and how good (adds yards after contact per carry) | Habit | +6.0% (+0.8 to +11.0) |
| Who and how good | Who (does how good add?) | **-0.8%** (-3.3 to +1.6) |

**H80 (a), the roles:** 82% of outside linebackers' seasons fall outside the middle third of rush share (461 seasons; by fifths of rush share 108, 23, 55, 132, 143), so there are two groups: rushers and droppers, with few in between. Inside linebackers are one group: 98% are coverage-first (438 of 496 in the lowest fifth).

### What the third look found

**F10. A receiver's plain catch rate is more his than catches over expected is** (H79). It repeats 0.45 against 0.27 (the difference +0.18, +0.11 to +0.24), and movers keep 71% of it. Catches over expected takes out the throw's difficulty, and with it part of what the receiver brings (where he gets open, how deep). The plain rate keeps that.

**F11. The outside linebackers' 97% was mostly role** (H80). An outside linebacker is either a rusher or a dropper, and that role goes with him when he moves (kept 106%). The pressure rate across all of them travels because the role travels. Among the rushers only, the pressure rate repeats 0.34 and movers keep 14% (51 movers): how much a rusher gets home on his new team is much more the new team's. F9 and the second look's +15.1% on next season's sacks need this caveat: much of it is knowing who rushes. Inside linebackers' role does *not* travel (27%): how often an inside linebacker blitzes is the scheme's. That is the reverse of the CEO's coordinator reading, which put the scheme on the outside linebackers.

**F12. Coverage numbers repeat a little, and what repeats travels** (H81). Throw depth against (0.37), interceptions per target (0.29) and catch rate allowed (0.21, raw 0.20: right on the bar) repeat; yards per target (0.15) and passes defensed (0.19) don't reach 0.2. Movers keep half or more of all but yards per target. Depth against is likely his assignment (deep safety or press corner) more than his skill.

**F13. Sacks per pressure aren't a QB trait here; sacks per dropback are** (H82). Sacks per pressure, as pre-registered, repeat only 0.20 for QBs once the league's level is out, and QB movers keep nothing. Sacks per dropback repeat 0.36 and QB movers keep more than stayers, while linemen movers keep 42%. The pressure rate itself also follows the QB more than any lineman (QB 0.47, kept 33%; a lineman's 0.28, kept 8%): the QB makes some of his own pressure, by holding the ball. The pressure flag changed source in 2023, so the per-pressure rate is the shakiest number on this page.

**F14. Time to throw is partly the QB's and not the line's; depth is the QB's and the receivers'** (I89). QBs' time to throw repeats 0.61 but movers keep only 36%: the rest is the offense (the play-caller's concepts). The line's is the team's that season (a lineman who moves keeps nothing). Throw depth is a QB trait that travels (79%), close to receivers' 85% (retro 2's F1): both carry it, and the line doesn't (16%).

**F15. How a runner is brought down is his** (H83). Broken tackles per carry repeat 0.22 (a weak but real repeat) and movers keep more than stayers; the share of his tackles after the line that need two or more tacklers repeats 0.46 and movers keep 65%. Before the line, it repeats 0.21: that's more where the line lets him be hit.

**F16. A moving back's new share comes from who is left, not from the backfield's habit or how good anyone is** (H78). Knowing the staying backs' shares removes 6.8% more of the error than the backfield's past split. Adding how well everyone ran (yards after contact) adds nothing (-0.8%). Volume tells who gets the ball; quality doesn't, at least not in one season's yards after contact.

### The hunches

| # | Verdict | Why | Real? | Pays? |
|---|---|---|---|---|
| H78 | **Failed** as worded | Who beats habit (+6.8%), but how good adds nothing (-0.8%), and the claim needed both | Partly (who, not how good) | Partly: +6.8% on a held-out forecast of the new share, from who alone |
| H79 | **Held** | 0.45 against 0.27; movers keep 71% | Yes | Not tested as a forecast |
| H80 | **Held in part** | The roles exist (82% outside the middle third), and the 97% was role (within rushers, kept 14%). But the scheme sets the inside linebackers' role, not the outside ones' | Partly | Not tested |
| H81 | **Held, at the edge** | Three of five repeat 0.2+ (catch rate allowed 0.205, interceptions, depth) and travel; catch rate allowed is 0.199 before demeaning | Partly | Not tested |
| H82 | **Unclear** | The pre-registered sacks per pressure fails (QB kept -46%); sacks per dropback supports the CEO (QB 149% against linemen 42%); 41 QB movers and a flag that changed source | Unclear | Not tested |
| H83 | **Held** | Broken tackles 0.22, kept 168%; tacklers needed after the line 0.46, kept 65% | Yes | Not tested |
| I89 | Answered | Time to throw: partly the QB's (kept 36%), not the line's (-10%). Depth: the QB's (79%) and the receivers' (85%), not the line's (16%) | | |

### The odds, scored

| Bet | CEO | Claude | Result |
|---|---|---|---|
| H78 as worded | 30% | 45% | Failed |
| H78: who beats habit | | 70% | Held |
| H78: how good adds | | 30% | Failed |
| H79 as worded | 40% | 60% | Held |
| H80: the roles exist | 90% | 85% | Held |
| H80: we find something because of them | 60% | | Held (within rushers, kept 14%) |
| H80 as worded (with the coordinator part) | | 35% | In part |
| H80: rushers still keep 75%+ | | 65% | Failed (14%) |
| H80: outside roles move more than inside | | 60% | Failed (the reverse) |
| H81 as worded | 50% | 25% | Held at the edge |
| H81: depth against 0.3+ | | 45% | Held (0.37) |
| H81: passes defensed 0.2+ | | 45% | Failed (0.19) |
| H81: catch rate allowed 0.2+ | | 25% | Held at the edge (0.205) |
| H81: interceptions 0.2+ | | 10% | Held (0.29): set too low |
| H82 as worded | 60% | 70% | Unclear |
| H82: QB movers keep half of sacks per pressure | | 65% | Failed |
| H82: QBs keep less of pressure rate than of sacks per pressure | | 70% | Failed (33% against -46%) |
| H83 as worded | 60% | 55% | Held |
| H83: broken tackles 0.3+ | | 60% | Failed (0.22) |
| H83: tacklers needed after the line 0.2+ | | 35% | Held (0.46) |
| I89: time to throw is the QB's (60%+ kept, line under 30%) | | 70% | Failed (36%) |
| I89: depth is the QB's more than the receivers' | | 60% | Failed (79% against 85%) |
| I89: the line owns either | | 35% | Failed, as expected |

The CEO's as-worded bets: 4 of 6 held, at odds of 30% to 60%, which beats those odds. Claude's: 3 held and 1 in part, at 25% to 70%. Claude's coverage odds were too low (interceptions at 10%, the claim at 25%).

### The case against

- **Share kept has no interval**, and the mover groups are small (41 QBs, 46 to 59 RBs, 51 rushers). The verdicts that rest on one share kept (H82, H80 (b)) could flip with a different handful of movers.
- **Demeaning was added after the first run.** It was decided from the raw sacks numbers, before any verdict was read, and it moves only the sacks and tacklers rows; but it is a change made after seeing data.
- **The lineman's "team on his dropbacks"** is the team's rate on plays he was on the field, so a moving lineman joins a new line and a new QB at once: a low share kept says it isn't his, not whose it is.
- **Rush share uses coverage targets**, which depend on how often he's thrown at, not how often he drops. A dropper who is never targeted looks like a rusher.
- **H83's tacklers count** comes from play-by-play's tackler fields, which list at most two tacklers plus assists and are charted unevenly.

### Next steps (for the CEO's direction)

1. **Forecast tests for the new measures** (pays?): plain catch rate for next season's catches; broken tackles and tacklers needed for next season's yards per carry and yards after contact; sacks per dropback for next season's sacks.
2. **H82 again on one pressure source** (2023-2024 only, or 2016-2022 only) and with an interval on share kept (I90).
3. **The rushers' forecast** (I91): redo the second look's +15.1% within rushers only, to see how much of it is role.
4. I76 (the movers model) and drafting the brief.

### The CEO's answers to the third look (2026-11-20)

- **H82:** "H82; I meant sacks overall and I think that applies to a per drop back basis." On that reading H82 **held**: QB sacks per dropback repeat 0.36 and QB movers keep more than stayers (149%, 41 movers), while a lineman who moves keeps 42% of his team's. It is flagged in `HUNCHES.md`, because the pre-registered measure (sacks per pressure) failed and the reading came after the result. Claude's 70% on the claim as worded scores as held, with the same flag. I90 (one pressure source, an interval on share kept) still runs.
- **H80:** "H80; yes it does fit that theory of roles and usage."
- **The merge:** "Yes you can merge so far."
- **H84, a new hunch** (recorded open in `HUNCHES.md`, not tested in the reply that recorded it): "I have a hunch that if you used the context expert's estimates then we could measure the stability of these same metrics but instead relative to situation rather than relative to the league average. First we measure the "over expected x" for each x metric (pressure rate, catch rate, yards after contact) and then measure the carry over from a new team or to a new season. I would be very confident that this would find more significant results than just raw rate above league averages."

**Was this already done?** Only in part. The first look measured three skills over someone's situation expectation: completion over nflfastR's expected, catches over nflfastR's catch chance and rushing yards over Next Gen Stats' expected. It also ran context-live's own expectations for two of them (completion and rushing yards), but on one season pair only (2023 to 2024: 29 QBs and 37 backs). The third look's metrics (pressure rate, catch rate, sacks, time to throw, depth, coverage, broken tackles, tacklers needed) were all measured against the league's average for the season, not against the situation.

**What it needs first:** context-live's walk-forward history starts in 2023 (pressure and time to throw in 2024), and the 2025 vault is closed, so it has no season-to-season pairs for pressure at all. Context-live has expectations for pressure, sacks, completion (so catch rate and catch rate allowed), time to throw, throw depth and rushing yards, but none for yards after contact or broken tackles. The method is the CEO's choice with Claude (the charter's "football claims first, methods together").

