# Results: the touchdown expert (`td-expert`)

**Date:** 2026-11-24 (built the same day) · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **Build plan and odds:** [BUILD.md](BUILD.md) (written before any result) · **MLflow experiment:** `td-expert` · **Decision:** [0043](../../docs/decisions/0043-td-expert.md) · **Reports:** `build/` (facts, walks, ideas, regression, one per harness run)

## In short
Touchdowns are now a table: every chance's expected touchdown (`play.xtd`, scrambles included), every drive's touchdown chance (`drive.td_chance`), and per player-game and team-game the sums, the luck measure and near misses. Six forecasts are built and validated: players' rushing and receiving touchdowns, a quarterback's thrown touchdowns and a team's touchdowns, each for next game and for the rest of the season, with the chance of at least one.

The headline is the brief's bet on method: **forecasting from chances (method A) is not better than forecasting from volume (method B)**. A ties B for players next game, beats it for thrown touchdowns next game (+0.19%), and loses everywhere over the rest of the season (players −1.25%, thrown −10.1%: whether he keeps playing is the story there, and volume knows it better). **Trees on B's inputs win for players next game** (+0.57% over B, +3.0% for QBs). **A quarterback's red-zone carries are the one red-zone input that pays** in the backtest (I58: +10.6% of the squared error on QBs' rest-of-season touchdowns), **but the vault reversed it** (2025: −5.1%). On the vault, every champion passes the leakage checks and its shuffled copies; A beat B for players next game (+0.46%), and trees tied both (R15). The team's ceiling is large (61% of next game's error knowing every red-zone trip's chance), but the market-free team forecast gets 6.5% of it. **After the CEO's answers (2026-11-24):** the game's opening line now feeds teams' next-game touchdowns (+1.6% of the squared error in the harness, +5.0% trained on kickoff lines; R17), a wider count makes players' rest-of-season chances calibrated (published only on the CEO's yes; R18), and the spot-check kept B for teams' rest of season.

**Champions** (`registry.yaml`):

