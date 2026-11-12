# Brief: Participation inference, second edition (`participation-late`)

**Status:** kickoff 2026-11-12. The CEO, closing `participation-live`: "Yes, I think it should have the mapping should have a second interval, 1 to 2 weeks after each game. So I don't know if how you really want to build that out, but that's definitely smart. We should definitely have some sort of reiteration, some sort of recalculation that goes back. Maybe we can add that into the certainty somehow, if that's easier or if that's simpler or more cost effective, or if you just want to build out a whole new system that does the same thing every 2 weeks out. That's good with me." · **Layer:** expert · **Cadence:** in_season (each completed game, again once FTN's charting for it is out, about 1–2 weeks later)

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
*To come: the CEO's hunches, word for word.*
