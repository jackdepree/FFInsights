"""The validation scorecard (docs/VALIDATION.md §11): one self-contained HTML page per run.

Saved in MLflow and next to the run's history (`outputs/<id>/<run_id>/scorecard.html`). It holds
the vault status and versions tried, the scores against every baseline with 90% intervals, the
signal and no-noise results, calibration or range coverage, the leakage checklist, and the
sanity results with the CEO's review lists.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

import polars as pl

from pcf.config import get_config
from pcf.validation import calibration, scores

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
    if kind == "amount":
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
