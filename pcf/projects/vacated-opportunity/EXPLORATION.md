# Vacated opportunity: the exploration

> Started 2026-11-24, after the CEO's hunches H109 to H112, their odds, and the methods ("Try the first two methods in this exploration"). Everything above the results line was written before any test number. A discovery look, not proof: the build's harness and the 2025 vault confirm.

## The data (profiled before any test)

- **Snap shares per player-game** (`player_game.snaps`, from Pro Football Reference): offense and defense snaps and shares, every rostered player who played, 2013 on. Known after each game.
- **Who was on the roster each game** (`player_game.roster`, weekly rosters): team, position (WR, TE, RB, OL, DL, LB, DB, ...), birth date, draft year. It includes postseason weeks, so only regular-season games are kept.
- **Targets and carries per player-game** (`player_game.stats`), and the play-by-play for team efficiency (EPA per play) and pressure.
- **Pressure** (`play.participation`'s `was_pressure`, on dropbacks, 2016 on; about 40% of plays carry the flag before 2023, almost all from 2023). A sack counts as a pressure (F34: before 2023 the flag is empty on sacks). Pressure rate is computed over dropbacks where the flag or a sack is present. Pressure belongs to the line as a group, not to one lineman.
- **Roles' pooled offensive coordinates** (`<interim>/roles/pooled.parquet`, from roles' second look): 6 numbers per WR, TE and RB player-season with 200+ snaps.
- **Seasons:** 2016–2024 regular seasons. Offseason pairs run from 2016→2017 to 2023→2024. **The 2025 vault is untouched.**

## The terms

