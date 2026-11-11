# 0027: Elo and schemes-v2 join the ledger; the collectors run from the PC while GitHub is locked

**Date:** 2026-11-10 · **Decided by:** the CEO chose 1A, 2A and 3A in the `live-experts` brief (the nine final forecasts with free yardsticks; a replay of 2026 weeks 1–9; the collectors from this PC until GitHub Actions is unlocked, with the CEO's approval of the scheduled tasks). The calls below are Claude's technical calls, listed for veto at merge. · **Project:** `live-experts`

**Decision:**
- **The ledger's models** (`pcf.validation.live.MODELS`), in run order:
  - participation's five, as before;
  - Elo's `margin`, `total`, `win`, `wins_next3`, `wins_rest`;
  - schemes-v2's `pass_oe_rung2`, `shotgun_rung2`, `depth_rung2`, `tempo_shrunk`, then each trait's season-to-date average (`<trait>_season`) as its yardstick.
- **Elo against the close:** `ledger_score.close_card`, printed and saved by `pcf ledger score`.
- **The collectors on the PC:** `ops/collect-run.ps1` (`-What odds` or `nflverse`), set up by `ops/register-collector-tasks.ps1` as two tasks, "PCF odds (PC)" and "PCF nflverse (PC)".

**The calls:**
1. **Participation runs first,** so adding models can never cost its forecasts their kickoff. A test keeps it first.
2. **Live rows keep what an expert publishes** (Elo's ratings, decision 0021), as its backtest history does. A model whose published columns are missing is refused, so they can't go quietly empty.
3. **Each new model's scorecard yardstick is pinned:** Elo's final runs of 2026-11-07, schemes' 2016–2024 runs of its finals, and new 2016–2024 backtests of the four season-to-date averages (20 shuffled refits each: they're yardsticks, not candidates).
4. **Elo is set against nflverse's closing line,** in the measure of Elo's own results (elo#F2): the average miss in points for margins and totals, log loss for win chances. The close is known only at kickoff, so it's scored after the game rather than written as a forecast. The ledger's `market_*` columns stay empty until a product brings its line at its own moment.
5. **A refresh that fails is tried once more a minute later,** in the ledger's pull and the PC's nflverse snapshot. On 2026-11-10 nflverse replaced its schedule file while it was being downloaded, so the file didn't match the fingerprint listed a moment before; the retry 15 seconds later worked. A second failure is real and stops the run, as before.
6. **The PC collectors copy the Actions jobs exactly:** the same scripts, the same days (Tuesday and Saturday odds move 30 minutes, so they don't start with the ledger run), their own full clone of `pcf-data` (the ledger's clone is sparse), and The Odds API key read from `pcf/.env` and never logged. They commit as `pcf-collector-pc`.
7. **They stand down by themselves:** if GitHub's own collector (`pcf-collector`) has pushed in the last 2 days, a run collects nothing, so The Odds API's credits aren't spent twice, and shows a notice to remove the tasks.

**Alternatives:**
- **Collectors in the ledger task.** One task fewer, but the ledger runs three days a week and the collectors on five, plus a daily snapshot; and a collector failure would read as a ledger failure.
- **Retrying inside the download** (`nflverse._fetch_one`). The file has changed upstream, so a second download against the same listing fails again; the whole refresh has to list again.
- **Market rows in the ledger for Elo's yardstick.** They'd be written after kickoff, which the ledger refuses by design.
