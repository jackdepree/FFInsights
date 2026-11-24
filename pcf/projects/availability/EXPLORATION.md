# Availability: the exploration

> **Status:** pre-registered on 2026-11-23, before any hunch's number was run; **results in, 2026-11-23: GO.** The verdicts below follow the pass rules and wait for the CEO to close them. The CEO, 2026-11-23: "Please proceed with the exploration and any more questions that you have, thank you". The tests and pass rules below were committed before their results. Results are added below them and never edit them.

## The data (profiled before any test)

Built by [`explore/build_events.py`](explore/build_events.py) into `<interim>/availability/` (gitignored). It covers the 2013–2024 regular seasons, and the 2025 vault isn't read.

- **In-game injuries:** the play-by-play names them ("BAL-71-J.James was injured during the play"). That gives 9,617 named in 2013–2024, and 9,503 (98.8%) are matched to a player by team, jersey and last name. That's 660 to 960 a season, rising over time.
  - On scrimmage plays with who was on the field (2016–2024), 6,322 of 7,186 match to a player-play. The rest are on special teams and penalty plays, which have no on-field list.
  - The rate is about **1 per 1,000 snaps**: defensive backs 1.22, defensive line 1.12, linebackers 1.06, running backs 1.07, wide receivers 0.87, the offensive line 0.74, QBs 0.69, tight ends 0.66.
- **Time missed after an in-game injury:** his team's games before his next game with a snap, within the season (the season's end counts as "missed the rest").
  - Of 9,235 injuries, **65% miss no game**. The mean is 1.5 games, and 17% run to the season's end.
- **The injury report** (2009 on): body part, game status, Wednesday to Friday practice. Players on injured reserve aren't on it, so for long injuries the body part is often missing: 6,105 of the 9,235 injuries have no next-week report row.
- **Not in the free data:** a play's length. Two stand-ins:
  - the game clock between snaps after an incomplete pass, where the clock stops at the play's end;
  - time to throw on passes, from participation, 2016 on.

  Neither covers runs.

## The order (pre-registered)

All analyses are discovery. The forecasting checks are walk-forward: each season is scored by a model fitted only on earlier seasons, scored 2017–2024. Intervals are 90%, from resampling whole team-weeks (2,000 draws) unless said otherwise.

### 0. The noise ceiling (first, before any hunch)

- **Per-play and per-game injury chance:**
  - How much do players really differ in injury rate per snap beyond position? This comes from the over-dispersion of player-season injury counts against a Poisson with each player's snaps as the exposure.
  - From that, insurance's credibility weight, Z = n / (n + k): how many snaps before a player's own rate is half signal.
  - The season-to-season repeat of a player's injury rate per snap.
- **Time missed given an injury:** its spread. The **after-the-fact ceiling** is what the next week's report status and body part explain of games missed. They're known only after the injury, so they're a ceiling for "how long is he out", not an input before it.
- **Rest-of-season games played (the I60 room), split frequency against severity:** for regular QBs, RBs, WRs and TEs at each week, the games they then missed, split into games lost to an absence already going on at the forecast moment (severity: the injury is known) and games lost to absences that start later (frequency: new injuries).
- **Model noise:** each gradient-boosted fit is refitted with 3 seeds, and the spread is reported.

### H97: a per-play injury propensity (the CEO 70%; Claude 75% that at least two of three hold, 45% all three)

- **Rows:** player-plays, 2016–2024 scrimmage plays.
- **Test:** the injury rate on plays with each feature against plays without it, within play type (run, pass) and position group, as a rate ratio with a game-week-resampled interval:
  - (a) more than one tackler;
  - (b) a tackle behind the line (a tackle for loss or a sack);
  - (c) a long play: over 5 seconds of game clock on incomplete passes, and time to throw over 3.5 seconds, reported apart.
