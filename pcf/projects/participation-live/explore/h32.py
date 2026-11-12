"""H32: a player's past participation tendencies predict whether he's on each play. A first
reconstruction of 2022-2024 games, from what's known by the morning after (snap counts, named
players, the play-by-play's situation, depth charts) plus earlier seasons' true participation.

Each team-game-side is a table: plays (rows, 11 each) by the players with snaps for that side
(columns, each adding to his snap count, scaled to the plays we have). Named players and players
on every snap are fixed at 1. Every method's chances are then balanced to both totals (logit
raking, a smooth form of iterative proportional fitting), and the best guess takes each play's
most likely players.

Methods (each a prior for the open cells, then the same balancing):
- share: the snap share alone (the brief's baseline)
- league: the share plus the league's situational habits by position group (learned 2019-2021)
- history (H32 + H33): plus his own situational habits from earlier seasons and his team's from
  last season (the true participation of completed seasons only)
- shuffled: history with the history features shuffled across rows (rule k's null)
- oracle: history plus his true on/off on the team's previous snap (not usable; an upper bound for
  what a sequence model over the drive could add)
Also the depth chart: the same lineup every play, by depth then snap share (named players in).
"""

# ruff: noqa: E501
import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

from common import GROUP, SEASONS, _part, lineups, named, panel, plays, snaps

c = pl.col
TRAIN, TEST = [2019, 2020, 2021], [2022, 2023, 2024]
P = plays().filter(c("season") >= 2019)
FLAGS = {
    "third": c("down") == 3, "fourth": c("down") == 4, "short": (c("ydstogo") <= 2) & (c("down") >= 2),
    "long": (c("ydstogo") >= 8) & (c("down") >= 2), "red": c("yardline_100") <= 20, "goal": c("yardline_100") <= 5,
    "twomin": c("half_seconds_remaining") <= 120, "garbage": (c("qtr") == 4) & (c("score_differential").abs() >= 17),
    "q4": c("qtr") == 4, "shotgun": c("shotgun") == 1, "no_huddle": c("no_huddle") == 1, "first_snap": c("drive_n") == 0,
    "pass": c("pass") == 1,
}  # fmt: skip


def flags(df):
    return df.with_columns(**{f"f_{k}": v.fill_null(False) for k, v in FLAGS.items()})


# ---------- history from the true participation of completed seasons (the panel: part-timers) ----------
H = flags(panel()).with_columns(res=c("on") - c("share"))
ph, th = [], []
for S in [*TRAIN, *TEST]:
    past = H.filter(c("season") < S)
    agg = past.group_by("gsis_id").agg(
        *[((c("res") * c(f"f_{k}")).sum() / (c(f"f_{k}").sum() + 100)).alias(f"ph_{k}") for k in FLAGS],
        ph_n=pl.len(),
    )  # fmt: skip
    ph.append(agg.with_columns(season=pl.lit(S, pl.Int32)))
    last = H.filter(c("season") == S - 1)
    tagg = last.group_by("team", "side", "group").agg(
        *[((c("res") * c(f"f_{k}")).sum() / (c(f"f_{k}").sum() + 300)).alias(f"th_{k}") for k in FLAGS]
    )
    th.append(tagg.with_columns(season=pl.lit(S, pl.Int32)))
PH, TH = pl.concat(ph), pl.concat(th)

