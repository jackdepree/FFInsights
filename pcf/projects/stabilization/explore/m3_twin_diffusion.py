"""Stabilization, method 3 (EXPLORATION.md, exploratory): denoising all of a player's rates at once.
The twin (a multivariate empirical-Bayes pull) against a conditional diffusion model (context-v2's
second-look denoiser, adapted), and both against univariate M1. Receivers (2016+) and coverage
players (2018+). Fit on target seasons before 2022, tested on 2022-2024 (one split: the diffusion
model is too slow to refit every season). Discovery only; the 2025 vault is closed.

Run from pcf/:  python projects/stabilization/explore/m3_twin_diffusion.py   (writes m3_twin_diffusion.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import torch

sys.path.insert(0, str(Path(__file__).parent))
from m2_hunches import player_cond  # noqa: E402
from stab_common import Say, boot_gain, fit_m1, load, player_seasons  # noqa: E402

c = pl.col
RNG = np.random.default_rng(1)
TEST = 2022
Z80 = 1.2816
STEPS, DDIM_STEPS, PASSES, BATCH, DRAWS = 100, 50, 400, 256, 200
torch.set_num_threads(8)
say = Say(Path(__file__).with_suffix(".txt"))
GROUPS = {
    "receivers": dict(dims=["tprr", "yprr", "adot", "catch_oe", "yac_oe"], pos=["WR", "TE", "RB"], cond=["hs", "oc", "pr"], first=2016),
    "coverage": dict(dims=["tgt_per_cov", "catch_allowed", "adot_allowed", "missed_tackle"], pos=["CB", "S", "LB"], cond=["ocat"], first=2018),
}


def frame(s, game, cond, G):
    """One row per player-season S with every dim's x and n (centred by S's position mean), next season's y and w,
    and the teammates' conditions in S."""
    dims = G["dims"]
    psm = (s.filter((c("den") >= 10) & c("measure").is_in(dims)).group_by("measure", "pos", "season")
           .agg(mu=c("num").sum() / c("den").sum(), m=pl.len()).filter(c("m") >= 20).drop("m"))  # fmt: skip
    base = s.filter(c("measure") == dims[0]).filter(c("pos").is_in(G["pos"]) & (c("den") >= 50) & (c("season") >= G["first"])).select("gsis_id", "season", "pos")
    for m in dims:
        a = s.filter(c("measure") == m).select("gsis_id", "season", **{f"x_{m}": c("num") / c("den"), f"n_{m}": "den"})
        base = base.join(a, on=["gsis_id", "season"], how="left")
        base = base.join(psm.filter(c("measure") == m).select("pos", "season", **{f"mu_{m}": "mu"}), on=["pos", "season"], how="left")
        nx = s.filter(c("measure") == m).select("gsis_id", season=c("season") - 1, **{f"y_{m}": c("num") / c("den"), f"w_{m}": "den"})
        base = base.join(nx, on=["gsis_id", "season"], how="left")
    base = base.drop_nulls([f"mu_{m}" for m in dims])
    base = base.with_columns(*[(c(f"x_{m}") - c(f"mu_{m}")).fill_null(0).alias(f"d_{m}") for m in dims],
                             *[c(f"n_{m}").fill_null(0) for m in dims],
                             *[(c(f"y_{m}") - c(f"mu_{m}")).alias(f"t_{m}") for m in dims],
                             *[c(f"w_{m}").fill_null(0) for m in dims])  # fmt: skip
    pcs = None
    for m in dims[:1]:
        pcs = player_cond(game, cond, m, G["cond"])
    base = base.join(pcs, on=["gsis_id", "season"], how="left").with_columns([c(k).fill_null(0) for k in G["cond"]])
    # rows with a next season (some dims may be missing next season: masked)
    return base.filter(c(f"w_{dims[0]}") > 0)


