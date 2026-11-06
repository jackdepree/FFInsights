# 0015: Injury reports without a date are known when they reach nflverse's file

**Date:** 2026-11-06 · **Decided by:** Claude (technical call, while building `prediction-ledger`; brief decision 3)

**Decision:** A report with no `date_modified` (2009, 2025→) is known at noon Eastern the day before a Saturday, Sunday or Monday game, at noon on the day of any other, or an hour before an earlier kickoff. Reports that have `date_modified` keep it. Every live run also runs an input check (`pcf.validation.inputs`), since no leakage check can catch data that never arrives.

**Why:** the old rule, kickoff − 12 hours, hid every report from the Saturday run from 2025 on. In a 2024 test that made the range score (pinball) 17% worse (prediction-ledger#F1, #F2). A game's final report comes on a regular day, and nflverse's file updates once a day, between 9 and 12 Eastern (#F8, #F9). The rule is too early for 0.85% of 2021–2024 reports, and it restores reports to 6.9% of 2026's rows, against 7.3–9.9% in 2022–2024. Too-early rows can only affect rebuilt rows (the replay and training), because a live pull holds only what's already published.

**Alternatives:**
- First seen in our own pull (what the brief first proposed): our snapshot runs hours after nflverse's update, on a schedule GitHub delays. It first held Friday's reports at 13:31 Eastern on Saturday, so it would hide them from the noon run even though the file had them at 9:34. It stays as proof in each run's record.
- Noon the day before every game: too early for 6–7% of reports, mostly Thursday games, whose report comes the afternoon before (timeline#F4).
- One lead time before every kickoff: no single number fits. Sunday night's game needs at least 32 hours to be seen at Saturday noon, which would show Thursday night's report at Wednesday noon, before it's issued.

**Revisit if:** the input check flags the injury inputs live, nflverse changes its update time, or the file gets its `date_modified` back.
