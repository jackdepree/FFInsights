# 0006: A rolling vault season and proper scores

**Date:** 2026-10-30 · **Decided by:** CEO (with Claude's recommendation)

**Decision:** The most recent finished season (2025 now) is a vault: each project opens it once, at the end, and reports the result as-is. It rolls forward every February. Props use the 2026 live season as their vault, because their history is thin. Models are judged on proper scores (pinball loss, log loss, closing line value), and "beats" means the 90% week-block bootstrap interval of the improvement is above zero, with ties going to the simpler model. Full standards: VALIDATION.md.

**Why:** every look at the test seasons followed by a tweak makes them less honest. With dozens of experts tried on the same seasons, something will look great by luck. Proper scores reward honest uncertainty, which is part of PCF's product.

**Alternatives:** no vault, with the live ledger as the only honest test (we'd learn about overfitting only when it fails live); hit rate and ROI as headline scores (mostly noise at our sample sizes).

**Revisit if:** the vault leaves too little data for a specific project. That project's brief may then propose a different split, with the CEO's agreement.
