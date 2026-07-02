"""Statistical validity checks.

A profitable backtest is not evidence of edge by itself.  Checks provided:

* ``bootstrap_ci`` — IID bootstrap CI for the mean of per-trade R.  Fast
  first look; understates uncertainty when trades cluster in regimes.
* ``block_bootstrap_ci`` — circular moving-block bootstrap that preserves
  the serial dependence between neighboring trades.  Prefer this one.
* ``matched_baseline_test`` — the primary null: the strategy's own trades
  (side, stop/target geometry, risk sizing) replayed at random times in
  the same eligible-time universe.  Precise estimand: the probability
  that randomly *timed* replays of the same trade templates — executed as
  market entries, so execution type and realized exposure/holding may
  differ from the original limit fills — do at least as well as the
  strategy.  It is a randomized trade-template test, not a strict
  exposure-matched control; the matching diagnostics quantify the gap so
  the p-value can be read accordingly.  Mean per-trade R is reported as a
  second test statistic because it is risk-normalized and much less
  sensitive to the exposure mismatch than total return.
* ``random_baseline_test`` — a simpler drift-only control (random entries,
  fixed median holding, notional sizing).  NOT exposure/risk matched;
  treat its p-value as descriptive.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..core import BULL, Candles
from ..engine import BacktestResult, Backtester
from ..strategy.baselines import MatchedRandomStrategy, RandomStrategy


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


def block_bootstrap_ci(
    values: np.ndarray | list[float],
    n_boot: int = 10_000,
    alpha: float = 0.05,
    block_len: int | None = None,
    seed: int = 7,
) -> tuple[float, float, float, int]:
    """Circular moving-block bootstrap CI for the mean.

    Keeps blocks of consecutive trades together, preserving the regime
    clustering that an IID bootstrap destroys.  ``block_len`` defaults to
    the n^(1/3) rule of thumb.  Returns (mean, ci_low, ci_high, block_len).
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    if n == 0:
        return 0.0, 0.0, 0.0, 0
    b = block_len if block_len is not None else max(1, round(n ** (1 / 3)))
    b = min(b, n)
    if n == 1 or b >= n:
        mean, lo, hi = bootstrap_ci(v, n_boot=n_boot, alpha=alpha, seed=seed)
        return mean, lo, hi, b
    rng = np.random.default_rng(seed)
    k = -(-n // b)  # blocks per replicate, ceil
    starts = rng.integers(0, n, size=(n_boot, k))
    idx = (starts[:, :, None] + np.arange(b)) % n
    samples = v[idx.reshape(n_boot, k * b)[:, :n]]
    means = samples.mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(v.mean()), float(lo), float(hi), b


@dataclass(slots=True)
class BaselineTest:
    strategy_total_return: float
    baseline_mean_return: float
    baseline_std_return: float
    p_value: float          # P(null total return >= strategy's)
    n_sims: int
    kind: str = "drift"     # "matched" (trade-template null) or "drift"
    diagnostics: dict = field(default_factory=dict)
    p_value_mean_r: float = float("nan")  # P(null mean trade R >= strategy's);
                                          # risk-normalized, exposure-robust

    @property
    def significant_5pct(self) -> bool:
        return self.p_value < 0.05


def _exposure_stats(result: BacktestResult) -> tuple[int, float, float]:
    """(n_trades, exposure fraction, mean holding bars) of a result."""
    trades = result.trades
    n_bars = max(len(result.candles), 1)
    if not trades:
        return 0, 0.0, 0.0
    holds = [t.holding_bars for t in trades]
    return len(trades), float(sum(holds) / n_bars), float(np.mean(holds))


def matched_baseline_test(
    candles: Candles,
    result: BacktestResult,
    backtester: Backtester,
    eligible_mask: np.ndarray | None = None,
    n_sims: int = 200,
    seed: int = 42,
    risk_pct: float = 1.0,
    max_leverage: float = 5.0,
) -> BaselineTest:
    """Randomized trade-template null (see module docstring for the estimand).

    Side mix, stop/target geometry, risk sizing, trade count, and
    eligible-time universe are inherited from the real trades; entries are
    market orders at the randomized times, so execution type and realized
    exposure/holding may differ — the diagnostics quantify by how much.
    Two p-values are computed: total return (exposure-sensitive) and mean
    per-trade R (risk-normalized, exposure-robust).
    """
    trades = result.trades
    if not trades:
        return BaselineTest(0.0, 0.0, 0.0, 1.0, 0, kind="matched")

    def _mean_r(ts) -> float:
        rs = [t.r_multiple for t in ts if not np.isnan(t.r_multiple)]
        return float(np.mean(rs)) if rs else 0.0

    returns = np.empty(n_sims)
    mean_rs = np.empty(n_sims)
    diag_trades = np.empty(n_sims)
    diag_exposure = np.empty(n_sims)
    diag_holding = np.empty(n_sims)
    for k in range(n_sims):
        null = MatchedRandomStrategy(
            candles, trades, seed=seed + k, eligible_mask=eligible_mask,
            risk_pct=risk_pct, max_leverage=max_leverage,
        )
        res = backtester.run(candles, null)
        returns[k] = res.total_return
        mean_rs[k] = _mean_r(res.trades)
        diag_trades[k], diag_exposure[k], diag_holding[k] = _exposure_stats(res)

    strat_n, strat_exp, strat_hold = _exposure_stats(result)
    strat = result.total_return
    p = float((1 + np.sum(returns >= strat)) / (n_sims + 1))
    p_mean_r = float((1 + np.sum(mean_rs >= _mean_r(trades))) / (n_sims + 1))
    return BaselineTest(
        strategy_total_return=strat,
        baseline_mean_return=float(returns.mean()),
        baseline_std_return=float(returns.std(ddof=1)) if n_sims > 1 else 0.0,
        p_value=p,
        n_sims=n_sims,
        kind="matched",
        p_value_mean_r=p_mean_r,
        diagnostics={
            "strategy_trades": strat_n,
            "null_mean_trades": float(diag_trades.mean()),
            "strategy_exposure_pct": strat_exp * 100,
            "null_mean_exposure_pct": float(diag_exposure.mean()) * 100,
            "strategy_mean_holding_bars": strat_hold,
            "null_mean_holding_bars": float(diag_holding.mean()),
        },
    )


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
        return BaselineTest(0.0, 0.0, 0.0, 1.0, 0, kind="drift")

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
        kind="drift",
    )
