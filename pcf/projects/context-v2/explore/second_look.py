# ruff: noqa: E501
"""context-v2, the second look (2026-11-20): the CEO's conditional diffusion model (H85) against
the first look's trees, on the same plays (trained on 2023, scored on 2024).

Discovery only; the 2025 vault untouched. Designs and pass rules were committed before the run
(EXPLORATION.md, "Second look"; commits b970dee and ba7b4d3; decision 0039).

Run from pcf/:  python projects/context-v2/explore/second_look.py > projects/context-v2/explore/second_look.txt
"""

from __future__ import annotations

import importlib.util
import math
import time
from pathlib import Path

import numpy as np
import polars as pl
import torch
from sklearn.preprocessing import QuantileTransformer

from pcf.data.gateway import Gateway

c = pl.col
spec = importlib.util.spec_from_file_location("fl1", Path(__file__).with_name("first_look.py"))
fl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fl)
NAMES = list(fl.OUT)  # pressure, time_to_throw, sack, depth, completion, dropback_yards
COLS = [fl.OUT[n][0] for n in NAMES]
KIND = [fl.OUT[n][1] for n in NAMES]
STEPS, DDIM_STEPS, PASSES, BATCH, DRAWS, REVEAL = 100, 50, 200, 512, 64, 0.3
torch.set_num_threads(8)


def present(d: pl.DataFrame) -> np.ndarray:
    m = []
    for n, col in zip(NAMES, COLS, strict=True):
        ok = d[col].is_not_null().to_numpy()
        if fl.OUT[n][2] == "attempt":
            ok &= d["is_attempt"].to_numpy()
        m.append(ok)
    return np.column_stack(m)


class Coder:
    """Outcomes to numbers: yes-or-no as -1/+1, amounts as normal scores."""

    def __init__(self, d: pl.DataFrame, mask: np.ndarray):
        self.qt = {}
        for j, (col, kind) in enumerate(zip(COLS, KIND, strict=True)):
            if kind == "amount":
                v = d[col].to_numpy().astype(float)[mask[:, j]]
                self.qt[j] = QuantileTransformer(
                    n_quantiles=1000, output_distribution="normal", random_state=0
                ).fit(v[:, None])

    def encode(self, d: pl.DataFrame, mask: np.ndarray) -> np.ndarray:
        x = np.zeros((d.height, len(COLS)))
        for j, (col, kind) in enumerate(zip(COLS, KIND, strict=True)):
            v = np.nan_to_num(d[col].to_numpy().astype(float))
            x[:, j] = 2 * v - 1 if kind == "chance" else self.qt[j].transform(v[:, None])[:, 0]
        return np.where(mask, x, 0.0)

    def decode(self, j: int, z: np.ndarray) -> np.ndarray:
        return self.qt[j].inverse_transform(z.reshape(-1, 1)).reshape(z.shape)


def conditions(
    tr: pl.DataFrame, te: pl.DataFrame, fields: list[str]
) -> tuple[np.ndarray, np.ndarray]:
    a, b = fl.X(tr, fields), fl.X(te, fields)
    miss = np.isnan(a).any(0)
    mu, sd = np.nanmean(a, 0), np.nanstd(a, 0) + 1e-6

    def go(x):
        z = np.nan_to_num((x - mu) / sd)
        return np.column_stack([z, np.isnan(x[:, miss]).astype(float)])

    return go(a), go(b)


def schedule(T: int) -> torch.Tensor:
    s = 0.008
    t = torch.linspace(0, T, T + 1) / T
    f = torch.cos((t + s) / (1 + s) * math.pi / 2) ** 2
    return (f / f[0]).clamp(1e-5, 1)  # alpha-bar at 0..T


class Net(torch.nn.Module):
    def __init__(self, n_out: int, n_cond: int, width: int = 256):
        super().__init__()
        self.n_out = n_out
        d = n_out + 32 + n_cond + 2 * n_out
        self.body = torch.nn.Sequential(
            torch.nn.Linear(d, width),
            torch.nn.SiLU(),
            torch.nn.Linear(width, width),
            torch.nn.SiLU(),
            torch.nn.Linear(width, width),
            torch.nn.SiLU(),
            torch.nn.Linear(width, n_out),
        )

    def forward(self, x, t, cond, given_val, given_flag):
        k = torch.arange(16, dtype=torch.float32)
        ang = t[:, None].float() / STEPS * torch.exp(-math.log(1000) * k / 16)[None] * 1000
        emb = torch.cat([torch.sin(ang), torch.cos(ang)], 1)
        return self.body(torch.cat([x, emb, cond, given_val * given_flag, given_flag], 1))


