"""Study M3: high-volume revisit (design frozen in
reports/dev/M2_PARTB_ADJUDICATION.md before any run on real data).

The folklore claim: a bar that trades on abnormally high volume marks a
level the market "cares about", and price returns to that level. We test
the falsifiable core of that claim — do the midpoints of high-volume bars
get revisited *more often than matched control bars*, conditional on price
first leaving the level?

Bindings (all fixed before the real-data run):

* **Spike** — a bar whose volume exceeds the trailing rolling ``q``-quantile
  of the prior ``trailing`` bars (the quantile is ``shift(1)`` so the bar's
  own volume never enters its own threshold). Spikes are then *isolated*:
  a spike is kept only if no other spike occurred within the prior
  ``isolation`` bars, so clustered volume is counted once.
* **Departure** — from the spike bar, the first bar within ``horizon // 2``
  whose close is at least ``depart_atr`` * ATR(at spike) away from the
  spike midpoint. Events (and controls) that never depart are excluded:
  a level that was never left cannot be "revisited".
* **Revisit** — after departure, any bar within ``horizon`` whose range
  brackets the spike midpoint (``low <= mid <= high``).
* **Controls** — ``k`` non-spike bars matched to the event on ATR (within
  ``vol_tol``) and killzone flag; the control revisit statistic is the mean
  over the controls that themselves departed.
* **Statistic** — the ratio of the event revisit rate to the control
  revisit rate, with a block-bootstrap CI. Support (either direction) if
  the CI excludes 1 on >= 2/3 datasets.

Descriptive research on burned data; full-sample computation is legitimate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..core import Candles, atr as compute_atr
from .magnetism import _ratio_block_ci


def volume_spike_mask(candles: Candles, q: float = 0.99, trailing: int = 2880,
                      isolation: int = 96) -> np.ndarray:
    """Boolean mask of isolated high-volume bars.

    A bar is a spike if its volume exceeds the trailing ``q``-quantile of the
    prior ``trailing`` bars (own bar excluded via ``shift(1)``). Spikes within
    ``isolation`` bars of a previous spike are dropped so clusters count once.
    """
    vol = pd.Series(candles.volume)
    thresh = vol.rolling(trailing).quantile(q).shift(1).to_numpy()
    spike = candles.volume > thresh
    spike &= ~np.isnan(thresh)
    idx = np.flatnonzero(spike)
    keep = np.zeros(len(candles), dtype=bool)
    last = -10**9
    for t in idx:
        if t - last > isolation:
            keep[t] = True
        last = t
    return keep


def _depart_revisit(candles: Candles, t: int, horizon: int, depart_atr: float,
                    atr_t: float) -> tuple[bool, bool]:
    """(departed, revisited) for the bar at index ``t``.

    Departure: first bar in (t, t + horizon//2] whose close is >= depart_atr
    ATRs from the midpoint of bar t. Revisit: any bar after departure and
    within (t, t + horizon] whose range touches that midpoint.
    """
    mid = 0.5 * (candles.high[t] + candles.low[t])
    n = len(candles)
    d_end = min(t + horizon // 2, n - 1)
    j = -1
    for i in range(t + 1, d_end + 1):
        if abs(candles.close[i] - mid) >= depart_atr * atr_t:
            j = i
            break
    if j == -1:
        return False, False
    r_end = min(t + horizon, n - 1)
    for i in range(j + 1, r_end + 1):
        if candles.low[i] <= mid <= candles.high[i]:
            return True, True
    return True, False


def run_revisit_study(candles: Candles, kz_mask: np.ndarray | None = None,
                      horizons: tuple[int, ...] = (96, 384), q: float = 0.99,
                      trailing: int = 2880, isolation: int = 96,
                      depart_atr: float = 1.0, k: int = 20, vol_tol: float = 0.25,
                      atr_period: int = 14, seed: int = 42) -> list[dict]:
    a = compute_atr(candles, atr_period)
    n = len(candles)
    kz = kz_mask if kz_mask is not None else np.zeros(n, dtype=bool)
    spike = volume_spike_mask(candles, q, trailing, isolation)
    spikes = [int(t) for t in np.flatnonzero(spike)]
    rng = np.random.default_rng(seed)
    idx_all = np.arange(n)
    rows = []
    for N in horizons:
        ev_rev, ctl_rev = [], []
        for t in spikes:
            if not (trailing < t < n - N) or a[t] <= 0:
                continue
            departed, revisited = _depart_revisit(candles, t, N, depart_atr, a[t])
            if not departed:
                continue
            eligible = idx_all[(~spike) & (a >= a[t] * (1 - vol_tol))
                               & (a <= a[t] * (1 + vol_tol)) & (kz == kz[t])
                               & (idx_all > trailing) & (idx_all < n - N)]
            if len(eligible) == 0:
                continue
            picks = rng.choice(eligible, size=min(k, len(eligible)), replace=False)
            ctl = []
            for j in picks:
                dep, rev = _depart_revisit(candles, int(j), N, depart_atr, a[j])
                if dep:
                    ctl.append(1.0 if rev else 0.0)
            if not ctl:
                continue
            ev_rev.append(1.0 if revisited else 0.0)
            ctl_rev.append(float(np.mean(ctl)))
        ev_arr, ctl_arr = np.array(ev_rev), np.array(ctl_rev)
        if len(ev_arr) < 5:
            rows.append({"horizon": N, "n": len(ev_arr), "revisit_rate": float("nan"),
                         "control_rate": float("nan"), "ratio": float("nan"),
                         "ci_lo": float("nan"), "ci_hi": float("nan")})
            continue
        ratio, lo, hi = _ratio_block_ci(ev_arr, ctl_arr)
        rows.append({"horizon": N, "n": int(len(ev_arr)),
                     "revisit_rate": float(ev_arr.mean()),
                     "control_rate": float(ctl_arr.mean()),
                     "ratio": ratio, "ci_lo": lo, "ci_hi": hi})
    return rows


def render_revisit_table(rows: list[dict], title: str) -> str:
    lines = [f"**{title}** — revisit of high-volume bar midpoints "
             "(conditional on a >= 1 ATR departure)", "",
             "| horizon | n | event revisit | control revisit | ratio | 95% CI |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['horizon']} | {r['n']} | {r['revisit_rate']:.3f} | "
                     f"{r['control_rate']:.3f} | {r['ratio']:.3f} | "
                     f"[{r['ci_lo']:.3f}, {r['ci_hi']:.3f}] |")
    return "\n".join(lines)
