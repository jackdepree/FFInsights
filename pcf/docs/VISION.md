# Vision: Principal Component Football

> This is the north star. When the rules in [`CLAUDE.md`](../CLAUDE.md) don't decide a tradeoff, lean in the direction this document points.
> It's written in the CEO's voice. Notes marked **Claude's note** translate an idea into technical terms or flag an assumption.

## In two sentences

PCF is a machine learning forecasting engine that measures football and explains what is happening on the field through numbers. It aims to be the best football prediction engine in the world, and to show its work.

## The dream

Since I was a kid I've wondered: why can't you put all the data into a computer and have it tell you everything it knows?

That's what a football researcher, analyst or scout does. A person, or a group of people, watches games, studies stats, reads headlines, listens to commentators and argues about football. They pick up patterns. They make predictions, get feedback, learn from their mistakes, and get better. The brain is a statistical machine, and so is PCF. **PCF is an automated football researcher.**

It isn't as easy as putting everything into a computer, but in a way it is. You start with premises and assumptions, a level of detail in the data, and a sub-problem. You try to solve it, you get an estimate, you try to find the causal links, and you distill the structure. Sometimes there's a lot of structure. Sometimes there's none. Sometimes it's there, but hard to see or use. A computer working from the same data, in the same circumstances and toward the same goal will reach most of the same conclusions a human would. Models have biases for the same reason humans do: biases are heuristics. Our job is to find the heuristics that actually solve the problem.

The computer can also make things up. That's why we run checks, measure uncertainty, guard against leakage, and follow proper data science practice.

> **Claude's note:** Two honest limits on "the computer reaches the same place a human would":
> 1. Humans also have film and insider information, which we don't (see *Where our edge comes from*).
> 2. Most of what we find will be *associations*, not causes. When we claim something is causal (e.g. "fatigue *caused* the drop in efficiency"), the project brief has to say why that claim is justified.

## The name

**Principal Component Football.** Football produces a huge amount of messy, overlapping data. PCF compresses it into the components that matter: the context of a play, the role a player filled, the workload they carried, the value they added over what was expected. Then it builds predictions from those components. Compressing the structure comes first, and predictions come after.

## The problem: why build this

PFF, FantasyPros and others each tell you bits and pieces, cost money, and don't show their work. PCF becomes worth it when:

- **It tells me everything at once:** projections, probabilities, uncertainty, history and reasoning, all from one connected system.
- **It's just as accurate** as PFF or FantasyPros.
- **I control it.** I own the system that generates the information. The raw information is out there for anyone. What matters is how you clean it, transform it, compress it, decompress it and express it to get what you're after.

## Philosophy

1. **The data is already there. Feature engineering is the edge.** Garbage in, garbage out: good data matters most. I believe the free data that exists today can beat most professional models, because the difference comes down to feature engineering. Yards per route run is the example. Anyone could have calculated it for decades, and nobody talked about it until recently. Great features come from thoughtful, creative computation: contextualizing, associating, and looking at the data in ways others don't.
2. **Structure before predictions.** Build the expert models that compress football (context, roles, fatigue, participation, VOE) before building the products on top of them.
3. **Context over the box score.** Two players on the same team can play very different roles, in different game situations, under different pressure. A stat without its context is misleading.
4. **Uncertainty is part of the product.** A prediction without an honest measure of its uncertainty is incomplete. We want to *know* when we're unsure, and we want that uncertainty measure to be reliable itself.
5. **Football is noisy and samples are small.** There are only about 17 games per team per season, and plenty of unpredictable events. We respect that: we use simple baselines, check calibration, and stay humble about small edges.
6. **Show the work.** Every answer can be traced back to the experts and features that produced it.
7. **Simple first, complex when proven.** A sophisticated technique has to beat a cheap one to earn its place.

## Layers of an answer

Every output in PCF can be explored one layer deeper at a time:

1. **The takeaway:** the headline. "Take the under." "Start him." "His VOE is +0.12."
2. **The uncertainty:** how sure we are, as a range and a confidence grade.
3. **How we got there:** which experts and factors drove the answer, and which didn't matter.
4. **What it means:** the bigger picture. How these pieces come together, and what it says about the player, team or game.

You can stop at the takeaway, or keep going as far down the rabbit hole as you want.

## A week with PCF

### As a user (what PCF says on a Tuesday in November)
- **The main projections** for every player and game, with uncertainty and probabilities.
- **The best picks** for each kind of bet and each fantasy format.
- **The background:** player history, team history, and how things are trending.
- **Our track record:** past picks that won and lost.
- **Model scorecards:** which models make money, which lose money, which are erratic. Where we're strong and where we're not.

### As the builder (what I see when I'm developing PCF)
- **Project status:** what's done, what's in progress, and what we could work on next.
- **An impact map:** for any new project, where it plugs into the layers and which other sub-problems it could improve.
- **Exploratory assumption analysis:** when I find a new sub-problem, a quick first look at its assumptions and early results, so I can decide whether that rabbit hole is worth going down before committing to it.

> **Claude's note:** The builder view implies two things we'll design in `ROADMAP.md` and `ARCHITECTURE.md`:
> - a machine-readable registry of projects and their dependencies, which can draw the impact map automatically;
> - a lightweight "exploration" stage before the executive brief, for testing whether a sub-problem is worth pursuing.

## Who it's for

1. **Me (the power user):** everything, at every layer of depth, plus the builder view.
2. **A few friends:** the takeaways and picks, with uncertainty, as emailed HTML reports or a dashboard.
3. **Future subscribers (if results are strong):** a public website. Only once the track record earns it.

## Where our edge comes from

I want PCF to beat the sportsbooks, consensus rankings, ADP, and any one person's opinion, at every horizon: next week, next month, the next 10 games, the next Super Bowl or two, the next draft.

> **Claude's note:** To keep this ambition measurable and honest:
> - **Main game spreads and totals** are among the most efficient betting markets in the world. We use them as a *benchmark*: if our win probabilities come close to the closing line, the lower layers are healthy. They aren't the main profit target.
> - **Realistic edges** are in less efficient places: player props, touchdown scorers, early-week lines before the market settles, start/sit, DFS, best ball and dynasty values.
> - **Proving an edge takes time.** With about 272 games per season, telling skill from luck takes many bets. Our scorecards report their own uncertainty, so a hot month isn't mistaken for a real edge.
> - **We can't replicate PFF's film grades.** They come from people charting every snap. PCF's grades are *statistical*: performance over what was expected given the context (VOE). That's a different product, and arguably a more objective one.

## What sets PCF apart

- **Uncertainty first:** every number comes with a range and a confidence grade.
- **Explained picks:** every recommendation shows which experts drove it.
- **VOE as the signature stat:** PCF's headline measure of player value given context, the way PFF has its grades.

## Non-goals

PCF is deliberately **not**:

- **Live or real-time:** we work weekly, plus game-day updates (e.g. injuries).
- **A betting bot:** PCF recommends, and the human decides and places bets.
- **Other sports, or college football:** at least for now.
- **Film grading:** see *Where our edge comes from*.
- **Built on paid data:** ever.
- **"Lock of the week" picks:** every pick comes with a probability.

## Responsible use

PCF gives probabilities, not guarantees. Whether to bet, and how much, is always the user's decision.

## Success

We beat the market (positive closing line value), match or beat FantasyPros ECR on projection accuracy, and produce well-calibrated probabilities with trustworthy uncertainty. How we measure each of these lives in `VALIDATION.md` (to be written).