def noise_corr(game, s, G):
    """The noise correlation between dims, from odd-against-even game halves (the true rate cancels)."""
    dims = G["dims"]
    g = game.filter(c("measure").is_in(dims) & (c("season") < TEST))
    g = g.sort("week").with_columns(h=c("week").rank("dense").over("gsis_id", "season") % 2)
    a = g.group_by("gsis_id", "season", "h", "measure").agg(num=c("num").sum(), den=c("den").sum())
    a = a.with_columns(x=c("num") / c("den")).pivot(on="measure", index=["gsis_id", "season", "h"], values=["x", "den"])
    o, e = a.filter(c("h") == 1), a.filter(c("h") == 0)
    j = o.join(e, on=["gsis_id", "season"], suffix="_e")
    R = np.eye(len(dims))
    for i, mi in enumerate(dims):
        for k, mk in enumerate(dims):
            if k <= i:
                continue
            ok = j.filter((c(f"den_{mi}") >= 5) & (c(f"den_{mi}_e") >= 5) & (c(f"den_{mk}") >= 5) & (c(f"den_{mk}_e") >= 5))
            di = (ok[f"x_{mi}"] - ok[f"x_{mi}_e"]).to_numpy()
            dk = (ok[f"x_{mk}"] - ok[f"x_{mk}_e"]).to_numpy()
            R[i, k] = R[k, i] = np.corrcoef(di, dk)[0, 1] if len(di) > 50 else 0.0
    return R


def noise_cov(F, dims, sig, R):
    n = np.column_stack([F[f"n_{m}"].to_numpy() for m in dims]).astype(float)
    inv = np.where(n > 0, 1 / np.sqrt(np.maximum(n, 1e-9)), 1e3)
    S = R[None] * (sig[None, :, None] * sig[None, None, :]) * (inv[:, :, None] * inv[:, None, :])
    return S


def twin(F_tr, F_te, dims, sig, tau2, R):
    """Multivariate empirical-Bayes pull: theta = T (T + E_p)^-1 x. T from moments (diagonal set to M1's spread)."""
    X = np.column_stack([F_tr[f"d_{m}"].to_numpy() for m in dims])
    full = np.all(np.column_stack([F_tr[f"n_{m}"].to_numpy() >= 10 for m in dims]), 1)
    E = noise_cov(F_tr, dims, sig, R)
    T = np.cov(X[full].T) - E[full].mean(0)
    sd = np.sqrt(tau2)
    Cc = T / np.sqrt(np.outer(np.diag(T).clip(1e-12), np.diag(T).clip(1e-12)))
    T = np.clip(Cc, -0.95, 0.95) * np.outer(sd, sd)
    np.fill_diagonal(T, tau2)
    w, V = np.linalg.eigh(T)
    T = (V * np.maximum(w, 1e-6 * w.max())) @ V.T
    Xt = np.column_stack([F_te[f"d_{m}"].to_numpy() for m in dims])
    Et = noise_cov(F_te, dims, sig, R)
    A = T[None] @ np.linalg.inv(T[None] + Et)
    mean = np.einsum("pij,pj->pi", A, Xt)
    post = T[None] - A @ T[None]
    return mean, np.einsum("pii->pi", post), Cc


# ---------------------------------------------------------------- the diffusion model (context-v2's second look, adapted)


def schedule(T: int) -> torch.Tensor:
    s = 0.008
    t = torch.linspace(0, T, T + 1) / T
    f = torch.cos((t + s) / (1 + s) * math.pi / 2) ** 2
    return (f / f[0]).clamp(1e-5, 1)


class Net(torch.nn.Module):
    def __init__(self, n_out: int, n_cond: int, width: int = 256):
        super().__init__()
        self.n_out = n_out
        self.body = torch.nn.Sequential(torch.nn.Linear(n_out + 32 + n_cond, width), torch.nn.SiLU(), torch.nn.Linear(width, width), torch.nn.SiLU(),
                                        torch.nn.Linear(width, width), torch.nn.SiLU(), torch.nn.Linear(width, n_out))  # fmt: skip

    def forward(self, x, t, cond):
        k = torch.arange(16, dtype=torch.float32)
        ang = t[:, None].float() / STEPS * torch.exp(-math.log(1000) * k / 16)[None] * 1000
        return self.body(torch.cat([x, torch.sin(ang), torch.cos(ang), cond], 1))


