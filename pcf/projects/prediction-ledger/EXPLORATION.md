# Exploration: prediction ledger (`prediction-ledger`)

**Date:** 2026-11-06 · **Time box:** one session · **Verdict: GO, with one blocker to fix first** · **Script:** [`explore/first_look.py`](explore/first_look.py)

## The question

Can PCF record real forecasts before kickoff with no weekly work from the CEO? What would stop those forecasts matching the model we validated?

## The answer in one paragraph

The forecast itself works today and takes about 5 minutes. But **a live forecast wouldn't see the injury report.** Since 2025 nflverse's injury file has no modified date, so our rule treats a report as known 12 hours before kickoff, which is after the Saturday noon run. The model would treat every player as healthy. In a 2024 test that makes the range score (pinball) 17% worse, and players on the report go from a forecast of 20.0% to 46.5%, when they actually played 18.0%. This has to be fixed before anything counts. Separately, **GitHub has locked the account over a billing issue, so both collectors have stopped.**

## What we measured

| Check | Result |
|---|---|
| Forecast this week's games (week 9, as of 2026-11-06) | Works: 466 rows across 15 games, none missing. Thursday's game comes from the Wednesday run, the rest from Saturday's, as `trees_week` declares |
| Do the numbers look right? | Yes, before the fix: top starting QBs 95.8–96.7%, top WRs 85.8–89.6% |
| Time for one model | Refresh 20 s, 2026 tables 2 s, features 249 s, fit and predict 12 s: about 5 minutes |
| Reading `pcf-data` from this PC | Works. A push dry run reached the server, but no real write has been tried, and the PC has no copy of the repo yet |
| A market line for a snap forecast | None exists. Lines matter once a product joins the ledger |

## Findings

**1. Blocker: live forecasts can't see the injury report.** At the Saturday moment, weeks 6–8, rows with a report status:

| Season | Rows | With a report |
|---|---|---|
| 2022 | 1,380 | 137 (9.9%) |
| 2023 | 1,376 | 101 (7.3%) |
| 2024 | 1,423 | 111 (7.8%) |
| 2025 | 1,365 | **0** |
| 2026 | 1,357 | **0** |

A report in 2024 was known a median of 46.9 hours before kickoff. In 2026 it's exactly 12.0 for every row, because that's the fallback rule. The rule was written so reports wouldn't be counted too early (timeline#F4), and for these seasons it hides them completely.

**2. What that costs.** One test on 2024: trained with reports, then forecast with `report` and `practice` blanked, as live would be.

| Rows | Range score ×100 | Average miss ×100 | Said | Was |
|---|---|---|---|---|
| All (8,997): with report → hidden | 3.435 → 4.020 | 11.51 → 12.98 | 37.9 → 39.8 | 37.8 |
| On the report (627): with report → hidden | 3.217 → 11.657 | 11.96 → 33.12 | 20.0 → 46.5 | 18.0 |

This probably understates it, because the live gap also affects teammates' absences (finding 3), which this test left in place. It's one season.

**3. Only the injury inputs are affected.** Of `trees_week`'s 30 inputs, comparing how often each is non-zero in 2024 and 2026, five stand out, and all come from the injury report: `no_practice` (81.8% → 100%), `mates_out` (11.4% → 0), `mates_out_share` (10.8% → 0), `practice` (8.2% → 0), `report` (7.8% → 0). The other 25 are within 4.3 points. **No current check catches this:** the leakage checks catch data seen too early, not data that never arrives. The ledger should run this comparison every time.

**4. The report does seem to arrive in time.** Our first snapshot, Saturday 2026-10-31 at 13:31 Eastern, already held week 8's statuses: 46 Out, 73 Questionable, 2 Doubtful. That's 90 minutes after the noon run, so it doesn't prove noon. The first live Saturday will.

**5. This week's roster rows can land late.** Snapshots on Tuesday 15:00 and Wednesday 15:19 Eastern had no week 9 rows in the weekly roster file. They were there by Friday 11:13 Eastern. Our rule says Tuesday at midnight. The Wednesday run for Thursday's game may find no rows, though Saturday's should be safe. Last week's list could stand in: 90–91% of a week's rows (2024–2026) were on that team's list the week before.

**6. Collectors have stopped: the account is locked.** The `snapshot-nflverse` run on 2026-11-05 and the `collect-odds` run on 2026-11-06 both failed before starting, with GitHub's message: "The job was not started because your account is locked due to a billing issue." Pushing code still works. Thursday's pre-game odds snapshot is lost, and daily nflverse snapshots are being missed. Only the CEO can fix this. Later on 2026-11-06: another `snapshot-nflverse` run failed the same way, and the CEO reports GitHub says a coupon for their plan has expired. Our workflows run in the public FFInsights repo, where standard runners are free, so they shouldn't need a paid plan. Each successful run took about 1 minute, 2.9 at most.

