# Retro: what the record says, and what to try next

> The loop that learns from our own log (CLAUDE.md, "The retro"). After every second finished build (W12, retro 4) Claude reads every hunch, idea, finding and verdict, and writes here: how the last predictions scored, which kinds of bets hold, a prediction for every open idea and hunch, new ideas, and proposed changes to how we work.

- **A pattern is a hypothesis, not a finding.** It was fitted after the fact, on a few dozen verdicts that come in clusters (one project can supply most of a pattern). It earns trust only by predicting verdicts before they're known, which is what the predictions table is for.
- **Confidence means:** low, medium, high: roughly 60%, 75%, 90% sure the stated outcome happens. A retro scores them by counting how many in each band came true.
- **Where things go:** new ideas go in [IDEAS.md](IDEAS.md) as Claude's (I46 on); the CEO's edits can turn one into a hunch ([HUNCHES.md](HUNCHES.md)). Accepted workflow changes go in `CLAUDE.md`.
- **Next retro:** after the second project finished from 2026-11-15 on. That point came on 2026-11-19 (`crude-forecaster` and `context-live`). **The CEO postponed it** the same day: "I would personally like to hold off on the retro analysis number 2 ... I want to do VOE and maybe one other cousin, or maybe even some explorations first ... So I would like to push out retro number 2. We can do that later after we learn a lot from VOE and some experiments." Retro 2 runs after VOE and one or two of its cousins (`projects/voe/BRIEF.md`). **The CEO started it on 2026-11-20**, when VOE was paused: "let's start the retro 2 now, the retro analysis, and kind of look back. Keep asking me questions, keep telling me the limitations, keep telling me the constraints, the assumptions, because anytime I can push back, then we're getting value, and anytime you push back on me, then we're hopefully getting value and we're staying true and we're staying valid." Retro 3 comes after the next two finished projects. **Retro 3** came due on 2026-11-22 (`context-retro` and `opportunity-quality`) and the CEO started it on 2026-11-23. **Retro 5** ran 2026-11-26, after `vacated-opportunity`, `skill-over-expected` and `stabilization`; retro 6 comes after the next two finished builds (W12).

---

## Retro 5 (2026-11-26)

> The CEO, 2026-11-26: "Please start the next retro"

**Why now:** three builds have finished since retro 4: `vacated-opportunity` (built 2026-11-25 to 26), `skill-over-expected` (built 2026-11-25) and `stabilization` (built 2026-11-26). By W12 the retro was due at the second of them. `aging`'s exploration ran too (branch `pcf/aging`, not merged); explorations don't trigger a retro, but its hunches are scored here, provisionally.

**Read:** hunches H113 to H122, every idea closed or opened since retro 4 (I143 to I186), findings F94 to F129, the three builds' RESULTS, PREREG and SPOT_CHECK files, and aging's EXPLORATION.

**The steps,** in the charter's order: 1. sort the backlog; 2. score the predictions; 3. run the quick groups; 4. update the patterns; 5. rehearsal; 6. dreaming; 7. new ideas and predictions; 8. the findings table; 9. how we're working.

### 1. The backlog, sorted (2026-11-26)

**Since retro 4:** 65 were open after retro 4's dream run. The three builds opened 21 (numbered I154 to I186, with gaps) and closed 23, leaving 63. W9 held for every build: each row left Open in the same commit as its result.

**Closed by Claude at the sort** (no test needed):

