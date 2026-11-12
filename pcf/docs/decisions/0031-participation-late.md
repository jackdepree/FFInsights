# 0031: participation-late, the second edition of the participation map

**Date:** 2026-11-12 · **Project:** `participation-late` · **Status:** Claude's technical calls, listed for veto at merge

The CEO asked for "a second interval, 1 to 2 weeks after each game … some sort of recalculation that goes back", and left the build to Claude ("take the lead on this and probably just go for it").

1. **A later vintage, not a rewrite.** The late edition is its own output (`model` = `participation-late`) with a later `as_of`; the morning-after map (`participation-live`) is never changed. A higher layer reads whichever edition its own moment allows, so a backtest can't use the late edition before it existed (rule c). The CEO's "add it into the certainty" is met this way: each edition carries its own `certainty`, and the late one's reflects the extra evidence.
2. **The same model plus one input family.** participation-live's sequence rung, with FTN's counts per play as extra base columns (`model.fit(..., extra=...)`): the backfield count, the box count, pass rushers, blitzers, motion, play action, screen, and a missing flag (`pcf.experts.participation_late.ftn`). Everything else (the grid, history, the chain, the balancing, the lineups, the certainty) is participation-live's code.
3. **The next game's snap counts stay out.** H39 failed: they add 0.00% (participation-late#F1).
4. **Training on three seasons, FTN marked missing before 2022** (participation-late#F3): the other weights keep three seasons of data, and FTN's weights come from the FTN seasons. The backtest compares this with training on FTN's seasons only.
5. **Point in time:** a game's late `as_of` is the first weekly run at least 14 days after kickoff, FTN's known-at in history (DATA_SOURCES.md). Live, FTN's known-at is our own fetch time, so a game whose charting is late waits for the next run. The check rebuilds sample games from an inputs view at that moment (the gap must be 0), and checks that a view at the game's morning after holds none of its FTN rows.
6. **Test seasons 2023–2024.** FTN starts in 2022, so 2022 can't be tested with FTN weights learned before it. The 2025 vault stays closed.

**Alternatives:**
- **Folding FTN into the morning-after map** when it arrives (one output, rewritten). Simpler to read, but a backtest would then see FTN two weeks early. Two vintages keep each moment honest.
- **Fixing each play's position mix from FTN's counts** instead of new inputs. FTN's counts only lean toward personnel (two in the backfield means two backs on 35% of plays), so a hard count would be wrong often; as inputs they move the chances by as much as they're worth.
