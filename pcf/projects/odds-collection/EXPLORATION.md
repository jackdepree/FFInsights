# Exploration: betting-line collection (`odds-collection`)

**Date:** 2026-10-28 · **Time box:** one session · **Verdict: GO**

## The question

Can we collect game lines and player-prop lines for free, without scraping, well enough to test PCF's predictions against the market? Can we do it starting now, mid-season, so nothing more is lost?

## The answer in one paragraph

Yes, and better than expected.
- **Historical game lines** are already in nflverse: spreads and totals from 1999, moneylines from 2006.
- **Historical player-prop lines** are free through ESPN's public (undocumented) API, going back to 2024 in depth. ESPN also keeps props for completed 2026 games, so **this season isn't lost: we can backfill it.**
- **The gaps:** ESPN gives the prop *line* but not the *price*, and it has no touchdown-scorer odds. The Odds API's free tier can fill both for upcoming games, within its monthly credit limit.

## Sources tested

| Source | What it has | History | Cost / access | Verdict |
|---|---|---|---|---|
| **nflverse schedules** (`load_schedules`) | Spread, total, moneylines and their prices, one per game | Spreads/totals **1999→**, moneylines **2006→**. Upcoming 2026 games are already filled. | Free, no key | ✅ The backbone for game lines |
| **ESPN core API**: game odds | Spread, total and moneyline per game, by book | Many books in 2022; one book (ESPN BET, then DraftKings) since | Free, no key, undocumented | ✅ For snapshots of line movement |
| **ESPN core API**: `propBets` | Player props, **opening and current line**, `lastUpdated` timestamp, ESPN athlete id | **2024–2025:** ESPN BET, about 700–1,100 props per game. **2026:** DraftKings, about 700 per completed game, about 1,400 per upcoming game. **2022–23:** sparse (about 20–45 per game, several books). **2021 and earlier:** none. | Free, no key, undocumented | ✅ The main prop source, plus backfill |
| **The Odds API**, free "Starter" tier | Game lines and 30+ NFL prop markets (incl. anytime TD) **with prices**, many US books incl. FanDuel | **Historical endpoints are paid-only** | Free: 500 credits/month, needs an API key | ✅ Fills prices and TD odds for upcoming games |
| Sportsbooks' own JSON (DraftKings, FanDuel) | Everything | Live only | Not tested | ⏸ Not needed. These are the most terms-of-service-sensitive option. |

### What a prop record looks like (ESPN)
- **Fields:** player (ESPN athlete id), market (e.g. "Total Receiving Yards (incl. overtime)"), book, `open` line, `current` line, `lastUpdated`.
- **Markets seen:** passing, rushing and receiving yards; receptions; carries; completions; attempts; passing TDs and interceptions; longest reception, rush and completion; combined yards; kicking points, field goals and extra points.
- **ID match:** ESPN athlete ids matched nflverse player ids (`load_ff_playerids`) for **43 of 43** players tested.

### The Odds API budget on the free tier
- A prop call costs (markets returned) × (regions), per game. Empty responses cost nothing.
- **One weekly snapshot:** anytime TD plus 4 core props (receptions, receiving, rushing and passing yards) is 5 markets × 1 region × ~15 games ≈ **75 credits**.
- **Per month:** that's about 325 credits for props, plus game-line snapshots at 3 credits each. **It fits under 500, with room to spare.**

## Assumptions and limitations

1. **No prices on ESPN props.**
   - For over/under props we'd assume standard −110 on both sides.
   - Real prices range from about −130 to +100, so edge estimates from ESPN-only lines are *approximate*.
   - The Odds API snapshots give the real prices going forward.
2. **No touchdown-scorer odds in ESPN history.** TD-scorer props can only be backtested from the day we start The Odds API snapshots.
3. **"Current" on a completed game probably means the final pre-game line**, i.e. the closing line. Not yet verified. The brief should check `lastUpdated` against kickoff time.
4. **The book changes by season:** ESPN BET in 2024–25, DraftKings in 2026. Prop lines across books are close but not identical, so "book" has to be a column, never assumed.
5. **The ESPN API is unofficial.**
   - It could change or disappear at any time, which is the main reason to backfill *now*.
   - We save the raw responses, so a change in the API never costs us data already collected.
6. **When nflverse game lines were taken** (opening vs. closing) isn't documented. We need to verify that before using them as the "closing line" for closing line value.
7. **Terms of service.** Keyless, infrequent requests for personal research are low-risk. *Republishing* collected lines on a public PCF site is a separate question for Phase 5.
8. **Leakage (rule c).** Every line is stored with its `known_at` time (`lastUpdated` or our fetch time). Features may only use lines known before the prediction was made.

## Did we find signal?

This is a data-collection project, so "signal" means: does usable data exist? Yes. It's deep for 2024 onward and continuous through this week. **Go.**