- **Groups:** WR; TE; RB (with FB); OL; DL (the roster's DL; edge rushers listed as LB are not in it).
- **A top player:** among his team's top k by snaps in his group that season: WR 2, TE 1, RB 1, OL 5, DL 3.
- **His share:** the average of his snap share over the games he played for that team. Target share and carry share are his targets (carries) over his team's, in the games he played.
- **A departure:** a top player on team T in season s with no snap for T in s + 1 (he left, retired or was released).
- **A stayer:** a player in that group who played for T in both s and s + 1.
- **An absence:** a game his team played, between his first and last game for it that season, in which he had no snap.
- **His "with" share:** his share in season s's games where every departed teammate in his group played.

## The order (pre-registered)

### 0. The noise ceiling (first)

- **How much a stayer's next share can be forecast at all:** the split-half reliability (odd against even weeks) of his s + 1 share, per group. Its square root bounds any forecast's correlation.
- **How much the shares move:** the spread of a stayer's share change, s to s + 1, and how much of it the departures' vacated share explains in-sample (the room for H109).
- **Team efficiency:** the season-to-season r of a side's EPA per play, and how large a change is typical (the room for H110 and H112).
- **The plus-minus's fitting noise:** its ridge penalty is chosen once, by cross-validation on 2016's games. How often its pooled values flip sign across team-bootstrap draws is reported.

### H109: a plus-minus for all players gives the stayers' share (the CEO 75%; Claude 35%)

- **Rows:** stayers in groups with at least one departure, offseason pairs 2016→2017 to 2023→2024.
- **The target:** his s + 1 share.
- **Method 1, the usual way** (the simpler side):
  - **1a, proportional split** (the pre-registered comparison): his with share, plus the departed players' with shares shared out in proportion to the stayers' with shares, his total capped at 1.
  - **1b, with or without** (reported): his with share, plus his share in season s's games without the departed player minus his share with him, where he played 2+ games without him; otherwise 1a's allocation for that departed player.
  - **No change** (reported): his with share.
- **Method 2, the CEO's plus-minus for all players:** a ridge regression over every player-game in the five groups, fit on season s's games.
  - **Each player's share is measured against his own season average,** so a player's level doesn't count, only the games where it moves.
  - **The inputs:** each top teammate's absence that game, times that teammate's share. In two parts:
    - a pooled part per pair of groups (how much a WR's share rises per unit of a missing WR's share, a TE's per missing WR, ...), learned across every team and the seasons up to s;
    - a pair part for each player and each top teammate in his own group, shrunk by the penalty.
  - **The forecast:** his with share plus the sum, over the departed players, of (pooled + pair) × that player's share.
- **Pass rule:**
  - **Held** if method 2's squared error beats 1a's, with a 90% team-bootstrap interval above 0.
  - **Failed** otherwise. A tie goes to 1a.
  - Reported per group, and for the skill groups apart from the lines.
- **Side bets (Claude):**
  - **Target and carry share too (30%):** the same methods, with target share (WR, TE, RB) and carry share (RB) as the targets.
  - **Weekly absences (50%):** in season, a top player is absent after playing 2+ earlier games. The target is a teammate's share that game. Method 1a uses his season-to-date share with the absent player plus a proportional split. Method 2 uses the pooled part fit on earlier seasons only (walk-forward), plus the pair part fit on this season's earlier games. Scored 2017–2024.

### H110: an injury's efficiency cost brings intake at that group (the CEO 30%; Claude 25%)

- **Rows:** team-season-group-top player, with 2+ games played and 2+ absences in season s.
- **His absence cost:**
  - **Efficiency:** his side's EPA per play in the games he played minus the games he missed (for the DL, EPA allowed the other way round), so a positive cost always means worse without him.
  - **The group's own outcome:** the OL's pressure rate allowed, missed minus played; the DL's pressure rate made, played minus missed.
- **Intake:** players new to T at that group in s + 1 who played for T, counted, and their share of the group's s + 1 snaps.
- **The model:** intake on the cost (standardized within group), with whether this top player left, his age, the number of the group's top players who left, and group dummies.
- **Pass rule:** **held** if the efficiency cost's coefficient on the intake count is above 0, with a 90% team-bootstrap interval above 0. **Failed** otherwise. The group-outcome version for OL and DL is reported beside it.
- **Contracts aren't in the tables,** so the brief's "beyond contracts" is left out of this look.
- **Side bet (85%):** the "he left" coefficient on intake is above 0, with its interval above 0.

### H111: roles' coordinates predict who receives the vacated targets and carries (the CEO 60%; Claude 55%)

- **Rows:** WR, TE and RB stayers on teams where a top WR, TE or RB departed, with roles' coordinates for both (season s).
- **The target:** his change in target share (and, as a second target, carry share), s to s + 1.
- **The vacated share:** V = the departed players' target (carry) share in s.
- **Models** (ridge, leave-one-season-out):
  - **P, position labels:** V, V × (he's in the departed player's group), group dummies;
  - **Z, roles' coordinates:** V, V × exp(−his role distance to the departed player), the distance, group dummies.
- **Pass rule:** **held** if Z beats P on both targets, each with a 90% team-bootstrap interval above 0. **Held in part** if one. **Failed** if neither.
- **Side bet (35%):** Z's terms still add to P plus his own s share and V × his share, on target share, with an interval above 0.

### H112: bringing in a top player against leaving the group empty (the CEO 30%; Claude 25%)

- **Rows:** team-season-groups with at least one departure.
- **"Brought in a top player":** a player new to T at that group is among T's top k at the group in s + 1. Otherwise the group is **left empty**.
- **Outcomes, s to s + 1:**
  - the change in the side's EPA per play (offense for WR, TE, RB and OL; minus EPA allowed for the DL, so up is better);
  - the group's own outcome (OL: minus pressure rate allowed; DL: pressure rate made).
- **Pass rule:** **held** if the mean efficiency change of teams that brought in a top player minus those that left it empty is above 0, with a 90% team-bootstrap interval above 0. **Failed** otherwise.
- **Side bets:**
  - the spread differs: the ratio of the two groups' standard deviations has an interval excluding 1 (20%);
  - the stayers' summed share gain at the group is smaller where a top player came in (90%).

### The backlog checked here

- **I49:** swap pairs say who inherits an absent player's snaps. H109's pair part tests it.
- **I122:** a shrunk vacancy forecast. H111's P and Z are a version of it for shares.

## Results (run 2026-11-24)

> Scripts and their outputs sit side by side in `explore/`: `vo_common.py` (the tables), `h109_plus_minus.py` (the noise ceiling and H109), `h110_h112_intake.py`, `h111_role_distance.py`, `i125_intake_split.py`. Every interval is a 90% team bootstrap (2,000 draws). Verdicts are by the pass rules above; **the CEO closes the hunches.**

**Go.** There's a clear signal, and it splits by cadence:
- **In season,** the CEO's plus-minus is the best forecast of who absorbs an absent player's snaps.
- **In the offseason,** what matters first is whether the team brought in a top player. Where it didn't, the plus-minus beats "no change" too.

### 0. The noise ceiling

- **A stayer's next share is very forecastable in principle:** split-half r of next season's snap share is 0.92 (WR), 0.95 (TE), 0.93 (RB), 0.78 (OL) and 0.92 (DL). That's 0.88–0.97 for a full season.
- **The shares move a lot, and the usual way doesn't explain the moves:**
  - A stayer's change in share, from his with share to next season, has an SD of 0.25 (2,616 stayers).
  - The proportional split's allocation explains only 0–8% of that change (r-squared, by group).
- **Team efficiency barely repeats:**
  - offense EPA per play, season to season: r 0.39, SD of the change 0.098;
  - defense: r 0.25, SD of the change 0.086.

  So a single non-QB's effect on a season's efficiency (H110, H112) sits in a lot of noise.
- **The plus-minus's fitting noise is small:**
  - In 40 team-bootstrap refits, its same-group pooled values never flip sign, and their 90% ranges are narrow (WR +0.15 to +0.17).
  - Its penalty chose the smallest value on the grid (1). The build should extend the grid.
- **Absences:** 2,737 games missed by top players between their first and last game, 2016–2024. Per top player-season: OL 1.0, RB 0.9, WR 0.7, TE 0.6, DL 0.5.

### H109: the plus-minus for all players: **held by its pass rule**, but the bar was weak

- **What the plus-minus learned.** This is the pooled part: how much a player's share rises per unit of an absent top teammate's share.

  | The absent top player's group | A same-group player's share rises |
  |---|---|
  | WR | +0.16 |
  | TE | +0.28 |
  | RB | +0.24 |
  | OL | +0.08 |
  | DL | +0.09 |

  Across groups it's about 0. When a top player sits, his group-mates absorb a sixth to a quarter of his share, and other groups absorb none. The rest goes to players who weren't playing before.
- **Offseason departures, against the proportional split (1a), the pre-registered test.** Lower squared error on next season's snap share:
  - all groups: **+31%** (90% +28% to +34%); skill groups +48%, the lines +25%; every group is clear.
  - So by its pass rule, **held**.
- **Against "no change"** (his with share; reported):
  - all groups +9.9% (+5.8% to +13.7%);
  - the lines +13.6%;
  - **the skill groups −6.7% (−16.7% to +3.0%): a tie, which no change wins.**

  The proportional split loses badly to no change: 31% worse overall, 104% worse for the skill groups. It hands the stayers the departed share, but the team usually brings someone in (72% of the time, H112).
- **With or without (1b):** +2.4% over 1a, close to nothing.
- **I49 (swap pairs):** the pair part adds +2.3% (+0.1% to +4.5%) to the pooled part. Small, but clear of 0.
- **Side bet, target and carry share (Claude 30%): held as worded, against 1a.**
  - target share: +40% against 1a; carry share (RB stayers): +33%.
  - Both lose to no change: targets −7.6% (−12.0% to −3.4%), carries −7.3% (−12.9% to −1.5%).
- **Side bet, weekly absences (Claude 50%): held, and the strongest result.**
  - **Setup:** walk-forward (the pooled part from earlier seasons, the pair part from this season's earlier games), 9,713 player-games, 2017–2024.
  - **Against 1a:** +24.5% (+22.5% to +26.7%).
  - **Against no change:** +31.3% (+28.8% to +34.0%).
  - **Skill groups:** +29.8% against 1a and +38.7% against no change.
  - **By group:** clear in all five.

### I125 (Claude's idea, odds first): the stayers' forecast hinges on intake: **held**

The idea: split H109's stayers by whether the team brought in a top player at the group.
- **With the flag read from next season** (a newcomer among the group's top; hindsight):
  - **the group left empty:** the plus-minus beats no change by +34.6% (+24.0% to +45.7%) on skill snap share;
  - **a top player brought in:** it loses by 60%.
- **With a flag known in the offseason** (a newcomer who was a top player at his group elsewhere last season, or a pick 1–64 rookie):
  - **the group left empty:** skill snap share +16.9% (+2.1% to +32.4%); target share +11.4% (+3.2% to +20.7%); the lines +13.6%;
  - **a top player brought in:** skill −25.5%, targets −11.3%; the lines +13.5%.
- The proportional split loses to no change in every cell.
- **Claude's odds were 55%, for a 5–15% gain.** The offseason-known size, 16.9%, is just above that range.

### H110: an absence's efficiency cost and next offseason's intake: **failed by its pass rule**

- **Rows:** 642 top player-seasons with 2+ games played and 2+ missed.
- **Newcomers per SD of the efficiency cost:** +0.05 (90% −0.09 to +0.18). Their share of the group's snaps: −0.001 (−0.016 to +0.014).
- **The lines' pressure cost** (reported): +0.12 newcomers (−0.05 to +0.28).
- **Why it can't work as measured:** the cost averages +0.013 EPA per play, with an SD of 0.13. With a median of 3 games missed, sampling noise alone gives an SD of about 0.13 (a game's EPA per play has an SD of 0.20). The measured cost is almost all noise, for us and for a front office.
- **Side bet (85%), he left: failed as specified.** +0.05 newcomers (−0.25 to +0.34), because the count of the group's departures carries it (+0.88 newcomers per departure).
  - Without the count (reported, added after the pre-registration), he left: +0.98 (+0.69 to +1.25).
  - That two of my own controls overlap is a design flaw in the pre-registration.

### H111: roles' coordinates against position labels for who receives: **failed by its pass rule**

- **Rows:** 987 WR, TE and RB stayers with coordinates, on teams where a top skill player left.
- **Z (role distance) against P (same position):**
  - target share change: −0.1% (−1.3% to +1.1%);
  - carry share change: −2.7% (−5.5% to 0.0%).
- **P itself doesn't beat the mean** on target share (−0.1%). The vacated share barely tells which stayer gains (r 0.05), while his own share's pull back toward the middle dominates (r −0.23).
- **Side bet (35%): failed** (−0.3%, −0.4% to −0.1%).
- **Why:** the vacated targets mostly go to newcomers (H112's side bet, I125). Who receives among the stayers is a small slice of the change.

### H112: bringing in a top player against leaving the group empty: **failed by its pass rule**

- **Rows:** 619 team-season-groups with a departure; 72% brought in a top player (OL 87%, RB and TE 56–57%).
- **Efficiency change, s to s + 1:**

  | | EPA per play |
  |---|---|
  | brought in a top player | +0.0065 |
  | left the group empty | −0.0030 |
  | difference | **+0.0095 (90% −0.0040 to +0.0237)** |

- **By group:**
  - **The skill groups lean positive:** WR +0.025 (−0.000 to +0.052), TE +0.035, RB +0.032, each interval just reaching 0.
  - **The OL leans negative:** −0.022 (−0.051 to +0.006).
  - **The DL:** about 0.
- **Controlling for last season's efficiency** (reported): −0.008 (−0.021 to +0.007).
- **The lines' pressure:** −0.005 (−0.015 to +0.005).
- **Side bet, the spread differs (20%): failed, narrowly.** The SD ratio is 0.92 (0.85 to 1.01).
- **Side bet, stayers grow less where a top player came in (90%): held.** The stayers' summed share gain is +0.05 against +0.32. The difference is −0.27 (−0.33 to −0.21).

### What it means

- **An analogy, diversion ratios.**
  - **In season,** an absence is a stock-out. The plus-minus measures where the demand goes, and it's mostly to group-mates, at a sixth to a quarter of the share.
  - **In the offseason,** the store restocks: a new product usually comes in. The stock-out ratios then apply only where nothing new came in (I125).
- **The CEO's plus-minus is the method to build, in two cadences (rule m):**
  - **`vacated-live`** (in season): the weekly result, the strongest.
  - **`vacated-offseason`:** gated on intake, known after free agency and the draft.
- **The usual proportional split shouldn't ship anywhere.** It loses to "no change" in every cell.

### The case against (short; the full one goes in RESULTS.md)

- **H109's pass rule compared against a weak bar.** Against no change, the skill-group offseason result is a tie.
- **I125's offseason flag is a proxy.**
  - It uses who played for the team in s + 1 to find the newcomers. The week 1 roster gives about the same set before the season, but that's not checked.
  - Contracts aren't in the tables.
- **The pair part is fit on the same season it's applied to** (by design, for the offseason). That is fine for a departure, which happens after the season, but it isn't walk-forward within season s.
- **H110's side-bet model overlapped,** as written above.
- **Stayers include marginal players.** Rows aren't weighted by snaps.

### Technical calls (for veto before any merge)

- **The groups and top k:** WR 2, TE 1, RB 1 (with FB), OL 5, DL 3. The roster's DL only, so edge rushers listed as LB are not in it.
- **An absence:** a team game between his first and last game for that team in which he had no snap.
- **Pressure:** pressure rate over dropbacks with the flag or a sack, a sack counted as a pressure (F34).
- **The plus-minus:**
  - fit on seasons up to s, demeaned within player-season;
  - the pooled and pair parts share one penalty, chosen on 2016;
  - forecasts clipped to [0, 1].
- **Role distance:** Euclidean over the 6 pooled coordinates, scaled by its median, before exp(−d).
- **I125's offseason intake flag:** a newcomer at the group who was a top player at his group elsewhere last season, or a pick 1–64 rookie.

### The backlog checked

- **I49 (swap pairs):** the pair part adds +2.3%, clear but small. Kept as the pair part.
- **I122 (a shrunk vacancy forecast):** H111's P and Z models were the shares version, and neither found signal among the stayers. I122 stays open for roles' newcomers.
- **I125:** new, held, and graduates to the brief.
- **I126:** new, open. H111 retried on the groups left empty.
