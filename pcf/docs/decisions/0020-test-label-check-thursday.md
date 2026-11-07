# 0020: The test-label check leaves results known before a step's last run alone

**Date:** 2026-11-07 · **Decided by:** Claude (a technical fix to a shared check, listed for the CEO's veto at merge) · **Found by:** `elo` (the long horizon)

**Decision:** Leakage check 8 (test labels) scrambles the results of the games from a test step on, then refits and predicts that step; the predictions must not change. It now leaves alone any result already known by the step's **last** prediction moment. In practice that's Thursday's game, known Friday morning, before the Saturday run of the same step.

**Why:** a step holds every game of a week, each at its own moment (Thursday's at the Thursday run, the rest at Saturday). The check assumed no result in the step is known before any of its moments. That's wrong for Thursday's game. Elo's long horizon showed it: Eagles at Giants (2018 week 6) moved both teams' ratings, so the Saturday forecast for every team with the Eagles or Giants in its next 3 games changed when the check scrambled that score. The model was right to use it: the score was public a day before the run. The margin forecasts never tripped this, because a game's own two teams don't play again that week.

**What it costs:** Thursday's row is no longer checked against its own scrambled result. A model fit on the whole dataset is still caught by every other game of the step and the steps after, and checks 3 and 4 (future perturbation and deletion, 25 cutoffs) still test every row against data known after it. The planted leak in `tests/validation/planted.py` is still caught.

**Alternatives:**
- Scramble per moment (Thursday's rows against Thursday-on results, Saturday's against Saturday-on): exact, but it rebuilds each step twice; worth it only if a model's Thursday rows ever need it.
- Leave the check as it was and give Elo's long horizon an exception (rejected): an exception in one model hides the same false alarm from the next one.

**Reruns:** none needed for models that passed before: the check now scrambles less, not more. Elo's long-horizon variants are validated with it.
