"""Aging, method 2 (EXPLORATION.md): load, risk and roles. H115 (mileage split by kind), H116 (roles beyond snaps and
age), H118 (risk-weighted mileage). Discovery only, 2002-2024; the 2025 vault is closed.

Run from pcf/:  python projects/aging/explore/m2_load.py   (writes m2_load.txt)

Deviations from the pre-registration (technical calls, in EXPLORATION.md):
- The per-play injury note has a fixed form ("TEAM-##-Name was injured during the play") only from 2005; before that the
  notes are free text. The risk logistic is fit on 2005-2009 (not 1999-2009) and scored on 2010-2024.
- Model A is method 1's smooth age form (a cubic in age), which beat the one-step-a-year form everywhere in method 1.
"""

# ruff: noqa: E501
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from aging_common import CACHE, LAST, OFF, Say, load, pairs, pass_plays, wls  # noqa: E402

c = pl.col
RNG = np.random.default_rng(2)
say = Say(Path(__file__).with_suffix(".txt"))
TYPES = ["throw", "sack", "target", "catch", "carry", "scramble"]


# ---------------------------------------------------------------- the per-play risk score
def involvements() -> pl.DataFrame:
    """One row per (play, involved skill player): his kind of involvement, the play's yards, a tackle, a QB hit, and
    whether the play's note names him as injured (from 2005, by team and jersey)."""
    p = CACHE / "involvements.parquet"
    if p.exists():
        return pl.read_parquet(p)
    S = list(range(1999, LAST + 1))
    pbp = read_pbp(S)
    tg = pass_plays(S).select("game_id", "play_id", "rid")
    pbp = pbp.join(tg, on=["game_id", "play_id"], how="left")
    base = ["game_id", "play_id", "season", "posteam", "defteam", "yards_gained", "tackled", "qb_hit", "inj"]
    dropb = pbp.filter((c("pass_attempt") == 1) | (c("sack") == 1)).select(*base, gsis_id="passer_player_id", jersey="passer_jersey_number",
                                                                          kind=pl.when(c("sack") == 1).then(pl.lit("sack")).otherwise(pl.lit("throw")))
    tgt = pbp.filter((c("pass_attempt") == 1) & (c("sack") == 0)).select(*base, gsis_id="rid", jersey="receiver_jersey_number",
                                                                         kind=pl.when(c("complete_pass") == 1).then(pl.lit("catch")).otherwise(pl.lit("target")))
    car = pbp.filter(c("rush_attempt") == 1).select(*base, gsis_id="rusher_player_id", jersey="rusher_jersey_number",
                                                    kind=pl.when(c("qb_scramble") == 1).then(pl.lit("scramble")).otherwise(pl.lit("carry")))
    iv = pl.concat([dropb, tgt, car], how="diagonal_relaxed").drop_nulls("gsis_id")
    # explode the injured list and match: jersey equal and injured team not the defense
    ex = iv.select("game_id", "play_id", "gsis_id", "jersey", "defteam", "inj").explode("inj").drop_nulls("inj").with_columns(
        it=c("inj").struct.field("team"), ij=c("inj").struct.field("j"))
    ex = ex.filter((c("ij") == c("jersey")) & (c("it") != c("defteam"))).select("game_id", "play_id", "gsis_id").unique().with_columns(hurt=pl.lit(1))
    iv = iv.drop("inj").join(ex, on=["game_id", "play_id", "gsis_id"], how="left").with_columns(
        hurt=pl.when(c("season") >= 2005).then(c("hurt").fill_null(0)).otherwise(None))
    iv.write_parquet(p)
    return iv


