# Brief: Participation inference, second edition (`participation-late`)

**Status:** agreed 2026-11-12 after the exploration (GO, small), on the CEO's "take the lead on this and probably just go for it"; kickoff 2026-11-12. The CEO, closing `participation-live`: "Yes, I think it should have the mapping should have a second interval, 1 to 2 weeks after each game. So I don't know if how you really want to build that out, but that's definitely smart. We should definitely have some sort of reiteration, some sort of recalculation that goes back. Maybe we can add that into the certainty somehow, if that's easier or if that's simpler or more cost effective, or if you just want to build out a whole new system that does the same thing every 2 weeks out. That's good with me." · **Layer:** expert · **Cadence:** in_season (each completed game, again once FTN's charting for it is out, about 1–2 weeks later)

## The usual way
*Claude, 2026-11-12, before any research.*
- **Publish fast, then revise.** Data providers put out a quick first version and revise it when better sources arrive: the NFL's Wednesday stat corrections, charting companies' preliminary then quality-checked charts.
- **The revision is the same method with more evidence.** Nobody builds a second system; the same model runs again with the new inputs, and the change is reported.
- **Every edition is kept with its date** ("vintages"), so a backtest can use only what was published at the time, and users can see how much the later edition moved.

## Analogies
1. **GDP's advance, second and third estimates.** The government publishes GDP a month after a quarter, then revises it twice as more surveys come in. Economists keep every vintage, because a model tested on the final numbers would look better than it could have been in real time. Our `as_of` already does this: the morning-after map and the later one are two vintages of the same play.
2. **Weather reanalysis.** A forecaster's real-time picture of the atmosphere is later redone with observations from before *and after* each moment (smoothing instead of filtering). The morning-after map already smooths along the game. The second edition adds a new kind of observation, FTN's counts per play, to the same smoother.

## What it builds on
- **`participation-live` (done):** the morning-after map: each player's chance per play, the likeliest and snap-matched lineups, and each play's certainty. The second edition reuses it whole and adds evidence.
- **participation-live#R11:** each play's true personnel would be worth 6 points of open spots on offense and 4 on defense. FTN has no personnel, but it has partial clues.
- **FTN charting** (`play.ftn`, free through nflverse, 2022 on; known at kickoff + 14 days in history, our own fetch time live; DATA_SOURCES.md). Per play: `n_offense_backfield`, `n_defense_box`, `n_pass_rushers`, `n_blitzers`, motion, play action, screen, RPO, QB out of pocket, and more. 97% of plays are charted.
- **A first look** (2022–2024, against the true lineups; light, not a test):
  - **backfield count:** with 2 in the backfield, 35% of plays have two backs on the field; with 1, 5%. It also moves the tight ends (1.42 against 1.28);
  - **box count:** a 4-man box goes with 5.4 defensive backs (38% of plays with 6+), a 7-man box with 4.6 (3%); r 0.43 with the front's size;
  - **pass rushers:** almost unrelated to the number of defensive linemen on the field (r 0.07).

## Assumptions, limits and advantages (to test, not settled)
- **Thin history.** FTN starts in 2022, and 2025 is the vault, so there are three seasons to learn from (2024 tested on 2022–2023). That favours using FTN's counts as evidence in the balancing (a play's likely number of backs, defensive backs) over learning many new weights.
- **Partial clues.** No personnel, only counts that lean toward it. The gain is likely a fraction of R11's 4–6 points.
- **Certainty moves with it.** Each edition carries its own chances and certainty; a later edition should be more certain where FTN's clues bite. A downstream model reads whichever edition its moment allows (rule c), so the revision "goes back" without rewriting the first edition.
- **Advantage:** the same model, data and output schema; one more input and a second run per game.
- **A simpler alternative:** no new model, only a correction of the position mix (a play's count of backs and defensive backs) from FTN's counts, then the same lineups.

## CEO hunches
*The CEO, 2026-11-12, word for word:*

"I think this retro participation analysis expert is going to be basically the exact same with one caveat, is just instead of training exclusively on data like within a game and before a game, like the snap counts and whatever, now all we're going to do really is just add the snap counts for the next game, and then we just predict the past game. So it's really just almost the same exact stuff. I think this expert should be pretty easy to build and verify, because it's as long as we're not leaking too much, because we really shouldn't leak at all, because it's a retroactive, so we're like necessarily saying we're from the future. I don't know what else to add at this. I don't really have any hunches. I don't really have anything else to add. I think you can really take the lead on this and probably just go for it. But obviously, if you have more questions, let me know, because I always want to answer questions. Thank you."

| # | Hunch | How it will be tested |
|---|---|---|
| H39 | The games after a game help reconstruct it: "add the snap counts for the next game, and then we just predict the past game" | The next game's snap share (each player's, the same team) as an input to the same model, held out 2023–2024; the previous game's alongside, for comparison |

The CEO's other points: the late edition is "basically the exact same" expert, and it must not leak at all ("we're like necessarily saying we're from the future"). The CEO asked Claude to take the lead.

### Claude's assumptions and expectations (written before the tests)
- **H39: helps a little, less than FTN.** This game's own snap count already fixes how many snaps a player played; the next game's can only say *which* ones, through his role's direction (a back whose snaps jump next week was probably getting more of this game's late or high-leverage snaps). I expect under 0.5% log loss, most for backs and the defensive line. The previous game's snaps, known by the morning after, should help about as much, which would make it an input for the morning-after map too.
- **FTN's counts: helps more,** because they are clues about this very play: most for backs (the backfield count) and defensive backs (the box count), 1–3% of log loss on those groups, little elsewhere.
- **Not leaking:** the late edition's `as_of` is when the last input it uses is known: the next game's snap counts (the morning after that game) and FTN for this game (kickoff + 14 days in history). The morning-after edition stays as it is.
- **Thin FTN history:** 2022 on. The FTN tests train on FTN seasons only (2023 on 2022, 2024 on 2022–2023), against the same model trained on the same seasons without FTN.

## After the exploration (2026-11-12)
[EXPLORATION.md](EXPLORATION.md): H39 failed (the next game's snap counts add 0.00%); FTN's counts add 0.41% (offense) and 0.26% (defense) log loss in both held-out seasons. The build: the morning-after model plus FTN's counts, as a later vintage (decision 0031).

## Tests
- **Signal:** the late edition beats the morning-after map on the same plays (log loss on open spots, open spots right in the likeliest lineup), in both 2023 and 2024.
- **No noise:** it doesn't do worse for any position group.
- **Calibration:** within 3 points, slope 0.9–1.1; its certainty honest within 3 points.
- **Point in time:** sample games rebuilt from a view at their late `as_of` match the season run (gap 0), and a view at their morning after holds none of their FTN rows.

## The CEO's review of the results (2026-11-12, word for word)
- The spot-check: "The leakage check" (done: RESULTS.md, "The CEO's spot-check"; no leak found).
- Vetoes and merge: "Merge, no vetoes".

Against the tests above: signal, calibration and point in time pass. "No noise" holds for 7 of 8 position groups: the offensive line's log loss is 0.1% worse (its open spots right go up). That was in the case against when the CEO approved (RESULTS.md, point 3).
