# Results: availability (`availability`)

**Date:** 2026-11-25 (built 2026-11-24 to 25, in one build session; the CEO's review the same day) · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **Build plan and odds:** [BUILD.md](BUILD.md) (written before any result) · **The review's odds:** [REVIEW.md](REVIEW.md) (written before any of its results) · **Decision:** [0047](../../docs/decisions/0047-availability-build.md) · **MLflow experiment:** `availability` · **Reports:** `build/` (`compare.txt`, `games_played_rest_chain.txt`, `yardstick_rest_chain.txt`, `team_rest_chain.txt`, `measures.txt`, `sanity.txt`, one `forecast_<variant>.txt` per harness run)

## In short
Availability now forecasts who plays. A **weekly health-state chain** (method 2) is the champion for the next 3 games and the rest of the season, and it beats both method 1 (two models) and the hidden health state. Composed with each player's rate of playing when healthy, it gives **games played for any reason**, which beats I60's crude forecast by **23.3% of the squared error (20.7 to 26.0)** with the healthy rate fit on his record (I129, after the CEO's review; 14.4% with the first, shrunk rate), in every season 2019-2024, with a range that holds 81.0% (8.8% below q10: participation#F14's problem fixed). On the yardstick, beside I60's crude forecast and participation, it adds **+0.60% to rushing yards** and **+0.23% to receiving yards** over the rest of the season (both beat their 19 shuffled copies); nothing for passing. The team output (snap-weighted adjusted games lost) repeats a little (season r 0.22) and tracks the change in net EPA per play (r −0.21). Its forecast's +5.1% to team yards beside Elo **didn't survive the CEO's spot-check**: it is one season, 2021, and without 2021 it ties (+0.40%, −1.19 to +1.90; R8, R12).

Two of the brief's five tests failed: availability's next-game chance he's active **ties** participation's `active` (−0.57%, −1.98 to +0.78), and its kept share **ties** participation's share (−1.09%). By the brief's tie rule, participation keeps both. The premise that `active` overstates Out and Doubtful players twofold (participation#F12) didn't reproduce on 2017-2024's rows: it says 3.2% and 3.9% played.

**Champions** (`registry.yaml`; histories in `outputs/availability/<variant>/<run_id>/`):

| Forecast | Champion | Run | Signal | Against the rung below |
|---|---|---|---|---|
| Next game, chance of a health absence (the 53) | `next_logit` (method 1, the plain logistic) | `83fd8f38…` | 100 of 100 | +6.18% of the log loss over the status-by-body-part table (+5.37 to +6.97); ties the lasso (+0.14%) and trees (−0.63%) |
| Next 3 games, games of health absence (the 53 and reserve lists) | `next3_chain` (method 2) | `efc698b2…` | 20 of 20 | +3.55% of the range score over method 1 (+3.02 to +4.10), +5.08% over the table |
| Rest of season, games of health absence | `rest_chain` (method 2) | `ad99d09b…` | 20 of 20 | +5.59% over method 1 (+3.95 to +7.56), +3.53% over the table (+2.89 to +4.14) |
| Rest of season, games played (any reason) | the composite (`games.py`: the fitted healthy rate, `walk_healthy`, × `rest_chain`'s share not absent) | from `ad99d09b…`'s history | | +23.27% of I60's squared error (+20.74 to +25.96); +10.37% over the first, shrunk-rate composite (+9.65 to +11.06) |
| Team: snap-weighted adjusted games lost, to date and forecast | `measures.agl`, `agl_forecast` on `rest_chain` | | | a description (R7); the forecast beside Elo ties without 2021 (R8, R12) |

**Vault (2025): closed** (the CEO, 2026-11-25, in the build session: "Keep it closed, actually"). The CEO first approved opening it, relayed by the build chat; this session's permission check asked for the yes in the build session, and the CEO then chose to keep it closed. The odds and pass rules stay committed, unscored ([REVIEW.md](REVIEW.md) §1). The 2026 live ledger is the unseen-season test. **Versions tried:** 20 variants walked, 3 through the harness; after the review, 2 more walks (I130's tempered chains) and one more games-played composite (I129).

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal | `next_logit` beats 100 of 100 shuffled refits; `next3_chain` and `rest_chain` 20 of 20 (the chains' null shuffles the health record with the outcome: decision 0047 call 25) |
| No noise / beats baselines | Every champion beats its rung 0 with the interval clear (above). Ties went to the simpler side (rule k): participation's `active` and share over availability's; the plain logistic over the lasso and trees |
| Calibration and range | Next game: error 0.24 points (bar 3); slope 0.82 on every row (bar 0.9-1.1: fails), 0.97 on listed players. The slope is pulled down by the 90% of rows that are unlisted at one tiny rate. Horizons: the chance of any health absence, error 0.60 points, slope 0.87 (next 3), 2.22 points, 0.85 (rest): both a little overconfident, failing the slope bar; the health count's q10-q90 holds 94.2% (next 3) and 91.3% (rest), which is what a calibrated whole-number count with a spike at 0 shows (above q90 4.8% and 7.3%, inside the 10% a calibrated forecast allows; R16). Games played: 81.0%, with 8.8% below q10 and 10.2% above q90 |
| Leakage | All 10 checks pass for all three champions (25 cutoffs). The first `next_logit` run failed check 1 on the build's own cache reads in `checks.py` (not a leak; routed through `backtest.load_features`, decision 0047 call 24) |
| Football sanity | Claude's (`build/sanity.txt`): 2024's week-9 run puts Out players with soft-tissue and hamstring injuries at the top (Tee Higgins, Dallas Goedert, Mike Evans: 3.5 to 4.2 of 9 games expected; they missed 2 to 5). No healthy player has a q90 of 0 games over a rest of season. The most-hurt teams match the press: Denver 2022 (146), Houston 2023 (177). The CEO's review is pending |
| CEO spot-check | R8, the team gain beside Elo (2026-11-25): **didn't hold**. One season carries it (R12) |

## Hunch verdicts
No hunch was open at the build: the CEO closed H93-H98 at the exploration (H96 as failed, 2026-11-24). The build's findings bear on two of them:
- **H93** (two parts, the chance of injury and the time missed given one): as a forecasting method it lost. Method 1 loses to the plain table over the rest of the season (−2.17%) and to the chain over both horizons. The football claim (time missed is mostly the report) held at the exploration (62% of the error), and the build's winner is the one that reads the report week by week.
- **H94** (some injuries repeat): proneness repeats season to season, r 0.27 (0.25 to 0.29) for 300+ snap players, but on the yardstick it adds only +0.04% to receiving and costs rushing (I121, killed).

## Terms
- **Health absence:** a game with no snap while on that game's injury report (any status, or a limited or no-practice day) or on a reserve list for injury, illness or non-football injury (`RES`, `PUP`, `RSN`). No snap while unlisted, and off every roster, are participation's.
- **Listed:** on the report with a game status, or a limited or no-practice day.
- **The health states:** healthy, listed (Questionable or no status), out (Out or Doubtful), reserve, off (no roster that week).
- **Games played (any reason), availability's:** his rate of playing when healthy, (games played + 3.6) / (games not health-absent + 4), times the share of the window he isn't health-absent.
- **Snap-weighted adjusted games lost (AGL):** per team-game and side, the sum of its players' health absences, each weighted by his snap share on his side in his earlier games that season (else last season's, else his position's).
- **Kept share (when playing hurt):** a listed player's offensive snap share when he plays. Not opportunity-quality's kept share, which is the share of a gap that lasts.

## Findings
| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 | **Next game's health absence is the report, read with his history.** A logistic on the report, his history, proneness and exposure beats the status-by-body-part table by 6.18% of the log loss (+5.37 to +6.97), 9.6% on listed rows. Unlisted players are absent 0.24% of the time. The lasso ties the plain logistic (+0.14%), and trees tie the lasso (−0.63%) | `build/compare.txt` | strong | every position, 2017-2024 |
| R2 | **A weekly health-state chain is the best horizon model.** It beats method 1 by 3.55% (next 3) and 5.59% (rest) of the range score, and the table by 5.08% and 3.53%. The hidden health state loses to the chain (−10.05%, −2.64%), and trees on the chain's moves lose too (−1.21%, −3.18%). Method 1 loses to the table over the rest of the season (−2.17%) | `build/compare.txt` | strong | the 53 and reserve lists, 2017-2024 |
| R3 | **Availability doesn't improve participation's chance he's active.** The stack (participation's log-odds beside the report) ties `active` (−0.57%, −1.98 to +0.78); it helps listed players (+2.79%, +0.94 to +4.53) and costs unlisted ones. Fit and used on listed players only, it still ties (+0.03%). Questionable players' slope moves from 0.64 to 0.82 (bar 0.85). `active` isn't overstated at Out and Doubtful on these rows (predicted 3.2%, actual 3.9%; participation#F12's twofold was 2016-2024 by status) | `build/compare.txt` | strong | QB/RB/WR/TE on the 53 |
| R4 | **Games played for any reason beats I60's crude forecast by 14.4% of the squared error** (+11.3 to +17.4) with the shrunk healthy rate, +10.4% to +18.9% in each season 2019-2024; **23.3% (+20.7 to +26.0) with the fitted one** (R14). The gain is larger for players expected to miss time (0.0821 → 0.0663) but real for the healthy too (0.0808 → 0.0710). Its range from earlier seasons' misses holds 79.9% (81.0% fitted); the health count's own range held 26.5% | `build/games_played_rest_chain.txt`, `build/games_played_rest_chain_fitted.txt` | strong | the yardstick's rest-of-season rows |
| R5 | **On the yardstick, beside I60's crude forecast and participation, availability adds +0.55% to rushing yards (+0.38 to +0.74) and +0.21% to receiving yards (+0.10 to +0.33) over the rest of the season,** both beating 19 shuffled copies (largest +0.02%, +0.03%); with the fitted healthy rate (R14), +0.60% (+0.44 to +0.77) and +0.23% (+0.12 to +0.34). Passing: +0.06% (−0.54 to +0.61), no (+0.22% fitted, still no). Hindsight's ceiling on the same base: 26.7%, 22.5%, 67.7% | `build/yardstick_rest_chain.txt`, `build/yardstick_rest_chain_fitted.txt` | strong (rushing), moderate (receiving) | rest of season |
| R6 | **Kept share: participation's share when he plays already holds it.** The ridge with the report ties on squared error (−1.09%, −2.50 to +0.34) and loses on the range score (−2.33%) | `build/compare.txt` | moderate (3,246 rows) | listed QB/RB/WR/TE who play |
| R7 | **Snap-weighted adjusted games lost is a weak team trait that tracks the team's change.** Season to season r 0.22 (0.13 to 0.32; offense 0.23, defense 0.12). The same season's tally against the change in net EPA per play: −0.21 (−0.31 to −0.11); 10 weighted games lost ≈ −0.009 EPA a play. Last season's tally goes with a rebound (+0.19) | `build/measures.txt` | strong | teams, 2016-2024 |
| R8 | **Its rest-of-season forecast adds +5.06% to team yards beside Elo** (+2.86 to +7.32; copies' largest +3.82%), but ties beside Elo with I60's starters' forecast (+1.27%, −0.25 to +2.62). The tally to date doesn't count beside Elo (+2.94%, under the copies' +3.71%). **The spot-check (R12): the +5.06% is 2021; without 2021 it ties (+0.40%, −1.19 to +1.90)** | `build/team_rest_chain.txt`, `build/spot_r8.txt` | weak: one season | teams, rest of season |
| R9 | **Proneness repeats for backs and receivers, not tight ends.** Per 1,000 snaps, season to season: RB 0.26, WR 0.20, QB 0.17, TE 0.01 (−0.06 to +0.08). On the yardstick it adds +0.04% to receiving (counts, tiny) and costs rushing (−0.92%) | `build/measures.txt`, `build/yardstick_rest_chain.txt` | strong (repeat); the yardstick says don't use it there | 300+ snap player-seasons |

## Claude's odds, scored
Written in [BUILD.md](BUILD.md) before any result.

| # | Bet | Chance | Expected size | Result | Came true? |
|---|---|---|---|---|---|
| A1 | Method 1 beats rung 0, next game | 85% | 3-8% | +6.18% (+5.37 to +6.97) | yes, in size |
| A2 | Trees beat the lasso, next game | 35% | +0.5% | −0.63%, tie | no |
| A3 | Test 1: beside `active`, beats `active` alone | 55% | 0.5-2% | −0.57%, tie | no |
| A4 | Beats `active` recalibrated | 40% | 0.3-1% | +1.72% (+0.62 to +2.78); the recalibration itself loses to raw `active` (−2.33%) | yes, but the bar was lower than raw `active` |
| A5 | Questionable slope 0.85-1.15 | 60% | about 0.95 | 0.82 (stack), 0.79 (gated) | no |
| A6 | Out/Doubtful ratio under 1.3 | 75% | about 1.1 | 0.62 (stack); `active` itself 0.82 | yes as worded, but the twofold premise didn't reproduce |
| A7 | Test 2: games played beats I60 | 75% | 3-8% | +14.39% (+11.33 to +17.42) | yes, twice the size |
| A8 | Coverage 75-85% | 55% | | 79.9% (after the residual range; the first range 26.5%) | yes, with the caveat |
| A9 | Below q10 7-13% | 55% | | 9.9% | yes, with the same caveat |
| A10 | The chain beats method 1, rest | 40% (tie 45%, worse 15%) | 1-3% | +5.59% (+3.95 to +7.56) | yes, larger |
| A11 | The hidden state beats the chain | 20% (tie 50%, worse 30%) | | −2.64% (rest), −10.05% (next 3) | no: worse (the 30% side) |
| A12 | Test 3: kept share beats participation's | 55% | 1-3% | −1.09%, tie | no |
| A13 | Test 4: adds clearly on one board, beats 19 copies | 45% (receiving likeliest) | +0.3-1% | rushing +0.55%, receiving +0.21% | yes (rushing, not receiving, was the bigger) |
| A14 | AGL repeats, r 0.10-0.35 | 70% | about 0.2 | 0.22 (0.13 to 0.32) | yes |
| A15 | Tracks net EPA change, r −0.15 to −0.35 | 70% | about −0.22 | −0.21 (−0.31 to −0.11) | yes |
| A16 | The team forecast adds beside Elo | 40% | +0.5-2% | +5.06% (+2.86 to +7.32) | yes, larger (ties beside I60's starters too) |
| A17 | Every shipped forecast beats its shuffled copies | 95% | | 100 of 100 (next game), 20 of 20 (both chains), once the chains got a null that can test them | yes |
| A18 | Proneness repeats, r above 0.1 | 80% | about 0.25 | 0.27 (0.25 to 0.29) | yes |
| I121 | Proneness on the yardstick | 45% receiving 0.5%+, 30% rushing | | receiving +0.04%, rushing −0.92% | no, no |

Of 18 bets: 13 came true, 5 didn't. The misses were the bets on beating participation (A3, A5, A12) and on the fancier methods (A2, A11). The sizes ran larger than expected wherever the chain was involved (A7, A10, A16).

## The ladder
| Rung | Method | Next game (log loss) | Next 3 (range score) | Rest (range score) | Takeaway carried forward |
|---|---|---|---|---|---|
| 0 | the table (status × body part; state × weeks in it) | 0.04732 | 0.0632 | 0.3490 | The report and weeks in the state carry most of it |
| 1 | method 1: logistic / lasso; two parts | 0.04439 (+6.18%) | 0.0622 (+1.58%) | 0.3566 (−2.17%) | Exposure and history help next game; a single two-part fit per window is too coarse for long windows |
| 2 | method 2: the chain | (starts from rung 1's state) | **0.0599** (+3.55% over 1) | **0.3367** (+5.59% over 1) | Week-by-week moves compound correctly; the off state carries releases |
| 3 | trees (next game; the chain's moves) | 0.04461 (tie) | 0.0607 (−1.21%) | 0.3474 (−3.18%) | No interactions the linear moves miss |
| 4 | method 3: the hidden health state | | 0.0660 (−10.05%) | 0.3456 (−2.64%) | Four hidden states blur what the report already says; the observed state is the better state |

Each rung used the one below's takeaways: the report's codes and the body-part groups from rung 0 are rung 1's inputs; rung 1's inputs are the chain's moves' inputs.

## Where it misses
- **Questionable players' chance of playing** stays overconfident (slope 0.79-0.82). A game-day decision isn't in any Saturday input.
- **Healthy players' rest of season** is under-forecast (0.71 expected, 0.82 missed): new injuries are most of the room (decision 0044), and the chain spreads them evenly.
- **The health count's ranges hold 91-94%,** because the q10 is 0 for 82% of rows. That is what a calibrated whole-number count with a spike at 0 shows, not a fault (R16): above q90 4.8-7.3%, the chance of 1+ on the mark.
- **Games played was biased high** (0.850 against 0.815) with the shrunk healthy rate, which ignores releases; the fitted rate brings it to 0.824 (R14).
- **The COVID seasons' reserve codes** (R13): a Reserve/COVID-19 stint reads as injured reserve, so the chain expects a long absence for a one-week stint (0.39% of rows, 2.5% of the next-3 range score's total).

## The case against
- **Games played's range was fixed after a result.** The health-only range covered 26.5%. The residual range is the conventional fix and was fit walk-forward, but it was chosen after seeing that number (decision 0047 call 21).
- **The gated stack (R3) was added after a result too.** It tied anyway, so it changes nothing.
- **The 14.4% over I60 partly comes from information I60 doesn't have** (reserve lists and the report's history), which is the point. But I60 is a crude bar. The yardstick says the downstream worth is small: +0.21% receiving, +0.55% rushing beside I60 and participation, against a 22-27% ceiling. Most of the room is new injuries that nothing here sees coming.
- **Every result is 2017-2024 walk-forward**, trained from 2016 only (decision 0047 call 6), so 2017 trains on one season. The vault stays closed (the CEO), so the 2026 ledger is the first unseen season.
- **The team gain beside Elo (+5.06%) is one season** (the spot-check, R12): 2021 gives +23%, the other five seasons tie. The team rest board is small (about 530 team-games a season), and its shuffled copies already gain up to +3.8%, so a gain there needs a wide margin to mean anything.
- **The fitted healthy rate (R14) was adopted after its test** (decision 0047 call 27), on the same 2019-2024 rows it was scored on. It was pre-registered as I129 with a pass rule, and it beat the simpler rung (one walk-forward factor) by 8.6% (+7.96 to +9.27), but it hasn't met an unseen season: the 2026 ledger is its test.
- **2020's COVID opt-outs (R62) and the 2020-2021 Reserve/COVID-19 list (R59) count as health reserve** (R13). Small in the scores, but wrong for opt-outs.
- **`RSN` is read as non-football injury from its description,** never checked against the news.

## Pitfalls
- **`player_game`'s spine has no reserve lists,** so an injured-reserve stint is invisible without `roster_week`.
- **Before 2016 there are no weekly statuses:** a season-long reserve player looks active.
- **A per-row calibration slope on next game's health absence is dominated by unlisted rows.** Read the listed rows' slope beside it.
- **An expert's package may read only its view:** the harness's check 1 scans every file in the package, `checks.py` included.
- **Reserve codes R59 and R62 exist only in 2020-2021:** the Reserve/COVID-19 list (601 players in 2021, about a week each) and the 2020 opt-outs (69 players, about 10 weeks each). Both read as `RES`, a health reserve list (R13).
- **On the team rest board a shuffled copy gains up to +3.8% beside Elo alone:** the board is small and Elo alone is a weak base there (I115: −0.86%), so read a gain against the copies' spread and season by season (R12).
- **The harness's shuffled-outcome null can't test a model that doesn't learn from `y`.** The chain learns the week-to-week states in its features, so shuffling `y` left it unchanged (0 of 20 on next 3; a spurious 20 of 20 on rest). The fix is the expert's own `shuffle` (decision 0047 call 25): the health record shuffled with `y`. Any future model fit on transitions needs the same.

## Not looked at
- Depth-chart rank as the weight of a player with no share yet (decision 0047 call 7).
- The vault (kept closed by the CEO, R11).
- Why 2021 carries the team gain (R12). Not the Reserve/COVID-19 wave: the gain is largest in weeks 1-8, the wave was in weeks 15-18 (`build/spot_r8.txt`, S8).

## Could be improved
1. **Read 2020-2021's COVID codes right** (I139): opt-outs (R62) aren't health, and the COVID list (R59) is a short illness stint, not injured reserve.
2. **Put the AGL forecast into Elo's next build** (I115, the CEO's call), scored season by season and beside I60's starters' forecast, since R8's gain is one season (R12).
3. **Recalibrate participation's `active` on Questionable rows** (I138): it removes 1.66% of the log loss there and moves the slope from 0.66 to 1.09 (R15).

## Don't redo
- Method 1's two parts for a rest-of-season window: it loses to the table.
- The hidden health state with four states: it loses to the observed chain by 2.6-10%.
- Trees on next game's health absence or on the chain's moves: ties or losses.
- A stack on participation's `active` or its share: both tie.
- A team's habit of listing players Questionable, beside `active` (I128): ties.
- A temperature on the chain's moves (I130): ties or loses, and its ranges aren't too wide.
- Long-drive or long-first-half fatigue as an input (I29, I30): no gain.

## Interface card
| | |
|---|---|
| **Inputs** | `player_game` roster, snaps, injury, stats, injured, game_status; `roster_week` status; `team_game` schedule; participation `active` (pinned run 1a5406548afa4be181c2e88b9fa3b987) for the stack only |
| **Outputs** | `outputs/availability/<variant>/<run_id>/history.parquet`: `next_logit` (p_health_absent: mean), `next3_chain` and `rest_chain` (games_health_absent_next3/rest: mean, q10, q50, q90, p_nonzero, if_nonzero_mean/q10/q50/q90). Games played (any reason) and its range from `pcf.experts.availability.games` (`walk_healthy`, the fitted healthy rate, then `walk_ranges`); the team's snap-weighted games lost from `pcf.experts.availability.measures` (agl, agl_forecast) |
| **Level of detail** | player-game (every player on the 53 or a reserve list, all positions); team-game and side for AGL |
| **Interval** | weekly, every regular-season week, 2017-2024 tested |
| **Cadence** | in_season |
| **Known at** | the Saturday run (Thursday for Thursday games): this week's final report and roster |
| **How to use it** | The chain's rest-of-season mean, as a share of the window, and the games-played composite, as features for rest-of-season forecasts (rushing and receiving: R5). Keep participation's `active` and share for next game. The team forecast only as Elo's next build tests it (I115), season by season (R12). Proneness as a description, not a yardstick input (R9) |
| **Feeds** | crude-forecaster (yardstick), elo (I115), later team strength, futures and fantasy |

## After the CEO's review (2026-11-25)
The CEO: "We can open the 2025 vault to check the three forecasts. Yes Elos next build should definitely utilize games lost forecast. Can you spot check the team gain for elo. No vetoes from me. [...] Make sure to check the backlog of ideas and test the ones that fit into both of these builds, please." Every bet below was written in [REVIEW.md](REVIEW.md) and committed before its result.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R11 | **The vault (2025) stays closed** (the CEO, 2026-11-25, in the build session: "Keep it closed, actually"). Its odds and pass rules (V1-V8) were committed before any run and stay unscored; the 2026 ledger is the test | REVIEW.md §1 | | the three champions |
| R12 | **The spot-check of R8: the team gain beside Elo is one season.** By season, beside Elo: 2019 +3.8%, 2020 −4.2%, **2021 +23.0%**, 2022 +3.2%, 2023 −4.1%, 2024 +3.6%; without 2021, +0.40% (−1.19 to +1.90), a tie; beside Elo and I60's starters without 2021, +0.12% (−1.65 to +1.73). What is compared: the team rest-of-season board (team yards per game, 2019-2024, about 530 team-games a season, lasso refit each season), Elo's columns as the base, the forecast's offense and defense columns (games lost per game left) added. The worry before looking was the copies: a copy shuffled within the week keeps that week's average, so it could carry an early-or-late-season effect. It doesn't: the weekly averages alone tie beside Elo (+0.60%), so the copies' +2.3% average is fitting noise on a small board. Who is missing: the offense carries it, mostly the QB (QB part +4.75% beside Elo and the weekly averages, the line +0.18%, the backs and receivers −1.06%), and the defense's column adds nothing to own yards (+0.00%). Beside I60's starters it ties because I60's starters' forecast holds the QB's absences too (correlation −0.27). Within 2021 the gain is largest early (weeks 1-8 +35%, 9-13 +23%, 14-18 +9%), while the Reserve/COVID-19 list peaked in weeks 15-18 (126-186 players a week), so it isn't the COVID wave; why 2021 is unexplained. **No leak found:** the weights use only earlier games; every forecast was made by the board's moment (0 rows late); 256 week-1 tallies and 81 starters' values were filled with a median | `build/spot_r8.txt` | strong (that it's one season) | teams, rest of season |
| R13 | **The COVID seasons' reserve codes are read as health.** R62, only in 2020, is the opt-outs (69 players, about 10 weeks each); R59, in 2020-2021, the Reserve/COVID-19 list (211 and 601 players, about a week each). Both are `RES`. They are 0.24% and 0.39% of the horizons' rows; R59 rows are 2.5% of the next-3 range score's total (a one-week stint forecast as injured reserve). Left as is in this build (decision 0047 call 28); fixed in the next (I139) | `roster_week`, the champions' histories | strong | 2020-2021 |
| R14 | **I129 held: a healthy rate fit on his record beats the shrunk one.** A weighted logistic on the shrunk rate, his last game's share, his season's snaps, age, games, whether he played last game and position, fit walk-forward by season: games played then removes 23.27% of I60's squared error (+20.74 to +25.96), against 14.39% shrunk and 16.03% for the simpler rung (the shrunk composite times one walk-forward factor, 0.95-0.97). Against the simpler rung: +8.62% (+7.96 to +9.27); against the shrunk: +10.37% (+9.65 to +11.06). Every season +21% to +27% over I60; RB, WR and TE all gain. Its range holds 81.0%. On the yardstick it moves rushing to +0.60% and receiving to +0.23%. Now the shipped composite (decision 0047 call 27) | `build/ideas.txt`, `build/games_played_rest_chain_fitted.txt`, `build/yardstick_rest_chain_fitted.txt` | strong (2019-2024; adopted after the test) | QB/RB/WR/TE, rest of season |
| R15 | **I128 failed: a team's habit of listing players Questionable adds nothing beside `active`.** Teams do differ (the shrunk habit's spread 0.086 around a 0.311 absence rate) and the fit's sign is right, but beside participation's `active` recalibrated on Questionable rows it ties: +0.45% of the log loss (−0.24 to +1.15). The recalibration alone does what I128 hoped: on Questionable QB/RB/WR/TE rows it removes 1.66% of raw `active`'s log loss and moves the slope from 0.66 to 1.09, error 5.3 to 2.7 points (I138, for participation) | `build/ideas.txt` | moderate (2,807 rows) | Questionable QB/RB/WR/TE |
| R16 | **I130 failed, and its premise was wrong: the chain's ranges aren't too wide.** A calibrated whole-number forecast with 82% of q10s at 0 holds more than 80%: above q90 4.8% (next 3) and 7.3% (rest), under 10%; the chance of 1+ 25.7% against 25.7%, 40.1% against 41.3%. A temperature on the moves (tau chosen on the last training season) picks 1.0 in 5 of 8 seasons and ties (next 3, −0.40%) or loses (rest, −2.64%, −3.71 to −1.70) | `build/chain_temp.txt` | strong | the horizons |
| R17 | **The fatigue backlog.** **I29 (long drives tire the defense): real, doesn't pay.** A defender's injury rate on drive plays 7+ is 1.18 times plays 1-3 (1.08 to 1.30) with play type, tacklers, yards, down, field position, quarter, score and the defense's strength held; it keeps all of the raw rise (+18% against +16%), and snaps since the defense last rested carry it too (18+ snaps: 1.19 to 1.20). But the offense on the same plays rises nearly as much once held the same way (7+: 1.12, 0.995 to 1.25; 18+ snaps since the defense rested: 1.22), so it reads as long drives being a rougher kind of football more than a tired defense. As an input, a defender's long-drive snaps last game lose beside `next_logit` (−0.09%, −0.24 to +0.04). **I30 (pass defense after a long first half): failed.** Per +10 first-half snaps faced, dropback EPA rises +0.018 (+0.002 to +0.034) with the situation alone, +0.008 (−0.008 to +0.024) once the day's matchup is held; pass rush and coverage tie too. **I50 (fatigue shows as who is on the field): real, smaller than bet.** Late in long drives more backups are on the field: +1.9 points of the defense's 11 on plays 7-9 and +1.5 on 10+ against plays 1-3, with the score, quarter and win probability held; the line most (+3.7 and +2.7 points), linebackers +1.6 and +1.4, backs +1.0 and +0.9. A long first half brings no more backups after the break (+0.1 points per +10 snaps), and the backup share doesn't explain I30 (its coefficient stays +0.008) | `build/fatigue.txt` | strong (I29 real, I50), moderate (I29's offense check) | 2016-2024, every defensive play |

**The review's odds, scored:**

| # | Bet | Chance | Result | Came true? |
|---|---|---|---|---|
| V1-V8 | The vault | 55-95% | kept closed (the CEO) | not scored |
| S1 | The weekly averages alone add 2%+ beside Elo | 70% | +0.60%, tie | no |
| S2 | Beside Elo + weekly averages the real columns still add | 55% | +3.32% (+0.92 to +5.77), beats copies | yes |
| S3 | Beside Elo + I60's starters + weekly averages they tie | 65% | +3.90% (+1.61 to +6.22): they add, in a base the averages had hurt (−4.07%) | no |
| S4 | The part beyond I60's starters is the line and defense, and ties | 60% | the QB and skill parts carry it (+4.73%); the line +0.64% doesn't beat its copies | no |
| S5 | The offense carries it; the defense ties | 75% | offense +1.10%, defense +0.00% | yes |
| S6 | Positive in 4+ of 6 seasons | 60% | 4 of 6, but one season is +23% and the rest tie | yes as worded |
| S7 | No leak found | 85% | none | yes |
| I29 | The rise shrinks by half or more with play type and field position held | 60% | kept 112% | no |
| I29b | The controlled rise's interval clears 1 | 55% | 1.18 (1.08 to 1.30) | yes |
| I29c | Long-drive snaps count as an input | 15% | −0.09% | no (the 85% side) |
| I30 | Fails with the matchup held | 75% | +0.008 (−0.008 to +0.024) | yes |
| I50 | Backup share rises 2-4 points at 10+, mostly the line | 75% | +1.5 points overall, the line +2.7 | no as worded (the line, yes) |
| I50b | The backup share explains I30 | 60% | no change | no |
| I128 | Slope 0.85+ and a clear log-loss gain | 45% | tie (+0.45%) | no |
| I128b | A clear gain that beats 19 copies | 35% | no | no |
| I129 | 2%+ more of I60's squared error, clear against the shipped | 65% | +8.9 points (14.4% to 23.3%), +10.37% clear | yes, larger |
| I130 | Coverage 75-85% and the range score +1% | 55% | 94.9% and 91.0%; −0.40%, −2.64% | no |
| I130b | The same, after the doubt | 15% | no | no (the 85% side) |

Of 18 scored bets, 9 came true. The misses were the spot-check's guesses about where the gain sits (S1, S3, S4), and three of the fatigue sizes. The doubt written before I130 (whole numbers can't hold 80%) was right.

## Open questions for the CEO
1. ~~Open the vault (2025) once for the three champions?~~ Kept closed (the CEO, 2026-11-25, in the build session: "Keep it closed, actually"; R11).
2. ~~Should Elo's next build take the snap-weighted forecast for I115?~~ Yes, the games-lost forecast (the CEO, 2026-11-25). Since the spot-check found its gain is one season (R12), should Elo's build also carry I60's starters' forecast as the fallback?
3. Is the kept-share output worth keeping as a description, since participation's share already holds it (R6)?
