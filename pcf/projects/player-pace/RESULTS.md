# Results: Player pace and play-calling (`player-pace`, `player-pace-retro`)

**Date:** 2026-11-11 · **Status:** `player-pace-retro` validating (the CEO's spot-check: R1, below); `player-pace` (in season) a dead end, its model discarded and its findings kept (the CEO, 2026-11-11) · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiments:** `player-pace`, `player-pace-retro` · **Technical calls:** [decision 0029](../../docs/decisions/0029-player-pace.md)

## In short
Two experts, as the CEO asked: one for between seasons and one for within a season.
- **Between seasons (`player-pace-retro`), the clear win.** A back's, receiver's or tight end's pass-rate plus-minus (his team's pass rate over expected with him on the field, minus without) forecasts his next season's 15% better than his position's average (range score, R1). Most of it carries: 0.89 of a tight end's shrunk history, 0.77 of a back's, 0.70 of a receiver's. Defenders barely carry one (0.8% better), QBs none (they never sit), and pace barely (0.2%).
- **Within a season (`player-pace`), a small win for pass rate only.** Adding the expected starting QB to the team's forecast of its pass rate over expected beats the team-only model and team pace's best, by 0.3% overall and 4% in games where PCF expects a different starter (R2). It doesn't help the volume forecasts (plays, dropbacks, runs), **so the brief's main test, "helps team pace's volume in the weeks the QB changes", failed** (R3). Who's ruled out adds nothing (R4).
- **The expected starter is right 92% of the time,** but only 32% of real starter changes are visible by the Saturday run (R5). Most changes are surprises, which caps what any QB feature can do before kickoff.

**Scorecards:** `data/outputs/<id>/<variant>/<run_id>/scorecard.html` (MLflow experiments `player-pace`, `player-pace-retro`).
**Vault:** closed for both; 2025 is untouched. Confirmation is the walk-forward (2018–2024 for retro, 2016–2024 in season) plus 2026 live.
**Versions tried:** retro 1 per variant; in season 2 per variant (the first failed leakage checks 3 and 4 and was fixed), plus one quick check of `proe_lineup`.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal, or beats baselines | **Retro:** all 9 variants beat 100 of 100 shuffled refits; each `<m>_shrunk` beats both yardsticks with the whole 90% interval below zero. **In season:** all 8 beat 100 of 100 shuffled refits. `proe_qb` beats both yardsticks; `pace_oe_qb` beats the team-only one and ties team pace's best; `proe_lineup`, `plays_qb` and `dropbacks_qb` tie; `runs_qb` is worse (R2–R4) |
| Calibration and range coverage | **Retro:** 80% ranges hold 79.5–80.2%, every group and season inside the bar. **In season:** 79.4–80.9% for all 8, 49–52% above the median |
| Leakage | Every blocking check passes for every final run of both: identical at 25 cutoffs when future data is changed or deleted. The first in-season run failed checks 3 and 4 (a bulk-versus-moment mismatch, fixed; see Pitfalls) |
| Football sanity | Backups lower PROE; running QBs carry it; a player's own effect is smaller than the coach's (R6). The retro lists' ends are the right players (blocking tight ends and fullbacks low, receiving backs high). The CEO's review is pending |
| CEO spot-check | 2026-11-11: R1, the 15% between-seasons result. It holds: every season, every skill group, movers too, and 12.7% beyond playing time (see below) |

## What's built
- **`player_game.on_field_pace`** (2016 on, post-season): per player and game, his team's PROE and pace over expected on the snaps he played and sat, his plus-minus, its weight (on × off ÷ team snaps), and his pass-rate plus-minus within each personnel grouping. A defender's rates are the opposing offense's.
- **`player_season.on_field_pace`** (new table `player_season`): his season's weighted plus-minus, side, position group, main team, games, plays and last game's kickoff.
- **`player-pace-retro`** (`pcf.experts.player_pace_retro`), 9 variants: for PROE, PROE within personnel and pace, his group's average, his last season, and his decayed history shrunk toward his group with a slope per group (`<m>_shrunk`, the finals).
- **`player-pace`** (was `pcf.experts.player_pace`; **removed 2026-11-11**, the CEO discarded the model and kept these results), 8 variants at the team-game grain: team pace's habit features plus the expected starting QB's own history, a change of starter, a rookie (`<h>_qb`, the finals for PROE and pace), plus who's ruled out (`proe_lineup`), and team pace's full volume models plus the QB columns (`<v>_qb`).
- **The harness** learned a season-keyed grain (one retrospective step per season).

