# 0042: the yardstick batch, its technical calls

**Date:** 2026-11-23 · **Decided by:** Claude (technical calls, listed for the CEO's veto at merge), inside the batch's brief ([`projects/crude-forecaster/YARDSTICK_BATCH.md`](../../projects/crude-forecaster/YARDSTICK_BATCH.md), the CEO's pick at retro 3: "Ok, the build chat should do the yardstick batch, d.") · **Project:** `crude-forecaster` (discovery: nothing ships)

## The scorer

1. **`score_input` gains the shuffled copies** (`copies=19`) **and the counts rule** (I69, R7): the input's columns shuffled together within each week, refit through the same walk; a gain counts when its 90% interval clears zero and it beats every copy. The largest copy's gain (`copies_max`) and `p` are returned for every row, so every table prints them (I69's caution). Additive: old calls give the old result.
2. **`score_input` gains `beside`** (expert groups in both forecasts) **and `existing`** (board columns as the input), so "alone and with participation in" (the registry's `how_to_use`) is one call, and an expert's own column can be scored on its own (I59's PROE).
3. **Beside participation for players, beside Elo for teams.** Participation has no team rows; Elo is the team boards' obvious input (R5; the obvious-input check, retro 2).
4. **Each bet's verdict reads the added-alone number** (method A, the yardstick's headline), unless the bet names what it sits beside (I59: "once the offense's quality is in": participation and team efficiency). The readings were written into `explore/yardstick_batch/run_batch.py`'s header before any result.

## New boards

5. **QB rushing (I67) is a target the yardstick can score but doesn't publish** (`qb_rushing`, QBs expected to play): made on first use by `variant("qb_rushing", ...)`, kept out of the 48 published variants and out of `find`. Adding it to the published yardstick would change what the yardstick predicts, which is the CEO's call (CLAUDE.md, sign-off list).
6. **The depth-chart row rule (I70)** is a second row rule (`ROW_RULES`: `participation`, `depth`): a row is a starter or the first backup (depth 1 or 2) at his listed position on the depth chart going into the game (known at the week's start), whatever participation expects. It still needs participation's forecast for the row (its columns are the thing scored), so a player participation didn't forecast isn't a row.
7. **Boards under another rule have their own folders** (`boards/<target>_<horizon>_depthrows`); the published boards are untouched.

## The inputs (`pcf.baselines.crude.inputs`)

8. **Every input is made from what was known at its row's moment**, read through the gateway at the end of time and filtered by each row's `as_of` (a row's moment differs within one call). The ceilings say so in their names (`*_hindsight`, the kickoff line).
9. **I48, garbage time:** the tag table's rule (4th quarter with a 17+ point margin, or 3rd with 28+); a player's garbage-time yards per game this season so far and last season (`gt_y_s`, `gt_y_ls`), from the play-by-play, beside the board's pooled averages (the lasso's weight on them is the garbage yard's weight minus the rest's). The weight per yard is read by an OLS of next game's yards on the split averages (rest and garbage, this season and last), with a 90% interval from 300 resampled weeks: a description, not a forecast.
10. **I60, availability:** a crude forecast of the share of games he plays, `av_rate` = (games played so far + 4 × last season's rate) / (team games so far + 4), a newcomer's last-season rate 0.8; `av_y` = his yards average × `av_rate` (yards per game played times games played: the rest-of-season target counts an absent week as 0); this week's final injury report (questionable or doubtful; limited or no practice), known at the Saturday run; the share of this season's weeks he was listed out or doubtful. No fitted parameters (the 4 and the 0.8 are set, not fit), so nothing can leak. Teams: the week's depth-chart starters' `av_rate` (QB; QB, RBs, WRs, TEs). The hindsight version (the share of the window's games he did play) is the ceiling.
11. **I75, continuity:** pre-season, the share of the team's week-1 depth-chart starters (depth 1) with no NFL snap the season before, offense and defense apart; hindsight, the share of the season's snaps that went to such players. A player who changed teams counts as having played (the idea's rule). On the team board the offense's own and the opposing defense's (this row's yards allowed) are scored apart. Week-to-week consistency is 1 by construction (one value a season); only season-to-season is read.
12. **I84, movers:** a mover is a player whose team isn't the one he played most games for last season, in his first 4 games this season. Own prior: his last-season share of his old team's volume (targets over pass attempts; carries over carries, in the games he played) × the new team's volume per game last season. Slot prior: the new team's k-th biggest share at his position last season, k his rank on the new team's depth chart going into the game (depth, then label). Both × his own last-season yards per target or carry, 0 for everyone else, with a flag for the rows. Receiving: WRs and TEs; rushing: RBs. Which prior wins is a paired comparison on movers' rows.
13. **I114, the lines' timing: option (c), both** (the brief's recommendation):
    - **The ceiling:** the schedule's line (near the close, known at kickoff, DATA_SOURCES), flagged as "the line at kickoff". **It is never known at the Saturday run** and is never reported as if it were.
    - **The honest number:** ESPN's opening lines, already in our data (the odds collection's parse, `interim/espn_odds/game_lines.parquet`: no new source). Openers are posted early in the game's week, so they're known at the Saturday run (and the Thursday run for Thursday games). **2022 has no opening values in ESPN's history** (the raw files carry only the current line), so the openers cover 179 games of 2023 and 271 of 2024. The median over books, live-odds feeds left out; the sign was checked against the schedule's spread (r = 0.94).
    - **How the honest number is fit:** the lasso trains on earlier seasons' kickoff lines (all known long before any later season's fit, so nothing leaks into a forecast) and forecasts 2023-2024 with the openers; only rows with an opener are scored, against the crude forecast on the same rows. The ceiling is also scored on those rows, so the two can be set side by side.
    - The inputs: the team's expected margin, the game total and the team's implied points (total / 2 + margin / 2).

## Reading the results

14. **I67's "the crude forecast removes 20-35% of the error"** is read as `removed()`, the share of squared error around the scored rows' average (the exploration's unit), next game.
15. **I70 compares on each board's own rows:** participation's gain on depth-chart rows against its gain on participation's rows, both from this run (R3's numbers are the reference).

## After the results

16. **The yardstick's row rule stays participation's** (I70): depth-chart rows triple participation's worth, mostly with listed players who don't play (the easy zeros the brief's rule avoids).
17. **"Beside Elo" gains on team rest of season are checked against the plain crude forecast** (`check_beside_elo.py`), because Elo alone doesn't help that board (−0.86%): a gain beside it may only repair Elo. Both I60's and I75's team gains survive the check and are read as a lead (I115), not as the ideas' verdicts, which stay on the added-alone numbers set before the run.
18. **Ideas closed** (W9, in the same commit as the results): graduated I60, I67, I84, I114; killed I48, I59, I70, I75. New idea I115. Findings F51-F58. No odds were added or changed after a result.
19. **`I114`'s first run failed** (the lines builder dropped a team board's `team` key); fixed and rerun before any I114 number was read. The I75 run was repeated once to add the hindsight versions beside Elo (a check, not a change of reading).
