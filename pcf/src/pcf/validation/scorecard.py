"""The validation scorecard (docs/VALIDATION.md §11): one self-contained HTML page per run.

Saved in MLflow and next to the run's history (`outputs/<id>/<run_id>/scorecard.html`). It holds
the vault status and versions tried, the scores against every baseline with 90% intervals, the
signal and no-noise results, calibration or range coverage, where the model misses (dated lens
list), the leakage checklist, and the sanity results with the CEO's review lists.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

import polars as pl

from pcf.config import get_config
from pcf.validation import calibration, scores
from pcf.validation.misses import FLAG_LEVEL, LEVEL, MAX_FLAGGED, Misses

if TYPE_CHECKING:
    from pcf.validation.validate import Validation

STYLE = """
:root { --bg:#fbfaf7; --fg:#1d1c1a; --muted:#6b675f; --line:#e3dfd6; --ok:#1f7a4d; --bad:#b3261e;
        --flag:#9a6700; --card:#ffffff; --accent:#3b5bdb; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#161513; --fg:#ece9e2; --muted:#a29d93; --line:#34312c; --ok:#5cc28f;
          --bad:#f2827a; --flag:#e3b341; --card:#1f1d1a; --accent:#8da2fb; } }
body { background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif;
       margin:0 auto; max-width:980px; padding:24px 16px 64px; }
h1 { font-size:24px; margin:0 0 4px; } h2 { font-size:18px; margin:32px 0 8px; }
.muted { color:var(--muted); } .ok { color:var(--ok); font-weight:600; }
.bad { color:var(--bad); font-weight:600; } .flag { color:var(--flag); font-weight:600; }
.wrap { overflow-x:auto; } table { border-collapse:collapse; width:100%; font-size:14px; }
th, td { text-align:left; padding:6px 10px; border-bottom:1px solid var(--line); }
th { color:var(--muted); font-weight:600; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px;
        padding:12px 16px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; }
.big { font-size:22px; font-weight:650; }
"""


def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.3f}" if abs(value) < 1000 else f"{value:,.0f}"
    return escape(str(value))


def _table(df: pl.DataFrame) -> str:
    head = "".join(f"<th>{escape(c)}</th>" for c in df.columns)
    rows = []
    for row in df.iter_rows():
        cells = "".join(
            f'<td class="num">{_fmt(v)}</td>'
            if isinstance(v, int | float) and not isinstance(v, bool)
            else f"<td>{_status(v) if isinstance(v, bool) else _fmt(v)}</td>"
            for v in row
        )  # fmt: skip
        rows.append(f"<tr>{cells}</tr>")
    return f'<div class="wrap"><table><tr>{head}</tr>{"".join(rows)}</table></div>'


def _status(ok: bool, flag: bool = False) -> str:
    if ok:
        return '<span class="ok">pass</span>'
    return '<span class="flag">flag</span>' if flag else '<span class="bad">fail</span>'


def _card(label: str, value: str, note: str = "") -> str:
    return (
        f'<div class="card"><div class="muted">{escape(label)}</div>'
        f'<div class="big">{value}</div><div class="muted">{note}</div></div>'
    )


def _calibration_svg(table: pl.DataFrame) -> str:
    """Predicted vs actual rate per bin, with the diagonal."""
    size, pad = 260, 30
    inner = size - 2 * pad

    def xy(p: float, a: float) -> tuple[float, float]:
        return pad + p * inner, size - pad - a * inner

    dots = "".join(
        '<circle cx="{:.1f}" cy="{:.1f}" r="4" fill="var(--accent)"/>'.format(*xy(p, a))
        for p, a in table.select("predicted", "actual").iter_rows()
    )
    x0, y0 = xy(0, 0)
    x1, y1 = xy(1, 1)
    return (
        f'<svg viewBox="0 0 {size} {size}" width="{size}" role="img" '
        'aria-label="Calibration: predicted against actual rate">'
        f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="var(--line)" stroke-width="2"/>'
        f'<rect x="{pad}" y="{pad}" width="{inner}" height="{inner}" fill="none" '
        'stroke="var(--line)"/>'
        f"{dots}"
        f'<text x="{size / 2}" y="{size - 6}" fill="var(--muted)" font-size="11" '
        'text-anchor="middle">predicted</text></svg>'
    )


def misses_section(m: Misses | None) -> list[str]:
    """ "Where it misses": the fixed lenses, then the tags that stand out, with its dates."""
    if m is None:
        return []

    def show(df: pl.DataFrame) -> pl.DataFrame:
        return df.select(
            "lens", "when",
            (pl.col("bias_share") * 100).alias("bias share %"),
            (pl.col("spread_share") * 100).alias("spread share %"),
            "top_group", "top_rows", "avg_miss", "lo", "hi",
        )  # fmt: skip

    seasons = f"{m.seasons[0]}–{m.seasons[-1]}" if m.seasons else "none"
    out = [
        "<h2>Where it misses</h2>",
        f'<p class="muted">Lens list {escape(m.lens_list)} · scoring {escape(m.method)} · '
        f"measured {m.measured_at:%Y-%m-%d} · {m.rows:,} player-games, seasons {seasons}.</p>",
        '<p class="muted">A miss is actual minus projected (positive: the model was too low). '
        "Bias and spread shares: how much of the squared miss, and of the miss size, a correction "
        "per group removes when learned on the other half of the seasons. The top group is the "
        f"one with the largest average miss (200+ rows), with a {LEVEL:.0%} interval resampled by "
        'week. Lenses marked "after" are known only after the game: they explain misses and are '
        "never features.</p>",
        _table(show(m.lenses)),
    ]
    if m.flagged.is_empty():
        out.append(f'<p class="muted">No other tag stands out ({FLAG_LEVEL:.0%} interval).</p>')
    else:
        out += [
            f"<p>Tags that stand out (at most {MAX_FLAGGED}): the average miss where the tag "
            "fires, "
            "against the model's average at the same positions; the "
            f"{FLAG_LEVEL:.0%} interval excludes zero.</p>",
            _table(show(m.flagged)),
        ]
    if m.skipped:
        out.append(
            f'<p class="muted">Not measured (inputs missing): {escape(", ".join(m.skipped))}.</p>'
        )
    return out


def render_misses(m: Misses, title: str) -> str:
    """The miss report alone, as its own page (`pcf misses`)."""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Misses {escape(title)}</title><style>{STYLE}</style></head><body>"
        f"<h1>Where it misses: {escape(title)}</h1>" + "".join(misses_section(m)) + "</body></html>"
    )


def render(v: Validation) -> str:
    bt = v.bt
    expert = bt.expert
    kind = expert.kind
    vault = get_config().seasons.vault
    vault_text = f"opened ({v.made:%Y-%m-%d})" if v.vault_opened else "closed"
    summary = scores.summary(bt.scored, kind)
    main, readable = scores.MAIN[kind], scores.READABLE[kind]
    blocking = [ch for ch in v.checks if ch.blocking]
    passed = all(ch.passed for ch in blocking)

    head = [
        f"<h1>Scorecard: {escape(expert.label())}</h1>",
        f'<p class="muted">{escape(expert.quantity)} · {escape(expert.cadence)}'
        f"{' at the ' + escape(expert.run) + ' run' if expert.cadence == 'in_season' else ''}"
        f" · seasons {v.seasons[0]}–{v.seasons[-1]} · made {v.made:%Y-%m-%d %H:%M} UTC</p>",
        '<div class="grid">',
        _card(
            "Leakage checks",
            _status(passed),
            f"{sum(ch.passed for ch in blocking)} of {len(blocking)} blocking checks pass",
        ),  # fmt: skip
        _card(
            f"Main score ({main})", _fmt(summary[main]), f"{readable}: {_fmt(summary[readable])}"
        ),
        _card(f"Vault ({vault})", vault_text, "it opens once, for the final check"),
        _card("Versions tried", _fmt(v.versions_tried), "attempts in MLflow"),
        "</div>",
    ]

    label = expert.label()
    rows = [(label, summary[main], summary[readable], int(summary["rows"]), None, None, None,
             "—")]  # fmt: skip
    for name, hist in v.baselines.items():
        s = scores.summary(hist.filter(pl.col("y").is_not_null()), kind)
        comp = v.comparisons[name]
        rows.append((name, s[main], s[readable], int(s["rows"]), comp.diff, comp.lo, comp.hi,
                     comp.verdict))  # fmt: skip
    score_df = pl.DataFrame(
        rows,
        schema=["model", main, readable, "rows", "diff vs model", "90% lo", "90% hi", "model is"],
        orient="row",
    )
    body = [
        "<h2>Scores</h2>",
        f'<p class="muted">Lower is better. "diff vs model" is the model\'s {main} minus the '
        "baseline's on the same rows; the model beats a baseline only if the whole 90% interval "
        "(resampled by week) is below zero.</p>",
        _table(score_df),
    ]

    body.append("<h2>Signal and no noise</h2>")
    if v.signal is not None:
        s = v.signal
        body.append(
            f"<p>{_status(s.passed)} Beat {s.beaten} of {s.n} refits on shuffled outcomes "
            f"(needs {s.needed}). Real {main} {s.real:.3f}; shuffled from {min(s.nulls):.3f} "
            f"to {max(s.nulls):.3f}.</p>"
        )
    else:
        body.append('<p class="muted">Signal test not run.</p>')
    if v.no_noise is not None:
        verdict, comp = v.no_noise
        body.append(
            f"<p>{_status(verdict != 'adds noise')} No noise: {escape(verdict)} "
            f"(diff {comp.diff:.3f}, 90% {comp.lo:.3f} to {comp.hi:.3f}).</p>"
        )
    else:
        body.append('<p class="muted">No-noise test: no downstream target named.</p>')

    cal = v.calibration
    if cal.get("spike"):
        chance, share, blend = cal["chance"], cal["share"], cal["blend"]
        body += [
            "<h2>The two parts</h2>",
            f"<p>{_status(cal['passed'])} This forecast has a spike at 0, so each part is judged "
            "on its own (decision 0014).</p>",
            f"<p>{_status(chance['passed'])} <b>Chance the result is above 0:</b> calibration "
            f"error {chance['error']:.2f} points (bar ≤ {calibration.MAX_ERROR:.0f}); slope "
            f"{chance['slope']:.2f} (bar 0.9–1.1).</p>",
            _calibration_svg(chance["table"]),
            _table(chance["table"]),
            f"<p>{_status(share['passed'])} <b>The result where it was above 0:</b> q10–q90 holds "
            f"{share['inside']:.1%} of {share['rows']:,} results "
            f"(bar {calibration.COVERAGE[0]:.0%}–{calibration.COVERAGE[1]:.0%}); "
            f"{share['above']:.1%} land above q50 (bar 45–55%); average width "
            f"{share['width']:.2f}.</p>",
            '<p class="muted">Groups under 200 rows are shown, not judged (bar 70–90%).</p>',
            _table(share["groups"]),
            f'<p class="muted">The blend, reported and not judged: q10–q90 holds '
            f"{blend['inside']:.1%}, and {blend['above']:.1%} land above q50, average width "
            f"{blend['width']:.2f}. A result of exactly 0 counts as inside any range starting at "
            "0, so even a perfect forecast covers more than the 75–85% bar.</p>",
        ]
    elif kind == "amount":
        body += [
            "<h2>Range coverage</h2>",
            f"<p>{_status(cal['passed'])} q10–q90 holds {cal['inside']:.1%} of results "
            f"(bar {calibration.COVERAGE[0]:.0%}–{calibration.COVERAGE[1]:.0%}); "
            f"{cal['above']:.1%} land above q50 (bar 45–55%); average width "
            f"{cal['width']:.2f}.</p>",
            '<p class="muted">Groups under 200 rows are shown, not judged (bar 70–90%).</p>',
            _table(cal["groups"]),
        ]
    else:
        body += [
            "<h2>Calibration</h2>",
            f"<p>{_status(cal['passed'])} Calibration error {cal['error']:.2f} points "
            f"(bar ≤ {calibration.MAX_ERROR:.0f}); slope {cal['slope']:.2f} (bar 0.9–1.1).</p>",
            _calibration_svg(cal["table"]),
            _table(cal["table"]),
        ]

    checks = pl.DataFrame(
        [(ch.number, ch.name, ch.passed, "blocks" if ch.blocking else "flags", ch.detail)
         for ch in v.checks],
        schema=["#", "check", "pass", "kind", "detail"],
        orient="row",
    )  # fmt: skip
    body += misses_section(v.misses)
    body += ["<h2>Leakage checklist</h2>", _table(checks)]

    top, bottom = v.review
    body += [
        "<h2>Football sanity</h2>",
        _table(v.sanity),
        "<p><b>CEO review:</b> pending. The top and bottom 20 by the prediction:</p>",
        _table(top),
        _table(bottom),
    ]
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Scorecard {escape(expert.label())}</title><style>{STYLE}</style></head><body>"
        + "".join(head + body)
        + "</body></html>"
    )
