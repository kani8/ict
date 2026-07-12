from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from ict_backtest.analytics import compute_metrics
from ict_backtest.analytics.significance import block_bootstrap_ci
from ict_backtest.data import load_candles
from ict_backtest.engine import Backtester, CostModel
from ict_backtest.strategy import CATConfig, CATStrategy


OUT = Path("reports/dev/_cat_es_driver.json")


def fmt(v: float, nd: int = 2) -> str:
    if math.isinf(v) or math.isnan(v):
        return "—"
    return f"{v:,.{nd}f}"


def leg_summary(trades) -> dict:
    rs = np.array([t.r_multiple for t in trades if not math.isnan(t.r_multiple)])
    wins = sum(1 for t in trades if t.pnl > 0)
    return {
        "n": int(len(trades)),
        "mean_r": float(rs.mean()) if len(rs) else 0.0,
        "win_rate": float(wins / len(trades)) if trades else 0.0,
    }


def main() -> None:
    candles = load_candles("data/es_15m.parquet")
    intrabar = load_candles("data/es_1m.parquet")
    config = CATConfig.from_toml("configs/cat_es.toml")
    cost = CostModel(spread_bps=0.4, commission_bps=0.1, slippage_bps=0.4)
    backtester = Backtester(cost=cost, initial_equity=100_000.0,
                            intrabar_policy="conservative", intrabar=intrabar)
    strategy = CATStrategy(candles, config)
    result = backtester.run(candles, strategy)
    metrics = compute_metrics(result, bars_per_year=23447.4)
    rs = np.array([t.r_multiple for t in result.trades if not math.isnan(t.r_multiple)])
    mean_r, ci_lo, ci_hi, block_len = block_bootstrap_ci(rs)

    by_tag = {}
    for tag in sorted({t.tag for t in result.trades}):
        by_tag[tag] = leg_summary([t for t in result.trades if t.tag == tag])

    reasons = Counter(t.reason for t in result.trades)
    headline = {
        "bars": int(len(candles)),
        "trades": int(metrics.n_trades),
        "final_equity": float(result.final_equity),
        "total_return_pct": float(metrics.total_return_pct),
        "profit_factor": float(metrics.profit_factor),
        "mean_r": float(metrics.avg_r),
        "mean_r_bootstrap": float(mean_r),
        "ci_lo": float(ci_lo),
        "ci_hi": float(ci_hi),
        "block_len": int(block_len),
        "max_drawdown_pct": float(metrics.max_drawdown_pct),
        "exposure_pct": float(metrics.exposure_pct),
        "win_rate": float(metrics.win_rate),
        "sharpe": float(metrics.sharpe),
        "sortino": float(metrics.sortino),
        "avg_holding_bars": float(metrics.avg_holding_bars),
        "median_holding_bars": float(metrics.median_holding_bars),
    }

    rounded_cli_match = {
        "trades": headline["trades"] == 47387,
        "win_rate": fmt(headline["win_rate"] * 100, 1) == "46.5",
        "profit_factor": fmt(headline["profit_factor"]) == "0.62",
        "mean_r": fmt(headline["mean_r"]) == "-0.34",
        "total_return_pct": fmt(headline["total_return_pct"]) == "-100.00",
        "max_drawdown_pct": fmt(headline["max_drawdown_pct"]) == "-100.00",
        "exposure_pct": fmt(headline["exposure_pct"], 1) == "6.6",
    }
    if not all(rounded_cli_match.values()):
        raise AssertionError(rounded_cli_match)

    output = {
        "invocation": (
            "Python API equivalent of: uv run ict-backtest run --strategy cat "
            "--data data/es_15m.parquet --intrabar-data data/es_1m.parquet "
            "--config configs/cat_es.toml --spread-bps 0.4 --commission-bps 0.1 "
            "--slippage-bps 0.4 --bars-per-year 23447.4 --validate 500 "
            "--report reports/dev/CAT_ES_RUN.md"
        ),
        "headline": headline,
        "rounded_cli_match": rounded_cli_match,
        "per_leg": by_tag,
        "skip_counts": strategy.skip_counts,
        "exit_reasons": dict(reasons),
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