## Findings
| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 | A skill player's pass-rate plus-minus forecasts his next season's 15% better than his position's average; 0.89 of a tight end's shrunk history carries, 0.77 of a back's, 0.70 of a receiver's | `proe_shrunk` vs `proe_group`, RB/WR/TE: −0.0031 [−0.0034, −0.0029], 2,594 player-seasons | strong | RB, WR, TE; 2018–2024 |
| R2 | The expected starting QB's history improves the team's next-game PROE forecast, a little | `proe_qb` vs team pace's `proe_shrunk`: −0.3% overall [interval below 0]; −4.0% in the 267 games with an expected change; −1.7% in the 600 with a real change | strong (small) | team-game, 2016–2024 |
| R3 | The QB columns don't improve volume: plays and dropbacks tie, runs get slightly worse | `runs_qb` vs `runs_full`: +0.1% [+0.00021, +0.00328]; +0.7% in expected-change games | strong | team-game |
| R4 | Who's ruled out adds nothing to PROE, though its sign is right | `proe_lineup` vs `proe_qb`: +0.1%, interval across 0; coefficient +0.18 (missing pass-tells lower PROE) | strong | team-game |
| R5 | The expected starter is right 92% of the time, 72% when PCF expects a change, but only 32% of real changes are visible by the Saturday run | 4,952 tested team-games | strong | 2016–2024 |
| R6 | Backups pass less: an expected change lowers PROE 1.4 points beyond the team's own history; teams average −1.5% PROE in those games against +1.2% | `proe_qb` fit through 2024 | strong | team-game |
| R7 | Pace over expected is barely a player's: the shrunk retro history beats the group average by 0.2%, and the QB columns tie team pace's best on pace | `pace_shrunk` vs `pace_group`; `pace_oe_qb` vs `pace_oe_shrunk` | strong | all |
| R8 | Defenders carry a pass-rate plus-minus a tenth as useful as skill players' (0.8% better than their group) | `proe_shrunk` vs `proe_group`, defense: −0.8% | strong | DL, LB, DB |

## The ladder
| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | Retro: position-group average; last season | Last season is 31% worse than the group average: one season is too noisy alone | Shrink history toward the group |
| 1 | Retro: decayed history shrunk toward the group, slope per group | Beats both, all three measures | The slope differs by group (TE 0.89, LB 0.18): keep it per group |
| 0 | In season: the team's own history (`<h>_team`); team pace's `<h>_shrunk` | — | |
| 1 | In season: plus the expected QB (`<h>_qb`) | Beats both for PROE; beats team-only for pace, ties team pace's best | The gain lives in change games |
| 1 | In season: plus who's out (`proe_lineup`) | Ties | Stop: the ladder ends here for lineup |
| 1 | Volume: team pace's `<v>_full` plus the QB | Ties or worse | Stop: volume stays team pace's |

## Where it misses
The miss lenses run on player-game amount models only; neither expert is one. By group, the retro's ranges are a little wide for backs (84% inside, the bar's edge) and right for the rest. In season, games with a real starter change carry the largest misses (the range score is about 9% higher in them), because most real changes aren't visible by Saturday (R5).

## The case against (2026-11-11, written before the merge)
- **The in-season gains are tiny.** 0.3% overall is real by the interval, but it's the size of noise in most uses. If PROE forecasts feed volume, and volume doesn't improve (R3), the in-season expert may never matter downstream.
- **The QB's history may be the team's in disguise.** Per standard deviation, `qb_proe_gap` outweighs the coach column (0.0077 against 0.0043). Most of a starter's starts are with this team and coach, so his gap is another read of the same habit. The part that's really his (`qb_proe_other`, his starts elsewhere) is 0.0004, tiny. So R2's gain is mostly better averaging of team history, and the clean QB effect is small, as the exploration said (F6: movers carry PROE 0.10).
- **The retro win is partly role, not the player.** F4 showed backs' plus-minus is mostly their package. A receiver who plays only in 11 personnel carries the 11-personnel pass rate. That's still a real, repeatable thing to forecast, but "the player makes the team pass more" overstates it. `proe_pers_shrunk` (within personnel) still beats the group by 10.7% for skill players, so most survives.
- **Seven seasons.** Participation starts in 2016, so the retro walk is 2018–2024: seven held-out seasons, resampled by season. The intervals are tight because there are many players, but a regime change (a league-wide shift in personnel use) would hit every player at once.
- **The expected starter rule can't see surprises.** 68% of real changes aren't visible by Saturday: the last starter isn't ruled out and is still on the roster. Why (benchings, late scratches, injuries during the game) isn't broken down here. A Sunday-morning run would see more; PCF doesn't run then.

