# composites/ (layer 2)

Models that combine expert outputs (team strength, player opportunity, game simulation).

- Same contract as experts (`docs/ARCHITECTURE.md`).
- Train on experts' **walk-forward history**, never on today's champion run over past rows (rule e, the vintage rule).
- Must beat their simple baselines (`docs/VALIDATION.md` section 6).
