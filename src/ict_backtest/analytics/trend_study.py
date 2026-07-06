"""Program T, Stage 1: time-series momentum diagnostics on daily bars.

Design frozen in ``reports/PREREGISTRATION_T.md`` before any run on real
data.  For each instrument, per-day gross strategy returns

    x[t] = signal[t] * scale[t] * r[t+1]

where ``signal[t]`` is the sign of the trailing L-day log return (or the
majority vote across lookbacks), ``scale[t]`` is 1 (raw) or the
volatility-targeting leverage min(target/realized, cap), and ``r[t+1]``
is the next day's close-to-close log return.  Every input to day t's
signal is knowable at day t's close.

Statistics per variant: block-bootstrap CI of mean(x), plus a
**circular signal-shift null**: the same statistic recomputed with the
signal series rotated by a random offset ≥ ``min_shift`` days.  The
shift preserves both the price path and the signal's autocorrelation
while destroying their alignment — the cleanest "is the timing real?"
control for an always-in-the-market strategy.

The portfolio row inner-joins instruments on date and averages their
per-day x (equal weight): diversification is the claim under test as
much as the signal, so the portfolio is the primary object.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..core import Candles
from .significance import block_bootstrap_ci

DEFAULT_LOOKBACKS = (21, 63, 252)


def trend_signals(close: np.ndarray, lookbacks: tuple[int, ...] = DEFAULT_LOOKBACKS,
                  ) -> dict[str, np.ndarray]:
    """Per-day trend signals in {-1, 0, +1}; value at t uses closes <= t.

    Keys: one per lookback (``"252"`` etc.) plus ``"vote"`` (sign of the
    sum of the individual signs).  The first max(lookback) days are 0.
    """
    n = len(close)
    logc = np.log(close)
    out: dict[str, np.ndarray] = {}
    total = np.zeros(n)
    for lb in lookbacks:
        sig = np.zeros(n)
        if n > lb:
            sig[lb:] = np.sign(logc[lb:] - logc[:-lb])
        out[str(lb)] = sig
        total += sig
    vote = np.sign(total)
    vote[: max(lookbacks)] = 0.0  # no vote until every lookback is live
    out["vote"] = vote
    return out


def vol_scale(close: np.ndarray, vol_lookback: int = 63, vol_target: float = 0.10,
              cap: float = 4.0, periods_per_year: int = 252) -> np.ndarray:
    """Volatility-targeting leverage per day; value at t uses closes <= t."""
    r = pd.Series(np.diff(np.log(close), prepend=np.log(close[0])))
    realized = r.rolling(vol_lookback).std().to_numpy() * np.sqrt(periods_per_year)
    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(realized > 0, vol_target / realized, 0.0)
    scale[np.isnan(scale)] = 0.0
    return np.minimum(scale, cap)


def shift_null_p(sig_scaled: np.ndarray, r_next: np.ndarray, n_shifts: int = 500,
                 min_shift: int = 260, seed: int = 42) -> float:
    """P(mean of randomly rotated signal >= observed mean)."""
    n = len(sig_scaled)
    if n <= 2 * min_shift:
        return float("nan")
    observed = float(np.nanmean(sig_scaled * r_next))
    rng = np.random.default_rng(seed)
    offsets = rng.integers(min_shift, n - min_shift, size=n_shifts)
    nulls = np.array([np.nanmean(np.roll(sig_scaled, int(k)) * r_next) for k in offsets])
    return float((1 + np.sum(nulls >= observed)) / (n_shifts + 1))


def _daily_x(candles: Candles, variant: str, lookbacks: tuple[int, ...],
             vol_lookback: int, vol_target: float, cap: float,
             scaled: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(ts_of_day_t, sig_scaled[t], r_next[t]) for days with a live signal."""
    close = candles.close
    sig = trend_signals(close, lookbacks)[variant]
    scale = vol_scale(close, vol_lookback, vol_target, cap) if scaled else np.ones(len(close))
    r_next = np.empty(len(close))
    r_next[:-1] = np.diff(np.log(close))
    r_next[-1] = np.nan
    live = (sig != 0) & (scale > 0) & ~np.isnan(r_next)
    return candles.ts[live], (sig * scale)[live], r_next[live]


