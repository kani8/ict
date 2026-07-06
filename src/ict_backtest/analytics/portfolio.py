"""Portfolio aggregation of per-instrument backtests (Program T, Stage 2).

The engine runs one instrument at a time; a diversified program is the
equal-weight daily-rebalanced average of the per-instrument return
streams.  Each instrument's daily return comes from its own equity
curve (net of that run's costs); days on which an instrument has no bar
contribute 0 for it (flat through single-market holidays).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..engine import BacktestResult
from .significance import block_bootstrap_ci


def daily_returns(result: BacktestResult) -> pd.Series:
    """Per-bar simple returns of the equity curve, indexed by UTC day."""
    eq = result.equity_curve
    prev = np.concatenate(([result.initial_equity], eq[:-1]))
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(prev > 0, eq / prev - 1.0, 0.0)
    day = (result.candles.ts // 86400).astype(np.int64)
    return pd.Series(r, index=day)


def combine_portfolio(results: dict[str, BacktestResult],
                      periods_per_year: int = 252) -> dict:
    """Equal-weight portfolio metrics across instruments.

    Returns a dict with the compounded portfolio metrics plus a
    block-bootstrap CI on the mean daily portfolio return, and the
    per-instrument net metrics for side-by-side reading.
    """
    frames = {name: daily_returns(res) for name, res in results.items()}
    joined = pd.DataFrame(frames).fillna(0.0).sort_index()
    port = joined.mean(axis=1).to_numpy()

    curve = np.cumprod(1.0 + port)
    peak = np.maximum.accumulate(curve)
    max_dd = float((curve / peak - 1.0).min()) if len(curve) else 0.0
    n_years = len(port) / periods_per_year if len(port) else 0.0
    cagr = float(curve[-1] ** (1 / n_years) - 1.0) if n_years > 0 and curve[-1] > 0 else 0.0
    vol = float(np.std(port, ddof=1) * np.sqrt(periods_per_year)) if len(port) > 1 else 0.0
    ann = float(np.mean(port) * periods_per_year) if len(port) else 0.0
    sharpe = ann / vol if vol > 0 else float("nan")
    mean, lo, hi, block = block_bootstrap_ci(port) if len(port) >= 30 else (0.0, 0.0, 0.0, 0)

    per_instrument = {
        name: {
            "total_return": res.total_return,
            "n_trades": len(res.trades),
            "n_days": int(len(frames[name])),
        }
        for name, res in results.items()
    }
    return {
        "n_days": int(len(port)),
        "n_instruments": len(results),
        "cagr": cagr,
        "ann_return": ann,
        "ann_vol": vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "mean_daily": mean,
        "ci_lo": lo,
        "ci_hi": hi,
        "block_len": block,
        "per_instrument": per_instrument,
    }


def render_portfolio(stats: dict, title: str) -> str:
    lines = [f"**{title}** — equal-weight portfolio "
             f"({stats['n_instruments']} instruments, {stats['n_days']} days)", "",
             "| metric | value |", "|---|---|",
             f"| CAGR | {stats['cagr'] * 100:+.2f}% |",
             f"| ann. return (arith.) | {stats['ann_return'] * 100:+.2f}% |",
             f"| ann. vol | {stats['ann_vol'] * 100:.2f}% |",
             f"| Sharpe | {stats['sharpe']:.2f} |",
             f"| max drawdown | {stats['max_drawdown'] * 100:.2f}% |",
             f"| mean daily ret | {stats['mean_daily']:+.6f} "
             f"[{stats['ci_lo']:+.6f}, {stats['ci_hi']:+.6f}] (block={stats['block_len']}) |",
             "", "| instrument | net total return | trades | days |", "|---|---|---|---|"]
    for name, m in stats["per_instrument"].items():
        lines.append(f"| {name} | {m['total_return'] * 100:+.2f}% | "
                     f"{m['n_trades']} | {m['n_days']} |")
    return "\n".join(lines)