# ---------- the grid: every player with snaps for the side x the side's plays ----------
sn = snaps().filter(c("season") >= 2019).with_columns(group=c("position").replace_strict(GROUP, default=None))
plays_side = pl.concat([
    P.with_columns(side=pl.lit("offense"), team=c("posteam")),
    P.with_columns(side=pl.lit("defense"), team=c("defteam")),
]).select("game_id", "play_id", "side", "team", "season", "n", "fixed_drive", *[k for k in ("down", "ydstogo", "yardline_100", "half_seconds_remaining", "qtr", "score_differential", "shotgun", "no_huddle", "drive_n", "pass")])  # fmt: skip
n_plays = plays_side.group_by("game_id", "side", "team").agg(n_plays=pl.len())
cand = pl.concat([
    sn.filter(c("offense_snaps") > 0).select("game_id", "team", "gsis_id", "group", "position", snap=c("offense_snaps")).with_columns(side=pl.lit("offense")),
    sn.filter(c("defense_snaps") > 0).select("game_id", "team", "gsis_id", "group", "position", snap=c("defense_snaps")).with_columns(side=pl.lit("defense")),
]).drop_nulls("team")  # fmt: skip
cand = cand.join(n_plays, on=["game_id", "side", "team"])
cand = cand.with_columns(tot=c("snap").sum().over("game_id", "side", "team")).with_columns(
    share=(c("snap") * 11 / c("tot")).clip(0, 1), full=c("snap") >= c("snap").max().over("game_id", "side", "team")
)
cand = cand.with_columns(group=c("group").fill_null("OTHER"))
G = cand.select("game_id", "side", "team", "gsis_id", "group", "share", "full").join(plays_side, on=["game_id", "side", "team"])
key = ["game_id", "play_id", "side", "gsis_id"]
G = G.join(lineups().select(key).with_columns(on=pl.lit(1, pl.Int8)), on=key, how="left").with_columns(c("on").fill_null(0))
G = G.join(named().select(key).with_columns(named=pl.lit(True)), on=key, how="left").with_columns(c("named").fill_null(False))
G = G.with_columns(pinned=c("named") | c("full"))
G = flags(G)
G = G.join(PH, on=["gsis_id", "season"], how="left").join(TH, on=["team", "side", "group", "season"], how="left")
G = G.with_columns(pl.col("^ph_.*$").fill_null(0), pl.col("^th_.*$").fill_null(0))
# the oracle's previous snap (true), same game
G = G.sort("game_id", "side", "gsis_id", "n").with_columns(
    prev_on=c("on").shift(1).over("game_id", "side", "gsis_id").fill_null(1),
    same_drive=(c("fixed_drive") == c("fixed_drive").shift(1).over("game_id", "side", "gsis_id")).fill_null(False),
)
print(f"grid 2019-2024: {G.height:,} player-plays; open (not pinned) {(~G['pinned']).mean():.1%}; truth on among open {G.filter(~c('pinned'))['on'].mean():.1%}")
true_cover = G.group_by("game_id", "play_id", "side").agg(found=c("on").sum())
print(f"share of true on-field players who are candidates (have snaps): {true_cover['found'].sum() / (true_cover.height * 11):.2%}")

F = [f"f_{k}" for k in FLAGS]


def feats(df, kind, shuffle=None):
    ls = (c("share").clip(0.01, 0.99) / (1 - c("share").clip(0.01, 0.99))).log()
    cols = [ls, ls**2, *[c(f) for f in F], (c("drive_n").clip(0, 15) / 5)]
    if kind in ("history", "shuffled", "oracle"):
        cols += [c(f"ph_{k}") * c(f"f_{k}") for k in FLAGS] + [c(f"th_{k}") * c(f"f_{k}") for k in FLAGS]
        cols += [c("ph_n").fill_null(0).clip(0, 3000) / 1000]
    if kind == "oracle":
        cols += [c("prev_on") * c("same_drive"), c("prev_on") * ~c("same_drive"), c("same_drive")]
    m = df.select([x.cast(pl.Float32).fill_null(0).alias(f"x{i}") for i, x in enumerate(cols)]).to_numpy()
    if kind == "shuffled":
        rng = np.random.default_rng(shuffle)
        a = 2 + len(F) + 1
        m[:, a:] = m[rng.permutation(len(m)), a:]
    return m


# ---------- fit the priors per position group, on open cells of the training seasons ----------
open_tr = G.filter(~c("pinned") & c("season").is_in(TRAIN))
TE = G.filter(c("season").is_in(TEST))
prior = {k: np.zeros(TE.height) for k in ("share", "league", "history", "shuffled", "oracle")}
prior["share"] = TE["share"].clip(0.01, 0.99).to_numpy()
grp_te = TE["group"].to_numpy()
for g in sorted(open_tr["group"].unique()):
    tr = open_tr.filter(c("group") == g)
    idx = np.where(grp_te == g)[0]
    if tr.height < 2000 or not len(idx):
        for k in ("league", "history", "shuffled", "oracle"):
            prior[k][idx] = prior["share"][idx]
        continue
    te = TE[idx]
    y = tr["on"].to_numpy()
    for k in ("league", "history", "shuffled", "oracle"):
        m = LogisticRegression(max_iter=300).fit(feats(tr, k, 1), y)
        prior[k][idx] = m.predict_proba(feats(te, k, 2))[:, 1]
    print(f"fitted {g}: {tr.height:,} training cells")


