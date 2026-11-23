"""How much of the block reward is left for new streams.

New streams can only take weight from the burn residual w0 = 1 - w1 - w2.
This module works out that residual quarter by quarter for a few demand
scenarios, and the part of it an automatic mechanism could use if it always
keeps one gate step free for w2.

Run:  python -m autostreams.headroom
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Callable

from . import fip0118 as fip
from .weights import apply_write, residual, validate

SCENARIOS: dict[str, Callable[[int], bool]] = {
    "every gate passes": lambda q: True,
    "every other gate passes": lambda q: q % 2 == 0,
    "no gate passes": lambda q: False,
}

INDICATIVE_ISSUANCE_FIL = 20_000_000  # per year, the figure FIP-0118 uses


@dataclass(frozen=True)
class QuarterRow:
    scenario: str
    quarter: int
    w1_start: Fraction
    w2_end: Fraction
    residual_min: Fraction
    residual_max: Fraction
    usable_min: Fraction  # after reserving one gate step


def usable(res: Fraction, w2: Fraction) -> Fraction:
    """Residual left once the next w2 step is set aside."""
    reserve = fip.W2_STEP if w2 < fip.W2_CAP else Fraction(0)
    return max(Fraction(0), res - reserve)


def table(horizon: int = 12, p: fip.Params = fip.MAINNET) -> list[QuarterRow]:
    rows: list[QuarterRow] = []
    for name, passes in SCENARIOS.items():
        base = fip.bootstrap_records(p)
        writes = fip.gate_writes(passes, horizon, p)
        assert not validate(base, writes), "FIP schedule must be valid"
        for q in range(1, horizon + 1):
            start, end = p.quarter_start(q), p.quarter_start(q + 1) - 1
            # The residual is linear between writes, so the extremes sit at the
            # quarter edges and on either side of each write.
            points = {start, end}
            for w in writes:
                if start < w.effective_epoch <= end:
                    points.update({w.effective_epoch - 1, w.effective_epoch})
            samples = []
            for e in sorted(points):
                recs = base
                for w in writes:
                    if w.effective_epoch <= e:
                        recs = apply_write(recs, w)
                w2 = recs[fip.SERVICE_ID].at(e)
                r = residual(recs, e)
                samples.append((r, usable(r, w2), w2, recs[fip.CONSENSUS_ID].at(e)))
            rows.append(
                QuarterRow(
                    scenario=name,
                    quarter=q,
                    w1_start=samples[0][3],
                    w2_end=samples[-1][2],
                    residual_min=min(s[0] for s in samples),
                    residual_max=max(s[0] for s in samples),
                    usable_min=min(s[1] for s in samples),
                )
            )
    return rows


def pct(x: Fraction) -> str:
    return f"{float(x) * 100:.1f}"


def write_csv(rows: list[QuarterRow], path: Path) -> None:
    with path.open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(
            ["scenario", "quarter", "w1_start_pct", "w2_end_pct",
             "residual_min_pct", "residual_max_pct", "usable_min_pct"]
        )
        for r in rows:
            out.writerow(
                [r.scenario, r.quarter, pct(r.w1_start), pct(r.w2_end),
                 pct(r.residual_min), pct(r.residual_max), pct(r.usable_min)]
            )


def series(
    passes: Callable[[int], bool], horizon: int = 12, p: fip.Params = fip.MAINNET
) -> list[tuple[int, Fraction]]:
    """(epoch, residual) points over the horizon. Straight lines join them."""
    base = fip.bootstrap_records(p)
    writes = fip.gate_writes(passes, horizon, p)
    end = p.quarter_start(horizon + 1)
    epochs = {p.quarter_start(q) for q in range(1, horizon + 2)}
    for w in writes:
        if w.effective_epoch < end:
            epochs.update({w.effective_epoch - 1, w.effective_epoch})
    out = []
    for e in sorted(epochs):
        recs = base
        for w in writes:
            if w.effective_epoch <= e:
                recs = apply_write(recs, w)
        out.append((e, residual(recs, e)))
    return out


def write_svg(path: Path, horizon: int = 12, p: fip.Params = fip.MAINNET) -> None:
    """Plain SVG line chart of the burn residual over time."""
    width, height, left, bottom, top, right = 720, 380, 56, 48, 28, 190
    plot_w, plot_h = width - left - right, height - top - bottom
    y_max = 45.0
    span = p.quarter_start(horizon + 1)
    colors = ["#1f6feb", "#bf8700", "#cf222e"]

    def x(epoch: int) -> float:
        return left + epoch / span * plot_w

    def y(v: float) -> float:
        return top + plot_h - v / y_max * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="Helvetica, Arial, sans-serif" font-size="12">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ]
    for v in range(0, 46, 5):
        parts.append(
            f'<line x1="{left}" y1="{y(v):.1f}" x2="{left + plot_w}" y2="{y(v):.1f}" '
            f'stroke="#d0d7de" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y(v) + 4:.1f}" text-anchor="end" fill="#57606a">{v}%</text>'
        )
    for q in range(1, horizon + 1):
        x0, x1 = x(p.quarter_start(q)), x(p.quarter_start(q + 1))
        parts.append(
            f'<line x1="{x0:.1f}" y1="{top + plot_h}" x2="{x0:.1f}" y2="{top + plot_h + 5}" '
            f'stroke="#8c959f" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{(x0 + x1) / 2:.1f}" y="{height - bottom + 20}" text-anchor="middle" '
            f'fill="#57606a">Q{q}</text>'
        )
    # Draw the fastest scenario last so its sawtooth stays on top.
    for i, name in reversed(list(enumerate(SCENARIOS))):
        pts = " ".join(
            f"{x(e):.1f},{y(float(r) * 100):.1f}" for e, r in series(SCENARIOS[name], horizon, p)
        )
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="{colors[i]}" stroke-width="2" '
            f'stroke-linejoin="round"/>'
        )
        ly = top + 14 + i * 22
        parts.append(
            f'<line x1="{left + plot_w + 16}" y1="{ly - 4}" x2="{left + plot_w + 40}" '
            f'y2="{ly - 4}" stroke="{colors[i]}" stroke-width="2.5"/>'
        )
        parts.append(f'<text x="{left + plot_w + 46}" y="{ly}" fill="#24292f">{name}</text>')
    parts.append(
        f'<text x="{left}" y="16" fill="#24292f" font-size="13">'
        f"Burn residual over the first {horizon} quarters, share of block reward</text>"
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n")


def main(argv: list[str]) -> int:
    rows = table()
    for name in SCENARIOS:
        print(f"\n{name}")
        print("  quarter   w1(start)  w2(end)  residual min..max   usable min")
        for r in (r for r in rows if r.scenario == name):
            print(
                f"  Q{r.quarter:<7} {pct(r.w1_start):>6}%  {pct(r.w2_end):>6}%  "
                f"{pct(r.residual_min):>6}% .. {pct(r.residual_max):>5}%   {pct(r.usable_min):>6}%"
            )
    per_point = INDICATIVE_ISSUANCE_FIL // 100
    print(f"\nOne point of weight is about {per_point:,} FIL a year at ~20M FIL issuance.")
    if len(argv) > 1:
        out = Path(argv[1])
        out.mkdir(parents=True, exist_ok=True)
        write_csv(rows, out / "headroom.csv")
        write_svg(out / "headroom.svg")
        print(f"Wrote {out / 'headroom.csv'} and {out / 'headroom.svg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