- **Pass rule (the claim as worded, "more likely on average to observe an injury"):** a feature holds when its rate ratio's interval is above 1 at the play level (any injury on the play), within play type. **H97 held** if at least two of the three hold, **failed** if none, **unclear** if one.
- **Also reported:** the ratios by position group, and a per-play model (logistic, then gradient-boosted trees as the next rung) with position group × play features, scored by held-out log loss against position group and play type alone.
- **Claude's side check (I29, the long-drive lead):** the player's snaps so far in the drive and in the game, as features.

### H96: risk-weighted snaps beat snap counts (the CEO 70%; Claude 45%)

- **Rows:** player-games where he played, 2017–2024 scored.
- **Target:** an in-game injury that game.
- **Weights:** each past play's injury chance from H97's per-play model, fitted only on earlier seasons.
- **Two models, both logistic, with the same base:** position group, plus the player's snaps last game (this game's exposure is unknown before it).
  - **Counts:** adds snaps over the last 4 games and season to date.
  - **Weighted:** adds the same windows summed as risk-weighted snaps.
- **Pass rule:** **held** if weighted beats counts on held-out log loss with the interval above zero; **failed** if the interval is below zero or the gain is under 0.1% of the base's log loss; otherwise **unclear**.

### H98: fatigue as a recency-weighted sum of risky plays (the CEO 50%; Claude 30%)

- **Rows and target:** as in H96.
- **Feature:** the risk-weighted snaps summed with an exponential decay. The half-life is chosen inside the training seasons from 1, 2, 4 and 8 games.
- **Pass rule:** **held** if it adds clear held-out log loss (interval above zero) beside the base, plain snap counts (last 4 and season to date) and the season-to-date risk-weighted sum; **failed** if the interval reaches below zero with a gain under 0.1%; otherwise **unclear**.
- **Also reported:** a within-game version, the player's snaps so far in the game (from the H97 model).

### H93: given an injury, past injuries, recovery rate and age forecast time missed (the CEO 60%; Claude 70%)

- **Rows:** in-game injuries, 2016–2024 scored. History counts from 2013, with a career-so-far count at each injury.
- **Target:** games missed within the season, scored by squared error on log(1 + games), and also the chance of missing at least one game.
- **Base:** his position's average from the training seasons.
- **Model** (a Poisson regression):
  - past in-game injuries (count, and per 1,000 snaps);
  - his recovery rate, the average games he missed on past injuries, shrunk toward the position's (credibility);
  - age.
- **Pass rule:** **held** if the model beats the position average on held-out error with the interval above zero; **failed** if not.
- **Claude's side bet:** the same three, beside the after-the-fact ceiling (next week's body part and status), add anything clear.

### H94: some injuries repeat and others don't (the CEO 30%; Claude 70%)

- **Rows:** injury report episodes, 2009–2024. An episode starts when a body part first appears on a player's report after 4+ weeks without it.
- **For each of the 10 most common body parts:**
  - **R_same:** the chance of a new same-part episode in his next 17 team-games, over the base rate for that part (players of his position with no recent episode of it);
  - **R_other:** the same for a new episode of any other part, measuring general proneness;
  - a part **repeats specifically** if R_same / R_other's interval (resampling players) is above 1.
- **Pass rule:** **held** if at least 2 parts repeat specifically and at least 2 don't (interval covering 1); **failed** if all or none do; otherwise **unclear**.

### H95: roles differ in injury risk, and speedsters get hurt more (the CEO 50%; Claude 45% as worded)

