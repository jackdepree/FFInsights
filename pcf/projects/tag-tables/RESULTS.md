# Results: Tag tables (`tag-tables`)

> An infrastructure project: no model, so no MLflow experiment, ladder or vault.

**Date:** 2026-11-01 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** none

## In short
PCF now has a tag catalog: **52 tags and 11 references**, each defined once in `pcf.data.tags.catalog`, readable in [`docs/TAGS.md`](../../docs/TAGS.md) (generated from the code).
- **Where they live:** tags are table parts, so `load()` returns them like any column. They're on `play.tags` (29 tags), a new **`drive` table** (8 tags, 170,771 drives), `team_game.tags` and `tags_result` (9), and `player_game.tags` and `tags_result` (6).
- **Two kinds of timing:** each tag declares its football timing (before the snap, before the game, after the play, drive or game). Its data timing is the part's `known_at`, the latest of what it reads.
- **Checked:** every tag falls inside its rate band in every complete season, 1999–2025. Scrambling a play's result, or anything later, never changes a before-the-snap tag; the same holds for drives, team-games and player-games.
- **Two data fixes on the way:** 2000–2005 night kickoffs were 12 hours early (F13), and "empty" injury-report rows had been hiding inside the rates (F14).
- `pcf tables build` builds the tags too (about 10 seconds more; 13 MB on disk).

