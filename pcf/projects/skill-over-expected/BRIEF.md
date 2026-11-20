# Skills over expected: a VOE cousin

> **Status:** exploring, 2026-11-20. Kickoff on 2026-11-20, after retro 2 (the CEO: "let's look at the skill over expected. Let's do the kickoff for that. Let's start the brief and the exploration"). This is a **draft brief**: it is agreed after the exploration (CLAUDE.md, lifecycle step 3). The first look is in [EXPLORATION.md](EXPLORATION.md).

## The usual way

Analysts measure a player's skill on outcomes he controls more than EPA: actual minus what a model expected. Common examples are completion over expected for passers (nflfastR, Next Gen Stats), rushing yards over expected for runners (Next Gen Stats, from tracking at the handoff), and pressure and pass-rush win rates for rushers and blockers (PFF, ESPN). Each is summed per player-season, shrunk toward the average by sample size, and judged by how well it repeats from one season to the next. The public consensus is this. Pass-rush measures repeat well. Completion over expected repeats moderately. Rushing yards over expected repeats weakly, and much of it is read as the line's. Few public studies check whether a measure follows a player who changes teams, which is the test that separates his skill from his surroundings.

## Two analogies

- **Baseball's stabilization points.** Every rate needs a number of chances before it is half signal and half luck. Strikeout rate gets there in about 60 plate appearances; batting average on balls in play needs about 800. That gives a sample-size column for the CEO's per-position map (I79): a measure is "use" for a position only if a season gives it enough chances to stabilize.
- **Teachers' value-added.** A teacher's value is her students' scores minus what was expected of them. The well-known trap is sorting: good teachers get good students, just as good backs may get good lines. The fix in that field is the same as ours: follow teachers who change schools (I76), and check the measure beside the obvious input (W1).

## The CEO's hunches (word for word, before any test)

