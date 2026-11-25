# Availability: the CEO's review (vault, spot-check, backlog), written before any result

**Date:** 2026-11-25 · **Results:** [RESULTS.md](RESULTS.md) (its "After the CEO's review" section) · **Decision:** [0047](../../docs/decisions/0047-availability-build.md) (calls 26 on)

## The CEO's answers (2026-11-25, word for word, relayed by the build chat)

> "We can open the 2025 vault to check the three forecasts. Yes Elos next build should definitely utilize games lost forecast. Can you spot check the team gain for elo. No vetoes from me. [...] Make sure to check the backlog of ideas and test the ones that fit into both of these builds, please."

- **Vault:** opened once, for the three shipped forecasts (`next_logit`, `next3_chain`, `rest_chain`). **Later the same day: kept closed** (the CEO, 2026-11-25, in the build session: "Keep it closed, actually"), after this session's permission check asked for the yes in the build session. Section 1's bets are left unscored.
- **I115:** Elo's next build uses availability's snap-weighted games-lost forecast (I131 settled the same way).
- **Spot-check:** R8, the team gain beside Elo.
- **Vetoes:** none on decision 0047's calls 1-25.
- **Backlog:** every open idea that fits this build is tested below.

Everything below was written and committed before the vault was opened and before any test in it was run. Odds are Claude's.

## 1. The vault (2025)

**What runs:** each champion exactly as registered (no change of code, settings or inputs), through the harness (`run forecast --open-vault --seasons 2025`): trained on 2016-2024, refit once before 2025's week 1, scored on 2025's regular season. The baselines are the rung 0 table for each, and method 1 (two parts) for the two chains, the rung each beat in the backtest. Shuffles: 100 for `next_logit`, 20 for each chain. The MLflow run is tagged `vault_opened`. Whatever comes out is reported as is; nothing is changed after.

**Pass rules and odds:**

| # | Bet | Pass rule | Chance | Expected size |
|---|---|---|---|---|
| V1 | Next game beats its table | `next_logit` against `next_table`, log loss, 90% interval by week clear of zero | 85% | +4% to +8% (backtest +6.18%) |
| V2 | Next 3 games beats method 1 | `next3_chain` against `next3_two`, range score, interval clear | 70% | +2% to +5% (backtest +3.55%) |
| V2b | Next 3 games beats its table | against `next3_table`, interval clear | 75% | +3% to +6% |
| V3 | Rest of season beats method 1 | `rest_chain` against `rest_two`, interval clear | 55% (one season: wide intervals; tie 40%) | +2% to +6% (backtest +5.59%) |
| V3b | Rest of season beats its table | against `rest_table`, interval clear | 60% | +2% to +5% |
| V4 | Real signal | `next_logit` beats 95+ of 100 shuffled refits; each chain 19+ of 20 | 90% | |
| V5 | No leak | all 10 leakage checks pass for all three | 95% | |
| V6 | Next game calibrated | calibration error under 3 points | 90% | about 0.3 points |
| V6b | Listed players' slope | 0.85 to 1.15 on listed rows | 65% | about 0.95 |
| V7 | Chains' ranges | q10-q90 holds 88-96% (the backtest's 91-94%) | 75% | |
| V8 | The vault holds | none of V1, V2, V3 has its interval below zero (worse) | 85% | |

**Not in the vault:** games played (any reason), the yardstick and the team output are scored on the yardstick's boards, which stop at 2024 (the crude forecaster's vault stays closed, the CEO, 2026-11-19).

## 2. Spot-check: R8, the team gain beside Elo

**What R8 says:** on the team rest-of-season board (team yards per game, 2019-2024), the snap-weighted games-lost forecast (offense, defense) adds +5.06% (+2.86 to +7.32) beside Elo and beats 19 copies (largest +3.82%); beside Elo plus I60's starters' forecast it ties (+1.27%, −0.25 to +2.62).

**The worry before looking:** the copies' own gain, +3.8%, is large. A copy shuffled within a week keeps that week's average, so it still says "late season" or "early season", and the base may lack that. If so, most of the +5.06% is a week effect any column with the same weekly average would give, and the real margin is the gap to the copies.

**What the spot-check runs (`build/spot_r8_run.py`):**
- S1: the within-week averages of the two columns, added to Elo alone: what the copies carry.
- S2: beside Elo plus those weekly averages, the real columns' gain, with 19 copies.
- S3: the same beside Elo, I60's starters' forecast and the weekly averages.
- S4: the forecast split by who is missing: QB, RB/WR/TE, offensive line, defense. Which part carries the gain beside I60's starters' forecast?
- S5: offense and defense apart (team yards gained is the offense's: does the defense's side add anything?).
- S6: per season, and the correlation of the forecast with I60's starters' forecast.
- S7: the leak audit: the weights (earlier games only), the forecast's moment against the board's, the fill of missing values, the tally to date.

| # | Bet | Chance | Expected size |
|---|---|---|---|
| S1 | The weekly averages alone add 2%+ beside Elo | 70% | about +3.5% |
| S2 | Beside Elo + weekly averages the real columns still add, interval clear | 55% | +0.5% to +2.5% |
| S3 | Beside Elo + I60's starters + weekly averages they tie | 65% | |
| S4 | The part beyond I60's starters is the line and the defense, and it ties | 60% | |
| S5 | The offense's side carries the gain; the defense's ties | 75% | |
| S6 | Positive in 4+ of 6 seasons | 60% | |
| S7 | No leak found | 85% | |

## 3. The backlog that fits

