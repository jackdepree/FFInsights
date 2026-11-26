# Results: Skills over expected (`skill-over-expected`)

**Date:** 2026-11-25, rerun 2026-11-26 · **Brief:** [BRIEF.md](BRIEF.md) (agreed 2026-11-20) · **Decision:** [0051](../../docs/decisions/0051-skill-over-expected-build.md) · **MLflow experiment:** `skill-over-expected`, run `6ecfce2ac8c341c5a505a71c0c9365fd` ("skill-retro v1") · **History:** `outputs/skill-over-expected/6ecfce2ac8c341c5a505a71c0c9365fd/history.parquet` (10,161 rows) · **Spot-check:** [SPOT_CHECK.md](SPOT_CHECK.md)

## In short

A retrospective table of 12 player-season traits in 15 position groups. Each trait comes with:
- its raw rate;
- its rate shrunk toward the position (one stabilization constant per trait);
- a 90% interval for his true rate;
- next season's forecast, with an 80% range;
- an owner label (player or team), from the share movers keep.

**What the build found:**
- **Shrinking wins for 14 of 15 trait-groups.** It removes 5% to 44% of the raw rate's error on next season's rate, every season. Inside linebackers' rush share ties.
- **Against the position's average,** the champion wins for 10 of 15.
- **The owner split (rung 3) pays across all players** only for outside linebackers' pressures (+8.0%). Since the reclassification below, that group is edge players.
- **Players who change teams** fall back toward the average harder than stayers on team-owned traits. Their new team's rate adds nothing beyond that harder pull, except for linemen and edge pressure (the spot-check).
- **On the yards yardstick,** only a QB's sack rate counts.

The brief's success test passes in part (below). The vault stays closed (the CEO, 2026-11-25).

**Rerun 2026-11-26 (decision 0051 call 31).** After the CEO's answer, 4-3 off-ball outside linebackers count as inside linebackers, by the role table's role: 472 of 1,280 OLB player-seasons move. Only the OLB and ILB rows changed (below). The shrink ships over one flat pull, an exception to rule k, with its revert written out (call 30; the CEO: no vetoes).

**Scorecard:** MLflow run 6ecfce2a (`build/report.txt`) · **Vault:** closed, not opened (the CEO, 2026-11-25: "No keep 2025 closed please") · **Versions tried:** four logged runs, and two no-log runs before them:
- fcd9a509: k per group;
- c671d2e2: the pooled-k rerun;
- 94e6bd0e: the same, with the range and bootstrap fixes;
- 6ecfce2a: off-ball OLBs as ILB.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | Every champion beats all 20 copies with every input shuffled, against the position's average (the signal test). Every rung that ships clears the rung below on a 90% player-bootstrap interval. The split counts for the linemen's rows (not shipped) and for OLB pressures |
| Calibration and range coverage | 80% ranges for next season's rate hold 69% to 85%, after a conformal scale fit on earlier seasons (unscaled 55% to 74%; F117). Short: OLB rush share (69%), time to throw and interceptions (72%). The 90% interval for this season's true rate is a normal approximation, and isn't checked against truth (nothing observes it) |
| Leakage | k, the slopes, the ranges and the owner labels are fit on seasons up to the row's season only (a test changes the last season and checks earlier rows' k). One look-ahead: the split's "next team" is his main team next season, for in-season trades too (the case against). `as_of` is participation's release, the day after the Super Bowl. The role table that regroups linebackers is the same season's, which a retrospective table may read |
| Football sanity | The 2024 top and bottom 10 per trait are in `report.txt`. Hutchinson, Hendrickson, Parsons and Garrett top DL pressures; St. Brown tops WR catch rate; Josh Allen has the lowest sack rate; Henry tops yards after contact and broken tackles. The OLB group's bottom is now edge players (Lorenzo Carter, Chaisson), not off-ball linebackers. **One flag:** the ILB top for pressures and rush share holds hybrids the role table calls off-ball (Tillman, Patrick Jones II, Van Ginkel, Jennings). These are the rule's misfiles (call 31), about 6% of the rows |
| CEO spot-check | Done: the inside linebackers' movers result ([SPOT_CHECK.md](SPOT_CHECK.md)). It changed the advice for movers, not the table (call 33) |

