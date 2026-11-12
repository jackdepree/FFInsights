# 0030: Participation inference rebuilds each completed game play by play, outside the forecast harness

**Date:** 2026-11-11 · **Decided by:** the CEO agreed the brief ("Yes we can start the build as long as our goal is to map every play's participation", 2026-11-11). The calls below are Claude's technical calls, listed for veto at merge; the CEO: "no vetos" (2026-11-12). · **Project:** `participation-live`

**Decision:** `pcf.experts.participation_live` estimates, for every scrimmage play of every completed game, each possible player's chance of being on the field (both sides) and one best-guess lineup, from what's known by the morning after. It has its own walk-forward runner (`reconstruct.backtest`), not `pcf.validation.backtest`.

**The calls:**
1. **Its own runner, not the forecast harness.** The harness predicts games before kickoff from a view at the run before it. This expert rebuilds games after they're played, so its moment is after the game: a row's `as_of` is the first weekly run at least a day after kickoff, when the snap counts are in (Monday-night games: the Thursday run). The point-in-time rules are kept in two ways:
   - **Inputs and the answer key come from different views.** The inputs view (play-by-play, rosters, snap counts, head coaches) doesn't declare `player_play`, so the gateway refuses the answer key. The answer key is read from a retrospective view, for history, training and scoring only.
   - **Each game uses its own rows**, plus earlier seasons' answer keys. `check_point_in_time` rebuilds sample games from a view at each game's own `as_of` and compares the chances with the season run's (the gap must be 0).
2. **The snaps come from the play-by-play alone:** every pass, run, no-play, kneel and spike that isn't special teams, numbered in each team's game. The exploration chose plays whose true lineup had 11 a side; the build never does, so a live game gets the same grid. Scores count only play-sides whose true lineup has 11 (91% of them).
3. **Candidates, pins and targets.** The candidates are the players with snaps for the side in that game. Two kinds are pinned:
   - Every player named by the play-by-play on a play is pinned on it.
   - Every player with the side's most snaps is pinned on every snap.
   A player's target is his snaps scaled so the side's targets add to 11 a snap.
4. **The model, per position group, is a logistic regression with two snaps of memory**, trained on true sequences of completed seasons (teacher forcing). It climbs the ladder:
   - `share`: the snap share alone;
   - `league`: plus situation;
   - `history`: plus his own habits from earlier seasons and his team's from last season (H32, H33);
   - `sequence`: plus memory (the snap before and the one before that, same drive or not, no-huddle, his stay and return rates (H35), and the snap number in the drive (H34)).
   - Each rung is fitted on the 3 seasons before the test season.
5. **The balancing keeps the sequence and the totals.** Each player's on/off along his side's snaps is a chain with the model's transition chances, and named snaps are evidence. Offsets per snap and per player are added to the log-odds until every snap's chances add to 11 and every player's add to his target. This is the distribution closest to the model's that meets both totals. It's found as the minimum of the convex dual with L-BFGS-B, with offsets kept within ±20. A first version used Newton steps per total. It didn't settle when the chains were sticky: plays added to 4.5–8 instead of 5 on a synthetic game. The dual's gradient is exact.
6. **The best guess is one assignment over the whole game,** solved as a linear program:
   - the open players with the most likely chances;
   - 11 a play;
   - each player's total within a play of his target, with a costly slack where that's impossible;
   - **each play's count of each position group** (backs, tight ends, receivers, linemen, quarterbacks; on defense linemen, linebackers, backs) **fixed at what the group's chances on that play add to**, rounded to whole players.
   - The constraints form a network, so the answer is whole players. The exploration's per-play top picks missed the totals by 7.8 plays a player.
   - **The rounding is done over the whole game at once** (controlled rounding): each count is the floor or ceiling of its expected count, each play's counts add to its open spots, and each group's game total matches its players' snaps. It's a small transport problem, solved the same way.
   - **Why the mix:** without it, the chances were right but the lineups weren't football. 14% of snap-matched plays had no running back (truly 1%) and 17% no tight end (truly 2%), so the personnel (backs and tight ends) was right on only 35% of plays, and 11 personnel came out on 33% against a true 62% (participation-live#R4).
   - **Tried and dropped:**
     - Bounds of a step either side of the expected count: 44% personnel right; the program used the slack to stack two backs.
     - Rounding each play alone: a team's only tight end, 60% likely, rounded up on every snap and broke his total by 9 plays on a synthetic game.
