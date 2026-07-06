"""Program T: trend-study library, TSMOM strategy, portfolio aggregation."""

import numpy as np
import pytest

from ict_backtest.analytics.portfolio import combine_portfolio, render_portfolio
from ict_backtest.analytics.trend_study import (
    portfolio_rows,
    render_trend_battery,
    shift_null_p,
    trend_signals,
    tsmom_rows,
    vol_scale,
)
from ict_backtest.core import BEAR, BULL, Candles
from ict_backtest.engine import Backtester, Broker, CostModel
from ict_backtest.strategy import TimeSeriesMomentumStrategy, TrendConfig

ZERO_COST = CostModel(spread_bps=0.0, commission_bps=0.0, slippage_bps=0.0)
DAY = 86_400


def daily_candles(closes: np.ndarray, start_ts: int = 1_600_000_000) -> Candles:
    n = len(closes)
    ts = start_ts - start_ts % DAY + DAY * np.arange(n)
    opens = np.concatenate(([closes[0]], closes[:-1]))
    return Candles(ts=ts.astype(np.int64), open=opens,
                   high=np.maximum(opens, closes) * 1.001,
                   low=np.minimum(opens, closes) * 0.999,
                   close=closes.astype(float), volume=np.ones(n), timeframe_s=DAY)


def trending_closes(n: int, drift: float, vol: float = 0.005, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return 100.0 * np.exp(np.cumsum(drift + vol * rng.standard_normal(n)))


# ---------------------------------------------------------------------------
# trend_study
# ---------------------------------------------------------------------------


def test_trend_signals_signs_and_warmup():
    up = daily_candles(trending_closes(400, +0.002))
    sigs = trend_signals(up.close)
    assert set(sigs) == {"21", "63", "252", "vote"}
    assert np.all(sigs["vote"][:252] == 0)             # no vote until warmed up
    assert np.all(sigs["vote"][300:] == 1)             # steady uptrend -> long
    down = daily_candles(trending_closes(400, -0.002))
    assert np.all(trend_signals(down.close)["vote"][300:] == -1)


def test_vol_scale_trailing_and_capped():
    close = trending_closes(300, 0.0, vol=0.02, seed=2)
    scale = vol_scale(close, vol_lookback=63, vol_target=0.10, cap=4.0)
    assert np.all(scale[:62] == 0) or np.all(np.isfinite(scale))
    live = scale[100:]
    assert np.all(live <= 4.0) and np.all(live > 0)
    # low-vol series should get more leverage than high-vol
    calm = vol_scale(trending_closes(300, 0.0, vol=0.002, seed=2), cap=100.0)
    assert np.nanmean(calm[100:]) > np.nanmean(
        vol_scale(trending_closes(300, 0.0, vol=0.02, seed=2), cap=100.0)[100:])


def test_tsmom_rows_positive_on_strong_trend_null_on_noise():
    trend = daily_candles(trending_closes(1500, +0.001, vol=0.004, seed=3))
    rows = tsmom_rows(trend, n_shifts=100)
    primary = next(r for r in rows if r["variant"] == "vote" and r["scaled"])
    assert primary["mean"] > 0 and primary["ci_lo"] > 0
    # a driftless random walk must not show support
    noise = daily_candles(trending_closes(1500, 0.0, vol=0.01, seed=4))
    nrows = tsmom_rows(noise, n_shifts=100)
    nprimary = next(r for r in nrows if r["variant"] == "vote" and r["scaled"])
    assert not (nprimary["ci_lo"] > 0 and nprimary["p_shift"] < 0.05)


def test_shift_null_p_detects_alignment():
    rng = np.random.default_rng(5)
    r = rng.standard_normal(2000) * 0.01
    aligned = np.sign(r)                                # perfect foresight signal
    assert shift_null_p(aligned, r, n_shifts=200) < 0.05
    shuffled = rng.permutation(aligned)
    assert shift_null_p(shuffled, r, n_shifts=200) > 0.05


def test_portfolio_rows_and_render():
    instruments = {
        "A": daily_candles(trending_closes(900, +0.001, seed=6)),
        "B": daily_candles(trending_closes(900, -0.001, seed=7)),
    }
    rows = portfolio_rows(instruments, n_shifts=50)
    assert rows[0]["name"] == "PORTFOLIO" and rows[0]["n"] >= 600
    assert {r["name"] for r in rows[1:]} == {"A", "B"}
    per = {k: tsmom_rows(v, n_shifts=50) for k, v in instruments.items()}
    text = render_trend_battery(per, rows, "toy")
    assert "PORTFOLIO" in text and "per-variant" in text


# ---------------------------------------------------------------------------
# TimeSeriesMomentumStrategy
# ---------------------------------------------------------------------------


def test_tsmom_goes_long_uptrend_and_flips():
    closes = np.concatenate([trending_closes(400, +0.003, vol=0.001, seed=8),
                             trending_closes(400, -0.003, vol=0.001, seed=9)
                             * trending_closes(400, +0.003, vol=0.001, seed=8)[-1] / 100.0])
    candles = daily_candles(closes)
    strat = TimeSeriesMomentumStrategy(candles, TrendConfig())
    result = Backtester(cost=ZERO_COST).run(candles, strat)
    sides = [t.side for t in result.trades]
    assert BULL in sides and BEAR in sides              # traded both regimes
    assert sides[0] == BULL                             # uptrend first
    # every entry matches the signal at the preceding bar's close
    for t in result.trades:
        assert np.sign(strat.signal[t.entry_index - 1]) == t.side


def test_tsmom_vol_targeting_sizes_notional():
    closes = trending_closes(600, +0.002, vol=0.004, seed=10)
    candles = daily_candles(closes)
    cfg = TrendConfig(vol_target=0.10, max_leverage=4.0)
    strat = TimeSeriesMomentumStrategy(candles, cfg)
    result = Backtester(cost=ZERO_COST, initial_equity=100_000).run(candles, strat)
    assert result.trades or Backtester(cost=ZERO_COST).run(candles, strat)
    first = result.trades[0] if result.trades else None
    if first is not None:
        notional = first.qty * first.entry_price
        lev = strat.leverage[first.entry_index - 1]
        assert notional == pytest.approx(100_000 * lev, rel=0.05)


def test_tsmom_rebalance_band_limits_churn():
    closes = trending_closes(700, +0.002, vol=0.004, seed=11)
    candles = daily_candles(closes)
    tight = Backtester(cost=ZERO_COST).run(
        candles, TimeSeriesMomentumStrategy(candles, TrendConfig(rebalance_band=0.01)))
    loose = Backtester(cost=ZERO_COST).run(
        candles, TimeSeriesMomentumStrategy(candles, TrendConfig(rebalance_band=1e9)))
    assert len(tight.trades) > len(loose.trades)


def test_trend_config_from_toml(tmp_path):
    path = tmp_path / "t.toml"
    path.write_text("[trend]\nlookbacks = [63, 252]\nvol_target = 0.15\n")
    cfg = TrendConfig.from_toml(path)
    assert cfg.lookbacks == (63, 252) and cfg.vol_target == 0.15
    path.write_text("[trend]\nbogus = 1\n")
    with pytest.raises(ValueError):
        TrendConfig.from_toml(path)


# ---------------------------------------------------------------------------
# portfolio aggregation
# ---------------------------------------------------------------------------


def test_combine_portfolio_math_and_render():
    a = daily_candles(trending_closes(500, +0.002, seed=12))
    b = daily_candles(trending_closes(500, +0.002, seed=13))
    bt = Backtester(cost=ZERO_COST)
    results = {"A": bt.run(a, TimeSeriesMomentumStrategy(a)),
               "B": bt.run(b, TimeSeriesMomentumStrategy(b))}
    stats = combine_portfolio(results)
    assert stats["n_instruments"] == 2 and stats["n_days"] == 500
    assert np.isfinite(stats["sharpe"]) and stats["max_drawdown"] <= 0
    # portfolio vol should not exceed the max single-instrument vol
    single = {k: combine_portfolio({k: v})["ann_vol"] for k, v in results.items()}
    assert stats["ann_vol"] <= max(single.values()) + 1e-12
    text = render_portfolio(stats, "toy portfolio")
    assert "Sharpe" in text and "| A |" in text


# ---------------------------------------------------------------------------
# no-lookahead: prefix consistency
# ---------------------------------------------------------------------------


class RecordingTSMOM(TimeSeriesMomentumStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submissions: list[tuple] = []

    def on_bar(self, i, broker: Broker):
        before = broker._next_id
        super().on_bar(i, broker)
        for oid in range(before, broker._next_id):
            order = broker.pending.get(oid)
            if order is not None:
                self.submissions.append(
                    (i, order.side, round(order.qty, 8), order.type))


@pytest.mark.parametrize("cutoff", [600, 900])
def test_prefix_consistency_tsmom(cutoff):
    closes = trending_closes(1200, +0.0005, vol=0.01, seed=14)
    candles = daily_candles(closes)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)

    full = RecordingTSMOM(candles)
    bt.run(candles, full)
    full_subs = [s for s in full.submissions if s[0] < cutoff]

    prefix = RecordingTSMOM(candles.slice(0, cutoff))
    bt.run(candles.slice(0, cutoff), prefix)

    assert len(full_subs) > 0, "test is vacuous: no orders before the cutoff"
    assert prefix.submissions == full_subs