| Idea | Closed as | Why, in one line |
|---|---|---|
| I69, the noise floor in every yardstick table | **Graduated** | Done in the code: `score_input` returns the copies' largest gain beside every gain, and every board result prints it |
| I96, the diffusion model as a play simulator | Killed | It waits for a simulator nobody has kicked off, and diffusion lost both times it was tried (H85; stabilization's third method) |
| I104, a kept share that changes by season | Killed | Its form failed in stabilization's build (F126); the season-varying share is the same question from the other side |

I153 (historical analogs) was tested on `pcf/aging` and added nothing beyond the player's levels. It closes when aging merges.

**The sort: 61 open** (after step 3's closures and steps 6 and 7's new rows), by what they need:

| Group | Ideas | Cost | Where it runs |
|---|---|---|---|
| **A. Retro-sized, data in hand** | I187 (ranges on biased rows), I192 (travel beside Elo), I193 (a moving lead back's split) | Under an hour each | Retro 6's step 3, or now if the CEO wants |
| **P. Participation's next build** | I11, I15, I16, I51, I138, I191 (6) | A session | participation's next version. I138 has new evidence (I4, below) |
| **S. Stabilization's next version** | I183 (the opponent-adjusted faced rate), I186 (the trend for teams), I189 (k by role) (3); with I185's per-position k to ship-test | A session | stabilization's next build |
| **O. Player opportunity** | I5 (rookies, its original form), I149, I152 (its original form), I153 (closes at aging's merge), I184 (5) | Inside the build | `player-opportunity`'s build |
| **E. Player value on lower-noise outcomes** | I77, I78, I81, I82, I92, I99, I111 (7) | A session each; I111 on the CEO's hold | context and VOE's next looks |
| **B. Misses after a change** | I41, I54, I56, I68 (4) | A session each | team-efficiency, pace, crude-forecaster |
| **T. Teams** | I31, I32, I42, I115, I127, I148 (6) | In a build | team-efficiency's and Elo's next builds |
| **AV. Availability** | I120, I139 (2) | A session | availability and td-expert |
| **H. Coaches and schemes** | I21, I71, I88, I93 (4) | One session | schemes-v2's next look |
| **J. Tooling** | I45, I62, I64, I66, I72, I188 (6) | When a build touches the harness | the build that needs it |
| **C. Ranges** | I1, I52, I85 (3) | One session | `pcf.validation`, then each expert |
| **D2. Inside built experts** | I103, I117, I119 (3) | Quick each, inside the build (retro 4) | opportunity-quality's and td-expert's next builds |
| **K. After the season** | I6, I8, I173 (3) | Quick | the first retro after 2026 ends |
| **N. Night builds and the CEO's yes** | I141 (H6 runs inside it), I145 (a yardstick change) (2) | A night build | when the CEO sets one up |
| **L. Waiting** | I110 (the CEO's hold), I147 (needs every build to save per-season gains: W13), I150 (the betting cousin), I190 (scored at retro 6) (4) | | their dependency |

**What the sort says:**
- **The backlog held steady (63 to 61):** builds now close about as many ideas as they open, because every build runs the backlog (the CEO, 2026-11-26).
- **No retro-sized group was left over from the builds** except the CEO's routed four (I4, I9, I10, I86) and two from stabilization (I183, I185). Step 3 ran five of the six, plus H5 and I144.
- **Two builds would clear a fifth of the rest:** participation's next version (P, 6, plus I187's ranges) and player-opportunity (O, 5).

**Open hunches:**
- **H5** was rated retro-sized at retro 4 and never run. It ran in step 3: proposed failed, for the CEO to close.
- **H6** waits for I141's night build.
- **H18** needs a session (the contract table's join).
- **H71 and H74** have no test yet. skill-over-expected's build didn't touch them; they belong to a VOE look.
- **Aging's H115 to H122** sit on `pcf/aging` with proposed verdicts, still waiting for the CEO.

### 2. How the predictions scored ([`retro/explore/retro5_calibration.py`](retro/explore/retro5_calibration.py), output [`.txt`](retro/explore/retro5_calibration.txt))

**What's scored:** every bet written before its test since retro 4 that now has a result: the three builds' briefs, PREREGs and spot-checks, the stabilization exploration, and aging's exploration. "Held in part" counts as held, as before. Bets the tests never answered are left out (listed in the script). **Aging's hunches are provisional:** they're scored on the proposed verdicts, which the CEO hasn't closed. H117's told-apart half and H119's real half pass their written rules but are proposed failed (both are the pull-back). The proposed verdict is scored, and a sensitivity line scores the written rules instead.

**The CEO's first number: 9 hunches (H113, H114, and aging's H115 to H122 less H119, which has no CEO odds), 7 held.**

| | Bets | Held | Average odds | Brier | Pays (any held-out gain) |
|---|---|---|---|---|---|
| **Retro 5: all** (aging provisional) | 9 | 7 (78%) | 49% | **0.262** | 7 |
| Football claims | 6 | 5 | 56% | 0.243 | 5 |
| Methods | 3 | 2 | 35% | 0.301 | 2 (H114, H118, both as plain mileage or a pull, not the method's twist) |
| Retro 4, for comparison | 20 | 11 (55%) | 51% | 0.230 | 5 |

- **The CEO was too cautious this round.** The four bets at 25-30% held 3 of 4 (H113, H114, H115); the high ones (H121 95%, H122 80%) held. The 45-50% bets split.
- **This reverses retro 4,** where the 30% bets held 1 of 6. Two rounds in a row the CEO's low band is the one off, in opposite directions. Nine bets is too few to call that a habit.
- **Claims held 5 of 6. The one failure is H117** (two ways to decline), which was the pull-back.
- **Running total over four retros:** claims held 27 of 37 (73%); methods 8 of 22 (36%).

**Claude, on the CEO's claim as worded (W6): 10 bets, 7 held, average odds 50%, Brier 0.233** (0.293 if H117's and H119's written rules are scored instead).
- Claims 0.196, methods 0.318. Claude bet against H118 (25%) and H115 (25%), and both held by their rules. Both held as plain mileage, which is what Claude expected to fail.
- **Head to head on the 9 with both numbers: the CEO closer on 5, Claude on 2, level 2.** Brier: the CEO 0.262, Claude 0.254. This is the first retro where the CEO was closer bet by bet.

**Claude's side bets, ideas and build odds: 119 bets, 59 came true (50%) at average odds of 53%. Brier 0.233,** about level with retro 4's 0.220, still better than a coin (0.250).

| Claude's stated odds | Bets | Came true |
|---|---|---|
| 0 to 35% | 22 | 41% |
| 35 to 55% | 30 | **30%** |
| 55 to 75% | 45 | 56% |
| 75% and up | 22 | 73% |

- **The 35-55% band is too high again** (retro 4: 29% at 44%; now 30% at 43%). When Claude says "about even", the bet comes true less than a third of the time.
- **The low band is too low:** 41% came true at 23%.
- **By source:** the vacated build and spot-check were sharp (Brier 0.202 and 0.123). The skills spot-check was the worst (0.382): 3 of 9 came true at 59%. The CEO's spot-check found the new-team gain was scheme, and Claude's odds had bet against that.
- **Nine confident bets (70%+) failed.** Among them: I55's first game back (90%), I163's nests below 1 (75%), I79 (no RB efficiency measure makes "use", 75%), "it's scheme" (75%, the skills spot-check), and age against no age for usage at 4 of 4 (80%).
- **Size bets: 2 of 8 came true, at average odds of 61%.** W11 (Claude's own rule, retro 4: a size bet starts at 35%) **wasn't kept.** The size bets written since averaged 61%, higher than before the rule. Two were bets on a size band that the result overshot: I170 (+3 to 6%, actual 13%) and I171 (5-15%, actual larger). Claude's rule didn't change Claude's numbers, so step 9 proposes a different form (W15).

### 3. The quick groups, run (2026-11-26, discovery only; scripts in `retro/explore/retro5_*.py`)

The CEO routed I4, I9, I10 and I86 here ("We can leave quick ideas missed by a build to be tested by the retro"). I185 and I144 were retro-sized by their own rows, and H5 by retro 4's design. Every bet below was written in its script's header before the run. I183 needs a faced-rate forecast built on stabilization's opponent code, so it goes to stabilization's next version (group S), under W7. I147 waits for W13.

| Idea | Result | Odds, scored |
|---|---|---|
| **I4,** Questionable players produce less ([`retro5_i4_questionable.py`](retro/explore/retro5_i4_questionable.py)) | **The flag pays a little, and not through playing hurt.** On the yardstick (next game, 2019-2024), beside participation, the Questionable flag adds +0.06% on receiving (0.02 to 0.11) and +0.14% on rushing (0.02 to 0.27), beating all 19 copies. Over all Questionable rows the forecast runs high (−1.8 and −2.2 yards). Those who play *beat* it: +3.5 and +6.7 yards, against +0.5 and +1.5 for players not listed. The gain is the chance he sits, which participation under-reads (I138). Killed as worded; F133 | 30% it counts beside participation: **came true**; size 0.05-0.2%: **came true**. 55% over-forecast when he plays: **failed** |
| **I9,** movers' first games ([`retro5_i9_i10_participation.py`](retro/explore/retro5_i9_i10_participation.py)) | **Real, doesn't pay.** Participation still over-forecasts a mover's first 4 games by 1.1 points of share (0.6 to 1.5). His new group's unclaimed share, as a walk-forward correction, loses 0.3% on those games; a constant shift ties. Killed; F132 | 50% the miss is still below 0: **came true**. 40% (vacated's PREREG) the unclaimed share pays: **failed** |
| **I10,** no depth-chart slot (same script) | **Real, doesn't pay.** No-slot rows are over-forecast by 3.1 points of share (2.1 to 4.3), in all 9 seasons. A walk-forward shift ties overall and loses on those rows: 2016's −11.5 over-shifts the later seasons. Killed; F132 | 40% still over-forecast by 1+ point: **came true**. 20% a shift pays: **failed** |
| **I86,** the backfield split is the coach's ([`retro5_i86_backfield.py`](retro/explore/retro5_i86_backfield.py)) | **It's the lead back's.** The lead back's share of his team's RB carries repeats when he stays (r 0.28 same coach, 0.30 new coach). It doesn't repeat when he changes under the same coach (0.04), and it doesn't travel with a moving coach (21 moves, r 0.00). Killed; F130 | 35% (retro 3) that it's the coach's: **failed**. 35% that it travels with him: **failed** |
| **H5,** strength is conditional (the CEO's; [`retro5_h5_conditional.py`](retro/explore/retro5_h5_conditional.py)) | **Proposed failed.** Beside Elo, no team's gap repeats between a season's halves: home −0.02, the opponent's offense (top or bottom third) +0.01, the opponent's pass lean +0.02, leading or trailing at the half −0.06. No team-by-condition term adds (−0.19% to −0.01%). Even a team's own home edge doesn't repeat: only the league's does, and Elo has it. F131 | The CEO's 30% (a large effect): **failed**; the CEO's 50% (nothing worth keeping): **came true**. Claude's 10%: failed (as bet). Claude's 75% (only home holds): **came true** |
| **I185,** a k per position ([`retro5_i185_position_k.py`](retro/explore/retro5_i185_position_k.py)) | **Pays where positions differ.** Clearly better than the pooled k for 4 of 20 rates: yards a route +0.9%, aDOT +0.9%, targets a coverage snap +0.9%, aDOT allowed +0.5%. Worse for 2 (missed tackles −0.3%, QB hits −0.02%). 11 rates have one position and can't differ. Graduated to stabilization's next version (it ships only after a test there with copies); F134 | 30% clear for 2+: **came true**; size 0.5-2%: **came true** for 3 of 4 |
| **I144,** the self-model ([`retro5_i144_self_model.py`](retro/explore/retro5_i144_self_model.py)) | **Loses to Claude's written odds.** A logistic on the tags every bet carries, fit on retros 3-4's 165 bets: Brier 0.251 on retro 5's 129 Claude bets against the written odds' 0.233. On the CEO's 9 first numbers it was *better* (0.226 against 0.262): the CEO's odds were too low this round, and the tags just said "hunches hold about 60%". Killed. The good part became I190 | 35% it beats Claude's odds: **failed**. 50% it beats both on pays: **failed** |

**What it means:**
- **Three of the five football ideas are real and don't pay** (I4's playing-hurt reading, I9, I10). They join P14.
- **Two of them point at participation** (I138 for the sitting chance; I187 for ranges where the middle can't move).
- **I86 and H5 close two old team-level claims.** Neither a coach's backfield habit nor a team's conditional strength repeats. That is P15 (step 4).
- **Step 3's 17 bets: 8 came true** (Claude's: 7 of 15).

**Closed:** I4, I9, I10, I86, I144 killed; I185 graduated. With step 1's three (I69, I96, I104): **9 closed.**

### 4. The patterns, updated

| # | Pattern | New for it | New against it, or its limit |
|---|---|---|---|
| P4 | **Methods tie the simple version, or lose** | Stabilization: the diffusion model lost to a ridge on its own inputs; the ridge cleared the pull for 3 of 20; layered credibility (I181) and a game-noise factor (I154, I182) killed. Aging: roles, hidden states and analogs add nothing beyond a linear model on his levels (H116, I153); risk weighting adds nothing over plain mileage (H118). Skills: per-group k ties (I172) | **What paid was simple and new:** the trend (F124, one more column), the second pull (one slope), a k per position where positions differ (F134). Also I180's exact ratio, a correction from data we had. P4 still reads "a simple thing with new information beats a clever thing with the same information" |
| P13 | **Bodies and usage hold; front-office decisions don't** | Aging: age and mileage forecast usage and the chance he's still playing (H115, H118, H121, H122). Mileage reads as durability, not wear | No new team-decision hunch was tested this round |
| P14 | **Real but small loses to the board's noise** | I9 (−1.1 points, a correction loses), I10 (−3.1 points, a shift ties), I4 (a real gap among those who played), I143 (COVID rates differ a little), I164 (a sudden absence transfers 0.018 more) | **A limit worth testing:** a real bias that a mean shift can't fix may still fix a range. I187 tests that |
| **P15 (new)** | **League-wide rates plus who is present; team and coach extras don't repeat** | F101 (teams and coaches have no own transfer rates), F131 (no team-specific conditional strength, home included), F130 (the backfield split follows the lead back, not the coach), F23 and H78 (a mover's share comes from who is left), F115 (a mover's team-owned trait: a harder pull; the new team's rate adds only for linemen) | **Not linemen and edge pressure:** the new team's rate adds there (F115), and a lineman's numbers are his line's (F114). P15 says a team's *habit* doesn't carry; the *players* around him do |
| **P16 (new)** | **Usage moves and repeats; efficiency regresses** | Stabilization: usage rates are real within weeks (k 4 to 69 attempts) and drift in season; efficiency rates take seasons (k 136 to 255) and stay static (F120, F125, F126). Aging: age explains 1-6% of usage's true change and about none of efficiency's (H122). Rookies' usage doesn't rise in season (I5's form) | The oldest pattern in a new form: P9 (volume carries player forecasts). P16 says why: usage is the coach's choice and it lasts; efficiency is mostly the play's luck |

**What the patterns say to do:**
- The CEO's next football bets should keep to bodies and usage (P13, P16).
- Team- or coach-level "habit" claims should be bet low unless a lineman or edge rusher is involved (P15).
- A method is worth a test when it adds a column of new information, not when it re-reads the same one (P4).

### 5. Rehearsal ([`retro5_rehearsal_stabilization.py`](retro/explore/retro5_rehearsal_stabilization.py), outputs `retro5_rehearsal_stabilization.txt` and `_test_seasons.txt`)

**What was re-read:** F94 to F129 (the three builds), against this retro's step 3 and aging's exploration.

**What was re-run:** the findings that later work leans on most are F121 (M1, the base of every pulled rate), F122 (the second pull) and F124 (the trend, which ships as rung 4 and was chosen on the test seasons). Stabilization's walk starts at targets 2007, fit only on earlier pairs at every step. So its forecasts for **targets 2010-2017 already existed and had never been looked at.** Eight rates have play-by-play from 2006. Scored here for the first time, with the same 8 on 2018-2024 for a like-for-like comparison:

| Rung, clear of the one below (8 rates) | 2010-2017 (never scored) | 2018-2024 (the test seasons) | Claude's odds, written before the run |
|---|---|---|---|
| M1 against the raw rate (F121) | 7 | 8 | 85% for 8 of 8: **failed** |
| M1 against the position's average (F121) | 5 | 7 | 80% for 6+: **failed** |
| The second pull against M1 (F122) | 2 (and 2 worse) | 4 | 55% for 3+: **failed** |
| The trend against the ridge (F124) | 3 (none worse; 6 of 8 lean positive) | 5 | 55% for 4+: **failed**; 30% for 6+: failed |

- **Nothing is contradicted:** every rung points the same way out of time, so no finding is marked unclear.
- **Everything reaches about two rates fewer.** That is the size of the test seasons' lean, and it's what the vault would show too.
- **The trend's QB pressure gains don't hold out of time:** hit-or-sack +3.5% and sack rate +3.6% on 2018-2024, −0.8% and −0.1% on 2010-2017. Its gains on aDOT, catch over expected and scramble rate hold.
- F121, F122 and F124 carry these numbers now.
- **Claude's four odds all failed,** each by about one rate: the odds read the 20-rate headlines, not these 8 rates.

**What later work says about the others:**

| Finding | What later work says | Done |
|---|---|---|
| F23 and F2, a back's share is his backfield's | I86: the team-level split follows the lead back, not the coach (F130) | F23 notes it |
| F111 and I172, one k per trait | I185: a k per position pays for receiving and coverage rates, where positions differ (F134). I172 tied for the pass-rush traits | Not a conflict: F134 names the limit |
| F120 and F125, usage moves and efficiency doesn't | Aging (unmerged): age explains usage's change and not efficiency's (H122) | Supports; aging's rows come at its merge |
| F124, the trend | Aging's comeback (H119) is the pull-back. The trend is the opposite read (where he's heading), and it holds out of time on 3 of 8 rates | Notes above |
| F57, a mover's new slot | I9: participation, which reads it, still over-forecasts movers' first games by 1.1 points, and no shift fixes it (F132) | No change |

### 6. Dreaming

**What was read:** all 193 ideas, the 129 findings and the 122 hunches (aging's on its branch). Four threads stood out since retro 4:
- the misses that are real but can't be corrected (P14);
- "told apart" results that turned out to be the pull-back (H117, H119);
- simple columns of new information pay (the trend, a k per position);
- our own odds, which miss in the same bands retro after retro.

Five dreams, tagged `dream, retro 5` in IDEAS.md with their odds:

| # | The dream | From | Claude's odds |
|---|---|---|---|
| I187 | **Misses that don't shift should widen:** where a forecast is biased but a correction loses (no slot, a mover's first games, Questionable), widen the range there instead of moving the middle | I9, I10, I4, F93 | 60% coverage is under 75% on 2+ of the 3 kinds; 35% the widening pays on the range score |
| I188 | **The pull-back null as a standard check:** every "kinds of player" or "comeback" claim scored beyond what his own pulled level and last two seasons forecast, as one `pcf.validation` function beside the copies | H117, H119 | 50% another past held "kinds" result falls under its rule; 70% it's cheap enough to be standard |
| I189 | **k from the role, not the position** | I185, P11 | 30% better for 2+ of the 9 rates that span positions |
| I190 | **Our odds, recalibrated by our own record:** each author's written odds mapped through how often that band came true, fit on retros 1-5, scored at retro 6 | Five retros of step 2; I144's side result | 45% beats Claude's written odds; 40% the CEO's |
| I191 | **Usage momentum within a season:** a player's snap-share trend over his last 6 games, beside participation's rest-of-season forecast | F124, F125, aging's durability | 30% it counts on a rest-of-season board |

**Where they go:** I187 is retro-sized (saved walks). I188 is tooling for the next exploration that labels kinds. I189 goes to stabilization's next version and I191 to participation's. I190 is scored at retro 6.

**How the origins have done** (closed ideas that had a test):

| Origin | Through retro 4 | Since retro 4 | All | Graduated | Paid as a forecast since retro 4 |
|---|---|---|---|---|---|
| Retro-born | 12 tested, 8 graduated | 7 (I49, I79 held; I143, I55, I76, I86, I144 failed) | 19 | **10 (53%)** | 1 (I49) |
| Project-born | 64, 28 graduated | 26 (I14, I136, I155, I156, I164, I165, I170, I171, I172, I185 held) | 90 | **38 (42%)** | 8 (I14, I156, I165, I170, I171, I180, I185, and I4's small flag) |
| Dream-born | 2 (I146 graduated, I151 killed) | 0 closed | 2 | 1 | see below |

- **Retro-born ideas still graduate more often** (53% against 42%), but the gap narrowed: 2 of 7 graduated since retro 4. The retro-born ideas built in the builds this round were mostly bets against (I55, I143) that failed.
- **The dreams' first real payoff is I152, the role drift.** Its form in stabilization (where a rate was heading) cleared 16 of 20 rates and ships as rung 4, the largest gain any retro 4 idea made. Its row stays open for its original form (the role table).
- **The other retro 4 dreams:** I146 paid as a discovery; I151 was real and small; I148 is unclear; I153 failed (on aging's branch). I147, I149 and I150 are untested.
- **Of the six dreams tested, two paid** (I146, I152's form). That matches the project-born rate on a tiny count.

### 7. New ideas and predictions

**Two new ideas, as Claude's,** tagged `retro 5` in IDEAS.md:

| # | Idea | The bet | Claude's odds |
|---|---|---|---|
| I192 | **Bodies, not teams: travel and body clock beside Elo** (P13 and H5): league-wide terms for time zones crossed, a western team's early kickoff in the east, and short rest after travel | Elo's saved margins, walk-forward slopes, the share of squared error removed | **30%** clear; 0.1-0.3% |
| I193 | **Does a lead back carry his split?** (from I86) | A moving lead back's new split on his old team's split and the new team's last split | **35%** his old split adds (about 40 moves) |

**Predictions moved by this retro** (every other open idea's and hunch's prediction stands as last written in IDEAS.md and HUNCHES.md):

| Bet | Was | Now | Why |
|---|---|---|---|
| I138, recalibrate participation's chance he plays on Questionable rows | (none) | **55%** | I4: the forecast runs high on Questionable rows, and those who play beat it: the sitting chance is under-read |
| I186, the trend for teams | 35% | **30%** | The rehearsal: the trend reaches two rates fewer out of time |
| I152, role drift in its original form (the role table) | 40% | **45%** | Its stabilization form paid; it holds out of time on 3 of 8 rates |
| I5, rookies (its original form, fantasy points) | medium | **35%** | Rookies' usage rates don't rise in season (its stabilization form). The under-projection would have to come from efficiency, which regresses (P16) |
| H18, schemes predict whom teams pay (Claude's number) | 35% | **30%** | P15: team habits don't carry |
| H71, a latent space of the 22 (Claude's number) | 20% | **15%** | P4: roles, hidden states and analogs added nothing in aging; the diffusion model lost in stabilization |

### 8. The findings table

Five new rows (F130 to F134), and the rehearsal's numbers on F121, F122, F124 and F23:
- **F130 (I86):** a team's backfield split belongs to the lead back, not the head coach.
- **F131 (H5):** beyond Elo's league-wide home edge, team strength isn't conditional.
- **F132 (I9, I10):** participation over-forecasts no-slot rows (−3.1 points) and movers' first games (−1.1), and neither bias pays as a correction.
- **F133 (I4):** a Questionable listing adds a little beside participation, through the chance he sits.
- **F134 (I185):** a k per position beats the pooled one where positions differ.

"Use and ignore" now lists these under running backs, teams, availability and movers, and any player's rate.

### 9. How we're working

**How retro 4's accepted changes went:**

| Change | How it went |
|---|---|
| W10, rehearsal and dreaming inside the retro | Worked. One dream (I152) became the biggest shipped gain of the round, and the rehearsal found the earlier seasons the walk had already made |
| W12, retros after two finished builds | Worked; this one came after three builds, which finished within two days of each other |
| W11, Claude's size bets start at 35% | **Not kept.** Size bets averaged 61% and came true 2 of 8 |
| "Every build runs the backlog" (the CEO, 2026-11-26) | Worked. Builds closed as many ideas as they opened, and each build listed what it didn't run |

**Proposed now** (the CEO accepts, edits or rejects; all three accepted 2026-11-27, "I approve w13-w15", and written into `CLAUDE.md`):

| # | Change | Why |
|---|---|---|
| W13 | **Accepted 2026-11-27.** **Every build saves each tested input's gain per season**, beside the pooled gain (a small table in its outputs) | I147 (seasons won as a vault-risk test) can't run without it, and retro 4's F62 reversal is the case for it. It costs a few lines per build |
| W14 | **Accepted 2026-11-27.** **The earlier-seasons check:** where a build's walk already forecasts seasons before its test window, the shipped rungs are scored there too, before shipping, and reported beside the test seasons | The rehearsal found 2010-2017 forecasts that had been made and never read, and they showed the test seasons' lean (two rates fewer). It's a second vault that costs nothing, and the 2025 vault stays closed |
| W15 | **Accepted 2026-11-27.** **Claude writes a size as a middle and an 80% range** ("about +1%, 80% between +0.3% and +2%"), scored by how often the result lands in the range, instead of a probability on a narrow band. It replaces W11 | W11 asked Claude to lower its own numbers and it didn't happen. A range is scored by coverage, which is the same test our forecasts already pass |

**Questions for the CEO:**
1. How have the last two days of builds felt from your side? Is anything slower or noisier than it should be?
2. This retro ran every quick idea itself, and the backlog held at 61. Do you want retro 6 to aim to shrink it, by closing more ideas that wait on projects not yet planned?
3. Is there a pattern in how we work that you'd like the retro to measure next time (for example, how long each build takes, or how often your spot-check changes a verdict)?

### Waiting on the CEO (asked 2026-11-26)

1. **H5:** close it as failed (F131)?
2. **Aging's H115 to H122** (on `pcf/aging`, asked 2026-11-25): close them as proposed? H117 and H119 pass their written rules but are proposed failed, since both are the pull-back.
3. **W13, W14 and W15:** accept, edit or reject?
4. **Group A** (I187, I192, I193): run them now, or leave them for retro 6?
5. The three questions above, on how we're working.

**The CEO's answers (2026-11-27):** "Did we accidentally not test h115-h122 or do you just need my approval to close them, if so then yes you may close h115-h122. Yes you can close h5. I approve w13-w15."

- **H5** closed as failed (HUNCHES.md). **Aging's H115 to H122** closed as proposed, on `pcf/aging` (they were tested in aging's exploration and only waited for the CEO's close). So step 2's aging scores are now final, not provisional: the 0.293 in the case against no longer applies.
- **W13, W14 and W15** are in `CLAUDE.md` (building, validating, and the odds paragraph). W11 is retired.
- Still open: group A (item 4) and the three questions on how we're working (item 5).

### The case against this retro

- **Step 2 leaned on unmerged verdicts** (settled 2026-11-27: the CEO closed them as proposed). Aging's eight hunches were scored on proposed verdicts. If the CEO closes H117 and H119 by their written rules instead, Claude's Brier on the CEO's claims moves from 0.233 to 0.293.
- **I4's "those who play beat it" conditions on playing.** The forecast already discounts him for the chance he sits, so a player who plays beats it by construction. What the test shows is that nothing points to a cost of playing hurt. It doesn't show there is none: the forecast's "if he plays" share isn't on the yardstick board.
- **I9 and I10 tried one-number corrections.** Participation's trees already read the unlisted and new-team flags. A correction that learns by position or by depth slot might still pay. I187 tries the range instead.
- **I86 used one definition of the split** (the lead back's share). A coach's committee habit could show in another (the top two backs' share, or a concentration index).
- **H5 used the opposing offense's dropback EPA to date as "the opponent's QB",** as a team rate. A QB-level split (the starter's own rate) might differ, though P2 has failed at every level so far.
- **I185 had no shuffled copies.** 4 of 20 at a one-sided 95% bound is above the 1 expected by chance, but not by much. Stabilization's next version tests it with copies before anything ships.
- **The rehearsal re-ran 8 of 20 rates.** The stand-in and PFR rates start too late for earlier seasons. The trend's most important gains (usage: targets a route, carries a run snap) aren't among the 8.
- **The dreams are Claude's reading, in one sitting.** Their odds are guesses, as every idea's are.

---

## Retro 4 (started 2026-11-25)

> The CEO, 2026-11-25: "Start retro 4"

**Why now:** three projects finished since retro 3: `td-expert` (built 2026-11-24), `availability` (built 2026-11-24 to 25) and `roles-archetypes` (built 2026-11-24 to 25). The yardstick batch (retro 3's group D) and vacated opportunity's exploration and brief came in between. By the charter the retro was due at the second of them, before the next project starts.

**Read:** hunches H93 to H112 (20, all with the CEO's odds written before the test), ideas I113 to I139, the yardstick batch, and the projects since retro 3: `td-expert` (built), `availability` (exploration, brief, build), `roles-archetypes` (three looks, brief, build in two rounds), `vacated-opportunity` (exploration, brief agreed).

**The steps,** in the charter's order: 1. sort the backlog; 2. score the predictions; 3. run the quick groups; 4. update the patterns; 5. new ideas and a prediction for every open one; 6. the findings table; 7. workflow changes for the CEO.

### 1. The backlog, sorted (2026-11-25)

**Since retro 3:** 68 were open. The builds and the yardstick batch closed 32 (20 graduated, 12 killed) and opened 9 (I115, I117, I119, I120, I126, I127, I137, I138, I139). W9 worked: every row closed by a build left Open in the same commit.

**Housekeeping, closed by Claude** (three rows had a result but sat under Open, from before W9):

| Idea | Closed as | Why, in one line |
|---|---|---|
| I49, swap pairs inherit an absent player's snaps | **Held, small** | It became the vacated plus-minus's pair part: +2.3% (+0.1 to +4.5), with H101 and I136 (the replacement is nearer in role) |
| I25, tendencies settle fast, efficiency doesn't | **Held in part** | schemes-v2#F5: shotgun, no-huddle and man rate settle in 1-2 games, efficiency a third; pass rate over expected and depth don't settle faster |
| I23, receiver depth fit | Killed | schemes-v2#F13 left it unclear (+0.03 EPA per target, intervals touch zero, 193 movers); matchups tie (P2) and there are no new movers until the season ends |

**The sort: 58 open ideas,** by what they need and what they cost:

| Group | Ideas | Cost | Where it runs |
|---|---|---|---|
| **A. Retro-sized: data in hand, no package code** | I137 (the yardstick's rushing floor; the CEO, 2026-11-25: "Keep i137 for the next retro"), I28 (a playoff flag for the traits), I97's data check (enough quasi-random absences?) | Under an hour each | Step 3 |
| **D2. Quick runs on saved walks: a build-chat batch** | I103 (trees for opportunity-quality's horizons), I117 (trees for the other touchdown forecasts), I119 (a game's chance of 2+ touchdowns) | Quick each, but inside built experts (W7) | The build chat, as one batch |
| **E. Player value on lower-noise outcomes** | I76, I77, I78, I79, I81, I82, I97, I99, I111 (9); hunches H71, H74 | A session each; I76-I78 heavy | skill-over-expected's build (brief agreed 2026-11-20, still not started) |
| **G. Participation's next build** | I9, I10, I11, I15, I16, I51, I55, I138 (8) | A session | participation's next version |
| **B. Misses after a change, other experts** | I4, I5, I41, I54, I56, I68 (6) | A session each | team-efficiency, pace, crude-forecaster |
| **T. Teams** | I115, I127 (2) | In a build | Elo's next build (I115 with the games-lost forecast, the CEO, 2026-11-25), team-efficiency |
| **V. Vacated** | I126 (1) | Quick | vacated-offseason's build |
| **AV. Availability's next** | I120, I139 (2) | A session; I120 needs the starter's chance to keep the job | availability and td-expert |
| **H. Coaches and schemes** | I21, I71, I86, I88 (4) | One session | schemes-v2's next look |
| **J. Tooling** | I45, I62, I64, I66, I69, I72 (6) | When a build touches the harness | the build that needs it |
| **C. Ranges** | I1, I14, I42, I52, I85 (5) | One session (one coverage tool) | `pcf.validation`, then each expert |
| **M. Context's next version** | I92, I93, I110, I112 (4) | A session each; I110 and I112 on hold (the CEO, 2026-11-22) | context-retro's next version |
| **K. After the season** | I6, I8 (2) | Quick | the first retro after 2026 ends |
| **L. Parked** | I31, I32, I96, I104 (4) | | their projects |

(I97 sits in A for its data check and in E for its test, so the groups add to 59.)

**What the sort says:**
- **The backlog shrank for the first time:** 68 to 58, because three builds ran (W7's batch and the builds closed 32).
- **Group F (fatigue) is empty:** availability's review settled I29, I30 and I50.
- **Two builds would clear a third of the rest:** skill-over-expected (E, 9 and two hunches) and participation's next version (G, 8).
- **Only three are retro-sized** (group A), plus K after the season.

**Open hunches (the CEO's to close):** H5, H6 and H18 (open since retro 1, kept open at retro 3), and H71 and H74 (odds given at retro 3; they wait for skill-over-expected's build).

### 2. How the predictions scored ([`retro/explore/retro4_calibration.py`](retro/explore/retro4_calibration.py), output [`.txt`](retro/explore/retro4_calibration.txt))

**What's scored:** every bet written before its test since retro 3 that now has a result, plus the yardstick batch's and the builds' ideas. "Held in part" counts as held, as before. Bets the tests never answered are left out (listed in the script). The Brier score is the average squared gap between the odds and what happened: 0 is perfect, and always saying 50% scores 0.250.

**The CEO's first number: 20 hunches (H93 to H112), 11 held.**

| | Bets | Held | Average odds | Brier | Pays (any held-out gain) |
|---|---|---|---|---|---|
| **Retro 4: all** | 20 | 11 (55%) | 51% | **0.230** | 5 |
| Football claims | 13 | 7 (54%) | 45% | 0.213 | **4** |
| Methods | 7 | 4 (57%) | 63% | 0.262 | **1** (H109) |
| Retro 3, for comparison | 14 | 7 (50%) | 53% | 0.177 | |

- **The CEO's calibration slipped back toward a coin:** 0.177 to 0.230.
- **The CEO's 50% bets all held (5 of 5); the 30% bets mostly failed (1 of 6).** The CEO sorted the bets well and was too timid at both ends. The 60-75% bets were the weak band (H96, H99, H103, H111 failed).
- **Methods held this time (4 of 7), but only one paid.** H100, H107 and H108 held by their pass rules as descriptions, and none improved a forecast beyond what we had. H109 is the exception: the CEO's plus-minus beats "no change" by 31% on weekly absences.
- **The running total over three retros:**
  - held: claims 22 of 31 (71%), methods 6 of 19 (32%);
  - paid, this round: claims 4 of 13, methods 1 of 7.

  So "football claims pay more than methods" still stands, on paying more than on holding.
- **A sharper split than claim or method** (for step 4): the CEO's claims about players' bodies held 5 of 5 (H93, H94, H95, H97, H98, all injury). The claims about what teams decide or how schemes match up failed 6 of 6: H103 scheme fit, H104 coaches seek roles, H105 teams target roles, H106 matchups, H110 intake after efficiency losses, H112 efficiency after intake.

**Claude, on the CEO's claim as worded (W6): 20 bets, 11 held, average odds 50%, Brier 0.193.**
- On claims Claude was sharp: Brier 0.139, against the CEO's 0.213.
- On methods Claude was worse than the CEO: 0.292 against 0.262. Claude bet low on H108 (25%) and H109 (35%), which held, and high on H99 (65%), which failed. P4 made Claude expect methods to fail on their pass rules, when they mostly fail on paying.
- **Bet by bet, Claude was closer on 13 of the 20, the CEO on 7.**

**Claude's side bets and ideas: 68 bets, 35 came true (51%) at average odds of 56%. Brier 0.220, better than retro 3's 0.260.**

| Claude's stated odds | Bets | Came true |
|---|---|---|
| 0 to 35% | 8 | 25% |
| 35 to 55% | 21 | 29% |
| 55 to 75% | 23 | **70%** |
| 75% and up | 16 | 69% |

- **The 55-75% band is fixed** (retro 3: 23%; now 70%).
- **The 35-55% band is too high:** 29% came true at 44%.
- **Size bets are still the weak spot: 6 of 23 came true at average odds of 57%.** Retro 3's lesson ("a size bet should start nearer 40%") wasn't applied enough: the size bets written after retro 3 still averaged in the mid-50s, and about a quarter came true. Examples:
  - a hamstring repeating 2x (1.22);
  - part-timers gaining 0.05 (−0.002);
  - proneness adding 0.5% (0.04%);
  - the hysteresis band's 14% (14.05%).
- **Lesson for Claude, made a rule for itself:** a bet on a size starts at 35% unless an earlier result of the same kind measured it.

### Waiting on the CEO (asked 2026-11-25)

1. **H5, H6 and H18** (open since retro 1, kept open at retro 3): keep them open again, or close them as not tested?
2. **Group A:** run I137, I28 and I97's data check here in step 3?
3. **Group D2** (I103, I117, I119): send them to the build chat as one batch, like the yardstick batch?
4. **For step 7:** what in the last two days' way of working helped, and what wasted time?

**The CEO's answers (2026-11-25):** "1; can we test those hunches? 2; no, we will test those ideas within the build and i want to do builds at night when i am asleep. 3; i do not have any new workflow ideas. 4; yes run group a now. then when group a finishes. please review all of our ideas and hunches to then spontaneously - and thoughtfully - create three to ten more ideas that we can test now or later. the goal is to almost replicate the google deepmind paper on large language models sleeping. we want to create a dataset of football knowledge so that we can iteratively improve our experts and find new features."

- **H5, H6 and H18 get tests** (designs below). All three have the CEO's odds from 2026-11-15, written before any test, so they count as before the test.
- **Group D2 (I103, I117, I119) is tested inside each expert's next build**, not as a batch. **Builds run at night,** while the CEO sleeps.
- **No new workflow ideas from the CEO.** Step 7 has Claude's proposal.
- **Group A ran (step 3).** Then the backlog and the hunches were read again for new ideas, modelled on Google's "Language Models Need Sleep" paper (step 5).

### 3. The quick groups, run (2026-11-25, discovery only; scripts in `retro/explore/retro4_*.py`)

**Group A:**

| Idea | Result | Claude's odds, scored |
|---|---|---|
| I97's data check: enough quasi-random absences? ([`retro4_i97_absences.py`](retro/explore/retro4_i97_absences.py)) | **Too few for the QB test.** The weekly roster codes mark the COVID list (R59, 2020-2021), fixed suspensions (R40) and indefinite ones (R30). Regulars (top players, and each team's main QB) missed **202 games** on these lists after their first game for the team: OL 74, DL 48, WR 26, TE 18, RB 17, **QB 9** (nine players, one game each). Suspensions almost all start before a player's first game, so they leave the count. For scale, vacated's absences for any reason number 2,737 | 50% that the free data mark too few: **came true** for QBs. The 40% QB slope and the 20% for other groups can't be tested |
| I28, a playoff flag for the traits ([`retro4_i28_playoffs.py`](retro/explore/retro4_i28_playoffs.py)) | **The bias is real, and the flag doesn't pay.** On 218 playoff rows, actual less forecast: pass rate over expected +0.010, shotgun +0.015, +0.44 seconds a snap (the sizes schemes-v2 found). A flag learned on earlier seasons changes playoff squared error by −1.9% (−6.8 to +2.2), +1.1% (−1.2 to +3.4) and −0.5% (−5.9 to +4.2): all ties. A constant shift is small beside one game's noise. A side result: the same teams pass *less* than forecast in their last three regular-season games (−0.015) | 75% (medium) that a flag beats the blends at about the stated sizes: **failed.** The sizes held; the forecast gain didn't |
| I137, the yardstick's rushing floor ([`retro4_i137_floor.py`](retro/explore/retro4_i137_floor.py)) | **The guess was wrong: it isn't the penalty pick.** The grid tops out at 1.0 while the target's SD is about 27 yards, so the picks are nearly least squares. But scaling the grid to the target changes nothing (role-table copies −0.53% to −0.55%). A one-standard-error rule, about 10 times the penalty, halves the copies' cost (−0.30%), and it also shrinks real gains (the role table +0.74% to +0.22%) and flips four verdicts (fine back roles lose; carries per run snap gains on rushing; on receiving the coordinates and their backs-only version lose). On rushing, the copies cost about 0.08% per noise column. The floor is the board's size (15,383 rows, few backs), not the rule | 55% that the copies' cost falls under −0.15%: **failed** (−0.30% at best). 70% that no counted input loses its verdict: **failed** under the one-SE rule |

**What it means:** a no-signal input costs about −0.5% on the rushing board under any reasonable rule, so a rushing gain means something only beside its copies, as test 4 already requires. The yardstick doesn't change. But the rushing verdicts depend on the penalty rule, so each night's replay re-scores them under a second rule (I142).

**Closed by Claude:** I28 and I137 killed; I97 killed (its QB test can't be run on 9 games; the usable part, the 202 non-QB games, became I143). **The backlog: 58, less these three, plus 6 new ideas (step 5): 61 open.** After the CEO's W10 yes: less I140 and I142, plus 8 dreams: **67 open.**

**H5, H6 and H18: how they'll be tested** (pre-registered now; the CEO's odds from 2026-11-15 stand, written before any test):

| Hunch | The test | Pass rule | Cost | The CEO's odds | Claude's odds |
|---|---|---|---|---|---|
| **H5** strength is conditional | Elo's saved walk-forward margins, 2016-2024. Each team's residual margin (actual less Elo's) split by four conditions: home or away; the opponent's QB in the top or bottom third (by dropback EPA to date); the opponent pass-heavy or run-heavy (pass rate over expected to date); leading or trailing at the half. For each, does a team's condition gap repeat between a season's halves, and does a team-by-condition term lower next games' squared error beyond Elo, walk-forward? | Held if at least one non-home condition repeats (split-half r 0.2+, interval above 0) **and** its term adds with an interval above 0 | Under an hour each (saved histories): retro-sized | 30% a large effect; 50% nothing worth keeping | 10% for a large effect; 75% that only home holds (P2, matchups tie). Unchanged |
| **H6** consistent measures predict other outcomes (sharpened, 2026-11-15) | Inside the first dream batch (I141): every measure in CONSISTENCY.md with a week r, scored on the yardstick boards it wasn't built for, with 19 copies each | Held if measures with week r 0.5+ count on another outcome more often than measures under 0.5, the difference's interval above 0 (bootstrap over measures) | A night build | "almost certainly true" (given for the first wording) | **50%** for the sharpened claim; 75% that few forecast beyond the overall rating |
| **H18** schemes predict whom teams pay | Contracts (the OverTheCap file snap-leverage read once) by team, position and signing year, 2017-2024: the share of new money a team spends at TE, WR and RB, on its last-season personnel rates (12 and 11 personnel, pass rate over expected), beside need (the group's departures, age, last season's spend) | Held if a scheme term adds to the need-only model with an interval above 0, held out by season | A session (the contract table's join) | 20% a modest effect; 50% nothing | **35%** (was 60%): P13, the CEO's claims about team decisions failed 6 of 6, and H105 found teams don't shop for roles |

### 4. The patterns, updated

| # | Pattern | New for it | New against it, or its limit |
|---|---|---|---|
| P4 | **Methods tie the simple version, or lose** | Refined: methods now hold as **descriptions** (H100, H107, H108 held) and still don't pay. The one that paid, H109, brings new information: who sat | Claude bet against methods' pass rules (H108 25%, H109 35%) and lost those bets: P4 is about paying, not about holding |
| P11 | Role first | The role table beats the coordinates and the pooled PCA (I113's build, F76); I135 (the table counts without his own target rates); I136 | |
| **P13 (new)** | **Bodies and usage hold; front-office decisions don't** | Claims about players' bodies held 5 of 5 (H93 to H98, injury). Claims about what teams decide failed 6 of 6: H103 scheme fit, H104 coaches seek roles, H105 teams target roles, H106 matchups, H110 intake after efficiency losses, H112 efficiency after intake. A team gives the role after arrival (H104's side bet); it doesn't shop for it (H105) | Not usage: how teams *redistribute* share when a player sits is real and pays (H109). It's the decision (whom to sign, which scheme to fit) that the free data can't see: contracts, medicals, price |
| **P14 (new)** | **Real but small loses to the board's noise** | I28 (a real playoff bias, too small to beat one game's noise), I137 (no-signal copies cost 0.5% on a small board), I97 (natural experiments too rare), H94 and H95 (real, never tried as forecasts). 31 hunches are real and never paid | The cure is pooling (I140 to I142): many small, real effects, tried together on every outcome with a false-discovery control, not one at a time |

**What the patterns say to do:** the CEO's next football bets should lean on bodies and usage (P13), not on what front offices decide. A method is worth testing when it brings new information (P4). The record now holds 31 real hunches that never paid and many consistent measures. That bank is the "day's experience" the sleep paper consolidates (step 5).

### 5. New ideas and predictions

**The paper** ([arXiv 2606.03979](https://arxiv.org/abs/2606.03979), Behrouz, Hashemi, Javanmard and Mirrokni, Google, July 2026; read from its abstract and two explainers, not the full text):
- language models learn well in context but can't move that short-term knowledge into their long-term parameters without forgetting old skills;
- the fix is a **sleep** phase after waking:
  - **consolidation** distils the short-term knowledge upward into long-term capacity, keeping the old;
  - **dreaming** has the model write its own practice data and keep only what makes a test copy better, so new learning doesn't overwrite old.

**The football version:**
- **Waking:** the day's builds and explorations. Their findings sit in many files, as short-term memory.
- **Sleep:** each night after the builds.
  - **Consolidation:** everything learned goes into one football knowledge dataset (I140).
  - **Dreaming:** the system writes its own candidate features from that dataset and tests each on a sandbox copy, the yardstick with shuffled twins. It keeps only what beats the copies (I141).
  - **Rehearsal:** it replays what we already know, so a change can't silently overwrite an old finding (I142).

**Six new ideas, as Claude's** (in IDEAS.md with their odds; size bets start at 35%, step 2's rule):

| # | Idea | The bet | Claude's odds |
|---|---|---|---|
| I140 | **The football knowledge ledger (consolidation):** one machine-readable table, a row per tested claim, measure or input. Each row has its id (H, I, F) and kind (claim or method). It has its subject (bodies, usage, skill, role, team decision, scheme, market) and its level. It holds the outcomes tried, its consistency (week r, season r, movers' share kept), its gain on its own target and on each yardstick board with intervals, and real? and pays?. It also holds when it's known, where its column lives (table, run id) and the odds written before. Built from HUNCHES, IDEAS, CONSISTENCY, FINDINGS and RESULTS, and rebuilt each night | It parses every F row and every closed H and I row with an outcome; it reproduces retro 4's calibration with no hand entry | **80%** for the parse; 60% that it reproduces retro 4's Brier scores within 0.005 |
| I141 | **Dreaming: a nightly candidate batch.** Candidates come from the ledger by fixed rules, not by hand: (1) **transfer:** every real-but-unpaid measure (31 hunches, plus consistent rows in CONSISTENCY.md) on every yardstick board and expert target it wasn't built for; (2) **within role** (P11); (3) **recency** variants. Each runs through `score_input` with 19 copies, and is kept only if it counts and survives a false-discovery control across the night (Benjamini-Hochberg at 10%). Kept ones enter the ledger as discoveries, never a champion without a build. **H6's test runs inside it** | The first night's batch | **55%** at least one candidate passes; 25% three or more; 35% the best adds 0.3%+ on some board |
| I142 | **Rehearsal: replay what counts.** Each night, every input the ledger marks as counting is re-scored on its board under today's code and data (the vault closed), and under a second penalty rule (I137's one-SE). A flip is flagged as forgetting before it reaches a build | The first replay | **40%** at least one counted input flips under today's code; 35% that a quarter or more flip under the second rule |
| I143 | **The COVID-list knockouts check vacated-live** (from I97's count): absences for injury may be confounded (a player playing hurt loses share before he sits). The 202 games regulars missed to the COVID list are close to random, so group-mates' share changes there should match the transfer rates fit on all absences | The plus-minus's pooled same-group rates on COVID-list absences against injury absences, the difference's interval | **65%** they agree (interval covers 0); 25% the COVID rate is higher |
| I144 | **A self-model: the ledger predicts verdicts.** A plain logistic on the ledger's tags (kind, subject, level, whether a cheaper input exists, consistency), fit on every bet through retro 4, predicts whether the next 20 bets hold and pay, before their tests. Scored against our own written odds | Brier on the next 20 bets | **35%** it beats Claude's odds on "holds"; 50% it beats both of ours on "pays" (the subject tag carries P13) |
| I145 | **Upward distillation into the crude forecaster:** fit the yardstick's lasso on a blend of the true outcome and the champion experts' walk-forward forecasts (soft targets), to steady the small boards (rushing) | The rushing and receiving rest-of-season boards, distilled against plain, with copies | **30%** it lowers rushing's squared error clearly. A yardstick change needs the CEO's yes; it's also a candidate for `player-opportunity` |

**Predictions moved by this retro:**

| Bet | Was | Now | Why |
|---|---|---|---|
| H18 (Claude's number) | 60% | **35%** | P13: team-decision claims 0 of 6; H105 |
| H6, sharpened (Claude's first number for it) | (none) | **50%** | The test exists now (I141) |
| I9, movers over-projected (participation's next build) | medium | medium | I84 and I122 gave it a slot and a vacancy prior; still open |
| I126, H111 where the group was left empty | 25% | **20%** | P13 and H111: who receives among stayers is a small slice |

Retro 3's predictions for the other open ideas, and for H71 and H74, stand.

### 6. The findings table

- **F89 (I25):** a new head coach's tendencies (shotgun, no-huddle, man rate) settle in 1-2 games, efficiency in many more.
- **F90 (I28):** playoff teams pass more over expected, use the shotgun more and play slower than their regular season says (+0.010, +0.015, +0.44 seconds a snap), but a playoff flag doesn't improve the forecast.
- **F91 (I137):** on the yardstick's rushing rest-of-season board, signal-free inputs cost about 0.08% per column under any reasonable penalty rule. Read a rushing gain only beside its copies.
- **"Use and ignore":** the teams' row adds F89 and F90.

### 7. Workflow changes, proposed (the CEO accepts, edits or rejects)

**How retro 3's accepted changes worked:**

| Change | How it went |
|---|---|
| W7, quick build work goes to the build chat as a batch | Worked: the yardstick batch ran and closed 8 ideas. The CEO now prefers ideas tested inside each expert's build (D2) |
| W9, an idea leaves Open with its result | Worked for every build since; three older rows were left over (cleaned at step 1) |

**Proposed now:**

| # | Change | Why |
|---|---|---|
| W10 | **Rehearsal and dreaming, inside the retro** (rewritten after the CEO's direction below; first written as a nightly cycle). Two new steps: **rehearsal** re-reads the findings table against everything since and marks contradicted rows unclear; **dreaming** reads all three logs (ideas, findings, hunches) and writes new, abstract ideas outside the normal path, each tagged `dream, retro N`. Every idea carries an origin tag (`project`, `retro N`, `dream, retro N`), past ones flagged too, and each retro scores how often each origin pays | The CEO's direction (2026-11-25, below): the three logs already consolidate; the dream is a retro step, not a nightly job, and not its own project |
| W12 | **Retros are triggered by two finished builds,** never by explorations or briefs started. Builds run at night; spot-checks and finishing in the morning | The CEO (2026-11-25): "So after builds, we should trigger retros" |
| W11 | **Claude's size bets start at 35%** unless an earlier result of the same kind measured the size | Size bets came true 6 of 23 at 57% (step 2). This is Claude's own rule, listed so the CEO sees it |

**The CEO on W10 (2026-11-25, word for word):** "Okay, so well, I think your consolidation and dreaming and the rehearsal is fair, but it's not quite what I was looking for. So what I was kind of looking for was instead of every night, it would be more of um, within the retro analysis or like these projects that we're doing right now, this retro analysis for, I would say like, okay, we have all of these ideas and hunches, and I guess I forgot about the findings table. I think you could use the findings table also because that also consolidates information that we have discovered. So I think it would be ideas, findings, and hunches. You look at all three of those, and because it's already consolidated, we're consolidating them when we build and when we explore and when we create briefs, right? We're logging those findings, we're creating new ones, we're testing them when we're doing the builds. And then I was thinking within the retro, we basically go over like a couple things. We go over like how have we been doing? Are we working together well? Do we think there's like, I don't know, do you think there's a new pattern we can do to be better and be more effective and discover more things with the data? And then also, it would be to basically allow you to do this sort of like um, this dreaming where you look at all of our past ideas, findings, and hunches, and you say, okay, this is what we thought, this is what happened, and if we extrapolate that, if you think about it and extrapolate it, just look at the patterns and say, okay, well, these worked, so can we make some really cool ideas from our past ideas, just the patterns, not even thinking about any project in the future or whatever, just like just really creative, really abstract, really new and fun and different. And then you write those up and now you just made a couple more ideas, and those ideas basically came from a process that's outside of our normal process because our normal process is, brief exploration or exploration, brief, and then build, right? That's and then spot check. That's our normal process, which is great, and we do a lot in that normal process, but it's guided a lot by me. And if you're coming up with ideas on the side within these retro analysis, I think that could be really powerful, and I think we can learn a lot, and we can create some really cool things with your guesses, with your dreaming. So I don't think it should be every night. I think having the builds done at nighttime is good. Um, but I think for the dreaming and the rehearsal, it should be during the retros. So during the retros, it's like, okay, and it doesn't have to be a huge process. It's just like it's we can make it its own project if you want it to be a really big process. If you think that would fit into our entire goal of building this product, if you think it should be its own project, like, okay, we're going to do a dreaming, or we're going to do um, a large language model sleep project or whatever, we can make that a new thing that we do once in a while, just like how we do retro once in a while. But I think it could just stay within the retros. And I also think for the retros should come after builds. They should be triggered by the builds. They shouldn't be triggered by the explorations. So just because we start a project, if we started 5 projects, that does not mean we should do a retro. But if we built 2 projects and we finish them, then we should do a retro, because if we're building stuff, that means we tested a bunch of ideas. We already did the exploration. We already did the brief. You tested all the hunches. So after builds, we should trigger retros. The brief and exploration should just be to start everything, and then at nighttime I can set the builds up and you can just run them while I'm sleeping, and then in the morning I can do the spot checks and we can finalize the builds. What do you think?"

- **W10 as written (nightly) is not what the CEO wants.** Dreaming and rehearsal belong inside the retro, read from the three logs that already consolidate what we learn: ideas, findings and hunches. Builds still run at night; the CEO's spot-checks and the builds' finishing happen in the morning.
- **Retros are triggered by finished builds** (two of them), never by explorations or briefs started.
- **Claude's answer:** agreed; dreaming stays inside the retro (an hour of reading and writing whose output is ideas, which already have a home), with an origin tag so later retros can score dreams against project-born ideas; rehearsal becomes a retro step too; the workflow step opens with the CEO's questions.

**The CEO's decisions (2026-11-25):** "Yeah, so you can rewrite W10 and W12 this way. I think that's great. I think what you listed out is great. But also, and you can totally start the your dreaming now. That would be great too. But one thing too to make sure is could you because you mentioned labeling the ideas as dreams or if they came from a dream or came from a retro. So if you do that, which I think is great, but could you also go back and look at our past retros and find which ideas you came up with and then go back and flag those ideas? So we have, some backwards data too, because I know we did this in the past, but that'll also be great to do moving forward. So yeah, you can proceed. Please dream now."

| # | Decision | Where |
|---|---|---|
| W10 (rewritten) | **Accepted:** rehearsal and dreaming are retro steps 5 and 6; every idea carries an origin tag, past ones flagged | `CLAUDE.md`, "The retro"; origins in `IDEAS.md` (below) |
| W11 | Claude's own rule (size bets start at 35%) | Claude's numbers from retro 4 on |
| W12 | **Accepted:** retros follow two finished builds | `CLAUDE.md`, "The retro" and the lifecycle's done step |

### After the CEO's yes: I140 to I142 re-sorted (2026-11-25)

- **I140, the ledger: closed, superseded.** The three logs already are the consolidated knowledge (the CEO's W10 direction), so a separate table would copy them.
- **I141 rewritten as one night build:** every real-but-unpaid measure scored on the boards and targets it wasn't built for, with copies and a false-discovery control. H6's test runs inside it.
- **I142 graduated into the retro:** rehearsal is now step 5 of every retro, run on the findings later work leans on.
- **I144** now reads its tags from the three logs; I143 and I145 are unchanged.

### Rehearsal (the new step 5, first run 2026-11-25)

Every one of the 91 findings was re-read against what came after it. Nothing was re-run this time: the CEO asked for the dream first, and the findings later work leans on most are F1 (target share is the player's), F23 (a moving back's share comes from who is left) and F76 (the role table). All three feed vacated-live, so its night build re-runs them as its first step, before anything is built on them.

| Finding | What later work says | Done |
|---|---|---|
| F62, QBs' red-zone carries | The vault (2025) reversed it; the row already says unclear | Stays unclear. I147 asks whether its seasons-won count would have warned us |
| F81, the rushing board's floor | F91 (I137) answered the cause F81 left open: the board's size, not the penalty pick | F81 now points to F91 |
| F40 and F45, the after-pressure part | F40 holds on the old provider; on the new one (2023 on) the trait sits in the pressure part (F45). Both rows already say so | No change |
| F36 and F37, efficiency | Not a conflict: efficiency earns more chances (F36) and doesn't last as efficiency (F37) | No change |
| F38 against F62 and F63 | F38 (kind of chance adds nothing) is for backs and receivers; F62 was QBs only and is now unclear | No change |
| F55, the row rule | Participation's yardstick worth moves 3-4 times with the row rule. The yardstick kept its own rule (participation's chance of a snap), so the later board rows (F74, F78, F82) are read as worth among players already expected to play | No change |

No other finding is contradicted by anything learned since.

### Dreaming (the new step 6, first run 2026-11-25)

**What was read:** all 145 ideas, all 91 findings and all 112 hunches. Five threads run through them:
- simple inputs from another expert pay (volume, role, the line, availability);
- fast traits are real but rarely pay;
- forecasts miss after changes;
- team totals are easier to forecast than player shares;
- the vault punishes inputs that win narrowly.

Eight ideas came out. They are tagged `dream, retro 4` in IDEAS.md with their odds, and none is tied to a project.

| # | The dream | From | Claude's odds |
|---|---|---|---|
| I146 | **The experts' miss matrix:** read every expert's misses against every other expert's outputs, and let the cells with signal say which feature should pass between experts | P9, P11 (what paid was another expert's output) | 60% one cell passes; 35% it adds 0.3%+ once built |
| I147 | **Seasons won as a vault-risk test:** an input that wins overall but in few of nine seasons is a vault risk | F62's reversal | 55% F62's input won fewer seasons than the median; 35% the count separates clearly |
| I148 | **Fast traits as a change alarm:** shotgun, no-huddle and quick-pass rates jump when an unrecorded change happens (a new play-caller, a hurt QB); the efficiency forecast shortens its memory after a flag | F89, F5, I47 | 45% flagged weeks miss more; 25% it pays |
| I149 | **Players must add up to their team:** scale player forecasts to the team forecast by their error variances (retail's reconciliation) | F54, F58 (team totals are readable) | 50% beats on receiving; 35% by 0.3%+ |
| I150 | **The market's update as a target:** do our Saturday experts forecast the move from the opening to the closing line? | F7, F50, F58 | 60% they explain 10%+ of it; 15% an edge |
| I151 | **Hidden injuries read from usage:** a healthy-listed player far below his snap forecast is likely hurt | I4, I143's confound | 50% beats the chain on absence; 30% pays |
| I152 | **Role drift:** where a player's role is heading, not only where it is | F76, F79 | 40% adds; 30% by 0.3%+ |
| I153 | **Historical analogs:** forecast a player-season from its 20 nearest past ones (weather's analogs) | F76, movers and rookies are thin | 25% beats alone (P4); 40% the blend adds |

**Where they go:**
- I147 is cheap: retro 5's rehearsal runs it on saved walks.
- I146 is a night build on saved walks only.
- I148, I149, I151, I152 and I153 go inside their experts' next builds.
- I150 waits for the betting cousin.

### Where ideas came from: the backward flags (2026-11-25)

Every idea born in a retro is now tagged in IDEAS.md. The tags were read from each idea's source and from each retro's own list of new ideas.

| Retro | Ideas born there | Count |
|---|---|---|
| 1 | I46-I53 (new ideas), I54-I56 (the follow-ups of I47, the retro's first pick) | 11 |
| 2 | I76-I78 (new ideas), I79 (the CEO's), I80-I83 (the idea review), I84-I88 (the backlog) | 13 |
| 3 | I113, I114 | 2 |
| 4 | I140-I145 (from the CEO's sleep question); dreams I146-I153 | 6 + 8 |

**How each origin has done so far** (counting closed ideas that had a test; I140 and I142 were closed without one, as were project-born I7, I12 and I18):

| Origin | Tested and closed | Graduated | Paid as a forecast |
|---|---|---|---|
| Retro-born | 12 | **8 (67%)** | 4: I80 (+4.2% receiving), I84 (backs), I113 (the role table), I114 (the opener, teams +5%) |
| Project-born | 64 | **28 (44%)** | not yet counted row by row |
| Dream-born | 0 | — | first scored at retro 5 |

**What it says:** retro-born ideas graduate more often. There are two cautions.
- With only 12 of them, the interval runs from about 40% to 85%.
- They were written with the patterns in hand, later, and often as the CEO's requested "safe" bets (I80).

Retro 5 counts "paid" for the project-born rows as well, and scores the first dreams.

**The CEO on the head start (2026-11-25, word for word):** "It seems like a head start, because you're already looking at all the other patterns and you're looking at the ideas and findings and what worked, what didn't work, and you're kind of making a guess on what would work in the future or what would be interesting to test, or even making an idea that you think will fail is good too, because then we know not to do that. We know that that path is blocked or constrained or restricted. So it's good to have failings too. It's what is really good is the thing that we really want is to know what we know and to know what we do not know. That's really the goal of everything in this project, and everything we do. We want to know what we don't know. And I think it is a head start, but that's kind of the point. The point is that it's a head start. The point that when you do this dreaming step, we can kind of like leapfrog some work or some tests or some thought process or some brainstorming. We can leapfrog it, and we can kind of like get ahead of the curve. So it's kind of the point to have a head start. And then I think which dream should run first? I guess. I don't know. You can do any of them. Any of them that are easy to test right now, go for it. And then if any of them fit like within an expert down in the future, like we can keep them there. But I mean, like any of them that are easy right now, just do. And if you don't do it, we'll revisit in the next retro. So I think you can do whatever you think. Your call."

- **The head start is the point.** A retro or dream idea that graduates more often is the step working, not a bias to correct. The score compares origins so the dream step can be judged, not so retro ideas are marked down.
- **A dream expected to fail is welcome.** A closed path is knowledge: we know what we don't know. Dreams may carry low odds on purpose.
- **Run the dreams that are easy now** (Claude's call); the rest wait in their experts' builds or come back at retro 5.


### The easy dreams, run (2026-11-25, the CEO: "Any of them that are easy to test right now, go for it"; discovery only)

Three of the eight could run on saved walks (2016-2024, the vault untouched). The rest need a build or new data, or re-runs:
- **I147:** the saved walks don't keep each input's base version, so it needs re-runs.
- **I149, I152, I153:** need `player-opportunity`'s build.
- **I150:** needs the betting cousin.

| Dream | Result | Claude's odds, scored |
|---|---|---|
| **I146, the miss matrix** | **34 of 180 cells pass.** It re-finds the yardstick's known inputs (participation, opportunity-quality and availability in the crude forecaster), a check that it works. New: participation's snap-share misses are read in production forecasts (the fantasy lasso +1.7%, opportunity-quality +0.7%); team-efficiency and Elo fill each other's misses (+0.4% to +0.6%); schemes-v2's tempo misses what pace knows (+1.7%). Graduated; F92 | 60% a cell passes: **came true**. 35% for 0.3%+ once built: waits for the builds |
| **I151, hidden injuries** | Real and small: after a big snap drop, the next game's absence is 1.2 points above the forecast (+0.4 to +2.0), in all 8 seasons; as a flag it ties. Killed; F93 | 50% beats the forecast: **came true, small**. 30% pays: **failed** |
| **I148, the change alarm** | Outside known changes, team-efficiency misses more after an alarm (offense +10%, defense +15% of the squared miss) but neither interval clears 0. Stays open for the shorter-memory test in team-efficiency's build | 45% flagged weeks miss more: **unclear, leaning yes** |

**What it means:**
- The dream step's first scores: one dream paid as a discovery, one was real but small, one is unclear.
- F92's new cells are named candidates for three builds:
  - **participation:** read production forecasts, F36's "efficiency earns opportunity" from the other side;
  - **team-efficiency and Elo:** read each other;
  - **schemes-v2's tempo:** read pace.
- F93 is a closed path. The report already knows most of what a snap drop says.

**The backlog after the run:** 67 open, less I146 and I151: **65 open.**

### The case against this retro

- **Step 2's scores lean on Claude's sorting.** Claim or method, and which side bets count, were sorted after the results (W2 was rejected). H111 as a method and H102 as a claim could each go the other way.
- **P13 rests on one week of hunches** from three projects (availability, roles, vacated). The six team-decision failures share data limits (no contracts, no medicals), so P13 may be "the free data can't see decisions" more than "decisions aren't football".
- **I137 tried only three rules.** A rule fit across several holdout seasons, or a stronger penalty grid, wasn't tried.
- **I28's test is small:** 196 rows, 8 seasons. A real 1% gain can't be ruled out.
- **The sleep mapping is Claude's reading of the paper from its abstract and two explainers,** not its full text. The football ideas stand on their own tests either way.
- **I141 is a multiple-testing machine.** The false-discovery control and the vault are what keep it honest. Its finds are discoveries, never proof.

- **I146's cells are one-column linear corrections on saved walks,** often on the overlap of two experts' rows. A cell's size is not what the input adds once built; the builds decide that.
- **The dreams are Claude's reading of the logs, in one sitting.** They are guesses with odds, as every idea is. The first honest score comes at retro 5.
- **The backward origin flags are Claude's judgment** for the follow-ups (I54-I56 are counted as retro 1's, though they came from running I47).

---

## Retro 3 (started 2026-11-23)

> The CEO, 2026-11-23: "Let's start the retro analysis for iteration number 3. What do you need from me?"

**Why now:** two projects finished since retro 2: `context-retro` (built 2026-11-22) and `opportunity-quality` (built 2026-11-22). `context-v2` (explored, its build was context-retro) and voe's fourth and fifth looks came in between.

**Read:** hunches H78 to H92 (15, all with the CEO's odds written before the test), ideas I84 to I112, and the projects since retro 2: `skill-over-expected` (third and fourth looks, brief agreed), `context-v2` (four looks), `context-retro` (built), `opportunity-quality` (built), `voe` (fourth and fifth looks).

**The steps,** in the charter's order: 1. sort the backlog; 2. score the predictions; 3. run the quick groups; 4. update the patterns; 5. new ideas and a prediction for every open one; 6. the findings table's summary; 7. workflow changes for the CEO.

### 1. The backlog, sorted (2026-11-23)

**Housekeeping first.** 19 rows sat under "Open" in IDEAS.md although they had a result (I13, I19, I22, I24, I33-I38, I40, I47, I73, I74, I89, I90, I94, I95, I102). They now sit under Graduated (7) or Killed (12), with their source, test and odds kept in the row. The real open count was 75, not 94.

**Closed by Claude (the CEO, 2026-11-20: "You have authority with the ideas, but I still want to learn about the ideas"):**

| Idea | Closed as | Why, in one line |
|---|---|---|
| I80, where a player's chances come from, in the yardstick | **Held** | opportunity-quality's build ran it (R14): expected receiving yards +4.15%, rushing +4.55% beside participation, above Claude's 1 to 3% |
| I46, incentive states beyond seed-locked | Killed | Its main bet failed in retro 2's batch; the rest needs standings math we don't have, and seed-locked already covers the big case |
| I26, matchup types learned from results | Killed | Real but tiny (r +0.03 to +0.05) and matches no charted style; matchups have tied every time (P2) |
| I27, outside runs against man-heavy defenses | Killed | One term of 308, at the edge of chance, and a matchup |
| I39, the play weights without DML | Killed | A reweighting of the same plays (P4), only needed for futures, which has no brief |

**The sort: 70 open ideas,** by what they need and what they cost (quick: under an hour; a session; expensive):

| Group | Ideas | Cost | Where it runs |
|---|---|---|---|
| **A. Quick, data in hand: run in this retro** | I87 (the total after a QB change), I91 (the rushers' forecast), I98 (the sorting test for VOE), I103 (trees for opportunity-quality's longer horizons) | Under an hour each | Step 3 |
| **D. Yardstick inputs: one batch** | I48, I58, I59, I60, I61, I67, I70, I75, I84 | Quick each through `score_input`; one batch | Step 3, after A (retro 2 sorted them and they never ran: the slip to fix) |
| **E. Player value on lower-noise outcomes** | I76, I77, I78, I79, I81, I82, I97, I99, I111; hunches H71, H74 | A session each; I76-I78 expensive in compute; I97 needs a data check first | skill-over-expected's build |
| **M. Context's next build** | I92, I93, I110, I112 | A session each; the CEO, 2026-11-22: "No split idea for now" on I110 and I112 | context-retro's next version |
| **B. Misses after a change, fixed inside an expert** | I4, I5, I9, I10, I11, I41, I54, I55, I56, I68 | A session each, inside that expert's next build | team-efficiency, participation, pace, crude-forecaster |
| **C. Ranges** | I1, I14, I42, I52, I85 | One session together (one coverage tool) | `pcf.validation`, then each expert |
| **G. Playing time** | I15, I16, I49, I51 | One session | participation's next build |
| **H. Coaches and schemes** | I21, I23, I25, I28, I71, I86, I88 | One session | schemes-v2's next look |
| **F. Fatigue** | I29, I30, I50 | A project | injury-fatigue |
| **J. Tooling, not bets** | I45, I62, I64, I66, I69, I72 | Done when a build next touches the harness | the build that needs it |
| **K. Wait for a live season** | I6, I8 | Nothing until 2026 ends | after the season |
| **L. Parked** | I20 (graduated, the CEO's answer below), I31, I32, I43, I57, I96, I104 | | their projects |

**What the sort says:** 13 of the 70 can run now (A and D). 36 wait for a build of an existing expert (B, E, G, H, M), so the backlog shrinks mostly when builds happen, not at retros. Group D is the one that should have shrunk since retro 2 and didn't: it was sorted as "one session" and no session picked it up.

**Open hunches (the CEO's to close):** H5 (strength is conditional), H6 (consistent measures predict other outcomes), H18 (schemes predict who teams pursue), all open since retro 1; H71 (the latent space of 22) and H74 (other experts as confounders), open since VOE's kickoff with no odds asked.

### Waiting on the CEO (asked 2026-11-23)

1. H71 and H74: odds now (they're untested, so they count as before the test), or park them with VOE.
2. H5, H6, H18: keep open, or close as not tested.
3. I20 (the CEO's consistency discovery): graduate it, since `CONSISTENCY.md`, the findings table and skill-over-expected's "whose trait is it?" now do what it asked?
4. For step 7: what in the last week's way of working helped, and what wasted time.

**The CEO's answers (2026-11-23):** "H71; 30% h74; 40%. H5, h6, and h18 keep them open. I20 yes graduated." On the workflow: "I think our current workflow is good. I like splitting my work/input between strategy and vision where I think thoughtfully. Then I let you build on your own and give me updates in the build and work chat."

- H71 30% and H74 40% are in HUNCHES.md, beside Claude's numbers from retro 2 (25% and 35%). They count as before the test: neither has been tested.
- H5, H6 and H18 stay open.
- I20 is graduated. **69 ideas are open.**

### 2. How the predictions scored ([`retro/explore/retro3_calibration.py`](retro/explore/retro3_calibration.py), output [`.txt`](retro/explore/retro3_calibration.txt))

**What's scored:** every bet written before its test since retro 2 that now has a result. H84 and I94 are left out (unclear), and so are bets the tests never answered. "Held in part" counts as held. The Brier score is the average squared gap between the odds and what happened: 0 is perfect, and always saying 50% scores 0.250.

**The CEO's first number: 14 hunches (H78 to H92 without H84), 7 held.**

| | Bets | Held | Average odds | Brier |
|---|---|---|---|---|
| **Retro 3: all** | 14 | 7 (50%) | 53% | **0.177** |
| Football claims | 8 | **7 (88%)** | 60% | |
| Methods | 6 | **0 (0%)** | 43% | |
| Retro 2, for comparison | 16 | 10 (62%) | 62% | 0.249 |

- **The CEO's calibration improved a lot:** 0.249 to 0.177. At retro 2 the CEO's odds did no better than a coin; now they clearly do.
- **The whole error is in one place: claims are under-bet, methods over-bet.** Claims came true 88% of the time at average odds of 60%. Methods came true 0% of the time at 43%.
- **The running total over both retros:** claims 15 of 18 held, methods 2 of 12.

**Claude, on the CEO's claim as worded (W6, first used this round): 14 bets, 6 held, average odds 39%, Brier 0.114.** Claude's numbers sat lower on methods (16% against the CEO's 43%) and about level on claims (57% against 60%). Most of Claude's edge is the methods, where Claude bets second, after seeing the design.

**Claude's side bets and ideas: 29 bets, 10 held (34%) at average odds of 52%. Brier 0.260, worse than a coin.**

| Claude's stated odds | Bets | Came true |
|---|---|---|
| 0 to 35% | 5 | 40% |
| 35 to 55% | 8 | 25% |
| **55 to 75%** | **13** | **23%** |
| 75% and up | 3 | 100% |

- **Claude was badly overconfident on its narrower bets in the 55 to 75% band** (3 of 13 came true). At retro 2 that band was right (9 of 12).
- **What the misses share:** most were bets on *how big* or *how precise* something would be once it was real: movers keeping 75%+ (14% kept), a weighting raising the fit (+0.02), the gap halving (44%), the 200-400 gap halving, time to throw being the QB's (it is partly the offense's). Claude got the direction right and the size too generous.
- **Lesson for Claude:** a side bet about size should start nearer 40% than 60%. Retro 3's new predictions (step 5) apply it.

### 3. The quick groups, run (2026-11-23, discovery only; scripts in `retro/explore/retro3_*.py`)

**Group A:**

| Idea | Result | Claude's odds, scored |
|---|---|---|
| I87, the total after an in-season QB change | **No edge.** The total is 0.57 points too high in games 1-4 after (-1.39 to +0.24), and the under wins 49.7%. With I83, the line prices a QB change on both the spread and the total | 45% that it's 1+ point too high: failed. 20% for an edge: right to be low |
| I91, the pass rushers' forecast | **It was the role.** Across outside linebackers, pressures add +15.1% to next season's sacks. Within rushers they add +0.8% (-4.4 to +5.5), and past sacks forecast nothing there either | 65% that the gain falls under half: held. 75% that it stays above zero: failed (the interval spans zero) |
| I98, the sorting test for VOE | **Closed without a run.** The movers' repeat already answers it (0.08 against stayers' 0.27), and here the test is confounded, because good teams sign genuinely good players | Not scored |
| I103, trees for opportunity-quality's longer horizons | **Moved to the build chat.** It needs harness runs inside a built expert | |

**Group D (nine yardstick inputs) goes to the build chat as one batch.** Each input is a new feature put through `score_input`, which is a build session's work, not a retro's. Retro 2 sorted it as "one session" and no session picked it up. W7 below is the fix. The batch's brief:
- **Run:** I48, I58, I59, I60, I61, I67, I70, I75, I84, and the new I114.
- **The rule for each:** it beats its shuffled copies and its interval clears zero, beside participation, as I69's rule says. The 2025 vault stays out.
- **Odds:** each idea's own row in IDEAS.md, written before this retro. Step 5 updates I84 and I59.

**The backlog after this:** 69 open, less I87, I91 and I98 (closed), plus I113 and I114 (step 5). **68 open.**

### 4. The patterns, updated

| # | Pattern | New for it | New against it, or its limit |
|---|---|---|---|
| P1 | "This habit is real, and it belongs to X" | H82 (sacks are the QB's, as pressure to sack), H83 (broken tackles are the runner's), H81 (coverage traits are weak but travel), I89 (throw depth is the QB's and the receivers'; time to throw is partly the QB's) | Narrowed again by P11: much of what travels is the role, not the skill |
| P4 | **Cleverer methods tie the simple version, or lose** | **The strongest pattern in the record.** H85 (diffusion, worse on all 11 outcomes), H89 (success), H90 (predictable plays), H91 (replacement level), H92 (a net and interactions), I95. The CEO's methods since retro 2: 0 of 6; over both retros: 2 of 12 | None. The one exception is a method that brings new information (H86: conditioning on the real pressure), which is really a claim about data |
| P5 | The gains are where history is stale or blind | H78's who-is-left (+6.8%); the blame split | **Limit: the market already sees the obvious changes** (I83, I87: the line prices a QB change on spread and total). Our edge from P5 is for players and props, not for the game line |
| P7 | Real is not the same as useful | H79, H80, H81, H83 are all real, and none was tested as a forecast; H86 is real but not a forecast; F43 (season over-expected priors don't pay) | I80 paid more than expected (+4%) |
| P9 | Volume carries player forecasts | I80: expected yards, which is volume weighted by where the chances happen, add 4% beside participation | |
| P10 | On-field value is the team's, except at QB | VOE's fourth and fifth looks: no outcome, reference, weighting or model makes a non-QB's plus-minus his own | |
| **P11 (new)** | **Role first: much of what repeats and travels is the player's role, not his skill** | I91 (a rusher's 15.1% was knowing who rushes), H80 (the outside linebacker's 97% was role), H79 (plain catch rate repeats more than catches over expected because it holds his role), H84 (measuring over the situation adds nothing: the situation he's put in is his role), H78 (who is in the backfield, not how good) | Not every trait: after-pressure handling is the QB's skill (F33, F40). Role is volume's cousin (P9): both say "what he's asked to do" carries more than "how well" |
| **P12 (new)** | **Before the snap, context explains little whatever the method; facts from after the snap explain a lot** | H84 and context-v2 (the situation explains 1 to 9% of an outcome), H85 (a bigger model doesn't raise it), H86 (given the real pressure, sack loss falls 31%), F41 | It's for retrospective experts (blame, credit) and never for forecasts before kickoff. It fits Claude's I99 and I111: credit each player on what happened at his job |

**What the patterns say to do:** read every player measure within his role before calling it skill (P11), and give player credit from after-snap facts (P12). Expect methods alone to tie (P4), so a method is worth a look only when it brings new information. The game line already knows about changes (P5's limit), so the betting edge has to come from props and player rates, where P9 and P11 live.

### 5. New ideas and predictions

**Two new ideas, as Claude's** (in IDEAS.md with their odds; Claude's size bets now start nearer 40%, as step 2 says):

| # | Idea | The bet | Claude's odds |
|---|---|---|---|
| I113 | **A role table:** for every player-season, his role in a few numbers (a rusher's rush share; a receiver's slot, wide or inline share and his depth; a back's share of his backfield), as the standard input every skill measure is read within (P11) | At least half of skill-over-expected's 14 measures repeat less once role is held | **65%** for half or more; size: the median repeat falls 0.05 or more, 40% |
| I114 | **The betting lines as yardstick inputs:** the spread and total known before kickoff, in the crude forecaster's team yards and the players' yards (P5's limit turned around: if the line knows, use it) | Team yards gained and allowed: the total and the spread add 2%+ of the remaining error | **75%** for team yards; 40% for players' yards (participation and expected yards already carry the volume) |

**Predictions moved by this retro:**

| Bet | Was | Now | Why |
|---|---|---|---|
| H71, the latent space of 22 (Claude's number) | 25% | **20%** | P4: methods 0 of 6 since retro 2. The CEO's is 30% |
| H74, other experts as confounders | 35% | **30%** | P12: the context explains little before the snap, so matching on it adds little. The CEO's is 40% |
| I84, running backs: the new backfield's split wins or ties | 65% | **75%** | H78: who is left in the backfield beats the old habit (+6.8%) |
| I86, the backfield split is the coach's | 55% | **35%** | H78 again: the coach's past split lost to who is in the room |
| I59, a pass-heavy team's receivers score more | 35% | **30%** | P9 and P11: volume and role carry it |
| I76 to I78, the causal player-value methods | open, as forecasts | **20% each to beat the plain version as forecasts** | P4, P10. They're still worth running for the question they answer: how much is the player's |

Retro 1's and retro 2's predictions for the other open ideas, and for H5, H6 and H18, stand.

### 6. The findings table

- **F49 (I91):** an outside linebacker's pressures forecast next season's sacks only because they say who rushes.
- **F50 (I87):** the closing total prices an in-season QB change, as the spread does.
- **"Use and ignore" now has a VOE row** (use the lasso for team values and a QB's plus-minus; ignore any non-QB's plus-minus as his own, and F46 to F48's methods). The pass rushers' and teams' rows now cite F49 and F50.
- **Still to do:** the first full fill, every project finished before retro 2. FINDINGS.md has said so since 2026-11-20.

### 7. Workflow changes, proposed (the CEO accepts, edits or rejects)

**How retro 2's accepted changes worked:**

| Change | How it went |
|---|---|
| W1, the obvious-input check | Worked. It's what made I91 visible: the obvious input for a rusher's pressures is whether he rushes |
| W3, odds with the hunch | Kept: all 15 hunches since retro 2 had the CEO's odds before the test. H71 and H74 got theirs today |
| W4, a backlog read at each exploration | Partly: I90, I94 and I95 were checked in context-v2, but group D sat untouched |
| W5, the findings table | Built and used (F1 to F50). The first full fill is still owed |
| W6, Claude's number on the exact claim first | Used on all 15. It shows the gap is in methods: on claims Claude's odds and the CEO's were about level |
| The sorted backlog | It shrinks when builds happen: 36 of 66 ideas wait for a build |

**Proposed now:**

| # | Change | Why |
|---|---|---|
| W7 | **Quick work that needs new features or harness runs goes to the build chat as a named batch,** with a short brief in RETRO.md, and is not left in the retro | Group D sat for a retro cycle. It's build work, and the CEO's split is strategy here, builds there (the CEO, 2026-11-23: "I let you build on your own and give me updates in the build and work chat") |
| W8 | **A stop rule for method looks:** when two looks in a row fail on one expert's data with methods alone, the next look must change the data or the outcome | VOE had five looks. The last two were methods on the same plays and failed as P4 predicted; the ideas that change the data (I97, I99) waited behind them. The CEO can still overrule it for any one look |
| W9 | **An idea with a result leaves "Open" in the same commit as its result** | 19 closed rows had piled up under Open, so the backlog looked like 94 when it was 75 |

**The CEO's decisions (2026-11-23):** "w7; approved. w8; declined. w9; approved."

| # | Decision | Where |
|---|---|---|
| W7 | **Accepted** | `CLAUDE.md`, the retro's step 3 |
| W8 | **Declined.** No stop rule: a method look can follow two failed method looks on the same data. Claude still states its odds first, and P4 stays in its numbers | |
| W9 | **Accepted** | `CLAUDE.md`, "The hunch scoreboard" (ideas) |

### The buckets after step 3, and what blocks each (the CEO's question, 2026-11-23)

> The CEO, 2026-11-23: "Can you tell me the buckets for backlog open ideas? What is stopping each bucket and which buckets are most appropriate for a retro analysis; which buckets need a build?"

68 open ideas. Group A (quick, run in the retro) is now empty.

| Bucket | Ideas | What's stopping it | Needs |
|---|---|---|---|
| **D. Yardstick inputs** | I48, I59, I60, I67, I70, I75, I84, I114 (8; I58 and I61 moved to td-expert's build) | Nothing but scheduling: each is a new feature run through `score_input` | **A build-chat batch: the CEO's pick, 2026-11-23** ([brief](crude-forecaster/YARDSTICK_BATCH.md)) |
| **E. Player value on lower-noise outcomes** | I76, I77, I78, I79, I81, I82, I97, I99, I111, I113 (10); hunches H71, H74 | skill-over-expected's build hasn't started (brief agreed 2026-11-20). I76 to I78 are heavy in compute; I97 needs a data check first (are there enough quasi-random absences?) | **A build** (skill-over-expected) |
| **B. Misses after a change** | I4, I5, I9, I10, I11, I41, I54, I55, I56, I68 (10) | They live in experts that are done (team-efficiency, participation, pace, crude-forecaster), and none has a next version scheduled | **Builds**, each inside its expert's next version |
| **H. Coaches and schemes** | I21, I23, I25, I28, I71, I86, I88 (7) | schemes-v2 is done, and no next look is scheduled. I23 and I25 already have first looks | **Mixed:** I23, I25 and I28 are discovery checks on tables we have (retro-sized); the rest need schemes-v2's next look |
| **J. Tooling** | I45, I62, I64, I66, I69, I72 (6) | Not bets: they're fixes to the harness or a model, done when a build next touches it | **A build** that needs them |
| **L. Parked** | I31, I32, I43, I57, I96, I104 (6) | Their projects don't exist yet (futures, roles-archetypes, the game simulator), or the CEO said wait (I104) | **Their project's kickoff** |
| **C. Ranges** | I1, I14, I42, I52, I85 (5) | No shared coverage tool in `pcf.validation` yet | **A build** (one tool, then each expert) |
| **G. Playing time** | I15, I16, I49, I51 (4) | participation's next build isn't scheduled | **A build** (participation) |
| **M. Context's next version** | I92, I93, I110, I112 (4) | The CEO, 2026-11-22: "No split idea for now" (I110, I112). I92 has no free data source, so it's a session; I93 needs a kickoff | **A build**, when the CEO lifts the hold |
| **F. Fatigue** | I29, I30, I50 (3) | injury-fatigue is still an idea in the registry | **A project kickoff** (strategy chat), then a build |
| **K. Wait for a live season** | I6, I8 (2) | The 2026 season has to finish (January 2027) | **A retro**, after the season: both are quick checks against ECR |
| **N. Inside a built expert** | I103 (1) | Harness runs inside opportunity-quality | **A build** (opportunity-quality's next version) |

**Retro-sized** (discovery on data we have, no package code): K after the season, I23, I25 and I28 in H, and I97's data check in E. That's 6 of 68.
**Build-sized:** the other 62. **The backlog now shrinks only when builds are scheduled.** Three builds would clear about half of it: the yardstick batch (D, 10), skill-over-expected (E, 10) and participation's next version (G plus B's participation rows I9, I10, I11 and I55: 8).

**The CEO's pick, 2026-11-23:** "Ok, the build chat should do the yardstick batch, d." The brief is [`crude-forecaster/YARDSTICK_BATCH.md`](crude-forecaster/YARDSTICK_BATCH.md). Writing it, Claude made three calls for the CEO's veto:
- **I58 and I61 leave the batch for `td-expert`'s build.** They're about touchdowns, and the yardstick is yards only, so the batch runs 8 ideas.
- **I48 is scored in yards**, not fantasy points.
- **I114 needs its timing settled first.** The schedule's lines count as known at kickoff, after the yardstick's Saturday moment. The batch reports the kickoff line as a ceiling and the earlier lines (ESPN openers from 2022) as the honest number.

### The case against this retro

- **The claim-or-method sort is Claude's,** made after the results (W2 was rejected). H86 and H87 could be read as methods and H88 as a claim. Moving them changes the counts (claims 7 of 8 could become 5 of 6; methods 0 of 6 could become 2 of 8), but not the gap.
- **The CEO's methods since retro 2 were all on exploratory or parked projects** (VOE, context-v2), where P4 was already expected to bite. That's part of why 0 of 6 looks so stark.
- **I91 rests on 164 rusher seasons,** so "+0.8%, spanning zero" can't rule out a real gain of 3 to 5%.
- **I98 was closed by argument, not by a run.** A run with a prior-season control could have been less ambiguous than the argument says.
- **P11 and P12 are fitted after the fact** on a few projects (skill-over-expected and context-v2 supply most of both). They are hypotheses until I113 and the build batch predict something in advance.


---

## Retro 2 (2026-11-20)

Read: hunches H50 to H77, ideas I46 to I79, and the five projects since retro 1: `crude-forecaster` (done), `opportunity-quality` (explored), `context-live` (done), `td-expert` (explored), `voe` (paused). Scoring: `retro/explore/retro2_calibration.py` and `.txt` (each bet as a row, its odds and whether it came true).

### 1. How the predictions scored

**Retro 1's predictions:** about 45 were written; **one has a result** (I47, high, held). Every other idea in retro 1's table is still open. The backlog check stopped after I47, and the open list grew from 32 to 60 ideas. That is a finding about the workflow (W4 below), not about football.

**The CEO's odds.** 16 hunches had odds written before their test. Left out: six whose odds came after the result (H58, H61, H62, H64, H65, H66), two unclear verdicts (H53, H63), H76 (odds not asked, Claude's slip), and the open ones (H71, H74, H77). "Held in part" counts as held.

| The CEO's confidence | Bets | Held | Which |
|---|---|---|---|
| 25 to 30% | 2 | 1 (50%) | H57 held, H60 failed |
| 40 to 50% | 3 | 2 (67%) | H54, H67 held; H68 failed |
| 60 to 70% | 5 | 2 (40%) | H50, H55 held; H52, H70, H73 failed |
| 75 to 80% | 4 | 4 (100%) | H51, H56, H59, H69 |
| 90% | 2 | 1 (50%) | H75 held in part; H72 failed |
| **All** | **16** | **10 (62%)**, at an average confidence of 62% | |

**The same 16 bets, the CEO's odds against Claude's** (Claude's number for the CEO's own claim, from the "Claude expected" column). A Brier score is the average squared gap between the odds and what happened: 0 is perfect, 0.25 is a coin flip.

| | Bets | Held | The CEO's average confidence | Claude's | The CEO's Brier score | Claude's |
|---|---|---|---|---|---|---|
| **Football claims** (what is true) | 10 | **8 (80%)** | 58% | 60% | 0.229 | 0.101 |
| **Methods** (how to measure it) | 6 | **2 (33%)** | 68% | 49% | 0.282 | 0.215 |
| All | 16 | 10 | 62% | 56% | 0.249 | 0.143 |

Claims: H50, H51, H52, H54, H55, H56, H57, H59, H67, H68. Methods: H60, H69, H70, H72, H73, H75 (Claude's sort; W2 would make it the CEO's).

- **In plain words: your football claims are better than your odds say** (8 of 10 held at 58%), **and your odds on methods run too high** (2 of 6 at 68%). Both of your 90% bets were methods (H72 in-game injuries, H75 the VOE model with sums). Retro 1 said claims pay more often than methods; this is the first time it shows in the odds themselves.
- Your 75 to 80% band went 4 for 4, and all four were "this is consistent" claims (H51, H56, H59, H69). That's P1 again.
- Claude's number was closer on 12 of 16. **That is partly position, not skill:** Claude writes after hearing the hunch, after seeing the data's shape, and designs the test that settles both bets.

**Claude's own 47 bets** (every probability in the "Claude expected" columns of H50 to H75 and the ideas I47 to I74 that have results): Brier 0.169, against 0.244 for always saying the base rate.

| Claude's confidence | Bets | Came true |
|---|---|---|
| 5 to 30% | 14 | 1 (7%) |
| 35 to 50% | 10 | 2 (20%) |
| 60 to 70% | 12 | 9 (75%) |
| 80 to 85% | 7 | 4 (57%): over-confident (H66a players repeat 0.5+, H68a red-zone chances in the top three, H72a a QB leaving mid-game shows a drop) |
| 90 to 97% | 4 | 4 (100%) |

Claude's low bets came true less often than stated, and the 80 to 85% band is the weak spot. Most of Claude's bets are "the usual way wins", which is usually right and is also the cheap bet to make.

**Sizes.** The CEO gave few. They ran small for volume (H51: "about 50%" of the explained variance from yards; it was 90 to 99%) and about ten times too large for situational and player effects (H63: 10% of rushing yards' error, it was 0.8%; H66: 10 points of success rate, it was 0.84). Claude's ran large for player effects too (H66: 1 to 2 points), and stated I47's size in a unit that couldn't be checked.

### 2. The backlog check (proposed; the CEO picks, as at retro 1)

Open ideas that cost under an hour, highest confidence first, with how each bears on the next cousin:

| Idea | Claude's odds (retro 1) | Cost | Why now |
|---|---|---|---|
| I53 which usage rates travel with a mover | high (target depth) | under an hour | The first rows of the per-position map (I79) |
| I44 clutch as a trait | high that it fails | under an hour | A "repeats or not" test, the map's kind of question |
| I21 stayers for coaches | high | about an hour | A difference in differences: the causal kind the CEO asked about |
| I17 a final-week share in playoff forecasts | high | under an hour | No link to the cousin; cheap and high-confidence |
| I14 ranges widen with swing | high | under an hour | No link; cheap |

Not under an hour: I4 and I55 (they need the harness). I26 and I27 need the 2025 vault, which is spent once.

### 3. The patterns, updated

| # | Pattern | New for it | New against it, or its limit |
|---|---|---|---|
| P1 | "This habit is real, and it belongs to X" | H55 (boom-or-bust repeats for backs and receivers), H59 (expected points 0.84 week to week), H57 (a mover keeps most of his role), H67 (touchdown tendencies are the team's) | **Narrowed:** it holds for what a player *does* (usage, habits, role), not for how well his team does while he plays (P10). H62 failed |
| P2 | "A matters only against B" | H65 (both sides' calls add up, nothing extra from the combination, on single plays too), H60 (scheme fit) | None. It now holds at play level as well, which retro 1 had as its exception |
| P3 | Don't throw plays away | No new test | |
| P4 | Cleverer methods tie the simple version | The small MLP did worse than the lasso; VOE's slots added nothing over the plus-minus sum; I74's prior barely moved values; H76 gave identical values; H60 | None |
| P5 | The gains are where history is stale or blind | I47 held (three experts biased after a change); I75 (the share of plays by new players: +4.6% offense, +6.6% defense); whole games missed (QB −0.049 EPA a play); participation first on all 9 player tables (H50) | H72: absence within a game showed nothing |
| P6 | Fatigue shows in who is on the field | No new test | |
| P7 | Real is not the same as useful | The strongest gain of any pattern: H55, H56 (goal-line chances worth 3+ points, nothing beyond counts), H58 (tight ends only), H66 (real, a tenth of the size), H68 | H61: efficiency did add +0.94% |
| P8 | Small exploration gains shrink in the build | context-live: rushing 2.5% became 1.2%, the box count 0.8% became 0.23 points, H66 0.84 became 0.7 | H50 held in the build |
| **P9 (new)** | **Volume carries player forecasts.** Who plays and how often explains nearly all of what can be forecast about a player's yards and points; efficiency adds under 1% | H51 (yards-only inputs keep 90 to 99%), H50 (participation first on all 9 player tables), H53 (attempts +13.6 to 29%, yards per attempt +0.4 to 2.7%), H56, H68 | H61 (+0.94%: efficiency earns opportunity), H54 (recent form, small). The limit: tested on totals (yards, fantasy points), not on rates, which some props bet on |
| **P10 (new)** | **On-field value belongs to the team, except at QB** | H69 (a mover's plus-minus repeats 0.07, a QB's 0.40, QBs carry +13.9% of a team's next offense), H70, H72, H75, I74, H76; earlier H27, H31; a whole game without the main QB costs 3 to 4 times what any other starter does | Usage travels (H36, H57). Untested: outcomes with less luck than EPA, which is exactly H77 |

**What the patterns say about the next cousin, before it starts:**
- **P10:** it works where one player owns the outcome (a pass rusher's pressure, a QB's completion) and struggles where a unit shares it (a lineman's pressure allowed, a runner's yards, which belong partly to his blockers).
- **P9:** even where it's real, it will forecast fantasy points mostly through volume. Its worth is rankings, the per-position map (I79) and rate-based props, more than the fantasy middle.
- **P4:** the causal methods (I76 to I78) will tie the plain version as forecasts. They are worth running for the questions they answer (how much is the player, how much the team), not for accuracy.

### 4. New ideas and predictions

New, as Claude's, each with its odds in [IDEAS.md](IDEAS.md): **I76** (the movers model, from labor economics: the player's part and the team's part), **I77** (double machine learning for rotating players), **I78** (synthetic control for long absences), **I79** (the per-position map of what to use and what to ignore: the CEO's idea, logged as an idea because it is a view to build, not a football bet).

The open hunches:

| Hunch | Claude expects | Confidence |
|---|---|---|
| H77 lower-noise outcomes show player value | Holds for pass rushers and QBs, fails for runners and for linemen credited one by one (P10) | 80% pass rushers, 70% QBs, 30% runners (the row's numbers) |
| H71 the latent space of 22 | Ties the plus-minus sums on EPA; more use as an input to other experts | 25% it adds 0.2%+ of a play |
| H74 other experts as confounders | Ties context-live on outcomes; helps as a control in I77 | 35%, 60% |
| H5, H6, H18 | Retro 1's predictions stand | |

Retro 1's predictions for the older ideas stand. One moves: **I59** (a pass-heavy team's receivers score more than their numbers say) from 45% to 35%, by P9.

### 5. Workflow changes, proposed (the CEO accepts, edits or rejects)

**How retro 1's accepted changes worked:**

| Change | How it went |
|---|---|
| Odds before every test | Mostly kept: 16 of 27 hunches since were scorable. It slipped when a hunch came in the same message that asked for a run (six odds given after the result; H76 with none) |
| The noise ceiling first | Worked: VOE's room (about 0.4% of a play) was known before anything was built on it |
| The crude forecaster | Built; it scored H50 to H55 on one yardstick |
| Strategy chat apart from builds | Working: context-live and crude-forecaster were built in their own sessions |
| The change lens | In the miss report (decision 0035) |
| Real? and pays? | Used on every row; it is what made P7 and P10 visible |

**Proposed now:**

| # | Change | Why |
|---|---|---|
| W1 | **The obvious-input check** (from retro 1, still undecided): every new trait is tested beside the one input most likely to carry it already, before a build is planned | H56 and H68 were volume in disguise; VOE's roster gain was partly the share of plays by new players, found only in the second look (I75) |
| W2 | **Tag each hunch as a claim or a method** (from retro 1, still undecided), by the CEO when it's made | It is this retro's biggest finding, and Claude had to sort the rows by hand after the fact |
| W3 | **Odds in the same reply that records a hunch, and no test in that reply** | H76's slip, the six after-the-fact odds, and H71 and H74 never asked |
| W4 | **One backlog idea per exploration:** every exploration also checks one open idea that touches its data | The open list doubled (32 to 60) while one idea was checked |
| W5 | **The per-position map as a standing view** in CONSISTENCY.md (I79), updated at every project's done step | The CEO's direction: "tell them exactly what they need to look at" |
| W6 | **Claude states its number for the CEO's exact claim first,** then any side bets | So the scoreboard compares us on the same event without anyone picking the closest number later |

**The CEO's answers (2026-11-20):**

On the claims-versus-methods result: "I think it kind of makes sense that my methods don't always hold true. I don't have like perfect knowledge of data science or like data science techniques or methodologies. So really like a lot of my stuff is pretty aspirational when I talk about methods. But I think also when I'm talking about methods, I'm more so talking about like maybe pushing you to try different techniques instead of just a really simple and basic one, because I think a really simple basic one almost always does pretty well ... But when I'm talking about football, it's really just like I'm kind of just like describing, you know, simple patterns that I've noticed or that I've heard people talk about ... If we apply those football theories to data, what do we expect to find? And that's really all I'm doing."

| # | Decision | The CEO's words | Where |
|---|---|---|---|
| W1 | **Accepted** | "testing each new trait beside its most obvious input, I think that's totally fine. I think that's good. We can do that." | `CLAUDE.md`, lifecycle step 2 |
| W2 | **Rejected** | "I don't want to tag each hunch as a claim or a method. I think that's too tedious." Claude sorts them at each retro, and says so | |
| W3 | **Edited:** odds stay with the hunch; when something said wasn't clearly a hunch, the CEO may add odds afterwards, marked and scored apart | "I think we mostly try to keep the odds with the hunches. I try to do that too, but it's not perfect. So sometimes I might say a hunch, but it didn't really like come across as a hunch, or I might be saying just my knowledge and it might come across as a hunch. So I think like I can apply retroactive odds. I'll try and be like as honest as possible." | `CLAUDE.md`, "Every bet states its odds first" |
| W4 | **Edited:** every exploration starts with a quick read of the backlog; it checks an idea only when one fits | "I think the explorations don't need to check a backlog idea. I think it should be practiced, at least at the very minimum, look at the backlog ideas, because those can really pile up ... if it fits perfectly within this expiration, then boom, that's great, let's do it. But it doesn't have to." | `CLAUDE.md`, lifecycle step 2 |
| W5, W6 | **Asked again, in plainer words** | "I don't know what W5 means ... Also, I don't know what W6 means" | Answered in section 7 |

H77's odds came in the same message, before any test: 70% for runners and defensive linemen (HUNCHES.md). That is the opposite end from Claude's 30% for runners. The next cousin settles it.

On `line-play` and `qb-talent`: "we can keep it more general than the line play and the QB talent, so this can feed into the line play and the QB talent." `skill-over-expected` stays general and feeds both (registry).

### 6. The idea review, before the merge (the CEO's ask)

The CEO, 2026-11-20: "before you merge Retro 2, I would like you to kind of do another review of the ideas and try and look at, like, okay, which ones held, which ones failed, and try and come up with 3 or 4 new ideas that we haven't tried that you think are, you know, that balance aspiration and integrity and validity, and, you know, give your odds."

**The record of the 83 ideas:** 23 have a result; the other 60 are open, three of them with a first look.

| | Ideas | What they have in common |
|---|---|---|
| **Held** (8) | I2, I13 (partly), I19, I33, I36, I38, I47, I73 (in part) | All but one are about **what history can't see yet** (P5): who changed, who is missing, what a team is playing for. I33 (the noise ceiling) is measurement hygiene |
| **Failed** (10) | I3, I22, I24, I34, I35, I37, I40, I63, I65, I74 | **Cleverer methods** (I34 luck-stripping, I35 stacking, I37, I40, I74: P4), **fit and matchups** (I22, I24: P2), and **team calls as a trait** (I65) |
| **Unclear** (5) | I1, I23, I25, I26, I69 (partly tested) | Mostly too few rows. Beside them, first looks only: I5, I9, I41 (the bias is still there) |

Claude's ideas follow the same split as the CEO's hunches: claims about where history is blind pay; new ways to weigh the same data tie. The backlog's open ideas lean the wrong way: about half are method or matchup ideas (I7, I12, I15, I16, I26, I27, I32, I39, I44, ...), which the record says will mostly tie.

**Four new ideas, from safe to long shot** (each in IDEAS.md with its test):

| # | Idea | The bet | Claude's odds | If it works |
|---|---|---|---|---|
| I80 | **Where a player's chances come from, in the yardstick**: opportunity-quality's expected points per game beside participation | Safe: volume weighted by where the chances happen (P9), and it repeats 0.84 | **85%** it adds to receiving yards; size 1 to 3% | A steady gain on the player forecasts that matter most for fantasy |
| I81 | **Linemen's absences measured on pressure, not EPA** | Middle: a lower-noise outcome on the natural experiment that already half-worked (I73) | **75%** for offensive linemen; 55% defensive; 35% that the size follows the player | The first per-lineman value with a natural experiment behind it |
| I82 | **What the coaches see**: snaps that rise or fall more than production explains, as a read of skill | Long shot: coaches watch film and practice; their choices may carry it | **25%** | Borrowed private information on rookies and backups, where our own numbers are thinnest |
| I83 | **Does the closing line share our blind spots after a change?** | Longest shot: I47's biases, checked against the market's spread | **15%** for an edge against the spread; 60% the line shows no bias | The first route to beating the closing line, PCF's first success test |

The case against the four: I80 may be past targets in disguise (P7, now checked first by W1). I81 has two seasons of expectations, so wide intervals. I82's signal may be the same box score the coaches read. I83 tests many games for a small edge, and the market has priced coaching and QB changes for decades.

### 7. The CEO's answers after the review (2026-11-20)

**W5, accepted and widened into a findings table.** The CEO: "I think W5 is pretty smart. I think having some sort of consolidation of information is definitely the way to go ... we're almost like running an organization in a way, like ... a lab, like we're doing a bunch of research, and we're having a bunch of findings, and we're almost like we're writing papers ... and it's all like gobbled up, and some is over here, some more is over there. It's not all in the same spot ... So I think things need to aggregate, just like it needs to be hierarchical, or else you and I will basically miss the findings ... that's my idea for, at least with the modeling, how we have like level 1, level 2, level 3, level 4 ... we're taking super complex raw data, and we're compressing it and expressing it and compressing it and expressing it over and over until we get one final answer that we can use confidently ... And I think the same applies for the findings ... for every position or for a team or for a season, we need to be able to say like, hey, this feature, it works. Oh, this other feature does not work. Oh, this feature is able to predict from here to here to here, but not over there. So it's almost like we would need like a table, like it would be like a meta table that talks about results and says, okay, like here's a feature. What's the granularity? Like how consistent is it? Like how predictive is it? What positions does it affect? What study did it come from? What idea did it come from? What hunch did it come from? All that kind of stuff ... I don't think we need to do it like that, but something like that." The design is Claude's call ("if you think that is the best way to do it, then that's how we should do it"). It becomes `projects/FINDINGS.md`, the top of the findings hierarchy (CLAUDE.md, "The findings table"); the first fill is a next step.

**W6, accepted.** "Sure, we can move forward with W6" (the voice transcript reads "W62"). Claude's first number beside a hunch is for the CEO's exact claim (CLAUDE.md, "Every bet states its odds first").

**The four new ideas.** "I think definitely linemen miss games measured on pressure instead of EPA. That's smart. I think ... idea 83 is the most intriguing because that would like right away give us some really good bets to take, but I don't know if ... it's actually going to be real or manipulatable. So out of the four ideas that you gave, they're all cool, but ... none of them really stick out at me as like we should go at the most." No CEO odds on I80 to I83.

**A new first step for every retro: sort the backlog.** "60, that's really surprising. I'm very surprised we still have 60 after all these things that we've been doing ... every time we do net retro analysis, we should look at all of the open-ended ideas and we should group them, cluster them and say, okay, these ones are really easy to do. Oh, these ones are a little bit harder to do, and these ones are, very computationally expensive. And then, okay, well, let's not do the computationally expensive ones right now, but let's group up the other ones and say, okay, well, these ones all fit under this project, and we can do them basically simultaneously ... I think that should honestly be the first step of a retro analysis is like do do the backlog of ideas because we just can't have that many ideas. Like what's the point of a retro analysis if we don't have this data to work from? ... If we always do this, we're always improving, then we'll make a good product." Written into CLAUDE.md, "The retro", as step 1. Retro 2's own sort (the 60 open ideas) is still to do; it replaces the five-idea check proposed in section 2.

**The merge:** "you have my approval to merge both. So I think it's all good to go." `pcf/voe` and `pcf/retro-2` merged into `main` the same day.

### 8. The backlog, sorted and a first batch run (2026-11-20, after the merge)

The CEO, 2026-11-20: "keep the findings table to just settled stuff ... I think for the ideas are mostly for you. I think it's good for you as Claude to like look for ideas and then label them, test them, and close them on your own, because it's a lot of them are pretty technical. For the hunches, you can ask me. We can keep that more my side ... You have authority with the ideas, but I still want to learn about the ideas ... I think for idea 83, the betting line idea, I think there's probably a 10% chance that holds. Well, maybe 15 ... I'd like it if you started with a backlog right now, sort the ideas, figure out which ones are pretty similar to each other, which ones are not too expensive to do, and then go ahead and figure out those ideas, log them in the findings ... Make 5 more, because now you have more data to look from." Written into CLAUDE.md ("The hunch scoreboard", "The findings table").

**The sort.** The 60 open ideas, by what they need and what they cost:

| Group | Ideas | Cost | Where it runs |
|---|---|---|---|
| **A. Quick, data in hand: run now** | I16 (step 1), I17, I44, I46 (final week), I53, I83 | Under an hour each | This batch (below) |
| **B. Misses after a change, fixed inside an expert** | I4, I5, I9, I10, I11, I41, I54, I55, I56, I68 | A session each, inside that expert's next build | team-efficiency, participation, pace, the lasso, crude-forecaster |
| **C. Ranges** | I14, I42, I52, I85 | One session together (one coverage tool) | `pcf.validation`, then each expert |
| **D. Yardstick inputs** | I48, I58, I59, I60, I61, I67, I70, I75, I80, I84 | Quick each through `score_input`; one crude-forecaster session for all | crude-forecaster |
| **E. Player value on lower-noise outcomes** | I20, I71, I76, I77, I78, I79, I81, I82 | The cousin's exploration; I76-I78 heavier in compute | skill-over-expected |
| **F. Fatigue** | I29, I30, I50 | A project | injury-fatigue |
| **G. Playing time** | I15, I16 (step 2), I49, I51, and I17's fix | One session | participation's next build |
| **H. Coaches and schemes** | I21, I28, I86, I88 | One session | schemes-v2 |
| **I. Markets** | I87 | Under an hour | the next batch |
| **J. Tooling, not bets** | I45, I62, I64, I66, I72 | Done when a build next touches the harness | the build that needs it |
| **K. Wait for a live season** | I6, I8, I27 | Nothing until 2026 ends | after the season |
| **L. Parked** | I31, I32, I39 (team-efficiency, only if futures need them), I43, I57 (roles-archetypes) | | their projects |
| **Closed by Claude** | I7, I12, I18 | | IDEAS.md, Killed, with reasons |

The groups are where the work is cheapest, not an order. Expensive in compute: I76 to I78 (the corrected movers model, double machine learning, synthetic control) and I45 (refits with several seeds).

**The batch (group A), discovery only, 2016-2024** (I83 2006-2024), scripts in `retro/explore/retro2_*.py`:

| Idea | Result | Claude's odds, scored |
|---|---|---|
| I83, the line after a change | **No edge:** 51.1%, 50.9% and 50.0% against the spread, none beats 52.4%. But the line is 1.0 point too kind after an in-season QB change (13 of 19 seasons) | 60% no bias: wrong in part. 15% an edge: right to be low. **The CEO's 10 to 15%: right to be low** |
| I44, clutch | **No trait:** QBs 0.08 against a null of 0.09, RBs 0.00, receivers -0.01 | High, no trait: held |
| I53, usage that travels | Target share (88% kept) and depth (85%) travel; carry share doesn't (35%); goal line in between | Depth travels: held. Target share is the room's: **failed** |
| I16, script tendencies (step 1) | Repeat for RBs (0.25) and TEs (0.29), not WRs | Medium, they repeat: held for two of three |
| I17, rested starters in the playoffs | Regulars on seed-locked teams +9.2 points of share in the first playoff game, fill-ins -9.7 | High, 3 to 6 points: held, larger |
| I46, eliminated teams (final week) | Young players: nothing (+0.3 points); Elo's margin +2.3, unclear | Medium, +1 to 3 points: **failed** |

Claude's batch: 4 of 6 main bets held, at a stated confidence around 70%.

**A correction found on the way.** I47's two in-season rows compared each team's games after a change only with its own other games after a change, because the flag is empty before any change. Against every team-game, an in-season change of starting QB leaves the offense over-forecast for 4 games (-0.039 EPA a play, 9 of 9 seasons) with no rebound after (+0.008). Elo's margin misses by 1.8 points in those games. So I54 is restated (a level for the new starter from his first game, not a lag), and the findings table carries the corrected version (FINDINGS.md, F5). Retro 1's "held in discovery" for I47 stands; only the rebound half of the QB row is withdrawn.

**Five new ideas** (IDEAS.md, I84 to I88), from what the batch found:

| # | Idea | Claude's odds |
|---|---|---|
| I84 | Each mover's usage prior from whoever owns it: his own for receivers, the new backfield's for running backs | 80% receivers; 65% running backs |
| I85 | Ranges after a QB change: the point-sized miss lives in a few blowouts, so the ranges there are too narrow | 60% coverage 4+ points low |
| I86 | The backfield split is the coach's | 55% |
| I87 | The total after a QB change: do unders win? | 45% a 1-point bias; 20% an edge |
| I88 | A coach's aggressiveness as his own read of his team's strength | 20% |

**The CEO's reading of I53 (2026-11-20), and a new hunch.** "It doesn't really surprise me that a running back's carry share does not travel with him, because running backs tend to be, in my opinion, tend to be extremely dependent upon their surroundings. So first of all, you have the entire offensive line, which is 5 people, sometimes even the tight end, which could go up to 6 people that have to block for you. And if any one of them makes a mistake, you instantly get tackled behind the line of scrimmage without any opportunity ... it's hard for a running back to create opportunity. They have to thrive within opportunities, and the team around them has to create the opportunities for them ... So why give the ball to someone when you know you can't help them succeed? With a wide receiver, they're much more independent. They only have to beat the cornerback and possibly maybe a safety ... They create their own opportunities ... the bare minimum is maybe they need the offensive line to have pass protection that is sufficient for their quarterback to even throw the ball, but that only matters for deep throws usually, because every other throw can be performed under 2 seconds." It agrees with P10 and F2. From I84 the CEO built H78 (HUNCHES.md, 30%): a moving back's share comes from who is in the new backfield and how good they are, not from the backfield's habit.

**The backlog after this:** 60 open, 7 settled or closed (I17 and I53 graduated; I44 and I83 killed; I7, I12, I18 closed), 5 new: **58 open**, each now with a group, a cost and a home. Quick ones left for the next batch: group D (one crude-forecaster session) and I87.

### The case against this retro

- The same reader sorted the patterns, scored both of us, and wrote half the bets. Nothing here is held out.
- Claude's better Brier score is partly position (it bets second, after seeing the data and designing the test). A fair head-to-head needs W6 and odds written before Claude sees the data.
- 16 scored CEO bets is few. One verdict changes a band by 20 to 50 points.
- P9 leans on `crude-forecaster` and P10 on `voe`: each pattern is mostly one project.
- The batch (section 8) is discovery on seasons our experts have seen. I53's movers are few (78 to 150 per rate) and chosen by volume in both seasons, so a back who lost his job on moving is missing from F2. I17 rests on about 100 regulars. Each fix still has to win through the harness.
- I83 tested three pre-registered sides and showed eight changes. The 1-point miss after a QB change was the one clear row, and it was predicted by I47's direction.
- "Held in part" counted as held is generous to both of us. Counting it as half (and H50, H54, H55, which held for one part only) moves the CEO's claims from 8 to 6 of 10 and methods from 2 to 1 of 6: the gap stays.

---

## Retro 1 (2026-11-15)

Read: all 50 rows of HUNCHES.md (H1 to H49), all 45 ideas (I1 to I45), and KNOWLEDGE.md. Not re-read: each project's RESULTS.md in full, so the sizes below are the logs' own.

### The record

| | Held | Failed | Unclear | Open |
|---|---|---|---|---|
| The CEO's hunches (50) | 21 | 15 | 11 | 3 |
| Ideas with a result (13 of 45, most of them Claude's) | 4 (I2, I19, I33, I36) | 7 (I3, I22, I24, I34, I35, I37, I40) | 2 (I13, I25) | 32 |

Of the tested hunches, 45% held. That is a good rate for bets against the usual way, and it hides a large spread between kinds of bet, which is the point of this page.

### Patterns

| # | Pattern | For it | Against it, or its limit |
|---|---|---|---|
| **P1** | **"This habit is real, and it belongs to X."** Claims that something repeats and has an owner (a coach, a player, a pair) hold about nine times in ten. This is the CEO's strongest kind of hunch | H10 (tendencies follow the coach), H23, H26, H28, H29, H33, H36 (tandems, r 0.83), H37, H38; I25 in part | H31: defenders carry a third of what skill players do. H27: QBs carry little to a new team |
| **P2** | **"A matters only against B."** Matchups, fit and conditional strength at the level of teams and games haven't held once | H9, H11, H12, H13, H14, H16, H49, H2b; I22, I26 so far | Real interactions exist on single plays (passing into 8-man boxes +0.12 EPA, schemes-v2#F21) and vanish at game level. About 4,000 games is too few (H9 needed 7,000), so this says "not measurable here", not "not true". Untested with player-level samples |
| **P3** | **Don't throw plays away.** Using every play, measured against an expectation, beats any filtered sample. The largest gains on the board | H22 (pace on every play: 0.85 against 0.66), H41 (every play counted: +3.9 to 7.5% over the garbage-time rule), I2 | None yet. Only tried on teams |
| **P4** | **Cleverer weighting, cleaning or method ties the simple version.** Whoever proposes it | H3, H4, H40, H42 (double machine learning), H43 (grains), H44, H45 (leverage weights); Claude's I34, I35, I37, I40 | H41's weights gained +0.3 to 0.9%, about the size of their own split luck. Methods mostly cost nothing either: they tie, they rarely hurt |
| **P5** | **The gains are where history is stale or blind.** Who is available, what a team is playing for, what changed since last season. The second-largest gains | H1 (absences), H2a (the pull between seasons, 0.21 points), H8 (seed locked, 0.43 points in the final week), the new-coach prior (+11.1% in weeks 1 to 4), I19, I13 | H2b: scaling the pull by roster turnover failed. I37: a mid-season QB change ties (the old QB's games still describe the offense) |
| **P6** | **Fatigue shows in who is on the field, not in how they play** | H34 held (linemen come off after two or three snaps); H24 and H25 failed (pace doesn't cause injuries or late collapses) | I29 and I30 are open leads the other way |
| **P7** | **Real is not the same as useful.** A trait can repeat strongly and add nothing once a simpler input is in the model | H33 (team substitution habit: nothing on top of the players' own habits), H35 (nothing on top of two snaps of memory), H15 (failed the vault), H28 ("a tell of the call more than a cause"), efficiency beside Elo (r 0.90) | Some redundant traits found a use elsewhere: `leverage_usage` as a feature, series success rate for its own future |
| **P8** | **A small gain in the exploration doesn't survive the build.** Gains under about 0.3% came back as ties or losses; gains of 2% or more held | Shrank: H45 (+0.14% became −0.23%), H42 (+0.2% to a tie), H44. Survived: H32 (1.9%), H41's full sample (4.6%), H36 (0.47% at the build) | The new-coach prior held at +0.3% in the backtest and then lost the 2025 vault. The models' own fitting noise is 0.1 to 0.2% (snap-leverage#R5) |

One more, from KNOWLEDGE rather than the verdicts: **nothing we've built adds to the closing line on sides and totals** (elo#F4, team-efficiency#R6, schemes-v2#F28). Where a consensus has shown a bias, it has been the fantasy consensus on specific kinds of player (questionable players, players at home: miss-lenses#F12, F13).

### What the patterns say to do

- Spend hunches where the record is strong: **who owns a measure (P1)** and **what the model can't see yet (P5)**. The CEO's open I20 ("whose trait is it?") is the highest-prior idea on the board.
- Treat any **team-level matchup** idea as a long shot until it's tried where samples are large (P2).
- Before any filter or reweighting, try **every play, counted equally (P3, P4)**.
- Ask of every new trait, in the exploration: **what does it add beyond the one obvious input (P7)?**
- Read a gain against the **noise ceiling and the fitting noise (P8)**, now the first step of every exploration.

### Predictions for everything open

Written 2026-11-15, before any of these is tested. Each idea's line is also in IDEAS.md ("Expected before the test").

| Expected to hold | Confidence | Expected to tie or fail | Confidence |
|---|---|---|---|
| I20 whose trait | high | I15 script-adjusted share | high |
| I21 stayers for coaches | high | I26 learned matchup types, live | high |
| I4 playing while questionable | high | I27 outside runs against man | high |
| I14 ranges widen with swing | high | I39 play weights without DML | high |
| I17 final-week share in the playoffs | high | I44 clutch as a trait | high |
| I47 the change lens | high | I7 multiplying conditions (in trees) | medium |
| I9 vacated snaps for movers | medium | I12 pre-trained tabular model | medium |
| I10 no depth-chart slot | medium | I16 script tendencies (repeat, but no gain) | medium |
| I5 rookies improve in season | medium | I23 receiver depth fit | medium |
| I8 ECR and home players (half size) | medium | I30 pass defense after a long half | medium |
| I28 a playoff flag | medium | I32 pass defense shrinkage | medium |
| I31 series success for drives | medium | I6 ECR and top questionable players (shrinks) | low |
| I41 new coach's defense (half size) | medium | I11 the bye (fades) | low |
| I42 season-shift ranges | medium | I29 long drives and injuries (shrinks) | low |
| I43 the passing-down role and contracts | medium | | |
| I46, I48, I49, I51, I52 (new) | medium | | |
| I50 backups rise with fatigue | medium | I50's second half: that it explains I30 | low |
| I53 target depth travels | high | I53: target share travels | medium that it doesn't |
| I1 ranges and expert disagreement | low | | |

The open hunches. The CEO's own odds were added on 2026-11-15, word for word in HUNCHES.md: H5, 30% for a large effect and 50% for nothing worth keeping; H6, "almost certainly true"; H18, 20% for a modest effect and 50% for nothing with our data.

| Hunch | Claude expects | Confidence |
|---|---|---|
| H5 conditional strength | Home holds, as it always has. Strength against the opponent's QB, coverage or game state fails at team level (P2) | medium |
| H6 stabilization | It finds consistent conditions (P1). Few of them forecast beyond the overall rating (P7) | high, then medium |
| H18 schemes predict the players a team seeks | Holds, small: coach-owned traits (P1) should show in who a team signs, mostly through personnel groupings (a team heavy in two-tight-end sets signs tight ends) | low |

### New ideas

I46 to I53 in [IDEAS.md](IDEAS.md), each with a test, a confidence and an expected size:

| # | Idea | From |
|---|---|---|
| I46 | Incentive states beyond seed-locked: eliminated teams, and clinched ones, in the last three weeks | P5 |
| I47 | One "games since a change" lens on every expert's misses | P5 |
| I48 | Garbage-time production counts for players too | P3 |
| I49 | Swap pairs say who inherits an absent player's snaps | P1, P5 |
| I50 | Fatigue shows as who is on the field | P6 |
| I51 | A probable starting QB from practice reports, not a yes-or-no one | P5 |
| I52 | Real but redundant traits belong in the ranges | P7 |
| I53 | Which usage rates travel with a player (the CEO's I20, for fantasy usage) | P1 |

### Workflow changes

**Accepted by the CEO (2026-11-15), now in `CLAUDE.md`:**

| Change | The CEO's words | Where |
|---|---|---|
| Confidence and expected size on every hunch and idea, before the test | "adding confidence and expected effect size is smart to each hunch and idea" | "Every bet states its odds first"; new columns in HUNCHES.md and IDEAS.md; the brief template |
| Football claims first; Claude more exploratory with methods; the CEO stays involved in methods | "I will try to focus more on football claims rather than methods, but I will ask for you to be more exploratory with methods"; "I do like to be involved in the methods, though" | "Football claims first, methods together"; a Methods section in the brief template |
| The noise ceiling first in every exploration | "Putting noise ceiling first in exploration is very smart" | Lifecycle step 2; the brief template; definition of done |
| Scheduled backlog checks and retros | "we could schedule backlog checks or retro analysis like this so that we always improve our building capabilities" | "The retro": after every second finished project |
| A crude forecaster to score incremental gains; the vision is many models and several products | "The vision can really be multi-model. I have a vision for a dashboard, summarized betting advice, a website, and general forecasts and diagnostics"; "we can draft a crude and simple forecaster to measure incremental gains" | "One yardstick for incremental gains"; `crude-forecaster` in the registry (an idea: its kickoff and brief are still to come) |
| Two questions beside every verdict: real? and pays? | "I think that will be useful to know, because it might suggest a discovery is significant when predicting a different outcome. So yes." | "The hunch scoreboard"; two new columns and a second tally in HUNCHES.md (rows before H50 filled in by Claude from each row's text) |
| The change lens in every miss report | "yes please add the change lens to the miss report" | The lens list of 2026-11-15 in `pcf.validation.misses`: `player_change` and `team_change` (decision 0035) |
| A strategy chat apart from the build sessions | "This chat is just the strategy and vision chat so we will only complete briefs and exploration in this chat" (later the same day, after "we can wait for now") | "Two kinds of session" in `CLAUDE.md`; first used for `crude-forecaster` |

**Rejected by the CEO (2026-11-15):**

- **A build bar** (a gain under the fitting noise makes a project an investigation). The go rule stays "unless there's literally zero signal": "I think this will be more of a in the moment call on the vision of the product. Some experts can be useful for telling a coherent story rather than explicitly as a distinctive forecaster. So I think the literal zero rule can hold." The noise ceiling is still reported first, as the evidence for that call.

**Proposed, not decided:**

1. **The obvious-input check.** In every exploration, each new trait is tested beside the single most obvious input that might already carry it (P7), before a build is planned.
2. **Tag each hunch as a football claim or a method** in HUNCHES.md, so the next retro can score the two kinds apart without Claude classifying them afterwards.

### Since retro 1

**I47, the change lens (2026-11-15, the CEO's first pick; `retro/explore/i47_change_lens.py` and `.txt`).** Discovery only: saved walk-forward histories for 14 forecasts, 2016–2024, each expert's average miss just after a change against the same weeks' other rows, weeks resampled.

| Expert | Change | Gap (result minus forecast) | Share of its typical miss | Seasons with the same sign |
|---|---|---|---|---|
| team-efficiency, defense | New head coach, games 1–4 | +0.034 EPA per play allowed (after: +0.010) | 35% | 8 of 9 |
| team-efficiency, offense | Starting QB changed in season, games 1–4 after | −0.024 EPA per play | 25% | 6 of 9 |
| team-efficiency, offense | The same, from the fifth game | +0.037 EPA per play | 38% | 8 of 9 |
| participation | A player's first game back from injury | +3.3 points of snap share (games 2–4: −1.0) | 28% | 6 of 6 |
| The lasso (fantasy points) | A player new to his team, his games 1–4 | −0.75 points | 16% | 9 of 9 |
| The lasso | Rookies, from their fifth game | +0.37 points | 8% | 9 of 9 |
| pace, runs | First game after a bye | +1.4 runs | 25% | 8 of 9 |

- 119 expert-and-change pairs were looked at; 19 clear the 99% bar where about 1 would by chance, 9 clear 99.9%.
- **Nothing clear** for ECR (three seasons only; its largest lean is −0.38 points for teammates of a new season-start QB in games 1–4), Elo's margin, or the scheme traits.
- **Scored against the prediction** (Claude, high: "holds for at least two experts; each bias worth 0.3 to 1.0% of that expert's range score on the rows it touches"): **held** on the count (three experts). The size was stated in the wrong unit to check here: the gaps are 16–38% of the typical miss on the rows touched, which is more than expected there, but those rows are about 5% of all rows and no correction has been fitted, so the forecast gain is unmeasured.
- **The case against:** the next-3-games targets overlap from week to week, so the team-efficiency intervals are too narrow (the season counts are the safer read). The first rows and the new-coach defense come from the same seasons as team-efficiency#R20, so that one is a sharper look, not a new test. "Games 5 on after a QB change" includes original starters coming back, which is part of why it runs high.
- **In the miss report since** (decision 0035): on participation's champion the first game back from injury is the top group (+4.3 points of share); both lenses' bias share is about 0.0%, so the biases are real and fixing them would move the overall error very little.
- **Follow-ups:** I54 (a level for each QB in the offense's rating), I55 (a games-since-return input for participation), I56 (an off-bye input for pace).

### The case against this retro

- The patterns were found and counted by the same reader, on the same rows, in one pass: no held-out verdicts. P2 leans on one project (`schemes-v2` supplies 8 of its 10 rows), P6 on three hunches.
- "Held" mixes sizes from 0.06 points to 7.5%, and mixes explorations with builds. A pattern counted by verdicts can be wrong about where the value was.
- Sorting a hunch into a pattern is a judgment. H41 sits in P3 (its full-sample part) and in P4 (its weights) at once.
- The predictions lean on the patterns, so if a pattern is wrong, its predictions fail together. That is also what makes them a fair test.