## The CEO's spot-check (2026-11-11): R1, the 15% between-seasons result
The claim: for backs, receivers and tight ends, `proe_shrunk` forecasts next season's pass-rate plus-minus 15% better than `proe_group` (the position's average). Script and output: [explore/spot_r1.py](explore/spot_r1.py), [spot_r1.txt](explore/spot_r1.txt).

**The rows.** 2,594 skill player-seasons, 2018–2024, each measured on at least 20 weight (on × off ÷ team snaps). In plain units, the range score falls from 2.03 to 1.72 points of PROE: −15.4%. The features use only earlier finished seasons (leakage checks 3 and 4, and a test).

**Where the 15% comes from.**

| Cut | Rows | Better than the group average by |
|---|---|---|
| Tight ends / backs / receivers | 687 / 756 / 1,151 | 22.3% / 14.5% / 10.9% |
| Each season, 2018 to 2024 | 350–396 each | 13.6%, 18.1%, 14.8%, 14.8%, 12.2%, 16.9%, 17.5% |
| Outcome season lightly / moderately / heavily measured (weight 20–50 / 50–150 / 150+) | 308 / 1,079 / 1,207 | 5.9% / 15.1% / 19.2% |
| History brought in (decayed weight under 50 / 50–200 / 200+) | 197 / 716 / 1,681 | 4.2% / 11.6% / 18.7% |
| Stayed with his team / moved to a new one | 1,913 / 681 | 16.8% / 11.6% |

Every interval is below zero (by group and the other cuts, resampled by season; a single season is its own block, so it has no interval, but all seven point the same way). The gain grows with the evidence on both sides: more history in, and an outcome season measured well enough to see it. That's what a real trait looks like; a fluke would not sort itself that way.

**The forecast's lean comes true at full size.** Split by how far `proe_shrunk` leans from the group's average, in fifths: leans of −5.7, −1.8, +0.1, +2.0 and +6.2 points are followed by actual gaps of −5.9, −2.5, −0.4, +1.8 and +6.5. The lean and the actual gap correlate at 0.53. So the shrinkage is about right: it doesn't overreach.

**The alternative: is it only playing time?** The case against said part of it could be role. A yardstick of group × last season's plays per game (under 20, 20–40, 40+), fit walk-forward on earlier seasons, beats the group average by only 3.1%. `proe_shrunk` beats that role yardstick by 12.7% (tight ends 19.1%, backs 14.3%, receivers 6.9%; all intervals below zero). So playing time explains little of it. The personnel package explains some, more for backs: within personnel (`proe_pers_shrunk`) the gain is 10.7% (F4).

**Named rows, 2024** (points of PROE; group average −2.6 for tight ends, +0.2 for receivers, −2.1 for backs):
- Highest forecasts: Lucas Krull (TE) +12.1, actual +12.3; Chris Olave (WR) +11.5, actual +15.0; Kyle Pitts (TE) +10.7, actual +14.6. Two that faded: Tyreek Hill +8.4, actual +2.0; DeAndre Hopkins +8.8 after a trade to KC, actual +4.6.
- Lowest forecasts: Charlie Kolar (TE) −13.4, actual −13.0; Patrick Ricard (fullback, listed RB) −12.0, actual −8.0; Chris Manhertz (TE) −11.1, actual −10.8. A miss: Chris Rodriguez Jr. (RB), one season of history at −26.7, forecast −12.9, actual +2.4.

The ends are the right players: pass-catching tight ends and deep threats at the top, blocking tight ends and a fullback at the bottom.

**What would change the answer.**
- A role yardstick built on personnel and alignment (snap share in 12 and 21 personnel, in-line or slot) that matches `proe_shrunk`. Then R1 is a role measure under another name, still useful but redundant with `roles`. Plays per game already fails to match it.
- A drop in the vault season (2025, closed): it opens once, for the final check.
- A league-wide change in how teams use personnel, which would move every player's plus-minus at once (seven seasons can't rule it out).