| # | Hunch | The CEO's odds | Claude's odds |
|---|---|---|---|
| H77 | "if we go after the lower noise outcome, I think that would be really great ... So pressure rate for linemen, the completion over expected. We could do pressure rate over expected, and we can do rush yards over expected. Even though that we found that rush yards are pretty hard to model." Its odds: "I think I'm like 70% confident that if we look at runners, and maybe some defensive players, maybe like defensive linemen, then the less noisy outcomes will be much better for prediction." | 70%, for runners and defensive linemen | For the claim as worded (both groups' lower-noise measures repeat clearly more than their EPA): 35%. By group: defensive linemen 75%; runners 35%. Side bets in HUNCHES.md |
| H78 | "a running back snap share, new snap share, is not actually what the backfield is. It's who is in the backfield and how good are those individuals in that backfield" (in full in HUNCHES.md) | 30% | 45% for the claim as worded; 70% that the remaining backs' shares alone beat the backfield's past split; 30% that how well they ran adds |
| H79 | Wide receivers' plain catch rate ("completions divided by targets") as the stat | 40% | 60% |
| H80 | Outside linebackers are two roles, pass rush and coverage, set by the defensive coordinator; the 97% kept is "slightly misleading"; inside linebackers' roles are steadier | 90% the roles exist; 60% we find something because of them | 35% as worded; 85% the split exists |
| H81 | Defensive backs' coverage numbers (catch rate allowed, yards, passes defensed, interceptions, throw depth against) carry over, including to a new team | 50% | 25% |
| H82 | Sacks follow the quarterback; pressures are line against line | 60% | 70% |
| H83 | Broken tackles and how many tacklers it takes, before and after the line, show a runner's skill | 60% | 55% |
| (I89) | Who owns time to throw and throw depth: QB, receivers or line? (a question; in IDEAS.md) | 50 to 60% | 70% time to throw is the QB's |

The CEO's direction for the project, from 2026-11-20, word for word (kept from the idea page):

"I think based on your analysis, if we go after the lower noise outcome, I think that would be really great. I think it's kind of building on the context expert, which is good because that's what we built that for. So pressure rate for linemen, the completion over expected. We could do pressure rate over expected, and we can do rush yards over expected. Even though that we found that rush yards are pretty hard to model. And so I think that's probably the first thing we should go after, because I think we'll learn a lot from that, and then we can, like you said, we can build off of it. So when I think about like an expert that is like picking apart value between players and between their teammates, like extracting value and saying like, oh, this person has a certain amount of value. Like a team should pay this person a certain amount. This person should like have some sort of consistency that we can predict because of this value. When I think of that, I'm thinking along the lines of this is going to be like depending on obviously all the assumptions. It could be used for anything. It could be used for player rankings, which I think are super cool to look at and super. I think people love player rankings, and I think that's like a great avenue. It could also be used for features. I think it would be very powerful as an individual player level feature. But also, I think it's really interesting to see like we can have an expert down the line, or we can just build features as we go. We can label like say like, hey, this looking at the data in this way, looking at rush yards, looking at pressure rate over expected, looking at EPA, it's so convoluted, and we can say, hey, this analysis found that this statistic and this feature and this condition do not carry over. They are not consistent. These should be ignored for future downstream models. So I think we can incorporate that and say, hey, like on a positional level, like if you're trying to extract like value or consistent real measurables for this specific position, only look at this stuff. Don't look at anything else. So we can really say like for the downstream models, we can tell them exactly what they need to look at. I think that's really powerful as a feature. And then obviously anything will be anything that we can add. I think anything that doesn't add noise, and or at least is better than noise. And if we give it to the fantasy and betting models, they will do really well. So I think I always want to keep this stuff at the player level, but anything that breaks out to the position is still great, because maybe we say like, hey, it's based on the data we have, it's just impossible to know if a running back is good or not. Or we can say the only thing that tells us whether a running back is good or not is feature X. So that's something that we need to build out as we do this. Yeah, I think can you log kind of this as like what I'm talking about as the next thing to go after? So I think what you've said already is really good. So where we could have causal methods in model experts, like you said, the movers model from labor economics, that's a great idea. The rotating players, that's a great idea. The individual absence, that's a good idea. The outcomes that are less noisy or less lucky, that's a great idea. So I think as long as we record those, because I think you identified good things, record those as ideas or future models or methods or however you think is the most effective to keep that information, write it down, and then we can start retro to right now."

The CEO's football reading of retro 2's I53 (2026-11-20) belongs here too: a back "has to thrive within opportunities, and the team around them has to create the opportunities for them"; a receiver creates his own (RETRO.md, retro 2, section 8). It predicts that a runner's yards before contact belong to the line and his yards after contact to him. The first look checks that.

## The question (draft)

For each position, which measures of a player's skill over expected are real (they repeat), are his (they follow him when he changes teams), and are better than EPA? The answer becomes the per-position map (I79) and the first player-level features, and it feeds `line-play` and `qb-talent` ("we can keep it more general than the line play and the QB talent, so this can feed into the line play and the QB talent").

## The terms

- **Over expected:** actual minus what a model of the situation expected, per play, summed per player-season. Pressure measures have no expectation yet in the first look (below).
- **Repeat:** the season-to-season correlation of a player's per-play rate, among players with enough chances in both seasons.
- **Reliability:** the same rate's odd-week against even-week correlation within a season, stepped up to a full season (Spearman-Brown). It is the noise ceiling: a measure can't repeat across seasons much more than it agrees with itself within one.
- **Share kept:** movers' repeat divided by stayers' (retro 2's I53). Near 1 means the measure is the player's; near 0, his surroundings'.

## Known before the kickoff

- **context-live's expectations** (`pressure_prob`, `completion_prob`, `rush_yards_exp` and 14 more) cover **2023 and 2024 only** (pressure 2024 only), from the walk-forward history (2025 is in the vault run). That's one season pair, and none for pressure. So the first look uses free public expectations for 2016-2024 (nflfastR's completion probability, Next Gen Stats' expected rushing yards) and context-live's for the 2023-2024 cross-check.
- **Who was on the field** (participation) is post-season, so the first version is retrospective, like voe.
- **Rushing yards were hard to forecast** from the situation (H64). That's a statement about the situation, not about runners.
- **It stays general and feeds** `line-play` and `qb-talent`.
- **Ideas that fit** (the backlog read, W4): I79 (the map; this look starts it), I81 (linemen's absences on pressure), I82 (what the coaches see), I84 and H78 (movers' shares), I76 to I78 (the causal methods, later), I71 (a defense's calls).

## The first look's technical calls (Claude's, for the CEO to veto)

1. **Seasons 2016-2024** for discovery (rushing yards over expected and PFR pressures from 2018). The 2025 vault is untouched.
2. **Measures, per player-season, with a volume floor in both seasons:**
   - QBs: completion over expected per pass (nflfastR's `cpoe`), 150+ passes. Beside it, EPA per dropback.
   - Receivers (WR, TE, RB): catches over expected per target (caught minus nflfastR's `cp`), 40+ targets. Beside it, EPA per target.
   - Runners (RB): rushing yards over expected per carry (Next Gen Stats), 80+ tracked carries. Also PFR's yards before contact and yards after contact per carry (2018+). Beside them, EPA per carry.
   - Pass rushers (DE, DT, NT, OLB, and inside linebackers apart): PFR pressures per dropback he was on the field for (on-field map), 150+ such dropbacks. Beside it, sacks per dropback (the noisier outcome).
   - Offensive linemen (T, G, C): the team's pressure on dropbacks he was on the field for, over a situation expectation (season x down x distance band x rushers) and over the defense's own pressure habit; 300+ dropbacks. Shared by the five (L2), so a lineman's number is his line's while he plays.
3. **Next Gen Stats' expected rushing yards come from tracking at the handoff**, so they already include part of the blocking. Their yards over expected are partly "after the handoff". This favours runners, and the first look says so beside the result.
4. **Movers:** a player whose main team (most games) changed between the seasons. Share kept = movers' repeat / stayers'.
5. **The obvious-input check (W1):** for runners, his rushing yards over expected minus his teammates' in the same season (the line's part removed); for pass rushers, beside his snap share.
6. **Intervals:** 90%, from resampling players (pairs), 2,000 draws; the difference against EPA uses the same players in both.

## Pass rules, written before the run

- **H77, the CEO's claim (runners and defensive linemen):** held for a group if its lower-noise measure repeats at least 0.15 more than the same players' EPA measure (for defensive linemen, sacks, since a lineman has no EPA of his own), with the 90% interval of the difference above zero. Both groups: held. One: held in part.
- **Claude's side bets (HUNCHES.md, H77's row):** pass rushers' pressure repeats 0.3+ (80%); QBs' completion over expected 0.3+ (70%); runners' rushing yards over expected 0.3+ (30%); movers keep half: pass rushers and QBs 60%, runners 30%, linemen 25%.
- **The CEO's reading of I53 (not a hunch with odds; Claude's expectation):** yards after contact repeat and travel more than yards before contact, 65%.
- **H78** is tested in the next look (CLAUDE.md: a hunch's test isn't run in the reply that records it). Its design: running backs who change teams, their new carry share from the remaining backs' old shares and rushing yards over expected, the departed backs' shares, and the incoming back's own share and over-expected yards; against the new backfield's past split (its top back's share) alone; held out by season.

**The CEO's choices for the next looks (2026-11-20):** the forecast test comes next: "the next test should be the next season or maybe even the next game for runners and sacks and pressures and completion percentage". For H78, a back's "goodness" is yards after contact: "the hunch says that they cannot create yards before contact because that's dependent upon your whole team. And also, it's dependent upon the defenses you play ... if you have an explosive play and no one touched you, was that really the running back's vision and their skill, or was it more about the defense being poorly set up to make the stop and your offense blocking everyone". Everyone is in scope: "I don't want to leave out anyone. I want to try and incorporate everyone." There's no free tracking for defenders; PFR's coverage charting (2018 on) is the stand-in.
