# Data sources

> Every source PCF uses, how far back it goes, when it updates, and **when its data counts as "known"** (rule c).
> **nflverse (`nflreadpy`) is the backbone, the Bible.** Everything else adds to it.
> Facts here were verified on **2026-10-30** against the nflverse release listing and live loads, and corrected the same day by the [package-scaffold profile](../projects/package-scaffold/EXPLORATION.md). Re-verify a source before relying on a detail that may have changed.

## Rules for using sources

### Trust tiers
| Tier | What | Rule |
|---|---|---|
| **1: Structured and maintained** | nflverse | The backbone. Use it freely. |
| **2: Unofficial or public APIs** | ESPN, Sleeper, Fantasy Football Calculator | Always save the raw response. Expect breakage and have a fallback. Use for extra signal, case studies and benchmarks. |
| **3: Free tiers with limits** | The Odds API, College Football Data, Open-Meteo | Budget guards. Keys live in `pcf/.env` and in Actions secrets. |
| **4: Unstructured text** | RSS feeds, Reddit | Save the text plus timestamps. A compiler turns it into structured signals (e.g. sentiment). Nothing becomes a feature without an exploration first. |

### Known-at rules
`known_at` is **the earliest moment PCF could have had this data, in this form, for a live prediction.** Every row in the data layer carries one.
- When a source publishes a timestamp (`dt`, `trade_date`, `scrape_date`), use it, **after checking it records first availability and not a later re-pull** (FTN's `date_pulled` doesn't; see its row).
- When it doesn't, use the conservative rule in that source's table below.
- If unsure, pick the later time. Being a little late costs a little accuracy. Being early is leakage.

