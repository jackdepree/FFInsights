# 0012: Benchmarks run at kickoff; baselines at the model's run

**Date:** 2026-11-02 · **Decided by:** Claude (technical calls D3, D5 and D8 in the `baselines` brief, approved by the CEO)

**Decision:**
- **Benchmarks** are yardsticks from outside PCF: FantasyPros' ECR and the betting market's closing line. A model marks itself `benchmark = True`. It needs no signal test (there's no signal of ours to test), and only a benchmark may declare the `kickoff` prediction moment.
- **The closing line runs at kickoff**, when it's known. The gateway shows an output only to views at or after its `as_of`, so a kickoff-time prediction can never become a feature of a model that runs earlier.
- **ECR is a table part** (`player_game.ecr`), holding only the games that kick off after the snapshot is known. The gateway, not each model, keeps the Thursday game out of the Friday ranking (baselines#F2).
- **A baseline is judged at the model's own run.** When a scorecard compares a model with a baseline, the harness reruns the baseline at the model's run, so a Saturday product is compared with Saturday averages, not Tuesday ones that can't see Monday night. Benchmarks keep their own moment.
- **Baselines are variants of one project** (`baselines/rolling4`, `baselines/ecr`, …), in `pcf.baselines`. Their outputs are in `outputs/baselines/<variant>/<run_id>/`.

**Why:** a closing line or a ranking is a fair bar only at the moment it existed. Scoring the close at a Saturday run would be a leak; scoring a product at Saturday against a Tuesday average would flatter the product.

**Alternatives:**
- Score products against the raw lines in the scorecard code, outside the harness. It's simpler, but the market would get no history, no calibration check and no ranges.
- One registry entry per baseline. It's cleaner on paper, but it means five projects' paperwork for 50-line models.

**Revisit if:** our own collected odds become a table. Then a market benchmark at the Saturday run (the line we could actually bet) joins the closing one.
