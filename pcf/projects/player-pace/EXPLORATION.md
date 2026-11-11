# Exploration: Player pace and play-calling (`player-pace`, `player-pace-retro`)

> Do players carry their own pace and pass rate over expected, and do the CEO's hunches H26–H31 hold? Run 2026-11-11 on regular seasons 2016–2024 for anything that needs who was on the field on each play (participation), and 2002–2024 for starting QBs (known in season). Measures are pace's own (`play.pace`: PCF's pass rate over expected, PROE, and pace over expected, on every snap). The 2025 vault isn't read. Scripts and their full output: [`explore/`](explore/).

**Verdict (2026-11-11): GO, for both experts.** Players carry a plus or minus on pass rate that repeats week to week and season to season, follows tight ends and receivers to new teams, and still holds within each personnel grouping. It reads like football: fullbacks and blocking tight ends sit at one end, receiving backs and slot corners at the other. The in-season version (games a QB started against games he didn't) repeats season to season for QBs. Pace is mostly the team's: little of it follows a player.

| Hunch | Verdict | Size |
|---|---|---|
| H26 find the conditions where player rates don't repeat | **held** | Found: a new team, a new coach (QB pass rate), part-time players, and defenders' pace. A QB's on-field PROE repeats at 0.38 with the same team and coach, 0.07 with a new coach, −0.06 at a new team |
| H27 players carry their rates to a new team | **unclear** (mixed) | QBs carry some pace (0.21 of it, 90% 0.10 to 0.34; the team keeps 0.44), not clearly pass rate (0.10, −0.04 to 0.25). Tight ends and receivers carry their pass-rate plus-minus (r 0.54 and 0.31) |
| H28 players carry a plus or minus against their team | **held** for pass rate, small for pace | Player-season plus-minus sd 7.7–9.5 points of PROE for backs, receivers and tight ends; it survives taking each personnel grouping's average out |
| H29 that plus or minus repeats | **held** for pass rate | Week to week 0.42–0.62 and season to season 0.38–0.56 (backs, receivers, tight ends). Pace: week 0.06–0.20, season 0.02–0.08. In season, QBs' with-or-without repeats season to season (PROE 0.14, pace 0.26) |
| H30 pace or pass rate tracks age by position | **held**, small, for pass rate | Within a coach's stint: a rookie QB's season −2.5 points of PROE (90% −3.4 to −1.7); older receivers, linemen and tight ends +0.3 to +0.5 points per year. Pace: nothing clear |
| H31 defenders carry the same as offensive players | **failed** | The same kind of measure, at a third of the strength: defensive backs' pass-rate plus-minus 0.15 week to week, 0.12 season to season (receivers 0.42, 0.41); defenders' on-field pace is noise or close to it |

## Expectations, written before running
From the brief (2026-11-11, "Claude's assumptions, limits and expectations"): QBs consistent, others noise; QBs carry a little PROE, nobody carries pace; a real QB plus-minus, small elsewhere; a small rookie-QB lean to the run; defenders mostly fail.
- **Right:** the rookie-QB lean, defenders, QBs' pass rate staying with the team.
- **Wrong, and the main finding:** I expected skill players' plus-minus to be noise. It's the steadiest measure here.
- **Wrong the other way:** QBs carry pace more than pass rate.

## Data and definitions
- **Plays:** every regular-season pass or run snap, 2016–2024: 308,700. **Who was on the field:** `player_play.on_field` (participation, known the day after the Super Bowl), about 10.5 identified players per side per play.
- **Player-game rows:** 179,143 (player, side, team-game), with the plays he was on for and the team's rates on and off them. For a defender, the rates are what the offense did on those plays.
- **On-field rate:** the team's PROE or pace over expected on the plays he was on the field for.
- **Plus-minus by play (retrospective):** on-field minus off-field, same team-game, each game weighted by n_on × n_off / n_team (the weight a difference of two means earns). Only the plays he sat out measure it, so an every-snap starter barely has one.
- **Plus-minus by game (in season):** the team's rate in games he played at least half the snaps minus games he played under 10% or not at all, same team-season. Weekly snap counts are enough for it.
- **Consistency:** split-half (odd against even weeks) and one season against the next, as [`pcf.validation.consistency`](../../src/pcf/validation/consistency.py), with the weights above and Fisher 90% intervals. Groups: QB, RB (with fullbacks), WR, TE, OL, DL, LB, DB.
- **QB movers (H27):** starting QBs (`team_game.pregame.qb_id`, known in season) 2002–2024, 4+ starts per team-season, next season within 3, each season's league level taken out (pace#B2). 155 moved, about 7 a season; 562 stayed.

## Findings

**F1. A player's on-field rate is mostly his team's** ([output](explore/h26_h28_h29_h31.txt), first table).
- Every offensive group's on-field PROE and pace repeat week to week at 0.42–0.58 (all intervals above 0.38), because a player on the field for most snaps is measuring his team.
- Season to season it holds with the same team and coach (QB PROE 0.38, WR 0.38, TE 0.50) and falls apart when he changes teams (QB −0.06, RB 0.08, OL 0.04; WR 0.13). A new coach on the same team is enough to break a QB's PROE (0.07) but not his pace (0.35).
- The exception is tight ends' PROE, which carries to a new team (0.44, 90% from 0.34): see F3.

**F2. The conditions that make rates noise (H26).**
- **Changing teams:** on-field rates, all groups (F1).
- **A new coach:** a QB's pass rate (0.07).
- **Part-timers:** under 30% of the team's snaps, on-field pace drops to 0.27–0.32 week to week (linemen 0.10, interval reaching 0), against 0.72–0.82 for 70%+ players.
- **Defenders' pace:** on-field pace 0.01–0.09 week to week, about 0 season to season, for every defensive group.
- **Pace plus-minus, season to season:** 0.02–0.08 in every group but the in-season QB version (F5).

**F3. Players carry a pass-rate plus-minus, and it repeats (H28, H29)** ([output](explore/h26_h28_h29_h31.txt), third table).

| Group | Week r (90%) | Season r (90%) | Moved teams r (90%, pairs) | Player-season sd |
|---|---|---|---|---|
| TE | 0.62 (0.58–0.65) | 0.56 (0.52–0.60) | 0.54 (0.45–0.61, 210) | 9.5 points |
| RB | 0.49 (0.46–0.53) | 0.38 (0.34–0.43) | 0.23 (0.13–0.33, 242) | 8.3 |
| WR | 0.42 (0.39–0.46) | 0.41 (0.37–0.44) | 0.31 (0.24–0.39, 380) | 7.7 |
| QB | 0.13 (0.06–0.21) | 0.08 (0.00–0.16) | −0.01 (−0.16 to 0.13, 130) | 8.3 |
| OL | 0.09 (0.05–0.12) | 0.06 (0.02–0.10) | 0.01 (−0.07 to 0.09, 450) | 7.1 |

- The sd includes sampling noise; the repeat r says how much is real.
- **Pace plus-minus is weaker:** week to week 0.06–0.20 (QB 0.20, TE 0.15, RB 0.13), season to season 0.02–0.08.

**F4. It's the player's role, and the role isn't only the package (Claude's check)** ([personnel.py](explore/personnel.py), [output](explore/personnel.txt)).
- A coach chooses his personnel knowing the call, so a second tight end in heavy sets "runs" and a third-down back "passes". Taking each offense's season average per personnel grouping out of every play:
  - **Backs:** the plus-minus shrinks (week 0.30, season 0.19) and no longer follows them to a new team (0.00). A back's plus-minus is his package.
  - **Tight ends and receivers keep it:** week 0.46 and 0.29, season 0.45 and 0.35, new team 0.43 and 0.32. Within 12 personnel, which tight end is in still tells the call: a blocking tight end is a blocking tight end on any team.
- So "players carry a plus-minus" holds, but it's a tell (what the coach calls with them in), not the player making the team pass. Whether it's cause or tell doesn't matter for a forecast; it matters for how it's described.

**F5. In season, QBs carry a plus-minus by game** ([output](explore/h26_h28_h29_h31.txt), fourth table).
- With or without, by game, from snap counts: QBs' season-to-season r is 0.14 for PROE (0.03–0.25) and 0.26 for pace (0.15–0.36), from 206 pairs. Tight ends' pace 0.16 (0.05–0.27); backs' pace −0.14 (−0.25 to −0.03), the one negative; every other group about 0.
- Week to week every group shows 0.20–0.37, but that's inflated: a player who missed the second half of a season has his with-without gap set by whatever changed in the team over the season, in odd and even weeks alike. Season to season is the honest test.
- On average a backup QB doesn't change PROE (with minus without: −0.3 points, 436 team-seasons). The usual way cuts pass volume for a backup; if that's right, it comes through fewer plays or more trailing, which PCF's expected pass chance already knows, not through the play-caller passing less.

**F6. QBs carry pace more than pass rate (H27)** ([output](explore/h27_h30.txt)). Next season's rate in his starts against his old rate and the new team's rate the season before:

| | His rate carries | The team's carries | n |
|---|---|---|---|
| QB moved, PROE | 0.10 (−0.04 to 0.25) | 0.16 (0.03 to 0.30) | 155 |
| QB moved, pace | 0.21 (0.10 to 0.34) | 0.44 (0.18 to 0.67) | 155 |
| QB stayed, PROE | 0.27 (0.11 to 0.45) | 0.33 (0.13 to 0.52) | 562 |
| QB stayed, pace | 0.27 (0.05 to 0.48) | 0.42 (0.24 to 0.64) | 562 |

- Head coaches who moved straight to another head job: 31, too few to say (PROE 0.32, −0.11 to 0.70).
- The running QBs sit at the bottom of the play-level plus-minus (Fields −20 points, Jackson −13, Newton −11; [sanity](explore/sanity.txt)): designed QB runs count as runs. That's the part of a QB's pass rate most likely to travel, and the next thing to test.

**F7. Age goes with pass rate, a little (H30)** ([output](explore/h27_h30.txt)). Within a head coach's stint at a team, so his own habits are held fixed:
- **A rookie QB's season:** −2.5 points of PROE (90% −3.4 to −1.7), 736 team-seasons, 2002–2024; unchanged when years into the stint are held fixed. Pace −0.19 s (−0.39 to +0.02).
- **QB age:** +0.2 points of PROE per year (0.1 to 0.2).
- **Other positions (2013–2024, snap-weighted, 384 team-seasons):** receivers +0.5 points per year (0.3 to 0.7), linemen +0.5 (0.1 to 0.9), tight ends +0.3 (0.1 to 0.5), backs −0.3 (−0.6 to 0.0). Pace: tight ends +0.06 s per year (0.00 to 0.11), the rest about 0.
- **Defense against opponents:** linebackers +0.3 points of opponent PROE per year (0.1 to 0.5), defensive line +0.04 s of opponent pace (0.00 to 0.09).
- **About 20 coefficients were looked at,** so one or two near the edge could be chance. The rookie QB is the clear one.

**F8. Defenders carry a weaker version (H31).**
- **Plus-minus on the opponent's PROE:**
  - **Defensive backs:** week 0.15 (0.12–0.18), season 0.12 (0.09–0.16), moved 0.10 (0.04–0.17); 0.09, 0.07 and 0.07 within the offense's personnel grouping.
  - **Linebackers and the line:** about 0.1 week to week, about 0 season to season.
- **Who:** box safeties and run-down linebackers sit low (McDonald, Jenkins, Posluszny), slot corners high: the defense's own substitution, following the offense's.
- **Pace:** nothing a defender carries.

**Football sanity** ([sanity.txt](explore/sanity.txt)): the ends of each list are the right players.
- **Backs:** fullbacks lowest (Nix, Develin, Watt); receiving backs highest (White, Cadet).
- **Tight ends:** blocking tight ends lowest; Pitts and Walker highest.
- **QBs:** running QBs lowest.
- **Defense:** slot corners highest, box safeties lowest.

## What this changes in the brief
- **Pass rate is where the player signal is; pace stays mostly with the team** (F3, F6). Pace stays in, with QBs as its main carrier.
- **`player-pace-retro`:** per player-season, the play-level plus-minus on PROE (and pace), raw and within the personnel grouping. These are priors for later seasons, and they repeat at 0.4–0.56 for tight ends, receivers and backs.
- **`player-pace`, in season:**
  - each player's with-or-without by game (QBs first, F5);
  - last season's retrospective plus-minus as a prior;
  - the rookie-QB flag (F7);
  - all weighted by participation's forecast of who plays.
- **The target test** (does it help team pace's plays, dropbacks and runs, above all when the starter changes?) is the build's: not run here.
- **New terms:** on-field rate, player plus-minus, mover (as the brief defines them), and "tell": a plus-minus that marks the call more than it causes it.

## Not looked at
- **Mid-season movers** separately: they're inside the season pairs as a team change.
- **Running QBs carrying PROE**, split out from F6.
- **A full regularized plus-minus** (every player in one ridge regression, the way basketball does it). The on-off version doesn't separate two players who always sub in together; the ridge is the build's version.
- **The target test** (above).

## What not to redo
- **Don't measure a player's rate on his touches:** targets are passes and carries are runs.
- **Don't trust the week-to-week r of the by-game with-or-without:** it's inflated by changes within a season (F5).
- **Don't read a back's plus-minus as his own:** it's his package (F4).