**Verdict:** R1 holds as stated: 15% against the position's average, 12.7% against playing time, steady across seasons and groups, and strongest where there's the most evidence.

## Pitfalls
- **Leakage check 2 needed `last_kickoff` on season rows.** The first validation crashed; `player_season` now carries each player's last game.
- **A season-keyed grain had no step join.** The harness joined steps on `game_id`; season rows now join their season's retrospective step.
- **The bulk history read more seasons than a single moment.** `lineup_out` read every earlier season of plus-minus in bulk but 4 per moment, so from 2021 (the first season with a fifth earlier one) the two disagreed. Leakage checks 3 and 4 failed on every in-season variant; one window (`PM_SEASONS`) used in both fixed it, with a test. The build's own comparison of bulk against per-moment used seasons before 2021, which is why it missed this: compare the latest season too.
- **The pregame starter is known only at kickoff.** Using it would have leaked on every Saturday row, the same trap as pace's line (pace#R5).

## Not looked at
- A Sunday-morning run (inactives are known 90 minutes before kickoff).
- QB pace for movers within a season (trades), too few.
- Age (H30) as a feature: the rookie flag is in; age curves wait for `aging`.

## Could be improved
1. Use `player-pace-retro`'s skill-player plus-minus as a feature in player opportunity (targets, routes): it's the steadiest thing this project found.
2. A starter-change forecast (who'll start, with a probability) would lift R5's 32%; it belongs to participation or injury.
3. Volume in change games may need the market's total (pace#R5): the line moves when the QB changes.

## Don't redo
- Rates on touches as a pace measure (decision 0029, alternative 1).
- The pregame `qb_id` as a Saturday feature.
- `proe_lineup` as built (ties); retry only with this season's plus-minus, which needs in-season participation.

## Interface card
`player-pace-retro` only; the in-season model was discarded (the CEO, 2026-11-11).

| | |
|---|---|
| **Inputs** | `player_season.on_field_pace`. No model outputs |
| **Outputs** | Per player-season, mean q10 q50 q90 of next season's `pm_proe`, `pm_proe_pers`, `pm_pace` (`<m>_shrunk`). Tables `player_game.on_field_pace`, `player_season.on_field_pace` (2016 on) |
| **Level of detail** | Player-season (the tables also per player-game) |
| **Interval** | Once a season |
| **Cadence** | retrospective |
| **Known at** | The day after the Super Bowl, for later seasons only (rule m) |
| **How to use it** | As a prior for skill players' role (the pass tell, R1); not for QBs (no weight) or pace (R7) |
| **Feeds** | player opportunity, fantasy projections, roles |

## Hunch verdicts (build)
The exploration's verdicts stand (HUNCHES.md). The build adds:
- **H27 (movers carry their rates):** still unclear for QBs. The QB's own history helps PROE, but its clean part, his starts elsewhere, is tiny (case against).
- **H29 (plus-minus repeats):** held more strongly: next season's skill-player plus-minus is forecast 15% better from it (R1).
- **H31 (defenders like offense):** failed, confirmed: 0.8% against 15% (R8).

## Open questions for the CEO
1. ~~The brief's main test failed (R3). Keep `player-pace` (in season) as it is, or park it and keep only the retro one?~~ **Answered 2026-11-11:** "keep the results and findings of the in-season expert but discard the model". The code and its tests are removed, `player-pace` is a dead end in the registry and ROADMAP, and R2–R6 stay in KNOWLEDGE.
2. ~~Which one decision or finding to spot-check?~~ **Answered 2026-11-11:** "please spot check the 15% between season result" (R1, below).

## Technical calls (for veto at merge)
All in [decision 0029](../../docs/decisions/0029-player-pace.md):
- on-field rates and the harmonic plus-minus weight;
- the in-season expert at the team-game grain;
- the expected-starter rule;
- the QB history's shrinkage (600 plays, 500 snaps) and 3 seasons;
- `lineup_out` from earlier seasons' plus-minus;
- the retro features (decay 0.7, 4 seasons, minimum weight 20, a slope per group);
- the harness's season-keyed grain and `last_kickoff`;
- `depends_on` without pace and participation.
