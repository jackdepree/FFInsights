# Exploration: Schemes v2 (`schemes-v2`)

**Status:** in progress, 2026-11-08. Parts 1–4 of the plan done (part 4: matchups on margins, H9, and morphs, H13), plus a first look at H14. Still to do: game states (H11, diagnosis); scheme fit for receivers, then QBs (H12, I22–I24). Discovery only: nothing here counts as proof, and the vault (2025) wasn't read.

**Scripts:**
- [`explore/tendencies.py`](explore/tendencies.py): builds the team-game tendency table, then consistency, whose it is, coach movers and how fast tendencies settle.
- [`explore/conditions.py`](explore/conditions.py): H14.
- [`explore/margins.py`](explore/margins.py): H9 on margins.
- [`explore/morphs.py`](explore/morphs.py): H13.
- [`explore/cycles.py`](explore/cycles.py): the first look at H9 (in the brief).

## In short
1. **v1's tendencies were real; its last step wasn't.** v1's own numbers show its tendencies repeating (r 0.35–0.74). It found nothing because it looked for discrete clusters of single games, with a few broken "expected" models on the way (F1).
2. **Almost every tendency is a team trait.** 18 of 19 repeat within and across seasons. Shotgun use, no-huddle, personnel and tempo repeat most (0.77–0.92 between halves of a season). 4th-down aggressiveness per game is noise (F2).
3. **Tendencies fall into three families: the head coach's, the QB's, and the team's (F3, F4):**
   - The head coach's: shotgun, no-huddle, tempo, personnel and coverage shells. They stay when the QB changes and carry to the coach's new team.
   - The QB's: scrambling and efficiency.
   - The team's: outside-run share, which stays whatever changes (possibly a charting artefact).
   - This is the first look at H10, for head coaches only: it supports it.
4. **On its own, a scheme isn't alpha, as H14 says (F6).**
   - Raw tendencies do go with EPA: shotgun +0.025 EPA per play per standard deviation. That's talent.
   - Beyond team strength they mostly vanish. Shotgun is the exception: +0.008, about half a point a game.
5. **Scheme against scheme: only a faint signal so far (F7, F8).**
   - No single offense × defense pair beats the null for testing 77 pairs.
   - All pairs together, fitted on some seasons and tested on others, predict the residual at r +0.028. Shuffled opponents get there 2.5% of the time. Real, maybe, but tiny.
   - Clusters show nothing.
6. **Tendencies settle within 1–2 games; efficiency takes 6+ (F5).**
7. **Style pairings against the close's margin: a faint signal, at the edge of chance (F9, H9).**
   - The pairings fitted on other seasons predict the margin's miss against the close at r +0.035. Shuffled opponents get there 5% of the time.
   - About 0.4 points per standard deviation; no cover edge (48% against 46% between the extreme fifths).
   - Settling it needs about 7,000 games; we have 4,018.
8. **Teams do bend against opposing styles, but all the same way (F10, F11, H13).**
   - The average bend is real and football-sensible in 22 of 98 pairs: defenses put fewer in the box and blitz less against pass-heavy offenses, and offenses throw deeper against man.
   - A head coach's own bend, beyond the average, doesn't repeat: no more pairs than chance (5 of 98), in seasons or in games.
   - The test would have seen own bends of about a third of the largest average bend.
9. **The cluster version shows nothing either (F12).** A game sits in its own regime's usual cluster only 47% of the time, so game-level clusters are mostly noise, as in v1.

## Data and definitions
- **Team-games:**
  - 9,853 team-games, 2006–2024 regular season, from play-by-play.
  - Participation adds personnel, box and blitz from 2016, and man/zone and shells from 2018 (it has no coverage before 2018).
  - Participation is published after the season only, so these tendencies are retrospective (rule m).
