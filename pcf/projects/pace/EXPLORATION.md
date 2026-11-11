# Exploration: Pace and play-calling (`pace`)

> Is there signal in pace and pass rate over expected, and do the CEO's hunches H19–H25 hold? Run 2026-11-10 on regular-season games 2006–2024, with the key numbers repeated on 2020–2024. nflverse's expected pass chance, win chance and expected points are in-sample before 2020 (tag-tables#F4). The 2025 vault isn't read.

**Verdict (2026-11-10): GO.** Every habit measured here repeats within and across seasons, and next game's plays, dropbacks and runs can be forecast better than a shuffled version of the same inputs. Volume is noisy, though: the best first-look forecast explains 5% of a team's plays in a game and 10% of its runs, with a typical miss of about 7 plays.

| Hunch | Verdict | Size |
|---|---|---|
| H19 PROE the same across situations | **unclear** (mixed) | The same trait across score, win chance, quarters 1–3 and field position outside the red zone (0.81–1.02, where 1 is identical); not across downs (0.45–0.63) |
| H20 pass rate follows win odds | **held** (as the usual way says) | −1.0 point of pass rate per +10 points of pre-game win chance; already inside nflverse's expected pass chance on each play |
| H21 recent pass success raises pass rate | **held**, small | +0.5 points of PROE per sd of pass success (90% +0.4 to +0.7); +0.3 beyond schemes' forecast. The season's success, not the last 4 games' |
| H22 expected pace on every play | **unclear** (mixed) | The principle held: a full sample beats close games only. The recipe failed: win chance and expected points explain 5% of the time between snaps |
| H23 our features always consistent | **held** | All 14 measures are traits (week to week 0.35–0.89, season to season 0.38–0.56) |
| H24 early pace, more injuries later | **failed** | No carry-over to the second half beyond what the same half shows |
| H25 early pace tires the defense | **failed** | Fourth-quarter EPA allowed: +0.000 per 10 first-half snaps faced (90% −0.013 to +0.013) |

## Expectations, written before running
In the brief, 2026-11-10 ("Claude's assumptions, limits and expectations, per hunch"). In short: H19 holds on downs 1–2, score and field position, weaker on 3rd down and late; H20 large at the game level, near zero on a play; H21 small, mostly the QB; H22 steadier than neutral-only, a modest gain on plays; H23 fails as "always"; H24 yes per game (exposure), faint per play; H25 small at most. **Wrong:** H19 on downs (1st and 2nd down differ too) and H23 (every measure repeats).

## Data and definitions
- **Plays:** regular-season scrimmage snaps, 2006–2024, from nflverse play-by-play ([`explore/build_plays.py`](explore/build_plays.py)): 669,082 snaps.
- **PROE** (pass rate over expected): pass (a dropback: passes, sacks and scrambles) minus nflverse's `xpass`, on every play with an `xpass`. **Neutral:** win chance 20–80%, downs 1–3, outside the last two minutes of a half, as schemes-v2 measures it.
- **The gap:** game seconds from the previous snap of the same drive and quarter (0–60 s). nflverse's `play_clock` is 0 on every play, so there's no play clock.
- **Expected pace** (gradient-boosted trees, out of fold by season):
  - `ceo`: the CEO's H22 inputs, win chance and expected points, plus the season.
  - `clock`: Claude's addition, labelled as such. It adds what stops or slows the clock: the previous snap an incompletion, out of bounds, a penalty or no-play, a spike or a sack; timeouts since the previous snap; the quarter and seconds left in the half.
- **Pace over expected:** the mean of (gap − expected) over a team's snaps in a game. Negative is fast.
- **In-game injuries:** snaps whose description says a player "was injured during the play", by side. About 360 a season in 2006 and 800 in 2024; side known for all.
- **Scripts:** [`h19_h21_pass.py`](explore/h19_h21_pass.py), [`h22_h23_pace.py`](explore/h22_h23_pace.py), [`h24_h25_fatigue.py`](explore/h24_h25_fatigue.py), [`volume_first_look.py`](explore/volume_first_look.py).

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | PROE is one trait across game state, but not across downs | strong |
| F2 | Win chance moves runs, not passes, and nflverse's expected pass chance already uses it | strong |
| F3 | Pass success adds a little to next game's PROE, and it's the season's success, not the last month's | moderate |
| F4 | The time between snaps is mostly the clock stopping | strong |
| F5 | With the clock known, full-sample pace is the steadiest pace measure | strong |
| F6 | Full-sample PROE is steadier than neutral PROE | strong |
| F7 | Every habit is a trait; single games are noisy | strong |
| F8 | Volume is hard to forecast, but every step adds real signal | moderate |
| F9 | Plays are mostly plays per drive, which is efficiency: the basketball analogy held | strong |
| F10 | Early pace doesn't raise later injury rates | moderate |
| F11 | Long drives may raise the defense's injury rate (a lead, not a finding) | weak |
| F12 | No sign that early pace tires the defense | moderate |

**F1. PROE is one trait across game state, but not across downs (H19).** Per team-season, each slice's PROE was correlated with another slice's, then divided by the most each slice's own noise allows (split-half, odd weeks against even). 1.0 means the same trait. 608 team-seasons:

| Family | Pairs (disattenuated r) |
|---|---|
| Score | down 9+ with within 8: 0.84; up 9+ with within 8: 1.02; down 9+ with up 9+: 0.66 |
| Win chance | 20–80% with <20%: 0.81; with >80%: 0.95; <20% with >80%: 0.66 |
| Quarter | 1 with 2: 0.89; 2 with 3: 0.96; 3 with 4: 0.90; 1 with 4: 0.67 |
| Field | own half with their 21–50: 0.87; red zone with their 21–50: 0.83; with own half: 0.67 |
| Clock | last 2 minutes with the rest of the half: 0.71 |
| **Downs** | **1st with 2nd: 0.58; 2nd with 3rd: 0.63; 1st with 3rd: 0.45** |

2020–2024 is the same shape (downs 0.50–0.66; score and win chance 0.88–1.02). A team's lean is the same whether it's ahead or behind, and in most of the field. But a team that passes more than expected on 1st down isn't much more likely to on 3rd: early downs and 3rd down are separate habits. The extremes (way ahead against way behind; 1st quarter against 4th; the red zone) are the next-weakest links.

**F2. Win chance moves runs, not passes, and nflverse's expected pass chance already uses it (H20).**
- **On a play,** PROE is flat across win chance bands (−0.1 to −1.4 points), so `xpass` already prices the game state.
- **In a game,** a team's pass rate falls 1.0 point per +10 points of pre-game win chance (from the close's moneyline), beyond its season-to-date PROE. R² goes from 0.066 to 0.098; 2020–2024 is the same.
- **By band:**

