# 0011: Features are defined per moment; bulk is a checked speed-up

**Date:** 2026-11-02 · **Decided by:** Claude (technical call, in the `validation-harness` brief)

**Decision:** A model's features are defined by `features(view, games)`: the rows predicted at one moment, built from a view at that moment. The backtest calls it at every prediction moment from the first training season on. A model may add `features_history(view, games)`, which computes every row at once from a view of everything. The harness uses it only if it matches the per-moment features, and its own result with the future deleted or scrambled, at every leakage cutoff.

**Why:** a feature computed per moment can't leak through timing: the view doesn't hold the future. A bulk "so far" feature looks honest and can still leak. In the exploration, "points in earlier games" used Monday night's stats at a Tuesday moment (validation-harness#F2). Views are cheap: about 0.2 seconds each from memory, so a 19-season feature history takes about 75 seconds (#F5, #F14).

**Alternatives:**
- Bulk only, with the checks at 25 cutoffs. It's faster, but a leak between cutoffs could slip through.
- Bulk features trusted by reading the code (rejected): F2 is the counter-example.

**Revisit if:** a model's per-moment features take hours (play-level features over 19 seasons). Then bulk becomes the default for that model, and the cutoff checks carry the full weight.
