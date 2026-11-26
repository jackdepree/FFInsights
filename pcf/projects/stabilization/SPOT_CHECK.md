# Spot-check: the second pull (stabilization)

**The CEO's pick (2026-11-26):** "Please spot check the second pull, then you may merge." The odds were written in [decision 0052](../../docs/decisions/0052-stabilization-build.md) ("The CEO's answers") before any of this ran. The checks are scratch scripts run on the build's own frames, with corrected run snaps (call 36) and the trend shipped (call 35). Gains are shares of the rung below's squared error, weighted by next season's attempts, with 90% intervals from 2,000 player resamples, as in `build/players.txt`.

**In one line:** the second pull is fit only on earlier seasons, its slope barely moves from season to season, and its gain is real for 11 of 20 player rates next season. It ships alone for 5 of them. For most of the rest the ridge's own weight on M1 already does its job. It does nothing in season, because there the next 4 games' noise swamps it. Dropping it would cost 1% to 2% for three rates (scramble, completion over expected, catch rate allowed), and catch rate allowed and 5 team sides would fall back to the average.

## What it is

M1 pulls a player's rate toward his position's mean by k: (n × rate + k × mean) / (n + k). Rates are kept as gaps from the position's mean, so M1 = reliability × his gap. The second pull multiplies that gap by one more number, a slope b:

forecast = b × M1, with b = Σ w·M1·y / Σ w·M1², a weighted least-squares slope through the origin.

Here y is next season's gap and w is next season's attempts. `pcf.validation.stabilize.second_pull` fits b separately for each target season t, **on the pairs whose target is before t only** (`walk_slopes`; at least `MIN_PAIRS` pairs, or no forecast). A slope below 1 means one season's reliability overstates next season's: part of what was real about him this season doesn't carry over (role changes, aging, a new team).

## 1. Is it known before each season?

**Yes, and tested two ways.**
- **The build's leakage check:** every measure's outcomes from the target season on were scrambled, and the targets' forecasts (pull included) didn't move: 0 of 750 differ (`build/leakage.txt`).
- **This spot-check:** every outcome from 2021 on was shuffled and the slopes refit. The forecasts for 2018-2021 were unchanged for 20 of 20 rates.

The only inputs are M1 (from seasons before the target) and earlier targets' outcomes.

## 2. How steady is it, season by season?

The slope each target season used (fit on the seasons before it), and the pull's gain over M1 that season:

| Rate | Slopes 2018 → 2024 | The pull's gain over M1 by season (%) |
|---|---|---|
| targets a route | 0.82, 0.83, 0.84, 0.84, 0.84, 0.85, 0.85 | +3.2, +0.7, +3.9, +1.6, +0.1, +1.4, +4.8 |
| yards a route | 0.81, 0.83, 0.83, 0.83, 0.83, 0.83, 0.85 | −0.3, +1.3, +3.2, +2.1, +1.3, −2.1, +4.9 |
| aDOT | 0.84, 0.84, 0.84, 0.83, 0.82, 0.81, 0.81 | +2.2, +2.7, +3.4, +7.0, +5.0, +3.5, −1.1 |
| carries a run snap | 0.89, 0.88, 0.88, 0.87, 0.87, 0.87, 0.88 | +5.2, +5.0, +7.1, +5.8, +5.8, +0.7, +5.7 |
| broken tackles a touch | –, –, 0.49, 0.50, 0.55, 0.54, 0.50 | +4.8, +0.4, +3.6, +5.2, +7.3 |
| scramble rate | 0.97, 0.97, 0.95, 0.95, 0.94, 0.95, 0.94 | −0.4, +3.1, +0.8, +1.8, −2.3, +1.7, +2.3 |
| QB aDOT | 0.62, 0.61, 0.62, 0.60, 0.61, 0.61, 0.60 | +8.5, +2.8, +13.4, +0.2, +4.1, +15.7, −4.9 |
| completion over expected | 0.91, 0.90, 0.88, 0.87, 0.87, 0.85, 0.84 | +0.7, +3.5, +2.0, +0.6, +4.2, +1.4, −1.5 |
| targets a coverage snap | –, –, 0.92, 0.93, 0.93, 0.91, 0.90 | +0.7, +0.6, +2.0, +2.2, +1.5 |
| catch rate allowed | –, –, 1.01, 0.69, 0.81, 0.71, 0.66 | −0.0, −0.7, +1.1, +1.9, +1.4 |
| aDOT allowed | –, –, 0.67, 0.61, 0.57, 0.58, 0.60 | +7.4, +8.6, +5.1, +2.7, +2.6 |

(The PFR rates, the ones with dashes, start in 2018, so their first slope is for 2020.)