# ---------- balance each team-game-side table to its totals (logit raking) ----------
def rake(z, fixed, row_t, col_t, iters=25):
    """z: logits (plays x players); fixed: cells pinned at 1. Adjust a row and a column offset so
    each play's open cells add to row_t and each player's to col_t; finish on the rows."""
    a, b = np.zeros(z.shape[0]), np.zeros(z.shape[1])
    free = ~fixed
    for it in range(iters):
        for axis in ((1, 0) if it < iters - 1 else (1, 1)):
            for _ in range(4):
                p = 1 / (1 + np.exp(-(z + a[:, None] + b[None, :]))) * free
                d = p * (1 - p)
                if axis == 1:
                    a += (row_t - p.sum(1)) / np.maximum(d.sum(1), 1e-6)
                    a = np.clip(a, -25, 25)
                else:
                    b += (col_t - p.sum(0)) / np.maximum(d.sum(0), 1e-6)
                    b = np.clip(b, -25, 25)
    p = 1 / (1 + np.exp(-(z + a[:, None] + b[None, :])))
    return np.where(fixed, 1.0, p * free)


TE = TE.with_row_index("i")
order = TE.sort("game_id", "side", "team", "n", "gsis_id")
results = {k: np.zeros(TE.height) for k in prior}
pick = {k: np.zeros(TE.height, dtype=bool) for k in prior}
for (gid, side, team), d in order.group_by(["game_id", "side", "team"], maintain_order=True):
    plays_ = d["play_id"].unique(maintain_order=True).to_list()
    players = d["gsis_id"].unique(maintain_order=True).to_list()
    pi = {p: i for i, p in enumerate(plays_)}
    pj = {p: j for j, p in enumerate(players)}
    r = np.array([pi[x] for x in d["play_id"].to_list()])
    q = np.array([pj[x] for x in d["gsis_id"].to_list()])
    rows_i = d["i"].to_numpy()
    shape = (len(plays_), len(players))
    fixed = np.zeros(shape, bool)
    fixed[r, q] = d["pinned"].to_numpy()
    share = np.zeros(len(players))
    share[q] = d["share"].to_numpy()
    row_t = np.clip(11 - fixed.sum(1), 0, None)
    col_t = np.clip(share * len(plays_) - fixed.sum(0), 0, (~fixed).sum(0))
    for k in prior:
        z = np.full(shape, -30.0)
        z[r, q] = np.log(np.clip(prior[k][rows_i], 1e-4, 1 - 1e-4) / (1 - np.clip(prior[k][rows_i], 1e-4, 1 - 1e-4)))
        pr = rake(z, fixed, row_t, col_t)
        results[k][rows_i] = pr[r, q]
        # best guess: the pinned players plus each play's most likely open players
        g = fixed.copy()
        open_p = np.where(fixed, -1, pr)
        for i in range(shape[0]):
            need = int(row_t[i])
            if need > 0:
                g[i, np.argsort(-open_p[i])[:need]] = True
        pick[k][rows_i] = g[r, q]

# the depth chart: the same lineup every play (depth, then snap share), named players in
dep = _part("player_game", "depth", TEST, ["gsis_id", "game_id", "depth"]).group_by("gsis_id", "game_id").agg(c("depth").min())
TE = TE.join(dep, on=["gsis_id", "game_id"], how="left").sort("i")
TE = TE.with_columns(rank_key=c("depth").fill_null(9) * 10 - c("share"))
TE = TE.with_columns(
    open_rank=pl.when(~c("pinned")).then(c("rank_key")).rank("ordinal").over("game_id", "play_id", "side"),
    n_pin=c("pinned").sum().over("game_id", "play_id", "side"),
)
pick["depth"] = (TE["pinned"] | (TE["open_rank"] <= (11 - TE["n_pin"]))).fill_null(False).to_numpy()

