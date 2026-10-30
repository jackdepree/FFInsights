# 0001: Python only

**Date:** 2026-10-30 · **Decided by:** CEO (with Claude's recommendation)

**Decision:** All code in `pcf/` is Python.

**Why:** nflreadpy, Polars, DuckDB, scikit-learn, XGBoost, PyMC and MLflow all live in Python. One language means one environment, one test suite, and functions any project can reuse (rule j).

**Alternatives:** Python plus R, as in `old/`. R has strong modeling packages, but two languages doubles the tooling and splits shared code.

**Revisit if:** a method we need exists only in R. Then call it from Python for that one project, rather than splitting the codebase.