### Revisions and snapshots
Some sources get corrected after the fact: stat corrections, roster moves, updated depth charts. Loading them today can show information that wasn't true at the time.
- **Sources that change** (rosters, depth charts, injuries, rankings, ADP, lines): keep **dated snapshots** of what we pulled and when.
- **Stable history** (past seasons' play-by-play, combine, draft): keep the latest version only.

### Manual downloads
**Never recurring.** A one-time download for a research case study is fine (e.g. Big Data Bowl). Anything needed weekly or monthly must be automated.

## How ids join

| Id | Meaning | Where it comes from |
|---|---|---|
| `gsis_id` | **The player id.** Everything joins on it. | nflverse (`players`, rosters, stats) |
| `game_id` | **The game id**, e.g. `2026_08_CAR_GB` | nflverse (`schedules`, play-by-play) |
| `game_id` + `play_id` | **The play id** | nflverse play-by-play. FTN maps to it via `nflverse_game_id` and `nflverse_play_id`. |
| ESPN, PFR, Sleeper, Yahoo ids, … | Other player ids | Mapped to `gsis_id` by `load_ff_playerids` (ESPN prop athletes matched 99.7–99.9% for 2024+) |
| ESPN event id | ESPN's game id | Mapped to `game_id` through the `espn` column of `load_schedules` (100% matched) |
| The Odds API event id | The Odds API's game id | Matched to `game_id` by home team, away team and kickoff date |

## Tier 1: nflverse (`nflreadpy`)

"Updates" is in-season timing as observed. For example, Thursday night's game was in play-by-play by 11:37 UTC the next morning.

### Plays and games
| Source (loader) | Level of detail | Years | Updates | Known-at rule | Feeds |
|---|---|---|---|---|---|
| Play-by-play (`load_pbp`) | play | 1999→ | Morning after each game | Kickoff + 1 day | Context, VOE, team efficiency, tags, nearly everything |
| Schedules (`load_schedules`) | game | 1999→ | Several times a week | Game facts (date, roof, surface, rest): at schedule release. **Lines:** spreads and totals 1999→, moneylines 2006→. They sit *near* the closing line (they match ESPN's close in 45–84% of games), so treat them as known at kickoff. | Environment, Elo, baselines, closing-line fallback |
| FTN charting (`load_ftn_charting`) | play | 2022→ | About 1–2 weeks behind (week 7 on Oct 30) | **History:** kickoff + 14 days. **Live:** our own fetch time. Not `date_pulled`: whole seasons were re-pulled later (2022–23 all show 2024-09-06), so it isn't first availability ([exploration](../projects/package-scaffold/EXPLORATION.md)). | Context, roles, schemes, line play |
| Officials (`load_officials`) | game | 2015→ | Preseason assignments, then weekly | Kickoff − 2 days | Referee crews (parked) |

### Players and usage
| Source (loader) | Level of detail | Years | Updates | Known-at rule | Feeds |
|---|---|---|---|---|---|
| Player stats (`load_player_stats`) | player-week | 1999→ | Morning after | Kickoff + 1 day | Baselines, every player expert |
| Team stats (`load_team_stats`) | team-week | 1999→ | Morning after | Kickoff + 1 day | Team experts |
| Snap counts (`load_snap_counts`) | player-game | 2013→ | Morning after | Kickoff + 1 day | Participation, fatigue, vacated opportunity |
| ⚠️ **Participation** (`load_participation`) | play (who was on the field, routes, coverage, pressure, time to throw) | 2016–**2025** | **After the season only** (last update Feb 2026; no 2026 data) | End of season | **Training only.** See the callout below. |
| Next Gen Stats (`load_nextgen_stats`) | player-week | 2016→ | Morning after | Kickoff + 1 day | Context, QB talent, separation, time to throw (weekly) |
| PFR advanced stats (`load_pfr_advstats`) | player-week | 2018→ | About a week behind (week 7 on Oct 30) | The Tuesday after the following week (conservative) | Pressure, drops, broken tackles |
| Expected fantasy points (`load_ff_opportunity`) | player-week | 2006→ | Morning after | Kickoff + 1 day | Opportunity quality (benchmark) |
| Depth charts (`load_depth_charts`) | player-snapshot | 2001→ | **Daily** from 2025: snapshot rows with `dt` and **no `season` or `week`**. Weekly rows through 2024. | `dt`. Older weekly-format years: the start of that week. | Participation, roles, vacated opportunity |
| Weekly rosters (`load_rosters_weekly`) | player-week | 2002→ | Daily during the season | The start of that week | Joining, team membership |
| Rosters, players (`load_rosters`, `load_players`) | player | 1920→ | Daily | Snapshot date | Bio, age, position |
| Id map (`load_ff_playerids`) | player | — | Regularly | — | Joining all non-nflverse sources |

### Health, people and the offseason
| Source (loader) | Level of detail | Years | Updates | Known-at rule | Feeds |
|---|---|---|---|---|---|
| Injuries (`load_injuries`) | player-week (game status plus Wed–Fri practice status) | 2009→ | During each game week | **Noon ET the day before kickoff.** The final report comes 1–2 days before the game. No timestamp column. | Injury & fatigue, vacated opportunity |
| Combine (`load_combine`) | player | 2000→ | After the combine (March) | The day after that year's combine ends | Prospects |
| Draft picks (`load_draft_picks`) | player | 1980→ | After the draft (late April) | The day of the pick | Prospects, aging, dynasty |
| Contracts (`load_contracts`, OverTheCap) | player-contract | Signing years through 2026. Only the year signed, no exact date. | Regularly | Use our snapshot date, because the year signed alone is too coarse for point-in-time | Contract & motivation (parked) |
| Trades (`load_trades`) | transaction | 2002→ | When trades happen | `trade_date` | Timeline, vacated opportunity |
| FantasyPros ECR (`load_ff_rankings`) | player-ranking | `type="all"`: archived history, Dec 2019→. `"draft"` and `"week"`: the current snapshot only. | Weekly in season | `scrape_date` | Crowd expert, ECR benchmark |

> ⚠️ **Participation is post-season only. This is why Context and VOE each come as two experts** (`context-live` / `context-retro`, `voe-live` / `voe-retro`; rule m).
> Play-level fields like routes run, coverage type, pressure and time to throw arrive only after the season ends. The old Context and VOE models were built on them. A model *trained* on these fields can't be *fed* them for live, mid-season predictions. That mismatch (train/serve skew) silently breaks a model in production.
> So every expert declares a `cadence` in the registry:
> - **in_season:** uses only fields available live: play-by-play, FTN charting (with its lag), daily depth charts, weekly snap counts, Next Gen Stats and PFR advanced stats.
> - **retrospective:** updated between seasons, and may use participation. Useful for player value, archetypes and next-season priors.
>
> Where an idea needs both, it becomes two experts.

## Tier 2 to 4: other free sources

| Source | Tier | What | Status | Known-at rule | Feeds |
|---|---|---|---|---|---|
| **ESPN odds and props** | 2 | Game lines (open/close, with prices) and player props (open/current lines, no prices) | ✅ **Collecting.** History 2022→ (deep from 2024). See [the exploration](../projects/odds-collection/EXPLORATION.md). | History: open and close only, never "the line at time t". Live: our fetch time. | Market, props board, closing line value |
| **The Odds API** | 3 | Game lines and props **with prices**, incl. FanDuel and anytime TD | ✅ **Collecting** since 2026-10-28 (free tier, ~410 of 500 credits/month) | Our fetch time | Props board, TD props, market |
| **Open-Meteo** | 3 | Weather forecasts and history, no key | ○ To explore | Forecast: issue time. History: kickoff. | Environment (upcoming games) |
| **Sleeper API** | 2 | Trending adds and drops, players | ○ To explore | Fetch time (snapshots) | Crowd expert, case studies |
| **Fantasy Football Calculator** | 2 | ADP by format | ○ To explore | Fetch time (snapshots) | Crowd expert, ADP benchmark |
| **College Football Data** | 3 | College stats, recruiting, draft | ○ Key in `.env` | Game date (college stats). Draft data at the draft. | Prospects |
| **RSS feeds** (team sites, ESPN, NFL.com, Google News) | 4 | News articles | ○ To build | Publish time | News & off-field |
| **Reddit** (free app registration) | 4 | Posts and comments | ○ CEO to register the app | Post time | News & sentiment |

Collected data (lines, snapshots) can't be re-downloaded, so it lives in the private `jackdepree/pcf-data` repo (rule g). Everything else is cached locally in `pcf/data/` and can be rebuilt.

### Research-only exception: Big Data Bowl
The NFL's free full-tracking samples: every player's position 10 times a second, for a few weeks of a season. **A one-time manual download from Kaggle, for case studies only** (e.g. exploring context, roles, separation). Never a dependency of the weekly pipeline.

## Deliberately not used

| Source | Why not |
|---|---|
| PFF exports | Paid, and redistributing them breaks their terms |
| Scraping Pro Football Reference | Blocks scrapers and limits request rates. nflverse already serves much of PFR's advanced data. |
| X / Twitter | The API is paid |
| Sportsbooks' internal endpoints | The most terms-of-service-sensitive option. ESPN and The Odds API cover what we need. |
| Any recurring manual download | Can't be automated. See *Manual downloads*. |

## Known gaps

| Gap | What it limits | Workaround |
|---|---|---|
| Film grades | Player grading | Statistical grades: VOE (value over expected) |
| Full player tracking | Separation, coverage and route detail | Weekly Next Gen Stats aggregates. Big Data Bowl for research. |
| **Live play-level participation** | Context, VOE, roles and coverage, in-season | See the callout above: live-only fields, or retrospective experts |
| Detailed practice reports (beyond the injury report) | Injury & fatigue | Practice status from `load_injuries`, and news |
| Prop lines, 2025 weeks 14–22 | Prop backtests for those weeks | None free. Exclude those weeks. |
| Prop **prices** before 2026-10-28 | Prop edge sizes in backtests | Assume −110 for over/under. Real prices from The Odds API going forward. |
| Touchdown-scorer odds before 2026-10-28 | TD-prop backtests | The Odds API from now on |
| Exact line timing in ESPN history | "Line at time t" features | Use opening and closing lines only |