- **The slopes are nearly constant.** For 10 of these 11 rates, every season's slope sits within 0.1 of its 2024 value, most within 0.03. The exception is **catch rate allowed**: its first slope was fit on one season of pairs (1.01, then 0.66-0.81).
- **The two slopes that drift both drift down:** completion over expected 0.91 → 0.84, and aDOT 0.84 → 0.81. As seasons pile up, both rates carry over a little less.
- **The gain season by season** is positive in 6 or 7 of 7 seasons for targets a route, aDOT, carries a run snap, QB aDOT and completion over expected. It's positive in 5 of 5 for broken tackles, targets a coverage snap and aDOT allowed, and in 5 of 7 for yards a route and scramble rate. Catch rate allowed is positive in 3 of 5.
- **The rates it doesn't help** have unsteady slopes:
  - yards after contact: 1.33 for 2020, from few pairs, then 0.61-0.76;
  - pressured rate: 0.23, then 0.60-0.67;
  - YAC over expected: 0.81-0.88, with a gain below zero in 4 of 7 seasons;
  - missed tackles: 0.86-1.07;
  - hit-or-sack and sack rate: steady slopes, but gains that swing both ways.

## 3. Which rates carry it, and by how much

These are the 11 rates where the pull clears M1, next season, 2018-2024. "Hindsight" is one slope fit on the scored pairs themselves: the most a constant slope could have done. "One slope 0.85" uses the same number for every rate.

| Rate | Ships now | Pull vs M1 (90%) | Hindsight slope (gain) | Share of the hindsight gain the real pull got | One slope 0.85 for all | M1 vs the average |
|---|---|---|---|---|---|---|
| carries a run snap | trend | **+5.1%** (+2.5 to +7.2) | 0.87 (+5.2%) | 98% | +5.1% | +68.1% |
| QB aDOT | pull | **+5.8%** (+0.5 to +10.4) | 0.62 (+5.9%) | 98% | +3.7% | +8.6% (−5.6 to +21.4): a tie |
| aDOT allowed | pull | **+5.4%** (+2.9 to +7.7) | 0.60 (+5.6%) | 97% | +3.4% | +8.0% |
| broken tackles a touch | average | +4.5% (+1.7 to +7.1) | 0.44 (+4.6%) | 97% | +2.1% | −1.6%: a tie, so the average ships |
| aDOT | trend | +3.4% (+1.8 to +4.8) | 0.79 (+3.5%) | 95% | +3.2% | +31.7% |
| targets a route | trend | +2.3% (+1.1 to +3.5) | 0.86 (+2.4%) | 96% | +2.4% | +46.5% |
| yards a route | trend | +1.5% (+0.3 to +2.7) | 0.85 (+1.7%) | 91% | +1.7% | +36.0% |
| completion over expected | pull | +1.4% (+0.3 to +2.5) | 0.72 (+2.3%) | 63% | +1.8% | +11.0% |
| targets a coverage snap | trend | +1.4% (+0.8 to +2.0) | 0.90 (+1.5%) | 95% | +1.1% | +52.4% |
| scramble rate | pull | +1.0% (+0.1 to +1.8) | 0.89 (+1.8%) | 56% | +1.5% | +53.7% |
| catch rate allowed | pull | +0.7% (+0.1 to +1.2) | 0.60 (+1.2%) | 59% | +0.7% | +1.9% (−0.3 to +4.0): a tie |

- **Three rates carry most of it:** QB aDOT, aDOT allowed and carries a run snap, each about +5%. Those three slopes sit furthest from 1 (0.60, 0.60, 0.88) or rest on the most attempts. Broken tackles has a slope of 0.5 and gains as much, but M1 itself ties the average there, so the average ships.
- **Walk-forward costs almost nothing:** for 8 of 11 rates, the real pull gets 91%-98% of what a slope fit in hindsight would have got. The three that get less (scramble, completion over expected, catch rate allowed) are the ones whose slopes drifted or started on few pairs.
- **One slope for every rate isn't enough:** a flat 0.85 matches the per-rate slope where the true slope is near 0.85. It gives up a third or more where the slope is near 0.6 (QB aDOT +3.7 vs +5.8, aDOT allowed +3.4 vs +5.4, broken tackles +2.1 vs +4.5). So the pull is a per-rate fact.
- **Against shuffles:** every rate the pull ships for beats all 19 shuffled copies as the champion (best copy at most +1.0%, for QB aDOT; `build/players.txt`). Where the pull ships, it wins 6 or 7 of 7 seasons against the average, 5 of 5 for aDOT allowed and 4 of 5 for catch rate allowed.

## 4. Why it doesn't help in season

In season the pull clears M1 for only 2 of 20 rates: aDOT +0.7% (+0.2 to +1.2) and carries a run snap +0.6% (+0.3 to +0.9). It's clearly worse for scramble rate (−1.7%) and catch over expected (−1.0%). Two reasons:

