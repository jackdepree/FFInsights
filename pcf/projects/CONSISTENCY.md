# Consistency register: which measures are signal, which are noise

> Every measure we build gets two tests (CLAUDE.md, "Two tests for every new measure"): does it help its project's target, and is it consistent? This page keeps the second answer, so a measure that's real but useless to one project isn't lost, and noise isn't built on. Started 2026-11-07 at the CEO's request.

**How to read it:**
- **Week r:** each team-season's average in odd weeks against even weeks, correlated across team-seasons. 1 means it's entirely about the team; 0 means it's luck, or the same for everyone. The margin itself is 0.51.
- **Season r:** a team's season average against its next season's.
- **Verdict:**
  - **trait:** repeats within and across seasons; something a team *is*.
  - **state:** repeats within a season but not across; something a team is *in* for a while, like an injured quarterback.
  - **noise:** doesn't repeat week to week.
  - Each r has a 90% interval; a verdict is given only when its interval clears zero ([`pcf.validation.consistency`](../src/pcf/validation/consistency.py)).
- **Helps its target:** the project's first test, with the size. "Not tested" means it was only measured.
- **Per team per regular-season game,** net of nothing unless the name says so (a team's own value, or the value it allowed).

| Measure | Project | What it is | Week r (90%) | Season r | Verdict | Helps its target? | Note |
|---|---|---|---|---|---|---|---|
| Same-team share | elo (H1) | Share of a team's usual snaps available this week | 0.83 (0.81–) | 0.40 | trait | Yes: −0.02 points on next margin, more with the QB (F15) | Some teams are reliably healthier from season to season, not just this season. Worth asking why (age, medical staff, depth) |
| Usual QB missing | elo (H1) | Starter out or off the roster | 0.66 (0.61–) | 0.03 | state | Yes: −0.04 points (F14) | Injuries last for weeks but don't carry over to next season, as expected |
| Points scored | elo | | 0.55 (0.50–) | 0.44 | trait | In the rating (F4) | Offense repeats more than defense |
| Pass EPA, offense | elo (H7) | Expected points per pass play | 0.53 (0.49–) | 0.45 | trait | No, on top of the points rating (F18) | The most consistent efficiency measure. Use it where points aren't the target: game script, play mix, fantasy |
| Margin | elo | | 0.51 (0.46–) | 0.41 | trait | The rating's input | The reference |
| Average win probability | elo (H3) | Mean home-team win probability across a game's plays | 0.41 (0.36–) | 0.39 | trait | Barely: −0.02 at best as a blend (F11) | Less consistent than the margin it summarises |
| Rush EPA, offense | elo (H7) | Expected points per run | 0.40 (0.35–) | 0.34 | trait | No (F18) | |
| Points allowed | elo | | 0.36 (0.31–) | 0.31 | trait | In the rating (F4) | |
| Rush EPA allowed | elo (H7) | | 0.31 (0.25–) | 0.27 | trait | No (F18) | Run defense repeats more than pass defense |
| **Finishing** | elo (H3) | Result (win 1, tie 0.5, loss 0) minus average win probability: high when a team wins games it "shouldn't have" | 0.28 (0.22–) | 0.22 | **trait** | No on margins: +0.00 in rung 3 (F23). Win chances not tested | **The CEO's late-underdog-win idea, measured directly: it repeats.** Some teams reliably finish better or worse than their game control says, and it carries into next season. A candidate for H5/H6 (game-state strength) and win forecasts |
| Pass EPA allowed | elo (H7) | | 0.25 (0.20–) | 0.28 | trait | No (F18) | |
| Kicking luck, own | elo (H4) | Field goals and extra points against the league's make rate at that distance | 0.24 (0.18–) | 0.30 | trait | Removing it: +0.00 (F8) | Kickers differ: it's skill, not luck |
| Return TDs allowed | elo (H4) | Defensive and special-teams TDs given up | 0.17 (0.12–) | 0.17 | trait | Removing it: +0.02 (F8) | Ball security and coverage units are partly a team trait |
| Kicking luck, opponent | elo (H4) | The other team's kicking against the league's rate | 0.16 (0.11–) | 0.28 | trait | Not tested | Probably the home stadium (domes, wind, altitude), not the opponents. A candidate for the environment expert |
| Long TDs scored | elo (H4) | Offensive TDs of 40+ yards (expected points) | 0.15 (0.09–) | 0.13 | trait | Removing it: +0.01 (F8) | Weak |
| Interceptions caught | elo (H4) | Expected points gained by the defense on interceptions | 0.12 (0.06–) | 0.11 | trait | Not tested on its own | Weak |
| Interceptions thrown | elo (H4) | | 0.11 (0.05–) | 0.17 | trait | Removing both: +0.09 (F8) | Weak within a season, a bit stronger across (quarterbacks persist) |
| Return TDs scored | elo (H4) | | 0.07 (0.01–) | 0.21 | trait, barely | Removing it: +0.02 (F8) | Hardly repeats within a season, but does across: return units and opportunistic defenses persist |
| Long TDs allowed | elo (H4) | | 0.03 (−0.03–) | 0.09 | noise | — | Big plays given up are luck |
| Fumble-recovery luck | elo (H4) | Who recovers a fumble, against the average fumble | −0.05 (−0.11–) | 0.05 | noise | Removing it: +0.02 (F8) | Pure luck, as the CEO said. It still didn't help the rating, because over a dozen games it averages out |

Measured 2026-11-07 with [`projects/elo/explore/consistency_so_far.py`](elo/explore/consistency_so_far.py): 829 team-seasons, 1999–2024 regular season (384 from 2013 for the snap and injury measures). The vault (2025) isn't read.

**Caveat for state-like measures:** odd and even weeks sit next to each other, so a measure that lasts for weeks (an injury) looks consistent week to week. The season r tells a trait from a state.
