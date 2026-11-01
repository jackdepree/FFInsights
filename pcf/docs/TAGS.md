# Tags

> Generated from `src/pcf/data/tags/catalog.py` by `python -m pcf.data.tags.page`. Don't edit by
> hand: change the catalog (a changed rule is a new version) and regenerate.

Tags are football's shared vocabulary as yes/no (or category) labels: half statistics
(successful, explosive), half what fans, commentators and analysts point out (hero ball, answer
drive, trap game). They give every project the same definitions, and many ways to build features
and stratify models. Glossary: *tag*, *tag family*, *football timing*, *reference tag*.

**How to use them**
- They're table parts: `load("play", parts=["tags"])`, `load("drive")`,
  `load("team_game", parts=["tags", "tags_result"])`, `load("player_game", parts=["tags",
  "tags_result"])`. Each column is `tag_<name>` (`tag_<name>_v2` for a second version).
- **Empty means the tag doesn't apply** (a run has no `low_percentage_throw`) or its data doesn't
  cover that season. It never means "no".
- **Football timing decides how a tag may be used.** Only tags known *before the snap* or *before
  the game* may describe the row a model predicts (stratifying plays by red zone is fine;
  by successful, it leaks the answer). Tags known *after* describe earlier rows only, such as a
  player's share of explosive plays in past games.
- **Data timing** is the part's `known_at`: the latest of the parts each tag reads.
- **Band:** the share of applicable rows the tag fires on in a complete season. The build's checks
  fail when a season falls outside it (rule h).

## play tags (29)

Parts: `play.tags`.

| Tag | Family | Timing | Meaning | Rule | Years | Band |
|---|---|---|---|---|---|---|
| `tag_successful` | measured | after the play | the play gained positive expected points | EPA above 0 (nflverse `success`) | 1999→ | 37.0%–50.0% |
| `tag_explosive` | measured | after the play | a big play | run of 10+ yards or pass of 20+ yards | 1999→ | 7.0%–13.0% |
| `tag_chunk` | measured | after the play | a chunk of yards in one play | any gain of 15+ yards | 1999→ | 7.0%–13.0% |
| `tag_stuffed_run` | measured | after the play | the run went nowhere | run for 0 or fewer yards | 1999→ | 15.0%–25.0% |
| `tag_negative_play` | measured | after the play | lost yards | loss of yards, sacks included | 1999→ | 6.0%–12.0% |
| `tag_first_down_gained` | measured | after the play | moved the chains | the play earned a first down | 1999→ | 24.0%–33.0% |
| `tag_added_win_probability` | measured | after the play | the play helped the offense win | WPA above 0 | 1999→ | 38.0%–50.0% |
| `tag_high_leverage` | measured | after the play | a play that mattered | WPA of 5 points or more either way | 1999→ | 9.0%–17.0% |
| `tag_turnover` | measured | after the play | gave the ball away | interception or lost fumble | 1999→ | 1.2%–3.5% |
| `tag_low_percentage_throw` | measured | after the play | a risky throw | pass with under 40% completion probability | 2006→ | 7.0%–16.0% |
| `tag_garbage_time` | situation | **before the snap** | the game is decided | 4th quarter with a 17+ point margin, or 3rd quarter with 28+ (CEO decision 1A) | 1999→ | 4.0%–10.0% |
| `tag_game_script` | situation | **before the snap** | who's ahead, from the offense's view | leading by 9+, trailing by 9+, or neutral (within one score) (values: leading, trailing, neutral) | 1999→ | — |
| `tag_neutral_script` | situation | **before the snap** | teams play their normal game | within one score (8 points), outside the last 2 minutes of a half, regulation only (CEO decision 1A) | 1999→ | 50.0%–68.0% |
| `tag_red_zone` | situation | **before the snap** | inside the 20 | inside the opponent's 20 | 1999→ | 11.0%–19.0% |
| `tag_goal_to_go` | situation | **before the snap** | goal to go | goal-to-go down | 1999→ | 4.0%–9.0% |
| `tag_backed_up` | situation | **before the snap** | backed up against its own goal line | inside its own 10 | 1999→ | 1.5%–4.5% |
| `tag_money_down` | situation | **before the snap** | 3rd down | 3rd down | 1999→ | 17.0%–25.0% |
| `tag_obvious_pass_down` | situation | **before the snap** | everyone knows a pass is coming | 2nd and 8+, or 3rd or 4th and 5+ | 1999→ | 28.0%–40.0% |
| `tag_short_yardage` | situation | **before the snap** | a yard or two to go on a money down | 3rd or 4th and 2 or less | 1999→ | 5.0%–10.0% |
| `tag_two_minute_drill` | situation | **before the snap** | hurrying to score before the half | last 2 minutes of a half, offense not leading by more than 8 | 1999→ | 7.0%–14.0% |
| `tag_four_minute_offense` | situation | **before the snap** | running out the clock | last 4 minutes of the game, offense leading by 1 to 16 | 1999→ | 1.0%–4.0% |
| `tag_middle_eight` | situation | **before the snap** | the stretch around halftime where a team can score twice | last 4 minutes of the 1st half or first 4 minutes of the 2nd | 1999→ | 13.0%–20.0% |
| `tag_opening_script` | lore | **before the snap** | the coach's scripted opening plays | fewer than 15 earlier run or pass plays by this offense in the game | 1999→ | 20.0%–30.0% |
| `tag_fourth_down_attempt` | situation | after the play | went for it on 4th down | a run or pass on 4th down (the decision is only known at the snap) | 1999→ | 10.0%–45.0% |
| `tag_hero_ball` | lore | after the play | the QB forced a difficult throw downfield | throw 15+ yards downfield with under 35% completion probability | 2006→ | 3.0%–10.0% |
| `tag_check_down` | lore | after the play | took the short, safe throw | pass thrown under 2 yards downfield, not a scramble | 2006→ | 15.0%–35.0% |
| `tag_scramble_drill` | lore | after the play | the play broke down and the QB ran | QB scramble (nflverse `qb_scramble`) | 1999→ | 1.0%–5.0% |
| `tag_momentum_swing` | lore | after the play | a play that swung the game | WPA of 10 points or more either way, or a turnover | 1999→ | 3.0%–7.0% |
| `tag_stat_padding` | lore | after the play | yards that came when the game was decided | trailing team gains yards in garbage time | 1999→ | 1.0%–5.0% |

