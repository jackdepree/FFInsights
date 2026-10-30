# 0003: The as_of gateway and stacked leakage checks

**Date:** 2026-10-30 · **Decided by:** CEO (with Claude's recommendation)

**Decision:** Models read data only through `gateway.as_of(moment, cadence, inputs)`. Eleven automated checks are stacked on top (ARCHITECTURE.md, "Leakage defense in depth"), and nine of them block a model from being registered.

**Why:** leaked backtests look great and then fail live. Leakage hides in joins, rolling windows, feature selection and stacked models, so it's enforced in one place and tested many ways, rather than left to each expert's care (rule c).

**Alternatives:** each expert filters dates itself, plus code review. That works until one expert forgets.

**Revisit if:** the gateway becomes a bottleneck. Then optimize it, but don't route around it.
