"""Study M1: liquidity magnetism — does price seek resting liquidity?

Event study per reports/PREREGISTRATION_M.md. For every confirmed
liquidity pool we ask: was the level reached within N bars? The control
asks: how often does an equal-sized move in the same direction happen
from ATR-matched random bars, unconditionally? The ratio of the two is
the "magnetism" of liquidity. Ratios reliably above 1 support the ICT
claim; ratios near 1 mean pools are just levels like any other.

This is descriptive research on burned data — full-sample computation is
legitimate here; there is no trading decision to protect from lookahead.
"""

from __future__ import annotations

import numpy as np

from ..core import BULL, Candles, atr as compute_atr
from ..detectors import detect_liquidity_pools, detect_swings

DIST_BUCKETS = ((0.5, 1.0), (1.0, 2.0), (2.0, 4.0))
HORIZONS = (96, 384)


def pool_touch_events(candles: Candles, swing_k: int = 3, eq_tol_atr: float = 0.25,
                      atr_period: int = 14) -> list[dict]:
    """One record per confirmed pool: distance (ATR units) and touch times."""
    a = compute_atr(candles, atr_period)
    swings = detect_swings(candles, swing_k)
    pools = detect_liquidity_pools(candles, swings, eq_tol_atr, atr_period)
    close = candles.close
    n = len(candles)
    events = []
    for p in pools:
        c = p.confirm_index
        if c >= n - 1 or a[c] <= 0:
            continue
        dist = (p.level - close[c]) if p.side == BULL else (close[c] - p.level)
        if dist <= 0:
            continue  # level already beyond price at confirmation; not a draw
        events.append({
            "confirm": int(c),
            "side": int(p.side),
            "d_atr": float(dist / a[c]),
            "taken": int(p.taken_index),
        })
    events.sort(key=lambda e: e["confirm"])
    return events


def baseline_move_rate(candles: Candles, event: dict, horizon: int,
                       atr_arr: np.ndarray, rng: np.random.Generator,
                       k: int = 20, vol_tol: float = 0.25) -> float:
    """P(equal-sized same-direction move within `horizon`) at ATR-matched bars."""
    n = len(candles)
    c = event["confirm"]
    ref_atr = atr_arr[c]
    lo, hi = ref_atr * (1 - vol_tol), ref_atr * (1 + vol_tol)
    eligible = np.flatnonzero((atr_arr >= lo) & (atr_arr <= hi)
                              & (np.arange(n) < n - horizon))
    if len(eligible) == 0:
        return float("nan")
    picks = rng.choice(eligible, size=min(k, len(eligible)), replace=False)
    hits = 0
    for j in picks:
        d = event["d_atr"] * atr_arr[j]
        if event["side"] == BULL:
            hits += bool(candles.high[j + 1 : j + 1 + horizon].max() >= candles.close[j] + d)
        else:
            hits += bool(candles.low[j + 1 : j + 1 + horizon].min() <= candles.close[j] - d)
    return hits / len(picks)


def _ratio_block_ci(touch: np.ndarray, base: np.ndarray,
                    n_boot: int = 4000, seed: int = 7) -> tuple[float, float, float]:
    """Block-bootstrap CI for mean(touch)/mean(base) over time-ordered events."""
    n = len(touch)
    b = max(1, round(n ** (1 / 3)))
    rng = np.random.default_rng(seed)
    point = float(touch.mean() / base.mean()) if base.mean() > 0 else float("nan")
    if n < 2:
        return point, float("nan"), float("nan")
    kblocks = -(-n // b)
    starts = rng.integers(0, n, size=(n_boot, kblocks))
    idx = (starts[:, :, None] + np.arange(b)) % n
    idx = idx.reshape(n_boot, kblocks * b)[:, :n]
    t = touch[idx].mean(axis=1)
    m = base[idx].mean(axis=1)
    ratios = np.where(m > 0, t / m, np.nan)
    lo, hi = np.nanquantile(ratios, [0.025, 0.975])
    return point, float(lo), float(hi)


def run_magnetism(candles: Candles, swing_k: int = 3, eq_tol_atr: float = 0.25,
                  atr_period: int = 14, horizons: tuple[int, ...] = HORIZONS,
                  buckets: tuple[tuple[float, float], ...] = DIST_BUCKETS,
                  baseline_k: int = 20, seed: int = 42) -> list[dict]:
    """The full M1 table: one row per (bucket, horizon)."""
    a = compute_atr(candles, atr_period)
    events = pool_touch_events(candles, swing_k, eq_tol_atr, atr_period)
    rng = np.random.default_rng(seed)
    rows = []
    for blo, bhi in buckets:
        bucket_events = [e for e in events if blo <= e["d_atr"] < bhi]
        for N in horizons:
            usable = [e for e in bucket_events if e["confirm"] < len(candles) - N]
            if not usable:
                rows.append({"bucket": f"{blo}-{bhi}", "horizon": N, "n": 0,
                             "touch_rate": float("nan"), "baseline_rate": float("nan"),
                             "ratio": float("nan"), "ci_lo": float("nan"),
                             "ci_hi": float("nan")})
                continue
            touch = np.array([1.0 if (e["taken"] != -1 and e["taken"] <= e["confirm"] + N)
                              else 0.0 for e in usable])
            base = np.array([baseline_move_rate(candles, e, N, a, rng, k=baseline_k)
                             for e in usable])
            ok = ~np.isnan(base)
            touch, base = touch[ok], base[ok]
            ratio, lo, hi = _ratio_block_ci(touch, base)
            rows.append({"bucket": f"{blo}-{bhi}", "horizon": N, "n": int(len(touch)),
                         "touch_rate": float(touch.mean()) if len(touch) else float("nan"),
                         "baseline_rate": float(base.mean()) if len(base) else float("nan"),
                         "ratio": ratio, "ci_lo": lo, "ci_hi": hi})
    return rows


def render_magnetism_table(rows: list[dict], title: str) -> str:
    lines = [f"**{title}** — pool touch rate vs ATR-matched unconditional move rate", "",
             "| distance (ATR) | horizon | n | touch | baseline | ratio | 95% CI |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['bucket']} | {r['horizon']} | {r['n']} | {r['touch_rate']:.3f} | "
            f"{r['baseline_rate']:.3f} | {r['ratio']:.2f} | "
            f"[{r['ci_lo']:.2f}, {r['ci_hi']:.2f}] |")
    return "\n".join(lines)
