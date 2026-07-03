"""Study M2: post-sweep conditional behavior (design frozen in
reports/dev/M1_ADJUDICATION.md before any run on real data).

Two questions about the bars where resting liquidity actually gets taken:

* **Direction** — ICT predicts a sweep (purge-and-close-back) reverses and
  a run continues. Signed forward return per event: positive means the
  prediction was right. Support = block-bootstrap CI of the mean excludes
  0 upward on >= 2/3 datasets.
* **Volatility** — do liquidity-taking events expand realized volatility
  (next 96 bars vs prior 96) beyond ATR/killzone-matched control bars?
  Support = ratio-of-ratios CI excludes 1 upward on >= 2/3 datasets.

Descriptive research on burned data; full-sample computation is
legitimate.
"""

from __future__ import annotations

import numpy as np

from ..core import Candles, atr as compute_atr
from ..detectors import detect_liquidity_pools, detect_swings
from .magnetism import _ratio_block_ci
from .significance import block_bootstrap_ci


def sweep_events(candles: Candles, swing_k: int = 3, eq_tol_atr: float = 0.25,
                 atr_period: int = 14) -> list[dict]:
    """One record per taken pool: when, what kind, and the predicted direction."""
    swings = detect_swings(candles, swing_k)
    pools = detect_liquidity_pools(candles, swings, eq_tol_atr, atr_period)
    events = []
    for p in pools:
        if p.taken_kind is None:
            continue
        # sweep of buy-side liquidity is a bearish signal; a run continues through
        predicted = -p.side if p.taken_kind == "sweep" else p.side
        events.append({"t": int(p.taken_index), "kind": p.taken_kind,
                       "side": int(p.side), "predicted": int(predicted)})
    events.sort(key=lambda e: e["t"])
    return events


def _realized_vol(close: np.ndarray, start: int, end: int) -> float:
    """Std of 1-bar log returns over bars (start, end]."""
    r = np.diff(np.log(close[start : end + 1]))
    return float(r.std(ddof=1)) if len(r) > 1 else float("nan")


def direction_rows(candles: Candles, events: list[dict],
                   horizons: tuple[int, ...] = (96, 384)) -> list[dict]:
    close = candles.close
    n = len(candles)
    rows = []
    for kind in ("sweep", "run"):
        for N in horizons:
            sel = [e for e in events if e["kind"] == kind and 0 < e["t"] < n - N]
            signed = np.array([e["predicted"] * (np.log(close[e["t"] + N])
                                                 - np.log(close[e["t"]])) for e in sel])
            if len(signed) < 5:
                rows.append({"kind": kind, "horizon": N, "n": len(signed),
                             "mean_signed": float("nan"), "ci_lo": float("nan"),
                             "ci_hi": float("nan")})
                continue
            mean, lo, hi, _ = block_bootstrap_ci(signed)
            rows.append({"kind": kind, "horizon": N, "n": len(signed),
                         "mean_signed": mean, "ci_lo": lo, "ci_hi": hi})
    return rows


def vol_rows(candles: Candles, events: list[dict], kz_mask: np.ndarray | None = None,
             window: int = 96, k: int = 20, vol_tol: float = 0.25,
             atr_period: int = 14, seed: int = 42) -> list[dict]:
    close = candles.close
    a = compute_atr(candles, atr_period)
    n = len(candles)
    kz = kz_mask if kz_mask is not None else np.zeros(n, dtype=bool)
    rng = np.random.default_rng(seed)
    idx_all = np.arange(n)
    rows = []
    for kind in ("sweep", "run"):
        sel = [e for e in events if e["kind"] == kind
               and window < e["t"] < n - window]
        ev_exp, ctl_exp = [], []
        for e in sel:
            t = e["t"]
            before = _realized_vol(close, t - window, t)
            after = _realized_vol(close, t, t + window)
            if not (before > 0 and after > 0):
                continue
            eligible = idx_all[(a >= a[t] * (1 - vol_tol)) & (a <= a[t] * (1 + vol_tol))
                               & (kz == kz[t]) & (idx_all > window) & (idx_all < n - window)]
            if len(eligible) == 0:
                continue
            picks = rng.choice(eligible, size=min(k, len(eligible)), replace=False)
            ctl = []
            for j in picks:
                b = _realized_vol(close, j - window, j)
                f = _realized_vol(close, j, j + window)
                if b > 0 and f > 0:
                    ctl.append(f / b)
            if not ctl:
                continue
            ev_exp.append(after / before)
            ctl_exp.append(float(np.mean(ctl)))
        ev_arr, ctl_arr = np.array(ev_exp), np.array(ctl_exp)
        if len(ev_arr) < 5:
            rows.append({"kind": kind, "n": len(ev_arr), "event_expansion": float("nan"),
                         "control_expansion": float("nan"), "ratio": float("nan"),
                         "ci_lo": float("nan"), "ci_hi": float("nan")})
            continue
        ratio, lo, hi = _ratio_block_ci(ev_arr, ctl_arr)
        rows.append({"kind": kind, "n": int(len(ev_arr)),
                     "event_expansion": float(ev_arr.mean()),
                     "control_expansion": float(ctl_arr.mean()),
                     "ratio": ratio, "ci_lo": lo, "ci_hi": hi})
    return rows


def run_sweep_study(candles: Candles, kz_mask: np.ndarray | None = None,
                    swing_k: int = 3, eq_tol_atr: float = 0.25,
                    atr_period: int = 14, seed: int = 42) -> dict:
    events = sweep_events(candles, swing_k, eq_tol_atr, atr_period)
    return {
        "n_events": len(events),
        "direction": direction_rows(candles, events),
        "vol": vol_rows(candles, events, kz_mask, atr_period=atr_period, seed=seed),
    }


def render_sweep_tables(result: dict, title: str) -> str:
    lines = [f"**{title}** — post-liquidity-take behavior ({result['n_events']} events)", "",
             "*Direction (signed toward ICT prediction; support = CI > 0)*", "",
             "| kind | horizon | n | mean signed logret | 95% CI |", "|---|---|---|---|---|"]
    for r in result["direction"]:
        lines.append(f"| {r['kind']} | {r['horizon']} | {r['n']} | "
                     f"{r['mean_signed']:+.5f} | [{r['ci_lo']:+.5f}, {r['ci_hi']:+.5f}] |")
    lines += ["", "*Volatility expansion (next 96 / prior 96, vs matched controls; support = CI > 1)*",
              "", "| kind | n | event | control | ratio | 95% CI |", "|---|---|---|---|---|---|"]
    for r in result["vol"]:
        lines.append(f"| {r['kind']} | {r['n']} | {r['event_expansion']:.3f} | "
                     f"{r['control_expansion']:.3f} | {r['ratio']:.3f} | "
                     f"[{r['ci_lo']:.3f}, {r['ci_hi']:.3f}] |")
    return "\n".join(lines)
