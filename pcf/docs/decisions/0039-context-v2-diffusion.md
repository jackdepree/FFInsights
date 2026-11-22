# 0039: PyTorch and a conditional diffusion model, for context-v2's H85

**Date:** 2026-11-20 · **Decided by:** the CEO chose the test (2026-11-20: "Can we test the diffusion model against the chain on the same plays?"). These are Claude's technical calls, listed for veto at merge. · **Project:** `context-v2`

1. **PyTorch is added** (`uv add torch`, 2.15.0, the CPU build). A diffusion model needs a neural network and its gradients; scikit-learn's networks can't take the noise step as an input. It is a discovery dependency for now: no package code imports it.
2. **DDPM over a play's outcomes**, coded as "analog bits" (yes or no as -1 or +1) and normal scores (amounts by their training quantiles). This is the simplest tabular diffusion; TabDDPM's multinomial diffusion for categories is more exact, but every outcome here is yes-or-no or an amount.
3. **Outcomes a play doesn't have are masked out of the loss.** Filling them in (a depth on a sack) would teach the model a number that never happened.
4. **One model for "before the snap" and "given an outcome".** Each present outcome is shown as a condition with chance 0.3 in training (the fill-in-the-blanks idea, method B, inside method C). That is cheaper than training a model per question, and it is how the CEO's "given there is a pressure" is answered.
5. **Small and untuned:** 3 layers of 256, 100 steps, 40 passes, 64 draws per play, 2 seeds. A first look, scored against untuned trees, so neither side is tuned.