def tsmom_rows(candles: Candles, lookbacks: tuple[int, ...] = DEFAULT_LOOKBACKS,
               vol_lookback: int = 63, vol_target: float = 0.10, cap: float = 4.0,
               n_shifts: int = 500, seed: int = 42) -> list[dict]:
    """One row per (variant, scaling): mean daily gross x, CI, shift-null p."""
    rows = []
    for variant in [str(lb) for lb in lookbacks] + ["vote"]:
        for scaled in (False, True):
            _, s, r = _daily_x(candles, variant, lookbacks, vol_lookback,
                               vol_target, cap, scaled)
            x = s * r
            if len(x) < 30:
                rows.append({"variant": variant, "scaled": scaled, "n": int(len(x)),
                             "mean": float("nan"), "ci_lo": float("nan"),
                             "ci_hi": float("nan"), "p_shift": float("nan")})
                continue
            mean, lo, hi, _ = block_bootstrap_ci(x)
            rows.append({"variant": variant, "scaled": scaled, "n": int(len(x)),
                         "mean": mean, "ci_lo": lo, "ci_hi": hi,
                         "p_shift": shift_null_p(s, r, n_shifts, seed=seed)})
    return rows


def portfolio_rows(instruments: dict[str, Candles],
                   lookbacks: tuple[int, ...] = DEFAULT_LOOKBACKS,
                   vol_lookback: int = 63, vol_target: float = 0.10, cap: float = 4.0,
                   n_shifts: int = 500, seed: int = 42,
                   variant: str = "vote", scaled: bool = True) -> list[dict]:
    """Equal-weight portfolio of per-day x across instruments (primary object).

    Days are inner-joined on the trading date (UTC calendar day of the
    daily bar); an instrument missing a date contributes 0 that day
    (flat), matching how a portfolio holds through single-market
    holidays.  Returns one portfolio row plus one row per instrument
    (same variant/scaling) for side-by-side reading.
    """
    frames = []
    per_inst_rows = []
    for name, candles in instruments.items():
        ts, s, r = _daily_x(candles, variant, lookbacks, vol_lookback,
                            vol_target, cap, scaled)
        x = s * r
        day = (ts // 86400).astype(np.int64)
        frames.append(pd.Series(x, index=day, name=name))
        if len(x) >= 30:
            mean, lo, hi, _ = block_bootstrap_ci(x)
            per_inst_rows.append({"name": name, "n": int(len(x)), "mean": mean,
                                  "ci_lo": lo, "ci_hi": hi,
                                  "p_shift": shift_null_p(s, r, n_shifts, seed=seed)})
        else:
            per_inst_rows.append({"name": name, "n": int(len(x)), "mean": float("nan"),
                                  "ci_lo": float("nan"), "ci_hi": float("nan"),
                                  "p_shift": float("nan")})
    joined = pd.concat(frames, axis=1).fillna(0.0)
    port = joined.mean(axis=1).to_numpy()
    if len(port) >= 30:
        mean, lo, hi, _ = block_bootstrap_ci(port)
        ann = float(np.mean(port) * 252)
        vol = float(np.std(port, ddof=1) * np.sqrt(252))
        sharpe = ann / vol if vol > 0 else float("nan")
        row = {"name": "PORTFOLIO", "n": int(len(port)), "mean": mean,
               "ci_lo": lo, "ci_hi": hi, "p_shift": float("nan"),
               "ann_return": ann, "ann_vol": vol, "sharpe": sharpe}
    else:
        row = {"name": "PORTFOLIO", "n": int(len(port)), "mean": float("nan"),
               "ci_lo": float("nan"), "ci_hi": float("nan"), "p_shift": float("nan")}
    return [row] + per_inst_rows


def render_trend_battery(per_instrument: dict[str, list[dict]],
                         portfolio: list[dict], title: str) -> str:
    lines = [f"**{title}** — TSMOM battery (gross, pre-cost)", "",
             "*Portfolio (primary: vote + vol-scaled; support = CI > 0)*", "",
             "| name | n | mean daily x | 95% CI | p_shift | ann ret | ann vol | Sharpe |",
             "|---|---|---|---|---|---|---|---|"]
    for r in portfolio:
        extra = (f" {r.get('ann_return', float('nan')):+.4f} | "
                 f"{r.get('ann_vol', float('nan')):.4f} | "
                 f"{r.get('sharpe', float('nan')):.2f} |"
                 if "sharpe" in r else " | | |")
        lines.append(f"| {r['name']} | {r['n']} | {r['mean']:+.6f} | "
                     f"[{r['ci_lo']:+.6f}, {r['ci_hi']:+.6f}] | {r['p_shift']:.3f} |"
                     + extra)
    for name, rows in per_instrument.items():
        lines += ["", f"*{name} — per-variant (exploratory)*", "",
                  "| variant | scaled | n | mean daily x | 95% CI | p_shift |",
                  "|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['variant']} | {r['scaled']} | {r['n']} | "
                         f"{r['mean']:+.6f} | [{r['ci_lo']:+.6f}, {r['ci_hi']:+.6f}] | "
                         f"{r['p_shift']:.3f} |")
    return "\n".join(lines)