**7. Scheduled GitHub runs start hours late.** The last 6 `collect-odds` runs started 3h51 to 6h10 after their scheduled time. Monday's "before Monday Night Football" run started at 02:10 UTC on 2026-11-03, 55 minutes after kickoff, and Sunday's started 43 minutes before the 1 pm games. `snapshot-nflverse` ran 4.5 to 9.2 hours late. Forecasts on the PC's Task Scheduler avoid this, which is one more reason to run them there. The odds schedule itself needs moving earlier, as a separate fix.

**8. nflverse's injury file updates once a day, in the morning (added 2026-11-06).** The 7 update times we've recorded fall between 9:14 and 11:59 Eastern, and on Friday 2026-11-06 the file was still unchanged at 17:45. So a report issued in the afternoon isn't in the file until the next morning. Saturday's file at 9:34 held Friday's reports for Sunday's games, and Sunday's file added the 11 statuses for Monday's game. One update, at 11:59, came close to the noon run, and 7 is a small sample. **Saturday 2026-11-07:** the file was updated at 8:53 Eastern and already held week 9's 141 statuses (63 Out, 72 Questionable, 6 Doubtful), three hours before the noon run.

**9. A report's timing is regular enough for a rule (added 2026-11-06).** On 2021–2024's 23,081 reports with real times, the final version appears two days before a Sunday (92%), Monday (91%) or Saturday game (92%), and the day before a Thursday (93%), Friday (93%) or Wednesday game (93%), at a median of about 15:15 Eastern. So the rule is: noon the day before a Saturday, Sunday or Monday game, noon on the day of any other, or an hour before an earlier kickoff.

| Rule | Too early | Reports at the Saturday run, 2026 |
|---|---|---|
| Kickoff − 12 hours (old) | 0.06% (2010–2024) | 0 of 1,357 rows |
| Noon the day before every game (older) | 6–7% (2021–2024) | not measured |
| **This rule** | **0.85%** (2021–2024; 0.53–1.14 by season; 1.83% of Sunday rows with a status) | **93 of 1,357 rows (6.9%)** |

Rows with a report at each season's moments, weeks 6–8: 2022 9.9%, 2023 7.3%, 2024 7.8%, 2025 7.5%, 2026 6.9%. The input check now flags 0 of 30 inputs, against the 5 in finding 3. Week 8 of 2026 agrees: Sunday's statuses were in the file updated at 9:34 on Saturday, and Monday's in the one updated at 9:14 on Sunday, each before the rule's noon. Thursday's has no such record, because our logs begin after it. Too-early rows matter only for rebuilt rows (the replay and training), since a live pull can't hold anything unpublished. Scripts: [`explore/injury_timing.py`](explore/injury_timing.py), [`explore/injury_fix_check.py`](explore/injury_fix_check.py).

**10. Thursday games still can't see their final report at the Wednesday run (added 2026-11-06).** In the backtest's real times, 76% of Thursday games' final reports were out by Wednesday 16:00. But the file doesn't update until Thursday morning: Wednesday 2026-11-04's file held 28 week-9 rows and no statuses. So the live Wednesday run sees no final report for Thursday's game, while the backtest mostly does. That's one game a week. Moving the run to Thursday noon would fix it, and it's a decision for the CEO, since it changes every backtest's Thursday rows. **The CEO chose the move on 2026-11-06** (finding 11, [decision 0016](../../docs/decisions/0016-thursday-run.md)).

**11. Moving the run to Thursday noon works, and it helps (added 2026-11-06).** On 2021–2024's Thursday games, 75.2% of reports with a status were known by Wednesday 16:00 in real times, and 99.7% by Thursday noon. Thursday games' rows with a report, Wednesday 16:00 then Thursday noon: 2022 5.3% → 9.3%, 2023 8.4% → 10.7%, 2024 6.0% → 6.4%, 2025 0 → 9.3%, 2026 0 → 3.1%. 2026 is low because its Thursday games have few statuses in the file at all (9 of 287 skill-position rows, all of them seen), and it's only 9 games.

On 2016–2024, `trees_week`'s Thursday rows improve: range score ×100 3.392 → 3.297 (−0.095, −0.143 to −0.051; 5,043 rows). Average miss goes from 11.26 to 11.02 points. For Thursday players with a report status (467 rows), the forecast goes from 21.7 to 18.6 against 17.7 played, and the average miss from 13.40 to 10.71. Other champions and the costs are in [decision 0016](../../docs/decisions/0016-thursday-run.md). This week's roster rows at Thursday noon are unproven: none on Wednesday at 15:19, there by Friday at 11:13, and Thursday's snapshot failed because of the account lock.

## Assumptions and limits

- Week 9 is a single week, and these numbers come from local files, not a scheduled run.
- Whether Windows wakes this PC and runs on time is untested.
- Runs happen only if the CEO stays logged in to Windows, because we won't store a Windows password. A locked screen is fine.
- Smart App Control blocked pandas once before. If it blocks a scheduled run, we report it and don't work around it.

## Go or no-go

**Go.** It's cheap, the forecast path works, and live weeks are the only honest test left for `trees_week`. The injury-report fix comes first, or the ledger would record a worse model than the one we validated. It would also flag that model for a problem in our own rule.
