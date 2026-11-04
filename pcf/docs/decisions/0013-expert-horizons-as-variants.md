# 0013: One expert's horizons are variants, each with its own champion

**Date:** 2026-11-03 · **Decided by:** Claude (technical calls D3, D4 and D9 in the `participation` brief, approved by the CEO)

**Decision:**
- **Each horizon is a variant of one project** (`participation/trees`, `participation/lasso_h3`, `participation/lasso_rest`), each a direct model with its own history and scorecard. The chance of being active is a variant too (`participation/active`).
- **The ladder runs per horizon, so champions differ:** trees for the next game, the lasso for the next 3 games and the rest of the season. A tie goes to the simpler model.
- **The next game's two parts are "takes an offensive snap" and "share if they do".** Its spike is "no offensive snap", not "inactive", because that's what the outcome says.
- **Registering champions waits for the weekly run.** `registry.yaml` holds one `champion` number per project, and `tracking.log_model` takes one scikit-learn estimator. This expert has four champions, each a set of per-position parts. Nothing loads a registered model yet, and higher layers read saved histories (rule e). Pending the CEO's call at merge: `participation` RESULTS, case against 6.

**Why:** the horizons have different models because they have different answers: trees win by 0.053 at one game and lose by 0.151 over the rest of the season (participation#F10, F17). Rolling one model forward understates how injuries pile up (D9). Variants reuse the harness as it stands.

**Alternatives:**
- *One model with the horizon as an input.* Shares its strength across horizons, but its errors are correlated and the ladder couldn't choose per horizon.
- *A separate project per horizon.* Clean, but the inputs and code are the same, and the registry would fill with near-copies.
- *Extending registration now.* A bundle class and a per-variant `champion` are perhaps half a day, for something nothing reads yet. The weekly run will say what shape it needs.
