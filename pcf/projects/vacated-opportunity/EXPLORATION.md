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

## Results

*Not yet run.*