def train(x0, mask, cond, seed: int) -> Net:
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    ab = schedule(STEPS)
    net = Net(x0.shape[1], cond.shape[1])
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=PASSES * math.ceil(len(x0) / BATCH)
    )
    X0, M, C = (torch.tensor(a, dtype=torch.float32) for a in (x0, mask, cond))
    t0 = time.perf_counter()
    for ep in range(PASSES):
        order = rng.permutation(len(x0))
        total = 0.0
        for i in range(0, len(order), BATCH):
            idx = torch.tensor(order[i : i + BATCH])
            x, m, cnd = X0[idx], M[idx], C[idx]
            reveal = (torch.rand(m.shape) < REVEAL) & (m > 0)
            t = torch.randint(1, STEPS + 1, (len(idx),))
            a = ab[t][:, None]
            eps = torch.randn_like(x)
            xt = a.sqrt() * x + (1 - a).sqrt() * eps
            pred = net(xt, t, cnd, x, reveal.float())
            w = m * (~reveal).float()
            loss = ((pred - eps) ** 2 * w).sum() / w.sum().clamp(min=1)
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            total += float(loss) * len(idx)
        if ep in (0, 9, 49, 99, 149, PASSES - 1):
            print(
                f"  seed {seed} pass {ep + 1}: training loss {total / len(order):.4f} ({time.perf_counter() - t0:.0f}s)",
                flush=True,
            )
    return net


@torch.no_grad()
def draw(
    net: Net, cond: np.ndarray, given_val: np.ndarray, given_flag: np.ndarray, seed: int
) -> np.ndarray:
    """DDIM (eta 0) in DDIM_STEPS steps; DRAWS plays per row. Returns rows x draws x outcomes."""
    torch.manual_seed(seed)
    ab = schedule(STEPS)
    ts = torch.linspace(STEPS, 1, DDIM_STEPS).round().long()
    out = []
    for i in range(0, len(cond), 1024):
        cnd = torch.tensor(cond[i : i + 1024], dtype=torch.float32).repeat_interleave(DRAWS, 0)
        gv = torch.tensor(given_val[i : i + 1024], dtype=torch.float32).repeat_interleave(DRAWS, 0)
        gf = torch.tensor(given_flag[i : i + 1024], dtype=torch.float32).repeat_interleave(DRAWS, 0)
        x = torch.randn(len(cnd), net.n_out)
        for k, t in enumerate(ts):
            a = ab[t]
            a_prev = ab[ts[k + 1]] if k + 1 < len(ts) else torch.tensor(1.0)
            eps = net(x, t.repeat(len(x)), cnd, gv, gf)
            x0 = ((x - (1 - a).sqrt() * eps) / a.sqrt()).clamp(-6, 6)
            x = a_prev.sqrt() * x0 + (1 - a_prev).sqrt() * eps
        out.append(x.reshape(-1, DRAWS, net.n_out).numpy())
    return np.concatenate(out)


def estimates(z: np.ndarray, coder: Coder) -> dict[str, np.ndarray]:
    out = {}
    for j, (n, kind) in enumerate(zip(NAMES, KIND, strict=True)):
        if kind == "chance":
            out[n] = np.clip((z[:, :, j] > 0).mean(1), 0.5 / DRAWS, 1 - 0.5 / DRAWS)
        else:
            out[n] = coder.decode(j, z[:, :, j]).mean(1)
    return out


