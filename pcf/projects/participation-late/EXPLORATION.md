# Exploration: Participation inference, second edition (`participation-late`)

**Date:** 2026-11-12 · **Verdict:** GO, small · **Script:** [explore/late_inputs.py](explore/late_inputs.py) → [late_inputs.txt](explore/late_inputs.txt) · **Brief:** [BRIEF.md](BRIEF.md)

**The question.** What can a map made 1–2 weeks after a game know that the morning-after map didn't? Two candidates, each added to the morning-after model (the sequence rung, `participation-live`) and scored on held-out 2023 and 2024 (log loss on open spots; open spots right in the likeliest lineup):
- **H39 (the CEO):** the next game's snap counts ("add the snap counts for the next game, and then we just predict the past game"), with the previous game's alongside;
- **FTN's charting per play:** the backfield count, the box count, pass rushers, blitzers, motion, play action, screens.

## Findings
Cite as `participation-late#F1`.

**F1. The next game's snap counts add nothing (H39 failed).**
- Each player's snap share in his team's next game, as a change from this game's: +0.00% on offense and +0.01% on defense (worse by a hair), in both seasons.
- The previous game's, alongside: +0.02% / +0.01%. So it isn't an input for the morning-after map either.
- **Why:** this game's own snap count already fixes how many snaps he played, and the model already knows his habits by situation from earlier seasons. Next week's share only says where his role is heading, which doesn't say *which* of this game's snaps he played.

**F2. FTN's counts add a little, in both seasons.**

| Trained on the FTN seasons before (2023 on 2022, 2024 on 2022–2023) | Offense | Defense |
|---|---|---|
| Log loss, change against the same training without FTN | −0.41% (−0.46%, −0.35% by season) | −0.26% (−0.28%, −0.26%) |
| Open spots right, likeliest lineup | +0.15 points | +0.12 points |
| Most for | backs (0.356 → 0.353), tight ends, receivers, quarterbacks | defensive backs (0.369 → 0.367) |

- The size fits the first look (BRIEF): the backfield and box counts lean toward personnel without fixing it (two in the backfield means two backs on only 35% of plays).
- It's a fraction of what knowing each play's personnel would be worth (4–6 points, participation-live#R11).

**F3. Training on the FTN seasons alone costs 0.15% on offense** against the morning-after map's three seasons (0.4084 against 0.4078), so the net gain over the morning-after map is about 0.27% / 0.23%. Training on three seasons with FTN marked missing before 2022 would keep both; the build tests it.

## Hunch verdicts
| # | Hunch | Verdict | Evidence |
|---|---|---|---|
| H39 | The next game's snap counts help rebuild the past game | **failed** | +0.00% / +0.01% log loss in both held-out seasons (F1). The previous game's add nothing either |

Claude expected H39 to help a little (under 0.5%): it didn't help at all. Claude expected FTN to help more, 1–3% on backs and defensive backs: it helped less (about 0.6–0.8% for those groups).

## Go / no-go
**GO, small.** FTN's counts are real signal in both seasons, and the second edition costs little: the same model with one more input family, run again when FTN's charting is out. Its worth is honest but small: about 0.3–0.4% better chances and 0.1–0.15 points more players right. The bigger prize (per-play personnel, R11) isn't in any free source.

## For the build
- The same model and outputs as `participation-live`, plus FTN's counts as inputs (`model.fit` with extra columns); the next game's snap counts stay out (F1).
- Train on three seasons, FTN marked missing before 2022 (F3); compare with FTN seasons only.
- **Point in time:** a game's late edition has `as_of` = the first weekly run at least 14 days after kickoff (FTN's known-at in history). Sample games rebuilt from a view at that moment must match the season run, and a view at the morning after must refuse FTN.
- Held out 2023 and 2024 only (FTN starts in 2022; the 2025 vault stays closed).
- Scored against the morning-after map on the same plays: does the late edition move the chances, the lineups and the certainty, and is it better?