def train(y, mask, cond, seed):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    ab = schedule(STEPS)
    net = Net(y.shape[1], cond.shape[1])
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=PASSES * math.ceil(len(y) / BATCH))
    Y, M, C = (torch.tensor(a, dtype=torch.float32) for a in (y, mask, cond))
    for _ in range(PASSES):
        order = rng.permutation(len(y))
        for i in range(0, len(order), BATCH):
            idx = torch.tensor(order[i : i + BATCH])
            x, m, cnd = Y[idx], M[idx], C[idx]
            t = torch.randint(1, STEPS + 1, (len(idx),))
            a = ab[t][:, None]
            eps = torch.randn_like(x)
            xt = a.sqrt() * x + (1 - a).sqrt() * eps
            loss = (((net(xt, t, cnd) - eps) ** 2) * m).sum() / m.sum().clamp(min=1)
            opt.zero_grad()
            loss.backward()
            opt.step()
            sch.step()
    return net


@torch.no_grad()
def draw(net, cond, seed):
    torch.manual_seed(seed)
    ab = schedule(STEPS)
    ts = torch.linspace(STEPS, 1, DDIM_STEPS).round().long()
    out = []
    for i in range(0, len(cond), 512):
        cnd = torch.tensor(cond[i : i + 512], dtype=torch.float32).repeat_interleave(DRAWS, 0)
        x = torch.randn(len(cnd), net.n_out)
        for k, t in enumerate(ts):
            a = ab[t]
            a_prev = ab[ts[k + 1]] if k + 1 < len(ts) else torch.tensor(1.0)
            eps = net(x, t.repeat(len(x)), cnd)
            x0 = ((x - (1 - a).sqrt() * eps) / a.sqrt()).clamp(-8, 8)
            x = a_prev.sqrt() * x0 + (1 - a_prev).sqrt() * eps
        out.append(x.reshape(-1, DRAWS, net.n_out).numpy())
    return np.concatenate(out)


def cond_matrix(F, dims, G, sd, cstats=None):
    X = np.column_stack([F[f"d_{m}"].to_numpy() / sd[i] for i, m in enumerate(dims)])
    N = np.column_stack([np.log1p(F[f"n_{m}"].to_numpy()) for m in dims])
    P = np.column_stack([(F["pos"] == p).to_numpy().astype(float) for p in G["pos"]])
    K = np.column_stack([F[k].to_numpy() for k in G["cond"]])
    Z = np.column_stack([X, N, K])
    if cstats is None:
        cstats = (Z.mean(0), Z.std(0) + 1e-9)
    return np.column_stack([(Z - cstats[0]) / cstats[1], P]), cstats


