# Retro: what the record says, and what to try next

> The loop that learns from our own log (CLAUDE.md, "The retro"). After every second finished project Claude reads every hunch, idea and verdict, and writes here: how the last predictions scored, which kinds of bets hold, a prediction for every open idea and hunch, new ideas, and proposed changes to how we work.

- **A pattern is a hypothesis, not a finding.** It was fitted after the fact, on a few dozen verdicts that come in clusters (one project can supply most of a pattern). It earns trust only by predicting verdicts before they're known, which is what the predictions table is for.
- **Confidence means:** low, medium, high: roughly 60%, 75%, 90% sure the stated outcome happens. A retro scores them by counting how many in each band came true.
- **Where things go:** new ideas go in [IDEAS.md](IDEAS.md) as Claude's (I46 on); the CEO's edits can turn one into a hunch ([HUNCHES.md](HUNCHES.md)). Accepted workflow changes go in `CLAUDE.md`.
- **Next retro:** after the second project finished from 2026-11-15 on.

---

## Retro 1 (2026-11-15)

Read: all 50 rows of HUNCHES.md (H1 to H49), all 45 ideas (I1 to I45), and KNOWLEDGE.md. Not re-read: each project's RESULTS.md in full, so the sizes below are the logs' own.

### The record

| | Held | Failed | Unclear | Open |
|---|---|---|---|---|
| The CEO's hunches (50) | 21 | 15 | 11 | 3 |
| Ideas with a result (13 of 45, most of them Claude's) | 4 (I2, I19, I33, I36) | 7 (I3, I22, I24, I34, I35, I37, I40) | 2 (I13, I25) | 32 |

Of the tested hunches, 45% held. That is a good rate for bets against the usual way, and it hides a large spread between kinds of bet, which is the point of this page.

### Patterns

| # | Pattern | For it | Against it, or its limit |
|---|---|---|---|
| **P1** | **"This habit is real, and it belongs to X."** Claims that something repeats and has an owner (a coach, a player, a pair) hold about nine times in ten. This is the CEO's strongest kind of hunch | H10 (tendencies follow the coach), H23, H26, H28, H29, H33, H36 (tandems, r 0.83), H37, H38; I25 in part | H31: defenders carry a third of what skill players do. H27: QBs carry little to a new team |
| **P2** | **"A matters only against B."** Matchups, fit and conditional strength at the level of teams and games haven't held once | H9, H11, H12, H13, H14, H16, H49, H2b; I22, I26 so far | Real interactions exist on single plays (passing into 8-man boxes +0.12 EPA, schemes-v2#F21) and vanish at game level. About 4,000 games is too few (H9 needed 7,000), so this says "not measurable here", not "not true". Untested with player-level samples |
| **P3** | **Don't throw plays away.** Using every play, measured against an expectation, beats any filtered sample. The largest gains on the board | H22 (pace on every play: 0.85 against 0.66), H41 (every play counted: +3.9 to 7.5% over the garbage-time rule), I2 | None yet. Only tried on teams |
| **P4** | **Cleverer weighting, cleaning or method ties the simple version.** Whoever proposes it | H3, H4, H40, H42 (double machine learning), H43 (grains), H44, H45 (leverage weights); Claude's I34, I35, I37, I40 | H41's weights gained +0.3 to 0.9%, about the size of their own split luck. Methods mostly cost nothing either: they tie, they rarely hurt |
| **P5** | **The gains are where history is stale or blind.** Who is available, what a team is playing for, what changed since last season. The second-largest gains | H1 (absences), H2a (the pull between seasons, 0.21 points), H8 (seed locked, 0.43 points in the final week), the new-coach prior (+11.1% in weeks 1 to 4), I19, I13 | H2b: scaling the pull by roster turnover failed. I37: a mid-season QB change ties (the old QB's games still describe the offense) |
| **P6** | **Fatigue shows in who is on the field, not in how they play** | H34 held (linemen come off after two or three snaps); H24 and H25 failed (pace doesn't cause injuries or late collapses) | I29 and I30 are open leads the other way |
| **P7** | **Real is not the same as useful.** A trait can repeat strongly and add nothing once a simpler input is in the model | H33 (team substitution habit: nothing on top of the players' own habits), H35 (nothing on top of two snaps of memory), H15 (failed the vault), H28 ("a tell of the call more than a cause"), efficiency beside Elo (r 0.90) | Some redundant traits found a use elsewhere: `leverage_usage` as a feature, series success rate for its own future |
| **P8** | **A small gain in the exploration doesn't survive the build.** Gains under about 0.3% came back as ties or losses; gains of 2% or more held | Shrank: H45 (+0.14% became −0.23%), H42 (+0.2% to a tie), H44. Survived: H32 (1.9%), H41's full sample (4.6%), H36 (0.47% at the build) | The new-coach prior held at +0.3% in the backtest and then lost the 2025 vault. The models' own fitting noise is 0.1 to 0.2% (snap-leverage#R5) |

One more, from KNOWLEDGE rather than the verdicts: **nothing we've built adds to the closing line on sides and totals** (elo#F4, team-efficiency#R6, schemes-v2#F28). Where a consensus has shown a bias, it has been the fantasy consensus on specific kinds of player (questionable players, players at home: miss-lenses#F12, F13).

### What the patterns say to do

- Spend hunches where the record is strong: **who owns a measure (P1)** and **what the model can't see yet (P5)**. The CEO's open I20 ("whose trait is it?") is the highest-prior idea on the board.
- Treat any **team-level matchup** idea as a long shot until it's tried where samples are large (P2).
- Before any filter or reweighting, try **every play, counted equally (P3, P4)**.
- Ask of every new trait, in the exploration: **what does it add beyond the one obvious input (P7)?**
- Read a gain against the **noise ceiling and the fitting noise (P8)**, now the first step of every exploration.

### Predictions for everything open

Written 2026-11-15, before any of these is tested. Each idea's line is also in IDEAS.md ("Expected before the test").

| Expected to hold | Confidence | Expected to tie or fail | Confidence |
|---|---|---|---|
| I20 whose trait | high | I15 script-adjusted share | high |
| I21 stayers for coaches | high | I26 learned matchup types, live | high |
| I4 playing while questionable | high | I27 outside runs against man | high |
| I14 ranges widen with swing | high | I39 play weights without DML | high |
| I17 final-week share in the playoffs | high | I44 clutch as a trait | high |
| I47 the change lens | high | I7 multiplying conditions (in trees) | medium |
| I9 vacated snaps for movers | medium | I12 pre-trained tabular model | medium |
| I10 no depth-chart slot | medium | I16 script tendencies (repeat, but no gain) | medium |
| I5 rookies improve in season | medium | I23 receiver depth fit | medium |
| I8 ECR and home players (half size) | medium | I30 pass defense after a long half | medium |
| I28 a playoff flag | medium | I32 pass defense shrinkage | medium |
| I31 series success for drives | medium | I6 ECR and top questionable players (shrinks) | low |
| I41 new coach's defense (half size) | medium | I11 the bye (fades) | low |
| I42 season-shift ranges | medium | I29 long drives and injuries (shrinks) | low |
| I43 the passing-down role and contracts | medium | | |
| I46, I48, I49, I51, I52 (new) | medium | | |
| I50 backups rise with fatigue | medium | I50's second half: that it explains I30 | low |
| I53 target depth travels | high | I53: target share travels | medium that it doesn't |
| I1 ranges and expert disagreement | low | | |

The open hunches (the CEO's own confidence is theirs to add):

| Hunch | Claude expects | Confidence |
|---|---|---|
| H5 conditional strength | Home holds, as it always has. Strength against the opponent's QB, coverage or game state fails at team level (P2) | medium |
| H6 stabilization | It finds consistent conditions (P1). Few of them forecast beyond the overall rating (P7) | high, then medium |
| H18 schemes predict the players a team seeks | Holds, small: coach-owned traits (P1) should show in who a team signs, mostly through personnel groupings (a team heavy in two-tight-end sets signs tight ends) | low |

### New ideas

I46 to I53 in [IDEAS.md](IDEAS.md), each with a test, a confidence and an expected size:

| # | Idea | From |
|---|---|---|
| I46 | Incentive states beyond seed-locked: eliminated teams, and clinched ones, in the last three weeks | P5 |
| I47 | One "games since a change" lens on every expert's misses | P5 |
| I48 | Garbage-time production counts for players too | P3 |
| I49 | Swap pairs say who inherits an absent player's snaps | P1, P5 |
| I50 | Fatigue shows as who is on the field | P6 |
| I51 | A probable starting QB from practice reports, not a yes-or-no one | P5 |
| I52 | Real but redundant traits belong in the ranges | P7 |
| I53 | Which usage rates travel with a player (the CEO's I20, for fantasy usage) | P1 |

### Workflow changes

**Accepted by the CEO (2026-11-15), now in `CLAUDE.md`:**

| Change | The CEO's words | Where |
|---|---|---|
| Confidence and expected size on every hunch and idea, before the test | "adding confidence and expected effect size is smart to each hunch and idea" | "Every bet states its odds first"; new columns in HUNCHES.md and IDEAS.md; the brief template |
| Football claims first; Claude more exploratory with methods; the CEO stays involved in methods | "I will try to focus more on football claims rather than methods, but I will ask for you to be more exploratory with methods"; "I do like to be involved in the methods, though" | "Football claims first, methods together"; a Methods section in the brief template |
| The noise ceiling first in every exploration | "Putting noise ceiling first in exploration is very smart" | Lifecycle step 2; the brief template; definition of done |
| Scheduled backlog checks and retros | "we could schedule backlog checks or retro analysis like this so that we always improve our building capabilities" | "The retro": after every second finished project |
| A crude forecaster to score incremental gains; the vision is many models and several products | "The vision can really be multi-model. I have a vision for a dashboard, summarized betting advice, a website, and general forecasts and diagnostics"; "we can draft a crude and simple forecaster to measure incremental gains" | "One yardstick for incremental gains"; `crude-forecaster` in the registry (an idea: its kickoff and brief are still to come) |

**Proposed, not decided:**

1. **Two verdicts per hunch: "is it real?" and "does it pay?"** The CEO found this confusing (2026-11-15), so it is not adopted. The plain version: H33 said each coach has his own substitution habits. That is true (it repeats at 0.85 and follows the coach), so the hunch about football was right. Added to the model, it improved nothing, because the players' own habits already carried it. Today the row reads "held", and a reader can't tell a hunch that was right about football from one that also made a forecast better. Two columns would show both. Under P7 this happens often.
2. **A build bar.** The charter says an exploration is a go "unless there's literally zero signal". P8 says exploration gains under about 0.3% haven't survived a build. A possible rule: a gain smaller than the fitting noise makes the project an investigation (features and findings, no forecast), as the CEO ruled for `snap-leverage`. The noise ceiling step now reports the numbers; whether they set the bar is the CEO's call.
3. **The obvious-input check.** In every exploration, each new trait is tested beside the single most obvious input that might already carry it (P7), before a build is planned.
4. **Tag each hunch as a football claim or a method** in HUNCHES.md, so the next retro can score the two kinds apart without Claude classifying them afterwards.

### The case against this retro

- The patterns were found and counted by the same reader, on the same rows, in one pass: no held-out verdicts. P2 leans on one project (`schemes-v2` supplies 8 of its 10 rows), P6 on three hunches.
- "Held" mixes sizes from 0.06 points to 7.5%, and mixes explorations with builds. A pattern counted by verdicts can be wrong about where the value was.
- Sorting a hunch into a pattern is a judgment. H41 sits in P3 (its full-sample part) and in P4 (its weights) at once.
- The predictions lean on the patterns, so if a pattern is wrong, its predictions fail together. That is also what makes them a fair test.