def read_pbp(S) -> pl.DataFrame:
    from pcf.data.gateway import read_part

    pbp = read_part("play", "pbp", S, None).select(
        "game_id", "play_id", "season", "season_type", "posteam", "defteam", "desc", "pass_attempt", "sack", "rush_attempt", "qb_scramble",
        "complete_pass", "two_point_attempt", "yards_gained", "solo_tackle", "assist_tackle", "qb_hit",
        "passer_player_id", "passer_jersey_number", "receiver_jersey_number", "rusher_player_id", "rusher_jersey_number",
    ).collect().filter((c("season_type") == "REG") & (c("two_point_attempt").fill_null(0) == 0))  # fmt: skip
    m = c("desc").str.extract_all(r"([A-Z]{2,3})-(\d+)-\S+ was injured during the play")
    pbp = pbp.with_columns(inj_raw=m).with_columns(
        inj=c("inj_raw").list.eval(pl.struct(team=pl.element().str.extract(r"^([A-Z]{2,3})-", 1),
                                             j=pl.element().str.extract(r"^[A-Z]{2,3}-(\d+)-", 1).cast(pl.Int32))),
        tackled=((c("solo_tackle").fill_null(0) + c("assist_tackle").fill_null(0)) > 0).cast(pl.Int8),
        qb_hit=c("qb_hit").fill_null(0).cast(pl.Int8), yards_gained=c("yards_gained").fill_null(0),
        passer_jersey_number=c("passer_jersey_number").cast(pl.Int32, strict=False),
        receiver_jersey_number=c("receiver_jersey_number").cast(pl.Int32, strict=False),
        rusher_jersey_number=c("rusher_jersey_number").cast(pl.Int32, strict=False),
    ).drop("inj_raw", "desc")
    return pbp


def risk_design(iv: pl.DataFrame, pos: pl.DataFrame) -> np.ndarray:
    iv = iv.join(pos, on=["gsis_id", "season"], how="left").with_columns(c("pos").fill_null("UNK"))
    y = iv["yards_gained"].clip(-10, 40).to_numpy().astype(float)
    cols = [(iv["kind"] == k).to_numpy().astype(float) for k in TYPES]
    cols += [y / 10, (y / 10) ** 2, iv["tackled"].to_numpy().astype(float), iv["qb_hit"].to_numpy().astype(float)]
    cols += [(iv["kind"] == k).to_numpy() * iv["tackled"].to_numpy().astype(float) for k in ("catch", "carry", "scramble")]
    cols += [(iv["pos"] == p).to_numpy().astype(float) for p in ("QB", "RB", "WR", "TE")]
    return np.column_stack(cols)


def risk_mileage(say) -> pl.DataFrame:
    """Fits the per-play logistic on 2005-2009, scores 2010-2024, and returns each player-season's cumulative
    risk-weighted mileage (the sum of every involvement's chance of an injury, 1999 through s)."""
    iv = involvements()
    s = load("season").select("gsis_id", "season", "pos")
    lab = iv.filter(c("hurt").is_not_null())
    tr, te = lab.filter(c("season") <= 2009), lab.filter(c("season") >= 2010)
    m = LogisticRegression(C=1.0, max_iter=2000).fit(risk_design(tr, s), tr["hurt"].to_numpy())
    pt = m.predict_proba(risk_design(te, s))[:, 1]
    auc = roc_auc_score(te["hurt"].to_numpy(), pt)
    # a plain count's AUC (every involvement equal) is 0.5; a kind-only model is the simple twin
    k1 = LogisticRegression(max_iter=2000).fit(risk_design(tr, s)[:, :6], tr["hurt"].to_numpy())
    auc_k = roc_auc_score(te["hurt"].to_numpy(), k1.predict_proba(risk_design(te, s)[:, :6])[:, 1])
    rate = lab.group_by("kind").agg(n=pl.len(), r=c("hurt").mean()).sort("r", descending=True)
    say("## The per-play injury score", "",
        f"Involvements 1999-2024: {iv.height:,} (dropbacks, targets, carries). Labelled 2005-2024 (the note's fixed form): {lab.height:,}, of which {int(lab['hurt'].sum()):,} name the player as injured "
        f"({lab['hurt'].mean():.3%}).",
        "Injury rate by kind (2005-2024): " + ", ".join(f"{k} {r:.3%}" for k, n, r in rate.iter_rows()) + ".",
        f"The logistic (kind, yards, a tackle, a QB hit, kind by tackle, position), fit 2005-2009: AUC on 2010-2024 **{auc:.3f}** (kind alone: {auc_k:.3f}). The bet: above 0.6 (Claude 60%).", "")
    iv = iv.with_columns(risk=pl.Series(m.predict_proba(risk_design(iv, s))[:, 1]))
    ps = iv.group_by("gsis_id", "season").agg(r=c("risk").sum()).sort("gsis_id", "season").with_columns(cm_risk=c("r").cum_sum().over("gsis_id"))
    return ps.select("gsis_id", "season", "cm_risk"), auc