- **Neutral situations:** win chance 20–80%, downs 1–3, not the last two minutes of a half.
- **Against what's expected:** shotgun, no-huddle and box count are each taken against the league's rate for that season, down and distance (box count by formation too). Pass rate over expected uses nflverse's `xpass`.
- **Against the season:** every tendency and outcome is taken against its league mean that season, so league trends don't pass for consistency. This matters: before the change, 4th-down aggressiveness looked like a trait (0.31 season to season), purely from the league-wide rise.
- **Tempo:** game seconds from an in-bounds run to the next snap on the same drive. The clock runs then, so the gap is huddle and play-clock use.
- **Regimes (the CEO's rule):**
  - A regime is the same head coach and the same starting QB (the QB with the most dropbacks).
  - A QB change counts only if the new QB starts two games in a row, so 309 one-game fill-ins stay inside their regime.
  - 815 regimes: median 6 games, 40% of them 8 or more.
  - Without the fill-in rule there were 1,321 regimes, 27% of them one game long.

## Findings

**F1. Why v1 found little** (read from `old/code/Schemes_Model.ipynb`, read-only):
- **The tendencies were consistent.** v1's own checks show it:
  - over-expectation features against the same coach's next 30 games: r 0.35–0.74;
  - between-coach variance at 0.1–1.1 of within-coach variance.
- **What failed was the last step.** PCA and clustering ran on one row per coach-game. Single games are noisy, and styles are blends (the dialects analogy), so there were no clusters to find:
  - silhouette 0.08 offense and 0.09 defense (Ward);
  - silhouette −0.01 and −0.02 (Gaussian mixture).
- **Some "expected" models were broken:**
  - Shotgun's expectation model had shotgun among its inputs, and no-huddle's had no-huddle, so the expected value equalled the actual (0.99998 or 0.0001) and "over expected" was about zero by construction.
  - Category tendencies were taken against the single most likely category instead of its probability.
  - The models were fitted and predicted on the same rows.
  - Pass rate over expected had its sign reversed.
- **Offense and defense were mixed:** the offense's columns included box count and man coverage over expected, which are what the defense did.
- **The coach was never separated from the roster** (no movers), and v1 used only even seasons, with a 75% sample of plays.
- **It never asked what a scheme does:** no link to EPA, margins or matchups.
- **Lesson kept:** simple rates against league expectations, no requirement for discrete clusters, then test whose a tendency is and what it does.

**F2. Consistency** (`pcf.validation.consistency`, team-seasons; split-half within regimes of 8+ games):

| Tendency | Side | Week r (90% low) | Season r | Split-half in a regime | Verdict |
|---|---|---|---|---|---|
| Shotgun over expected | O | 0.92 (0.91) | 0.62 | 0.92 | trait |
| Personnel: 11 (1 RB, 1 TE) | O | 0.90 (0.88) | 0.50 | 0.86 | trait |
| Personnel: heavy (RB + TE ≥ 3) | O | 0.91 (0.89) | 0.48 | 0.89 | trait |
| No-huddle over expected | O | 0.88 (0.87) | 0.52 | 0.93 | trait |
| Tempo | O | 0.77 (0.74) | 0.53 | 0.77 | trait |
| Pass rate over expected | O | 0.63 (0.59) | 0.40 | 0.62 | trait |
| QB scramble rate | O | 0.62 (0.58) | 0.46 | 0.69 | trait |
| Outside-run share | O | 0.59 (0.55) | 0.59 | 0.64 | trait |
| Middle-of-field pass share | O | 0.41 (0.35) | 0.39 | 0.35 | trait |
| Air yards per attempt (aDOT) | O | 0.34 (0.28) | 0.30 | 0.35 | trait |
| Deep pass rate (20+ air yards) | O | 0.27 (0.21) | 0.23 | 0.32 | trait |
| 4th-and-short go rate, midfield | O | 0.01 (−0.06) | 0.06 | 0.00 | noise |
| Man coverage rate (2018+) | D | 0.73 (0.67) | 0.49 | 0.72 | trait |
| Box count over expected | D | 0.72 (0.67) | 0.48 | 0.68 | trait |
| Two-high shell rate (2018+) | D | 0.71 (0.65) | 0.48 | 0.67 | trait |
| Blitz rate (5+ rushers) | D | 0.64 (0.58) | 0.45 | 0.52 | trait |
| Pass rate over expected faced | D | 0.24 (0.17) | 0.24 | 0.14 | trait |
| aDOT faced | D | 0.17 (0.10) | 0.24 | 0.22 | trait |
| Pressure rate (sack or hit) | D | 0.10 (0.03) | 0.24 | 0.14 | trait |

For comparison, offensive EPA per play is 0.60 and 0.43; defensive EPA allowed is 0.29 and 0.27.
- **The offense chooses; the defense mostly reacts.** Offensive choices repeat far more than anything a defense "allows". Defensive *choices* (man, shells, blitz, box) repeat as much as offensive ones.
- **4th-down aggressiveness:** at a few plays a game it can't show per game. It may still be a coach trait over a season.

**F3. Whose is it: season-to-season r, split by what changed between the two seasons** (team-season means; pairs of seasons in brackets):

| Tendency | Nothing changed (294) | New QB only (148) | New coach only (64) | Both new (70) | Reads as |
|---|---|---|---|---|---|
| Shotgun over expected | 0.78 | 0.59 | 0.32 | 0.15 | coach (some QB) |
| No-huddle over expected | 0.67 | 0.71 | 0.53 | 0.00 | coach |
| Tempo | 0.70 | 0.58 | 0.39 | −0.11 | coach |
| Personnel 11 (2016+) | 0.62 | 0.56 | 0.13 | −0.08 | coach |
| Personnel heavy (2016+) | 0.58 | 0.63 | 0.11 | −0.21 | coach |
| Man rate (2018+) | 0.55 | 0.69 | 0.12 | −0.15 | coach |
| Two-high rate (2018+) | 0.69 | 0.55 | 0.20 | −0.33 | coach |
| Blitz rate (2016+) | 0.42 | 0.61 | 0.20 | 0.54 | coach, or the roster |
| Pass rate over expected | 0.53 | 0.26 | 0.32 | −0.03 | both |
| Middle-of-field share | 0.53 | 0.33 | 0.17 | 0.01 | coach, partly |
| aDOT | 0.42 | 0.29 | 0.26 | −0.08 | both |
| QB scramble rate | 0.66 | 0.16 | 0.54 | 0.10 | **QB** (sanity check passed) |
| Offensive EPA per play | 0.47 | 0.19 | 0.50 | −0.16 | **QB** |
| Offensive success rate | 0.49 | 0.21 | 0.48 | −0.03 | **QB** |
| Outside-run share | 0.55 | 0.67 | 0.59 | 0.62 | **team** |
| Box over expected | 0.47 | 0.50 | 0.57 | 0.40 | team |

- **Scrambling** follows the QB and nothing else, as it must: the design works.
- **Efficiency follows the QB, not the coach.** This matches the CEO's "personnel performance" in H12.
- **Outside-run share stays with the team** even when the coach and QB both change (0.62). Run gaps are charted by each stadium's stat crew, so this may be a home-scorer artefact rather than football. To check: home games against away games.
- **Intervals are wide:** with 64 pairs, r 0.32 has a 90% interval of about 0.12 to 0.50.

**F4. Head coaches who change teams** (27 moves, a different team within 4 seasons): the new team's first season against the coach's last season elsewhere, and against the new team's previous season.

| Tendency | r with the coach's old team | r with the new team's last season |
|---|---|---|
| No-huddle over expected | 0.78 | −0.01 |
| Shotgun over expected | 0.67 | 0.15 |
| Pass rate over expected | 0.34 | −0.03 |
| Personnel 11 (9 moves) | 0.74 | 0.14 |
| Box over expected (9) | 0.76 | 0.30 |
| Pressure rate | 0.45 | 0.10 |
| aDOT faced | 0.49 | 0.15 |
| Tempo | 0.46 | 0.53 |
| aDOT | −0.23 | 0.24 |
| Offensive EPA | −0.01 | 0.09 |

- The coach brings shotgun use, no-huddle, pass rate over expected and personnel to the new team. That is H10's "scheme".
- Pass depth comes from neither: likely the new QB.
- Efficiency comes from neither.
- **Small numbers:** r 0.67 on 27 moves has a 90% interval of about 0.44 to 0.82.

**F5. How fast tendencies settle in a new regime (I25)** (regimes of 10+ games): r between the first k games' mean and the rest of the regime's mean.

| | k=1 | k=2 | k=4 | k=8 |
|---|---|---|---|---|
| Shotgun over expected | 0.68 | 0.72 | 0.77 | 0.83 |
| No-huddle over expected | 0.66 | 0.74 | 0.81 | 0.76 |
| Man rate | 0.48 | 0.55 | 0.63 | 0.60 |
| Tempo | 0.42 | 0.47 | 0.56 | 0.60 |
| Pass rate over expected | 0.30 | 0.34 | 0.48 | 0.51 |
| Offensive EPA | 0.18 | 0.36 | 0.44 | 0.53 |

- The clearest tendencies are at 80–90% of their eventual level after one or two games. Efficiency is at a third after one game.
- Pass rate over expected and aDOT settle not much faster than efficiency.
- **I25 partly holds:** for formation, no-huddle and coverage, yes.

**F6. H14, schemes on their own** (8,036 offense-against-defense sides, weeks 4+). Each tendency is known before the game: its mean over earlier games in the same regime. "Beyond strength" is the game's EPA per play less what both teams' season-to-date EPA (shrunk to last season) expects. Units: EPA per play per standard deviation of the tendency.

| Tendency | Raw EPA (t) | Beyond strength (t) |
|---|---|---|
| Shotgun over expected | +0.025 (10.3) | **+0.008 (3.7)** |
| Pass rate over expected | +0.019 (8.0) | +0.005 (2.0) |
| Outside-run share | +0.013 (5.3) | +0.002 (0.8) |
| Middle-of-field share | +0.012 (5.0) | +0.003 (1.2) |
| Pressure rate (D) | −0.012 (−4.8) | −0.003 (−1.4) |
| Pass rate over expected faced (D) | −0.010 (−4.2) | −0.006 (−2.6) |
| Blitz rate (D) | −0.011 (−3.1) | −0.008 (−2.3) |
| Every other tendency | within ±0.007 | within ±0.006, \|t\| ≤ 1.7 |

- **Talent shows up raw;** most of it goes once strength is in.
- **Shotgun survives:** a standard deviation more shotgun than the situation expects beats strength by 0.008 EPA a play, about half a point a game.
  - It may be real (shotgun suits modern passing, or shows a coach who adapts).
  - Or the strength measure lags: shotgun-heavy teams improving faster than season-to-date EPA catches.
- **For H14:** schemes alone are close to noise, as predicted, with one or two exceptions.

**F7. H14, scheme against scheme** (77 offense × defense tendency pairs: the product term on the residual, with both main effects in):
- **No single pair beats chance.**
  - The largest |t| is 2.7 (outside-run share × man rate).
  - With shuffled opponents (each offense gets a random defense from the same week), the largest |t| among 77 pairs reaches 3.4 one time in 20.
  - The top pairs are football-plausible but within chance: heavy personnel × two-high (+), 11 personnel × box (+), shotgun × blitz (−).
- **Together, held out, there's a whisper.** All 77 terms fitted on even seasons predict odd seasons, and the reverse.
  - The summed prediction correlates +0.028 with the residual.
  - Shuffled opponents reach that 2.5% of the time (200 shuffles).
  - Size: 0.08% of game EPA's variance. Small, but a matchup term only has to beat the close by a little.

**F8. H14 with clusters, the CEO's framing** (k-means, 6 offense × 6 defense clusters; 2,034 sides, 2018–2024 with every tendency):
- Offense cluster alone explains 0.25% of the residual's variance; shuffled clusters do better 39% of the time.
- Defense cluster alone: 0.35%; shuffled clusters do better 24% of the time.
- The offense × defense interaction beyond both: 0.96%, *below* the shuffled median (1.18%).
- **Nothing.** 36 cells of about 55 sides each can only show a large effect.
- **Here continuous tendencies beat clusters,** as the dialects analogy expects: blends, not categories. Clusters haven't earned their place (rule k).

**F9. H9, style pairings on margins** ([`explore/margins.py`](explore/margins.py), 4,018 games, weeks 4+, 2006–2024). Each game's matchup term is the home offense's summed offense × defense prediction less the away offense's. It comes from F7's 77 pairs, fitted on the other half of the seasons, with every tendency known before the game.

| Against | Games | r with the margin's miss | Shuffled opponents at or above |
|---|---|---|---|
| The close (result less `spread_line`) | 4,018 | +0.029 | 5.5% |
| The close, both sides with 3+ earlier regime games | 2,713 | +0.035 | 5.0% |
| Elo's validated margin (2016–2024) | 1,935 | +0.032 | 11.0% |
| The close, 2006–2017 (play-by-play tendencies) | 2,500 | +0.037 | 3.5% |
| The close, 2018–2024 (with coverage) | 1,518 | +0.026 | 17.0% |

- **Size:** one standard deviation of the term is about 0.4 points of margin.
  - The fifth of games where it favours home most: home beats the close by +0.56 points on average. The fifth where it favours away most: −0.53.
  - Cover rates are 48% and 46%: no betting edge at this size.
- **Power:** an r of 0.03 needs about 7,000 games to show reliably (80% power); we have 4,018. The faint signal is the right size to be real and the wrong size to prove here.
- **Coverage data doesn't help:** the seasons with coverage (2018–2024) are no stronger than those without.
- **H9's circles:** circles are rarer than chance (brief) and their games closer. A term this small couldn't make circles common, consistent with the first look.

**F10. H13, the average bend (ordinary opponent adjustment)** ([`explore/morphs.py`](explore/morphs.py), 7,518 team-games in regimes of 6+ games):
- The morph is a game's tendency less the team's own normal: the mean of its *other* games in the regime.
- The condition is the opponent's normal on the other side of the ball.
- **22 of 98 pairs bend clearly (|t| > 3).** In sd of the game's deviation per sd of the opponent's tendency:
  - defenses put fewer in the box against pass-heavy offenses (−0.28), more against heavy personnel (+0.22) and fewer against 11 personnel (−0.19);
  - they blitz less against pass-heavy offenses (−0.14) and play more two-high against them (+0.12);
  - offenses throw deeper against man (+0.09 aDOT, +0.06 deep rate) and against defenses that give up depth (+0.08);
  - offenses pass more against blitz-heavy and box-heavy defenses (+0.08, +0.07).
- That is the usual way: every team bends, and a model can know it from the two teams' tendencies.

**F11. H13, a coach's own bend** (the CEO's hunch: team A morphs *its own way*, and does it again):
- **The test:** after the average bend, each head coach's own slope against the condition, measured in even seasons and in odd seasons separately, then correlated across coaches.
- **Nothing:**
  - The mean split r across the 98 pairs is +0.005. Shuffled opponents give +0.004 (95th +0.039).
  - 5 of 98 pairs beat their own null's 95th; 5 are expected by chance.
  - Splitting by even and odd games instead: 6 of 98.
