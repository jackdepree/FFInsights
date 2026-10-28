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

## Open questions for the CEO

1. **The Odds API key.** You'd need to sign up for the free tier yourself (I can't create accounts). Then you'd put the key in a local config file that stays out of git. Or should we skip it for now and accept no prices and no TD odds?
2. **Backfill before the brief?** The ESPN API is unofficial and could vanish. I recommend running the backfill right away as exploration code, saving to a local data folder that's out of git, and writing the brief alongside it.
3. **Where the collector runs.** Snapshots several times a week need a machine that's on. That favors GitHub Actions for this one piece, even if everything else runs on your PC. It's an `ARCHITECTURE.md` question, but this project forces it early.

## Sources

- [The Odds API: plans](https://the-odds-api.com/) · [API docs (credit costs, historical is paid-only)](https://the-odds-api.com/liveapi/guides/v4/) · [Market keys](https://the-odds-api.com/sports-odds-data/betting-markets.html)
- [Community list of ESPN API endpoints](https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c). The `propBets` route was confirmed by direct testing.
- Endpoints tested:
  - `site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=<season>&seasontype=2&week=<n>`
  - `sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/<id>/competitions/<id>/odds`
  - `…/odds/<provider_id>/propBets?limit=1000&page=<n>`. Provider ids: 100 = DraftKings (2026), 58 = ESPN BET (2024–25).
