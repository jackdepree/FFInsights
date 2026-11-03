# Brief: Participation and snaps (`participation`)

> PCF's first expert: how much each skill player will be on the field next game. Exploration: [EXPLORATION.md](EXPLORATION.md). **Key decisions D1–D8 are at the end of this page, each to approve or deny.**

**Status:** draft, for the CEO · **Layer:** 1, experts · **Cadence:** in_season

## The question
Before each game, what share of their team's offensive snaps will each rostered QB, RB, WR and TE play, and how likely are they to play at all?

## Why it matters
- **Playing time is the largest part of the fantasy misses no baseline predicts** (miss-lenses#F2: snap share explains up to 8% of the squared miss, more than any other lens).
- **Box-score models don't know it well,** and ECR does (F5). This expert is how PCF's own models catch up on playing time.
- **It's a building block:** vacated opportunity, opportunity quality, injury and fatigue, and the game simulator all start from who is on the field.

## Terms
- **Standard terms used:** snap share, walk-forward history, prediction moment, pinball loss, no-noise test ([`GLOSSARY.md`](../../docs/GLOSSARY.md)).
- **New terms:**
  - **Snap share:** offensive snaps played ÷ the team's offensive snaps in that game (`offense_pct`). 0 when inactive or never on the field.
  - **Active:** on the game-day active list. Known only about 90 minutes before kickoff, so the expert predicts it.
  - **Two-part prediction:** the probability of being active, times the share if active.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `miss-lenses` (F2, F3) | Playing time is the biggest unexplained part of the misses | The reason to build this first |
| `grain-tables` (F2) | `player_game` snaps (2013→), depth, injury, game status | The inputs and the outcome |
| `cleaning-port` (F17), `timeline` (F4, F5) | Snap counts mapped to `gsis_id`; injury reports' and daily charts' known-at | Honest timing |
| `baselines` | The lasso's fantasy points | The no-noise test's downstream target (D6) |
| `validation-harness` | Contract, gateway, scorecard | How it's built and judged |

**Already tried:** `old/` used participation (routes) after the fact, never a forward prediction of snaps.

## Assumptions
- **The injury report's last version before Saturday is what the expert sees.** The gateway enforces it from each report's `date_modified`.
- **Snap counts are complete:** every player who took an offensive snap has a row (grain-tables#F2).
- **The weekly depth chart (daily from 2025) is the team's stated plan,** imperfect but known before the game.

## Goals
1. A registered expert, `pcf.participation`, with a walk-forward history of share and probability of being active, 2016–2024.
2. It beats its shuffled self (signal) and doesn't hurt the lasso's fantasy points (no noise).
3. Honest ranges for a two-humped outcome.

## Tests
- **Success looks like:**
  - signal: beats 95 of 100 (or 20 of 20) shuffled refits;
  - no noise, downstream: the lasso's fantasy points with the expert's share is "neutral" or "adds value" (D6);
  - each rung beats the one below on pinball loss, or the ladder stops;
  - the probability of being active is calibrated within 3 points;
  - q10–q90 coverage 75–85% overall, 70–90% per position;
  - every blocking leakage check passes; in particular, nothing from the game-day active list.
- **Failure looks like:** no better than the last-3 average once the injury report is in.
- **Baselines (rung 0):** last game's share and the last-3-games average.
- **Seasons:** training from 2013 (snap counts), reported 2016–2024. The vault stays shut.

## Inputs and outputs
- **Inputs:** `player_game` roster, snaps (known the day after the game), depth (start of the week; daily from 2025), injury (each report's `date_modified`), tags (new team, rookie).
- **Outputs:** per rostered QB/RB/WR/TE and game: `p_active`, and the share as `mean`, `q10`, `q50`, `q90`, in the standard schema; walk-forward history and scorecard.

## How it will be used
As a feature for weekly fantasy points (the lasso's next rung, then products), for vacated opportunity (who absorbs an injured player's snaps), and in the game simulator later. Products read it from saved, versioned results (rule e).

## Plan
1. Rung 0: last game and last-3 averages, through the harness.
2. Rung 1: a lasso per position on Saturday's information.
3. Rung 2: boosted trees, if they beat rung 1.
4. Ranges, the active probability's calibration, the no-noise test on the lasso.
5. RESULTS.md, the miss report, the case against.

Time box: two sessions.

---

## Key decisions (approve or deny each)

**D1. What it predicts (yours): offensive snap share and the probability of being active, for every rostered QB, RB, WR and TE.**
- 0 for inactive players, so "will they play" and "how much" are one forecast.
- *Alternative:* only players expected to play. It's simpler, but injuries are exactly when playing time is uncertain, and that's the information products need.

**D2. It runs on Saturday (yours).** The injury report lifts the active prediction from AUC 0.81 to 0.92 and the share from about 0.66 to 0.72 of variance explained (F2, F3). ECR is also judged at Saturday.
- A Tuesday variant can be added later from the same code, if a product needs early numbers.
- *Alternative:* Tuesday, to be ready earlier in the week. It would give up most of the injury information.

**D3. Two-part output, with ranges from the mixture (technical).** A probability of being active, and the share if active, combined into `mean` and q10/q50/q90. Shares are two-humped (F4), so one average with a symmetric spread would misstate both.

**D4. The ladder (technical):** last-3 average → lasso per position → boosted trees. A rung that doesn't beat the one below stops the climb.

**D5. Inputs (technical):** snaps, depth charts, the injury report and teammates' reports, tags. **Not** the game-day active list (known 90 minutes before kickoff) and **not** play-level participation (routes: post-season only, rule m).

**D6. The no-noise target (yours): the lasso's weekly fantasy points at Saturday.**
- The exploration says it should help there (F5: 2.9% of the squared miss). Against ECR it would likely be "neutral" (0.6%), which passes but says little. The scorecard will report both.
- *Alternative:* ECR as the target, under your new rule. It's the stricter bar, but this expert's job is playing time, which ECR already knows.

**D7. Which rows count (technical).** Every rostered skill player is predicted, but scores are reported for players who played an offensive snap in their last 8 games, as well as overall. Otherwise third QBs and call-ups, who are easy zeros, flatter the score (F6).

**D8. Rejected (✗):** use the game-day active list as an input. It would make the forecast look far better, but it's known only 90 minutes before kickoff, after every weekly run.
