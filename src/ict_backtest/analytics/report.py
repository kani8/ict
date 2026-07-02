"""Markdown report rendering."""

from __future__ import annotations

import math

import numpy as np

from ..engine import BacktestResult
from .metrics import Metrics
from .significance import BaselineTest, block_bootstrap_ci


def _fmt(v: float, nd: int = 2) -> str:
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return "—"
    return f"{v:,.{nd}f}"


def render_report(
    result: BacktestResult,
    metrics: Metrics,
    baseline: BaselineTest | None = None,
    title: str = "SMC Backtest Report",
) -> str:
    lines = [f"# {title}", ""]
    n_bars = len(result.candles)
    lines += [
        f"- Bars: **{n_bars:,}** ({result.candles.timeframe_s // 60}m timeframe)",
        f"- Initial equity: **{_fmt(result.initial_equity, 0)}**  →  Final: **{_fmt(result.final_equity, 0)}**",
        "",
        "## Performance",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Trades | {metrics.n_trades} |",
        f"| Win rate | {_fmt(metrics.win_rate * 100, 1)}% |",
        f"| Profit factor | {_fmt(metrics.profit_factor)} |",
        f"| Avg R multiple | {_fmt(metrics.avg_r)} |",
        f"| Total return | {_fmt(metrics.total_return_pct)}% |",
        f"| CAGR | {_fmt(metrics.cagr_pct)}% |",
        f"| Sharpe | {_fmt(metrics.sharpe)} |",
        f"| Sortino | {_fmt(metrics.sortino)} |",
        f"| Max drawdown | {_fmt(metrics.max_drawdown_pct)}% |",
        f"| Exposure | {_fmt(metrics.exposure_pct, 1)}% |",
        f"| Avg / median holding (bars) | {_fmt(metrics.avg_holding_bars, 1)} / {_fmt(metrics.median_holding_bars, 1)} |",
    ]

    rs = np.array([t.r_multiple for t in result.trades if not math.isnan(t.r_multiple)])
    if 0 < len(rs) < 5:
        lines += [
            "",
            "## Statistical validity",
            "",
            f"- Only {len(rs)} trade(s) — too few for confidence intervals or null "
            "tests. This result is **underpowered, not evidence** in either direction.",
        ]
    if len(rs) >= 5:
        mean, lo, hi, blen = block_bootstrap_ci(rs)
        verdict = "edge inconsistent with zero" if lo > 0 else "**cannot reject zero edge**" if hi > 0 else "negative edge"
        lines += [
            "",
            "## Statistical validity",
            "",
            f"- Mean trade R: **{_fmt(mean)}**, 95% block-bootstrap CI **[{_fmt(lo)}, {_fmt(hi)}]** "
            f"(block length {blen}, preserves trade clustering) — {verdict}.",
        ]
    if baseline is not None and baseline.n_sims == 0 and baseline.note:
        lines += [f"- Null test: {baseline.note}."]
    if baseline is not None and baseline.n_sims > 0:
        sig = "significant at 5%" if baseline.significant_5pct else "**not significant at 5%**"
        if baseline.kind == "matched":
            null_desc = (f"Trade-template null ({baseline.n_sims} sims: entry timing randomized; "
                         "side, fractional stop/target geometry, risk sizing, and trade count "
                         "retained; execution type and realized exposure may differ — see diagnostics)")
        else:
            null_desc = (f"Drift-control null ({baseline.n_sims} sims, random entries at matched "
                         "frequency; NOT exposure/risk matched — descriptive only)")
        lines += [
            f"- {null_desc}: "
            f"null mean return {_fmt(baseline.baseline_mean_return * 100)}% ± {_fmt(baseline.baseline_std_return * 100)}%, "
            f"strategy {_fmt(baseline.strategy_total_return * 100)}%, p = {_fmt(baseline.p_value, 3)} ({sig}).",
        ]
        if not math.isnan(baseline.p_value_mean_r):
            sig_r = "significant at 5%" if baseline.p_value_mean_r < 0.05 else "**not significant at 5%**"
            lines += [
                f"- Same null, mean trade R statistic (risk-normalized, robust to the exposure "
                f"mismatch): p = {_fmt(baseline.p_value_mean_r, 3)} ({sig_r}).",
            ]
        d = baseline.diagnostics
        if d:
            lines += [
                f"- Null matching diagnostics: trades {d['strategy_trades']} vs {_fmt(d['null_mean_trades'], 1)} (null mean); "
                f"exposure {_fmt(d['strategy_exposure_pct'])}% vs {_fmt(d['null_mean_exposure_pct'])}%; "
                f"mean holding {_fmt(d['strategy_mean_holding_bars'], 1)} vs {_fmt(d['null_mean_holding_bars'], 1)} bars.",
            ]

    if result.trades:
        lines += ["", "## Last trades", "", "| # | Side | Entry bar | Exit bar | R | PnL | Reason |", "|---|---|---|---|---|---|---|"]
        for k, t in enumerate(result.trades[-15:], 1):
            side = "long" if t.side == 1 else "short"
            lines.append(
                f"| {k} | {side} | {t.entry_index} | {t.exit_index} | {_fmt(t.r_multiple)} | {_fmt(t.pnl)} | {t.reason} |"
            )
    lines.append("")
    return "\n".join(lines)
