# Brief: Tag tables (`tag-tables`)

> An infrastructure project, but half of it is football knowledge, so the CEO owns the catalog's content. Two calls for the CEO (end of page). Light exploration: [EXPLORATION.md](EXPLORATION.md).

**Status:** draft · **Layer:** 0, data (Phase 0) · **Cadence:** — (rebuilt with the tables)

**Agreed in the brainstorm (CEO, 2026-11-01):**
- **Purpose.** Tags are half statistical labels and half the football knowledge fans, commentators and analysts point out. They exist for consistency, and to give many categorical and conditional ways to build features and stratify models.
- **1A:** start with a broad catalog.
- **2A:** one fixed, versioned rule per tag.

## The question
Turn football's shared vocabulary into labels on plays, drives, games and players, with one written rule for each, so every expert means the same thing by "garbage time" or "answer drive". Examples range from "successful play" and "red zone" to "hero ball" and "trap game".

## Why it matters
- **Consistency.** Without tags, every expert re-derives garbage time, red zone or "obvious passing down" its own way, and their results can't be compared.
- **Ways to slice.** Tags give the ladder ready-made splits and interactions: does a receiver's VOE hold up in neutral script, does a defense fold on money downs, does a QB play hero ball when trailing?
- **Testing football lore.** Once "answer drive" or "trap game" is a fixed rule, we can test whether it predicts anything, or is just a story told after the fact.