| Pre-game win chance | Dropbacks | Runs | Plays | Pass rate |
|---|---|---|---|---|
| under 20% | 38.8 | 23.2 | 62.0 | 62.4% |
| 20–40% | 40.4 | 24.1 | 64.5 | 62.6% |
| 40–60% | 40.0 | 25.3 | 65.3 | 61.0% |
| 60–80% | 39.3 | 26.7 | 66.0 | 59.4% |
| over 80% | 38.5 | 27.8 | 66.3 | 57.8% |

Dropbacks hardly move with win chance; big favorites run about 4.6 more times and run about 4 more plays. For volume, game script is mainly about runs.

**F3. Pass success adds a little to next game's PROE, and it's the season's success, not the last month's (H21).** Pass success is EPA per dropback (and success rate), net of the opponents' season-to-date average allowed.
- Beyond the team's own season-to-date and last-4 PROE: +0.57 points of PROE per sd for the last 4 games (90% +0.42 to +0.70), +0.56 for the season to date. R² rises 0.189 to 0.194.
- With both in, neither stands out (+0.36, interval reaching 0), so it's the lasting quality, like a good QB, not chasing a hot month.
- Beyond schemes-v2's own pass rate forecast (2016–2024, neutral PROE, its target): +0.34 per sd (90% +0.08 to +0.60). Real but small.
- 2020–2024: +0.43 to +0.74, the same story.

