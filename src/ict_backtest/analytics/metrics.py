"""Performance metrics computed from a BacktestResult."""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np

from ..engine import BacktestResult

SECONDS_PER_YEAR = 365.25 * 24 * 3600  # 24/7 markets; equities users can rescale


@dataclass(slots=True)
class Metrics:
    n_trades: int
    win_rate: float
    profit_factor: float
    avg_r: float
    expectancy_pct: float        # mean pnl per trade / initial equity, in %
    total_return_pct: float
    cagr_pct: float
    sharpe: float
    sortino: float
    max_drawdown_pct: float
    exposure_pct: float          # fraction of bars in a position
    avg_holding_bars: float
    median_holding_bars: float
    avg_win: float
    avg_loss: float

    def to_dict(self) -> dict:
        return asdict(self)


def compute_metrics(result: BacktestResult, bars_per_year: float | None = None) -> Metrics:
    """Compute performance metrics.

    ``bars_per_year`` defaults to wall-clock (24/7) bars, correct for crypto.
    For session-bound markets pass the actual figure — e.g. RTH 15m US
    equities: 26 bars/day x 252 days = 6552 — or Sharpe/Sortino/CAGR will be
    annualized against hours the market never traded.
    """
    trades = result.trades
    eq = result.equity_curve
    n_bars = len(eq)
    if bars_per_year is None:
        bars_per_year = SECONDS_PER_YEAR / result.candles.timeframe_s

    rets = np.diff(eq) / eq[:-1] if n_bars > 1 else np.array([0.0])
    std = rets.std(ddof=1) if len(rets) > 1 else 0.0
    sharpe = float(rets.mean() / std * math.sqrt(bars_per_year)) if std > 0 else 0.0
    downside = rets[rets < 0]
    dstd = downside.std(ddof=1) if len(downside) > 1 else 0.0
    sortino = float(rets.mean() / dstd * math.sqrt(bars_per_year)) if dstd > 0 else 0.0

    peak = np.maximum.accumulate(eq)
    max_dd = float(((eq - peak) / peak).min()) if n_bars else 0.0

    years = n_bars / bars_per_year if bars_per_year > 0 else 0.0
    final_ratio = eq[-1] / result.initial_equity if n_bars else 1.0
    cagr = (final_ratio ** (1 / years) - 1.0) if years > 0 and final_ratio > 0 else 0.0

    pnls = np.array([t.pnl for t in trades]) if trades else np.array([])
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    gross_win = wins.sum() if len(wins) else 0.0
    gross_loss = -losses.sum() if len(losses) else 0.0
    rs = np.array([t.r_multiple for t in trades if not math.isnan(t.r_multiple)])
    holds = np.array([t.holding_bars for t in trades]) if trades else np.array([0])

    return Metrics(
        n_trades=len(trades),
        win_rate=float(len(wins) / len(pnls)) if len(pnls) else 0.0,
        profit_factor=float(gross_win / gross_loss) if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0,
        avg_r=float(rs.mean()) if len(rs) else 0.0,
        expectancy_pct=float(pnls.mean() / result.initial_equity * 100) if len(pnls) else 0.0,
        total_return_pct=result.total_return * 100,
        cagr_pct=cagr * 100,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown_pct=max_dd * 100,
        exposure_pct=float(holds.sum() / n_bars * 100) if n_bars else 0.0,
        avg_holding_bars=float(holds.mean()) if len(holds) else 0.0,
        median_holding_bars=float(np.median(holds)) if len(holds) else 0.0,
        avg_win=float(wins.mean()) if len(wins) else 0.0,
        avg_loss=float(losses.mean()) if len(losses) else 0.0,
    )