def main() -> None:
    src = Gateway().source
    d, t1, t2, hind = fl.table(src)
    tr, te = d.filter(c("season") == fl.TRAIN), d.filter(c("season") == fl.TEST)
    m_tr, m_te = present(tr), present(te)
    coder = Coder(tr, m_tr)
    x_tr, x_te = coder.encode(tr, m_tr), coder.encode(te, m_te)
    c_tr, c_te = conditions(tr, te, t2)
    print(
        f"Dropbacks: {tr.height} (2023) and {te.height} (2024); {c_tr.shape[1]} condition columns; outcomes present in 2024: "
        + ", ".join(f"{n} {m_te[:, j].mean():.0%}" for j, n in enumerate(NAMES))
    )

    none_v, none_f = np.zeros_like(x_te), np.zeros_like(x_te)
    pv, pf = none_v.copy(), none_f.copy()
    j_pr = NAMES.index("pressure")
    pv[:, j_pr], pf[:, j_pr] = x_te[:, j_pr], m_te[:, j_pr].astype(float)
    est = {}
    for seed in (0, 1):
        net = train(x_tr, m_tr.astype(float), c_tr, seed)
        est[("before", seed)] = estimates(draw(net, c_te, none_v, none_f, 10 + seed), coder)
        z_pre = draw(net, c_te, pv, pf, 20 + seed)
        est[("given", seed)] = estimates(z_pre, coder)
        if seed == 0:
            z_before = draw(net, c_te, none_v, none_f, 30)

    res, cmp_rows = [], []
    for j, (name, kind) in enumerate(zip(NAMES, KIND, strict=True)):
        col = COLS[j]
        rtr, rte = fl.rows_for(tr, name), fl.rows_for(te, name)
        keep = m_te[:, j]
        y = rte[col].to_numpy().astype(float)
        base = float(rtr[col].mean())
        trees = {
            "trees, before the snap": fl.predict(fl.fit(rtr, t2, col, kind), rte, t2, kind),
        }
        if name != "pressure":
            trees["trees, given a pressure"] = fl.predict(
                fl.fit(rtr, t2 + ["pressure_y"], col, kind), rte, t2 + ["pressure_y"], kind
            )
        for label, p in trees.items():
            res.append({"outcome": name, "model": label, **fl.summary(y, p, base, kind)})
        for mode in ("before", "given"):
            if mode == "given" and name == "pressure":
                continue
            for seed in (0, 1):
                p = est[(mode, seed)][name][keep]
                res.append(
                    {
                        "outcome": name,
                        "model": f"diffusion, {'before the snap' if mode == 'before' else 'given a pressure'} (seed {seed})",
                        **fl.summary(y, p, base, kind),
                    }
                )
            p0 = est[(mode, 0)][name][keep]
            tl = "trees, before the snap" if mode == "before" else "trees, given a pressure"
            cmp_rows.append(
                {
                    "outcome": name,
                    "mode": mode,
                    **fl.paired(rte, y, p0, trees[tl], kind, ("diffusion", "trees")),
                }
            )

    pl.Config.set_tbl_rows(100)
    pl.Config.set_tbl_width_chars(220)
    pl.Config.set_fmt_str_lengths(60)
    print(
        "\n== Each outcome, 2024 (share = % of squared error removed against 2023's average; logloss_gain = % of log loss removed; p10/p90 = the spread of chances)"
    )
    print(pl.DataFrame(res, infer_schema_length=None).with_columns(pl.selectors.float().round(2)))
    print(
        "\n== Diffusion (seed 0) against the trees (gain = % of the trees' mean loss the diffusion model removes; negative = worse; clear = the interval is above zero)"
    )
    cm = pl.DataFrame(cmp_rows).with_columns(worse=c("hi_pct") < 0)
    print(cm.with_columns(pl.selectors.float().round(3)))
    pre = cm.filter(c("mode") == "before")
    print(
        f"H85: before the snap, clearly better on {int(pre['clear'].sum())} of 6, clearly worse on {int(pre['worse'].sum())}; 'matches' (interval includes zero or |gain| <= 0.5%) on {int(((~pre['clear'] & ~pre['worse']) | (pre['gain_pct'].abs() <= 0.5)).sum())}"
    )
    giv = cm.filter(c("mode") == "given")
    print(
        f"Given a pressure: within 1% of the trees' loss on {int((giv['gain_pct'].abs() <= 1).sum())} of {giv.height}"
    )

    # the joint: the four combinations of pressure and sack, before the snap
    rte = fl.rows_for(te, "pressure").filter(c("sack_y").is_not_null())
    rtr_p = fl.rows_for(tr, "pressure").filter(c("sack_y").is_not_null())
    keep = m_te[:, j_pr] & m_te[:, NAMES.index("sack")]
    zp = z_before[keep]
    combo = (rte["pressure_y"].to_numpy() * 2 + rte["sack_y"].to_numpy()).astype(int)
    pr_d, sk_d = zp[:, :, j_pr] > 0, zp[:, :, NAMES.index("sack")] > 0
    joint_d = np.stack(
        [((pr_d == bool(a)) & (sk_d == bool(b))).mean(1) for a in (0, 1) for b in (0, 1)], 1
    )
    joint_d = (joint_d * DRAWS + 0.25) / (DRAWS + 1)
    p_pr = fl.predict(fl.fit(rtr_p, t2, "pressure_y", "chance"), rte, t2, "chance")
    p_sk = fl.predict(fl.fit(rtr_p, t2, "sack_y", "chance"), rte, t2, "chance")
    indep = np.stack(
        [(1 - p_pr) * (1 - p_sk), (1 - p_pr) * p_sk, p_pr * (1 - p_sk), p_pr * p_sk], 1
    )
    msk = fl.fit(rtr_p, t2 + ["pressure_y"], "sack_y", "chance")
    s0 = fl.predict(msk, rte.with_columns(pressure_y=pl.lit(0.0)), t2 + ["pressure_y"], "chance")
    s1 = fl.predict(msk, rte.with_columns(pressure_y=pl.lit(1.0)), t2 + ["pressure_y"], "chance")
    chain = np.stack([(1 - p_pr) * (1 - s0), (1 - p_pr) * s0, p_pr * (1 - s1), p_pr * s1], 1)
    ll = {
        k: float(-np.log(np.clip(v[np.arange(len(combo)), combo], 1e-6, 1)).mean())
        for k, v in (
            ("diffusion", joint_d),
            ("trees multiplied (independent)", indep),
            ("trees, the chain (pressure, then sack given it)", chain),
        )
    }
    obs = np.bincount(combo, minlength=4) / len(combo)
    print(
        "\n== The joint of pressure and sack, before the snap: mean log loss of the combination that happened (lower is better)"
    )
    print({k: round(v, 4) for k, v in ll.items()})
    print(
        "Shares (no pressure no sack, no pressure sack, pressure no sack, pressure sack): actual",
        obs.round(4).tolist(),
        "| diffusion",
        joint_d.mean(0).round(4).tolist(),
        "| independent",
        indep.mean(0).round(4).tolist(),
        "| chain",
        chain.mean(0).round(4).tolist(),
    )


if __name__ == "__main__":
    main()
