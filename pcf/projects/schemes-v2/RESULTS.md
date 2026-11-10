# Results: Schemes v2 (`schemes-v2`)

**Date:** 2026-11-10 · **Brief:** [BRIEF.md](BRIEF.md) · **MLflow experiment:** `schemes-v2` · **Champion:** none registered (no project has a logged model yet; registry `elo` card)

## In short
A team's play style is a real, lasting trait that follows its head coach, and PCF now forecasts four of them for the next game before kickoff: pass rate over expected, shotgun rate, tempo and throw depth. All four beat every simple average on 2016–2024, and three of the four do on the 2025 vault (throw depth ties the league average). Using an option less is a real anti-trait on offense (teams that pass less gain less when they pass), but as a next-game forecast it fails the vault. Scheme against scheme, the CEO's conditional question, found nothing usable: charted types show nothing, and types learned from results are a faint in-season signal that doesn't help a margin forecast.

**Scorecards:** `data/outputs/schemes-v2/<variant>/<run_id>/scorecard.html` (MLflow experiment `schemes-v2`) · **Vault:** opened 2026-11-10, once, for the five final models (R12) · **Versions tried:** traits 2 (rung 1, rung 2), anti-traits 4 per option

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal, or beats baselines | Traits: every final model beats 100 of 100 shuffled refits, on 2016–2024 and on the vault, and beats its averages (R1, R11, R12). Pass anti-trait blend: passes on 2016–2024 (R5), **fails on the vault** (4 of 100; R12) |
| Calibration and range coverage | 80% ranges hold 79–80% for every final model, on 2016–2024 and the vault |
| Leakage | Every blocking check passes for every run (R2, R10) |
| Football sanity | The pass blend's top and bottom teams make sense (R5); playoffs are the one clear miss (Where it misses) |
| CEO spot-checks | 2026-11-09: F20 (corrected), F24 (holds), R6 (holds, as comparative advantage). 2026-11-10: F28 (holds) |

## Hunch verdicts
Final verdicts, copied into [`projects/HUNCHES.md`](../HUNCHES.md).

| # | Hunch | Verdict | Evidence, with its size |
|---|---|---|---|
| H9 | Style pairings (rock-paper-scissors) predict margins | **unclear, leaning failed** | Pairings predict the margin's miss against the close at r +0.035 (5% by chance, about 0.4 points per sd: F9); no pairing part in rematches (F20), and learned types don't help Elo or the close (F28) |
| H10 | What follows a coach is the scheme; what follows a player is the role | **held, for head coaches** | Shotgun, no-huddle, tempo, personnel and coverage follow the coach (F3, F4); the coach's history earns 0.15–0.29 of the blend's weight for three traits (R3). Coordinators untested |
| H11 | Schemes explain game states and comebacks | **failed for comebacks** | The win chance already knows comebacks; schemes add a faint second-half margin signal (F19) |
| H12 | Changing schemes costs players | **unclear, leaning failed** | No general cost for 193 receivers or 59 QBs; receiver depth fit leans right (F13, F14) |
| H13 | Teams morph against opposing schemes | **failed for head coaches** | Teams bend, but all the same way (22 of 98 pairs); a coach's own bend doesn't repeat (5 of 98: F10–F12). The average bend is in rung 2 (R11) |
| H14 | Schemes are conditional: an offense does well against one type of defense and badly against another | **failed for charted types; unclear for learned ones** | Charted types: nothing (F7, F8, F21–F23, F25). Types learned from results: r +0.031 as a forecast (F26), not strengthened (F27), no help in a margin forecast (F28) |
| H15 | Anti-clusters: avoided options are limits | **held in part, as comparative advantage** | Offense keeps the sign held out (+0.015 per sd, 196 of 200: R6), but it lives at the pass-heavy end (spot-check), and the forecast fails the vault (R12). Defense: no |
| H16 | The CEO's four pairings | **failed** | None passes; two lean the CEO's way (F23) |
| H17 | Schemes mask weaknesses (coaches lean into strengths) | **unclear, supported in direction** | Avoiders are no worse at passing than average teams; heavy passers are better (R6 spot-check: fifths −0.037, −0.039, −0.044, −0.006, +0.070) |

## Terms
- **Trait:** a team's tendency (pass rate over expected, shotgun rate, tempo, throw depth) as a lasting property, forecast for its next game.
- **Anti-trait:** a team's low use of an option, read as a possible limit; tested by whether low users gain less from the option (decision 0024).
- **Gain from an option:** EPA per play with the option less without, in neutral situations (decision 0024).
- **Opening coach:** a team's head coach for its first regular-season game, known from the start of week 1 (decision 0025).
- **Opponent's bend:** how far offenses move off the league's level against a given defense (exploration F10), as a shrunk season gap (decision 0025).
- **Matchup type (learned):** two hidden numbers per offense and defense, learned from results within a season, whose product is the matchup part (F24, F26).

## What's built so far
- **`team_game.tendencies`** ([decision 0023](../../docs/decisions/0023-team-game-tendencies.md)): each team's tendencies per game from play-by-play, in neutral situations, 1999 on, known the day after the game. Any project can read it.
- **Trait forecasts** (`pcf.experts.schemes_v2`): each team's tendency in its next game, predicted on Saturday (Thursday games on Thursday), for four traits. Each has three simple averages (rung 0) and a fitted blend (rung 1).
- **Gains per game** ([decision 0024](../../docs/decisions/0024-anti-traits.md)):
  - in `team_game.tendencies`: each offense's gain from passing and from the shotgun (EPA per play with the option less without);
  - a new post-season part, **`team_game.charted`**, 2016 on, known after the season: each defense's man coverage, two-high shells and blitzes, its use over the league's usual choice for the look, and its gain (EPA prevented).