| Forecast | Champion | Run (2016-2024) | Signal | Against rung 0 (season rate), Poisson log loss | Against the other method |
|---|---|---|---|---|---|
| Players, next game | `skill_next_volume_trees` | `7b6321a2…` | 20 of 20 | +3.5% (walk) | trees beat B +0.57% (+0.39 to +0.74), A +0.54% |
| Players, rest of season | `skill_rest_volume+qb_rz` | `756d21f9…` | 20 of 20 | +10.6% (walk) | B beats A +1.25%; + QBs' red-zone carries +0.37% (+0.30 to +0.45) |
| Thrown, next game | `thrown_next_chances` (A) | `63479e9a…` | 20 of 20 | +2.2% | A beats B +0.19% (+0.01 to +0.37) |
| Thrown, rest of season | `thrown_rest_volume` (B) | `eb589a2b…` | 20 of 20 | +37.9% | B beats A +10.1% |
| Teams, next game | `team_next_volume+line` (B + the opener, I118; the CEO, 2026-11-24) | `e26a1d97…` (2023-2024; 2016-2022: B's `1005eb29…`, the same model without an opener) | 20 of 20 | +0.89% (+0.32 to +1.47), 2023-2024 | beats B +0.24% (+0.03 to +0.45) on every 2023-2024 row; B beats A +0.19% (R17) |
| Teams, rest of season | `team_rest_volume` (B) | `fa0a9e01…` | 20 of 20 | +0.88% (+0.24 to +1.47) | tie (A −0.29%, −0.64 to +0.07): B ships, decision 0043 call 21 (for veto) |

**Vault (2025), opened once, 2026-11-24:** **all six champions pass all 10 leakage checks and beat 20 of 20 shuffled copies; five beat rung 0 clearly (teams next game ties it on 570 rows).** Two verdicts moved: players next game, A beat B (+0.46%, +0.08 to +0.85) and trees tied both; QBs' red-zone carries lost on 2025's QBs over the rest of the season (−5.1% of the log loss). Reported as they are; the champions stand (R15; decision 0043 call 24) · **Versions tried:** 24 variants (3 families × 2 horizons × 3 rungs, trees, 5 side variants), one recalibration fix and one ordering fix (decision 0043, calls 18-19), on 6 saved feature histories.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal | Every harness run beats its shuffled copies: 100 of 100 (the first players' run), 20 of 20 for every other (20-of-20 rule; decision 0043 call 20) |
| No noise (A at least as good as B) | Players next game: tie (+0.03%, −0.07 to +0.13); thrown next game: A better; every rest-of-season and teams next game: A worse; teams rest: tie. So A ships only for thrown next game (R4, R10, R11) |
| Beats baselines | Every champion beats rung 0 (the season rate) with its interval clear of 0 |
| Calibration and range | Next game, chance of 1+: players (the trees champion) error 0.42 points, slope 1.04; thrown 2.4, slope 1.04; teams 3.0, slope 1.15 (fails the slope). Chance of 2+: players 0.21 points, slope 0.92 (passes; B and A: slope 0.89); thrown 3.4 points, slope 0.86; teams 5.1 points (one game's touchdowns are less spread than a Poisson count: I119). Rest of season: the chances fail under a Poisson count (players' 1+ error 8 points, thrown 16; the season's total spreads wider: I116). The Poisson q10-q90 range is reported only (R6) |
| Leakage | All 10 checks pass for every champion (25 cutoffs). Check 8 caught an ordering bug in A's stage 1 (not a leak; fixed and tested; decision 0043 call 19) and check 1 an import in the build's own checks (fixed) |
| Football sanity | Claude's: 2024's highest next-game forecasts (8+ games, A's run): Saquon Barkley 0.90 touchdowns a game (scored 1.00), Kyren Williams 0.82 (0.94), Joe Mixon 0.70 (0.88), Jonathan Taylor 0.69 (0.86); QBs Jalen Hurts 0.49 (1.00), Josh Allen 0.43 (0.70); WRs Justin Jefferson 0.56 (0.56), CeeDee Lamb 0.55 (0.40); TEs Sam LaPorta 0.36 (0.47), Travis Kelce 0.34 (0.21) (R16). The CEO's review: ⟨pending⟩ |
| CEO spot-check | Teams' rest of season, B over A (the CEO's pick, 2026-11-24): B stays, by rules written first ("The spot-check" below) |

## Hunch verdicts
Copied into [`projects/HUNCHES.md`](../HUNCHES.md).

| # | Hunch | Verdict | Real? | Pays? |
|---|---|---|---|---|
| H67 | "touchdown allocation will be closely tied to scheme and play calling tendencies" | held in part (exploration); build: real, doesn't pay | Yes: the goal-to-go pass share is a team trait (0.30 week to week, 0.29 season to season) and the exploration found it shapes who scores | No: beside volume and the offense's quality, the calling adds −0.01% next game and −0.03% over the rest of the season; QBs +0.19% next game (R8) |
| H68 | "the combination of explosive play rate and red zone opportunities will be the strongest predictors of rest of season touchdown totals" | failed (exploration and build) | No for RB, WR, TE: red-zone chances are volume by another name | No: −0.02% beside volume (non-QBs). The exception is QBs' red-zone carries, +3.3% of the log loss (I58, R5, R9) |

## Terms
New ones in [GLOSSARY.md](../../docs/GLOSSARY.md): expected touchdowns (xtd), touchdowns over expected, the luck measure, the drive chance, the drive-aware hindsight, near miss, count forecast, Poisson log loss.

## Findings

**R1. The team's room is large, and the drive-aware hindsight measures it.** Regular season 2016-2024, 4,734 team-games (2.41 touchdowns a game, spread 1.39), share of squared error removed against the plain average (`build/facts.txt`, 3):

| Knowing | Next game | Rest of season (after weeks 4, 8, 12) |
|---|---|---|
| Where every drive started (the drive model at its first snap) | −6.8% | 49.2% |
| How many drives and red-zone trips (a straight line) | 27.5% | |
| **Each red-zone trip's chance at the 20, and every long touchdown (drive-aware)** | **60.8%** (dice left: 38.8%) | **89.4%** (dice left: 7.4%) |
| Every chance's expected touchdowns, summed (F21's, double counts) | 12.1% | 78.5% |

O1 (65%: 40%+ next game; expected 50% and 75%) held, larger than said; O2 (80%: the chance-sum is worse) held. Players with a chance, next game: knowing that game's chances removes 36.0% (dice 63%); QBs with 10+ throws, thrown touchdowns: 21.2% (dice 78%).

**R2. Expected touchdowns are calibrated, once scrambles count as carries.** 2016-2024 (fit on earlier seasons), 292,037 chances, 11,984 touchdowns against 11,658 expected: error 0.21 points by tenth, slope 1.03; log loss 0.101 against 0.247+ for 20 shuffled copies. RB, WR, TE targets slope 1.05, carries 1.03; QB carries (td-expert's own model) 0.88, 878 against 887; throws by passer 1.05. By season, touchdowns over expected run 0.99 to 1.08 (2018-2020 high). nflverse marks a scramble rush 0 and pass 1: without them 32 of 2023's 496 rushing touchdowns were missing (the pitfall below).

**R3. The drive model is honest, and near misses are a description.** At the first snap (54,730 drives) error 1.27 points, slope 0.97; at the first snap inside the 20 (16,510 drives, 30%), scored 56.2% against 53.6% said, slope 0.96. Field-goal drives came closest at 46.2% on average; those that reached the 20 at 54.8% (75% passed 50%); touchdown drives peaked at 61.2%. Near misses per game are noise (0.04 week to week); per field-goal drive, a state (0.11, 0.07). O19 (85%) held.

**R4. Players: volume forecasts touchdowns as well as chances do; trees do better.** Next game, 59,819 played player-games 2016-2024; share of squared error removed against the rows' own average: rate 9.3%, B 11.8%, A 11.7%, trees 12.1%. Poisson log loss: B beats rung 0 by 2.95% (+2.59 to +3.30); **A ties B, +0.03% (−0.07 to +0.13)**, worse for RBs (−0.37%), better for WRs (+0.19%) and TEs (+0.35%); **trees beat B by 0.57% (+0.39 to +0.74)** and A by 0.54%, most for QBs (+3.0%) and RBs (+1.1%). Rest of season (75,865 rows): rate 34.8%, B 44.5%, A 43.6%; **A loses to B by 1.25% (−1.49 to −1.03)**, every position and every season. O3 (60%) held (inside its ±0.2%); O4 (25%) failed as expected; O5 (55%) failed; O22 (35%: trees +0.3%) held. Likely reason: stage 1 forecasts next game's chances assuming he plays; over a season, whether he plays and keeps his role is most of the room (I60), and volume's playing-time inputs carry it.

**R5. A quarterback's red-zone carries forecast his rushing touchdowns (I58 held).** Beside B, QBs' rows: rest of season **+3.34% of the log loss (+2.66 to +3.97), +10.6% of the squared error (+7.2 to +13.7)**, everyone +0.37%; next game +0.92% (+0.42 to +1.42), +1.6% of the squared error. It is in the shipped rest-of-season forecast. O17 (70%: 2%+) held (rest of season; next game under the bar).

**R6. A Poisson count is right for one player's game after a recalibration; it is too narrow over a season and too wide for 2+ in a game.** The first run failed the chance of 1+ (1.55 points, slope 1.12): the Poisson regression's mean was too high at both ends and low in the middle. A recalibration of the mean on the latest 20% of the training window (decision 0043 call 18) fixed it: 0.26 points, slope 1.01 (O11, 85%, held; the trees champion 0.42, 1.04). The chance of 2+ stays slightly too sure for the Poisson regressions (slope 0.89 players, 0.86 thrown: O12, 65%, failed at 3.4 points; the trees champion passes at 0.92): one game's touchdowns are a sum of small chances, less spread than a Poisson (I119). Over the rest of the season the Poisson is too sure the other way (players' 1+ error 8 points, slope 0.79; thrown 16, 0.45): whether he plays spreads the total (I116). Publish the means there, not the chances.

**R7. Knowing the passer doesn't change a throw's expected touchdowns (I61 killed).** The passer's thrown touchdowns over expected per throw before this season (shrunk by 300 throws) and his offense's EPA per play beside the situation: +0.04% of the log loss per throw (164,099 throws). Past thrown touchdowns still add to the rest of the season beside the expected ones: +4.13% (−0.81 to +8.92) with the plain expected, +4.06% (−1.05 to +8.77) with the passer-aware (987 rows; a straight line, not the exploration's lasso and trees, which found +5.5%). O18 (50%) failed. The QB's keep is his, not his offense's in the throw's situation.

**R8. The calling near the goal line adds nothing beside volume (H67, build).** The offense's goal-to-go pass share and pass rate over expected, removed from B: −0.01% next game (−0.03 to +0.01), −0.03% rest of season (−0.06 to −0.01); QBs +0.19% next game, TEs −0.08%. O15 (30%) failed.

**R9. Red-zone chances add nothing beside volume (H68, build).** Inside-20 and inside-10 chances beside B, non-QBs, rest of season: −0.02% (−0.05 to −0.00); RB −0.06%, WR −0.04%, TE +0.05%. O16 (15%) failed as expected.

**R10. Thrown touchdowns: chances win next game, volume over the season.** Next game, 5,630 QB-games: rate 10.1%, B 13.9%, A 14.3%; **A beats B by 0.19% (+0.01 to +0.37)** (O6, 50%, held) and rung 0 by 2.2%. Rest of season: B removes 65.8%, A 59.2%; **B beats A by 10.1% (−12.0 to −8.4)**, 8 of 9 seasons: a QB's season is whether he keeps starting.

**R11. Teams: a market-free forecast gets a small part of the room.** Next game (4,952 team-games): rate 4.2%, B 6.5%, A 5.7%; B beats rung 0 by 0.60%, A loses to B by 0.19% (O7, 50%, failed). Rest of season: rate 77.3%, B and A 77.9% (the games left carry it); A ties B (−0.29%, −0.64 to +0.07; O8, 45%, held as a tie), B beats rung 0 by 0.88%. Against R1's 61% ceiling, 6.5% next game says the team's touchdowns need a better team input: the opening total is the obvious one (I118).

**R12. The regression measure: players keep about a tenth, and it doesn't beat keeping none clearly.** Tested seasons 2016-2024, each fit on the 6 season pairs before (`build/regression_backtest.txt`). Rushing and receiving (2,209 player-seasons with 30+ chances): kept share QB 0.01, RB 0.16, TE 0.10, WR 0.09; against keep-none +0.38% (−1.07 to +1.91), against keep-all +51.4%. Thrown (308 QB-seasons with 150+ throws): kept 0.17; against keep-none −1.01% (−4.90 to +2.29), keep-all +49.3%. Keeping all is badly wrong; between keeping none and a tenth the data can't tell. O13 (75%) and O14 (50%) failed. The forecast's own shrinkage (100 chances, 300 throws) is the same idea at a level the backtest prefers.

**R13. The luck measure: a player's season total over expected is almost pure dice.** Player-seasons with a dice spread over 0.7 (3,128): touchdowns over expected in dice spreads have a spread of 1.04 (pure dice 1.00); 5.1% beyond 2 (dice 5%). Luck is 75% of the spread in totals for players expecting 2 to 4 touchdowns, 72% for 4 to 7, 38% for 7+. QB-seasons' thrown touchdowns: 1.15, a little more than dice (the one place a skill shows). The average touchdown came on a chance worth 29%; 22% came on chances under 10%. Christian McCaffrey's 26 in 2023 (playoffs in) on 17.7 expected had a 1.7% chance.

**R14. Consistency** (`pcf.validation.consistency`; [CONSISTENCY.md](../CONSISTENCY.md)): expected touchdowns a game 0.55 week to week, 0.57 season to season (trait); touchdowns over expected 0.03 and 0.05 (QB, WR, TE noise; RB 0.06, weak); the luck measure noise; thrown touchdowns over expected per throw 0.15 and 0.11 (the one touchdown efficiency that repeats); team touchdowns over the hindsight 0.21 and 0.15 (finishing from the 20, a trait). O20 (85%) held.

**R15. The vault (2025).** Opened once, 2026-11-24, after the champions were final (`build/forecast_*_vault.txt`, `build/walks_*_vault.txt`, `build/regression_vault.txt`). Each champion's harness run on 2025: **all 10 leakage checks pass and every one beats 20 of 20 shuffled copies.** Against rung 0, five are clear (thrown next game −0.064 a row, −0.084 to −0.043; thrown and teams rest of season; players both horizons, walks: B +3.6% and +11.4% of the log loss); **teams next game ties rung 0** (−0.011, −0.030 to +0.009; 570 team-games). The verdicts, 2016-2024 against 2025 (share of the Poisson log loss; positive: the first one better):

| Comparison | 2016-2024 | 2025 (vault) |
|---|---|---|
| Players next game, A against B | tie, +0.03% | **A better, +0.46% (+0.08 to +0.85)**; QBs +1.7%, RBs +0.8%, WRs and TEs tie |
| Players next game, trees against B | +0.57% | tie, +0.27% (−0.29 to +0.81) |
| Players next game, trees against A (`build/trees_vs_chances.txt`) | +0.54% | tie, −0.19% (−0.76 to +0.35) |
| Players rest of season, A against B | B better, −1.25% | tie, −0.29% (−0.86 to +0.34); A better on the squared error (+4.2%): QBs and RBs A, WRs and TEs B |
| QBs rest of season, + red-zone carries (I58) | +3.34% (+10.6% of the squared error) | **worse, −5.05% (−6.61 to −3.48); −15.6% of the squared error** (1,372 rows, about 40 QBs) |
| QBs next game, + red-zone carries | +0.92% | tie, +0.57% (−1.65 to +2.68) |
| Thrown next game, A against B | A better, +0.19% | tie, +0.18% (−0.06 to +0.42) |
| Thrown rest of season, A against B | B better, −10.1% | B better, −8.5% |
| Teams next game, A against B | B better, −0.19% | tie, +0.14% |
| Teams rest of season, A against B | tie, −0.29% | **B better, −1.84% (−2.61 to −1.09)** |
| H68: red-zone chances, non-QBs, rest of season | −0.02% | +0.05% (+0.01 to +0.09) |
| H67: the calling, rest of season | −0.03% | −0.04% |

Calibration, the chance of 1+ next game: players (trees) error 1.05 points, slope 0.91, passes (A 0.41 points, slope 0.97); 2+ slope 0.87, just outside the bar (one game's 2+ again too sure: I119); QBs' thrown (A) 5.8 points, slope 1.22, **fails** (the recalibration held for players, not for one season of 658 QB-games); teams 1.1 points, slope 1.37, fails as in the backtest. The regression measure on 2025: kept shares RB 0.12, TE 0.10, WR 0.10, QB 0.00, thrown 0.21; against keeping none +3.5% (−0.6 to +7.4; RBs +10.7%, +0.9 to +18.2), thrown +9.5% (−7.5 to +22.4): leaning toward keeping a share, still not clear.

**O21 (70%) failed.** The shuffles held everywhere and rung 0 everywhere but teams next game; but two A-against-B verdicts moved (players next game to A, teams rest of season to B) and I58 reversed. **The champions stand, reported as they are** (docs/VALIDATION.md: a model changed after the vault is "vault spent", and the live 2026 ledger becomes its only test; decision 0043 call 24). How to read it: one season is about 40 starting QBs and 32 teams. The players' next-game rungs are within half a percent of each other on either sample, so the choice among them is close to a coin, and 2025 doesn't undo nine seasons. I58's reversal is the one large move (2025's QBs' red-zone carries didn't turn into the touchdowns they did before), and it is the first spot-check candidate.

**R16. Football sanity.** See the table above: the top of every list is the backs and quarterbacks who run near the goal line; tight ends top out at about a third of a touchdown a game. Over the season, 2024's highest rest-of-season forecasts made before week 9 (`skill_rest_volume+qb_rz`; Poisson q10-q90 in brackets): Kyren Williams 9.5 (6 to 14; scored 6), Jalen Hurts 7.3 (4 to 11; 7), Saquon Barkley 7.1 (4 to 11; 9), Bijan Robinson 6.1 (3 to 9; 10), D'Andre Swift 6.0 (3 to 9; 2), CeeDee Lamb 5.6 (2), Jahmyr Gibbs 5.5 (3 to 9; 13). Sensible names; the misses (Gibbs, Swift) are the season-long spread R6 says a Poisson understates.

**R17. The opening total for teams (I118; the CEO, 2026-11-24: "the open total market data can be used for the touchdown expert").** ESPN's opener (already in our data from the odds collection: no new source) is now a table part, `team_game.openers`, known at the start of the game's week + 2 days, before the Thursday and Saturday runs. History starts in 2023 (2022's ESPN files carry no openers). Two ways, both scored on 2023-2024's games with an opener:
- **Decision 0042's way** (`explore/i118_opener.txt`): earlier seasons train on the kickoff line (known long before any later fit), the forecast rows use the opener. Beside B, teams next game: **+5.0% of the squared error (+2.7 to +7.3), +1.15% of the log loss (+0.55 to +1.72)**; the kickoff line, the ceiling, +7.1%. Both seasons clear; 20 of 20 shuffled copies. I118's odds (75%: 3%+ of the squared error, interval clear) held.
- **The harness's way, what ships** (`team_next_volume+line`, run `e26a1d97…`, 2023-2024; `explore/i118_harness.txt`): each row sees only what was known at its own moment, so the line's weight is learned on opener rows only. All 10 leakage checks pass, 20 of 20 shuffled copies; against B on every row −0.0041 a row (−0.0077 to −0.0004). On the opener rows: **+1.6% of the squared error (+0.1 to +2.9), +0.31% of the log loss (+0.03 to +0.57)**. All of it is 2024 (+2.7%, +0.3 to +4.8): the model refits once a season, so 2023's fit had no opener rows to learn from. Live, the 2026 fit learns from 2023-2025's openers, so 2024 is the closer guide.
- **Players** (`explore/i118_players.txt`, the harness's way on the trees champion's features): a tie (+0.02%, −0.02 to +0.05; every position ties). Not shipped. Decision 0042's way gave +0.25% (+0.02 to +0.48), squared error a tie: the team's line is mostly in the players' forecasts already, through their team's inputs.
- **The vault is spent** for td-expert (R15), so **the live 2026 ledger is this input's only clean test.** Calibration of teams' chances of 1+ and 2+ next game still fails (error 4.2 and 10.8 points on the opener rows), as before: the mean is the product for teams.

**R18. A count wider than Poisson for the rest of the season (I116; the CEO: "we need to resolve the wider spread fits").** The champions' means stay as they are; only the spread around them changes (`explore/i116_spread.txt`). A negative binomial whose spread is fit on the seasons before each tested one (tested 2017-2024), judged on the chance of 1+ and of 2+ (bars: error 3 points, slope 0.9-1.1). The plain one (variance mean + α·mean²) overshoots long windows (players' 1+ slope 1.31 with 12+ games left), so the second look lets the spread grow more slowly with the mean (variance mean + α·mean^p, α and p fit per position and window length: games left 1-5, 6-11, 12+):

| Rest of season | Poisson | Negative binomial, by position | The slower spread, position × window |
|---|---|---|---|
| Players (67,328 windows) | 1+ error 8.1 points, slope 0.79; 2+ 3.1, 0.80 | 1+ 3.8, 1.05; 2+ 2.3, 1.09 | **1+ 1.7, slope 0.98; 2+ 1.6, slope 1.05: passes**; log loss +6.4% over Poisson |
| QBs' thrown (10,698) | 1+ 15.7, slope 0.45 | 1+ 7.8, 1.06 | 1+ 2.9, **slope 0.76: fails**; log loss +25% |
| Teams (4,222) | q10-q90 holds 73% | **q10-q90 holds 83%**; log loss +2.5% | the same (power runs to its bound: no gain) |

Players pass overall, and not in every slice: QBs' rushing 1+ slope 0.86, TEs' 2+ slope 1.14, windows with 12+ games left 2+ slope 1.17. QBs' thrown touchdowns don't fit any of these: the spread its fit wants runs to the bound (linear in the mean) and is still too narrow at the top and too wide at the bottom, the signature of a mixture (he keeps starting, or he doesn't: idea I120). For a team's season the chance of 1+ is near 100%, so the range is the readable test; the plain negative binomial brings it from 73% to 83%. I116's odds held for players (70%: 1+ under 3 points, slope 0.9-1.1) and failed for thrown touchdowns (45%). **Published where calibrated** (the CEO, 2026-11-24 (through the strategy chat): "Yes, where calibrated"; decision 0043 call 27). Every position × window cell was judged twice: the first look (`explore/i116_spread.txt`, the spread fit on earlier seasons' walks, 2017-2024) and the shipped model's own harness run (`explore/i116_published.txt`, the spread fit inside the model on the latest 20% of each training window, 2016-2024). A chance is published where it passed both; a 2+ only where its 1+ is. That leaves the last five games of the season (games left 1-5): RBs' and TEs' chances of 1+ and 2+, WRs' chance of 1+. RB 12+ passed the first look at the edge (slope 1.10) and failed the second (4.1 points, slope 0.85), so it was dropped. Average only: QBs' rushing, WRs' 2+, every window with 6+ games left (1+ off by 3 to 4.7 points, slopes up to 1.34), and QBs' thrown touchdowns. The shipped run (`0fdfa650…`, 2016-2024): all 10 checks, 20 of 20 shuffles; every row under its spread 1+ error 2.1 points, slope 0.94, 2+ 1.5, 1.01; the published chances (a quarter of the windows have a 1+, a seventh a 2+) 1+ 1.2 points, slope 0.92, 2+ 1.3, 0.93. The vault is spent here too: the 2026 ledger is the clean test.

## The ladder

| Rung | Method | Players next game (log loss vs rung below) | Takeaway carried forward |
|---|---|---|---|
| 0 | `rate`: touchdowns a game, this season and last, shrunk to the position's rate by 4 games, times the games | — | |
| 1 | `volume` (B): Poisson regression on yards, chances, snaps, past touchdowns, playing time (participation's inputs), the team and the opponent | +2.95% | Volume carries touchdowns (exploration F2); playing time first (participation) |
| 1 | `chances` (A): stage 1 next game's expected touchdowns by kind and zone; stage 2 corrections | tie with B (+0.03%) | The kind of chance adds nothing beyond its count (opportunity-quality F4), again |
| 3 | `volume_trees`: boosted trees, Poisson loss, B's inputs | +0.57% over B | QBs and RBs gain: the rushing side bends (I117 tries trees elsewhere) |

## Where it misses
Lens list 2026-11-15, the players' next-game champion (`skill_next_volume_trees`), 2016-2024 (average miss = actual − forecast, touchdowns a player-game; the average forecast is 0.20).

| Lens | Group | Rows | Average miss | 90% interval | Known | Idea |
|---|---|---|---|---|---|---|
| tag | big favorite | 3,809 | +0.030 | +0.012 to +0.047 | before | the line (I118): 15% more touchdowns than said |
| tag | trap game | 2,930 | +0.025 | +0.004 to +0.046 | before | |
| tag | backup QB starts | 9,138 | −0.019 | −0.028 to −0.011 | before | the QB's availability as an input |
| team change | QB changed in season, games 1-4 | 14,175 | −0.015 | −0.021 to −0.010 | before | as above (F5) |
| player change | rookie, weeks 1-4 | 2,189 | +0.013 | +0.002 to +0.023 | before | |
| position | QB | 6,058 | +0.012 | +0.004 to +0.019 | before | |
| depth | unlisted | 3,496 | −0.012 | −0.022 to −0.001 | before | |
| home | home | 29,980 | +0.011 | +0.005 to +0.016 | before | |
| team points (after) | 31+ | 13,484 | +0.129 | +0.125 to +0.134 | after | game script: the line |
| margin (after) | won by 14+ | 10,776 | +0.090 | +0.085 to +0.096 | after | |
| snap share (after) | under 25% | 17,716 | −0.052 | −0.055 to −0.050 | after | as any forecast made before the game |

The pattern: the forecast knows who the player is but not the game it's in. The betting lines (big favorites, then the after-game team points and margin) are the clearest missing input.

## The spot-check: teams' rest of season, B over A (R19)
The CEO picked candidate 3. The rules were written and committed before any number (`explore/spotcheck_team_rest.md`, commit 5d3453b); the numbers are in `explore/spotcheck_team_rest.txt` (2016-2024, the saved walks, 4,734 windows; Poisson log loss, positive: the first one better).

**What the brief says.** "Method A must do at least as well as ... method B ... where it doesn't, B ships." Read literally, a tie is A doing as well, so the brief's letter ships A. Decision 0043 call 21 shipped B on the tie because only B beats rung 0 clearly (rule k).

**The gaps.** Overall A ties B (−0.29%, −0.64 to +0.06). B beats rung 0 (+0.88%, +0.26 to +1.44); A doesn't clearly (+0.59%, −0.20 to +1.29). **By season the two trade places, by more than the overall gap:** B ahead in 2016 (−1.3%), 2018 (−2.6%), 2019 (−1.7%), 2020 (−1.8%) and 2024 (−0.4%); A ahead in 2017 (+2.4%), 2021 (+2.0%), 2022 (+0.3%) and 2023 (+0.3%). Most single seasons are clear one way. Per window, A is worse in 51% of them, and the net is small (0.009 a window). Both means are honest: said 20.9 touchdowns a window and scored 21.0 (B), 20.8 (A).

**Why volume wins where it does.** It isn't the players' "keeps playing" story: a team plays every game. It isn't a QB change either: **where the same QB starts every game of the window, B beats A by 0.65% (−1.10 to −0.22); where another QB starts some games, they tie** (+0.07%; a quarter or more of the games, +0.26%). B also wins the windows starting in weeks 7-12 (−0.54%) and 13+ (−0.27%), and the teams with a cold start (the bottom fifth of expected touchdowns a game so far, −0.44%); weeks 1-6 and hot starts tie. The reading: for a stable team, its yards and efficiency over the season (B) are a steadier guide to its touchdowns than its chances so far (A's stage 1: expected touchdowns, the hindsight, red-zone trips), which carry more of the dice of a few games. When the QB changes, both lose the same information.

**The verdict, by the rules written first:** B stays. A doesn't clearly beat rung 0 overall, and B is at least as good as A in 5 of the 9 seasons. The vault (2025) agreed (B better by 1.84%, −2.61 to −1.09). **Is shipping volume right?** Yes on the evidence: the difference is a season-to-season coin, and B is the simpler forecast and the only one that clears rung 0. The brief's letter points the other way. With the CEO's "no vetoes", B stands, and the rule's wording on a tie is a question for the next brief (below).

## The case against
1. **The rest-of-season and team chances aren't calibrated,** so the product for anytime-scorer chances is next game only (players and QBs), and even there the chance of 2+ is a little too sure. A user who reads a rest-of-season "chance of 10+ touchdowns" from a Poisson will be misled (R6).
2. **The recalibration is a fix found on the backtest.** It was added after the first run failed calibration, and every rung got it, so it can't favour one method; but it is a choice made after seeing 2016-2024. On the vault it held for players (the chance of 1+: 1.05 points, slope 0.91) and not for QBs' thrown touchdowns (5.8 points, slope 1.22; R15).
3. **A's loss over the season may be a design choice, not a verdict on chances.** Stage 1 assumes he plays; a stage 1 that forecast his chances including absences might close the gap. The brief's A was "chances, then corrections"; what lost is that A.
4. **The team forecast is weak** (6.5% next game) because it is market-free on purpose; anyone using it beside the betting total will find it adds little. The ceiling (R1) says the room is there.
5. **Most runs have 20 shuffled copies, not 100** (decision 0043 call 20): every champion beat all 20.
6. **The players' A runs were made before the ordering fix.** Their scorecards stand (check 8 passed); their reported comparisons come from walks after the fix (the same to 0.02%).
7. **The regression measure is a null result** in the backtest: 30+ chances and a kept share per position can't separate a tenth from nothing (R12).
8. **The vault moved the verdicts.** The players' next-game ladder (trees over B, B tied with A) didn't repeat on 2025: A beat B, and trees tied both. I58, the one input added to a champion, lost 5% on 2025's QBs. Nine seasons outweigh one, but the gains being shipped are fractions of a percent, and one season moved them by more than their size. The honest reading: for players next game, B, A and trees are interchangeable within about half a percent; I58 is unsettled (R15).

## Pitfalls
- **Scrambles are rush 0, pass 1 in nflverse.** A `rush == 1` filter drops them (32 of 2023's 496 rushing touchdowns); count any run with a rusher. Opportunity-quality's filter has the same trap, harmless there because it scores no QBs.
- **An unordered join before a positional split changes the fit.** `unique` and `join` don't keep order by default in Polars; a penalty picked on the "latest 20%" by position then moves between runs (leakage check 8 caught it).
- **A rest-of-season window over the schedule needs the schedule's games once:** the REG schedule has two rows per game (one per team), which doubled the windows until `unique`.
- **A Poisson regression extrapolates in log space:** its biggest forecasts overshoot. Recalibrate, or use trees.
- **An expert's package may not import the table builders** (leakage check 1), even analysis code: the build's checks carry their own small Poisson-binomial.

## Not looked at
- Method C (player and seat), as the CEO decided.
- Explosive-play rate in the build (the exploration's 0.0% beside volume stands).
- Playoff games as forecast targets (the facts include them; the forecasts are regular season next games and windows).
- Two-point conversions, defensive and return touchdowns.

## Could be improved
1. A spread that fits a rest-of-season total (I116) and one game's 2+ (I119).
2. Trees for the other forecasts (I117).
3. The opening total for teams (I118; a market input: the CEO's call).
4. A stage 1 that includes absences, then A against B again over the season.

## Don't redo
- Red-zone chances beside volume for RB, WR, TE: three looks (exploration F2-F4, H68's build, opportunity-quality F4), nothing.
- The calling beside volume and the offense (H67's build).
- A passer-aware throw model for thrown touchdowns' keep (I61).
- The chance-sum as the team ceiling (F21; R1).

## Interface card
Also in this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `play.pbp`, `play.xfp` (opportunity-quality's expected touchdowns), `drive.summary`; `player_game` parts roster, snaps, game_status, depth, injury, stats, opportunity, touchdowns; `team_game` touchdowns, efficiency, tendencies; the schedule for windows |
| **Outputs** | Facts: `play.xtd` (tdx_ columns: kind, player, position, passer, team, yard line, air yards, xtd, td, source), `drive.td_chance` (p_start, p_rz, p_peak, reached the 20, field-goal try, hindsight), `player_game.touchdowns` and `team_game.touchdowns` (counts, touchdowns and expected by kind and zone, thrown, dice spreads, luck z, the chance of at least that many; teams: drives, red-zone trips, the hindsight, near misses). Forecasts: `outputs/td-expert/<variant>/<run_id>/history.parquet`, quantities `td_rush_rec`, `td_thrown`, `td_team` (next game) and `*_rest` (rest of the regular season): the mean count, Poisson q10/q50/q90 |
| **Level of detail** | play; drive; player-game; team-game; forecasts per player (or team) and the game a window starts on |
| **Interval** | facts 2012 on (expected touchdowns; drive chances 2006 on); forecasts weekly, 2016-2024 reported plus the 2025 vault, every rostered QB, RB, WR, TE and every team |
| **Cadence** | in_season |
| **Known at** | facts with the play-by-play (kickoff + 1 day); forecasts at the Saturday run |
| **How to use it** | Next game: the mean and the chance of 1+ = 1 − exp(−mean) (calibrated for players and QBs); the chance of 2+ a little too sure (R6). Teams next game use the game's opener where there is one (R17). Rest of season: the mean; for players, `p_one` and `p_two` (the chances of 1+ and 2+ under the model's spread) where calibrated, the last five games of the season (games left 1-5): RBs' and TEs' chances of 1+ and 2+, WRs' chance of 1+, and null elsewhere (the CEO, 2026-11-24 (through the strategy chat): "Yes, where calibrated"; R18). The range comes from that spread Expected touchdowns a game as a feature (a trait); touchdowns over expected is noise except a QB's thrown (R14). The luck measure looking back only. From saved histories only (rule e) |
| **Feeds** | TD-scorer props, fantasy-projections, player-opportunity; candidates vacated-opportunity |

## The CEO's answers (2026-11-24)
The CEO, 2026-11-24 (through the strategy chat): "Please spot check the rest of season, 3. The yardstick should be market free but the open total market data can be used for the touchdown expert of course. The rest of season touchdowns should show the average only, but we need to resolve the wider spread fits. No vetoes."
- **No vetoes:** every call in decision 0043 stands, calls 21 (teams' rest of season ships B) and 24 (the champions stand after the vault, I58 in) among them.
- **The spot-check (3):** done; B stays ("The spot-check" above).
- **I118:** the opener may be used by td-expert (the yardstick stays market-free); built and shipped for teams next game (R17; decision 0043 call 25).
- **Rest of season:** the wider spread is resolved for players, not for QBs' thrown (R18; call 26). Then the CEO, 2026-11-24 (through the strategy chat): "Yes, where calibrated": the chances are published for the last five games of the season (games left 1-5): RBs' and TEs' chances of 1+ and 2+, WRs' chance of 1+, the average only elsewhere (call 27).

## Open questions for the CEO
1. **The brief's tie rule:** "at least as well" lets a tie ship the more complex method; the spot-check says a tie is a coin. Word it as "A ships only when it clearly beats B" in the next brief?

