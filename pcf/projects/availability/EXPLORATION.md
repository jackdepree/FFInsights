# Availability: the exploration

> **Status:** pre-registered on 2026-11-23, before any hunch's number was run. The CEO, 2026-11-23: "Please proceed with the exploration and any more questions that you have, thank you". The tests and pass rules below were committed before their results. Results are added below them and never edit them.

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

## Results

*To come, below this line, without editing the plan above.*
