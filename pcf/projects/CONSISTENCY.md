# Consistency register: which measures are signal, which are noise

> Every measure we build gets two tests (CLAUDE.md, "Two tests for every new measure"): does it help its project's target, and is it consistent? This page keeps the second answer, so a measure that's real but useless to one project isn't lost, and noise isn't built on. Started 2026-11-07 at the CEO's request.

**How to read it:**
- **Week r:** each team-season's average in odd weeks against even weeks, correlated across team-seasons. 1 means it's entirely about the team; 0 means it's luck, or the same for everyone. The margin itself is 0.51.
- **Season r:** a team's season average against its next season's.
- **Verdict:**
  - **trait:** repeats within and across seasons; something a team *is*.
  - **state:** repeats within a season but not across; something a team is *in* for a while, like an injured quarterback.
  - **noise:** doesn't repeat week to week.
  - Each r has a 90% interval; a verdict is given only when its interval clears zero ([`pcf.validation.consistency`](../src/pcf/validation/consistency.py)).
- **Helps its target:** the project's first test, with the size. "Not tested" means it was only measured.
- **Per team per regular-season game,** net of nothing unless the name says so (a team's own value, or the value it allowed).

| Measure | Project | What it is | Week r (90%) | Season r | Verdict | Helps its target? | Note |
|---|---|---|---|---|---|---|---|
| Same-team share | elo (H1) | Share of a team's usual snaps available this week | 0.83 (0.81–) | 0.40 | trait | Yes: −0.02 points on next margin, more with the QB (F15) | Some teams are reliably healthier from season to season, not just this season. Worth asking why (age, medical staff, depth) |
| Usual QB missing | elo (H1) | Starter out or off the roster | 0.66 (0.61–) | 0.03 | state | Yes: −0.04 points (F14) | Injuries last for weeks but don't carry over to next season, as expected |
| Points scored | elo | | 0.55 (0.50–) | 0.44 | trait | In the rating (F4) | Offense repeats more than defense |
| Pass EPA, offense | elo (H7) | Expected points per pass play | 0.53 (0.49–) | 0.45 | trait | No, on top of the points rating (F18) | The most consistent efficiency measure. Use it where points aren't the target: game script, play mix, fantasy |
| Margin | elo | | 0.51 (0.46–) | 0.41 | trait | The rating's input | The reference |
| Average win probability | elo (H3) | Mean home-team win probability across a game's plays | 0.41 (0.36–) | 0.39 | trait | Barely: −0.02 at best as a blend (F11) | Less consistent than the margin it summarises |
| Rush EPA, offense | elo (H7) | Expected points per run | 0.40 (0.35–) | 0.34 | trait | No (F18) | |
| Points allowed | elo | | 0.36 (0.31–) | 0.31 | trait | In the rating (F4) | |
| Rush EPA allowed | elo (H7) | | 0.31 (0.25–) | 0.27 | trait | No (F18) | Run defense repeats more than pass defense |
| **Finishing** | elo (H3) | Result (win 1, tie 0.5, loss 0) minus average win probability: high when a team wins games it "shouldn't have" | 0.28 (0.22–) | 0.22 | **trait** | No on margins: +0.00 in rung 3 (F23). Win chances not tested | **The CEO's late-underdog-win idea, measured directly: it repeats.** Some teams reliably finish better or worse than their game control says, and it carries into next season. A candidate for H5/H6 (game-state strength) and win forecasts |
| Pass EPA allowed | elo (H7) | | 0.25 (0.20–) | 0.28 | trait | No (F18) | |
| Kicking luck, own | elo (H4) | Field goals and extra points against the league's make rate at that distance | 0.24 (0.18–) | 0.30 | trait | Removing it: +0.00 (F8) | Kickers differ: it's skill, not luck |
| Return TDs allowed | elo (H4) | Defensive and special-teams TDs given up | 0.17 (0.12–) | 0.17 | trait | Removing it: +0.02 (F8) | Ball security and coverage units are partly a team trait |
| Kicking luck, opponent | elo (H4) | The other team's kicking against the league's rate | 0.16 (0.11–) | 0.28 | trait | Not tested | Probably the home stadium (domes, wind, altitude), not the opponents. A candidate for the environment expert |
| Long TDs scored | elo (H4) | Offensive TDs of 40+ yards (expected points) | 0.15 (0.09–) | 0.13 | trait | Removing it: +0.01 (F8) | Weak |
| Interceptions caught | elo (H4) | Expected points gained by the defense on interceptions | 0.12 (0.06–) | 0.11 | trait | Not tested on its own | Weak |
| Interceptions thrown | elo (H4) | | 0.11 (0.05–) | 0.17 | trait | Removing both: +0.09 (F8) | Weak within a season, a bit stronger across (quarterbacks persist) |
| Return TDs scored | elo (H4) | | 0.07 (0.01–) | 0.21 | trait, barely | Removing it: +0.02 (F8) | Hardly repeats within a season, but does across: return units and opportunistic defenses persist |
| Long TDs allowed | elo (H4) | | 0.03 (−0.03–) | 0.09 | noise | — | Big plays given up are luck |
| Fumble-recovery luck | elo (H4) | Who recovers a fumble, against the average fumble | −0.05 (−0.11–) | 0.05 | noise | Removing it: +0.02 (F8) | Pure luck, as the CEO said. It still didn't help the rating, because over a dozen games it averages out |
| Shotgun over expected | schemes-v2 | Neutral shotgun rate against the league's for that season, down and distance | 0.92 (0.91–) | 0.62 | trait | Beyond strength, +0.008 EPA a play per sd (schemes-v2#F6) | The head coach's: carries to a new team (r 0.67, 27 moves) |
| No-huddle over expected | schemes-v2 | Same, for no-huddle | 0.88 (0.87–) | 0.52 | trait | No (F6) | The head coach's (0.78 with the coach's old team) |
| Personnel 11 / heavy | schemes-v2 | Share of neutral snaps in 1 RB 1 TE / RB + TE ≥ 3 (2016+, after the season) | 0.90 / 0.91 | 0.50 / 0.48 | trait | No (F6) | The head coach's |
| Tempo | schemes-v2 | Game seconds from an in-bounds run to the next snap | 0.77 (0.74–) | 0.53 | trait | No (F6) | Mostly the coach's |
| Pass rate over expected | schemes-v2 | Neutral pass rate less `xpass` | 0.63 (0.59–) | 0.40 | trait | Barely: +0.005 beyond strength (F6) | Needs both the coach and the QB to repeat |
| QB scramble rate | schemes-v2 | Scrambles per neutral dropback | 0.62 (0.58–) | 0.46 | trait | No (F6) | The QB's (0.16 with a new QB, 0.54 with a new coach) |
| Outside-run share | schemes-v2 | Runs charted to the end gap | 0.59 (0.55–) | 0.59 | trait | No (F6) | Stays with the team whatever changes: possibly stadium-crew charting |
| Middle / deep / aDOT | schemes-v2 | Pass location and depth | 0.41 / 0.27 / 0.34 | 0.39 / 0.23 / 0.30 | trait | No (F6) | aDOT follows neither the coach nor the old team: likely the QB |
| 4th-and-short go rate | schemes-v2 | Went for it on 4th and ≤2 between the 30s, per game | 0.01 (−0.06–) | 0.06 | noise | — | Too few plays a game; may be a coach trait over a season. Looked like a trait (0.31) before taking out the league trend |
| Man / two-high / blitz / box | schemes-v2 | Defensive choices (participation; man and shells 2018+, after the season) | 0.73 / 0.71 / 0.64 / 0.72 | 0.49 / 0.48 / 0.45 / 0.48 | trait | No alone (F6); pairs with offense only as a whisper (F7) | Man and two-high follow the head coach |
| Pass rate / aDOT faced, pressure | schemes-v2 | What offenses do against a defense | 0.24 / 0.17 / 0.10 | 0.24 / 0.24 / 0.24 | trait | Pass rate faced −0.006 beyond strength (F6) | Defenses mostly react; their choices repeat far more than what they allow |
| QB man-less-zone EPA split | schemes-v2 (I22) | A QB's EPA per dropback against man less against zone (2018–2024, after the season) | −0.07 (odd against even weeks, per QB-season) | 0.04 | noise | No (schemes-v2#F15) | A QB isn't a man beater or a zone beater in EPA terms; per QB, not per team |
| Use over expected, per option (anti-traits) | schemes-v2 (H15) | A regime's use of an option (pass, shotgun, no-huddle, heavy personnel, man, two-high, blitz, 8+ box) against the league's usual choice for the play's situation, look and opponent | 0.42–0.80 (odd against even games in a regime) | shotgun +0.57 with a new QB, +0.16 with a new coach | signal (deep throws noise: 0.05) | Yes, in part: avoidance predicts being worse at the option (schemes-v2#F17) | Low use is the anti-trait |
| Option gap (comparative advantage) | schemes-v2 (H15) | A team's EPA per play beyond the league when using an option, less when not (defenses: EPA prevented) | −0.10 to +0.12 (odd against even games in a regime) | passing +0.33 (+0.23 with a new QB, +0.31 with a new coach); others −0.24 to +0.15 | passing signal; the rest noise | — (it's (a)'s outcome) | Too noisy alone; read it through avoidance |
| Gain per game, offense (pass, shotgun) | schemes-v2 (anti-traits) | `team_game.tendencies`: EPA per play with the option less without in a game, neutral situations; shotgun within passes and within runs (decision 0024) | pass 0.11 (0.05–0.18); shotgun 0.02 (−0.05–) | pass 0.25; shotgun 0.04 | pass trait (faint); shotgun noise | It's the target. Use predicts it on held-out seasons (schemes-v2#R6) | Single games are mostly noise (a spread of 0.57 and 0.70 EPA a play) |
| Use over expected per game, defense (man, two-high, blitz) | schemes-v2 (anti-traits) | `team_game.charted`: the share with the option less the league's usual choice that season for the down, distance, formation and personnel (after the season) | 0.76 / 0.72 / 0.67 | 0.50 / 0.48 / 0.47 | trait | No: last season's use doesn't predict the gain (schemes-v2#R6) | The defensive anti-trait is real as a style, not as a limit |
| Gain per game, defense (man, two-high, blitz) | schemes-v2 (anti-traits) | `team_game.charted`: EPA prevented with the option less without | 0.13 (0.02–) / −0.05 / −0.04 | 0.03 / 0.04 / −0.02 | man state; two-high and blitz noise | — (it's the target) | Too noisy to forecast from a season's charting |
| Offense personnel and formation over expected (11 / 12 / 21 / heavy / pistol) | schemes-v2 (`team_season`) | Share of neutral snaps against the league's that season for the down and distance (participation, after the season; backs include fullbacks) | 0.90 / 0.84 / 0.95 / 0.91 / 0.94 | 0.56 / 0.38 / 0.68 / 0.51 / 0.71 | trait | Not tested (a measured table, decision 0026) | 21 personnel and the pistol are the most lasting choices PCF has measured |
| Time to throw over expected | schemes-v2 (`team_season`) | Seconds from snap to throw on neutral dropbacks, against the league's for the down and distance | 0.56 (0.49–) | 0.44 | trait | Not tested | Likely the QB's (the quickest: 2020–21 Steelers, 2023 Dolphins) |
| What an offense faced (box / man / two-high / blitz over expected) | schemes-v2 (`team_season`) | Defenses' choices against this offense, beyond what they usually do against the look | 0.44 / 0.18 / 0.36 / 0.24 | 0.37 / 0.33 / 0.33 / 0.36 | trait | Not tested | How defenses respect an offense; repeats less within a season than defenses' own choices, as much across seasons |
| Defense choices per season (box / man / two-high / blitz / rushers / nickel / dime over expected) | schemes-v2 (`team_season`) | Against the league's usual choice for the down, distance, shotgun and personnel group (man and shells 2018+) | 0.73 / 0.75 / 0.69 / 0.67 / 0.67 / 0.87 / 0.93 | 0.49 / 0.50 / 0.50 / 0.48 / 0.44 / 0.49 / 0.54 | trait | Not tested | Matches the per-game `charted` rows (man 0.76, two-high 0.72, blitz 0.67). Nickel and dime are the defense's most lasting choices |
| Matchup residual (offense against a defense, beyond both units' strength) | schemes-v2 (scheme against scheme, F20) | An offense's EPA per play in a game less what both units' season strength expects; its repeat in the same pair's rematch, less what each unit carries into other games | rematch r +0.088, of which the pairing's own part is +0.1% of the residual (90% −4.2% to +4.6%; corrected at the CEO's spot-check, first misread as 9%) | — | noise (no pairing part beyond each unit's form) | Not as a raw first-meeting residual: r +0.008 against the close (912 games) | The repeat is each unit's form, not the pairing. Measured with `explore/spot_f20b.py`, not `pcf.validation.consistency` (it's a pair, not a team) |
| Learned matchup types (hidden offense and defense numbers, k 2) | schemes-v2 (F24, F26, F27) | Two hidden numbers per unit, learned within a season from results, whose product is the matchup part | — | not carried: last season's types predict nothing in weeks 2–5 (r +0.012, 25% by chance), and pulling this season's toward them removes the signal (F27) | noise across seasons (within-season only) | No: r +0.031 against what strength misses from week 6 (F26), but neutral in Elo's margin forecast and fails signal there (F28) | A pair measure, judged by carrying the types forward, not with `pcf.validation.consistency` |
| Pace over expected, clock-aware | pace (H22) | Seconds between snaps, every snap, against an expected pace that knows win chance, expected points and when the clock stopped (Claude's addition) | 0.85 (0.83–) | 0.54 | trait | Next plays: +0.007 R² beyond the line and plays so far (F5) | The steadiest pace measure; one game to the next 0.46 |
| Pace over expected, win chance and expected points | pace (H22) | The same, with the CEO's two inputs only | 0.62 (0.58–) | 0.50 | trait | +0.005 (F5) | Partly pass rate: incompletions stop the clock (r −0.28, F4) |
| Neutral seconds per snap | pace (usual way) | Seconds between snaps in neutral situations | 0.66 (0.63–) | 0.49 | trait | +0.004 (F5) | Also partly pass rate (−0.23) |
| No-huddle rate, every snap | pace | Share of snaps in no-huddle | 0.89 (0.88–) | 0.56 | trait | +0.003 (F5) | Neutral only: 0.89 and 0.54 |
| PROE, every play | pace (H19, H22) | Pass minus `xpass` on every play with one | 0.77 (0.74–) | 0.46 | trait | Next PROE (F3) | Steadier than the neutral version (0.64, 0.40; F6) |
| Pass success, opponent-adjusted | pace (H21) | EPA per dropback less the opponents' season-to-date average allowed (success rate: 0.51, 0.43) | 0.50 (0.45–) | 0.42 | trait | +0.3–0.5 pts of next PROE per sd (F3) | |
| Plays per game | pace | A team's scrimmage snaps | 0.35 (0.29–) | 0.38 | trait | (the target) | One game to the next 0.07: mostly what happened in the game |
| Dropbacks / runs per game | pace | Passes (with sacks and scrambles) and runs | 0.56 / 0.51 | 0.41 / 0.41 | trait | (targets) | Pass rate: 0.58, 0.42 |

| Pace over expected, built (`team_game.pace`) | pace (R2) | Clock-aware, every snap, against PCF's expected gap fit on the 10 seasons before | 0.84 (0.82–) | 0.57 | trait | Next plays: the full-sample volume model beats the neutral one (R1) | Centred by season (B2); raw it reads 0.92 |
| PROE, built (PCF's expected pass chance) | pace (R2) | Pass minus PCF's walk-forward expected pass chance, every scrimmage play | 0.77 (0.74–) | 0.49 | trait | Next dropbacks and runs (R1, R3) | By down: 1st 0.67, 2nd 0.68, 3rd 0.59 week to week; 3rd down repeats most across seasons (0.52) |
| Drives / plays per drive per game | pace (B1) | Drives with a scrimmage play; scrimmage plays over drives | 0.30 / 0.37 | 0.34 / 0.40 | trait | Plays per drive weighs little once efficiency is in (R3) | |
| What a defense allows: plays / PROE / pace over expected | pace (B1) | The opposing offenses' values against this defense | 0.15 / 0.23 / 0.08 | 0.23 / 0.31 / 0.26 | trait (pace barely) | Plays allowed helps next plays (+0.44 per sd, R3) | Pace is the offense's choice |

**Player measures** (player-pace exploration, 2026-11-11): per **player** per regular-season game, not per team. Week r is the split-half across player-seasons, each half weighted by the plays that measure it (n_on × n_off / n_team for a plus-minus). Groups pooled as shown.

| Measure | Project | What it is | Week r (90%) | Season r | Verdict | Helps its target? | Note |
|---|---|---|---|---|---|---|---|
| On-field PROE, offense | player-pace (H26) | The team's PROE on the plays he was on the field | 0.42–0.58 by group (0.38–) | 0.19–0.46; new team −0.06 to 0.13, TE 0.44 | trait | Not tested | His team's rate: it doesn't follow him to a new team (F1) |
| On-field pace over expected, offense | player-pace (H26) | The same for pace | 0.42–0.53 (0.38–) | 0.18–0.29; new team 0.02–0.12 | trait | Not tested | Under 30% of snaps: 0.27–0.32; linemen 0.10, noise (F2) |
| PROE plus-minus, TE / WR / RB | player-pace (H28, H29) | On-field minus off-field PROE, same team-game | 0.62 / 0.42 / 0.49 (0.39–) | 0.56 / 0.41 / 0.38; moved 0.54 / 0.31 / 0.23 | trait | **Yes:** next season's, 15% better than the group (player-pace#R1) | A role tell; within personnel groupings TE 0.46, WR 0.29 hold, RB 0.30 doesn't follow him (F3, F4) |
| PROE plus-minus, QB / OL | player-pace (H28, H29) | The same | 0.13 (0.06–) / 0.09 (0.05–) | 0.08 / 0.06 | trait, weak | QB no (+0.7%, tie); OL not reported | Starters rarely sit, so few plays measure it |
| Pace plus-minus, offense | player-pace (H28, H29) | On-field minus off-field pace over expected | 0.06–0.20 (QB 0.20, 0.12–) | 0.02–0.08 | state (most groups) | Barely: 0.2% (player-pace#R7) | Pace stays with the team (F3) |
| With-or-without by game, QB | player-pace (H28, in season) | Team's rate in games he played half the snaps minus games he didn't | inflated (F5) | PROE 0.14 (0.03–0.25), pace 0.26 (0.15–0.36) | trait | As the QB's start history: team PROE 0.3%, 4% in expected changes; not volume (player-pace#R2, R3) | Known in season from snap counts; other groups about 0 (TE pace 0.16) |
| PROE plus-minus, defense DB / LB / DL | player-pace (H31) | The opponent's PROE on-field minus off-field | 0.15 / 0.12 / 0.09 (0.06–) | 0.12 / 0.03 / 0.02 | DB trait; LB, DL state | Barely: 0.8% (player-pace#R8) | Substitution following the offense's (F8) |
| Pace, defense (on-field and plus-minus) | player-pace (H31) | The opponent's pace with him on | 0.00–0.09 | about 0 | noise or state | Not tested | Nothing a defender carries |

Player rows measured 2026-11-11 with [`projects/player-pace/explore/h26_h28_h29_h31.py`](player-pace/explore/h26_h28_h29_h31.py) and [`personnel.py`](player-pace/explore/personnel.py), 2016–2024.

Built pace rows measured 2026-11-11 with [`projects/pace/build/consistency_built.py`](pace/build/consistency_built.py), each measure centred on its season's league level (pace B2).

Pace rows measured 2026-11-10 with [`projects/pace/explore/h22_h23_pace.py`](pace/explore/h22_h23_pace.py): 608 team-seasons, regular seasons 2006–2024 (2020–2024 the same shape).

Measured 2026-11-07 with [`projects/elo/explore/consistency_so_far.py`](elo/explore/consistency_so_far.py): 829 team-seasons, 1999–2024 regular season (384 from 2013 for the snap and injury measures). The vault (2025) isn't read.

`team_season` rows measured 2026-11-10 with [`projects/schemes-v2/explore/team_season_check.py`](schemes-v2/explore/team_season_check.py): per team-game, regular season 2016–2025, every measure over expected.

Anti-trait rows (gains and defensive use per game) measured 2026-11-09 with [`projects/schemes-v2/explore/anti_sign.py`](schemes-v2/explore/anti_sign.py): regular season 2006–2024 (charting 2016+; coverage 2018+).

Schemes rows measured 2026-11-08 with [`projects/schemes-v2/explore/tendencies.py`](schemes-v2/explore/tendencies.py): 9,853 team-games 2006–2024, neutral situations, every tendency against its league mean that season.

**Caveat for state-like measures:** odd and even weeks sit next to each other, so a measure that lasts for weeks (an injury) looks consistent week to week. The season r tells a trait from a state.

## Feature candidates

> **The CEO's rule (2026-11-07):** experts exist to compress data into features for downstream experts and betting models. An expert output that is **consistent** (above) **and close to as good as the sportsbooks' close** is recorded here as a good candidate feature. Downstream feature selection, inside the folds, decides whether it's used (rule k).

| Output | Expert | Where to read it | Consistent? | Quality against the close | Note |
|---|---|---|---|---|---|
| Team rating (points against an average team) | elo | `home_rating`, `away_rating` in the `margin` history (decision 0021) | Yes: the end-of-season rating repeats into next season at r 0.58, and its inputs (margin, same-team share) are traits | Its margin forecast is 0.27 points behind the close (elo#F2), 0.22 outside the last two weeks | Ties the close when blended (elo#F4), so a betting model gains little from it directly. Most useful to other experts and before a line exists |
| Offense and defense ratings | elo | `home_offense`, `home_defense`, `away_offense`, `away_defense` | Yes: points scored r 0.44 and allowed 0.31 season to season | Its total is 0.30 behind the close (elo#F2) | Game environments for fantasy and props |
| Usual QB out, same-team share | elo | `h_qb`, `a_qb`, `h_share`, `a_share` | State (QB) and trait (share), above | Part of the 0.27 | Point-in-time availability, known by the Saturday run |
| Seed locked | elo | `h_lock`, `a_lock` in the `margin` history (decision 0022) | A state: one week a season, so the consistency test doesn't apply. Locked teams are the good ones (it follows the record) | Cuts Elo's final-week gap to the close from 1.32 to 0.89 (elo#F14) | A rest signal for any final-week forecast: player props, fantasy, totals (untested) |
| Margin, total, win chance | elo | `margin`, `total`, `win` histories | Built from traits | 0.27, 0.30 and 0.019 log loss behind the close | Calibrated ranges (elo#F5) |
| Wins next 3 games, rest of season | elo | `wins_next3`, `wins_rest` histories | Built from traits | No close to compare with; beats the record-based yardstick at every point in the season (elo#F8) | For futures and season-win markets |
| Offensive avoidance (pass, shotgun use) and the pass-gain blend | schemes-v2 (anti-traits) | `pass_use`, `shotgun_use` features; the `pass_gain_blend` forecast (not saved as outputs yet) | Yes: built from traits (pass rate over expected, shotgun rate) | No close to compare with. Use predicts the next game's gain from the option on held-out seasons, but faintly (+0.015 to +0.018 EPA a play per sd: schemes-v2#R6) | For play-mix and efficiency models (a team forced to pass); the raw use does as well as the opponent-adjusted one (R7) |
