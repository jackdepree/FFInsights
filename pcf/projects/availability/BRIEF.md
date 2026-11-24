# Availability: who plays, and for how many games

> **Status:** kickoff, 2026-11-23 (the CEO: "Ok, let's start the availability expert"). Waiting for the CEO's hunches. Nothing has been tested for this project yet.

## Why now

- **The yardstick batch (I60, 2026-11-23):** over the rest of a season, knowing the share of games a player goes on to play would remove 70.2% of the crude forecast's error for passing yards, 26.8% for rushing, 23.8% for receiving and 4.2% for team yards. A crude games-played forecast (games so far, shrunk to last season's rate, plus this week's report) gets 1.3% for receivers and nothing for QBs and backs. It's the biggest gap between hindsight and forecast we've measured.
- **Teams (I115):** a starters' games-played forecast adds +2.84% to team yards over the rest of the season beside Elo. That's an Elo repair, not a stand-alone signal yet.
- **The line's late news (I114's spot-check):** the kickoff line adds about 5.5% to team yards next game beyond all our team inputs, and most of its lead over the opener sits in games where the line moved 2.5+ points: injuries, weather, sharp money.

## The usual way

Teams' medical and sports-science staff forecast availability from workload tracking (GPS load, the acute-to-chronic workload ratio), screening and medical history, and none of that is public. Public analysts and fantasy and betting desks split it in two: **will he get hurt** (a rate per game or per snap by position and age, with past injuries as a flag), and **once he's hurt, how long is he out** (recovery times by injury type, read through the injury report, practice participation and beat reporters). The first part is usually found to be close to random beyond position, age and volume, so most of the skill sits in the second. For teams, the standard public tally is Football Outsiders' adjusted games lost, which weights starters more than backups.

## Two analogies

- **Insurance: frequency and severity.** An insurer prices a policy as how often claims come (frequency) times how big each one is (severity), and models the two apart because different things drive each. Its credibility theory then says how far to trust one driver's own record against the class average. That's the "injury-prone" question in numbers: how many past injuries before a player's own history outweighs his position and age?
- **Reliability engineering: the bathtub curve and repairs.** Machines fail often when new, rarely in mid-life, and more as they wear out, and a part that was just repaired fails again more often soon after. For players, the curve maps to rookies, the prime and age, and the repair to re-injury in the weeks after a return (the hamstring that comes back).

## What we already have

- **Participation's `active`:** the chance of being active next game. AUC 0.932 and close to calibrated (participation#F12), but it overstates Out and Doubtful players about twofold, and Questionable players are its weakest (slope 0.70, F27). Its next-3 and rest-of-season shares have no spike for a window that collapses through injury or release, so their q10 is too high (F14), and most misses there are a few games lost, not the whole window (F24).
- **Free data:**
  - injury reports from 2009, with Wednesday to Friday practice status and the body part (`report_primary_injury`, `practice_primary_injury`);
  - real game statuses from 2019, and the game-day inactive list (known an hour before kickoff, so never an input);
  - weekly rosters' status;
  - snap counts and depth charts;
  - participation's who-was-on-the-field, from 2016.
- **Not free:** workload tracking, medical detail, and most reporting. News is the weakest free source.

## The backlog that fits (W4's read)

- **I60** (graduated in the batch: the room is real, and the crude forecast of it is weak) and **I115** (inside Elo's next build).
- **I51,** a probable starting QB from the practice lines, and **I49,** swap pairs inheriting an absent player's snaps.
- **I9,** movers over-projected for snaps. Who absorbs a missing player's chances belongs to `vacated-opportunity`.
- **Fatigue (bucket F): I29, I30, I50.** The registry's `injury-fatigue` idea covers workload, risk tiers and recovery, so it overlaps this project.

## The CEO's hunches (word for word, before any test)

*To come.*