# ---------------------------------------------------------------- the forecasts
def agez(x):
    z = (x["age"].clip(21, 36).to_numpy() - 27) / 5
    return [z, z**2, z**3]


def feats(x, spec, roles_cols):
    cols = [np.ones(x.height), x["x"].to_numpy()] + agez(x)
    if "mil" in spec:
        cols += [np.log1p(x["cm_pass"].to_numpy()), np.log1p(x["cm_rush"].to_numpy())]
    if "risk" in spec:
        cols += [np.log1p(x["cm_risk"].to_numpy())]
    if "roles" in spec:
        cols += [x[r].fill_null(0).to_numpy() for r in roles_cols]
    if "hist" in spec:  # the obvious inputs: his last two seasons' pulled rate (0 and a flag when missing) and his years in the league
        cols += [x["l1"].fill_null(0).to_numpy(), x["l2"].fill_null(0).to_numpy(), x["l1"].is_null().to_numpy().astype(float),
                 x["l2"].is_null().to_numpy().astype(float), (x["season"] - x["entry"]).to_numpy().astype(float)]
    return np.column_stack(cols).astype(float)


def walk(x, specs, first_T, roles_cols=(), ridge=1e-2, logit=False):
    out = []
    for T in range(first_T, 2025):
        tr, te = x.filter(c("T") < T), x.filter(c("T") == T)
        if tr.height < 200 or te.height == 0:
            continue
        cols = {}
        for nm, spec in specs.items():
            A, B = feats(tr, spec, roles_cols), feats(te, spec, roles_cols)
            mu, sd = A[:, 1:].mean(0), A[:, 1:].std(0) + 1e-9
            A[:, 1:], B[:, 1:] = (A[:, 1:] - mu) / sd, np.clip((B[:, 1:] - mu) / sd, -5, 5)
            if logit:
                m = LogisticRegression(C=1.0, max_iter=2000).fit(A[:, 1:], tr["gone"].to_numpy())
                cols[nm] = m.predict_proba(B[:, 1:])[:, 1]
            else:
                b = wls(A, tr["y"].to_numpy(), tr["w"].to_numpy(), ridge)
                cols[nm] = B @ b
        out.append(te.with_columns(**{k: pl.Series(v) for k, v in cols.items()}))
    return pl.concat(out)


def err(f, col, logit):
    if logit:
        p = f[col].clip(1e-4, 1 - 1e-4)
        g = f["gone"].cast(pl.Float64)
        return -(g * np.log(p) + (1 - g) * np.log(1 - p)).to_numpy()
    return (f["w"] * (f["y"] - f[col]) ** 2).to_numpy()


def pooled(fs: dict, new: str, old: str, logit=False, draws=1000):
    """The mean over positions of each position's share of the old model's error that the new removes (each position
    weighs the same: their errors are on different scales); players resampled within each position."""
    per, mats = {}, []
    for pos, f in fs.items():
        e = f.select("gsis_id").with_columns(a=pl.Series(err(f, new, logit)), b=pl.Series(err(f, old, logit)))
        p = e.group_by("gsis_id").agg(a=c("a").sum(), b=c("b").sum())
        A, B = p["a"].to_numpy(), p["b"].to_numpy()
        idx = RNG.integers(0, len(A), (draws, len(A)))
        g = 1 - A[idx].sum(1) / B[idx].sum(1)
        per[pos] = (1 - A.sum() / B.sum(), np.quantile(g, 0.05), np.quantile(g, 0.95))
        mats.append(g)
    G = np.mean(mats, 0)
    pt = float(np.mean([v[0] for v in per.values()]))
    return pt, float(np.quantile(G, 0.05)), float(np.quantile(G, 0.95)), per


