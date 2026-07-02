import numpy as np

from ict_backtest.analytics import bootstrap_ci, compute_metrics, random_baseline_test, render_report
from ict_backtest.data import synthetic_candles
from ict_backtest.engine import Backtester, CostModel
from ict_backtest.strategy import RandomStrategy, SMCConfig, SMCStrategy


def _loose_config() -> SMCConfig:
    return SMCConfig(use_killzones=False, require_ote=False, require_discount=False,
                     htf_multiplier=8, min_rr=1.0)


def test_smc_end_to_end_produces_trades():
    candles = synthetic_candles(n=8000, seed=13, base_vol=0.004)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    result = bt.run(candles, SMCStrategy(candles, _loose_config()))
    assert len(result.trades) >= 5
    m = compute_metrics(result)
    assert m.n_trades == len(result.trades)
    assert 0.0 <= m.win_rate <= 1.0
    assert m.max_drawdown_pct <= 0.0
    # every trade respected the one-position-at-a-time rule
    for a, b in zip(result.trades, result.trades[1:]):
        assert b.entry_index >= a.exit_index


def test_bias_gates_direction():
    candles = synthetic_candles(n=8000, seed=13, base_vol=0.004)
    strat = SMCStrategy(candles, _loose_config())
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    result = bt.run(candles, strat)
    for t in result.trades:
        # order was staged at some bar <= entry; bias must have agreed at
        # staging time — weakly check the entry bar's neighborhood
        window = strat.bias[max(0, t.entry_index - strat.cfg.order_expiry_bars): t.entry_index + 1]
        assert (window == t.side).any()


def test_bootstrap_ci_signs():
    mean, lo, hi = bootstrap_ci(np.ones(50) + 0.1 * np.random.default_rng(0).standard_normal(50))
    assert lo > 0
    mean, lo, hi = bootstrap_ci(np.random.default_rng(0).standard_normal(200) * 2)
    assert lo < 0 < hi


def test_random_baseline_p_value_bounds():
    candles = synthetic_candles(n=4000, seed=13, base_vol=0.004)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    result = bt.run(candles, SMCStrategy(candles, _loose_config()))
    test = random_baseline_test(candles, result, bt, n_sims=20)
    assert 0.0 < test.p_value <= 1.0
    assert test.n_sims == 20


def test_random_strategy_roughly_breaks_even_gross():
    """On drift-free data with zero costs the null strategy must not have edge."""
    candles = synthetic_candles(n=6000, seed=21, trend_strength=0.0)
    bt = Backtester(cost=CostModel(0, 0, 0), initial_equity=100_000)
    finals = []
    for seed in range(10):
        strat = RandomStrategy(candles, entry_prob=0.05, holding_bars=8, seed=seed)
        finals.append(bt.run(candles, strat).total_return)
    assert abs(float(np.mean(finals))) < 0.05


def test_report_renders(tmp_path):
    candles = synthetic_candles(n=6000, seed=13, base_vol=0.004)
    bt = Backtester(cost=CostModel(), initial_equity=100_000)
    result = bt.run(candles, SMCStrategy(candles, _loose_config()))
    text = render_report(result, compute_metrics(result))
    assert "## Performance" in text
    assert "| Trades |" in text


def test_cli_smoke(tmp_path, capsys):
    from ict_backtest.cli import main
    from ict_backtest.data.fetch import save_candles

    data = tmp_path / "synth.parquet"
    save_candles(synthetic_candles(n=6000, seed=13, base_vol=0.004), data)
    rc = main([
        "run", "--data", str(data), "--validate", "5",
        "--report", str(tmp_path / "report.md"),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "## Performance" in out
    assert (tmp_path / "report.md").exists()
