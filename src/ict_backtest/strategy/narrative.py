"""Narrative engine: mechanized HTF judgment ("which way is the market going").

Study V3 replaces the single structure-direction bias with a weighted vote
of narrative factors, each an attempt to codify one input ICT cites when
"writing the narrative":

* ``struct_mtf``  — 4h structure direction (last BOS/MSS).
* ``struct_htf``  — daily structure direction.
* ``struct_wk``   — weekly structure direction (the highest timeframe with
                    enough bars to confirm swings on a multi-year sample;
                    monthly candles produce too few events to test).
* ``dol``         — draw on liquidity: imbalance of untaken daily liquidity
                    pools and unfilled daily FVGs above vs. below price.
                    Price is assumed to seek the heavier, nearer draw.
* ``ipda``        — IPDA data-range logic across ICT's full 20/40/60-day
                    triple (his stated substitute for calendar weekly and
                    monthly context): a close-break *above* a prior range
                    high is continuation; a *sweep* of a range low with a
                    close back above it is reversal — mirrored bearish.
                    Each window votes; the factor is their average, so
                    agreement across horizons scales conviction.  Events
                    hold for a fixed number of daily bars.

Each factor produces a per-daily-bar value in [-1, +1]; values become
visible to base bars only *after* the HTF bar closes (same bucket rule as
the rest of the codebase, so prefix consistency holds).  The narrative
score is the weighted mean; a bias is declared only when conviction
exceeds a threshold — no conviction, no trade.
"""

from __future__ import annotations

import numpy as np

from ..core import BEAR, BULL, Candles, resample
from ..detectors import detect_fvgs, detect_liquidity_pools, detect_structure, detect_swings


def _broadcast(n_base: int, last_base: np.ndarray, states: np.ndarray) -> np.ndarray:
    """Map per-HTF-bar states to base bars: bucket k sees the state after
    bucket k-1's close; bars after the final bucket see the last state."""
    out = np.zeros(n_base)
    for k in range(len(states)):
        start = int(last_base[k - 1]) + 1 if k > 0 else 0
        out[start : int(last_base[k]) + 1] = states[k - 1] if k > 0 else 0.0
    if len(states):
        out[int(last_base[-1]) + 1 :] = states[-1]
    return out


def _structure_states(htf: Candles, swing_k: int) -> np.ndarray:
    swings = detect_swings(htf, swing_k)
    events = detect_structure(htf, swings)
    states = np.zeros(len(htf))
    cur, ei = 0.0, 0
    for k in range(len(htf)):
        while ei < len(events) and events[ei].index <= k:
            cur = float(events[ei].direction)
            ei += 1
        states[k] = cur
    return states


def _dol_states(htf: Candles, swing_k: int, eq_tol_atr: float,
                min_gap_atr: float, atr_period: int) -> np.ndarray:
    """Draw-on-liquidity imbalance per daily bar, in [-1, +1]."""
    pools = detect_liquidity_pools(htf, detect_swings(htf, swing_k), eq_tol_atr, atr_period)
    fvgs = detect_fvgs(htf, min_gap_atr, atr_period)
    close = htf.close
    states = np.zeros(len(htf))
    for k in range(len(htf)):
        c = close[k]
        score = 0.0
        count = 0
        for p in pools:
            if p.confirm_index > k or (p.taken_index != -1 and p.taken_index <= k):
                continue
            if p.side == BULL and p.level > c:
                score += 1.0
                count += 1
            elif p.side == BEAR and p.level < c:
                score -= 1.0
                count += 1
        for g in fvgs:
            if g.confirm_index > k or (g.fill_index != -1 and g.fill_index <= k):
                continue
            mid = 0.5 * (g.low + g.high)
            if mid > c:
                score += 1.0
                count += 1
            elif mid < c:
                score -= 1.0
                count += 1
        states[k] = score / count if count else 0.0
    return states


