# baselines/

The yardsticks every product must beat (`baselines` project, rule k, VALIDATION.md §6). Each is a variant of the one project id: `pcf backtest baselines --variant <name>`.

| Module | Variants | Run |
|---|---|---|
| `averages.py` | `rolling4`, `season`, `last_season`: fantasy points averages, ranges per position | Tuesday |
| `lasso.py` | `lasso`: box-score history only (no ECR, no lines), penalty chosen inside each training window | Tuesday |
| `ecr.py` | `ecr`: FantasyPros' rank → points (isotonic curve per position), a benchmark | Saturday |
| `market.py` | `market_margin`, `market_total`, `market_win`: the closing line, benchmarks | Kickoff |
| `common.py` | Scoring formats, known games, ranges from residuals by group | |

- **A product names its baselines** in `baselines()`; the harness reruns them at the product's run. Benchmarks keep theirs (decision 0012).
- **Another scoring:** `scored(RollingAverage, "half")` (PPR, half, standard). ECR is PPR only.
- **ECR is judged on Sunday and Monday games, weeks 2–17, from 2022** (D4). The `player_game.ecr` part already drops the games before each snapshot.
- **Benchmarks are never features before they're known.** The closing line is known at kickoff only.
