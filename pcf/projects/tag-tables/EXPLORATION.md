# Exploration: Tag tables (`tag-tables`)

> A light exploration (infrastructure project). The CEO's brief for it (2026-11-01):
> - tags are half statistical labels and half the football knowledge fans, commentators and analysts point out;
> - they exist for **consistency**, and for **many categorical and conditional ways** to build features and stratify models;
> - the catalog starts broad (1A), with one fixed, versioned rule per tag (2A).
>
> This exploration asks: can a broad seed catalog be built from the `grain-tables` tables, from which years, and does each tag fire at a football-sensible rate?
> Run on 2026-11-01 with [`explore/prototype_tags.py`](explore/prototype_tags.py) on 2023–2024 (70,650 run and pass plays), plus a coverage check on 1999–2022.

**Verdict: GO.** All 52 seed tags can be built from the tables we have:
- 11 measured, 25 situation, 16 lore;
- at five levels: play, drive, game, team-game and player-game.

Almost all fire at believable rates. Examples: red zone 15% of plays, primetime 22% of team-games, three-and-out 22% of drives, revenge game 1% of player-games.

Five things shape the design:
- garbage time has two reasonable rules that disagree by a factor of three (F3);
- nflverse's model-based columns are in-sample before 2020 (F4);
- every tag needs two kinds of timing, not one (F10);
- a few lore tags leak easily if they're computed with the whole season in view (F8);
- some statistics only mean something summed up, not on one play (F12).

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **Every seed tag can be built, but from different years.** Play-by-play tags go back to 1999. Tags using completion probability or air yards start in 2006 (about 7% of passes have none). Participation tags cover 2016–2025, after the season. FTN tags start in 2022, injury-report tags in 2009, roster and player-game tags in 2002. Each tag's years are those of its inputs. | strong |
| F2 | **Rates are football-sensible** (2023–2024). Share of the rows each tag applies to (run and pass plays, drives, team-games or player-games):<br>• **measured:** successful 43%, first down 29%, explosive 9.8%, stuffed run 7%, negative play 9%, turnover 1.9%, high leverage 13%;<br>• **situation:** red zone 15%, goal-to-go 6%, money down 21%, obvious pass down 31%, short yardage 5%, two-minute drill 10%, four-minute offense 2%, middle eight 16%, backed up 3%;<br>• **lore:** scramble drill 3%, momentum swing 4.4%, stat padding 2.7%, three-and-out 22% of drives, answer drive 4.9%, goal-line stand 1.4%, trap game 4.5%;<br>• **games and players:** primetime 22% of team-games, short week 7%, off a bye 6%, divisional 35%, home underdog 20%, rookie 16% of player-games, new team 21%, revenge game 1.1%. | strong |
| F3 | **Garbage time: two common rules disagree by a factor of three.**<br>• **By win probability** (below 10% or above 90% in the second half): 20.6% of plays.<br>• **By score** (4th quarter, 17+ points; 3rd quarter, 28+): 6.8%.<br>Every score-rule play is also a win-probability play, so the score rule is the strict core and the win-probability rule adds 9,761 plays. Neutral script by win probability (20–80%, outside the last 2 minutes of a half) is 55% of plays. | strong |
| F4 | **nflverse's model-based columns are in-sample before 2020.** That's win probability, EPA (so `success`), completion probability and expected pass rate. nflfastR's models were fit around 2020 on seasons through 2019, so a 2010 play's win probability comes from a model that had seen 2010. The effect is probably small, since these describe average values of a game state, but tags built on them inherit it. Situation tags built from score, clock and field position have no such issue. | medium (model docs, not measured) |
| F5 | **Coverage sacks can't be built from participation.** It has no time-to-throw for 2,778 of 2,851 sacks, and marks 2,849 of them as pressured. FTN's `is_qb_fault_sack` (2022 on) is the nearest thing. | strong |
| F6 | **Play-by-play numbers are decimals** (`down`, `qtr`, `ydstogo`, flags like `sack`). Polars 2 refuses `down.is_in([3, 4])` on them, so tag rules compare with decimals or cast first. | strong |
| F7 | **Empty means "not listed", not "unknown", for injury reports.** 83–85% of player-games have no injury-report row. "Active while questionable" and "first game back" read empty as no. | strong |
| F8 | **Lore that compares to "usual" leaks easily.** A prototype "backup QB start" compared each starter with the season's most common starter, which uses games that haven't happened yet (19% of team-games). It has to be "most common so far", like the depth labels. "Trap game" uses next week's opponent, which is fine: the schedule is known from week 1. | strong |
| F9 | **Weather is known only after the game.** The schedule's temperature and wind are game-time readings, in `game`'s result part, and we have no forecasts. So a "weather game" tag can only stratify after the fact. Roof and outdoors are known before. | strong |
| F10 | **Tags need two kinds of timing.**<br>• **Data timing:** when PCF has the data (`known_at`), the same as the source it's built from. For example, play-by-play is known the day after kickoff.<br>• **Football timing:** whether the tag describes the moment *before* the event or its *result*. Red zone is known before the snap; successful only after the play.<br>Stratifying a model of a play by "red zone" is fine. Stratifying it by "successful" leaks the answer. The seed list splits into before the snap (15 play and drive tags), before the game (13), after the play (22), after the game (1) and after the season (1). | strong |
| F12 | **On a single throw, "positive CPOE" just means "completed"** (68% of passes): CPOE is completion minus its expected probability, so any completion is positive and any incompletion negative. It only means something summed over a game or season, so it belongs at player-game level (`passing_cpoe > 0`), not play level. | strong |
| F11 | **Drives are easy to build.** `fixed_drive` and `fixed_drive_result` are on every play, so drive tags (three-and-out, answer drive, goal-line stand) need no new source. PCF has no drive table yet. | strong |
