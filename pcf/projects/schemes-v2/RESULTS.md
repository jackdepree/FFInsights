# Schemes v2: results (draft, build in progress)

**Status:** building, 2026-11-09. Done: live traits (R1–R4) and anti-traits (R5–R9). Not done: retrospective traits, the vault, the case against, the interface card. This page is filled in as the build goes; the template's remaining sections come at the end.

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

**R6. The offensive anti-traits keep F18's sign on held-out seasons. The defensive ones don't.**

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

## Against the brief's draft tests
| Test | Result so far |
|---|---|
| Each trait repeats | Yes (CONSISTENCY.md, exploration F2) |
| Known before kickoff, it predicts the team's own next-game tendencies better than the league average and a rolling mean | **Yes, all four** (R1) |
| The shuffled version shows nothing | **Yes** (R2) |
| The anti-trait term keeps F18's sign on held-out seasons | **Yes on offense** (pass, shotgun: R6); **no on defense** (man, two-high, blitz) |
| The shuffled-team version of each shows nothing | Offense: the real slopes beat 196 and 198 of 200 shuffles (R6). As forecasts, only the pass blend passes the harness's signal test (R5) |

## Left to do
1. ~~Anti-traits~~ (done: R5–R9). Possible follow-ups: defensive avoidance from this season's live columns (pressure rate faced), and a defense's coordinator once that table exists.
2. **Retrospective traits** from participation (personnel, coverage, blitz, box), feeding in-season models from finished seasons only (rule m).
3. **Rung 2,** only if it beats the blend: weights that change with games played; the opponent's average bend (F10).
4. **A known-at rule for head coaches** (announced months before kickoff), so a new coach's history helps in week 1.
5. The vault, the case against, the spot-check, the interface card, KNOWLEDGE and CONSISTENCY rows.

## Technical calls so far (for veto at merge)
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
