# 0029: Player pace is two experts, an in-season one at the team-game grain and a retrospective one at the player-season grain

**Date:** 2026-11-11 · **Decided by:** the CEO chose both cadences ("Both, the pace expert for players should give downstream models within-season features and between-season features to learn from", 2026-11-11) and agreed the brief ("Build both as drafted, it looks great so far, thank you", 2026-11-11). The calls below are Claude's technical calls, listed for veto at merge. · **Projects:** `player-pace`, `player-pace-retro`

**Update (2026-11-11):** the CEO kept the in-season expert's results and findings but discarded the model ("keep the results and findings of the in-season expert but discard the model"). `pcf.experts.player_pace` and its tests are removed; `player-pace` is a dead end in the registry. Calls 2–5 below are kept as the record of what was tried. The tables, the harness changes and `player-pace-retro` stay.

**Decision:**
- **Two new table parts** (`pcf.data.tables.player_pace`):
  - `player_game.on_field_pace`: per player and game, his team's pass rate over expected and pace over expected on the snaps he played and on the snaps he sat, the gaps between them (his plus-minus), each gap's weight (on × off ÷ team snaps), and the pass-rate gap within each personnel grouping. A defender's rates are the opposing offense's.
  - `player_season.on_field_pace`: the season's weighted plus-minus per player, his side, position group, main team, games, plays and last game's kickoff. A new table, `player_season`.
  - Both come from `player_play.on_field` (participation), so both are post-season only, known the day after the Super Bowl.
- **`player-pace-retro`** (retrospective, player-season grain): each player's next-season plus-minus, 9 variants (3 measures × position-group average, last season, shrunk history).
- **`player-pace`** (in season, team-game grain): each team's next-game pass rate over expected, pace over expected and volume, team pace's features plus the expected starting QB and who's ruled out. 8 variants.

**The calls:**
1. **On-field rates, never rates on touches.** A receiver's targets say how often he was thrown to, not how often his team passed with him on the field. The plus-minus is on-field minus off-field, the way hockey and basketball measure it, weighted by on × off ÷ team snaps (the harmonic weight: a player who never sat out has no plus-minus and weight 0).
2. **The in-season expert predicts teams, not players.** The in-season data on who's on the field (weekly snap counts) has no play-by-play link, so a player's in-season plus-minus can't be measured. What players add in season is who's expected to play: the starting QB and the skill players ruled out. So the rows are team pace's (game, team), and its yardsticks are team pace's own models.
3. **The expected starting QB:** the team's starter in its last game known by the Saturday run (`team_game.pregame.qb_id` is known only at kickoff), unless this week's report lists him Out or Doubtful or he isn't on this game's roster; then the rostered QB not ruled out with the most offensive snaps this season, then last season. Right on 92% of 2016–2024's tested games, 72% of those where it expects a change.
4. **The QB's history is shrunk toward the league:** his starts' team PROE and pace over expected in the last 3 seasons, less each season's league level, shrunk by 600 plays (PROE) and 500 timed snaps (pace) worth of the league's 0. `qb_<m>_other` = gap × (1 − his share of the team's starts) is the part the team's own habits don't already carry.
5. **`lineup_out` uses earlier seasons' plus-minus, not this season's:** participation for the current season isn't available in season. Each ruled-out back, receiver and tight end counts his share of the team's snaps in its last game times his plus-minus over the 4 earlier finished seasons (`PM_SEASONS`; decayed 0.7 a season, shrunk by 50 weight), summed and negated. The 4-season window is applied in the bulk history too: the first validation read every earlier season in bulk and 4 per moment, and leakage checks 3 and 4 caught the mismatch from 2021 on (the first season with a fifth earlier one).
6. **The retrospective features:** per measure, last season's plus-minus and weight, and the last 4 seasons' weighted sums decayed 0.7 a season; the outcome is a season with at least 20 weight. `<m>_shrunk` is the group average plus a per-group slope on the shrunk history, its shrink chosen from a grid on training rows only.
7. **The harness learned a season-keyed grain:** a row without `game_id` joins its season's one retrospective step (`backtest._with_steps`), and the calibration groups take the row's own season (`validate`). Leakage check 2 compares a season row's `known_at` with its `last_kickoff`, so `player_season` carries one.
8. **`depends_on` is `[grain-tables, validation-harness]` for both.** The contract requires a model project in `depends_on` to be read as a model input; pace's and participation's code is reused, not their outputs.

**Alternatives:**
- **Rates on touches (target share, rush share):** they measure the player's role, not his team's lean with him on the field. Kept for `roles` later.
- **A player-game grain in season:** no play-level link in season, so the target would be his team's game rates, the same for every teammate.
- **The actual starter (pregame `qb_id`) as a feature:** known only at kickoff, after the Saturday run.
- **This season's plus-minus in season from snap counts:** snap counts say how many snaps, not which, so there's nothing to split on and off.
