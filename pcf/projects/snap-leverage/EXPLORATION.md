# Exploration: Snap leverage (`snap-leverage`)

**Date:** 2026-11-14 · **Verdict:** GO, small (there is signal; the direction is the CEO's call) · **Brief:** [BRIEF.md](BRIEF.md) · **Scripts:** [explore/](explore/) (each writes a `.txt` beside it)

**The question.** Which players does each team put on the field when the game hangs on the snap, beyond how much they play overall, and does that show who the team relies on? The CEO's main test is future playing time; contracts and plus-minus are the secondary tests (2026-11-14).

**How it was measured.**
- **Leverage** (the CEO's "variance of winning percent added per play based on conditions/situations"): the spread of WPA a play's situation allows, before the snap. It comes from a gradient-boosted model of WPA² on the quarter, clock, score margin, down, distance, field position, both teams' timeouts and the win chance going in, fitted walk-forward: each season 2016–2024 is scored by a fit on 2006 to the season before ([leverage.py](explore/leverage.py)). The leverage index (li) is 1.0 for an average snap. **High stakes** = the top fifth of each season's plays (li ≥ 1.23).
- **Who was on the field:** nflverse participation (`player_play.on_field`), 2016–2024 regular season, every position. That is 178,565 player-games ([measures.py](explore/measures.py)).
- **Per player-game:**
  - **snap share;**
  - **leverage share:** each snap weighted by its leverage;
  - **high-stakes share;**
  - **trust gap:** high-stakes share minus snap share (raw: the situation is left in);
  - **trust over expected:** high-stakes snaps beyond what his on-field rate in each kind of situation predicts. The kind of situation is the offense's expected pass chance (pace's `pcf_xpass`), in fifths.
- **Scores:** walk-forward by season, with 90% intervals from resampling whole weeks (players for contracts). **The 2025 vault wasn't read.** nflverse's win chance and WPA are in-sample before 2020 (tag-tables#F4).

## Findings
Cite as `snap-leverage#F1`.

**F1. Leverage before the snap works** ([leverage.txt](explore/leverage.txt)).

| Held-out seasons 2016–2024 | Correlation with the play's actual swing (\|WPA\|) | Share of WPA² explained |
|---|---|---|
| Leverage | 0.54–0.58, every season | 9–21% |
| Rung 0: 4th quarter, one-score game | 0.22–0.26 | 2–3% |

- **It's calibrated:** in each tenth of plays, the predicted spread matches the actual one within about 10% (top tenth: 8.3 against 8.9 points of win chance).
- **The top fifth of plays holds 61% of all the swing.** These plays are 44% in the 4th quarter, 96% in one-score games and 76% passes. Rung 0 catches only 42% of them.

**F2. Clock-draining runs are rare among high-stakes plays.** A leading team's runs are 3.9% of them. Leading, trailing and tied offenses each run on about 23% of their high-stakes plays.

**F3. Leverage share is snap share, nearly.** Both repeat 0.88 week to week and 0.69 season to season.

**F4. The raw trust gap repeats, but it is mostly the passing-down role** ([measures.txt](explore/measures.txt), [sanity.txt](explore/sanity.txt)).
- **It repeats:** 0.61 week to week, 0.47 season to season.
- **It follows the passing downs:**
  - **plus:** WR +4.0 points, CB +4.9, S +3.4;
  - **minus:** TE −4.6, DL −3.7, RB −2.0.
- **The names show the role.** At the top: third-down backs (Perine, Ty Johnson), pass-catching tight ends (Pitts, Gesicki), pass rushers (Bosa, Autry), slot and dime backs. At the bottom: early-down run stoppers (John Jenkins), early-down backs (Henry, Hunt) and blocking tight ends (Josh Oliver).

**F5. Trust over expected (the situation taken out) is a weak trait.**
- **Overall:** 0.12 week to week (0.11 to 0.13) and 0.10 season to season.
- **By position:**
  - **strongest:** DL (0.22 / 0.22), LB (0.17 / 0.15) and RB (0.14 / 0.14);
  - **within a season only:** WR, TE, CB and S;
  - **noise:** OL and QB.
- **Raw and adjusted rankings** of part-timers correlate 0.62–0.77.
- **Its 2024 leaders make football sense:** rotating stars who stay on the field when it matters (Bosa, Quinnen Williams, Greenard, Van Ginkel), and veterans over rookies (Rachaad White over Bucky Irving).

**F6. The main test: next 3 games' snap share** ([playing_time.txt](explore/playing_time.txt)). Scored 2018–2024 on 173,595 rostered player-games. The plain model (last game, last 3, season to date) has a mean squared miss of 0.043; the table shows the share of it removed, 90% interval.

| Added to plain snap share | Trees: everyone | First-year players | Weeks 1–4 | Linear: everyone |
|---|---|---|---|---|
| Leverage share | **+0.14% (+0.06 to +0.23)** | +0.29% (+0.12 to +0.45) | +0.31% (+0.17 to +0.45) | +0.14% (+0.09 to +0.19) |
| High-stakes share | −0.04% (−0.12 to +0.04) | +0.02% | +0.02% | +0.07% (+0.05 to +0.10) |
| Trust gap (raw) | −0.08% (−0.16 to +0.01) | −0.05% | −0.13% | +0.08% (+0.05 to +0.12) |
| Trust over expected | −0.23% (−0.31 to −0.13) | −0.12% | −0.32% | +0.01% (−0.01 to +0.02) |
| All four | −0.07% (−0.22 to +0.06) | +0.12% | −0.05% | +0.17% (+0.10 to +0.23) |

- **Weighting snaps by leverage helps, by a hair.** Snaps in blowouts count less, so the share is a little cleaner. The gain is larger for first-year players and early in a season.
- **Who a team relies on beyond the situation doesn't predict playing time.** Trust over expected is noise to the trees.
- **Next season's snap share:** nothing helps (all four −0.54%, part-timers −1.10%).

**F7. Starters (H46): barely more of the high-stakes snaps, once the situation is out** ([starters.txt](explore/starters.txt)).
- **By snap-share band:** at the same snap share, starters minus non-starters, in trust over expected:
  - **plus:** +0.8 points at 10–30% share, +1.3 at 70–90%, +0.2 at 90%+;
  - **zero:** 30–70%.
- **Overall:** starters' high-stakes share is 0.772 against a snap share of 0.780.
- **By position, at 30–90% snap share:**
  - **plus:** QB +9.2 points (few games), DL +1.6, LB +1.4;
  - **minus:** RB −1.8 (the listed starter is often the early-down back);
  - **about zero:** WR, TE, OL, CB, S.
- **Raw, with the situation left in, starters at 30–70% look *less* trusted** (−5.7 points), because base-package players leave on passing downs.

**F8. Positions (H48)** ([positions.txt](explore/positions.txt)).
- **(a) Where the ball goes.** Every kind of play swings 2.2–2.6 times as much on high-stakes plays.

  | Kind of play | High-stakes swing (sd, points of win chance) |
  |---|---|
  | **Targets to WRs** | **8.1 (the most)** |
  | QB passes | 7.7 |
  | QB runs | 7.4 |
  | Targets to TEs | 7.2 |
  | Targets to RBs | 6.1 |
  | RB runs | 5.6 |

  Cornerbacks can't be read this way: free play-by-play has no coverage credit.
- **(b) Which player holds the spot.** Split-half ridge plus-minus, less a shuffled null.
  - **Barely above noise:** QB 0.10, RB 0.11 and LB 0.06 points of win chance per snap, on high-stakes plays.
  - **About noise:** WR 0.03.
  - **Below the null:** TE, OL, DL, CB and S.

  Which player holds a spot hardly shows in single plays' WPA: it is too noisy at this scale.

**F9. Schemes (H49).** Splitting offenses by pass rate over expected, no position's player spread differs beyond random splits of team-seasons, except RB at the edge (−0.22 against a null range of −0.20 to −0.12). One of five is about what chance gives.

**F10. Contracts (secondary)** ([secondary.txt](explore/secondary.txt)). Next veteran contract as a share of the cap, 2021–2024 (4,718 contracts). The plain model (snap share, games, age, draft pick, experience, position) correlates 0.76 with pay.
- **The raw trust gap adds +1.7% (+0.04 to +3.2), and +2.1% (+0.4 to +4.1) on contracts worth 1%+ of the cap.**
- **Trust over expected adds nothing:** −0.7% (−2.4 to +0.9).
- Leverage share: −0.8%. All four: −3.7% (overfit).
- **Within position,** the raw gap correlates most with what the plain model leaves over on DL (+0.21) and LB (+0.21): **the market pays for the passing-down role** (pass rushers), not for trust beyond it.

**F11. Plus-minus (secondary).** "Newly missing" means the player played 30%+ of his side's snaps in the previous game and none in this one (5,899 absences, 2017–2024). The side is scored against team-efficiency's champion forecast, which doesn't know the absence.
- **Snap share matters.** A full-time player newly out costs his side +0.021 EPA per play on offense (+0.015 to +0.027) and +0.014 on defense (+0.006 to +0.023).
- **Trust over expected, beyond that:**
  - **offense:** +0.040 per unit (−0.0005 to +0.079), about +0.004 EPA per play per sd. At the edge.
  - **defense:** +0.003 (−0.043 to +0.061).

## Hunch verdicts

| # | Verdict | Size | Claude's expectation, before testing |
|---|---|---|---|
| H45 | **unclear, small** | Weighting snaps by leverage: +0.14% next 3 games (+0.06 to +0.23), +0.3% for first-year players and weeks 1–4. Who a team relies on beyond the situation: no help for playing time (−0.23%, trees), none for next season. Contracts: the raw gap +1.7%, which is the passing-down role (F10). Plus-minus: offense at the edge (F11) | Right: small, larger where roles change |
| H46 | **unclear, small** | Starters +0.2 to +1.3 points of the high-stakes snaps in 3 of 5 bands, zero in the middle; DL +1.6, LB +1.4, RB −1.8 | Wrong: expected clearly held |
| H47 | **failed** | The situation is most of the raw measure. Clock-draining runs are 3.9% of high-stakes plays; the raw gap repeats at 0.61, the situation-free one at 0.12; the passing-down roles top the raw list | Partly wrong: expected it to matter only for specialists |
| H48 | **unclear** | Held for wide receivers where the ball goes (the largest high-stakes swing, 8.1 points); cornerbacks untestable that way and no player signal; which player holds a spot barely shows anywhere | Partly wrong: expected QB first; WR targets edge QB passes |
| H49 | **failed** (leaning) | 1 of 5 offensive positions at the edge of random splits (RB) | Right: unclear, small at most |

## What this changes in the brief
1. **Leverage per play is the most solid product.** It's calibrated and four to six times sharper than the simple 4th-quarter flag, so any project could use it (game script, kickers, a clutch lens).
2. **The raw trust gap is a role measure, not a trust measure.** It marks passing-down specialists, it repeats, and the market pays for it. It belongs with `roles-archetypes` and contract value.
3. **Trust over expected is real but weak** (0.12 week to week). It's best on the defensive front and running backs, and it predicts neither playing time nor contracts.
4. **The main test passes by a hair** (+0.14%), so playing time alone can't carry a full expert.
5. **Timing:** true participation is known only after the season. Live, the morning-after map gets about 1 in 10 offensive players and 1 in 6 defensive players wrong per play, which is more than the size of this signal.

## Options for the CEO (the direction)
- **A. A small expert:** leverage per play and leveraged usage per player-game (leverage share, the passing-down role gap, trust over expected), published as features for player opportunity, roles and contract value. Honest, but its main-test gain is +0.14%.
- **B. Fold it in, no separate expert:** leverage becomes a shared column on every play for any project; the passing-down role gap goes to `roles-archetypes`; trust over expected stays as a lens in the miss reports. Cheapest; nothing is lost.
- **C. Reshape the question** around what showed signal: who plays the money downs on the defensive front and at running back (F5, F7, F10), tested against pass-rush value and contracts.
- **Tempting but bad: retune "high stakes"** (top 10%, 4th quarter only, other cuts) until playing time improves. Each retry is a new chance at a lucky result, and the vault would pay for it.

## Technical calls (Claude's, listed for veto)
- High stakes = the top fifth of each season's plays by leverage (baseball's "high leverage" is about the top tenth; a fifth keeps about 12 such plays per team side per game).
- Leverage is the square root of a boosted model of WPA², fitted on 2006 to the season before; nflverse's WPA, in-sample before 2020.
- The kind of situation for trust over expected = the offense's expected pass chance in fifths, from the same game's plays.
- Position groups from participation's position labels; starter = first at his depth-chart spot that week.
- H48 (b) uses ridge plus-minus with alpha 200 and 150+ snaps per half, odd against even weeks, less a WPA shuffle within each offense's season.
- Plus-minus expectation = team-efficiency's champion forecast for the next 3 games, made before the game.
