"""Statistical validity checks.

A profitable backtest is not evidence of edge by itself.  Two checks:

* ``bootstrap_ci`` — resample the realized per-trade R-multiples to get a
  confidence interval on the mean.  If the interval straddles zero, the
  sample is consistent with no edge.
* ``random_baseline_test`` — Monte Carlo null model: many random-entry
  strategies matched on trade frequency, holding period, direction mix,
  and time-of-day universe.  The p-value is the fraction of null runs
  that did at least as well as the strategy.  This controls for market
  drift (a long-only strategy in a bull market beats zero but not the
  null).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core import BULL, Candles
from ..engine import BacktestResult, Backtester
from ..strategy.baselines import RandomStrategy


def bootstrap_ci(
    values: np.ndarray | list[float],
    n_boot: int = 10_000,
    alpha: float = 0.05,
    seed: int = 7,
) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high) for the mean of ``values``."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(n_boot, len(v)))
    means = v[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(v.mean()), float(lo), float(hi)


@dataclass(slots=True)
class BaselineTest:
    strategy_total_return: float
    baseline_mean_return: float
    baseline_std_return: float
    p_value: float          # P(random >= strategy) under the null
    n_sims: int

    @property
    def significant_5pct(self) -> bool:
        return self.p_value < 0.05


def random_baseline_test(
    candles: Candles,
    result: BacktestResult,
    backtester: Backtester,
    eligible_mask: np.ndarray | None = None,
    n_sims: int = 200,
    seed: int = 42,
) -> BaselineTest:
    trades = result.trades
    if not trades:
        return BaselineTest(0.0, 0.0, 0.0, 1.0, 0)

    n_bars = len(candles)
    mask = eligible_mask if eligible_mask is not None else np.ones(n_bars, bool)
    holding = int(np.median([max(t.holding_bars, 1) for t in trades]))
    long_share = float(np.mean([t.side == BULL for t in trades]))
    # approximate frequency matching: eligible bars not absorbed by holding
    eligible = max(int(mask.sum()) - len(trades) * holding, 1)
    entry_prob = min(1.0, len(trades) / eligible)

    returns = np.empty(n_sims)
    for k in range(n_sims):
        base = RandomStrategy(
            candles,
            entry_prob=entry_prob,
            holding_bars=holding,
            seed=seed + k,
            eligible_mask=mask,
            long_prob=long_share,
        )
        res = backtester.run(candles, base)
        returns[k] = res.total_return

    strat = result.total_return
    p = float((1 + np.sum(returns >= strat)) / (n_sims + 1))
    return BaselineTest(
        strategy_total_return=strat,
        baseline_mean_return=float(returns.mean()),
        baseline_std_return=float(returns.std(ddof=1)) if n_sims > 1 else 0.0,
        p_value=p,
        n_sims=n_sims,
    )