| Test from the brief | Result |
|---|---|
| Every tag builds for every season its inputs cover; every part passes `check_part` | **Pass.** The contract test now covers the tag parts and the `drive` table. Every yes/no tag fires at least once in every complete season it covers. |
| Every tag's rate falls in its band every season | **Pass, for complete seasons.** The bands were set from the measured 1999–2025 ranges (table below), with margins. The season in progress (2026) is skipped: September isn't a season's mix (no cold games yet). |
| Scrambling outcomes leaves before-snap tags unchanged | **Pass** on toy plays: every outcome column scrambled for the cut play and every later one. The same scramble does change the after-play tags, so it bites. A static test also checks that no before tag's rule reads an outcome column. |
| Removing results leaves before-game tags unchanged | **Pass** on toy team-games (later starting QBs, this and later games' weather and roof scrambled) and toy player-games. |
| "So far" tags don't change when later weeks are deleted | **Pass**: the usual starter (backup QB start), first game back, new team and revenge game. |
| `load(..., at=moment)` returns a tag only once its source is known | **Pass** on a real 2024 game: team-game tags appear with the pregame part, weather and CPOE tags only after kickoff. |
| `docs/TAGS.md` matches the code | **Pass** (a test compares them). |
| Football sanity: three-and-outs have no first down; answer drives follow an opponent touchdown | **Pass** (2001 and 2024 drives), and garbage time is never neutral script. |

**Tests:** 190 offline and 95 `local_data`, all passing (19 offline and 9 `local_data` new, the kickoff fix included). One older toy test now names the `player_game` parts it loads, since "every part" includes the tag parts.

### Measured rates (complete seasons 1999–2025, lowest and highest season)
| Level | Tag: lowest – highest share of applicable rows |
|---|---|
| play | successful 39% (1999) – 45% (2020) · explosive 8.7–10.3% · chunk 9.6–11.6% · stuffed run 16–23% of runs · negative play 7.5–10% · first down 26–32% · added WP 39–45% · high leverage 11.5–13.6% · turnover 1.8% (2025) – 2.8% (1999) · low-percentage throw 11–15% of passes · garbage time 5.3–8.7% · neutral script 55–60% · red zone 13–16% · goal to go 5.3–6.6% · backed up 2.4–3.5% · money down 19–20% · obvious pass down 33–38% · short yardage 5.2–6.2% · two-minute drill 9.5–11.4% · four-minute offense 2.0–2.9% · middle eight 16–17% · opening script 23–24% · 4th-down attempt 11% (2011) – 22% (2025) of 4th downs · hero ball 6.3–9.0% of passes · check-down 20–27% · scramble 1.5–3.3% · momentum swing 4.1–4.9% · stat padding 2.3–3.5% |
| drive | scoring 29% (1999) – 40% (2020) · three-and-out 19–25% · methodical 9–16% · quick strike 4.4–6.2% · answer drive 2.7–5.8% · goal-line stand 1.3–2.0% · backbreaker 3.1–4.8% · sudden change 10–14% |
| team-game | primetime 13.5% (2000) – 22.5% (2025) · short week 0.7–6.7% · off a bye 6–11% · divisional 34–52% · home underdog 14–21% · big favorite 3.2–11% · trap game 3.1–9.5% · backup QB start 11–25% · weather game 13–28% of outdoor games |
| player-game | rookie 14–18% · new team 19–30% · revenge game 0.6–2.7% · first game back 2.0–4.5% · active while questionable 3.1–4.0% of active players · positive-CPOE game 47–56% of passers |

## Deviations from the brief
- **`fourth_down_attempt` is after the play**, not before the snap: whether a team goes for it is only known at the snap (a punt is the alternative). Its share is of 4th downs (11–22%), not of all plays (2%).
- **A sixth football timing, `after_drive`**, for drive tags whose result is the drive's end.
- **`sudden_change` follows a "Turnover" only**, not a turnover on downs: nflverse's drive results keep them apart, and a failed 4th down is a different story from a giveaway.
- **`trap_game` is regular season only:** the playoffs have no "next game" on the schedule.
- **Status tags start in 2019** (`first_game_back`, `active_while_questionable`), not 2009: they need `ACT` and `INA` statuses, which start in 2019 (grain-tables#F3). The injury report alone can't tell "active" from "inactive" before then.
- **`first_game_back` also counts a return from missing the team's previous game off the 53-man roster** (injured reserve), not only "listed Out the previous week".
- **`new_team` compares with the team at the end of the player's previous season**, so it starts in 2003. `revenge_game` counts any earlier game for that opponent, the same season included (a mid-season trade), and starts in 2003 too: 2002 had no earlier games to remember.
- **`positive_cpoe_game` needs 10+ attempts**, so a 2-for-2 cameo doesn't count.
- **`primetime` starts in 2000:** 1999 has no kickoff times (timeline#F1).
- **No tags read FTN or participation yet:** those are references. So no separate tag part for their later `known_at` was needed.

## Terms
As in the brief, now in `docs/GLOSSARY.md`: **tag**, **tag family** (measured, situation, lore), **football timing** (before the snap, before the game, after the play, after the drive, after the game, after the season), **reference tag**. And one more:
- **Rate band:** the share of applicable rows a tag should fire on in a complete season. A season outside it fails the build's checks (rule h).

## Findings
F1–F12 came from the light exploration ([EXPLORATION.md](EXPLORATION.md)). F13–F18 came from the build.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | Every seed tag can be built, from the years its inputs cover. | [EXPLORATION.md](EXPLORATION.md) | strong | the catalog |
| F2 | Rates are football-sensible (now measured on every season: the table above). | exploration; `check.rates` | strong | the bands |
| F3 | Garbage time by win probability (21% of plays) and by score (7%) disagree by a factor of three. The CEO chose score and clock (1A). | [EXPLORATION.md](EXPLORATION.md) | strong | situation tags |
| F4 | nflverse's WP, EPA, CP and expected pass rate are in-sample before 2020. | model docs | medium | measured tags built on them |
| F5 | Coverage sacks can't be built from participation; FTN's QB-fault sack is the nearest (2022→). | [EXPLORATION.md](EXPLORATION.md) | strong | references |
| F6 | Play-by-play numbers are decimals: compare `down` with `3.0`, not `3`. | Polars error | strong | every play rule |
| F7 | No injury-report row means "not listed", not "unknown". | [EXPLORATION.md](EXPLORATION.md) | strong | injury tags |
| F8 | "Usual" must mean "so far": a whole-season usual starter leaks the future. | [EXPLORATION.md](EXPLORATION.md) | strong | lore tags |
| F9 | Weather is known only after the game: we have readings, not forecasts. | [EXPLORATION.md](EXPLORATION.md) | strong | weather_game |
| F10 | Tags need football timing as well as data timing. | [EXPLORATION.md](EXPLORATION.md) | strong | every user of tags |
| F11 | Drives are easy to build from `fixed_drive` and `fixed_drive_result`. | [EXPLORATION.md](EXPLORATION.md) | strong | the `drive` table |
| F12 | On one throw, positive CPOE just means "completed": it's a game-level tag. | [EXPLORATION.md](EXPLORATION.md) | strong | positive_cpoe_game |
| F13 | **Leak-ish data error, fixed: 2000–2005 schedules write 9 PM night kickoffs as "09:00".** Monday night games (15–17 a season), and a few Thursday and Saturday games, were 12 hours early, so primetime was 7% of team-games instead of 13–16%. No game kicked off before noon Eastern before London games began (2007), so `standard.schedules` moves any pre-noon kickoff in 2000–2005 to the evening. `kickoff`, and every `known_at` derived from it, moved for those games. | the build; `test_standard` and a `local_data` test | strong | game, team_game, timeline 2000–2005 |
| F14 | **A share that ignores empties hides rule bugs.** `active_while_questionable` first measured about 100% and `first_game_back` 29–48%: players with no report row got an empty tag instead of "no", and the share counted only the non-empty ones. Rules now say "no" for "not on the report" (F7). Empty is kept for "doesn't apply". | the band check | strong | any rule on a sparse part |
| F15 | **Weather readings are missing for half the 2022 outdoor games (54% have them) and 79% in 2023**, against 95–99% otherwise. 2022's weather share (28%) is high because the games that have readings lean late-season. | `game.result` | strong | weather_game 2022–2023 |
| F16 | **Real football moves some rates a lot, so bands must be wide in places:** divisional games were half the schedule before the 2002 realignment (52%); 2001 had 11% of team-games off a bye (the week postponed after 9/11); 4th-down attempts doubled from 2011 (11%) to 2025 (22%); scoring drives rose from 29% (1999) to 40% (2020). | `check.rates` | strong | the bands; any trend over years |
| F17 | **The backup QB started 11–25% of team-games** by the "so far" rule, highest in 1999 (25%). A team's first game has no "usual" starter, so it's empty. | `check.rates` | strong | backup_qb_start |
| F18 | **1999 has no primetime tag and most tags have years shorter than 1999→:** CPOE and air-yards tags from 2006, roster tags from 2002–2003, status tags from 2019. `docs/TAGS.md` lists each tag's years. | the build | strong | anyone stratifying across years |

## Pitfalls
- **Shares that skip empties** (F14). Check a tag's rate against the rows it should apply to, not only the rows where it isn't empty.
- **Times on a 12-hour clock** (F13). Look at the distribution of kickoff hours by weekday before trusting a time column.
- **A season in progress fails season bands:** in September, no game is cold. Hold bands to complete seasons only.
- **Rules that read earlier tags** (`stat_padding` reads `garbage_time`): the catalog applies tags in order, so an earlier tag must come first.

## Not looked at
- **Whether any lore tag predicts anything.** That's the point of pinning lore to a rule ("is a trap game real?"), but it's an expert's job, not this project's.
- **Tags on FTN and participation** (play action rate, pressure): only referenced. When a tag is built from them it needs its own part, with their later `known_at`.
- **Season-level and career tags** (breakout season, contract year): `after_season` timing exists, but no tag uses it yet.
- **Flexed games:** primetime uses the final kickoff time, known from week 1, the same small issue as grain-tables' "not looked at".

## Could be improved
1. **The gateway should enforce football timing** (`validation-harness`): refuse an after-the-play tag as a feature of the same row.
2. **Win-probability versions** of garbage time and neutral script as `_v2` tags, if an expert wants them (F3).
3. **Forecast weather**, if a free source turns up, for a before-the-game weather tag (F9).

## Don't redo
- Don't build a tag on single-play CPOE (F12).
- Don't compare with "the season's usual" anything (F8).
- Don't fix a tag's rule in place: add `_v2` (2A).

## Interface card
Also in `registry.yaml` under `interface`.

| | |
|---|---|
| **Inputs** | `grain-tables`: `play` (pbp), `game` (result), `team_game` (pregame), `player_game` (game_status, injury, stats; the spine's history) |
| **Outputs** | `pcf.data.tags`: `TAGS`, `REFERENCES`, `Tag`, `tags_for(level, part)`, `BEFORE`, `build_tags(name, seasons)` (run by `pcf tables build`). `pcf.data.tags.check`: `rates`, `out_of_band`. Parts: `play.tags`; `drive` table (`summary`, `tags`); `team_game.tags`, `team_game.tags_result`; `player_game.tags`, `player_game.tags_result`. Columns `tag_<name>` (`_v2` for new versions). The catalog page: `docs/TAGS.md`. |
| **Level of detail** | play; drive; team-game; player-game |
| **Interval** | each tag's own years (`docs/TAGS.md`); 1999→ for most play and drive tags |
| **Cadence** | not applicable (rebuilt with the tables) |
| **Known at** | the part's `known_at`, the latest of the parts each tag reads: play-by-play for play and drive tags; the pregame part for team-game tags; game status and injuries for player-game tags; results and stats for the `tags_result` parts |
| **How to use it** | Only tags with timing before the snap or before the game may describe the row being predicted. Other tags are outcomes: targets, or features from earlier rows. Empty means "doesn't apply" or "not covered that year", never "no". Add a tag with a definition, a band and a test; a changed rule is a new version. |
| **Feeds** | every layer-1 expert (stratifying, interactions), `validation-harness` (the timing check) |

## Open questions for the CEO
- **Approve the merge?** Nothing new to install. After merging, `uv run pcf tables build` rebuilds the tables and tags (about 35 seconds).
- **The catalog is yours to edit** whenever you like (as agreed). Two you may want to look at first: `backup_qb_start` fires on 11–25% of team-games, which is more than "the backup" suggests: it includes a new starter who takes over mid-season, until they've started as often as the old one. And `weather_game` counts game-time readings, so it can't describe an upcoming game.
