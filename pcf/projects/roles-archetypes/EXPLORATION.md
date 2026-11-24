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

> Run 2026-11-24, from the scripts in `explore/` (each writes its `.txt` beside it): `build_roles.py` (the counts), `latent.py` (the noise ceiling, H99, H100, I57), `h101_substitutes.py`, `h102_role_change.py`, `h103_h106_fit.py`, `h104_h105_vacancy.py`. **Every verdict below is by its pass rule; the CEO closes the hunches.**

### The data, as built

- **15,721 player-team-seasons**, 2016–2024; **7,871 with 200+ snaps**: WR 1,239, TE 705, RB 626, DL 1,784, OLB 712, ILB 671, CB 1,187, S 947.
- **4,924 consecutive-season pairs** (1,141 of them movers).
- **Measurables:** height and weight for all of them; the 40 for 67%.

### 0. The noise ceiling

- **How much a role can repeat** (split-half r, odd weeks against even, median over groups):
  - **Playing time** repeats most: snap share 0.90, carries per run snap 0.90.
  - **When he's on the field:** the team-adjusted own-snap shares range 0.69–0.88, and the on/off tilts 0.60–0.78. The red zone is the exception: 0.29 and 0.31, too few plays.
  - **What he does:**
    - offense: targets per pass snap 0.69, target depth 0.52, the behind-the-line share 0.45, the outside-carry share 0.46, the deep share 0.33, the middle share 0.31;
    - defense: tackles per snap 0.44, rushes per pass snap 0.42, tackle depth 0.34, the solo share 0.32, passes defensed per pass snap **0.12** (close to noise).