7. **Two lineups are output, from the same chances:**
   - **`best`, snap-matched:** the program above. Every player's total matches his snaps, and the substitutions per snap match the truth's.
   - **`likeliest`:** the same program without the totals, so each play gets its own likeliest 11 within its position mix. More players right per play (about 4 points), but totals drift by about 7.5 plays a player and it substitutes half as often as the truth.
   - **The headline is `likeliest`** (the CEO's taste call, 2026-11-12: "higher layers should use the likeliest 11 players on each play"). `best` stays in the output for uses that need the snap counts kept.
8. **History is shrunk toward 0** with these prior counts:

   | History | Prior count |
   |---|---|
   | A player's situational habits | 100 snaps |
   | A team's | 300 snaps |
   | Stay and return rates | 50 snaps |

   A player's history uses every earlier season. A team's uses last season, and only when the head coach is the same (H33: same coach 0.74 season to season, new coach 0.23).
9. **The test seasons are 2019–2024;** 2016–2018 are for training and history only. The 2025 vault stays closed until validation.
10. **The output** is one row per candidate and snap, `quantity` = `on_field_chance`:
   - `mean` is the chance, and `q10`–`q90` equal it (a chance has no range);
   - `best` marks the snap-matched best guess and `likeliest` the likeliest lineup;
   - `certainty` is the play-side's expected share of the likeliest 11 right: the known spots plus the chances of the open players picked, over 11 (the CEO, 2026-11-12: "an estimate of certainty for each play"). It needs no independence between players (an expected count adds up whatever the correlations);
   - `side`, `team` and `n` (the team's snap number) come with each row;
   - `train_end` is the end of the season before.
11. **Two inputs added after the CEO's spot-check of the inputs** (2026-11-12, RESULTS "The CEO's spot-check: the inputs"):
   - **the competition in his group on the snap:** `gn`, his group's teammates named on the snap, and `gfull`, his group's every-snap players. The balancing knew 11 a play, but a player's own chance didn't know that a second back named on the snap pushes the first one off;
   - **his pair habits with the teammates named on the snap** (`pn`, H36 and H37): the sum, over his part-time teammates named on it, of how much more or less often he was on with each of them than his share says, from every earlier season (log-odds, shrunk by 50 snaps).
   Both are known by the morning after (the play-by-play and earlier seasons' answer key). The team's habits (H33) and the stay and return rates (H35) add nothing measurable on top of the rest (0.01–0.03%), but removing them is slightly worse in both seasons, so they stay. The offense's personnel as a defense input was tried and left out (0.00%). The choice used 2023–2024, also test seasons; 2019–2022 and the vault are the clean check. The CEO: "I don't veto anything" (2026-11-12).

**Alternatives:**
- **A full hidden Markov model over lineups** (the state is the whole 11). Exact, but there are thousands of possible lineups per side, and the snap totals couple every snap. The per-player chains with offsets keep the totals exactly and stay small.
- **Gibbs sampling of lineups.** It gives joint draws, which a causal model will want later, but it's slow and needs mixing checks. The chances and the best guess come first; draws can be added from the same chains.
- **The best guess as each snap's top picks only.** It breaks the snap totals (F7), so it is kept only as the second lineup (`likeliest`, call 7).
- **Running it through `pcf.validation.backtest`.** That would need a post-game moment kind in the shared harness, a large change to a module every model depends on (sign-off). It's worth doing once a second post-game expert exists.