def fmt(t):
    return f"{t[0]:+.2%} ({t[1]:+.2%} to {t[2]:+.2%})"


def rows(d, pos, kind):
    x = d.filter(c("pos") == pos)
    if kind == "u":
        x = x.filter(c("cu2").is_not_null() & c("pu").is_not_null()).with_columns(x=c("pu"), y=c("cu2"), w=pl.lit(1.0))
    elif kind == "e":
        x = x.filter(c("pe").is_not_null() & c("ce2").is_not_null() & (c("n2") > 0)).with_columns(x=c("pe"), y=c("ce2"), w=c("n2").cast(pl.Float64))
    else:  # still playing: every pair
        x = x.filter(c("pu").is_not_null()).with_columns(x=c("pu"), y=c("gone").cast(pl.Float64), w=pl.lit(1.0))
    lag = "pe" if kind == "e" else "pu"
    L = d.select("gsis_id", "season", lag).unique(["gsis_id", "season"])
    x = x.join(L.select("gsis_id", season=c("season") + 1, l1=lag), on=["gsis_id", "season"], how="left").join(
        L.select("gsis_id", season=c("season") + 2, l2=lag), on=["gsis_id", "season"], how="left")
    return x.with_columns(T=c("season") + 1)


def main() -> None:
    say("# Method 2: load, risk and roles (2026-11-25)", "",
        "Careers that started in 1999 or later (entry year), so mileage counts are complete. Mileage through season s from play-by-play: passing involvements (dropbacks for",
        "passers, targets for receivers) and rushing involvements (carries), logs of each. Every model is one weighted ridge per position on next season's rate, standardized inputs,",
        "walk-forward (targets 2010-2024; roles 2018-2024). Model A is method 1's age model (smooth: a cubic in age). Scores are the share of the simpler model's error removed;",
        "pooled scores average the four offensive positions (each weighs the same), players resampled within each position (1,000 draws); clear means the 90% interval leaves out 0.", "")
    rm, auc = risk_mileage(say)
    d = pairs().filter(c("entry") >= 1999).join(rm, on=["gsis_id", "season"], how="left").with_columns(c("cm_risk").fill_null(0))
    ra = pl.read_parquet(glob.glob(str(CACHE.parent.parent / "outputs" / "roles-archetypes" / "*" / "history.parquet"))[0])
    rc = ["z0", "z1", "z2", "z3", "z4", "z5", "t0_snap_share", "t1_tgt_per_pass", "t2_car_per_run", "t3_adot", "t4_adj_run", "t5_adj_p11"]
    ra = ra.filter(c("side") == "offense").sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first").select("gsis_id", "season", *rc)
    say(f"Pairs from careers starting 1999+: {d.height:,} (offense {d.filter(c('pos').is_in(OFF)).height:,}).", "")

    specs = {"A": ["age"], "B": ["age", "mil"], "D": ["age", "risk"], "BD": ["age", "mil", "risk"], "H": ["age", "hist"], "HB": ["age", "hist", "mil"], "HD": ["age", "hist", "risk"]}
    F = {}
    for kind in ("u", "e", "g"):
        for pos in OFF:
            F[(kind, pos)] = walk(rows(d, pos, kind), specs, 2010, logit=(kind == "g"))
    say("## H115 (mileage split by kind) and H118 (risk-weighted mileage)", "",
        "| Comparison | Usage (0 if he left) | Efficiency | Still playing (log loss) |", "|---|---|---|---|")
    res = {}
    for new, old, label in (("B", "A", "B (age + mileage) against A (age)"), ("D", "A", "D (age + risk-weighted mileage) against A"), ("D", "B", "D against B"), ("BD", "B", "B + risk against B")):
        r = [pooled({p: F[(k, p)] for p in OFF}, new, old, logit=(k == "g")) for k in ("u", "e", "g")]
        res[(new, old)] = r
        say(f"| {label} | {fmt(r[0])} | {fmt(r[1])} | {fmt(r[2])} |")
    say("", "**The obvious-input check:** H adds the obvious inputs to A (his last two seasons' pulled rate and his years in the league), then mileage or risk on top.", "",
        "| Comparison | Usage | Efficiency | Still playing |", "|---|---|---|---|")
    for new, old, label in (("H", "A", "H (A + history) against A"), ("HB", "H", "H + mileage against H"), ("HD", "H", "H + risk-weighted mileage against H")):
        r = [pooled({p: F[(k, p)] for p in OFF}, new, old, logit=(k == "g")) for k in ("u", "e", "g")]
        res[(new, old)] = r
        say(f"| {label} | {fmt(r[0])} | {fmt(r[1])} | {fmt(r[2])} |")
    say("", "By position (usage; efficiency; still playing):", "")
    for new, old in (("B", "A"), ("D", "A"), ("D", "B"), ("HB", "H"), ("HD", "H")):
        for pos in OFF:
            say(f"- {new} against {old}, {pos}: " + "; ".join(fmt(res[(new, old)][i][3][pos]) for i in range(3)))
    b_u, b_e = res[("B", "A")][0][1] > 0, res[("B", "A")][1][1] > 0
    side115 = any(res[("B", "A")][i][3][p][1] > 0 for i in (0, 1) for p in OFF)
    say("", f"H115: B beats A clearly for usage: {'yes' if b_u else 'no'}; for efficiency: {'yes' if b_e else 'no'} (passes if both). Side (one kind at one position or more): {'yes' if side115 else 'no'}.",
        f"H118: D beats A clearly on usage with the zeros, pooled: {'yes' if res[('D', 'A')][0][1] > 0 else 'no'}. Side: D beats B for running backs (usage): {'yes' if res[('D', 'B')][0][3]['RB'][1] > 0 else 'no'};"
        f" D beats A on still playing: {'yes' if res[('D', 'A')][2][1] > 0 else 'no'}.", "")

    # coefficients' signs, read on all rows (what mileage does once age is in)
    say("What mileage does with age held, all rows (standardized coefficients, usage; efficiency):", "")
    for pos in OFF:
        parts = []
        for kind in ("u", "e"):
            x = rows(d, pos, kind)
            A = feats(x, ["age", "mil", "risk"], ())
            A[:, 1:] = (A[:, 1:] - A[:, 1:].mean(0)) / (A[:, 1:].std(0) + 1e-9)
            b = wls(A, x["y"].to_numpy(), x["w"].to_numpy(), 1e-2)
            parts.append(f"passing {b[5]:+.4f}, rushing {b[6]:+.4f}, risk {b[7]:+.4f}")
        cr = np.corrcoef(np.log1p(d.filter(c("pos") == pos)["cm_pass"].to_numpy() + d.filter(c("pos") == pos)["cm_rush"].to_numpy()), d.filter(c("pos") == pos)["age"].to_numpy())[0, 1]
        say(f"- {pos}: {parts[0]}; {parts[1]}. Mileage's correlation with age: {cr:.2f}")

    # H116: roles, 2016+ rows
    say("", "## H116 (roles beyond mileage and age), 2016+ rows with a roles-and-archetypes row, targets 2018-2024", "",
        "| Kind | C (B + roles) against B, pooled | By position |", "|---|---|---|")
    r116 = {}
    for kind in ("u", "e", "g"):
        fs = {}
        for pos in OFF:
            x = rows(d, pos, kind).join(ra, on=["gsis_id", "season"], how="inner")
            if x.height < 300:
                continue
            fs[pos] = walk(x, {"B": ["age", "mil"], "C": ["age", "mil", "roles"]}, 2018, rc, ridge=0.1, logit=(kind == "g"))
        r = pooled(fs, "C", "B", logit=(kind == "g"))
        r116[kind] = r
        say(f"| {dict(u='usage', e='efficiency', g='still playing')[kind]} | {fmt(r)} | " + "; ".join(f"{p} {fmt(v)}" for p, v in r[3].items()) + " |")
    say("", f"H116: C beats B clearly for usage: {'yes' if r116['u'][1] > 0 else 'no'}; for efficiency: {'yes' if r116['e'][1] > 0 else 'no'} (passes if both). Side (usage alone): {'yes' if r116['u'][1] > 0 else 'no'}.")
    say.save()


if __name__ == "__main__":
    main()
