# 0043: availability's exploration and brief, their technical calls

**Date:** 2026-11-24 · **Decided by:** Claude (technical calls, listed for the CEO's veto at merge) · **Project:** `availability` (exploration and brief; nothing ships)

## The events

1. **In-game injuries come from the play-by-play's description:** `([A-Z]{2,3})-(\d+)-([A-Za-z\.'\- ]+?) was injured during the play`. Each is matched to a player by roster team, jersey number and last name: 9,503 of 9,617 matched (98.8%). The rest are dropped.
2. **Time missed is the team's games before his next game with a snap, within the season.** A season that ends first is censored. Any game without a snap counts, so a benching right after an injury counts as time missed.
3. **Not injuries:** report lines containing "not injury", "illness", "rest", "personal", "coach" or "suspen" are left out of H94's body parts.

## The scoring

4. **Walk-forward by season, scored 2017–2024; 2017 fits on itself** (it has no earlier season of rows), and the 2025 vault is untouched.
5. **Intervals are Poisson-bootstrap draws over team-weeks (player-games) or players (player-seasons).** A gain counts when its 90% interval is above 0.
6. **Proneness is shrunk by credibility,** Z = n / (n + k), where n is his expected injuries and k comes from the over-dispersion's τ² (half weight at about 2 expected injuries).
7. **The per-play model is a weighted cell logistic** (one-hot features and feature × position group), fitted on earlier seasons only. Its risk is what H96 and H98 read.

## The H96 follow-up

8. **Two addenda were added after seeing a result,** each written down before its own run:
   - **G, log exposure:** the first run's same-game ceiling came out negative, which pointed at the straight-line shape.
   - **H, touches against other contacts:** D's contacts include the usual way's touches.
9. **Personal contacts:** carries, catches, a passer's sacks and hits taken, and tackles made (solo, assisted, with assist, sacks and half sacks, QB hits). Each counts once per play.

## The brief

10. **Health absence means on the injury report (any status) or a reserve list.** A release or trade isn't a health absence; it's participation's.
11. **Adjusted games lost weights each game lost by his snap share on his side in his earlier games that season** (the CEO: "only what was known before the game"). In week 1, or before his first game of a season, it uses last season's share. With neither, it uses his depth-chart rank's average share at his position that week.
12. **Exposure enters as logs:** log(1 + snaps), touches and defenders' tackles made, plus a recency-weighted sum of snaps.
13. **Time box: four build sessions,** since the CEO chose all three methods.

## Data path

14. **The exploration's scripts read the main checkout's data through `PCF_DATA_DIR`** (the worktree has no `data/`). No config changed.