- **Could it have seen one?** Planting made-up coach slopes into one typical pair (pass rate over expected against the opponent's man rate) raises its split r:
  - from +0.10 to +0.17 at sd 0.05;
  - to +0.32 at sd 0.10, reaching that pair's null 95th of +0.36 at about sd 0.12;
  - to +0.49 at sd 0.15.
  - Pooled over 98 pairs, the test would see own bends of about sd 0.05.
  - So coaches' own bends are smaller than about a fifth to a third of the largest average bends, if they exist.
- **Limitation:** the head coach is the unit. Defensive game plans belong to defensive coordinators, who aren't in our data yet; the coordinator table is where H13 could still hold.

**F12. H13 with clusters, the CEO's framing** (2018–2024, 2,841 team-games; 6 offense clusters from game-level tendencies, 6 defense clusters from opponents' normals):
- **A game sits in its regime's usual cluster only 47% of the time.** Game-level cluster labels are mostly noise, the same problem v1 had.
- **The off-cluster rate barely moves with the opponent's cluster:** 50% to 56%.
- **A coach's off-cluster rate against a given defense cluster** (beyond the average for that cluster), even games against odd: r +0.13 over 163 coach × cluster cells. Shuffled opponents reach that 65% of the time: nothing.

## Hunch verdicts so far (first looks)
- **H10:** supported for head coaches (F3, F4). Shotgun, no-huddle, tempo, personnel and coverage follow the coach; scrambling and efficiency follow the QB. Stays **open** until coordinators and player movers are in.
- **H14:** the first half holds: schemes alone are near zero beyond strength, except shotgun (F6). The second half is a whisper at most: held-out r +0.028, 2.5% by chance; clusters show nothing (F7, F8). **Unclear** for now. The margins test (with H9) decides.
- **I25:** partly holds (F5).
- **H9:** **unclear.** Style pairings predict the margin's miss against the close at r +0.035, 5% by chance, about 0.4 points per sd. The direction is right; the data is too small to settle it (F9).
- **H13:** **failed for head coaches** in its team-specific form (F11, F12). Teams bend against opposing styles, but all the same way (F10). Coordinators are untested: if morphs are game plans, they belong to coordinators.
- **H11, H12:** not yet tested.