**The brief's tests.**
- **Success, as written:** "Each shrunk trait forecasts next season's same rate better than last season's raw rate and the position's average."
  - **Against the raw rate: held for 14 of 15.** Inside linebackers' rush share ties (+5.6%, −8.4 to +16.8), so its champion is the raw rate. It cleared before the reclassification (+4.6%).
  - **Against the average: held for 10 of 15 champions.** Five tie: both rush shares, yards after contact, broken tackles and catch rate allowed. For OLB pressures, what the history carries is M1, and M1 alone ties the average (+13.9%, −0.5 to +27.8). The split is what clears, so the history's count is 9 of 15.
- **Pass rushers:** their pressures keep their gain on next season's sacks.
  - **DL: held** (+10.8%).
  - **All OLBs: failed** after the reclassification (+3.8%, −1.5 to +9.0; it was +15.2%). The OLB group's sacks are noise from season to season (r 0.03).
  - **Within the pass-rusher role:** DL +13.2% (+5.3 to +20.9). OLB is **untestable** (31 rows). DL and OLB rushers together give +16.9% (+9.2 to +24.4) (I170).
- **Failure test:** not met. Shrinking beats the raw rate almost everywhere.

## Hunch verdicts

The brief's hunches were closed at the exploration (HUNCHES.md). The build adds this evidence and changes no verdict:

| # | Hunch | Verdict | The build's evidence |
|---|---|---|---|
| H77 | The lower-noise outcomes predict better for runners and defensive linemen | in part (unchanged) | DL pressures +41% against the average and +11% on next season's sacks; runners' contact numbers tie the average (F118) |
| H79 | WR plain catch rate as the stat | held (unchanged) | Shrunk, +19% against the average, kept 71%; nothing on receiving yards (F116) |
| H80 | Outside linebackers are two roles | held (unchanged) | Moving the off-ball ones to ILB (call 31) takes OLB rush share from +79% against the average to +13% (spans 0). Most of its spread was the two roles. What's left is kept 106% |
| H81 | DB coverage numbers carry over | (unchanged) | Throw depth against +16% and interceptions +6% against the average; catch rate allowed ties (F119) |
| H82 | Sacks follow the QB | held (unchanged) | QB movers keep 60% of sacks per dropback, a lineman's team 20% (I90) |
| H83 | Broken tackles and tacklers show a runner's skill | (unchanged) | The tacklers' share +17% against the average; broken tackles tie (F118) |

## Terms

