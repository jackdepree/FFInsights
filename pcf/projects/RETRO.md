# Retro: what the record says, and what to try next

> The loop that learns from our own log (CLAUDE.md, "The retro"). After every second finished project Claude reads every hunch, idea and verdict, and writes here: how the last predictions scored, which kinds of bets hold, a prediction for every open idea and hunch, new ideas, and proposed changes to how we work.

- **A pattern is a hypothesis, not a finding.** It was fitted after the fact, on a few dozen verdicts that come in clusters (one project can supply most of a pattern). It earns trust only by predicting verdicts before they're known, which is what the predictions table is for.
- **Confidence means:** low, medium, high: roughly 60%, 75%, 90% sure the stated outcome happens. A retro scores them by counting how many in each band came true.
- **Where things go:** new ideas go in [IDEAS.md](IDEAS.md) as Claude's (I46 on); the CEO's edits can turn one into a hunch ([HUNCHES.md](HUNCHES.md)). Accepted workflow changes go in `CLAUDE.md`.
- **Next retro:** after the second project finished from 2026-11-15 on. That point came on 2026-11-19 (`crude-forecaster` and `context-live`). **The CEO postponed it** the same day: "I would personally like to hold off on the retro analysis number 2 ... I want to do VOE and maybe one other cousin, or maybe even some explorations first ... So I would like to push out retro number 2. We can do that later after we learn a lot from VOE and some experiments." Retro 2 runs after VOE and one or two of its cousins (`projects/voe/BRIEF.md`). **The CEO started it on 2026-11-20**, when VOE was paused: "let's start the retro 2 now, the retro analysis, and kind of look back. Keep asking me questions, keep telling me the limitations, keep telling me the constraints, the assumptions, because anytime I can push back, then we're getting value, and anytime you push back on me, then we're hopefully getting value and we're staying true and we're staying valid." Retro 3 comes after the next two finished projects.

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
