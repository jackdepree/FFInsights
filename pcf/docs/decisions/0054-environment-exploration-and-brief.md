# 0054: environment's exploration and brief

**Date:** 2026-11-27 · **Decided by:** Claude (technical calls, for the CEO's veto) · **Asked by:** the CEO, 2026-11-27: "Use all three methods to test please" and "Brief should be around totals and the play mix and the wind bet." · **Detail:** `projects/environment/EXPLORATION.md`, `projects/environment/BRIEF.md`

**The calls:**
1. **The observed weather stands in for the forecast before 2022** (rule c). Open-Meteo's archive of issued forecasts starts in 2022. On 2022-2024 the two agree for wind (r 0.85) and temperature (r 0.99), not rain (r 0.46). Every live forecast and the vault use the forecast only.
2. **A game's weather is the mean of the three hours from kickoff (UTC)** at the stadium's coordinates (`explore/stadiums.csv`, 62 stadiums).
3. **Dome and closed-roof games get calm, dry, 70°F weather,** with the dome flag on, so the weather terms read outdoor games only. Retractable roofs follow the schedule's `roof`.
4. **The conditions are league-wide:** no team, QB or role sensitivities in the build, because method 3 and H124-H125 found them to be noise. The CEO's H128 (a matchup by roles or schemes) is tested as its own rung and ships only if it beats the rung below clearly.
5. **Out of the build's scope:** pace's clock (plays a game, seconds a play), sacks, interceptions, field goals (`kicker-dst` keeps wind by distance) and travel (F136). None moved in the exploration.
6. **The wind bet is scored on the squared error beside the closing total, plus the under's record against 52.4%,** as discovery. There is no closing line value without an earlier line.
7. **Live forecasts:** a small Open-Meteo step in the collector saves each game's forecast the morning of the game into `pcf-data`. It's a separate commit for the CEO to see, because it touches the GitHub workflow.
