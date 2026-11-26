# Results: Skills over expected (`skill-over-expected`)

**Date:** 2026-11-25 · **Brief:** [BRIEF.md](BRIEF.md) (agreed 2026-11-20) · **Decision:** [0051](../../docs/decisions/0051-skill-over-expected-build.md) · **MLflow experiment:** `skill-over-expected`, run `94e6bd0e5059449e89a2b235056b40ed` ("skill-retro v1") · **History:** `outputs/skill-over-expected/94e6bd0e5059449e89a2b235056b40ed/history.parquet` (10,161 rows)

## In short

A retrospective table of 12 player-season traits in 15 position groups. Each trait has its raw rate, its rate shrunk toward the position (one stabilization constant per trait), a 90% interval for his true rate, next season's forecast with an 80% range, and an owner label (player or team) from the share movers keep. **Shrinking wins for every trait:** it removes 5% to 44% of the raw rate's error on next season's rate, every season. It beats the position's average for 10 of 15 trait-groups. The owner split (rung 3) doesn't pay across all players for any shipped trait. For players who change teams, though, the new team's rate pays for team-owned traits (+21% to +28%). On the yards yardstick only a QB's sack rate counts. The brief's success test passes in part (below). The vault stays closed (the CEO, 2026-11-25).

**Scorecard:** MLflow run 94e6bd0e (`report.txt`) · **Vault:** closed, not opened (the CEO, 2026-11-25: "No keep 2025 closed please") · **Versions tried:** three logged runs (fcd9a509: k per group; c671d2e2: the pooled-k rerun; 94e6bd0e: the same with the range and bootstrap fixes), and two no-log runs before them

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | Every champion beats all 20 copies with every input shuffled, against the position's average (the signal test). Every rung that ships clears the rung below on a 90% player-bootstrap interval. The split counts only for the linemen's rows (not shipped) |
| Calibration and range coverage | 80% ranges for next season's rate hold 72% to 86% after a conformal scale fit on earlier seasons (unscaled 55% to 74%; F117). Short: time to throw and interceptions (72%). The 90% interval for this season's true rate is a normal approximation and isn't checked against truth (nothing observes it) |
| Leakage | k, slopes, ranges and owner labels are fit on seasons up to the row's season only (a test changes the last season and checks earlier rows' k). One look-ahead: the split's "next team" is the main team next season, for in-season trades too (the case against). `as_of` is participation's release, the day after the Super Bowl |
| Football sanity | 2024 top and bottom 10 per trait in `report.txt`: Hutchinson, Hendrickson, Parsons, Garrett top DL pressures; St. Brown tops WR catch rate; Josh Allen has the lowest sack rate; Henry tops yards after contact and broken tackles. One flag: the OLB group's bottom is 4-3 off-ball linebackers (Spillane, Baun, Franklin), so read OLB traits with the role table |
| CEO spot-check | Pending |

**The brief's tests.**
- **Success, as written.** "Each shrunk trait forecasts next season's same rate better than last season's raw rate and the position's average." Against the raw rate: **held for all 15**. Against the average: **held for 10 of 15**. Five tie the average: inside linebackers' pressures and rush share (the team's), yards after contact, broken tackles, and catch rate allowed.
- **Pass rushers.** Their pressures keep their gain on next season's sacks: **held** (DL +11.0%, OLB +15.2%). The same for outside linebackers within the rusher role: **untestable** (44 rows in the role table's role; I170).
- **Failure test:** not met. Shrinking beats the raw rate everywhere.

## Hunch verdicts

The brief's hunches were closed at the exploration (HUNCHES.md). The build adds this evidence and changes no verdict:

| # | Hunch | Verdict | The build's evidence |
|---|---|---|---|
| H77 | The lower-noise outcomes predict better for runners and defensive linemen | in part (unchanged) | DL pressures +41% against the average and +11% to next season's sacks; runners' contact numbers tie the average (F118) |
| H79 | WR plain catch rate as the stat | held (unchanged) | Shrunk, +19% against the average, kept 71%; nothing on receiving yards (F116) |
| H80 | Outside linebackers are two roles | held (unchanged) | OLB rush share +79% against the average, kept 105%; the OLB group holds 4-3 off-ball linebackers (sanity lists) |
| H81 | DB coverage numbers carry over | (unchanged) | Throw depth against +16% and interceptions +6% against the average; catch rate allowed ties (F119) |
| H82 | Sacks follow the QB | held (unchanged) | QB movers keep 60% of sacks per dropback, a lineman's team 20% (I90) |
| H83 | Broken tackles and tacklers show a runner's skill | (unchanged) | The tacklers' share +17% against the average; broken tackles tie (F118) |