## Proposed shape of the build (for the brief)

1. **Backfill now:** ESPN props and game odds for every game 2024–2026, plus the sparse 2022–23 data.
   - About 650 games and 1,300 requests, run politely (about one request per second, roughly 20–25 minutes).
   - Raw JSON is saved compressed and append-only, then parsed into one table.
2. **Weekly collector:** ESPN snapshots several times a week (e.g. Tuesday, Friday, Sunday morning) to capture line movement, plus one The Odds API snapshot (FanDuel and other books, with prices and anytime TD).
3. **One normalized lines table:** `known_at, source, book, game_id (nflverse), player_id (gsis), market (normalized), line, over_price, under_price, is_open`.
4. **Market-name mapping** between ESPN, The Odds API and our own stat names. For example, "Total Receiving Yards (incl. overtime)" maps to `player_reception_yds`, which maps to `receiving_yards`.

## Decisions made (2026-10-28)

1. **The Odds API key:** the CEO signed up. The key is in `pcf/.env` and goes in a GitHub Actions secret.
2. **Backfill:** run now, before the brief. Results are below.
3. **Collector:** runs on GitHub Actions 5 times a week (`.github/workflows/collect-odds.yml`) and commits to the **private `jackdepree/pcf-data` repo**. Collected lines are the one exception to rule g, because they can't be re-downloaded.

## Backfill results (2026-10-28)

**Raw data:** 1,264 game files, 13 MB compressed, in `pcf/data/raw/espn_odds/` (local, out of git). **Parsed tables:** 500,009 prop rows and 9,740 game-line rows in `pcf/data/interim/espn_odds/`.

| Season | Games with props | Props per game | Books | Markets | Players matched to nflverse |
|---|---|---|---|---|---|
| 2022 | 277 | ~108 | Caesars, MGM, DraftKings, SugarHouse | 6 | 98.5% |
| 2023 | 285 | ~98 | Caesars, MGM, DraftKings, PointsBet, SugarHouse | 7 | 97.3% |
| 2024 | 284 | ~561 | ESPN BET | 41 | 99.7% |
| 2025 | 198 | ~1,026 | ESPN BET, DraftKings | 79 | 99.9% |
| 2026 (wk 1–7) | 107 | ~676 | DraftKings | 77 | 99.9% |

Every row matched an nflverse `game_id`.

**What we learned:**
- **The "current" line on a completed game is a pre-game closing line, not an in-game line.** Tested on receiving, rushing and passing yards and receptions, for rows where the line moved.
  - "Current" was only **1–12% closer** to the actual result than "open". For example, 2025 receiving yards: open MAE 20.65, current MAE 20.24.
  - That's the size of improvement a closing line normally has over an opening line.
  - If in-game updates had leaked in, "current" would be dramatically more accurate.
  - We treat "current" as the closing line.
- **`lastUpdated` is *not* when the line was set.** On completed games it's mostly hours *after* kickoff (2025 median: about 6 hours after), which is when ESPN closed the market. For history, `open` and `current` have no exact timestamp. Features may use them only as "the opening line" and "the closing line", never as "the line at time t".
- **Gap: 2025 weeks 14–22 have no props** (about 90 games), almost certainly lost when ESPN switched from ESPN BET to DraftKings in December 2025. It can't be recovered for free.
- **ESPN game lines have open *and* close, with prices.**
  - nflverse's `spread_line` matches ESPN's *closing* spread in 45–84% of games, and the opening spread in only 11–30%.
  - So nflverse is near-closing but not exactly closing.
  - For closing line value, use ESPN close (2023 onward) and fall back to nflverse.
- **The 2022 game-line fields parse differently.** Open values are missing and close values never match nflverse. This needs a parser fix before 2022 game lines are used.
- **The Odds API free tier (tested live):** props **with prices** from FanDuel, DraftKings, BetMGM, BetRivers, Bovada and BetOnline, for all five markets requested, at 5 credits per game as estimated.

## Next step

The executive **brief**, written together. It covers: the normalized lines table, market-name mapping, how `known_at` is defined for history vs. live snapshots, the 2022 parser fix, and promoting these scripts into the package.

## Sources

- [The Odds API: plans](https://the-odds-api.com/) · [API docs (credit costs, historical is paid-only)](https://the-odds-api.com/liveapi/guides/v4/) · [Market keys](https://the-odds-api.com/sports-odds-data/betting-markets.html)
- [Community list of ESPN API endpoints](https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c). The `propBets` route was confirmed by direct testing.
- Endpoints tested:
  - `site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=<season>&seasontype=2&week=<n>`
  - `sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/<id>/competitions/<id>/odds`
  - `…/odds/<provider_id>/propBets?limit=1000&page=<n>`. Provider ids: 100 = DraftKings (2026), 58 = ESPN BET (2024–25).