- **Rows:** player-seasons, WR, RB and TE, 2016–2024, with 200+ offensive snaps.
- **Test:** a Poisson regression of in-game injuries with log snaps as the exposure, within position. The base is touches per snap (the obvious-input check).
- **Role measures:**
  - variance in yards per touch (the CEO's "low yardage variance per play"), as its standard deviation;
  - average target depth (WR, TE);
  - the share of touches that are catches (RB).
- **Pass rule (as worded, two parts):** roles differ if any role measure's 90% interval excludes zero beside the base; speedsters get hurt more if the yards-per-touch SD's coefficient is positive with its interval above zero.
  - **Held** if both;
  - **held in part** if roles differ but speedsters don't;
  - **failed** if neither.

### The CEO's direction: adjusted games lost (a first version, not a bet)

- **The measure:** a team-season tally of starters' games lost. Starters are the 22 with the most snaps in weeks 1–4, a stand-in for Football Outsiders' starters.
- **A game counts as lost** when he's rostered or on injured reserve and doesn't play: 1 for a game missed, 0.5 for a game he played while listed Questionable (FO's partial weight, reported both ways).
- **Its two tests:**
  - **consistency:** the season-to-season repeat;
  - **does it help:** whether last season's tally forecasts this season's, and how the same season's tally tracks the team's change in EPA per play.

## Results (2026-11-23)

*Every number comes from the scripts in [`explore/`](explore/), each with a `.txt` of its output. Each hunch's verdict follows its pass rule above, and the CEO closes it. I fixed four bugs before reading any verdict, and each verdict was read from the fixed run:*
- *A season filter in `h96_h98_workload.py` kept the wrong rows (operator precedence).*
- *`h95_roles.py`'s Poisson fits stopped after one iteration; the tolerance is now tight.*
- *`h94_repeats.py`'s list of parts let "Not Injury Related" and "resting player" through.*
- *The rest-of-season split counted a traded player as absent. It now reads him by week, on any team.*

### Go

**There's signal on every question.** The room is smaller than I60 suggested in one way and bigger in another:
- **Who gets hurt next is hard to forecast,** even though players really differ.
- **How long he's out is mostly what the next injury report says.**

### 0. The noise ceiling ([`noise_ceiling.txt`](explore/noise_ceiling.txt))

**Players really differ in how often they get hurt, beyond position.**
- **The spread:** the player-to-player variance of the true rate multiplier is about 0.49 (all positions pooled). That's an SD of about 0.7 around his position's rate, so a "fragile" player at +1 SD gets hurt 1.7 times as often.
  - By position it's 0.23 (TE) to 0.54 (LB), every interval above zero.
- **How long before his own record counts:**
  - By credibility, his own record is half signal after about **2 expected injuries**.
  - That's about 1,600 snaps for defensive players, 2,000 to 3,600 for the offense, and 6,700 for tight ends: two to four seasons of a starter.
- **It repeats:** players hurt more than expected in one season are hurt **1.37 times** their expectation the next, against 0.70 for the rest (a gap of +0.67, 0.60 to 0.74; 5,301 player-seasons with 300+ snaps in both).

**Time missed after an in-game injury:**
- **The spread:** 65% miss no game, 11% miss one, 10% two or three, 7% four to seven, and 7% eight or more. The mean is 1.5 games and the SD 3.1.
- **The after-the-fact ceiling:**
  - Next week's report status removes **62%** of the error in log(1 + games) (walk-forward 2016–2024).
  - Status × body part removes 60.5%, so the body part adds nothing once the status is known.
  - Position alone removes 1%.
  - Where they land:
    - not listed the next week: 98.7% miss nothing;
    - listed Out: 2.8 games on average;
    - off the roster the next game (reserve lists): 5.6.
- **So the "how long" question is answered mostly by the report, a week after the injury.**

**Rest-of-season games for regular QBs, RBs, WRs and TEs (2013–2024, 3,211 player-seasons):**
- **How much they miss:** 19.9% of their team's games ahead.
- **Severity against frequency:**
  - **24%** of those games are lost to an absence already going on at the forecast moment (severity: known);
  - **76%** to absences that start later (frequency: new).
- **What starts an absence** (2,878 spells):
  - 20% right after a named in-game injury;
  - 42% with an injury report listing whose injury wasn't named in a game;
  - 22% rostered and not on the report (healthy scratches, illness, other);
  - 16% off every active roster (reserve lists, releases).

  **The in-game injuries this exploration models start only a fifth of the absences.**

**Model noise:** the per-play trees' gain over three seeds runs from +1.25% to +1.40% of the log loss, so readings closer together than about 0.15 points aren't different.

### H97: a per-play injury propensity. **Held by the pass rule** (2 of 3) ([`h97_propensity.txt`](explore/h97_propensity.txt))

**Play level, any injury on the play, within play type** (2016–2024, 296,398 scrimmage plays, 6,182 with an injury):

| Feature | Rate ratio (90%) | Plays with it |
|---|---|---|
| (a) More than one tackler | **1.27 (1.20 to 1.33)** | 58,421 |
| (b) A tackle behind the line (tackle for loss or sack) | 0.94 (0.86 to 1.01), covers 1 | 22,464 |
| (c) Over 5 seconds of game clock, incomplete passes | **1.48 (1.32 to 1.66)** | 18,433 |
| (c') Time to throw over 3.5 seconds, passes | **1.12 (1.04 to 1.20)** | 25,659 |

More about (a):
- among tackled plays only, two or more tacklers against one is 1.20 (1.14 to 1.27);
- three or more tacklers: 2.57 (1.37 to 3.88), but only 206 plays.

**By position group, the feature matters for the players near it:**
- **A tackle behind the line:**
  - more injuries for the players at the ball: QBs 5.18 (sacks), RBs 1.80, the offensive line 1.47;
  - fewer for players downfield: WRs 0.12, DBs 0.35, TEs 0.55, LBs 0.75.
- **Long incomplete passes:** more injuries for WRs 2.04, DBs 1.94 and DL 1.80, the players running and rushing.
- **More than one tackler:** more injuries for DL 1.44, LB 1.42, TE 1.33, RB 1.31 and DB 1.27.

**As a model** (walk-forward 2017–2024, 5.8 million player-plays, log loss against position × play type):

| Model | Log loss removed |
|---|---|
| Logistic, the play features × position | **+0.82%** (+0.70 to +0.93) |
| Plus where the play falls in his game and in the drive | **+1.21%** (+1.08 to +1.33) |
| Gradient-boosted trees, three seeds | **+1.25% to +1.40%** |

**Claude's I29 check (the long-drive lead):**
- The defense's rate per 1,000 player-plays:
  - by his snaps so far in the game: 0.80 (snaps 1–15), 1.25, 1.54, 1.37 (56+);
  - by the play's number in the drive: 1.06 (plays 1–3), 1.24, 1.24, 1.22.
  - The offense is nearly flat in the drive (0.78 to 0.88).
- The two together add +0.39% (+0.32 to +0.45) beside the play features.
- The game-snap rise is partly who plays many snaps (starters) rather than fatigue.
- I29 stays open for the build.

**Claude's odds:**
- 75% that at least two of the three hold: **came true**.
- 45% that all three hold: didn't. A tackle behind the line is a risk only for the players at the ball.

### H96: risk-weighted snaps beat snap counts. **Failed** ([`h96_h98_workload.txt`](explore/h96_h98_workload.txt))

189,181 player-games played (2017–2024), with 6,424 in-game injuries. The base is position plus last game's snaps.

| Beside the base | Log loss removed |
|---|---|
| Counts (last 4 games, season to date) | +0.062% (+0.028 to +0.097) |
| Risk-weighted, the same windows | +0.045% (+0.017 to +0.075) |
| **Weighted against counts** | **−0.017% (−0.030 to −0.005)** |

- With this game's own snaps in both models (an after-the-fact exposure check), it's the same: −0.018%.
- The per-play risk knows the play, not whether this player was the one tackled, so weighting mostly adds noise to a count.
- Claude's 45%: didn't.

### H98: fatigue as a recency-weighted sum of risky plays. **Held by the pass rule, small**

- **Beside the counts and the season's weighted sum:** **+0.149%** (+0.085 to +0.215). The half-life chosen inside the training seasons ranges from 1 to 8 games.
- **Beside this game's own snaps** (the exposure check): +0.225% (+0.140 to +0.313), so it's not just "more snaps".
- **The trait check (who he is, or recency?):**
  - His career-long average risk per game and his past injury count, with no recency, add **+1.37%** (+1.09 to +1.66) to the same base.
  - Beside them, the recency-weighted sum still adds **+0.090%** (+0.031 to +0.147).
- **So recency is real but about a fifteenth the size of who he is.**
- Claude's 30%: **came true**. The size "under 1%" came true too.

### H93: given an injury, past injuries, recovery rate and age forecast time missed. **Held by the pass rule** ([`h93_time_missed.txt`](explore/h93_time_missed.txt))

7,186 injuries scored (2016–2024); the pre-registered score is log(1 + games).

| Against the position's average | Error removed |
|---|---|
| **Past injuries, recovery rate (shrunk), age** | **+1.62% (+1.09 to +2.21)** |
| The same, as a Poisson regression (Poisson deviance) | +2.05% (+1.21 to +2.99) |
| The chance of missing 1+ game (log loss) | +0.99% (+0.63 to +1.38) |
| *Claude's side bet:* beside the after-the-fact ceiling (status × body part) | +0.24% (−0.22 to +0.69), not clear |

**What the history says:**
- **A slow past recovery means a longer absence now:** +0.18 in log(1 + games) per unit of log recovery.
- **More past in-game injuries means shorter absences:**
  - by past injury count: 0 → 1.87 games, 1 → 1.44, 2–3 → 1.45, 4+ → 1.11;
  - many injuries go with many minor ones, and the count starts in 2013, so veterans' early injuries are missing.
- **Age:** 20–24 → 1.43 games, 31 and over → 1.82.

**Claude's odds:**
- 70% as worded: **came true**, small.
- 35% that they add beyond the report: didn't.

**The CEO's "if he got hurt on his next play" number exists:** about 1.5 games, moved by roughly ±10–20% by his history and age. The report, a week later, is what moves it most.

### H94: some injuries repeat and others don't. **Held by the pass rule** ([`h94_repeats.txt`](explore/h94_repeats.txt))

27,421 report episodes (2009–2024). Each row is the chance of a new episode in the 17 weeks after one ends, over the base rate for players of his position:

| Body part | Episodes | Same part | Any other part | Same over other (90%) | Repeats specifically? |
|---|---|---|---|---|---|
| Calf | 672 | 2.27 | 1.16 | **1.96 (1.46 to 2.45)** | yes |
| Back | 1,067 | 2.21 | 1.20 | **1.84 (1.55 to 2.12)** | yes |
| Foot | 949 | 1.90 | 1.18 | **1.61 (1.31 to 1.89)** | yes |
| Groin | 939 | 1.75 | 1.21 | **1.45 (1.18 to 1.72)** | yes |
| Hip | 882 | 1.72 | 1.22 | **1.41 (1.15 to 1.68)** | yes |
| Hamstring | 1,941 | 1.36 | 1.11 | **1.22 (1.10 to 1.34)** | yes |
| Knee | 3,443 | 1.35 | 1.17 | **1.15 (1.08 to 1.22)** | yes |
| Shoulder | 1,876 | 1.27 | 1.21 | 1.04 (0.93 to 1.15) | no |
| Ankle | 3,033 | 1.15 | 1.20 | 0.96 (0.89 to 1.03) | no |
| Concussion | 1,484 | 1.10 | 1.14 | 0.96 (0.84 to 1.10) | no |

- **The soft-tissue and chronic parts repeat** (calf, back, foot, groin, hip, hamstring), and so does the knee, mildly.
- **Ankles, shoulders and concussions** come back only at the general rate after any injury, about 1.1–1.2 times the base.
- Claude's odds:
  - 70% as worded: **came true**.
  - 40% that the hamstring repeat is 2x or more: didn't (1.36 against the base, 1.22 against other parts).

### H95: roles differ in injury risk, and speedsters get hurt more. **Held in part** ([`h95_roles.txt`](explore/h95_roles.txt))

2,395 player-seasons (2016–2024, 200+ snaps). Each is a rate ratio per SD of the measure, beside touches per snap:

| Position | Touches per snap (the obvious input) | Yards-per-touch SD ("speedsters") | Target depth | Catch share of touches |
|---|---|---|---|---|
| WR (1,204) | 1.27 (1.17 to 1.38) | 1.06 (0.97 to 1.17) | **1.13 (1.01 to 1.25)** | |
| TE (577) | 1.24 (1.16 to 1.43) | 1.11 (0.95 to 1.30) | 1.14 (0.98 to 1.31) | |
| RB (614) | 1.29 (1.02 to 1.67) | 1.09 (0.96 to 1.20) | | 1.07 (0.82 to 1.35) |

- **Roles differ:** a deep-target receiver gets hurt 13% more per SD of target depth than a short one with the same touches.
- **The speedster measure points the same way everywhere** (+6% to +11% per SD), but no interval clears 1. By its terciles, receivers go 0.78, 0.88 and 0.94 injuries per 1,000 snaps, and backs 0.81, 0.91 and 1.16.
- **The biggest role measure is touches per snap itself:** a player who has the ball more often gets hurt more often, 24–29% per SD.
- Claude's odds:
  - 45% as worded: didn't (in part only);
  - 60% that roles differ: **came true**;
  - 30% for speedsters: didn't.

### Adjusted games lost, a first version ([`agl_sketch.txt`](explore/agl_sketch.txt))

- **The tally:** 384 team-seasons (2013–2024). Starters' games lost per team-season average 45.9 (SD 17.6, range 6 to 114).
  - The worst: Denver 2022 (114), the Jets 2019 (100), Houston 2023 (98), Arizona 2022 (96) and Detroit 2021 (94).
  - Denver 2022 is the season the press called the most injured. That's a sanity check passed.
- **Consistency:** this season's tally against last season's is **r 0.20** (0.12 to 0.29). It's weak, as Football Outsiders found: teams' health repeats a little.
  - Offense 0.14, defense 0.13.
  - Full games only, without the Questionable half-games: 0.14.
- **Does it help:**
  - **The same season's tally tracks the change in net EPA per play: r −0.22** (−0.30 to −0.13). Each 10 starter games lost costs about 0.016 net EPA a play (a team's SD is 0.117).
  - The defense's games lost go with more EPA allowed (+0.14).
  - **Last season's tally doesn't forecast this season's change** (+0.06, −0.02 to +0.15).
- **It's a good description and a weak forecast,** which is what an availability expert's forecasts would have to fix.

### What it means for the brief (for the CEO's direction)

1. **Two parts, as the CEO and the analogy said, and they're very different in difficulty.**
   - **Frequency** (new absences) is three-quarters of the rest-of-season room. Per game it's barely forecastable: 1–2% of the log loss.
   - Its best inputs are **who he is** (proneness, +1.37%) and the play-level risk model. Fatigue is a small extra.
   - **Severity** (how long) is answered mostly by the next report (62%), and history adds 1.6%.
2. **In-game injuries are only a fifth of how absences start.** A target of "games played" (any cause) is what the yardstick's I60 room measures. "In-game injuries" alone would miss four-fifths of it.
3. **Proneness is the most useful new measure:**
   - a player's injury rate per snap, shrunk toward his position's by credibility (half weight at about 2 expected injuries);
   - with body-part repeat factors for the soft-tissue parts (H94).
4. **Adjusted games lost** is a team description that tracks EPA changes. Its forecast version is this expert's team output (I115 for Elo).

### The case against

- **The injured player is named in the play-by-play only when the broadcast or the league logged it.** That's 660 to 960 a season, rising over time, so part of any trend is the logging. The 98.8% match is by team, jersey and last name, and a few will be wrong.
- **"Missed" counts any game without a snap,** so a benching after an injury counts as time missed. Releases and trades land in "off every active roster".
- **Body parts come from the next report only when he's on it.** A player who went to injured reserve has no body part, so the long injuries are the least described.
- **H94's "repeats" may be one condition relisted,** not a new injury: a chronic back listed again after 4 weeks off the report looks like a repeat. A test on whether the repeat costs games would separate them.
- **The proneness spread** (τ² 0.49) includes role differences within a position (H95: deep receivers, players with the ball). It's "who he is and what he does", not only fragility.
- **H98's recency gain is small** (+0.09% beside the trait terms), and the half-life wanders from 1 to 8 games between seasons.
- **A play's length** is measured only on incomplete passes (the game clock) and by time to throw. Runs and completions have no free length.
- **All seven forecasting checks read the 2016–2024 seasons.** This is discovery. The build's harness and the vault confirm.

### Claude's new idea (to add to IDEAS.md when the brief is agreed)

- **I116 (proposed): proneness as a yardstick input.** A player's credibility-shrunk injury rate per snap, beside I60's crude games-played forecast, on the rest-of-season receiving and rushing boards.
  - Claude: 45% that it adds 0.5%+ to receiving rest-of-season, 30% for rushing.

## Follow-up: H96 against H97 (pre-registered 2026-11-23, before any number)

The CEO, 2026-11-23: "Can you please explain or test the possible incongruity between the results of h96 and h97?" H96 stays open meanwhile ("I will close all hunches except for h96, for now").

**The puzzle.** H97 says some plays are riskier than others (more tacklers 1.27x, long plays 1.48x). H96 says adding up a player's plays by that risk doesn't forecast his next injury any better than counting them. Both can be true in four ways, and each gets a check. Rows, scoring and intervals are H96's (189,181 player-games played, 2017–2024, walk-forward by season, log loss, team-week bootstrap). Script: [`explore/h96_h97_followup.py`](explore/h96_h97_followup.py).

| # | Why both could hold | The check | Claude's odds, before the run | Pass rule |
|---|---|---|---|---|
| A | **Averaging.** Over 4 games (about 150–250 plays) every player at a position gets about the same mix of risky and safe plays, so the weighted sum is a count times a constant | Within each position group: the correlation of the last-4 weighted sum with the last-4 count, and how much a player-game's average play risk varies (SD as a share of the mean) | 85% that the median group's correlation is 0.95 or more | "Averaging explains most of it" if the median correlation is 0.95+ |
| B | **Acute, not cumulative.** A risky play's danger is spent on that play. H97 is about the play itself; H96 asks whether last month's risky plays raise this week's risk | The same game, after the fact (not a forecast): this game's weighted sum against this game's count | 45% clear; if so, under 0.3% of the log loss | Clear if the interval is above 0 |
| C | **How much room weighting could ever have.** If the play model were exactly true and risk acute, what would weighting gain? | A simulated world: each player-play's injury drawn from its modelled risk, 10 draws. C1: B's same-game comparison on the drawn injuries. C2: H96's forward comparison on them | C2 covers 0 (a method check): 90%. The real B is at or below C1: 70% | Reported as the ceiling; C2 must cover 0 or the method is wrong |
| D | **Not personal.** A play's risk goes to all 22 players on it: a receiver 30 yards from a gang tackle gets the gang tackle's risk | Personal contacts instead: carries, catches, times hit or sacked as passer, tackles made (solo, assisted, sacks), over the last 4 games and season to date, beside the counts. A forecast, like H96 | 55% clear; if so, under 0.3% of the log loss | Clear if the interval is above 0 |
| E | **H98's gain is recency, not the risk weights** | H98's recency-weighted sum built on plain counts, against H98's own on risk-weighted plays, each beside the counts set, at H98's chosen half-lives | 60% that recency on plain counts gets 80%+ of the weighted version's gain | Reported as a share; "the weights carry H98" if weighted against counts is clear |
| F | **A trait, not a load.** How risky a player's plays are is part of his role (H95's deep receivers) | His career-long average risk per play beside his career injuries and career snaps per game (the obvious input) | 40% clear | Clear if the interval is above 0 |

**How it reads for H96 (the CEO closes it):**
- If **D is clear**, the CEO's idea holds with a personal weight. Weighting snaps works when the weight follows the player, not the play.
- If only **B is clear**, weighted snaps explain the same game's injuries but don't forecast the next one. H97's risk is acute.
- If **A holds and nothing else does**, the weights are a count in disguise.