1. **The target is noisy.** In season the target is the next 4 games' rate, a few dozen attempts. Most of M1's error there is the next 4 games' own dice, which no slope can remove. Next season, the target is a whole season's rate, so the part a slope can fix (how much of his gap carries over) is a bigger share of the error.
2. **There's little to fix, and it moves.** Fit at games 4, 8 and 12, the in-season slopes sit near 1 for the usage rates: targets a route 0.92-0.99, carries a run snap 0.97-0.99, targets a coverage snap 0.97-0.99. Within a season, his talent hasn't had time to drift, and k already sets the right pull. Where the slopes do differ from 1, they change by checkpoint and fall on both sides of it:
   - catch over expected: 0.96, 1.40, 1.66 at games 4, 8, 12;
   - pressured rate: 0.51 → 1.35;
   - missed tackles: 0.86 → 1.35.

   A slope that changes that much is noise, so a walk-forward slope from earlier seasons can't predict it. The in-season gains come from the filter, which lets the level drift (F125).

## 5. What changes if it's dropped

The ladder was rerun with the pull removed, so the ridge is compared with M1 directly. The table lists only the rates whose forecast would change:

| Rate | Ships now | Without the pull | Without vs now |
|---|---|---|---|
| scramble rate | pull | M1 | −1.0% (−1.8 to −0.1) |
| completion over expected | pull | M1 | −1.5% (−2.6 to −0.3) |
| catch rate allowed | pull | **the average** (M1 vs average +1.9%, −0.3 to +4.0: a tie) | −2.1% (−4.1 to −0.1) |
| QB aDOT | pull | the ridge (vs M1 +8.1%, +2.5 to +13.4) | +2.5% (−0.0 to +4.9): a tie |
| aDOT allowed | pull | the trend (vs M1 +4.3% for the ridge, then +1.6%) | +0.5% (−1.5 to +2.4): a tie |
| Team sides: offense's hit-or-sack, no-huddle, success, aDOT; defense's explosive rate allowed | pull | **the average** (M1 ties it for all 5; teams have no ridge) | not scored; the pull's gains there are +2.5% to +11% |

- **The 10 rates that ship the trend wouldn't change.** The ridge and the trend fit their own weight on M1, and that weight plays the pull's role. The pull is the rung they had to clear, not part of their forecast.
- **Three player rates would lose 1% to 2%**, and catch rate allowed would fall back to the average.
- **For QB aDOT and aDOT allowed,** the pull is what keeps the simpler forecast in place. The ridge ties the pull, so rule k ships the pull. Against M1 the ridge clears, so it would ship instead, for no real gain.
- **Teams lean on it most:** 5 of the 7 team sides that beat the average next season do so only through the pull.

## The odds, scored

| Bet (written first) | Odds | Result | Verdict |
|---|---|---|---|
| Each test season's slope within 0.1 of 2024's, for 8+ of the 11 | 55% | 10 of 11 (catch rate allowed's first slope 1.01) | **held** |
| The pull beats M1 in 6+ of 7 test seasons, for 6+ of the 11 | 50% | 5 of 11 at 6+ of 7. With the PFR rates' 5 of 5 counted as every season, 8 | **failed** on the wording |
| The walk-forward slope gets 70%+ of the hindsight gain, for 8+ of the 11 | 60% | 8 of 11 (91%-98%; scramble 56%, completion over expected 63%, catch rate allowed 59%) | **held**, exactly at the line |
| In season, the slopes sit within 0.95-1.05 for most rates | 70% | No: the usage rates are near 1, but most rates fall outside, at 0.5-0.9 at game 4 and up to 1.66 later | **failed** |
| Dropping it turns 2+ shipped next-season rates into ties with the average | 50% | 6: catch rate allowed and 5 team sides. For player rates alone, 1 (QB aDOT's place goes to the ridge, not the average) | **held** (for players alone it would have failed) |

**What would change the answer:**
- If the 2026 slopes moved by more than 0.1 for the rates where the pull ships, the walk-forward fit would be chasing noise, and M1 alone would be the safer base.
- If the pull's gain on 2026 came out below zero for QB aDOT and aDOT allowed, the two biggest gains it ships alone, the pull would be pulled back to M1 there.

## The verdict

The second pull stays as built. It's leak-free, steady, and nearly as good as hindsight for the rates where it ships. Its gain is small but real (+0.7% to +5.8%). It belongs next season only, which is where it ships. Nothing in this check changes a shipped rung.

**One thing it taught the build:** the pull is also what sets the bar for the ridge. Against the pull, the ridge ties for QB aDOT and aDOT allowed. Against M1, it would have looked like a win.
