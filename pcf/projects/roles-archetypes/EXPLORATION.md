# Roles and archetypes: the exploration

> Started 2026-11-24, after the CEO's hunches H99 to H106 and their odds ("So please proceed, thank you"). Everything below the results line was written before any test number. A discovery look, not proof: the build's harness and the 2025 vault confirm.

## The data (profiled before any test)

- **Who was on the field** (`player_play.on_field`, from participation): 6,823,406 player-plays in 2016–2024 regular seasons, every player on every scrimmage play, with his depth-chart position. After the season only, so **retrospective**.
- **Personnel** is counted from who's on the field (RBs, TEs and WRs on offense; DBs on defense), not parsed from participation's string, which has variants and is missing on 23% of plays in 2016–2022.
- **Routes:** the targeted receiver's route only, about 38% of plays (every target) 2016–2022, all plays 2023–2024. **Coverage** (man or zone, the shell) from 2018 only.
- **Play-by-play** (in season): pass or run, down, distance, field position, air yards, pass location, run direction, the targeted receiver and rusher, tacklers (solo and assisted), sacks and hits, passes defensed, pass rate over expected (`pass_oe`).
- **Measurables:**
  - height and weight for nearly every player (`players`);
  - combine results through `pfr_id` (the 40 for 90% of invitees, the vertical for 76%, the cone for 57%).
- **Team schemes** (`team_season.charted`, schemes-v2): each team-season's personnel rates, pistol, time to throw and the box, man, two-high and blitz rates it faced and used, raw and over expected.
- **The vault (2025) is untouched.**

## The terms

- **Player-season:** a player's rows with one team in one regular season, with 200+ snaps on his side. Groups by his most common position that season:
  - offense: WR; TE; RB (with FB);
  - defense: DL (DE, DT, NT); OLB; ILB (with MLB); CB; S (FS, SS).