**F4. The time between snaps is mostly the clock stopping (H22).** After an incomplete pass, the next snap comes 5.3 game seconds later; after everything else, 32.1. Win chance and expected points (the CEO's inputs) explain 5% of the gap; with the clock-stopping inputs, 78%. So the CEO's pace over expected is partly pass rate: passing teams throw incompletions, which stop the clock and make them look fast (r −0.28 with the game's pass rate). The usual neutral seconds per snap has the same problem (−0.23). Schemes' tempo (after in-bounds runs only) and the clock-aware measure don't (−0.02, −0.06).

**F5. With the clock known, full-sample pace is the steadiest pace measure (H22).** 2006–2024, 608 team-seasons:

| Pace measure | Snaps per game | Week to week r | Season to season r | One game to the next | Next game's plays, R² with the line and plays so far |
|---|---|---|---|---|---|
| CEO's expected pace (win chance, expected points), every snap | 55 | 0.62 | 0.50 | 0.18 | 0.0345 |
| Claude's clock-aware expected pace, every snap | 55 | **0.85** | 0.54 | **0.46** | **0.0368** |
| Neutral seconds per snap (the usual way) | 29 | 0.66 | 0.49 | 0.23 | 0.0338 |
| Schemes' tempo (neutral, after in-bounds runs) | about 8 | 0.82 | 0.54 | 0.38 | 0.0358 |
| No-huddle rate, every snap | 55 | 0.89 | 0.56 | 0.54 | 0.0322 |

The line and plays so far alone give 0.0296. So a full sample beats close games only, as the CEO bet, but only once the expected pace knows when the clock stopped. With win chance and expected points alone it's no steadier than the usual measure. As forecasts of plays, every pace measure adds about the same small amount (0.004–0.007 of R²).

**F6. Full-sample PROE is steadier than neutral PROE.** Week to week 0.77 against 0.64, season to season 0.46 against 0.40, one game to the next 0.33 against 0.22. It's the CEO's H22 principle again, this time for pass rate: since `xpass` prices the situation, every play can count. Schemes-v2's pass rate forecast uses neutral plays only.

**F7. Every habit is a trait; single games are noisy (H23).** All 14 measures repeat within and across seasons (`pcf.validation.consistency`; the CONSISTENCY.md rows are dated 2026-11-10):
- week to week from 0.35 (plays) to 0.89 (no-huddle);
- season to season 0.38–0.56;
- 2020–2024 the same.

A single game says little, though: one game to the next is 0.07 for plays, 0.14 for dropbacks, 0.33 for PROE and 0.54 for no-huddle. Habits are steady; one game's volume is mostly what happened in it.

**F8. Volume is hard to forecast, but every step adds real signal.** Next game's plays, dropbacks and runs, weeks 4+ (8,038 team-games). Each step's new columns are also shuffled to show what noise alone adds:

| Step | Plays R² | Dropbacks R² | Runs R² |
|---|---|---|---|
| Season average so far | 0.019 | 0.060 | 0.048 |
| + the line (team's spread, game total) | 0.029 | 0.076 | 0.073 |
| + own habits (clock-aware pace, PROE, no-huddle) | 0.037 | 0.089 | 0.097 |
| + the opponent (its pace, plays allowed, plays per drive) | **0.046** | **0.091** | **0.101** |
| shuffled at the last step | 0.038 | 0.089 | 0.097 |

- **Typical miss:** 6.9 plays (sd 8.8), 6.9 dropbacks, 5.7 runs; every interval is above its shuffled version.
- **Game totals:** both teams together run 130 plays (sd 9.3; 10th–90th percentile 119–142).

So ranges will be wide, and honest ranges matter more here than a sharp middle.

**F9. Plays are mostly plays per drive, which is efficiency: the basketball analogy held.**
- Drives alternate, so the two teams' drives match (r +0.80), but their plays trade off (r −0.44): more plays for one team means fewer for the other.
- Of the variance in a team's plays (log), plays per drive carries 71% and drives 29%.
- Plays per drive goes with the offense's EPA per dropback (r +0.41).

So a volume forecast should be drives times plays per drive, made for both teams together, and it needs each offense's and defense's efficiency, which pace alone doesn't have.

**F10. Early pace doesn't raise later injury rates (H24).**
- *Exposure:* games with 10 more first-half snaps have 0.10 more second-half injuries (90% +0.05 to +0.16), or 0.05 with second-half snaps held fixed (interval reaching 0).
- *Seconds per snap:* first-half pace over expected has no tie to second-half injuries per snap (+0.003 per second faster, 90% −0.03 to +0.03).
- *By side:* a defense that faced 10 more first-half snaps has +0.13 more second-half injuries per 100 snaps (+0.07 to +0.20). That survives its season strength and its own first-half injury rate (+0.12). But the same snaps predict the *first-half* rate just as much (+0.13). So it's something about those games, not fatigue building up. Offenses: +0.02 (−0.02 to +0.07).

**F11. Long drives may raise the defense's injury rate (a lead for injury & fatigue, not a finding).** Within drives of 10+ plays, the defense's injuries per 100 snaps go 1.09 (plays 1–3), 1.25 (4–6), 1.45 (7–9), 1.27 (10–12), 1.18 (13+). The offense's stay flat (0.74–0.85). Not tested against play type or field position; logged as Claude's idea I29.

**F12. No sign that early pace tires the defense (H25).** A defense's fourth-quarter EPA allowed per play (at win chance 5–95%), beyond the offense's and defense's strength in their other games:
- per 10 first-half snaps faced: +0.000 (90% −0.013 to +0.013; the sd of Q4 EPA per play is 0.39);
- per second faster opposing first-half pace: +0.002 (−0.003 to +0.006).

## Follow-up: which conditions hold, and is PROE measured right? (the CEO, 2026-11-10)
*The CEO asked which conditions hold for each hunch, whether PROE is measured correctly, and how consistent PROE and pace over expected are.* Scripts: [`proe_check.py`](explore/proe_check.py), [`conditions.py`](explore/conditions.py), [`conditions_fatigue.py`](explore/conditions_fatigue.py). The conditions are H19's slices. With about 100 tests, about 10 would exclude zero by chance, so one slice alone is a lead, not a finding.

| # | Finding | Confidence |
|---|---|---|
| F13 | PROE is measured correctly for comparing teams, but nflverse's expected pass chance is drifting | strong |
| F14 | PROE and pace over expected repeat in every condition; lopsided games and the last two minutes are the noisiest | strong |
| F15 | Pace is one habit in every condition but the last two minutes; PROE in every condition but downs and the last two minutes | strong |
| F16 | Win chance lowers pass rate only in the second half, through the score | strong |
| F17 | Pass success raises next game's PROE in all 18 conditions, most when ahead and late | strong |
| F18 | No condition shows fatigue building up (H24, H25); pass defense after a long first half is a lead with a confound | moderate |

**F13. PROE is measured correctly for comparing teams, but nflverse's expected pass chance is drifting.**
- *Definitions are right.* Dropbacks count as passes, including sacks and scrambles (scrambles are logged as runs; nflverse's `pass` flag catches them). Kneels and spikes are left out. Penalty plays that count as no play (4% of plays) count by the call: 76% of them were passes, because passes draw more flags.
- *nflverse's `xpass` is in-sample before 2020.* Our own expected pass chance, walk-forward (each season fit only on earlier ones, from the situation alone), is worse than `xpass` on 2010–2019 (log loss 0.511–0.530 against 0.500–0.517), and as good from 2020 (0.524–0.532 against 0.523–0.533). So `xpass`'s edge before 2020 is its fit on those seasons.
- *It's drifting.* Teams passed 1–2 points less than `xpass` expected in 2022–2024 (2022 −2.0, 2023 −1.1, 2024 −1.7). On 2020–2024 the gap is largest in the red zone (−3.1), on 3rd down (−2.6), in the last two minutes (−2.4) and in the fourth quarter (−1.9).
- *Rankings don't change.* Team-season PROE from our model and from nflverse's agree at r 0.988 (they differ by 1.75 points on average, against a spread of 4.2 between teams) and are equally consistent (week to week 0.76–0.77).
- *So:* any team comparison is safe, but the level is off by a league-wide 1–2 points, which a volume forecast would carry. The build uses our own walk-forward expected pass chance, refit each season and centred on the league's level so far (a technical call).

**F14. PROE and pace over expected repeat in every condition; lopsided games and the last two minutes are the noisiest (H23).** Every one of the 36 condition-measure pairs is a trait (`pcf.validation.consistency`, 2006–2024). Overall: PROE 0.77 week to week, 0.46 season to season; clock-aware pace over expected 0.85 and 0.54.

| Condition | Plays per game | PROE week / season r | Pace week / season r |
|---|---|---|---|
| 1st / 2nd / 3rd down | 28 / 22 / 14 | 0.68 / 0.40; 0.66 / 0.45; 0.62 / 0.54 | 0.75 / 0.50; 0.80 / 0.53; 0.61 / 0.46 |
| Down 9+ / within 8 / up 9+ | 30 / 42 / 24 | 0.33 / 0.28; 0.65 / 0.39; 0.23 / 0.24 | 0.37 / 0.33; 0.81 / 0.52; 0.15 / 0.14 |
| Win chance <20% / 20–80% / >80% | 25 / 39 / 24 | 0.24 / 0.24; 0.65 / 0.40; 0.26 / 0.30 | 0.27 / 0.27; 0.82 / 0.52; 0.17 / 0.15 |
| Own half / their 21–50 / red zone | 36 / 19 / 10 | 0.68 / 0.41; 0.59 / 0.38; 0.54 / 0.43 | 0.80 / 0.54; 0.71 / 0.49; 0.52 / 0.37 |
| Quarter 1 / 2 / 3 / 4 | 15 / 18 / 15 / 17 | 0.56; 0.61; 0.56; 0.52 (season 0.34–0.41) | 0.75; 0.68; 0.72; 0.50 (season 0.35–0.52) |
| Last 2 minutes / rest of half | 8 / 58 | 0.33 / 0.34; 0.75 / 0.45 | 0.10 / 0.14; 0.86 / 0.54 |

**F15. Pace is one habit in every condition but the last two minutes; PROE in every condition but downs and the last two minutes (H19, H22).** Each condition's team-season mean against the team's mean on all its other plays, divided by the most both sides' noise allows (1.0 = the same habit):

| Condition | PROE | Pace |
|---|---|---|
| 1st / 2nd / 3rd down | **0.58 / 0.68 / 0.60** | 0.96 / 1.00 / 0.88 |
| Down 9+ / within 8 / up 9+ | 0.82 / 0.94 / 0.98 | 0.92 / 1.01 / 1.08 |
| Win chance <20% / 20–80% / >80% | 0.77 / 1.01 / 1.00 | 0.88 / 1.00 / 1.06 |
| Own half / their 21–50 / red zone | 0.82 / 0.93 / 0.76 | 1.00 / 1.02 / 0.95 |
| Quarter 1 / 2 / 3 / 4 | 0.85 / 0.99 / 0.99 / 0.89 | 0.97 / 1.01 / 1.01 / 0.90 |
| Last 2 minutes against the rest | **0.70** | **0.51** |

So the low consistency in lopsided games (F14) is noise from fewer plays, not a different habit: those plays still match the team's other plays (0.77–1.08). The real exceptions are PROE by down, and both measures in the last two minutes, where everyone hurries.

**F16. Win chance lowers pass rate only in the second half, through the score (H20).** A team's pass rate in each condition, per +10 points of pre-game win chance, beyond its season-to-date PROE (90% interval):
- **By quarter:** Q1 +0.2 (+0.1 to +0.3), Q2 +0.2 (+0.1 to +0.3), Q3 −0.7 (−0.8 to −0.6), **Q4 −3.6 (−3.9 to −3.3)**; the last two minutes −1.2.
- **By down and field:** −0.7 to −1.2 everywhere.
- **Within a score band:** about 0 (down 9+: +0.1; within 8: −0.0; up 9+: +0.1).

So favorites don't start out running more; they run more once they're ahead, mostly in the fourth quarter. Once the score is known, the pre-game odds add nothing. Within in-game win chance bands the sign even turns positive (+0.2 to +1.0): a favorite that's behind passes more than an underdog that's behind. On PROE (after `xpass`) every condition is within ±0.4 points.

**F17. Pass success raises next game's PROE in all 18 conditions, most when ahead and late (H21).** Per sd of opponent-adjusted pass success so far, beyond the team's PROE history (overall and in that condition). Every interval is above zero, far more than chance:
- *strongest:* up 9+ +0.93 (+0.54 to +1.33), Q4 +0.76, win chance >80% +0.72, 2nd down +0.72;
- *weakest:* when trailing (+0.35 to +0.38) and on 3rd down (+0.36).

Teams that pass well keep passing when they don't have to. When the situation forces a pass, passing quality matters less.

**F18. No condition shows fatigue building up (H24, H25); pass defense after a long first half is a lead with a confound.** Per +10 first-half snaps faced by a defense, 90% intervals:
- *H24, its injuries per 100 snaps:* on runs +0.13 in the second half against +0.16 in the first; on passes +0.15 against +0.11; on 3rd down −0.00 against +0.18; close or not, nothing in the second half. Every rise in the second half is matched in the first, so it's those games, not fatigue.
- *H25, EPA allowed per play:* on passes Q4 +0.031 (+0.013 to +0.049) and Q3 +0.020 (+0.006 to +0.035); on runs Q4 −0.014 (−0.030 to −0.000); 3rd down, close and not close all include zero in Q4. Pass defense is a little worse all second half after a long first half. But a defense that faced many first-half snaps was usually being moved on that day, which our season-strength controls don't capture. It's a lead for `injury-fatigue` (I30), not a verdict change.

## What this changes in the brief
1. **The habits are measured on every play.** PROE on every play (F1, F6), with early downs and 3rd down as separate habits (F1). Pace over expected on every snap, from an expected pace that knows when the clock stopped (F4, F5). The no-huddle rate stays as a third habit (F5). The neutral versions remain as yardsticks.
2. **Volume is built as drives times plays per drive,** for both teams together (F9). It uses the line (F2: favorites run more), both teams' habits, and both offenses' and defenses' efficiency, from Elo's offense and defense ratings or EPA (F9). Ranges come first (F8).
3. **H24 and H25 leave this project.** F10 and F12 are reported to `injury-fatigue`, with F11 as its lead (I29).
4. **Our own walk-forward expected pass chance** replaces nflverse's `xpass` for levels (F13): refit each season, centred on the league's level so far. A technical call.
5. **Volume uses the game state, not just the line** (F16): the line's effect comes through the score, mostly in the fourth quarter.
6. **Schemes-v2's pass rate and tempo could move to the full sample** (F5, F6), as a new version of schemes. It's a technical call for later: pace tests the full-sample habits first.

## What not to redo
- Close-games-only pace as the main measure: once the clock is known, the full sample is steadier (F5).
- Win chance as a play-level pass input on top of `xpass`: it's already inside (F2).
- Fatigue carried from the first half to the second, by injuries or EPA (F10, F12).