y = TE["on"].to_numpy().astype(float)
op = ~TE["pinned"].to_numpy()
grp = TE["group"].to_numpy()


def ll(p, m):
    p = np.clip(p[m], 1e-4, 1 - 1e-4)
    return float(-(y[m] * np.log(p) + (1 - y[m]) * np.log(1 - p)).mean())


print(f"\nTest 2022-2024: {TE.height:,} player-plays, {TE.select('game_id', 'play_id', 'side').n_unique():,} play-sides; open cells {op.sum():,}")
rows = []
keys = TE.select("game_id", "play_id", "side").with_columns(side_off=c("side") == "offense")
for k in [*prior, "depth"]:
    pk = pick[k]
    hits = TE.select("game_id", "play_id", "side").with_columns(hit=pl.Series(pk & (y == 1)), true_open=pl.Series(op & (y == 1)), hit_open=pl.Series(pk & op & (y == 1)))
    per = hits.group_by("game_id", "play_id", "side").agg(c("hit").sum(), c("true_open").sum(), c("hit_open").sum())
    r_ = {"method": k}
    for s in ("offense", "defense"):
        x = per.filter(c("side") == s)
        r_[f"{s}_of_11"] = x["hit"].sum() / (x.height * 11)
        r_[f"{s}_open_right"] = x["hit_open"].sum() / x["true_open"].sum()
        r_[f"{s}_all11_right"] = (x["hit"] == 11).mean()
    if k in prior:
        r_["open_log_loss"] = ll(results[k], op)
        r_["open_ll_raw_prior"] = ll(prior[k], op)
    rows.append(r_)
with pl.Config(tbl_cols=12, float_precision=4):
    print("Best guess and on-field chances (open cells = not named, not on every snap):")
    print(pl.DataFrame(rows))

print("\nOpen-slot accuracy by position group (share of the true open on-field players the best guess gets):")
by = []
for g in sorted(set(grp)):
    m = op & (grp == g) & (y == 1)
    if m.sum() < 5000:
        continue
    by.append({"group": g, "true_open_on": int(m.sum()), **{k: float(pick[k][m].mean()) for k in [*prior, "depth"]}})
with pl.Config(tbl_rows=20, tbl_cols=12, float_precision=3):
    print(pl.DataFrame(by))

print("\nCalibration of the history method's balanced chances (open cells):")
p = results["history"]
cal = pl.DataFrame({"p": p[op], "y": y[op]}).with_columns(bin=(c("p") * 10).floor().clip(0, 9))
print(cal.group_by("bin").agg(mean_p=c("p").mean(), on_rate=c("y").mean(), n=pl.len()).sort("bin"))

# sanity: plays add to 11, players add to their snap targets
chk = TE.with_columns(p=pl.Series(results["history"]), g=pl.Series(pick["history"]))
s11 = chk.group_by("game_id", "play_id", "side").agg(sp=c("p").sum(), sg=c("g").sum())
print(f"\nsanity: mean |sum of chances - 11| per play {(s11['sp'] - 11).abs().mean():.3f}; best guess with 11: {(s11['sg'] == 11).mean():.1%}")
col = chk.group_by("game_id", "side", "gsis_id").agg(sp=c("p").sum(), sg=c("g").sum(), target=c("share").first() * pl.len(), true=c("on").sum())
print(f"players: mean |chances total - snap target| {(col['sp'] - col['target']).abs().mean():.2f} plays; |best-guess total - true| {(col['sg'] - col['true']).abs().mean():.2f}; |chances total - true| {(col['sp'] - col['true']).abs().mean():.2f}")
nh = chk.filter(c("f_no_huddle") & (c("side") == "offense") & c("same_drive"))
print(f"no-huddle offensive snaps: best guess equals the previous snap's for the player {(nh['g'] == nh['g'].shift(1)).mean():.1%} (not yet a constraint); truth unchanged from the previous snap {(nh['on'] == nh['prev_on']).mean():.1%}")
_ = SEASONS
