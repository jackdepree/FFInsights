# 0024: Anti-traits are judged on the next game's gain; defenses' choices are a post-season part of the team-game table

**Date:** 2026-11-09 · **Decided by:** the CEO chose the options and the target ("D1 should be pass and shotgun plus defense first. D2 should be the team's gain from that option in its next game"); Claude made the technical calls below, listed for veto at merge · **Project:** `schemes-v2`

**Decision:**
- **Offense gains in `team_game.tendencies`:** `pass_gain` and `shotgun_gain` per game (EPA per play with the option less without, neutral situations) with their effective plays, and `def_shotgun_rate` (what a defense faced).
- **New post-season part `team_game.charted`** (`pcf.data.tables.charted`): per defense and game, man coverage, two-high shells and blitzes (5+ rushers) on neutral dropbacks: rate, use over expected, gain (EPA prevented) and effective plays. Known when participation is (after the Super Bowl), so an in-season view sees only finished seasons (rule m).
- **The anti-trait variants** (`pcf.experts.schemes_v2.anti_model`): per option, the next game's gain from the league's gain (rung 0), the team's own past gain (rung 0), the league's plus a fitted weight on the team's use (rung 1, the anti-trait), and the same plus past gains (rung 1).

**The calls:**
1. **Gains are plain EPA differences, not residuals from a fitted EPA model.** EPA already prices down, distance and field position, the plays are neutral, and the expert subtracts the league's gain. The exploration's residual model (F17) would need fitting inside the table, which holds only counts.
2. **The shotgun's gain is measured within passes and within runs,** then averaged with the effective plays as weights. Otherwise most of it would be passing's gain again (shotgun plays are mostly passes).
3. **A defense's usual choice is the league's rate that season for the same down, distance bucket (1–3, 4–6, 7–10, 11+), shotgun or not, and heavy personnel or not.** Using the whole season is fine because the part isn't known before the season ends. These are cell means, not a fitted model.
4. **The offense's "against that opponent" part:** each opponent's level allowed (its defense's games this season and the last, known by the moment), less the league's, averaged over the team's games this season, with 4 games of zero. Pass rate keeps `xpass` as "standard strategy". The shotgun's use is the raw rate: neutral situations already even out the down-and-distance mix, and there is no expected-shotgun column. *(Changed from what I told the CEO before building: I had said the league's rate by down and distance from earlier seasons. Doing that would need the past seasons inside a per-season table build.)*
5. **A defense's features are its last finished season only,** with the league's gain from the last two finished seasons. A change of head coach or coordinator isn't taken into account yet.
6. **Targets aren't weighted by their plays:** the harness has no outcome weights. The effective plays stay in the tables for any later model.
7. **First training seasons:** blitzes 2017 and coverage 2019 (a feature needs a charted finished season, and an outcome is known only after its season). So the defensive backtests start in 2018 and 2020.
8. **The anti-trait's sign test** (the brief's "keeps F18's sign on held-out seasons") is a script (`projects/schemes-v2/explore/anti_sign.py`): it fits nothing, so every season is held out. The harness judges the variants as forecasts.

**Alternatives:**
- *A fitted play-level usual-choice model as a table part:* it's closer to the exploration, but it's a model inside the data layer, refitted per season, and F17 found the opponent part added almost nothing.
- *Judge the anti-trait on next-game EPA or the margin against the spread:* the CEO chose the gain, and F17(b) found the direct effect on EPA tiny.