## drive tags (8)

Parts: `drive.tags`.

| Tag | Family | Timing | Meaning | Rule | Years | Band |
|---|---|---|---|---|---|---|
| `tag_scoring_drive` | measured | after the drive | the drive scored | ends in a touchdown or field goal | 1999→ | 27.0%–45.0% |
| `tag_three_and_out` | lore | after the drive | three plays and a punt | ends in a punt without a first down | 1999→ | 15.0%–28.0% |
| `tag_methodical_drive` | lore | after the drive | a long, grinding drive | 10 or more run or pass plays | 1999→ | 7.0%–20.0% |
| `tag_quick_strike` | lore | after the drive | scored in a hurry | touchdown in 4 or fewer plays, or 90 seconds or less | 1999→ | 3.0%–8.0% |
| `tag_answer_drive` | lore | after the drive | answered a touchdown with a touchdown | touchdown right after the opponent's touchdown | 1999→ | 2.0%–7.0% |
| `tag_goal_line_stand` | lore | after the drive | the defense held at the goal line | had 1st and goal inside the 5 and didn't score a touchdown | 1999→ | 0.5%–2.5% |
| `tag_backbreaker` | lore | after the drive | a score right before halftime | touchdown or field goal ending in the last 2 minutes of the 1st half | 1999→ | 2.5%–6.0% |
| `tag_sudden_change` | situation | **before the snap** | taking over after a turnover | the drive starts right after the opponent turned the ball over | 1999→ | 6.0%–14.0% |

## team-game tags (9)

Parts: `team_game.tags`, `team_game.tags_result`.

