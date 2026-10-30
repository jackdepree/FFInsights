# 0005: Collectors on Actions, modeling on the PC

**Date:** 2026-10-30 · **Decided by:** CEO (with Claude's recommendation)

**Decision:** The odds collectors run on GitHub Actions and push to the private `pcf-data` repo. The refresh, modeling and reports run on the CEO's PC through Windows Task Scheduler (first schedule: Tuesday morning, Wednesday afternoon and Saturday afternoon, US Eastern).

**Why:** collectors must run on time even when the PC is off, and their data can't be re-downloaded. Modeling needs the local data cache and MLflow, is too heavy for free Actions machines, and its outputs shouldn't appear in this public repo's logs.

**Alternatives:** everything on Actions (moving gigabytes of cache every run, memory limits, public logs) or everything on the PC (lines lost whenever it's off).

**Revisit if:** the PC is unreliable on game weeks, or PCF goes public and needs an always-on server.