def main() -> None:
    s, game = player_seasons()
    cond = load("cond")
    say("# Method 3: denoising all of a player's rates at once (2026-11-25)", "",
        f"Fit on target seasons before {TEST}, tested on {TEST}-2024. Rows: a player's season with 50+ routes (receivers) or coverage pass snaps (coverage), and a next season.",
        "Everything centred by last season's position mean. **M1:** each rate pulled alone. **The twin:** all rates pulled together through the true rates' covariance",
        "(the observed covariance less the noise; the noise's correlation between rates from odd-against-even game halves), its diagonal set to M1's spread, so with no",
        "correlation it is M1 exactly. Ranges: the posterior spread plus next season's noise, normal. **The diffusion model:** learns next season's whole rate vector",
        "given this season's vector, its attempts, position and the teammates' conditions (not next season's attempts: their ratios give some rates away, e.g. targets over routes),",
        "200 draws a row, mean as the forecast, the 10th and 90th",
        f"percentiles as the 80% range. {PASSES} passes, 2 seeds (forecasts averaged; the seed-to-seed gap is the fitting noise).", "")
    for gname, G in GROUPS.items():
        dims = G["dims"]
        F = frame(s, game, cond, G)
        tr, te = F.filter(c("season") + 1 < TEST), F.filter(c("season") + 1 >= TEST)
        fits = [fit_m1(s, game, m, TEST) for m in dims]
        sig2 = np.array([f[1] for f in fits])
        tau2 = np.array([f[2] for f in fits])
        k = sig2 / tau2
        R = noise_corr(game, s, G)
        mean_t, post_t, Cc = twin(tr, te, dims, np.sqrt(sig2), tau2, R)
        say(f"## {gname} ({tr.height} training rows, {te.height} test rows)", "",
            "Noise correlation between rates (halves) and the true rates' correlation (moments, clipped at 0.95):", "",
            "| | " + " | ".join(dims) + " |", "|---" * (len(dims) + 1) + "|")
        for i, m in enumerate(dims):
            say(f"| {m} | " + " | ".join(f"{R[i, j]:+.2f} / {Cc[i, j]:+.2f}" for j in range(len(dims))) + " |")
        # diffusion
        sd = np.sqrt(tau2)
        Ytr = np.column_stack([tr[f"t_{m}"].fill_null(0).to_numpy() / sd[i] for i, m in enumerate(dims)])
        Mtr = np.column_stack([(tr[f"w_{m}"].to_numpy() > 0).astype(float) for m in dims])
        Ctr, cst = cond_matrix(tr, dims, G, sd)
        Cte, _ = cond_matrix(te, dims, G, sd, cst)
        t0 = time.perf_counter()
        draws = []
        for seed in (1, 2):
            net = train(Ytr, Mtr, Ctr, seed)
            draws.append(draw(net, Cte, seed) * sd[None, None, :])
        say("", f"(diffusion: 2 seeds trained and drawn in {time.perf_counter() - t0:.0f}s)", "",
            "| Rate | k | Test rows | Twin against M1 | 90% interval | Clear | Diffusion against the twin | 90% interval | Clear | Seed 1 against seed 2 | Diffusion against M1 | 80% coverage: twin, diffusion | Ridge, same inputs, against the twin | Diffusion against that ridge (90%) |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        Dm = np.mean([d.mean(1) for d in draws], 0)
        # the cheap version on the same inputs (rule k): a ridge per rate on exactly what the diffusion model sees
        from sklearn.linear_model import RidgeCV
        Rg = np.zeros((te.height, len(dims)))
        for i, m in enumerate(dims):
            okr = tr[f"w_{m}"].to_numpy() > 0
            rr = RidgeCV(alphas=np.logspace(-2, 4, 13)).fit(Ctr[okr], tr[f"t_{m}"].to_numpy()[okr], sample_weight=tr[f"w_{m}"].to_numpy()[okr].astype(float))
            Rg[:, i] = rr.predict(Cte)
        Dall = np.concatenate(draws, 1)
        for i, m in enumerate(dims):
            n, x = te[f"n_{m}"].to_numpy(), te[f"d_{m}"].to_numpy()
            ok = te[f"w_{m}"].to_numpy() > 0
            sub = pl.DataFrame({"gsis_id": te["gsis_id"], "y": te[f"t_{m}"].fill_null(0), "w": te[f"w_{m}"].cast(pl.Float64),
                                "m1": n / (n + k[i]) * x, "twin": mean_t[:, i], "diff": Dm[:, i],
                                "d1": draws[0].mean(1)[:, i], "d2": draws[1].mean(1)[:, i], "ridge": Rg[:, i]}).filter(pl.Series(ok))  # fmt: skip
            g1 = boot_gain(sub, "twin", "m1", RNG)
            g2 = boot_gain(sub, "diff", "twin", RNG)
            g3 = boot_gain(sub, "d1", "d2", RNG)
            g4 = boot_gain(sub, "diff", "m1", RNG)
            g5 = boot_gain(sub, "diff", "ridge", RNG)
            g6 = boot_gain(sub, "ridge", "twin", RNG)
            y = sub["y"].to_numpy()
            wv = te[f"w_{m}"].to_numpy()[ok]
            tv = post_t[ok, i] + sig2[i] / wv
            ct = float(np.mean(np.abs(y - sub["twin"].to_numpy()) <= Z80 * np.sqrt(tv)))
            lo, hi = np.quantile(Dall[ok, :, i], 0.1, axis=1), np.quantile(Dall[ok, :, i], 0.9, axis=1)
            cd = float(np.mean((y >= lo) & (y <= hi)))
            say(f"| {m} | {k[i]:.0f} | {sub.height} | {g1[0]:+.2%} | {g1[1]:+.2%} to {g1[2]:+.2%} | {'yes' if g1[1] > 0 else 'no'} | {g2[0]:+.2%} | {g2[1]:+.2%} to {g2[2]:+.2%} | "
                f"{'yes' if g2[1] > 0 else 'no'} | {g3[0]:+.2%} | {g4[0]:+.2%} | {ct:.0%}, {cd:.0%} | {g6[0]:+.2%} ({g6[1]:+.2%} to {g6[2]:+.2%}) | {g5[0]:+.2%} ({g5[1]:+.2%} to {g5[2]:+.2%}) |")
        say("")
    say.save()


if __name__ == "__main__":
    main()