| Tag | Family | Timing | Meaning | Rule | Years | Band |
|---|---|---|---|---|---|---|
| `tag_primetime` | situation | **before the game** | the night game | kickoff at 7pm Eastern or later (1999 has no kickoff times) | 2000→ | 8.0%–30.0% |
| `tag_short_week` | situation | **before the game** | a short week (Thursday games) | 4 or fewer days of rest | 1999→ | 0.0%–10.0% |
| `tag_off_bye` | situation | **before the game** | coming off a bye | 13 or more days of rest | 1999→ | 2.0%–13.0% |
| `tag_divisional` | situation | **before the game** | a division rival | division game (half the schedule before the 2002 realignment) | 1999→ | 30.0%–55.0% |
| `tag_home_underdog` | situation | **before the game** | the home team getting points | home team that's the underdog | 1999→ | 12.0%–25.0% |
| `tag_big_favorite` | situation | **before the game** | a heavy favorite | favored by 10 or more | 1999→ | 2.0%–13.0% |
| `tag_trap_game` | lore | **before the game** | a big favorite looking ahead to a rival | favored by 7+, with a division game next (regular season) | 1999→ | 2.0%–11.0% |
| `tag_backup_qb_start` | lore | **before the game** | the backup is starting | today's starting QB isn't the team's most common starter so far this season | 1999→ | 5.0%–28.0% |
| `tag_weather_game` | situation | after the game | a cold or windy game | outdoors, 32°F or colder or 15+ mph wind (game-time readings: no forecasts) | 1999→ | 5.0%–30.0% |

## player-game tags (6)

Parts: `player_game.tags`, `player_game.tags_result`.

| Tag | Family | Timing | Meaning | Rule | Years | Band |
|---|---|---|---|---|---|---|
| `tag_rookie` | situation | **before the game** | a rookie | first NFL season | 2002→ | 10.0%–22.0% |
| `tag_new_team` | situation | **before the game** | new to the team this season | on a different team than at the end of the player's previous season | 2003→ | 10.0%–30.0% |
| `tag_revenge_game` | lore | **before the game** | facing a former team | the opponent is a team the player was on in an earlier game | 2003→ | 0.3%–3.0% |
| `tag_first_game_back` | situation | **before the game** | back from injury | active after being listed Out for the team's previous game, or after missing the team's previous game off the 53-man roster | 2019→ | 1.0%–8.0% |
| `tag_active_while_questionable` | situation | **before the game** | playing through an injury | listed Questionable, then active (not on the report counts as no: tag-tables#F7) | 2019→ | 2.0%–8.0% |
| `tag_positive_cpoe_game` | measured | after the game | completed more than expected | the passer's CPOE for the game is above 0 (10+ attempts) | 2006→ | 40.0%–62.0% |

## Reference tags (11)

Columns nflverse already has, listed here so they're found, not copied.

| Name | Column | Meaning | Years |
|---|---|---|---|
| play_action | `play.ftn`: `is_play_action` | play action | FTN charting (2022→) |
| screen | `play.ftn`: `is_screen_pass` | screen pass | FTN charting (2022→) |
| rpo | `play.ftn`: `is_rpo` | run-pass option | FTN charting (2022→) |
| trick_play | `play.ftn`: `is_trick_play` | trick play | FTN charting (2022→) |
| no_huddle | `play.ftn`: `is_no_huddle` | no huddle | FTN charting (2022→) |
| motion | `play.ftn`: `is_motion` | pre-snap motion | FTN charting (2022→) |
| blitz | `play.ftn`: `n_blitzers` | blitz (more than 0 blitzers) | FTN charting (2022→) |
| out_of_pocket | `play.ftn`: `is_qb_out_of_pocket` | QB out of the pocket | FTN charting (2022→) |
| interception_worthy | `play.ftn`: `is_interception_worthy` | a throw that should have been intercepted | FTN charting (2022→) |
| held_the_ball | `play.ftn`: `is_qb_fault_sack` | sack on the QB: held the ball (stands in for coverage sack, tag-tables#F5) | FTN charting (2022→) |
| pressure | `play.participation`: `was_pressure` | QB pressured | participation (2016–2025, after the season) |

52 tags: 12 measured, 25 situation, 15 lore; 11 references.
