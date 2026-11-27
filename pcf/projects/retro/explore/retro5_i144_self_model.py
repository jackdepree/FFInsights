# ruff: noqa: E501
"""Retro 5: I144, a self-model. Do plain tags predict which bets come true better than our own written odds?

Fit on every scored bet of retros 3 and 4 (their calibration scripts' lists), scored on retro 5's (retro5_calibration.py,
the aging hunches on their proposed verdicts). The tags, the ones every list carries: who bet (the CEO or Claude),
which number (the first number on a hunch or a side bet), the hunch's kind (claim or method; side bets have none),
and whether the bet's wording holds a number (a size or a threshold: digits or a percentage; read the same way for
every retro, since retro 3's lists have no size flag). A plain logistic (L2, C=1) on those tags; never the stated odds.
Against it: the written odds, and the base rate (each group's share that came true through retro 4).

Odds, written before any test (Claude, 2026-11-25, IDEAS.md): 35% it beats Claude's odds on "holds"; 50% it beats both
of ours on "pays". Pays is asked only of the CEO's hunches, and there are 9 of them in retro 5, so pays is read with
that caveat. Not the 20 bets the idea named: retro 5 has 140.
Run from pcf/:  python projects/retro/explore/retro5_i144_self_model.py > projects/retro/explore/retro5_i144_self_model.txt
"""

import contextlib
import io
import re
import runpy
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).parent


def lists(name):
    with contextlib.redirect_stdout(io.StringIO()):
        return runpy.run_path(str(HERE / name))


NUM = re.compile(r"\d")


def rows(ns, retro):
    out = []
    for key, who, role in (("ceo", "ceo", "main"), ("ceo_closed", "ceo", "main"), ("ceo_aging", "ceo", "main"),
                           ("claude_main", "claude", "main"), ("claude_main_aging", "claude", "main"),
                           ("claude_side", "claude", "side"), ("claude_side_aging", "claude", "side")):
        for r in ns.get(key, []):
            kind = r[3] if role == "main" and isinstance(r[3], str) else "none"
            pays = r[4] if who == "ceo" and len(r) > 4 else None
            out.append({"retro": retro, "who": who, "role": role, "kind": kind, "num": bool(NUM.search(r[0].split(" ", 1)[-1])) if role == "side" else False,
                        "p": r[1], "y": r[2], "pays": pays, "name": r[0]})
    return out


data = rows(lists("retro3_calibration.py"), 3) + rows(lists("retro4_calibration.py"), 4) + rows(lists("retro5_calibration.py"), 5)


def X(rs):
    return np.array([[r["who"] == "ceo", r["role"] == "side", r["kind"] == "method", r["num"]] for r in rs], dtype=float)


def brier(p, y):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


tr = [r for r in data if r["retro"] < 5]
te = [r for r in data if r["retro"] == 5]
print(f"fit on {len(tr)} bets (retros 3-4), scored on {len(te)} (retro 5)")
m = LogisticRegression(C=1.0).fit(X(tr), [r["y"] for r in tr])
print("coefficients (CEO, side bet, method, has a number):", np.round(m.coef_[0], 2).tolist(), "intercept", round(float(m.intercept_[0]), 2))
pm = m.predict_proba(X(te))[:, 1]


def base(r):
    g = [q["y"] for q in tr if (q["who"], q["role"]) == (r["who"], r["role"])]
    return np.mean(g)


pb = np.array([base(r) for r in te])
yy = np.array([r["y"] for r in te])
pw = np.array([r["p"] for r in te])
print("\n== holds, retro 5's bets: Brier (lower is better)")
for name, sel in (("all", lambda r: True), ("the CEO's first numbers", lambda r: r["who"] == "ceo"),
                  ("Claude's on the CEO's claims", lambda r: r["who"] == "claude" and r["role"] == "main"),
                  ("Claude's side bets", lambda r: r["role"] == "side"),
                  ("Claude's, all", lambda r: r["who"] == "claude")):
    k = np.array([sel(r) for r in te])
    print(f"  {name:<30} n {k.sum():>3}: written odds {brier(pw[k], yy[k]):.3f}, self-model {brier(pm[k], yy[k]):.3f}, base rate {brier(pb[k], yy[k]):.3f}")
# side bets with a number against without: the self-model's one lever
for flag in (True, False):
    k = np.array([r["role"] == "side" and r["num"] == flag for r in te])
    print(f"  side bets {'with' if flag else 'without'} a number: n {k.sum()}, came true {yy[k].mean():.0%}, written {pw[k].mean():.0%}, self-model {pm[k].mean():.0%}")

# pays: the CEO's hunches only
trp = [r for r in tr if r["pays"] is not None]
tep = [r for r in te if r["pays"] is not None]
mp = LogisticRegression(C=1.0).fit(X(trp)[:, [2]], [r["pays"] for r in trp])
pp = mp.predict_proba(X(tep)[:, [2]])[:, 1]
yp = np.array([r["pays"] for r in tep])
ceo_w = np.array([r["p"] for r in tep])
claude_w = []
for r in tep:
    h = r["name"].split()[0]
    cm = [q for q in te if q["who"] == "claude" and q["role"] == "main" and q["name"].split()[0] == h]
    claude_w.append(cm[0]["p"] if cm else np.nan)
claude_w = np.array(claude_w)
ok = ~np.isnan(claude_w)
print(f"\n== pays, the CEO's {len(tep)} hunches in retro 5 (fit on {len(trp)}; tag: method or claim)")
print(f"  self-model {brier(pp[ok], yp[ok]):.3f}, the CEO's odds {brier(ceo_w[ok], yp[ok]):.3f}, Claude's {brier(claude_w[ok], yp[ok]):.3f} (n {ok.sum()}); paid {yp.sum()} of {len(yp)}")
holds_beats = brier(pm[[r['who'] == 'claude' for r in te]], yy[[r['who'] == 'claude' for r in te]]) < brier(pw[[r['who'] == 'claude' for r in te]], yy[[r['who'] == 'claude' for r in te]])
print(f"\n== verdicts: beats Claude's odds on holds (35%): {'yes' if holds_beats else 'no'}; beats both on pays (50%): {'yes' if brier(pp[ok], yp[ok]) < min(brier(ceo_w[ok], yp[ok]), brier(claude_w[ok], yp[ok])) else 'no'}")