- **Label noise (H102's floor):** M1's label differs between a season's two halves for **14%** of player-seasons at the median group, and between seasons for **22%**. **Most season-to-season "role changes" are the size of the label's own noise.**
- **Fitting noise:**
  - PCA loadings are stable: bootstrap congruence 0.9+ for the first 4 components in 6 of 8 groups (TE and ILB reach 0.8–0.88 on components 3–4).
  - The mixtures agree across seeds (adjusted Rand 0.99), but only 0.69 with measurables, and as low as 0.18 where BIC picked 5 or 6 clusters.
- **The room for fit effects (H103, H106):** efficiency itself barely repeats.

  | Group | Measure | Split-half r | Season r |
  |---|---|---|---|
  | WR | EPA per target | 0.11 | 0.16 |
  | TE | EPA per target | 0.12 | 0.05 |
  | RB | EPA per touch | 0.29 | 0.39 |

  A role × scheme effect has to hide inside that small repeatable part, so the ceiling said to expect failures there.

### H99: the plays he's off say his role (CEO 60%; Claude 65%) — **failed** by the pass rule

- **The test:** season-to-season r of the on/off versions minus the team-adjusted own-snap versions, averaged over 6 dimensions × 8 groups. The gain is **−0.051** (90% −0.067 to −0.035): the on/off versions repeat *less*.
- **Where:**
  - **About equal for offense and the defensive line.** For example, TE run tilt 0.76 against 0.77; DL run 0.73 against 0.72.
  - **Better in one place:** a back's 12-personnel tilt, 0.76 against 0.62 (+0.16 for part-time backs).
  - **Much worse for the back seven:**

    | Dimension | Group | Own-snap | On/off |
    |---|---|---|---|
    | Run | CB | 0.43 | 0.17 |
    | Run | S | 0.42 | 0.18 |
    | Run | ILB | 0.43 | 0.23 |
    | 11 personnel | ILB | 0.33 | 0.17 |

- **Claude's side bets:**
  - **Part-time players gain 0.05+ (55%): no**, −0.002.
  - **Every-down players nothing (85%): no.** They *lose* 0.039, because an every-down player's off plays are a handful of rest snaps and injuries, and those are noise.
- **Reading:**
  - **Real?** Partly. The off plays carry role information for part-timers in heavy personnel (backs, the second tight end), at about the own-snap measures' level, not above it.
  - **Pays?** No: as a general role measure it's worse.
  - **Why the back seven:** the defense doesn't pick its personnel by the offense's play, so a defender's on/off tilt against "run" is mostly substitution noise. **The own-snap, team-adjusted version is the simpler side and wins.**

### H100: a positionless latent space (CEO 50%; Claude 70%) — **held in part** by the pass rule

- **(a) Consistent: not met at the median group.**
  - For M2 without measurables, the median group has **2 of 6** components with split-half r 0.5+ (it needs 4).
  - **Offense meets it:** WR 5, TE 5, RB 3. **Defense doesn't:** DL 1, OLB 2, ILB 2, CB 1, S 2.
- **(b) Predicts roles: met in 3 of 3.** The held-out vertical route share gets a cross-validated R² of **0.43** (WR), **0.34** (TE) and **0.38** (RB) from the 6 components.
- **What the components are**, by their top loadings, and they read as football:
  - WR:
    - z0 is 11-personnel use (slot and three-receiver sets);
    - z1 is depth (target depth up, behind-the-line share down, deep share up);
    - z2 is playing time and targets;
    - z3 is the red zone.
  - TE: z0 is the run-blocking tilt (on for runs, off on 3rd down), explaining 37%; z2 is depth.
  - RB: z0 is 11 personnel against run downs; z1 is the 12-personnel and carries back.
  - DL: z0 is the run-down tilt, explaining 52% (the run stuffer against the pass rusher); z2 is sacks and the solo share.
- **The three methods side by side** (median over groups, first 4 components):

  | Method | Split-half r | Season r | Components at 0.5+ | Movers keep | Note |
  |---|---|---|---|---|---|
  | M1 role table + mixture | label flips 14% / 22% | | | | k = 2 in 7 of 8 groups |
  | M2 PCA (the CEO's) | 0.57 | 0.42 | 2 | 0.69 | |
  | Factor analysis (varimax) | 0.54 | 0.30 | 3 | 0.53 | worse than M2 everywhere but split-half count |
  | M3 on/off factorization | 0.58 | 0.32 | 2 | 0.53 | its first component *is* snap share (r 0.93–0.97) |
  | M2 + measurables | 0.71 | 0.58 | 4 | 0.84 | |
  | M3 + measurables | 0.85 | 0.55 | 4 | 0.63 | |

- **Three things the comparison says:**
  1. **Measurables inflate consistency, as warned.** Height, weight and the 40 don't change, so a component built on them repeats by construction. With measurables every method passes (a); without them only offense does. **Measurables belong beside the role as fixed inputs, not inside it.**
  2. **M1's clusters are mostly playing time.** With k = 2 in 7 of 8 groups, the split is the starter against the rotational player:
     - WR snap share logit 1.25 against 0.17;
     - CB 2.11 against 0.40;
     - ILB 2.63 against 0.27.

     The traditional labels the CEO wants ("slot receiver", "move tight end", "nickel corner") don't come out of a 4–5 feature mixture by BIC. **They'd need named rules or more clusters forced.**
  3. **M3 sees only when he's on the field,** and its first component is playing time. Its later components (personnel and down tilts) repeat less than M2's.
- **The obvious-input check:** each component's correlation with snap share is mostly under 0.4 for M2, except WR z2 (0.73) and the second components of CB and S (0.60–0.63). Refitted without snap share (`m2ns`), every result below is the same.
- **Claude's side bets:**
  - **Top components repeat season to season at r 0.5+ (75%): mostly no.** Median 0.42; yes for WR z1–z2, TE z0, RB z0–z1 and DL z0.
  - **Stable loadings, congruence 0.9+ for the first 4 (60%): yes**, in 6 of 8 groups.
  - **Beat a role table downstream (30%):** not tested here; it's the build's yardstick question.
- **Reading:**
  - **Real?** Yes for offense: a few components that repeat, read as football, and predict a route mix they never saw.
  - **For defense:** one strong component each (the run-down tilt, or playing time), and the rest near noise in this data. Without coverage or alignment, the free data sees a defender's role only through when he's on the field and a few counted events.

### H101: like-for-like substitutes (CEO 40% for like-for-like; Claude 85%) — **held** by the pass rule (small)

- **The data:** 13,294 regulars' absences; **904 events** with a pool of 2+ non-regular teammates who had a prior-season role.
- **The result:** the replacement's distance rank to the absent player is **0.439** (90% 0.404 to 0.471; chance 0.5). He's the closest in his pool 47% of the time, against about 44% by chance.
- **Without snap share** (the sensitivity): 0.435 (0.402 to 0.467). The same, so "they both play a lot" doesn't explain it.
- **By group** (mean rank):

  | RB | OLB | S | TE | ILB | WR | CB | DL |
  |---|---|---|---|---|---|---|---|
  | 0.30 | 0.24 | 0.38 | 0.42 | 0.43 | 0.45 | 0.47 | 0.48 |

- **Claude's side bets:**
  - **More for tight ends and backs than receivers (55%): yes for backs**, about even for tight ends.
  - **Closer than the depth chart's next man (45%):** not tested; the depth-chart join is for the build.
- **Reading:**
  - **Real?** Yes, but small. Teams do swap roughly like for like, most clearly at running back and outside linebacker. Defensive linemen and corners are replaced almost at random by role, because rotations there are by count, not by kind.
  - **Pays?** Not tested as a forecast. It supports I49 (swap pairs).

### H102: an in-season chance his role is unchanged (CEO 60%; Claude 70%) — **held in part** by the pass rule

- **The data:** 4,924 pairs; the label changed for **21.1%** (S 37%, OLB 6%). Scored 2018–2024, 4,318 pairs.
- **Week 8:** the log loss is 0.4857 against the base rate's 0.5031.
  - The gain is **0.0174** (3.5%; 90% 0.0085 to 0.0256).
  - The calibration slope is **0.65**: outside 0.8–1.2, so overconfident. The model has about 30 inputs for 4,000 rows.
  - The top fifth changed 37.5% of the time, the bottom fifth 7.9%.
- **Week 4 (Claude's 50% side bet): yes.** The gain is 0.0209 (0.0128 to 0.0289), *larger* than week 8's, another sign of overfitting.
- **The obvious input:** the change in snap share alone, with group dummies, gains **0.0198: 114% of the full model**. **By rule k the simpler model wins:** a role-change chance from the snap-share change alone.
- **Reading:**
  - **Real?** Yes, but mostly because M1's labels are playing-time tiers (H100), so a "role change" is mostly a playing-time change.
  - **Pays?** As a playing-time signal, which the participation expert already has.
  - A role-change chance worth having needs a label that isn't playing time (I123).
  - The base rate is near the label's own noise (21% changes against 14% between halves), so a third of "changes" can't be forecast at all.

### H103: roles and schemes fit (CEO 75%; Claude 30%) — **failed** by the pass rule

- **Side bet: roles cluster on schemes (Claude 80%): held.** A multinomial of M1 labels on the team's scheme traits beats teams shuffled, in cross-validated log loss:

  | Group | Log loss | Shuffled | Better than |
  |---|---|---|---|
  | WR | 0.6932 | 0.6966 | 98% of 50 shuffles |
  | TE | 0.6834 | 0.6898 | 98% |
  | RB | 0.7674 | 0.8521 | 100% |

  Backs are the large one: a team's personnel use says a lot about which kind of back it plays.
- **The fit test:** label × scheme interactions make leave-one-season-out efficiency forecasts **worse**:

  | Group | B's gain | 90% interval |
  |---|---|---|
  | WR | −0.6% | covers 0 |
  | TE | −1.2% | below 0 |
  | RB | −2.7% | below 0 |
  | Pooled | −0.00033 EPA² | −0.00054 to −0.00014 |

- **In-sample** (Claude's 50% side bet: technically yes, at chance level). 2 of 21 interactions have a clear 90% interval, about what chance gives:
  - the WR playing-time tier × pass rate over expected (+0.022 EPA per target per SD);
  - one RB label × 12-personnel rate (−0.009).

  **Retroactive and one of many tried.**
- **Reading:**
  - **Real?** The association is real: schemes use certain roles. That it changes efficiency is not seen.
  - **Pays?** No.
  - **Why:** the ceiling said so. Efficiency repeats at 0.11–0.29 within a season, and a role × scheme effect would be a slice of that slice.

### H104 and H105: vacancies and targeting (CEO 30% each; Claude 55% and 35%) — both **failed** by the pass rule

- **The data:** 218 vacancies (a top-2 WR, top TE or top RB gone the next season), filled by 393 newcomers.
- **H104:** forecasting the newcomer's coordinates. Mean squared distance:

  | Forecast | Distance | Against (a), 90% interval |
  |---|---|---|
  | (a) the group's average | 13.9 | |
  | (b) the departed player | 20.8 | −6.9 (−8.1 to −5.8) |
  | (c) the team's usual role | 15.8 | −2.0 (−2.5 to −1.4) |

  A single player's point is far noisier than the average, so it loses as a raw forecast.
- **Side bet** (Claude 60%): newcomers sit closer to their own team's departed player than to other teams'. **Held:** rank 0.421 (0.393 to 0.449; chance 0.5), and 0.415 without snap share.

  So **the vacancy's role is information** (real), just not as a forecast on its own (pays: not as tested). Shrinking the forecast part-way from the average toward the departed player is the fair test (I122).
- **H105:** veteran movers' role *before* they arrived, against the departed player's, ranked among that offseason's movers in the group. **0.491** (0.458 to 0.524; chance 0.5): **no sign teams target by role** in free agency and trades. Without snap share, 0.499.

  The likeness in H104's side bet comes after arrival: **the team gives the newcomer the role, it doesn't shop for it.**

### H106: archetype against the defense's scheme (CEO 30%; Claude 15%) — **failed** by the pass rule

- **The data:** WR and TE player-games with 3+ targets, 2019–2024: WR 6,494 and TE 2,582 (2020–2024 scored).
- **The result:** label × the opponent's prior-season box, man, two-high and blitz rates make the walk-forward forecast of EPA per target **worse**:
  - WR −0.26% (interval below 0);
  - TE −0.17% (covers 0);
  - pooled −0.00099 (−0.00166 to −0.00035).
- **In-sample** (Claude 45%): **no**, 0 of 8 interactions clear.
- **Reading:**
  - **Real?** Not seen.
  - **Pays?** No.
  - This is schemes' matchup result again (H9, H13) at the player level. The labels here are playing-time tiers, though, not speed archetypes. A test with a real speed archetype (the 40, or a deep-share label) against two-high rates is the narrower version still untried (I123's labels would make it possible).

### The backlog checked here

- **I57 (Claude 80%): held.** A receiver's vertical route share repeats season to season at **r 0.60** (724 pairs with 20+ targeted routes both seasons), and M2's components predict it (R² 0.43).
- **I113:** M1 is the role table's first version, and it reads as playing-time tiers. **The next version needs named, rule-based roles beside the mixture.**
- **I49:** H101 supports swap pairs' idea, small (rank 0.44), clearest for backs (0.30).

### How Claude's odds did (for the retro)

| Hunch | CEO | Claude | By the pass rule |
|---|---|---|---|
| H99 | 60% | 65% | failed |
| H100 | 50% | 70% | held in part |
| H101 | 40% | 85% | held (small) |
| H102 | 60% | 70% | held in part |
| H103 | 75% | 30% | failed |
| H104 | 30% | 55% | failed |
| H105 | 30% | 35% | failed |
| H106 | 30% | 15% | failed |

Side bets: 5 of 9 tested came true. Yes: H100's congruence, H101's backs, H102's week 4, H103's clustering, H104's own-team closeness. No: H99's part-time and every-down, H100's season r, H106's in-sample.

### The case against

1. **M1's labels are fitted on 2016–2020** and used as H102's target in its 2018–2020 training seasons, so the label definition saw those seasons. The inputs are point-in-time; the label isn't. That's acceptable for a look, not for the build.
2. **H101's replacement is defined by a rise in snap share,** not by play-level substitution. A team that spreads an absent player's snaps over three teammates gets one "replacement" here. The effect is small (closest 47% against 44% by chance), and with 904 events in 8 groups it could shrink in a cleaner design.
3. **H99's defensive failure may be participation's recording,** not football. If on-field lists for defensive backs are noisier, the on/off tilt suffers most where the off plays are fewest. This look can't tell the two apart.
4. **H104's pass rule was unfair to (b):** a raw point against an average. It was pre-registered, so the verdict stands, but its side bet says the information is there.
5. **Many tests were run,** and the in-sample interactions (2 of 21, 0 of 8) are at chance. **Nothing in H103 or H106 should be read as a combination that works.**
6. **The labels that most tests use are M1's playing-time tiers.** H102, H103 and H106 are tests of tiers, not of the archetypes the CEO had in mind. A failure here doesn't rule out a real archetype (a speed receiver, a move tight end) against a scheme.

### Go or no-go

**Go**, as a retrospective expert first. There's signal, and it's clearest on offense:
- the components repeat, read as football and predict a held-out route mix;
- substitutes are roughly like for like;
- roles cluster on schemes;
- the vacancy's role is information.

What the brief should carry (the CEO decides):
- **`roles-retro`:**
  - M2 components per offensive group, without measurables inside them (measurables as separate fixed inputs);
  - named rule-based labels beside them (I113's next version);
  - the defense limited to its one or two components that repeat.
- **`roles-live`** (the in-season chance): **the snap-share change wins by rule k** until a label that isn't playing time exists, so it may fold into participation rather than stand alone.
- **Dropped from the build, as tested:** on/off tilts as a general measure; role × scheme efficiency effects; role targeting in free agency.


## The second look: H107 and H108 (pre-registered 2026-11-24, before any number)

> After the CEO's reply to the results (BRIEF.md, the third message) and their odds ("H107; 75%, h108; 50% please proceed with the exploration"). Offense only (WR, TE, RB), as the CEO directed. Written before either script ran.

### The positionless space (both tests use it)

- **One PCA across WR, TE and RB pooled**, not one per group: the same features as M2 (snap share, the team-adjusted own-snap shares, the on/off tilts, the offensive usage rates), standardized, 6 components, fit on 2016–2020 player-seasons with 200+ snaps, applied to every season. No measurables and no position label inside it.
- **Reported:** its loadings, its components' split-half and season r, and how well the coordinates alone recover the position label (cross-validated accuracy against the majority share), so we see whether "positionless" still sorts the positions.

### H107: a latent space of responsibilities describes players better than position labels (the CEO 75%; Claude 80%)

- **Rows:** consecutive-season pairs, WR, TE and RB, 200+ snaps in both seasons.
- **Targets:** next season's targets per snap and carries per snap.
- **Models** (ridge, standardized inputs, leave-one-target-season-out):
  - **P:** the three position labels;
  - **Z:** the 6 pooled coordinates from season s, no position label.
- **Pass rule:** **held** if Z's squared error beats P's on both targets, each with a 90% player-bootstrap interval above 0. **Held in part** if one. **Failed** if neither.
- **Side bets (Claude):**
  - **Beyond the obvious input (45%):** on next season's receiving plus rushing yards per game (a stand-in for the crude yardstick, not `score_input`), the base is P plus last season's targets, carries and yards per game and his snap share; adding Z beats the base with a 90% player-bootstrap interval above 0.
  - **Against a role table of the same size (30%):** six hand-picked features (snap share, targets per pass snap, carries per run snap, target depth, the team-adjusted run share and 11-personnel share), added to the same base. Z beats the table with an interval above 0. A tie goes to the table (rule k).

### H108: outcomes attributed by responsibility (the CEO 50%; Claude 25%)

- **Plays:** every regular-season pass or run, 2016–2024. Each offensive WR, TE and RB on the field (participation), the play's EPA.
- **The target group** on a play is the targeted receiver or the ball carrier. Every other skill player on the field is the **support group**. Sacks and scrambles have no target: everyone is support.
- **Three credit models,** one season at a time, ridge, with the offense's and the defense's team-season as fixed effects (they absorb the quarterback, the line and the opponent):
  - **A, plain plus-minus (the simpler side):** one value per player for being on the field.
  - **B1, by responsibility:** two values per player, one when he's the target group and one when he's support. His credit is the two weighted by his own mix that season.
  - **B2, by identity in the latent space:** plain plus-minus with his pooled coordinates as inputs. A play's skill players' coordinates enter as summed features, so outcomes are partly credited to the role. His credit is the role's part plus his own.
  - The ridge penalty is chosen once, by 5-fold cross-validation on 2016 only, for each model.
- **The test:** each model's credits, season to season, for **movers**: players with 300+ on-field plays in both seasons who changed teams. Stayers are reported beside them.
- **Pass rule:** **held** if B1 or B2 repeats more for movers than A does (season r), with a 90% player-bootstrap interval above 0. **Failed** otherwise. A tie goes to A.
- **B2 is partly circular,** because its role part repeats whenever the coordinates do. So its player's own part (the residual) is reported apart, and the verdict names which part carried it.
- **Side bet (Claude 50%):** the target-group value alone (B1's) repeats for movers at r 0.2 or more.
- **Pays? (reported, not part of the pass rule):** each team-season's average of last season's credits for its skill players on the field. Does it forecast this season's offensive EPA per play beyond last season's EPA per play? This is the roster-change idea at small scale: the partial correlation with a team bootstrap, for each model.
