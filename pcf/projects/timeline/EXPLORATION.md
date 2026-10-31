# Exploration: NFL timeline and known-at timestamps (`timeline`)

> A light exploration (infrastructure project). It asks three things: can we get a reliable kickoff time for every game, can a season be cut into clean weeks, and which offseason dates exist in our free data. It also checks two known-at rules from `DATA_SOURCES.md` against the timestamps the data carries.
> Run on 2026-10-31 with [`explore/profile_inputs.py`](explore/profile_inputs.py) on our raw nflverse copy (`data-layer`).

**Verdict: GO.** Kickoff times and week boundaries are clean in the schedules file for 2000–2026. Two things need work. The offseason has almost no dates in nflverse (F6), so its calendar needs another source. And the injury known-at rule is too early for about 6% of recent rows (F4), which is a leak.

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **Schedules' `gametime` is US Eastern time, for every game, including London, Germany, Mexico and Brazil.** Checked against the first play's UTC clock in play-by-play for 2011–2025 (4,096 games): the first play comes a median 2 minutes after the scheduled kickoff, and 99% within 16 minutes. 1999 has no `gametime` at all (259 games); 2000–2026 have it for every game. | strong |
| F2 | **The actual start can be hours late, and play-by-play's clock is sometimes wrong.** Weather delays pushed four first plays over an hour late (2016 TB at ARI: 3 hours). Seven games have a first play hours *before* kickoff, which is impossible: London games in 2017–18 are off by about 12 hours, and two 2011 games by 3 and 7. So the scheduled kickoff is the one to use. Known before the game, it's also the only one a live prediction can use. | strong |
| F3 | **Weeks never overlap.** Every week's games fall within 5 days, except 2020 week 12 (6 days: the postponed Ravens–Steelers game was on a Wednesday). There are at least 2 days between one week's last game and the next week's first. So each week can be the span from the day after the previous week's last game to its own last game. Before the Super Bowl there's a 13–14 day gap (the bye week). The 2026 schedule has the regular season only (weeks 1–18, ending 2027-01-10); playoff games appear when they're set. | strong |
| F4 | **The injury rule "noon ET the day before kickoff" is too early for 6–7% of rows in 2021–2024.** Their `date_modified` is later than that, though still before kickoff: 82% of them are Thursday games, whose final report comes out Wednesday afternoon (27–29 hours before kickoff). Before 2021, under 0.4% of rows break it. Across 2010–2024, 0.35% of reports are modified within 24 hours of kickoff, and 0.03% after it. `date_modified` is missing in 2009 and from 2025 (`package-scaffold#F5`). | strong |
| F5 | **2025+ depth-chart snapshots are taken once a day, mostly at 06:00–08:00 UTC** (the middle of the night in Eastern time), a median 23 hours apart. The longest gap is 8 days (March 2026). So every Sunday game has a snapshot from the morning of the game, before kickoff. The start-of-game-day cutoff `cleaning-port` uses until kickoff is available misses it. | strong |
| F6 | **The offseason has almost no dates in nflverse.** Draft picks and the combine have a year only. Contracts have the year signed. Nothing gives the start of the league year (free agency), the draft days, camp, or roster cuts. Trades are the exception: 1,675 trades from March 2002, each with a `trade_date`. Each year's two busiest days for trading that year's picks fall on the draft (2024: April 26–27; 2025: April 25–26), but the draft's first day is usually missing, so the trades give the draft only roughly. | strong |
| F7 | **The trades file stops in April 2026.** Its last trade is 2026-04-17, and nflverse last uploaded it on 2026-05-19. No 2026 in-season trade is in it. It works as history; for this season, team changes have to come from weekly rosters or other sources. | strong |
| F8 | **Weekly rosters cover weeks 1–22 of each season**, and 2026 weeks 1–8 so far. There are no offseason weeks. The known-at rule "the start of that week" needs a week start date, which the week windows (F3) give. | strong |
| F9 | **The ECR archive has 371 scrapes**, from 2019-12-27 to 2026-10-30. Each `scrape_date` is a ready-made known-at. | strong |

## What it means for the brief
- **Games and weeks come straight from schedules** (F1, F3). Kickoff is `gameday` plus `gametime` in Eastern time, converted to UTC. The 1999 games need a stand-in time.
- **Each known-at rule in `DATA_SOURCES.md` becomes a function**, with a test that checks it against the timestamps the data carries where it has any. The injury rule needs fixing (F4).
- **`cleaning-port`'s depth-chart cutoff moves to kickoff** (F5).
- **The offseason calendar needs a decision** (F6): where its dates come from.

## Next step
The [brief](BRIEF.md).