Read on 2026-11-25: every open idea in `IDEAS.md`, the brief's backlog (I29, I30, I50, I121; I49, I51 stay with participation and vacated-opportunity) and decision 0044's routing. Six fit this build's data and outputs; each keeps the odds already written in `IDEAS.md` (scored as written), and gets its pass rule here.

| Idea | Fits because | Not here |
|---|---|---|
| I29 long drives tire the defense | routed here (injury-fatigue replaced) | |
| I30 pass defense after a long first half | routed here | |
| I50 fatigue shows as who is on the field | routed here | |
| I128 a team's habit of listing players Questionable | the active family's rows | |
| I129 the healthy rate counts releases | test 2's rows | |
| I130 a narrower chain | the chains' walks | |
| I127 injury-wrecked teams rebound | | needs a team-strength season-start rating: team-efficiency or Elo's build |
| I131 / I115 | | Elo's next build (the CEO's answer above) |
| I55 first game back | | participation's champion and target |
| I120 a QB's touchdowns as a mixture | | td-expert's counts (availability's chain gives the chance he keeps playing) |
| I4, I6, I14, I49, I51, I97 | | products, participation, vacated-opportunity, or a data check first |

**Shared rules:** intervals resample whole games (play level) or whole weeks (forecasts); 90% level; ties go to the simpler side (rule k); a forecast gain counts only with its interval clear of zero and beating 19 copies shuffled within the week.

### I29: long drives tire the defense
- **Real?** On every defensive player-play (true participation, 2016-2024, runs and passes), a logistic of the player's injury on the play's number in the drive (1-3, 4-6, 7-9, 10+), against the same with controls: play type, tacklers, tackle behind the line, yards, down, field position, quarter, score, the defense's season strength (EPA per play allowed in its other games), and snaps since the defense last rested (its plays on the field since its offense last had 4+ plays, or the half began). The rise is the 7+ against 1-3 rate ratio.
- **Odds (IDEAS.md, 2026-11-15):** low (60%) that the rise shrinks by half or more once play type and field position are held fixed. Side bet now: 55% that the controlled 7+ ratio's interval still clears 1.
- **Pays?** A defender's snaps on long-drive plays (7+) in his last game, beside `next_logit`'s log-odds, in a walk-forward logistic on next game's health absence (defenders, 2018-2024): log loss against `next_logit` recalibrated alone, 19 copies. 15% that it counts; expected size under +0.2%.

### I30: pass defense after a long first half
- **Real?** On second-half dropbacks, EPA per play on the defense's first-half snaps faced (per +10), with the day's matchup held fixed (the offense's first-half EPA per play against this defense), both teams' season strength in their other games, score, win probability, down, distance and field position. Pass rush (sack or hit rate) and coverage (EPA on non-sack dropbacks) apart; runs as the check that should show nothing.
- **Odds (IDEAS.md, 2026-11-15):** medium (75%) that it fails: with the matchup held fixed, the per-10-snaps effect's interval covers zero or falls under +0.01.

### I50: fatigue shows as who is on the field
- **Real?** Each defensive play's share of the 11 on the field who aren't the team's regulars (under 60% of its defensive snaps that season), by play in the drive and by first-half snaps faced, holding the score, quarter and win probability fixed (blowouts bring backups). By group: line, linebackers, backs.
- **Odds (IDEAS.md, 2026-11-15):** medium (75%) that the backup share rises 2 to 4 points late in long drives (10+ against 1-3), mostly the line; low (60%) that it explains I30's effect, read here as: with the backup share held fixed, I30's coefficient falls by half or more (moot if I30 fails).

### I128: a team's habit of listing players Questionable
- **Test:** each team's earlier Questionable listings (every position, every earlier week and season) and how often those players were health-absent, shrunk to the league's rate with 30 listings. On Questionable QB/RB/WR/TE rows, a walk-forward logistic of active on participation's `active` log-odds plus the habit's log-odds gap, against the same without the habit (participation's recalibrated), 2018-2024.
- **Odds (IDEAS.md, 2026-11-25):** 45% that the slope reaches 0.85 and the log loss improves clearly on Questionable rows. Side bet: 35% that the log loss alone improves clearly and beats 19 copies.

### I129: the healthy rate counts releases
- **Test:** the healthy share (games played over games not health-absent, in the rest of the season) fit walk-forward by season with a logistic on his record: the shrunk healthy rate, position, his last game's snap share, his season share, age, games this season. Games played = that rate times the chain's share not absent. Scored like test 2 (2019-2024, the receiving board's rows), against I60 and against the shipped composite.
- **Odds (IDEAS.md, 2026-11-25):** 65% that it adds 2%+ more of I60's squared error (to 16.4%+), with the interval against the shipped composite clear of zero.

### I130: a narrower chain
- **Before the test, a doubt:** the chain's counts are whole games with most of the mass at 0. A calibrated forecast of whole numbers with a spike at 0 holds more than 80% between its q10 and q90 by construction (the q10 is 0, and a whole-number q90 sits at or above the 90th percentile). So 91-94% may be what a calibrated chain must show, not too wide. Checked first by the share above q90 (calibrated: at most 10%) and a randomized PIT (calibrated: flat).
- **Test as written:** the chain with a temperature on its move chances (each row's chances raised to 1/τ and renormalized), τ chosen on the last training season from 0.7, 0.85, 1, 1.2, 1.5 by range score, then refit on every training season; walked 2017-2024 like the champions.
- **Odds (IDEAS.md, 2026-11-25):** 55% that coverage lands in 75-85% and the range score improves 1%+. Side bet now, after the doubt: 15%.
