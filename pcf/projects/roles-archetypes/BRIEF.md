# Roles and archetypes: what each player is asked to do

> **Status:** kickoff, 2026-11-24 (the CEO: "i would like to start roles and archetypes, please"). Waiting for the CEO's hunches. Nothing has been tested for this project yet.

## Why now

- **Much of what repeats and travels is role** (retro 3, P11). Target share and target depth belong to the receiver (F1). A running back's carry share belongs mostly to his backfield (F2). An outside linebacker's rusher-or-dropper role is his own, and an inside linebacker's is the scheme's (F18). Next season's sacks come from the role, not from pressures within it (F49).
- **Other projects are waiting for a role table:**
  - I113 (skill-over-expected's 14 measures read within role);
  - I79 (the per-position map of what to use and ignore);
  - `vacated-opportunity` (who's like the missing player);
  - availability (deep-target receivers get hurt more, H95).
- **Movers:** a mover's new slot adds more to his first 4 games than his own old share does (F57). A role says what slot he's walking into.

## The usual way

Charting services (PFF, FTN, Sports Info Solutions) label every snap by hand: where each player lined up (wide, slot, inline, backfield, box, edge) and what he did (route, block, rush, coverage). Analysts then sum each player-season into a usage vector (alignment shares, route mix, target depth, carries by down) and cluster it, usually k-means or a Gaussian mixture. That gives archetypes such as the slot receiver, the X receiver, the satellite back, the move tight end, the box safety and the slot corner. The labels are used for comparables ("players like him"), for matchups, and as inputs in projection models, often with a similarity score to find a player's nearest past seasons.

## Two analogies

- **Ecology: niches and guilds.** Ecologists define a species by what it does (what it eats, where, when), not by what it looks like. Species that do the same job form a guild. When one is removed, the closest member of its guild takes over its niche. A role is a player's niche, and an archetype a guild. The analogy suggests two things to look at:
  - Roles are continuous, and guilds are a convenient cut. How many archetypes are real, and do the cuts repeat?
  - The empty-niche question is `vacated-opportunity`'s: who fills it is whoever's most alike.
- **Basketball's positionless era.** NBA analysts found the five listed positions hid a dozen or so playing styles. Topological data analysis on box-score profiles found 13, and lineup analysis now uses style, not position. In football the listed position is "WR", but a slot receiver and an X receiver are asked to do different jobs. The analogy suggests asking whether style beats listed position as the bin every other measure is read within.

## What we already have

- **Findings:**
  - Target share and depth travel with the player (F1). Carry share is mostly the backfield's (F2).
  - Outside linebackers split into rushers and droppers (F18, 82% of seasons outside the middle third). Inside linebackers' role is the scheme's.
  - Schemes-v2 split what moves with a play caller (scheme) from what moves with a player (role), and found throw depth is a QB and roster trait (R3).
  - The passing-down role is paid in contracts (I43, snap-leverage F10).
- **Free data:**
  - **In season:**
    - play-by-play: targets, air yards, pass location, run gap and direction, carries by down and distance;
    - weekly snap counts (offense, defense, special teams);
    - depth-chart labels on every play (the cleaning port's `slot_labels`, from 2016);
    - Next Gen Stats weekly: target depth, separation, cushion, share of team air yards, rushing against 8+ in the box;
    - PFR advanced stats;
    - FTN charting from 2022 (motion, play action, blitzers; about 1–2 weeks behind).
  - **After the season only** (retrospective; never a live input): participation from 2016. It says who was on the field, the offense and defense personnel, the targeted receiver's route (one route a play), coverage and pressure.
- **Not free:** per-snap alignment for every player (slot, wide, inline) and every receiver's route. The free route is only the targeted receiver's.

## The backlog that fits

- **I113,** a role table for every player-season (slot, wide or inline share and depth for receivers; a back's share of his backfield). It's open, for skill-over-expected's build (group E). It's this project's first deliverable, or a shared one.
- **I57,** forecasting a receiver's route mix from his past routes. It repeats as a role; the routes arrive only after the season.
- **I79,** the per-position map of what to use and what to ignore.
- **I23,** receiver depth fit: deep threats moving to short-passing offenses.
- **I9 and I49,** movers over-projected for snaps, and swap pairs inheriting an absent player's snaps (role-alike substitutes).
- **I91,** how much of the outside linebackers' sack forecast is only knowing who rushes.
- **Answered and reusable:** I53 and I84, which usage rates travel with a mover.

## The CEO's direction and hunches (word for word, before any test)

*Waiting for the CEO.*
