# Schemes v2: results (draft, build in progress)

**Status:** building, 2026-11-09. First slice done: live traits. Not done: anti-traits, retrospective traits, the vault, the case against, the interface card. This page is filled in as the build goes; the template's remaining sections come at the end.

## What's built so far
- **`team_game.tendencies`** ([decision 0023](../../docs/decisions/0023-team-game-tendencies.md)): each team's tendencies per game from play-by-play, in neutral situations, 1999 on, known the day after the game. Any project can read it.
- **Trait forecasts** (`pcf.experts.schemes_v2`): each team's tendency in its next game, predicted on Saturday (Thursday games on Thursday), for four traits. Each has three simple averages (rung 0) and a fitted blend (rung 1).

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

## Against the brief's draft tests
| Test | Result so far |
|---|---|
| Each trait repeats | Yes (CONSISTENCY.md, exploration F2) |
| Known before kickoff, it predicts the team's own next-game tendencies better than the league average and a rolling mean | **Yes, all four** (R1) |
| The shuffled version shows nothing | **Yes** (R2) |
| The anti-trait term keeps F18's sign on held-out seasons | **Not built yet** |

## Left to do
1. **Anti-traits:** the play-level usual-choice model (the CEO's "clearly favorable") as a table part, then the avoidance terms, tested as in F18 but walk-forward.
2. **Retrospective traits** from participation (personnel, coverage, blitz, box), feeding in-season models from finished seasons only (rule m).
3. **Rung 2,** only if it beats the blend: weights that change with games played; the opponent's average bend (F10).
4. **A known-at rule for head coaches** (announced months before kickoff), so a new coach's history helps in week 1.
5. The vault, the case against, the spot-check, the interface card, KNOWLEDGE and CONSISTENCY rows.

## Technical calls so far (for veto at merge)
Decision 0023's eight calls: neutral situations only; raw rates; live columns only; the coach from the latest known game; 4 games' weight on the league; least-squares blend; `elo` out of `depends_on` for now; Saturday run.
