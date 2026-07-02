"""Development diagnostics: does a bias/factor separate forward returns?

The key development question for a narrative layer is whether its states
predict anything *before* triggers get involved.  ``forward_return_table``
groups bars by a discrete state array and reports the mean forward log
return per state with an honest t-statistic.

Statistical note: consecutive bars share most of their forward window, so
computing a t-stat over *overlapping* windows wildly overstates
significance.  By default the table samples non-overlapping windows
(``step = horizon_bars``); pass ``step=1`` only if you want the
(optimistic) dense means for descriptive purposes.
"""

from __future__ import annotations

import math

import numpy as np

from ..core import Candles


def forward_return_table(
    candles: Candles,
    states: np.ndarray,
    horizon_bars: int = 96,
    step: int | None = None,
) -> list[dict]:
    """Rows of {state, n, mean_fwd_logret, t_stat} grouped by state value.

    ``states[i]`` must be knowable at bar i's close (the caller is
    responsible for using confirm-index-safe arrays such as
    ``SMCStrategy.bias`` or ``sign(NarrativeEngine.factors[...])``).
    The forward return of bar i is ``log(close[i+h] / close[i])``.
    """
    if len(states) != len(candles):
        raise ValueError("states must align 1:1 with candles")
    if horizon_bars < 1 or horizon_bars >= len(candles):
        raise ValueError("horizon_bars out of range")
    step = horizon_bars if step is None else max(1, step)

    close = candles.close
    n_usable = len(candles) - horizon_bars
    idx = np.arange(0, n_usable, step)
    fwd = np.log(close[idx + horizon_bars]) - np.log(close[idx])
    s = np.asarray(states)[idx]

    rows = []
    for value in sorted(set(np.unique(s).tolist())):
        r = fwd[s == value]
        n = len(r)
        mean = float(r.mean()) if n else 0.0
        if n > 1:
            sd = float(r.std(ddof=1))
            t = mean / (sd / math.sqrt(n)) if sd > 0 else 0.0
        else:
            t = 0.0
        rows.append({"state": float(value), "n": n,
                     "mean_fwd_logret": mean, "t_stat": float(t)})
    return rows


def render_forward_table(rows: list[dict], title: str) -> str:
    lines = [f"**{title}** (non-overlapping windows)", "",
             "| state | n | mean fwd logret | t |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['state']:+.0f} | {r['n']} | "
                     f"{r['mean_fwd_logret']:+.5f} | {r['t_stat']:+.2f} |")
    return "\n".join(lines)