- **Own-snap features** (the usual way): shares of *his* snaps. Examples: the share of his snaps that are passes, in 11 personnel, on 3rd or 4th down, in the red zone. Each comes raw and **team-adjusted** (minus his team's share on all its plays), which holds his team's pass rate and personnel use fixed.
- **On/off features** (H99): his chance of being on the field in one kind of team play against another, on the log-odds scale. Examples: the run tilt, logit(on | run) − logit(on | pass), and the same for 11 personnel faced or used, 3rd or 4th down, and the red zone. They read the plays he's *off* as much as those he's on, within his own team's plays.
- **Usage features:**
  - offense: targets per pass snap, target depth, the share of targets that are deep (20+ air yards), behind the line, or to the middle; carries per run snap; the share of carries outside;
  - defense: tackles per snap, the solo share of his tackles, tackle depth (yards gained on plays he tackled), sacks and hits per pass snap, passes defensed per pass snap.
- **Measurables:** height, weight, the 40. A missing value gets the group's mean plus a flag.
- **Shrinkage:** each rate is pulled toward its group's average by a prior worth 100 snaps (10 targets for per-target means); on-rates are smoothed. Low-snap players don't read as extreme.

## The order (pre-registered)

### 0. The noise ceiling (first)

- **How much a role can repeat:** every feature's split-half reliability, odd weeks against even weeks within a season, per group.
- **Label noise (H102's floor):** the share of player-seasons whose cluster label differs between the odd-week and even-week halves of one season. "Role changes" below that rate are noise.
- **Fitting noise:**
  - PCA: each component's loadings refit on 200 player-bootstrap samples, against the full fit (congruence);
  - the clusters: agreement across 20 seeds (adjusted Rand).
- **The room for fit effects (H103, H106):** the split-half reliability of efficiency (EPA per target or per touch). An effect bigger than what efficiency itself repeats can't be found.

### H99: the plays he's off say his role (the CEO 60%; Claude 65%)

- **Test:** matched pairs, each one dimension measured two ways: own-snap and team-adjusted, against on/off.
  - pass or run;
  - 11 personnel;
  - 12 personnel;
  - heavy personnel;
  - 3rd or 4th down;
  - the red zone.

  For each pair and group: the season-to-season correlation of player-seasons in consecutive seasons, and the split-half correlation.
- **Pass rule:** **held** if the average season-to-season r of the on/off versions minus the team-adjusted own-snap versions is above 0, with a 90% player-bootstrap interval above 0. **Failed** if the interval is below 0 or the average gain is under 0.02. **Unclear** otherwise.
- **Reported apart:** part-time players (snap share under 60%) against every-down players (Claude's side bets).

### H100: a positionless latent space (the CEO 50%; Claude 70%)

- **The three methods** (the CEO: "try all three"), fitted per group on 2016–2020 player-seasons and applied to all seasons:
  - **M1, the role table and clusters (the usual way, and the simpler side):** 4–5 hand-picked features per group (I113). A Gaussian mixture with 2 to 6 clusters, the count picked by BIC, and the clusters named afterwards from their centres.
  - **M2, PCA (the CEO's method):** every feature (own-snap, on/off, usage), standardized, 6 components. Factor analysis with varimax rotation (6 factors) is reported beside it.
  - **M3, the on/off factorization (exploratory):** each player-season's smoothed log-odds of being on the field in each of 32 kinds of team play (pass or run × early or late down × personnel faced or used: 11, 12, heavy, other × red zone or not). PCA of that matrix, 6 components. It sees only *when* he's on the field, nothing of what he does.
- **Each method is run with and without the measurables.**
- **Pass rule for the CEO's claim** (M2 without measurables):
  - (a) **consistent:** at least 4 of the first 6 components have a split-half r of 0.5 or more, at the median group;
  - (b) **predicts roles:** for WR, TE and RB, the components predict a held-out role measure better than the group's average, with a cross-validated R² of 0.2 or more in at least 2 of the 3 groups. The held-out measure, not among the inputs, is the vertical share of his targeted routes (GO, POST, CORNER, WHEEL).
  - **Held** if both; **held in part** if one; **failed** if neither.
- **Claude's side bets:**
  - season-to-season r of 0.5+ for the top components, 75%;
  - stable loadings (congruence 0.9+ for the first 4), 60%.
- **Also reported:**
  - **the three methods side by side:** the median split-half and season r of the first 4 components, and the share of the repeat a mover keeps;
  - **the obvious-input check:** each component's correlation with snap share, and its repeat after snap share is removed.

### H101: like-for-like substitutes (the CEO 40% for like-for-like; Claude 85%)

- **Events:** a regular is out. That's a player with a 50%+ snap share in his group over the earlier games he played that season (2+ games). He has no snap in a team game, and the team plays.
- **The replacement:** the teammate in his group who played that game and whose snap share rose most above his own earlier average.
- **The comparison pool:** the teammates in his group who played that game, weren't regulars themselves, and have a prior-season role.
- **The statistic:** the rank of the replacement's distance to the absent player among the pool (0 closest, 1 farthest, ties averaged), using M2's prior-season components (known before the season). Chance is 0.5.
- **Pass rule:** **held** (like-for-like) if the mean rank is below 0.5 with a 90% team-season bootstrap interval below 0.5. **Failed** if the interval covers or exceeds 0.5.
- **Sensitivity:** the same with components refitted without snap share (playing time), so "he also plays a lot" can't make two players look alike.

### H102: an in-season chance his role is unchanged (the CEO 60%; Claude 70%)

- **The label:** M1's cluster. A change means his season's label differs from last season's, in the same group, with 200+ snaps both seasons. 2017–2024.
- **In-season inputs through week 4 and week 8, with no participation:**
  - from in-season snap counts and play-by-play: snap share, targets per snap, carries per snap, target depth, the middle-target share, tackles per snap, the solo share, tackle depth, sacks and hits per snap, passes defensed per snap;
  - each against his last season;
  - a team-change flag;
  - his team's pass rate over expected and pace (plays a game), against last season;
  - last season's label and how sure the mixture was of it.
- **Model:** a logistic regression with group dummies, walk-forward by season (trained on earlier seasons; 2018–2024 scored).
- **Baseline:** each group's change rate in the training seasons.
- **Pass rule:**
  - **Held** if the week-8 log loss beats the baseline with a 90% team-season bootstrap interval above 0 *and* the calibration slope is between 0.8 and 1.2.
  - **Held in part** if only the gain is clear.
  - **Failed** if the gain isn't clear.
  - Week 4 is reported beside it (Claude's side bet, 50%).

### H103: roles and schemes fit (the CEO 75%; Claude 30%)

- **Rows:** WR, TE and RB player-seasons.
- **The scheme:** his team's season traits over expected:
  - 11, 12 and heavy personnel rates;
  - time to throw;
  - pistol;
  - plus pass rate over expected and target depth from the play-by-play.
- **Side bet, roles cluster on schemes (Claude 80%):** a multinomial of M1 labels on the scheme traits, scored by cross-validated log loss against the same model with teams shuffled.
- **The fit test:**
  - **Outcome:** EPA per target (WR, TE) or per touch (RB), weighted by volume.
  - **Model A:** label + scheme traits + his prior-season efficiency (the obvious input), with a flag when he has none.
  - **Model B:** A + label × scheme traits.
  - **Scoring:** leave-one-season-out, weighted squared error.
- **Pass rule:** **held** if B beats A with a 90% team-season bootstrap interval above 0. **Failed** otherwise.
- **Also reported:** the in-sample combinations with clear intervals (Claude's side bet, 50%), marked as retroactive and as one of many tried.

### H104 and H105: vacancies and targeting (the CEO 30% each; Claude 55% and 35%)

- **Departures:** a regular (his team's top 2 WRs, top TE or top RB by snaps) on team T in season s who has no snaps for T in s + 1.
- **Newcomers:** players in that group on T in s + 1 with 200+ snaps who weren't on T in s.
- **H104:**
  - **The task:** forecast the newcomer's M2 coordinates with T in s + 1 from (a) his group's average, (b) the departed player's coordinates, or (c) T's average coordinates in that group in season s (the scheme's usual role). Error is the squared distance.
  - **Pass rule:** **held** if (b) or (c) beats (a) with a 90% team bootstrap interval above 0.
  - **Side bet:** newcomers are closer to their own team's departed player than to other teams' departed players at the same group (a permutation).
- **H105** (veteran movers only, his role before arriving):
  - **The test:** his season-s coordinates (with his old team) against the departed player's, ranked among the season-s coordinates of every veteran mover in his group that offseason.
  - **Pass rule:** **held** if the mean rank is below 0.5 with a 90% bootstrap interval below 0.5.

### H106: archetype against the defense's scheme (the CEO 30%; Claude 15%)

- **Rows:** WR and TE player-games with 3+ targets, 2019–2024 (coverage traits start in 2018, so prior seasons from 2018).
- **The outcome:** EPA per target that game.
- **Inputs, all known before the season:**
  - his prior-season M1 label;
  - his prior-season EPA per target;
  - the opponent's prior-season pass EPA allowed per play;
  - the opponent's prior-season defensive traits over expected: box, man, two-high, blitz.
- **Model A:** main effects. **Model B:** A + label × the four traits.
- **Scoring:** walk-forward by season, target-weighted squared error.
- **Pass rule:** **held** if B beats A with a 90% game-week bootstrap interval above 0. **Failed** otherwise.
- **Also reported:** in-sample interactions with clear intervals (Claude's side bet, 45%).

### The backlog checked here

- **I57:** a receiver's targeted route mix (the vertical share) repeats season to season. Claude 80%.
- **I113:** M1's role table is its first version.
- **I49:** H101 tests the swap pairs' idea.

## Results

*Not yet run.*
