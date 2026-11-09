# 0023: Scheme tendencies are a part of the team-game table; the scheme expert's first build predicts traits

**Date:** 2026-11-09 · **Decided by:** the CEO chose the direction ("start with traits and anti-traits") and agreed the draft tests; Claude made the technical calls below, listed for veto at merge · **Project:** `schemes-v2`

**Decision:**
- **New part `team_game.tendencies`** (`pcf.data.tables.tendencies`): one row per team and game with how the team chose to play, counted from play-by-play in neutral situations. Known when play-by-play is (kickoff + 1 day).
- **The scheme expert's first variants** (`pcf.experts.schemes_v2`): each team's next-game tendency for four traits (pass rate over expected, shotgun rate, tempo, throw depth), as three simple averages and one fitted blend.

**Why a table part:** a model reading plays through the gateway would hold all of play-by-play in memory (about 2.7 GB), and every leakage check would scramble it. The tendencies are plain counts with no fitting, like box-score stats, so they belong in the tables, built a season at a time. Any other project can read them.

**The calls:**
1. **Neutral situations only:** downs 1–3, win chance 20–80%, outside the last two minutes of a half, no kneels or spikes (the exploration's definition). Outside them the score and the clock choose the plays.
2. **Raw rates, not "over expected"** for shotgun and no-huddle. The exploration took them against the league's rate by season, down and distance, which uses the whole season. The expert compares each team with the league's level known at the moment instead. Pass rate keeps nflfastR's `xpass`.
3. **Live columns only.** Personnel, coverage, blitz and box counts come from participation (after the season), so they're left for a retrospective part.
4. **The head coach is the one from the team's latest known game.** A game's own coach is in the pregame part, known at kickoff. So a new coach's history can't help before their first game with the team. Coaches are announced months ahead; a better known-at rule for them is a data-layer follow-up.
5. **The shrunk season average** gives the league's level 4 games' weight (the exploration found tendencies settle in 1–2 games, F5; the blend's fitted weights then decide how much to trust it).
6. **The blend is weighted least squares** on the league's level and four gaps from it (shrunk season, last 4 games, last season, the coach's history), with ranges from the training misses. That's rungs 0 and 1 of the ladder; rung 2 follows only if it beats the blend.
7. **`elo` leaves `depends_on`** for now: the trait variants don't read it. It returns when a matchup variant does.
8. **Runs on Saturday** (Thursday games at the Thursday run), like Elo, so Monday night's game is in.

**Alternatives:**
- *Read plays through the gateway:* simplest to write, but too heavy (above).
- *One multi-output model:* the contract is one quantity per variant, and higher layers read variants one at a time.