- **Stabilization constant (k):** σ²/τ², the noise per chance (from each player's games) over the true spread of rates at the position. There is one per trait, pooled over its groups and fit on past seasons. A season with n chances is trusted n/(n + k) of the way from the position's mean; that share is its **reliability**.
- **Shrunk rate (M1):** the rate pulled that way. **Second pull:** M1 times one more slope, fit on earlier season pairs (I156).
- **Owner split (rung 3):** M1 plus the **team change**. The team change is his new team's shrunk rate at his position less his old team's, with him left out of both, so it is zero for a player who stays.
- **Share kept:** movers' carry-over as a share of stayers' (`pcf.validation.owners.kept`). Half or more makes the trait the player's.
- **Flat pull:** one slope on the raw rate, the same for every player (no chances). It is the revert for rung 2 (call 30).
- **Off-ball OLB:** an OLB player-season that the role table calls a box linebacker or a base defensive back. It counts as an inside linebacker (call 31).
- **Trait table:** this project's history.

All of these are in GLOSSARY.md.

## Findings

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 (F110) | Shrinking toward the position by one k per trait beats the raw rate for 14 of 15 trait-groups | +5% to +44% of next season's error; seasons won 4 of 4 to 7 of 7. ILB rush share ties (+5.6%) | strong | 15 trait-groups, targets 2018-2024 |
| R2 (F111) | His chances barely matter beyond one pull per trait | Shrunk against the flat pull ties for 14 of 15; the flat pull leans ahead for 12 | strong | All shipped traits |
| R3 (F112) | Within the role table's pass-rusher role, a DL's pressures still forecast next season's sacks | +13.2% (+5.3 to +20.9), 20 of 20 copies; DL and OLB rushers together +16.9% | suggestive (101 rows) | DL rushers; OLB too few |
| R4 (F113) | The second pull pays only for QB throw depth, DB throw depth against, and team-owned numbers | +8.3%, +5.9%; linemen +10% to +22%; the line +18.5% | strong | |
| R5 (F114) | A lineman's own numbers are his line's; only the owner split reads them | +4.0% and +4.7%, movers +19% to +21%; his shrunk pressure is 28% worse than the average | strong | OL, not shipped |
| R6 (F115) | A mover's team-owned trait falls back toward the average more than a stayer's; his new team's rate adds beyond that only for linemen | ILB movers: the split +9.4% and +11.0%, but a shuffled team does as well, and the second pull alone gives +10.4% and +12.4% (the split adds −1.2% and −1.7% beyond it). WR and DB the same. Linemen: +19.6% and +23.2% beyond the second pull | suggestive (80 ILB movers) | Movers |
| R7 (F116) | On the yards yardstick only a QB's raw sack rate counts | +0.66% (+0.21 to +1.11), 19 of 19 copies | strong | Passing board |
| R8 (F117) | Normal ranges need a conformal scale | 55-74% becomes 69-85% | strong | All traits |
| R9 (F118) | RB yards after contact and broken tackles repeat but don't beat the average; the tacklers' share does | +6.3% and +1.9% (span 0); +16.6% | strong | RB, 80+ carries |
| R10 (F119) | The per-position use and ignore map | FINDINGS.md's summary | strong | All positions |
| R11 | A QB's sacks per pressure follows him on the old provider's pressures; the new provider's two seasons say nothing | 2016-2022 movers keep 99% (49-157%, 32 movers); 2023-2024 196% (6 movers) | suggestive | QB (I90) |

The FINDINGS.md numbers are in brackets. Cite these as `skill-over-expected#R1` and so on (the exploration's F1-F6 keep their numbers). R6 was rewritten by the spot-check. It first read "for movers, a team-owned trait follows the new team" (ILB +20.7% and +27.9%, 66 movers).

## The ladder

The target is next season's centred rate. Each gain is the share of the base's squared error removed, weighted by next season's chances. The 90% intervals come from resampling players. The OLB and ILB rows are after call 31's reclassification.

| Trait, group | k (chances) | Shrunk vs raw | Champion vs average | Champion | Coverage | Owner (kept) |
|---|---|---|---|---|---|---|
| Pressures, DL | 178 dropbacks | +18.1% (+13.8 to +22.1) | +41.3% | M1 | 85% | player (82%) |
| Pressures, OLB | 178 | +23.0% (+16.6 to +27.9) | +20.8% (M1 alone +13.9%, span 0) | split (history: M1) | 84% | player (53%, 2% to 108%) |
| Pressures, ILB | 178 | +24.0% (+12.9 to +33.0) | +34.8% (+3.8 to +53.4) | M1 | 84% | team (47%) |
| Rush share, OLB | 10 | +12.6% (+7.9 to +16.9) | +13.0% (span 0) | M1 | 69% | player (106%) |
| Rush share, ILB | 10 | +5.6% (span 0) | +43.3% (span 0) | raw | 80% | team (45%) |
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

Before the reclassification (run 94e6bd0e):
- **OLB:** pressures +54.9% against the average (owner player, 95%); rush share +78.8% (105%).
- **ILB:** pressures +30.0% (span 0; team, 30%); rush share M1 +43.4% (span 0; team, 29%).
- **k:** 132 for pressures and 3 for rush share.

Rung by rung:

- **Rung 1, the raw rate.** This is the base.
- **Rung 2, the shrink (M1).** It clears the raw rate for 14 of 15. It ties one flat pull for 14 of 15 (F111), and ships over the flat pull for its per-player interval. That is an exception to rule k, written up with its one-line revert (`traits.SHRINK = "flat"`) and what would trigger it in [decision 0051 call 30](../../docs/decisions/0051-skill-over-expected-build.md).
  - **Takeaway carried forward:** within a floored set, a season's chances matter little.
- **Rung 2b, the second pull.** It clears M1 for QB throw depth (+8.3%) and DB throw depth against (+5.9%), and ties the other 13.
  - **Takeaway:** a slope under 1 only pays where M1 under-pulls.
- **Rung 3, the owner split** (his M1 plus the team change).
  - **It counts for one shipped group: OLB pressures,** +8.0% (+2.1 to +12.9) over M1, beating the 20 copies (best +5.1%). It also beats the second pull (+2.9%, +0.7 to +5.6; call 34).
  - **For no other shipped group:** DL pressures +0.6% (spans 0), WR +2.3%.
  - **It counts for the linemen's rows** (+4.0% and +4.7%, beating 20 of 20 copies).
  - **The history carries M1 for OLB pressures,** because the split needs next season's team (call 21).
  - **Takeaway:** stayers' teammates add noise. For movers, see the spot-check (R6).
- **The ladder stops** at M1 for 12 trait-groups, at the second pull for 2, and at raw for 1. The split sits above M1 for OLB pressures.

**Beside the ladder, not shipped:**
- **Pass rushers' sacks:** shrunk beats raw by 31% to 37%. Pressures add 11% for DL; for all OLBs they now tie.
- **A QB's pressure rate** is his offense's (kept 13%). His sacks per pressure are his (kept 104%).
- **A lineman's pressure and sacks** belong to his line (kept 25% and 20%).
- **The line's pressure over expected:** shrunk beats raw by +20.5%, and the second pull adds +18.5%.
- **I172,** one k against a k per group: ties for all three multi-group traits, so one k ships (call 24).

## The spot-check (the CEO's pick: inside linebackers' movers)

The full walk-through, with the odds written first and then scored, is in [SPOT_CHECK.md](SPOT_CHECK.md).

1. **The gain is real, but the reading changes.** After the reclassification, the movers' gain still clears: pressures +9.4%, rush share +11.0% (80 movers).
2. **It doesn't need the right team.** Moving the new team's part to a random inside linebacker that season scores as well (the copies' median is +9.7% and +11.8%).
3. **The second pull alone gives it** (+10.4% and +12.4%), and the split adds nothing beyond that pull.
4. **It isn't scheme.** The team change has no relation to how his rate moves (r −0.04 and 0.01).
5. **It leans on one season.** 2020 carries about half of it.
6. **The other movers results are the same harder pull:** WR catch rate and DB throw depth against.
7. **The new team adds beyond the harder pull only for offensive linemen** (+19.6% and +23.2%), and, checked afterwards, for OLB pressures (+10.8% for movers; a lead, I173).
8. **What ships:** the interface advice for movers. Nothing in the history.

My odds: 3 of 8 bets held (SPOT_CHECK.md). The 75% that it was scheme failed.

## Where it misses

The fixed miss lenses (`pcf.validation.misses`) aren't run, because this is a season-level table, not a game forecaster. What the build saw:

- **Short ranges:**
  - OLB rush share (69%);
  - time to throw and interceptions (72%);
  - QB sacks per pressure (74%).
- **Small groups:** after the reclassification, OLBs have 126 pairs and 34 movers. QBs have 35 movers and ILBs 80, so every mover number for them is wide.
- **The reclassification's misfiles:** about 6% of the OLB rows over a floor go the wrong way (call 31). Edge-ish hybrids sit at the top of the ILB pressure list.

## The case against

- **The gains over the raw rate are partly a floor artefact.** Every rate is noisy, so almost any pull toward the mean beats the raw rate. F111 says one flat pull does as well (its point estimates even lean ahead for 12 of 15), so "shrinking works" is no claim about *how* to shrink. The claim that rests on the per-player k is the interval, and it isn't checked against truth. That is why call 30 is written as a revertible exception.
- **The 10 of 15 against the average is the stronger claim, but it's centred.** Every rate has its position-season mean taken out, and next season's mean is not forecast. A downstream model needs the level from elsewhere.
- **Movers are few.** The owner labels for QBs (42 movers) and OLBs (56) have intervals that span the 50% line. Time to throw's kept is 32% (−20% to 70%); OLB pressures' is 53% (2% to 108%). A different season set could flip them.
- **The groups were changed after the results were seen.** The off-ball rule (call 31) came from the CEO's football answer, not from the numbers. Still, it moved OLB and ILB results a lot: OLB pressures against the average went from +54.9% to +13.9%, and OLB pressures' split went from not counting to the champion. So the OLB and ILB rows are a fifth look at the same seasons.
- **The OLB split is a lead, not a finding.** Its check against the second pull (call 34) was run after the result was seen, on 126 pairs.
- **The next team is a small look-ahead.** The split uses his main team next season, which for an in-season trade is known only after the trade. It touches the movers numbers and OLB pressures' champion choice, not the shipped history, which has no split rung.
- **Four logged runs, and changes made after the first.** All after the first full run (decision 0051 calls 22-25 and 31): rung 3 was redesigned, the flat rung added, k pooled, the ranges scaled, and the linebackers regrouped. The odds were written before that first run, and the spot-check's odds before the fourth. Every vault-free number here has been seen more than once.
- **PFR's charting is one charter's judgement** (pressures, contact, broken tackles). The provider change in participation (2023) is handled only by centring each season.
- **What would check it:** a season this table hasn't seen. Participation's 2025 release is already out, but the CEO has kept the vault closed. The 2026 release (February 2027) would test the table fresh.

## Pitfalls

- **Count the floor on the right column.** A trait floored on another trait must count that trait's chances (its den), not its successes. QB sacks were counted at first, which emptied the QB table.
- **NaN isn't null in polars.** Drop and fill NaN explicitly (`fill_nan(None)`), or a range turns NaN and `drop_nulls` keeps it. The test caught it in the published ranges.
- **Shuffling a player's chances keeps the average pull,** so those copies can't test M1 against the raw rate (call 23).
- **polars group order isn't stable,** so sort before a bootstrap (call 29).
- **The OLB roster label isn't the role.** Regroup with the role table (`traits.regroup`) before any linebacker trait.
- **A movers gain needs the harder-pull check.** Score the split against the second pull, not only against M1, or a harder pull looks like the new team (the spot-check).

## Not looked at

- Over-expected versions of the traits (H84). The brief's table is plain centred rates, and context-retro's expectations are a separate input.
- Tight ends: no trait passed the exploration.
- The 2025 vault (closed).
- In-season updating. That is stabilization's cadence, not this table's.

## Could be improved

1. **Move the k and pull code to stabilization's shared module** (call 32, rule j). This table then imports it.
2. **A movers-only pull** (I173): pull movers harder for team-owned traits, and test whether the new team adds for edge pressure on more seasons.
3. **Read OLB traits by the role table's role** once more seasons give enough rushers.
4. **Check the per-player 90% interval** against split-half truth (odd weeks against even). That is call 30's revert trigger (b).

## Don't redo

- The movers model (I76) as a share estimate: it ties the share kept where readable, and can't read QBs.
- I112: the after-pressure part as a sack forecast loses to the plain rate.
- Per-group k (I172).
- The owner split on all rows, for every shipped trait but OLB pressures.
- The new team's rate for movers' traits other than linemen's (the spot-check): use the second pull.

## Overlap with stabilization

It is the same method in two projects. This build follows stabilization's exploration rather than inventing a second one:
- method 1's k = σ²/τ², from the game scatter;
- centring by position-season;
- the second pull (I156).

It doesn't build stabilization's deliverables.

**Where they overlap:** both have pressures per pass snap, yards after contact, broken tackles and catch rate allowed.

**Where they differ:**

| | Stabilization | This table |
|---|---|---|
| Cadence | In season | Retrospective (the season's exact participation counts) |
| Base | The two pulls | M1, with the second pull only where it clears |
| Pull target | Last season's position mean | The same season's (a finished season) |
| Floors | `min_den` 10 | The brief's, per trait |
| Linebacker groups | Roster position | Off-ball OLBs as ILB (call 31, the one football reason) |
| Live stand-ins | Yes | No |

**The direction** (the CEO, 2026-11-26; decision 0051 call 32):
- **Stabilization owns the pull code**, and other experts use it.
- **The code stays the same across projects unless there's a good football reason.** The one here is the linebacker groups. The pull target and the floors are arguments, not differences in the method.
- **The package copy:** `pcf.experts.skill_over_expected.traits` holds it until stabilization's build moves it. A note for that build is in the roadmap.
- **Stabilization's own results:** its exploration found the second pull beats M1 for 12 of 18 rates. Here it clears M1 for only 2 of 15. Floors and centring differ. The shared module should settle which pull is the default.

## Interface card

| | |
|---|---|
| **Inputs** | `play.pbp`, `play.participation`, `player_play.on_field`, `player_game.roster` and `pfr` (retrospective view), 2016-2024. Roles-archetypes' role table (run 696a3f0b) for the linebacker groups (call 31) and the pass-rusher tests |
| **Outputs** | `outputs/skill-over-expected/6ecfce2ac8c341c5a505a71c0c9365fd/history.parquet`. Keys: gsis_id, season, trait, group. Columns: team, chances, rate, mu, rate_c, k, reliability, shrunk, shrunk_lo and shrunk_hi (90%, this season's true rate), shrunk_c, rung, next_c, next_q10 and next_q90 (80%, next season's centred rate; null in the first seasons), owner, share_kept, as_of, train_end, cadence |
| **Level of detail** | Player-season, per trait and position group (DL, OLB, ILB, WR, QB, RB, DB). ILB includes off-ball OLBs |
| **Interval** | Seasons 2016-2024 (PFR's and participation's traits from 2018) |
| **Cadence** | Retrospective |
| **Known at** | The day after the Super Bowl (participation's release), for the whole season |
| **How to use it** | **As a prior:** use it as last season's prior for a player's rate (rule m), and train only on this walk-forward history (rule e). **Owner:** read `owner`; a team-owned trait (time to throw, ILB pressures and rush share) follows his team. **Movers** (the spot-check, call 33): pull him harder rather than toward his new team. Use the second pull (M1's centred value times the trait's fitted slope). Add his new team's rate at his position only for linemen and edge pressure. **Which traits:** the ones in FINDINGS' "use" column (F119). Not for yards beside participation, except a QB's sack rate (F116). **Rung 2** is M1 by an exception to rule k; the revert is one line (`traits.SHRINK = "flat"`, decision 0051 call 30) |
| **Feeds** | line-play, qb-talent, stabilization (shared method), the fantasy projections, FINDINGS' map |

## Open questions for the CEO

Answered 2026-11-26 (decision 0051, calls 30-33):
1. **Rule k on the shrink:** "No vetoes from me, we should record the thought process and the exception for call 30 so we can always revert that decision in the future." Recorded in call 30, with a one-line switch.
2. **The overlap with stabilization:** "Yes stabilization should own the code for pulling rates toward the average, but that does not necessarily mean other experts can not use that code. The code should be consistent between projects unless there is a good football reason." Recorded in call 32.
3. **The 4-3 outside linebackers:** "Yes we can count those linebackers as middle/inside linebackers." Done by rule (call 31).
4. **The spot-check:** "Can you spot check the inside linebacker result?" Done ([SPOT_CHECK.md](SPOT_CHECK.md)).

Still open:
1. **Vetoes on calls 31-34**, before the merge.
2. **Stabilization's linebackers.** Should stabilization's build also count off-ball OLBs as ILB? It is the one football reason the two copies of the code differ.

## At the merge (2026-11-26)

The CEO, word for word: "Yes please merge skills over expected into main. No vetoes from me. No stabilization's build does not need to count off ball linebackers as inside linebackers for now."