## Terms
- **Standard terms used:** EPA, CPOE, WPA, success rate, known_at, table part, spine. See `docs/GLOSSARY.md`.
- **New terms:**
  - **Tag:** a named label on a row of a table (a play, drive, game, team-game or player-game), computed by one written rule. It's usually yes/no; some are categories (game script: leading, trailing, neutral).
  - **Tag family:**
    - **measured:** a statistical definition, e.g. successful = positive EPA;
    - **situation:** the game state, e.g. red zone;
    - **lore:** a commentator's idea pinned to a rule, e.g. answer drive.
  - **Football timing:** whether a tag describes the moment *before* the event or its *result*. The five values are before the snap, before the game, after the play, after the game and after the season. It's separate from `known_at`, which is when PCF has the data (F10).
  - **Reference tag:** a catalog entry that points at a column nflverse already has (FTN's `is_play_action`), so the catalog lists every way to slice without copying data.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `grain-tables` | `play`, `game`, `team_game`, `player_game`, the parts mechanism, `load(name, at)`, `check_part` | Tags are saved as table parts with their own `known_at` |
| `grain-tables#F11`, `#F18` | Pre-2016 roster status isn't weekly; traded players appear on two teams | Player-game tags must respect both |
| `cleaning-port` depth labels | Average depth "so far", never the whole season | The pattern for "usual starter" and similar lore (F8) |
| `timeline` | Kickoffs and week windows | Primetime, short week, off a bye |
| exploration F1–F12 | Years, rates, the garbage-time split, timing classes | The catalog below |

**Already tried:** `old/` filtered garbage time and "neutral" situations inline in each notebook, each slightly differently. Nothing was shared.

## Assumptions (technical calls, Claude's)
- **The catalog is code, with a readable page generated from it.** Each tag is defined once in `pcf.data.tags` with:
  - its name, level, family and football timing;
  - its everyday meaning and its rule;
  - its years, and an expected rate band;
  - the project that added it.
  - `docs/TAGS.md` is generated from the code for you to read, and a test keeps it current.
- **Tags are saved as table parts**, so `load(name, at)` returns them with everything else:
  - `play`, `team_game` and `player_game` each get a tags part.
  - Tags built from FTN or participation go in their own part, so they keep those sources' later `known_at`.
  - A new small `drive` table holds drive tags (F11).
  - Columns are `tag_<name>`. A changed rule becomes `tag_<name>_v2` alongside the old one, never a silent edit (2A).
- **Football timing is enforced by a test:**
  - Scrambling a play's outcome columns (yards, EPA, result) must not change any of its before-snap tags.
  - Removing a game's results must not change its before-game tags.
  - Tags that compare to "usual" use data so far only: deleting later weeks changes nothing earlier (F8).
- **Football sanity on every build:** each tag has an expected rate band (red zone 10–20% of plays). A season outside its band fails the build, which also catches source changes (rule h).
- **Situation tags avoid nflverse's model columns where the meaning allows** (F4); see question 1.
- **Reference tags** (play action, screen, RPO, blitz, no-huddle, motion, interception-worthy, QB-fault sack) are listed, not copied.
- **Any later project can add a tag:** a definition, a rate band, a test. Its brief names the tags it adds.

## The seed catalog (v1: first drafts, yours to edit)
"Known" is football timing. Shares are from 2023–2024 (F2). Years follow their inputs (F1).

**Play: measured** (after the play; 1999→ unless noted)
| Tag | Rule v1 | Share |
|---|---|---|
| successful | positive EPA (nflverse `success`) | 43% |
| explosive | run 10+ yards or pass 20+ yards | 10% |
| chunk | any gain of 15+ yards | 10% |
| stuffed_run | run for 0 or fewer yards | 7% |
| negative_play | loss of yards (sacks included) | 9% |
| first_down_gained | the play earned a first down | 29% |
| added_win_probability | positive WPA | 44% |
| high_leverage | WPA of 5 points or more either way | 13% |
| turnover | interception or lost fumble | 1.9% |
| low_percentage_throw ("risky") | completion probability under 40% (2006→) | 11% of passes |

**Play: situation** (before the snap; 1999→)
| Tag | Rule v1 | Share |
|---|---|---|
| garbage_time | **question 1** | 7% or 21% |
| game_script (category) | offense leading by 9+ / trailing by 9+ / within one score | — |
| neutral_script | within one score, not the last 2 minutes of a half (question 1) | — |
| red_zone | inside the opponent's 20 | 15% |
| goal_to_go | goal-to-go down | 6% |
| backed_up | inside its own 10 | 3% |
| money_down | 3rd down | 21% |
| fourth_down_attempt | a run or pass on 4th down | 2% |
| obvious_pass_down | 2nd and 8+, or 3rd/4th and 5+ | 31% |
| short_yardage | 3rd/4th and 2 or less | 5% |
| two_minute_drill | last 2 minutes of a half, offense not leading by more than 8 | 10% |
| four_minute_offense | last 4 minutes, offense leading by 1–16 | 2% |
| middle_eight | last 4 minutes of the 1st half, first 4 of the 2nd | 16% |
| opening_script | the offense's first 15 plays of the game | 24% |

**Play: lore** (after the play)
| Tag | Rule v1 | Share |
|---|---|---|
| hero_ball | throw 15+ yards downfield with under 35% completion probability (2006→) | 6% of passes |
| check_down | pass caught or thrown under 2 yards downfield, not a scramble | 15% |
| scramble_drill | QB scramble (nflverse `qb_scramble`) | 3% |
| momentum_swing | WPA of 10 points or more either way, or a turnover | 4.4% |
| stat_padding | trailing team gains yards in garbage time | 3% |

**Drive** (after the drive unless noted; new `drive` table)
| Tag | Rule v1 | Share of drives |
|---|---|---|
| scoring_drive | ends in a touchdown or field goal | 39% |
| three_and_out | punt with no first down | 22% |
| methodical_drive | 10+ plays | 16% |
| quick_strike | touchdown in 4 plays or fewer, or 90 seconds or less | 5% |
| answer_drive | touchdown right after the opponent's touchdown | 5% |
| goal_line_stand | 1st and goal inside the 5, no touchdown | 1.4% |
| backbreaker | score in the last 2 minutes of the 1st half | 4% |
| sudden_change (before the snap) | drive starts right after a turnover | 12% |

**Team-game** (before the game unless noted)
| Tag | Rule v1 | Share |
|---|---|---|
| primetime | kickoff 7pm Eastern or later | 22% |
| short_week | 4 or fewer days of rest | 7% |
| off_bye | 13+ days of rest | 6% |
| divisional | division game | 35% |
| home_underdog | home team getting points | 20% |
| big_favorite | favored by 10+ | 4% |
| trap_game | favored by 7+, with a division game next | 5% |
| backup_qb_start | today's starting QB isn't the team's most common starter so far that season | to measure |
| weather_game (after the game) | outdoors, 32°F or colder or 15+ mph wind | 8% |

**Player-game** (before the game; 2002→, injury tags 2009→)
| Tag | Rule v1 | Share |
|---|---|---|
| rookie | first NFL season | 16% |
| new_team | first season with this team | 21% |
| revenge_game | facing a team the player was on in an earlier season | 1.1% |
| first_game_back | active after being listed Out the previous week | to measure |
| active_while_questionable | listed Questionable, then active | to measure |
| positive_cpoe_game (after the game) | the passer's CPOE for the game is above 0 (F12) | to measure |

**Reference tags** (listed, not copied): play action, screen, RPO, trick play, no-huddle, motion, blitz (`n_blitzers` > 0), QB out of pocket, interception-worthy, QB-fault sack ("held the ball", stands in for coverage sack, F5), from FTN (2022→); pressure, from participation (2016–2025).

That's 52 tags plus 11 references, about half measured or situation and half lore or game context.

## Tests
- **Success looks like:**
  - Every tag builds for every season its inputs cover, and every tag part passes `check_part`.
  - **Rate bands:** every tag's rate falls in its band every season. A failure names the tag and season.
  - **Football timing:**
    - scrambling outcomes leaves before-snap tags unchanged;
    - removing results leaves before-game tags unchanged;
    - "so far" tags don't change when later weeks are deleted.
  - `load("play", at=moment)` returns a tag only once its source is known. `docs/TAGS.md` matches the code.
  - **Football sanity:** for example, no `three_and_out` drive has a first down, and `answer_drive` always follows an opponent touchdown.
- **Failure looks like:** tags that can't be built for the years their inputs cover, rates that swing for no football reason, or a before-snap tag that changes when the result changes.

## Inputs and outputs
- **Inputs:** the `grain-tables` tables (play-by-play, FTN, participation, schedules, rosters, injuries), timeline kickoffs.
- **Outputs:**
  - `pcf.data.tags`: the catalog and its builders;
  - tag parts on `play`, `team_game` and `player_game`, plus the new `drive` table;
  - `docs/TAGS.md`;
  - `pcf tables build` builds the tags too.

## How it will be used
Experts read tags through the gateway like any column, and stratify or interact by them on the ladder. Before-snap and before-game tags can describe the row being predicted. After-the-play tags are outcomes: targets, or features built from earlier rows only. The gateway (`validation-harness`) will enforce that from the catalog's timing.

## Questions for the CEO
1. **Should situation tags be measured by score and clock, or by win probability?**
   - **Why it matters:** garbage time and neutral script are the most used filters in football analytics, and the two ways disagree a lot. By win probability, garbage time is 21% of plays; by score, 7% (F3).
   - **A. Score and clock (recommended).** Garbage time = 4th quarter with a 17+ point margin, or 3rd quarter with 28+. Neutral script = within one score (8 points), outside the last 2 minutes of a half. It's how commentators talk ("a three-score game"), needs no model, and has no in-sample issue (F4). Its weakness: it ignores a team's strength, so a 17-point lead with 8 minutes left counts the same for every team.
   - **B. Win probability.** The analytics community's convention: garbage time = win probability below 10% or above 90% in the second half (21%); neutral = 20–80%. It adjusts for time, field position and timeouts. But nflverse's model was fit on 2000–2019, so it's in-sample for those years, and it tags a fifth of all plays as garbage.
   - **C. Whichever makes the models look best** *(tempting but bad)*. It's the cherry-picking 2A rules out: the definition would be fitted, not football.
2. **Is the seed catalog right?** It's yours to edit: add, drop or redefine any tag. The lore rules especially are my first drafts of commentator ideas, e.g. hero ball, trap game and backbreaker. Anything you leave unchanged ships as v1.

## Plan
No ladder (no model). The catalog structure, the timing tests and the rate bands first, on toy rows. Then play and drive tags, then team-game and player-game tags, then `docs/TAGS.md` and the real-data tests. About 2 sessions, then the results page and your merge.