def _ipda_states(htf: Candles, windows: tuple[int, ...], hold_days: int) -> np.ndarray:
    """Average of per-window IPDA votes; unavailable windows abstain (0)."""
    if not windows:
        raise ValueError("ipda_windows must not be empty")
    acc = np.zeros(len(htf))
    for w in windows:
        acc += _ipda_single(htf, int(w), hold_days)
    return acc / len(windows)


def _ipda_single(htf: Candles, ipda_days: int, hold_days: int) -> np.ndarray:
    """IPDA range events per daily bar: break/sweep-recovery of the prior
    ``ipda_days`` high/low, each holding for ``hold_days``."""
    h, l, c = htf.high, htf.low, htf.close
    states = np.zeros(len(htf))
    cur, ttl = 0.0, 0
    for k in range(ipda_days, len(htf)):
        range_hi = h[k - ipda_days : k].max()
        range_lo = l[k - ipda_days : k].min()
        event = 0.0
        if c[k] > range_hi:
            event = float(BULL)              # expansion above the data range
        elif c[k] < range_lo:
            event = float(BEAR)              # expansion below
        elif l[k] < range_lo and c[k] > range_lo:
            event = float(BULL)              # low swept, closed back -> reversal up
        elif h[k] > range_hi and c[k] < range_hi:
            event = float(BEAR)              # high swept, closed back -> reversal down
        if event != 0.0:
            cur, ttl = event, hold_days
        elif ttl > 0:
            ttl -= 1
            if ttl == 0:
                cur = 0.0
        states[k] = cur
    return states


class NarrativeEngine:
    """Aggregates narrative factors into a per-base-bar bias array."""

    FACTORS = ("struct_mtf", "struct_htf", "struct_wk", "dol", "ipda")

    def __init__(
        self,
        candles: Candles,
        swing_k: int = 3,
        mtf_multiplier: int = 16,      # 4h from 15m
        htf_multiplier: int = 96,      # daily from 15m
        wk_multiplier: int = 0,        # weekly; 0 = derive from bar duration
        eq_tol_atr: float = 0.25,
        min_gap_atr: float = 0.25,
        atr_period: int = 14,
        ipda_windows: tuple[int, ...] = (20, 40, 60),
        ipda_hold_days: int = 10,
        weights: tuple[float, ...] = (1.0, 1.0, 1.0, 1.0, 1.0),
        min_conviction: float = 0.5,
    ) -> None:
        n = len(candles)
        mtf, mtf_last = resample(candles, mtf_multiplier)
        htf, htf_last = resample(candles, htf_multiplier)
        if wk_multiplier <= 0:
            wk_multiplier = max(int(7 * 86400 // candles.timeframe_s), htf_multiplier * 2)
        wk, wk_last = resample(candles, wk_multiplier)

        self.factors = {
            "struct_mtf": _broadcast(n, mtf_last, _structure_states(mtf, swing_k)),
            "struct_htf": _broadcast(n, htf_last, _structure_states(htf, swing_k)),
            "struct_wk": _broadcast(n, wk_last, _structure_states(wk, swing_k)),
            "dol": _broadcast(n, htf_last, _dol_states(htf, swing_k, eq_tol_atr,
                                                       min_gap_atr, atr_period)),
            "ipda": _broadcast(n, htf_last, _ipda_states(htf, ipda_windows, ipda_hold_days)),
        }
        w = np.asarray(weights, dtype=float)
        if len(w) != len(self.FACTORS) or w.sum() <= 0:
            raise ValueError(
                f"weights must be {len(self.FACTORS)} non-negative numbers "
                "with a positive sum (order: " + ", ".join(self.FACTORS) + ")"
            )
        stacked = np.vstack([self.factors[name] for name in self.FACTORS])
        self.score = (w[:, None] * stacked).sum(axis=0) / w.sum()
        self.bias = np.where(self.score >= min_conviction, BULL,
                             np.where(self.score <= -min_conviction, BEAR, 0))