## Terms

- **Stabilization constant (k):** σ²/τ². It is the noise per chance (from each player's games) over the true spread of rates at the position. One per trait, pooled over its groups and fit on past seasons. A season with n chances is trusted n/(n + k) of the way from the position's mean (its **reliability**).
- **Shrunk rate (M1):** the rate pulled that way. **Second pull:** M1 times one more slope fit on earlier season pairs (I156).
- **Owner split (rung 3):** M1 plus the **team change** (his new team's shrunk rate at his position, less his old team's, him left out of both), which is zero for a player who stays.
- **Share kept:** movers' carry-over as a share of stayers' (`pcf.validation.owners.kept`). Half or more makes the trait the player's.
- **Flat pull:** one slope on the raw rate, the same for every player (no chances). A diagnostic rung.
- **Trait table:** this project's history.

All of these are in GLOSSARY.md.

## Findings

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 (F110) | Shrinking toward the position by one k per trait beats the raw rate for every trait | +5% to +44% of next season's error; seasons won 5 of 5 to 7 of 7 | strong | 15 trait-groups, targets 2018-2024 |
| R2 (F111) | His chances barely matter beyond one pull per trait | Shrunk against the flat pull ties for 13 of 15 | strong | All shipped traits |
| R3 (F112) | Within the role table's pass-rusher role, a DL's pressures still forecast next season's sacks | +13.0% (+5.0 to +20.8), 20 of 20 copies | suggestive (101 rows) | DL rushers; OLB too few |
| R4 (F113) | The second pull pays only for QB throw depth, DB throw depth against, and team-owned numbers | +8.3%, +5.9%; linemen +10% to +22%; the line +18.5% | strong | |
| R5 (F114) | A lineman's own numbers are his line's; only the owner split reads them | +4.0% and +4.7%, movers +19% to +21%; his shrunk pressure is 28% worse than the average | strong | OL, not shipped |
| R6 (F115) | For movers, a team-owned trait follows the new team | ILB pressures +20.7%, rush share +27.9% (66 movers) | suggestive | Movers |
| R7 (F116) | On the yards yardstick only a QB's raw sack rate counts | +0.66% (+0.21 to +1.11), 19 of 19 copies | strong | Passing board |
| R8 (F117) | Normal ranges need a conformal scale | 55-74% becomes 72-86% | strong | All traits |
| R9 (F118) | RB yards after contact and broken tackles repeat but don't beat the average; the tacklers' share does | +6.3% and +1.9% (span 0); +16.6% | strong | RB, 80+ carries |
| R10 (F119) | The per-position use and ignore map | FINDINGS.md's summary | strong | All positions |
| R11 | A QB's sacks per pressure follows him on the old provider's pressures; the new provider's two seasons say nothing | 2016-2022 movers keep 99% (49-157%, 32 movers); 2023-2024 196% (6 movers) | suggestive | QB (I90) |

The FINDINGS.md numbers are in brackets. Cite these as `skill-over-expected#R1` and so on (the exploration's F1-F6 keep their numbers).

## The ladder

Next season's centred rate. Each gain is the share of the base's squared error removed, weighted by next season's chances. 90% intervals come from resampling players.

| Trait, group | k (chances) | Shrunk vs raw | Champion vs average | Champion | Coverage | Owner (kept) |
|---|---|---|---|---|---|---|
| Pressures, DL | 132 dropbacks | +17.2% (+13.8 to +20.5) | +40.7% | M1 | 84% | player (82%) |
| Pressures, OLB | 132 | +15.1% (+10.5 to +18.9) | +54.9% | M1 | 84% | player (95%) |
| Pressures, ILB | 132 | +21.3% (+12.5 to +28.8) | +30.0% (span 0) | M1 | 83% | team (30%) |
| Rush share, OLB | 3 | +9.7% (+6.0 to +12.9) | +78.8% | M1 | 79% | player (105%) |
| Rush share, ILB | 3 | +4.6% (+2.7 to +6.5) | +43.4% (span 0) | M1 | 81% | team (29%) |
| Catch rate, WR | 74 targets | +26.1% (+22.5 to +29.8) | +19.0% | M1 | 84% | player (71%) |
| Sacks per dropback, QB | 255 | +23.8% (+16.9 to +30.0) | +24.7% | M1 | 82% | player (60%) |
| Throw depth, QB | 224 | +30.5% (+25.7 to +35.6) | +20.2% | second pull | 80% | player (75%) |
| Time to throw, QB | 77 | +14.2% (+10.0 to +17.9) | +38.1% | M1 | 72% | team (32%) |
| Yards after contact, RB | 281 carries | +36.4% (+28.7 to +43.0) | +6.3% (span 0) | M1 | 83% | player (137%) |
| Broken tackles, RB | 360 | +42.9% (+36.1 to +48.6) | +1.9% (span 0) | M1 | 76% | player (168%) |
| Tacklers' share, RB | 83 | +28.5% (+24.1 to +32.9) | +16.6% | M1 | 85% | player (65%) |
| Catch rate allowed, DB | 117 targets | +43.8% (+40.3 to +47.1) | +3.3% (span 0) | M1 | 81% | player (59%) |
| Interceptions, DB | 209 | +35.6% (+27.5 to +42.8) | +6.2% | M1 | 72% | player (131%) |
| Throw depth against, DB | 35 | +29.7% (+26.8 to +32.5) | +16.3% | second pull | 77% | player (64%) |

Rung by rung:

- **Rung 1, the raw rate.** This is the base.
- **Rung 2, the shrink (M1).** It clears the raw rate for all 15. It ties one flat pull for 13 of 15 (F111). It ships over the flat pull for its per-player interval (call 30).
  - **Takeaway carried forward:** a season's chances matter little within a floored set.
- **Rung 2b, the second pull.** It clears M1 for QB throw depth (+8.3%) and DB throw depth against (+5.9%), and ties the other 13.
  - **Takeaway:** a slope under 1 only pays where M1 under-pulls.
- **Rung 3, the owner split** (his M1 plus the team change). It counts for no shipped trait across all rows. Pressures, DL: +1.8% (spans 0). WR: +2.3%. It counts only for the linemen's rows (+4.0% and +4.7%, beating 20 of 20 copies).
  - **Takeaway:** stayers' teammates add noise; the split is for movers (F115).
- **The ladder stops at M1** for 13 trait-groups and at the second pull for 2.

**Beside the ladder, not shipped:**
- Pass rushers' sacks: shrunk beats raw by 31% to 38%, and pressures add 11% to 15%.
- A QB's pressure rate is his offense's (kept 13%). His sacks per pressure are his (kept 104%).
- A lineman's pressure and sacks belong to his line (kept 25% and 20%).
- The line's pressure over expected: shrunk beats raw by +20.5%, and the second pull adds +18.5%.
- I172, one k against k per group: ties for all three multi-group traits, so one k ships (call 24).

## Where it misses

The fixed miss lenses (`pcf.validation.misses`) aren't run: this is a season-level table, not a game forecaster. What the build saw:

- **Short ranges:** time to throw, interceptions (72%), QB sacks per pressure (74%). Rush share's small-chance third holds 67%.
- **Small groups:** inside linebackers and QBs have 35 to 66 movers, so every mover number for them is wide.
- **The OLB group mixes edge rushers and 4-3 off-ball linebackers** (roster position). Within-role tests need the role table, which leaves 44 OLB rusher rows.

## The case against

- **The gains over the raw rate are partly a floor artefact.** Every rate is noisy, so almost any pull toward the mean beats the raw rate. F111 says one flat pull does as well, so "shrinking works" is no claim about *how* to shrink. The claim that rests on the per-player k is the interval, and it isn't checked against truth.
- **The 10 of 15 against the average is the stronger claim, but it's centred.** Every rate has its position-season mean taken out, and next season's mean is not forecast. A downstream model needs the level from elsewhere.
- **Movers are few.** The owner labels for QBs (42 movers) and inside linebackers (71) have intervals that span the 50% line: time to throw's kept is 32% (−20% to 70%), and catch rate allowed's is 59% (4% to 125%). A different season set could flip them.
- **The next team is a small look-ahead.** The split uses his main team next season, which for an in-season trade is known only after the trade. It touches I171's movers numbers, not the shipped history, which has no split rung.
- **Three logged runs, and changes made after the first.** Rung 3 was redesigned, the flat rung added, k pooled and the ranges scaled, all after the first full run (decision 0051 calls 22-25). The odds were written before that run. The champions' choice only moved twice: OLB rush share from the second pull to M1, and ILB rush share from raw to M1, both from the pooled k, which I172's tie and the brief required. Every vault-free number here has been seen more than once.
- **PFR's charting is one charter's judgement** (pressures, contact, broken tackles), and the provider change in participation (2023) is handled only by centring each season.
- **What would check it:** the 2025 season. Participation's 2025 release is already out and the vault is closed by the CEO. The 2026 release (February 2027) would test the table fresh.

## Pitfalls

- **Count the floor on the right column.** A trait floored on another trait must count that trait's chances (its den), not its successes (QB sacks were counted at first, which emptied the QB table).
- **NaN isn't null in polars.** Drop and fill NaN explicitly (`fill_nan(None)`), or a range turns NaN and `drop_nulls` keeps it. The test caught it in the published ranges.
- **Shuffling a player's chances keeps the average pull,** so those copies can't test M1 against the raw rate (call 23).
- **polars group order isn't stable;** sort before a bootstrap (call 29).
- **The OLB roster label isn't the role.**

## Not looked at

- Over-expected versions of the traits (H84). The brief's table is plain centred rates, and context-retro's expectations are a separate input.
- Tight ends: no trait passed the exploration.
- The 2025 vault (closed).
- In-season updating. That is stabilization's cadence, not this table's.

## Could be improved

1. **Promote the k and shrink code to a shared module with stabilization** (rule j). The two projects now carry the same method twice (below).
2. **Read OLB traits by the role table's role** once more seasons give enough rushers.
3. **A movers-only feature downstream:** the new team's rate for team-owned traits (F115).
4. **Check the per-player 90% interval** against split-half truth (odd weeks against even).

## Don't redo

- The movers model (I76) as a share estimate: it ties the share kept where readable and can't read QBs.
- I112: the after-pressure part as a sack forecast loses to the plain rate.
- Per-group k (I172).
- The owner split on all rows for these traits.

## Overlap with stabilization

The same method, two projects. This build follows stabilization's exploration rather than inventing a second one:
- method 1's k = σ²/τ² from the game scatter;
- centring by position-season;
- the second pull (I156).

It doesn't build stabilization's deliverables.

**Where they overlap.** Both have pressures per pass snap, yards after contact, broken tackles and catch rate allowed.

**Where they differ:**

| | Stabilization | This table |
|---|---|---|
| Cadence | In season | Retrospective (the season's exact participation counts) |
| Base | The two pulls | M1, with the second pull only where it clears |
| Live stand-ins | Yes | No |

**Flags for the CEO:**
- **Code.** The k and shrink code is duplicated in `pcf.experts.skill_over_expected.traits`. Stabilization's build should make the shared module, and this table should then import it.
- **Results.** Stabilization found the second pull beats M1 for 12 of 18 rates. Here it clears M1 for only 2 of 15. Floors and centring differ, but a shared module should settle which pull is the default.

## Interface card

| | |
|---|---|
| **Inputs** | `play.pbp`, `play.participation`, `player_play.on_field`, `player_game.roster` and `pfr` (retrospective view), 2016-2024; roles-archetypes' role table (run 696a3f0b) for the pass-rusher tests |
| **Outputs** | `outputs/skill-over-expected/94e6bd0e5059449e89a2b235056b40ed/history.parquet`. Keys: gsis_id, season, trait, group. Columns: team, chances, rate, mu, rate_c, k, reliability, shrunk, shrunk_lo, shrunk_hi (90%, this season's true rate), shrunk_c, rung, next_c, next_q10 and next_q90 (80%, next season's centred rate; null in the first seasons), owner, share_kept, as_of, train_end, cadence |
| **Level of detail** | Player-season, per trait and position group (DL, OLB, ILB, WR, QB, RB, DB) |
| **Interval** | Seasons 2016-2024 (PFR's and participation's traits from 2018) |
| **Cadence** | Retrospective |
| **Known at** | The day after the Super Bowl (participation's release), for the whole season |
| **How to use it** | As last season's prior for a player's rate (rule m). Read `owner`: a team-owned trait (time to throw, ILB pressures and rush share) follows his team. For a mover, add his new team's rate at his position yourself (F115). Use the traits in FINDINGS' "use" column (F119). Not for yards beside participation, except a QB's sack rate (F116). Read OLB traits with the role table. Train only on this walk-forward history (rule e) |
| **Feeds** | line-play, qb-talent, stabilization (shared method), the fantasy projections, FINDINGS' map |

## Open questions for the CEO

1. **Rule k on the shrink.** M1 ties one flat pull for 13 of 15 traits. I kept M1 for its per-player interval (call 30). Veto it if the flat pull should ship instead.
2. **The overlap with stabilization:** should stabilization's build own the shared k and shrink module, with this table importing it?
3. **A football question:** are 4-3 outside linebackers off-ball linebackers (the ILB group) for every purpose, or only where the role table says they drop?
4. **The spot-check:** which finding or call?