## Pitfalls found
- **League trends pass for consistency** unless every tendency is taken against its season mean (4th-down rate: 0.31 → 0.06).
- **One-game fill-in QBs** split regimes into single games (27% before the rule).
- **The starting QB by most dropbacks** is known only after the game. `game.pregame` has the listed starters (`home_qb_id`, `away_qb_id`), known before kickoff, which is better for anything live.
- **Participation has no man/zone or coverage shell before 2018.**
- **Run gaps may be charted differently by stadium crew** (F3).

## Next
1. **Game states (H11, diagnosis):** do pass rate over expected and tempo predict how teams do when trailing at halftime, beyond the win-probability model?
2. **Scheme fit (H12): receivers first, then QBs.**
   - Receivers who change teams: their target depth × the new offense's depth before they arrived, with prior efficiency, age and the new QB partialled out, against placebo moves (I23).
   - Then QBs against coverage (I22) and the learning curve (I24).
3. **Small checks:**
   - the outside-run artefact (home against away);
   - shotgun's main effect against a strength measure that adapts faster.
4. **For later, with more data:** H9's faint signal could be settled by adding 2025+ seasons live (the ledger) rather than more tries on 2006–2024, which would spend the same data again.
5. **The coordinator table** (signed off in principle) is the place to retest H13: game plans are a coordinator's.

If regimes keep finding little, the CEO's fallback is high season-to-season player turnover as a boundary.