- **Anti-trait forecasts** (`anti_model.py`, the CEO's calls of 2026-11-09): each team's gain from an option in its next game, for pass and shotgun (live) and man, two-high and blitz (from finished seasons). Each option has:
  - two averages (rung 0): the league's gain and the team's own past gain;
  - the anti-trait (rung 1): the league's gain plus a weight on the team's use;
  - a blend (rung 1): the same plus its past gains.
- **Retrospective traits** ([decision 0026](../../docs/decisions/0026-team-season-charted-traits.md)): a new table, **`team_season`**, with one part, `charted`. It holds each team's charted choices per season, 2016 on, known after the season, with `prior_for` saying which season may use them (R13).

## Findings

**R1. The blend beats every simple average for all four traits, on 2016–2024** (walk-forward, about 4,950 team-games each; MLflow experiment `schemes-v2`, runs `ce050b08` pass rate, `d200bcfa` shotgun, `44a58bad` tempo, `51396e30` depth).

| Trait | Typical miss: league average | Last 4 games | Season to date | **Blend** | Prediction against result (r) | 80% range holds |
|---|---|---|---|---|---|---|
| Pass rate over expected | 0.076 | 0.075 | 0.074 | **0.070** | +0.35 | 79.4% |
| Shotgun rate | 0.142 | 0.100 | 0.100 | **0.097** | +0.72 | 80.4% |
| Tempo (seconds per snap, clock running) | 2.22 | 2.13 | 2.12 | **2.00** | +0.41 | 79.7% |
| Throw depth (air yards per attempt) | 2.29 | 2.42 | 2.39 | **2.25** | +0.18 | 80.4% |

- Typical miss is the mean absolute error, in the trait's own units (rates are 0–1).
- On the range score (the harness's main score), the blend beats each yardstick with the whole 90% interval below zero, for every trait.
- **Throw depth is the weak one:** a team's own recent depth predicts *worse* than the league average (single games are noisy), and the blend gains only 1.5% on the league. It's a trait, but a faint one per game.

**R2. Every blocking check passes for all four blends:** the gateway-only, known-at, future-perturbation and future-deletion checks (identical at 25 cutoffs), cadence, walk-forward, test labels, and the signal test (each blend beat 100 of 100 refits on shuffled outcomes; 95 needed).

**R3. What the blend weighs** (the last training window; weights on each gap from the league's level):

| Trait | Shrunk season | Last 4 games | Last season | Head coach's history |
|---|---|---|---|---|
| Pass rate over expected | 0.47 | 0.22 | 0.09 | 0.15 |
| Shotgun rate | 0.41 | 0.47 | 0.02 | 0.18 |
| Tempo | 0.40 | 0.24 | 0.06 | 0.29 |
| Throw depth | 0.35 | 0.08 | 0.22 | 0.03 |

- **The coach's history earns weight** for tempo, shotgun and pass rate, beyond the team's own season: the exploration's "schemes follow the coach" (F4), now inside a forecast.
- It earns nothing for throw depth, which the exploration tied to the QB and roster.

**R4. Early in the season the gain is smaller.** In a team's first two games of a season, the blend's edge on the league average is about a third to a half of its edge from game 6 on (pass rate: 0.071 against 0.073 early; 0.070 against 0.076 late). A new head coach's history can't be used before their first game, because the coach is in the pregame part, known at kickoff (decision 0023, call 4).

**R5. As next-game forecasts, only the pass blend beats its yardsticks, and only by a sliver** (walk-forward: offense 2016–2024, blitz 2018–2024, coverage 2020–2024). A single game's gain is mostly noise. Its spread is 0.57 EPA a play for passing, 0.70 for the shotgun, and about 1.0 for the defensive options.

| Option | Typical miss: league's gain | Own past gain | **Anti-trait** | Blend | Signal test (shuffled refits beaten, 95 needed) |
|---|---|---|---|---|---|
| Pass | 0.405 | 0.437 | 0.405 | **0.404** | anti-trait 70; **blend 100** |
| Shotgun | 0.471 | 0.513 | **0.471** | 0.471 | anti-trait 88; blend 72 |
| Man | 0.754 | 0.778 | 0.754 | 0.754 | anti-trait 32 |
| Two-high | 0.689 | 0.706 | 0.691 | 0.692 | anti-trait 55 |
| Blitz | 0.777 | 0.798 | 0.777 | 0.777 | anti-trait 76 |

- **Typical miss** is the mean absolute error, in EPA per play.
- **The pass blend:**
  - On the range score, it beats the league's gain, its own past gain and the anti-trait alone, with each 90% interval below zero. Against the league, the gap is −0.001, with an interval from −0.001 to −0.000.
  - Its ranges hold 80.3% of results.
- **Every blocking leakage check passes** for every variant run. The only failures are signal tests.
- MLflow runs (experiment `schemes-v2`): `efe03777` pass anti-trait, `9633e3c8` pass blend, `ce2bb226` shotgun anti-trait, `956e22ef` shotgun blend, `a1f436e6` man, `0c667ca0` two-high, `d7f0a2f0` blitz. The defensive blends weren't run through the harness: their anti-trait fails and their quick walk-forward is no better (the table above).
- **A team's own past gain alone is worse than the league's for every option.** Single-game gains are too noisy to average.
- **Football sanity:**
  - the pass blend's top forecasts are the 2016–18 Falcons (Matt Ryan, with Shanahan, then Sarkisian) and Brady's 2017 Patriots;
  - its bottom ones are the 2024 Panthers, around Bryce Young's benching.

**R6. The offensive anti-traits keep F18's sign on held-out seasons. The defensive ones don't.** *(Spot-checked 2026-11-09, below: pass holds after a situation adjustment but lives at the pass-heavy end; shotgun's weighted version is fragile.)*

How it's tested ([`explore/anti_sign.py`](explore/anti_sign.py)):
- nothing is fitted, so every season is held out;
- the measure is the slope of a game's gain on the team's use known before kickoff, weighted by the gain's plays;
- the 90% intervals come from resampling team-seasons;
- the null is 200 shuffles within each week.

| Option | Slope (EPA a play per sd of use) | 90% interval | Shuffles beaten (of 200) | Seasons positive |
|---|---|---|---|---|
| Pass | **+0.015** | +0.004 to +0.026 | 196 | 8 of 9 |
| Shotgun | **+0.018** | +0.004 to +0.032 | 198 | 7 of 9 |
| Man | +0.000 | −0.025 to +0.030 | 2 | 3 of 5 |
| Two-high | −0.009 | −0.031 to +0.011 | 86 | 1 of 5 |
| Blitz | −0.016 | −0.040 to +0.006 | 153 | 3 of 7 |

- **Positive means F18's sign:** teams that avoid passing or the shotgun gain less from them when they use them. The sizes are in line with the exploration's pregame look (F18: +0.031 and +0.016 per sd, on a different scale).
- **The weight holds when refitted:** at four cutoffs (2018, 2020, 2022, 2024), the anti-trait's weight on use is above zero every time, for pass (+0.019 to +0.026 per sd) and for shotgun (+0.015 to +0.032).
- **On defense, last season's avoidance says nothing about this season's gain.** There are two possible reasons, and this build can't separate them:
  - defensive choices react to the opponent far more than offensive ones do (in CONSISTENCY, what defenses allow repeats much less than what they choose);
  - a defense's features are a season old and span coordinator changes.

**R7. The CEO's "against that opponent" part adds nothing on offense.** Use without the opponents' part predicts the gain as well or slightly better (pass +0.017, shotgun +0.019 per sd). This matches F17, where the opponent's part of the usual choice mattered only for stacked boxes.

**R8. For passing, avoidance and past gains mostly tell the same story. For the shotgun, avoidance is the story.**
- **Pass blend:** the past gains (shrunk season, last season, the coach's) take most of the weight. Use keeps +0.006 to +0.011 per sd.
- **Shotgun blend:** the past gains earn about nothing, because the shotgun's gain doesn't repeat (R9). Use carries it, at +0.014 to +0.032 per sd.
- *Football reading:*
  - a team that passes less than expected is usually one whose passing has gone worse, so it's partly the same fact twice;
  - under-center teams that do go to the shotgun do worse from it, and their own past shotgun gain can't show that because it's too noisy.

**R9. The second test (consistency, 2006–2024 regular season).** Rows in CONSISTENCY.md.
- **Passing's gain per game is a faint trait:** 0.11 week to week, 0.25 season to season.
- **The shotgun's gain and every defensive gain are noise.** Man's gain is a state.
- **Defensive use over expected is a strong trait:** 0.67–0.76 week to week, about 0.48 season to season.
- So, on this evidence, a defense's avoidance is a real style but not a limit.

**R10. A new head coach now counts from week 1 (decision 0025). It's a small gain, and only the shotgun shows it clearly.** ([`explore/rung2_check.py`](explore/rung2_check.py))
- **The rule:** each team's coach for its first regular-season game is a new part, `team_game.opening_coach`, known at the start of week 1 (hires are announced months earlier). Before, a new coach's history could only help from their second game (R4).
- **What it changed** (the same blend before and after; 2016–2024; 61 first games with a new coach that have a result):

| Blend | All rows: range score change (90%) | First games with a new coach: change (90%) | Their typical miss, before → after |
|---|---|---|---|
| Pass rate over expected | −0.00000 (tie) | −0.00022 (−0.00056 to +0.00018), tie | 0.0660 → 0.0654 |
| **Shotgun rate** | **−0.00004 (−0.00007 to −0.00002), better** | **−0.0016 (−0.0031 to −0.0001), better** | **0.1451 → 0.1404** |
| Tempo | −0.0001 (tie) | −0.012 (−0.049 to +0.031), tie | 2.844 → 2.850 |
| Throw depth | −0.00001 (tie) | −0.0002 (tie) | 2.078 → 2.072 |
| Pass anti-trait blend | +0.00001 (tie) | −0.00000 (tie) | 0.3669 → 0.3642 |

- **Football reading:** the shotgun follows the coach most (exploration F4), so it gains most when the coach is known in time. Leakage checks pass for every variant (gateway, known-at, future perturbation and deletion at 25 cutoffs, test labels; the signal test beat 100 of 100).

**R11. Rung 2 beats the blend for pass rate, shotgun and throw depth, by small margins. Tempo stays at the blend.** (Regular-season rows, 2016–2024, where a team's game number is known.)

| Trait | All rows: range score change (90%) | Games 1–4 | Games 5+ | Typical miss, blend → rung 2 | Verdict |
|---|---|---|---|---|---|
| Pass rate over expected | −0.00015 (−0.00023 to −0.00008) | −0.00012, tie | −0.00016, better | 0.0703 → 0.0699 | **rung 2** |
| Shotgun rate | −0.00031 (−0.00043 to −0.00018) | −0.00061, better | −0.00021, better | 0.0973 → 0.0964 | **rung 2** |
| Tempo | −0.00045 (−0.00153 to +0.00067), tie | tie | tie | 1.999 → 1.996 | blend |
| Throw depth | −0.0014 (−0.0027 to −0.0001) | −0.0006, tie | −0.0016, better | 2.239 → 2.232 | **rung 2** |

- **What rung 2 adds:** early-season weights (each gap × 4 ÷ (4 + games)) and the opponent's bend (what offenses do against the opposing defense: F10's average bend). Tempo has no defensive column, so it gets only the early weights, and they don't help.
- **The takeaways it used from rung 1 (rule k):** the same four gaps (R3), R4's smaller early-season edge (so weights that change with games), and the exploration's average bend (F10), not a coach's own bend (failed, F11).
- **The gains are about 0.5–1% of the typical miss.** They're real by the harness's bar but small, which is about what a sticky trait leaves for a better model.
- **Rung 3 (trees) wasn't tried** (a technical call, below): the gain from rung 1 to rung 2 is already this small.

**R12. The vault (2025, opened once on 2026-11-10): the trait forecasts hold, except throw depth, which ties the league. The pass anti-trait fails.** ([`explore/vault_check.py`](explore/vault_check.py); 570 team-games each)

| Final model | Against the league's level: range score change (90%) | Typical miss, league → model | Prediction against result (r) | Against its own yardsticks | Signal (shuffled refits beaten) | Ranges hold |
|---|---|---|---|---|---|---|
| Pass rate over expected (rung 2) | −0.0011 (−0.0016 to −0.0006), **better** | 0.0747 → 0.0717 | +0.31 | ties the blend | 100 of 100 | 78.9% |
| Shotgun rate (rung 2) | −0.0118 (−0.0138 to −0.0100), **better** | 0.132 → 0.093 | +0.67 | beats the blend | 100 of 100 | 80.5% |
| Throw depth (rung 2) | −0.0071 (−0.0149 to +0.0005), tie | 2.234 → 2.208 | +0.13 | beats the blend | 100 of 100 | 79.5% |
| Tempo (blend) | −0.034 (−0.053 to −0.015), **better** | 2.043 → 1.931 | +0.28 | beats the league, last 4 and season averages | 100 of 100 | 79.8% |
| Pass anti-trait (blend) | +0.0005 (−0.0003 to +0.0013), tie | 0.399 → 0.400 | −0.01 | ties the league and the anti-trait alone; beats its own past gain | **4 of 100: fails** | 79.8% |

- **The traits generalise to an unseen season.** Throw depth's tie matches R1, where it was the weak one.
- **Rung 2's edge doesn't show for pass rate on one season.** It beats the blend for shotgun and depth, and ties it for pass rate. One season is 570 rows, against 4,777 in development.
- **The pass anti-trait forecast is gone on the vault,** as the case against warned (point 2): its 0.001 edge on 2016–2024 was the size of a single season's noise. The anti-trait's *sign* (R6) wasn't re-tested on 2025, and shotgun and the defensive options weren't final models, so they weren't run.
- **The vault is now spent for these models:** any change to them goes to the live ledger as its only honest test (VALIDATION §1).

**R13. The retrospective traits table (2026-11-10, the CEO's call): every charted trait repeats season to season, and the charting's level shifts by season, so compare seasons over expected.** ([`explore/team_season_check.py`](explore/team_season_check.py); [decision 0026](../../docs/decisions/0026-team-season-charted-traits.md))
- **What it is:**
  - `team_season.charted` has one row per team and season, 2016–2025 (320 rows);
  - it holds each team's charted choices over the regular season, in neutral situations;
  - the offense's personnel 11, 12, 21 and heavy, the pistol, and time to throw;
  - what the offense faced: box, man, two-high and blitz;
  - the defense's box, man, two-high, blitz, pass rushers, nickel and dime;
  - each comes raw and over expected, with play counts.
- **Timing, for later models:**
  - `known_at` is the day after the Super Bowl (participation's rule);
  - `first_kickoff` and `last_kickoff` give the games it sums up;
  - `prior_for` (the season + 1) is the first season an in-season model may use the row.
  - The gateway hides an unfinished season's row from in-season views whatever its date says, and leakage check 2 fails any row known before its last game.
- **Consistency** (per team-game, odd weeks against even and season to season):
  - every measure is a trait;
  - offense choices repeat 0.84–0.95 within a season and 0.38–0.71 across seasons. 21 personnel (0.68) and the pistol (0.71) are the most lasting choices PCF has measured;
  - defense choices repeat 0.67–0.93 and 0.44–0.54. Nickel and dime are the strongest;
  - what an offense faces repeats less within a season (0.18–0.44), but as much across seasons (0.33–0.37). That's how defenses respect an offense.
- **Football sanity holds:**
  - most man: the 2018–19 Patriots; least man and least two-high: the Chargers (single-high zone);
  - most 21 personnel: the 2023 Dolphins and 2018 and 2025 49ers;
  - most pistol: the 2019–20 Ravens;
  - most blitz: the 2023 and 2025 Vikings (Flores);
  - quickest throws: the 2020–21 Steelers and 2023 Dolphins; slowest: the 2016 Bills.
  - Some teams never use two backs on neutral plays (2–5 a season), which is real.
- **The raw rates aren't comparable across seasons.** The league's man rate is 0.41 in 2023, 0.49 in 2024 and 0.30 in 2025; the pistol is 0.044, 0.105 and 0.057. Those are charting shifts, not football. Use the `_oe` columns across seasons.
- **A fix it brought:** `team_game.charted` missed fullbacks from 2023 on, so 5–7% of plays had the wrong look. The heavy share was 28–34%; it's 34–40% with fullbacks counted. The part is rebuilt. The defensive anti-trait variants, which read it, weren't rerun: they're research only and not on the vault.

## The ladder
| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | Averages: the league's level, last 4 games, season to date (traits); the league's gain, own past gain (anti-traits) | — | The own averages beat the league for the sticky traits (shotgun, tempo); single-game gains are too noisy to average (R5) |
| 1 | Weighted least squares on the league's level and four gaps (shrunk season, last 4, last season, the head coach's); the anti-trait adds the team's use | Beats every average for all four traits (R1); only the pass anti-trait blend beats its averages, by a sliver (R5) | The coach's history earns weight for three traits (R3); the early season gains less (R4) |
| 2 | Rung 1 + early-season weights + the opponent's bend | Beats rung 1 for pass rate, shotgun and depth; ties for tempo (R11); on the vault, beats it for shotgun and depth, ties for pass rate (R12) | Stop here: the gain is about 0.5–1% of the typical miss |

## Where it misses
The miss lenses are for player-game models; for team-games, these (the final models, 2016–2024; average miss is actual less predicted, 90% interval by week; [`explore/rung2_check.py`](explore/rung2_check.py)):

| Lens | Group | Rows | Pass rate over expected | Shotgun rate | Tempo (seconds a snap) | Throw depth (yards) |
|---|---|---|---|---|---|---|
| Season stage | **Playoffs** | 174 | **+0.013 (+0.005 to +0.023)** | **+0.015 (+0.001 to +0.030)** | **+0.47 (+0.22 to +0.72)** | +0.07, tie |
| Season stage | A team's games 1–4 | 1,152 | +0.002, tie | −0.000, tie | −0.09, tie | −0.03, tie |
| Coaching | First game with a new head coach | 61 | −0.012, tie | +0.008, tie | +0.17, tie | −0.25, tie |
| Season stage | Everything else | 3,625 | −0.005 (−0.007 to −0.002) | −0.004 (−0.007 to −0.001) | +0.04, tie | −0.05, tie |

- **Playoff teams pass more, use the shotgun more and play slower than their regular season says.** That's a playoff flag (IDEAS I28).
- The regular season's small negative misses are the other side of the same thing: the model's level carries a little of the playoffs.

## Against the brief's draft tests
| Test | Result so far |
|---|---|
| Each trait repeats | Yes (CONSISTENCY.md, exploration F2) |
| Known before kickoff, it predicts the team's own next-game tendencies better than the league average and a rolling mean | **Yes, all four** (R1); on the vault, three of four beat the league (throw depth ties: R12) |
| The shuffled version shows nothing | **Yes** (R2) |
| The anti-trait term keeps F18's sign on held-out seasons | **Yes on offense** (pass, shotgun: R6); **no on defense** (man, two-high, blitz) |
| The shuffled-team version of each shows nothing | Offense: the real slopes beat 196 and 198 of 200 shuffles (R6). As forecasts, only the pass blend passes the harness's signal test (R5), and it fails on the vault (R12) |

## Scheme against scheme (discovery, not confirmed)
Discovery ran the CEO's order A → B → E → C → D on 2026-11-09. Full write-up in [EXPLORATION.md](EXPLORATION.md), F20–F25.
- **No measurable conditional part in rematches (F20, corrected at the CEO's spot-check):** an offense's result against a defense repeats in the rematch only as much as each unit's own form predicts. The pairing-specific part is +0.1% of what strength leaves (90% −4.2% to +4.6%). The first reading, 9%, came from a bias in the baselines.
- **Charted scheme types show nothing either:**
  - the play-by-play map has real interactions but carries nothing to games (F21);
  - look-alike opponents don't get look-alike results (F22);
  - the CEO's four pairings don't pass (F23);
  - the wide scan holds out at the shuffled level (F25).
- **Types learned from results are the one lead:** in 2015–2024 they predict held-out pairings at r +0.05 (+0.036 without 2021, beyond 95% of shuffles), even for pairs that never met, and survive an in-season trend control. There's nothing before 2015, and they match no charted style (F24). As a forecast from earlier games only, r +0.031 (F26); no variant strengthens it, and last season's types predict nothing (F27); in Elo's margin forecast it's neutral and fails signal (F28). Parked for live seasons (IDEAS I26).

## The case against (2026-11-09, written before the merge)
The strongest argument that these results are wrong or overstated:
1. **The confirmation isn't independent of the discovery.**
   - Pass and shotgun were picked as the anti-trait options *because* they worked in the exploration (F17–F18), on the same 2006–2024 seasons the build then "confirms" on (R6).
   - The walk-forward harness keeps each forecast honest in time, but not the choice of what to forecast.
   - Only the vault (2025, unread) or live seasons are a clean test, and neither has been run.
2. **The one anti-trait forecast that passes does so by a sliver.** The pass blend beats the league's gain by 0.001 on the range score (interval −0.001 to −0.000). That's practically nothing, and it could vanish on the vault.
3. **The trait forecasts beat easy yardsticks.** Tendencies are sticky, so beating the league and season averages is the expected part. Whether any of this helps a downstream model (margins, totals, player projections) is untested.
4. **Defensive charting comes after the season,** and it's charted on dropbacks only. Every defensive number rests on one source's charting, which nobody has audited.
5. **The matchup ceiling (F20) rests on a model of the residual:**
   - it assumes form adds up (offense form + defense form + pairing);
   - the nulls use the 3 nearest games;
   - strengths use the whole season;
   - home and away aren't modelled (they alternate in rematches, which biases *against* finding a repeat).
   **The CEO's spot-check confirmed this one:** the baselines were biased low, and the 9% falls to +0.1% when corrected (see below).
6. **Seven cuts were looked at in F20 and many settings in F24.** F24's robustness check was run after seeing the result, and 2021 drives much of it.
7. **The project isn't done.** The vault, the interface card, saved walk-forward outputs and retrospective traits are still open. This merge brings tested, unvalidated code to main. Nothing reads it yet, and the scheduled workflows (odds, nflverse snapshots) don't run it. *(2026-11-10: the vault and the interface card are done; see points 8–12.)*

**Added 2026-11-10, before the second merge:**

8. **The vault is one season.** 570 team-games can confirm a large edge (shotgun, tempo) but not a small one: pass rate's rung-2 gain and throw depth both tie there. Rung 2 was chosen on 2016–2024 alone, and for pass rate it's unconfirmed.
9. **The trait forecasts haven't been shown to help anything downstream.** They beat averages of themselves. Whether a margin, total or player model gains from them is untested (case against point 3 still stands). Of the downstream tests run, the only one (the learned matchup term in Elo, F28) found nothing.
10. **Rung 2's opponent bend uses what offenses did against the defense, which partly reflects which offenses it faced.** The shrinkage and the league gap soften this, but a strong schedule can pass for a bend. The leakage checks can't see it: it's a confound, not a leak.
11. **The coach rule assumes every opening coach was announced before week 1.** That's true for every hire in 2016–2024 as far as I know, but it's not checked against dated news.
12. **The project's one surviving anti-trait forecast is gone** (R12). The anti-trait story now rests on R6's held-out sign, which is a relationship, not a forecast, and was itself chosen on the same seasons.
13. **The retrospective table is measured, not tested** (R13):
    - Nothing shows it helps a forecast. "Trait" means it repeats, not that it predicts anything.
    - Its `known_at` trusts participation's rule (the day after the Super Bowl), which isn't checked against when nflverse actually published each season. If it's early, only a model run in the weeks right after a Super Bowl could see a row too soon.
    - The fullback fix changed `team_game.charted` for 2023–2025 after R6 and R9 were measured on it. Neither was rerun; both used 2016–2024, so only 2023–2024 moved.

## The CEO's spot-check (2026-11-09): F20 and F24
**F20, the rematch ceiling: wrong as first written, now corrected.** ([`explore/spot_f20.py`](explore/spot_f20.py), [`explore/spot_f20b.py`](explore/spot_f20b.py))
- **The rows:** the strongest repeats look football-sensible:
  - the 2021 Bengals offense against the Ravens: +1.5 and +2.3 sd;
  - the 2020 Browns offense against the Bengals: +1.6 and +2.2;
  - the 2019 Jets offense against the Patriots: −2.4 and −2.0.
- **The alternative that broke it:** F22's symmetric exclusions, where every pair leaves out both of its games.
  - Under them, the same offense against *other* defenses agrees at +0.046, and the same defense against other offenses at +0.041.
  - The rematch's +0.088 is just those two added together.
  - F20's baselines had let the first meeting's strength include the baseline game, which built in a negative correlation and pushed both baselines to about 0.
- **Corrected:**
  - **pairing share +0.1% (90% −4.2% to +4.6%);**
  - gap-matched +0.8%;
  - strength removed in full −1.4%;
  - home field changes nothing.
- **What would change the answer:** more rematches. The data still allows up to about 5% (r up to about 0.2), so a small conditional part isn't ruled out.

**F24, types learned from results: holds up.** ([`explore/spot_f24.py`](explore/spot_f24.py))
- **The rows:** the learned 2021 defensive direction runs from Cleveland, Chicago and New England at one end to Buffalo, Baltimore and Indianapolis at the other. Its offensive direction runs from Houston and San Francisco to Cincinnati and Indianapolis. It matches no charted style beyond chance (the largest is blitz, r +0.32).
- **The alternatives:**
  - 5 random seeds give r +0.046 to +0.062;
  - without 2021 it's +0.036, beyond the shuffled 95th percentile of +0.026;
  - an in-season trend per unit (teams improving or fading) leaves it at +0.055.
- **What would change the answer:** the forecast version (earlier games only) failing, or 2025+ live seasons showing nothing, as 2006–2014 did.
- **Its own design** (the strengths and the matchup part both fit on the same training folds, and a shuffled-pairing null centred at about 0) doesn't have F20's flaw.

**R6, the pass anti-trait: the slope is real, but it lives at the pass-heavy end.** ([`explore/spot_r6.py`](explore/spot_r6.py), the CEO's second pick)
- **The worry checked:** `pass_gain` is plain EPA on dropbacks less EPA on runs, while use is situation-adjusted. So run-heavy teams might show a lower gain just because they throw on third and long.
- **The alternative:** each play is measured against the league's mean EPA for the same choice in the same down, distance (4 buckets), field zone (4) and season. The same features go through R6's exact test.

| Version | Pass: slope per sd [90%], shuffles beaten, seasons positive | Shotgun |
|---|---|---|
| As published (raw gain, weighted by plays) | +0.0153 [+0.0038, +0.0258], 196/200, 8/9 | +0.0183 [+0.0046, +0.0336], 197/200, 7/9 |
| **Situation-adjusted** | **+0.0129 [+0.0014, +0.0241], 194/200, 7/9** | **+0.0074 [−0.0064, +0.0214], 128/200** |
| Raw, unweighted | +0.0185 [+0.0028, +0.0337], 199/200 | +0.0405 [+0.0199, +0.0628], 200/200 |
| Situation-adjusted, unweighted | +0.0159 [−0.0004, +0.0320], 189/200 | +0.0372 [+0.0160, +0.0580], 200/200 |

- **Pass survives:** the situation mix explains about a sixth of the slope.
- **Shotgun is fragile.** Weighted by plays, as published, it falls below the bar once adjusted. Unweighted, as the expert's target is (decision 0024), it stays strong. The difference comes from games where one side of the choice has few plays. So R6's shotgun line needs this caveat.
- **The rows** (team-seasons with 8+ test games; gain in EPA a play):
  - *Most pass-heavy:* the 2016–2022 Chiefs (adjusted gain +0.16 to +0.30), the 2022–2024 Bengals (+0.06 to +0.25), and the 2016 Packers (+0.23).
  - *Most pass-avoiding:* mixed. The 2020 Patriots (−0.56), 2017 Bears (−0.30), 2022 Falcons (−0.12) and 2022 Bears (−0.09) are low, but the 2018 Seahawks (+0.28) and 2022 Saints (+0.15) are high.
  - *By fifth of use:* adjusted gain −0.037, −0.039, −0.044, −0.006, **+0.070**.
- **What this changes:** the bottom three fifths are flat. **Avoiders are no worse at passing than average teams. Heavy passers are better.** That's comparative advantage (the CEO's H17: coaches lean into what their players do best), not a limit marked by avoidance (H15's reading). As a forecast feature it's still sound, but it mostly says "elite passing teams pass a lot". In the blend, the past gains already carry most of it (R8).
- **What would change the answer:** the vault or live seasons, and a version with the QB's own past efficiency in the baseline (does use add anything beyond the QB?).

## The CEO's spot-check (2026-11-10): F28, the matchup term in Elo's margin forecast
**F28 holds: the term points the right way, but it's too small to pay for itself.** ([`explore/spot_f28.py`](explore/spot_f28.py))
- **Reconciled with F26:** on the 1,663 games of 2016–2024 that have a term, it correlates with the margin's miss at +0.035 against the close and +0.037 against Elo. That's the same signal as F26 (+0.029), so the pipeline is right.
- **The weight is positive in 8 of 9 seasons:** about +0.35 to +0.6 points per sd of the term. The exceptions are +0.97 in 2019 and −0.13 in 2021.
- **The rows:**
  - by fifth of the term, the margin beats the no-term blend by −0.62, +0.43, −0.57, +0.95 and **+1.63** points (the top fifth favours home most). The ends point the right way; the middle is noise.
  - the 12 games the term moved most are all in weeks 14–18, ten of them in the season's final two weeks, when teams rest starters and Elo is weakest (elo F12, F14). The term moved 3 of those 12 closer to the result, and 44% of the 100 biggest moves.
- **Other scores agree:** the means' typical miss goes from 10.060 to 10.068 points, and the squared miss from 169.15 to 169.18.
- **The alternative:** blends trained from 2015, where F26's signal lives, are no better (+0.0016, −0.0025 to +0.0059, neutral; weeks 6+ +0.0027).
- **Why a real but tiny signal fails here:** r +0.037 explains about 0.14% of a margin's variance. At best that's about 0.01 points of typical miss, and learning the weight from earlier weeks costs about as much as it gains.
- **What would change the answer:**
  - many more games (each live season adds about 270 with a term);
  - a term several times larger;
  - dropping the final two weeks, where the biggest moves go wrong. That's a cut chosen after seeing the rows, so it would have to be tested on live seasons, not here.

## Pitfalls
- **Asymmetric exclusions in a leave-out baseline** (F20): a baseline pair must leave out both of its games, or a negative correlation is built in. It turned a +0.1% result into 9%, caught only at the CEO's spot-check.
- **League trends pass for consistency** unless every tendency is taken against its season mean (exploration pitfalls).
- **A situation mix can pass for a limit** (R6 spot-check): pass gain is plain EPA on dropbacks less runs, so run-heavy teams' third-and-long throws pull it down. Adjusting by down, distance and field zone took a sixth off the slope.
- **Weighted and unweighted versions can disagree** (R6 spot-check, shotgun): games where one side of a choice has few plays drive the weighted slope.
- **A tiny real signal fails a downstream forecast** (F28): r +0.037 is about 0.14% of a margin's variance, less than the cost of learning its weight.
- **Defensive charting is post-season and dropbacks only:** "zone against the run" can't be seen, and an in-season model can use only finished seasons (rule m).
- **A game's own coach is known only at kickoff** in nflverse; the opening-coach part fixes week 1 only (decision 0025).

## Not looked at
- **Coordinators:** the table is signed off in principle but not built. H10 and H13 are tested for head coaches only.
- **Retrospective traits as forecasts:** the table (R13) measures them; whether last season's row helps any in-season model is untested.
- **Rung 3 (trees)** for the traits (technical call below).
- **Downstream use:** the traits as features in a margin, total, pace or player model (case against point 9).
- **The anti-trait's sign on the vault** (only the forecast was run there), and the shotgun and defensive options on the vault (not final models).
- **Player-level scheme fit** beyond receivers' depth (I23) and a QB's coverage split (I22, killed).

## Could be improved
1. **A playoff flag** for the traits (Where it misses: playoff teams pass more, use the shotgun more and play slower; IDEAS I28).
2. **Test the traits downstream:** pace and totals (tempo, pass rate) and player volume (pass rate, depth) are the natural first users.
3. **The coordinator table,** then retest H13 and split the coach's weight between head coach and play caller.
4. **Live checks on 2026+** for what the vault couldn't settle: rung 2 for pass rate, throw depth against the league, the learned matchup term (I26) and outside runs against man (I27).
5. **Dated coach hires** (a new source, needs sign-off) if week-1 forecasts ever matter more than about 6–8 teams a year.

## Don't redo
- **Charted scheme-against-scheme matchups on 2006–2024** (F7, F8, F21–F23, F25): every route found nothing, and the wide scan showed how a model can look strong in-sample and still do no better than shuffled pairings. Retry only with new seasons or a new kind of data (coordinators, tracking).
- **Strengthening the learned matchup types** (F27): success rate, passing and rushing apart, and types carried across seasons all did worse.
- **The learned matchup term in Elo or with the close** (F28): neutral, fails signal.
- **A general scheme-change cost for movers** (F13, F14) and **a coach's own morph** (F11, F12).
- **Defensive anti-traits from last season** (R6): no sign held out. Retry only with live in-season defensive columns or coordinators.

## Interface card
Also in this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `team_game` parts `schedule`, `pregame`, `opening_coach`, `tendencies` (live); `charted` (post-season, defensive anti-traits only); gateway only |
| **Outputs** | `pcf.experts.schemes_v2` variants; histories in `outputs/schemes-v2/<variant>/<run_id>/history.parquet`, per team-game: mean, q10, q50, q90. **Final:** `pass_oe_rung2`, `shotgun_rung2`, `depth_rung2`, `tempo_shrunk`. Anti-traits (`<option>_gain_*`) are kept for research, not as features: none passes the vault. **Retrospective traits:** the table `team_season.charted` (R13), per team-season, raw and over expected, read through the gateway |
| **Level of detail** | team-game (the offense's tendency in its next game) |
| **Interval** | every regular-season and playoff game, from week 1; 2016–2024 reported, 2025 the vault |
| **Cadence** | in_season (the `team_season` table: retrospective; in season, a prior from finished seasons only, `prior_for`) |
| **Known at** | the Saturday run (Thursday noon for Thursday games), like Elo; tendencies are known the day after each game |
| **How to use it** | As features for pace, totals and player volume, from saved histories only (rule e). Expect a typical miss of about 0.07 in pass rate over expected, 0.09 in shotgun rate, 1.9 seconds a snap and 2.2 air yards. Throw depth barely beats the league: weight it lightly. Add a playoff adjustment, or expect the playoff misses above. Live runs aren't scheduled yet |
| **Feeds** | pace (`pace`), game environments and totals, player opportunity and fantasy projections; scheme context for `roles-archetypes` |

## Open questions for the CEO
1. **Retrospective traits:** a measured table per team-season (no model), or a second expert with its own forecasts? (asked 2026-11-10) *Answered 2026-11-10: a table, with timing columns so later models can use it without leaking. Built: R13, decision 0026.*
2. **Which downstream model should test the traits first:** pace and totals, or player opportunity?
3. **Should the anti-traits be retired** after the vault, or kept for the 2026 live season as one more honest test of the pass sign (R6)?

## Technical calls (for veto at merge)
- **Decision 0023's eight calls:**
  - neutral situations only;
  - raw rates;
  - live columns only;
  - the coach from the latest known game;
  - 4 games' weight on the league;
  - a least-squares blend;
  - `elo` out of `depends_on` for now;
  - a Saturday run.
- **Decision 0024's eight calls:**
  - gains as plain EPA differences;
  - the shotgun's gain within passes and within runs;
  - a defense's usual choice from the season's cell means;
  - the offense's opponent part, and the raw shotgun rate (*changed from what I told the CEO before building*);
  - a defense's features from its last finished season only;
  - unweighted targets;
  - first training seasons 2017 (blitz) and 2019 (coverage);
  - the sign test as a script.
- **Discovery method calls (explore scripts only, no package code):**
  - the matchup residual is EPA per play beyond both units' season strength, leaving out the games compared (F20);
  - each null averages the 3 games nearest in week (F20);
  - the play map uses EPA beyond the situation, with each call interacted with down and long distance (F21);
  - unit splits are shrunk with 800 plays' weight (F21);
  - style similarity is the Euclidean distance between season style vectors (F22);
  - DL weight is the current listed weight (F23);
  - the learned-type settings were chosen on 2006–2014 and applied once to 2015–2024 (F24).
  - after the first merge: the forecast settings fixed from F24 (k 2, λ 1, from week 6: F26); the four strengthening variants and the prior's weight (λ0 4) fixed before running (F27); the term tested in Elo's own no-noise test, blends trained from 2010, 20 shuffles (F28).
- **Decision 0025's four calls (2026-11-10):**
  - the opening coach is known at the start of week 1, not the hire date;
  - only the first game gets an opening-coach row;
  - rung 2's early weight is 4 ÷ (4 + games), one per gap;
  - the opponent's bend is the opposing defense's shrunk gap from the league.
- **Finishing calls (2026-11-10):**
  - **stop the ladder at rung 2** (no trees): the rung-2 gain is about 0.5–1% of the typical miss;
  - **tempo stays at the blend** (rung 2 ties it);
  - **the vault ran the five final models only** (four traits and the pass anti-trait blend) with the league averages as yardsticks, test season 2025 alone;
  - **anti-traits aren't offered as features** after failing the vault.
- **Decision 0026's calls (2026-11-10, the retrospective traits table):**
  - a new `team_season` table (keys team and season), not a part of `team_game`;
  - regular season only, in neutral situations;
  - "over expected" against the league's season cell: down and distance for offense choices; plus shotgun and personnel group for defense choices and what an offense faced;
  - the timing columns `known_at`, `first_kickoff`, `last_kickoff` and `prior_for`;
  - one personnel parser for both formats, counting fullbacks as backs, which fixes and rebuilds `team_game.charted` (2023–2025);
  - 0 pass rushers on a dropback counts as uncharted, in both tables;
  - leakage checks 2 and 8 handle a table keyed by season.
