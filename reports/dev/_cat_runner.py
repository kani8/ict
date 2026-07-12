"""CAT validation runner — mechanics calibration on synthetic worlds.

Thin driver over the tested library. Two worlds, ES-calibrated costs:

* regime world (``synthetic_cat_regimes``): consolidation/direction by
  construction — the exact universe the CAT approach claims as its edge.
  Correct mechanics should extract edge here.
* null world (``synthetic_candles`` with ``trend_strength=0``): a pure
  random walk — correct mechanics should find nothing.

Passing both is a calibration of the implementation, NOT evidence about
any market. The ES run itself is preregistered in configs/cat_es.toml
and blocked on data availability (see reports/CAT_STUDY.md).

Usage: uv run python reports/dev/_cat_runner.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ict_backtest.analytics import block_bootstrap_ci, compute_metrics, matched_baseline_test
from ict_backtest.data import synthetic_cat_regimes, synthetic_candles
from ict_backtest.engine import Backtester, CostModel
from ict_backtest.strategy import CATConfig, CATStrategy
from ict_backtest.strategy.cat import CAT_CONSOLIDATION, CAT_DIRECTION

ES_COST = dict(spread_bps=0.4, commission_bps=0.1, slippage_bps=0.4)
ZERO_COST = dict(spread_bps=0.0, commission_bps=0.0, slippage_bps=0.0)
N_BARS = 35_040          # one year of 15m bars
SEEDS = (1, 2, 3)
N_SIMS = 300


def run_one(candles, cfg, cost, n_sims=N_SIMS, policy="conservative"):
    bt = Backtester(cost=CostModel(**cost), intrabar_policy=policy)
    strat = CATStrategy(candles, cfg)
    res = bt.run(candles, strat)
    m = compute_metrics(res)
    rs = [t.r_multiple for t in res.trades if not np.isnan(t.r_multiple)]
    mean_r, lo, hi, blk = block_bootstrap_ci(rs) if rs else (0.0, 0.0, 0.0, 0)
    null = matched_baseline_test(candles, res, bt, eligible_mask=strat.eligible_mask,
                                 n_sims=n_sims, risk_pct=cfg.risk_pct,
                                 max_leverage=cfg.max_leverage)
    by_tag = {}
    for tag in ("cat_cons", "cat_dir"):
        tt = [t for t in res.trades if t.tag == tag]
        trs = [t.r_multiple for t in tt if not np.isnan(t.r_multiple)]
        by_tag[tag] = dict(n=len(tt), mean_r=float(np.mean(trs)) if trs else float("nan"),
                           win_rate=float(np.mean([t.pnl > 0 for t in tt])) if tt else float("nan"))
    return dict(
        n_trades=m.n_trades, total_return_pct=m.total_return_pct,
        win_rate=m.win_rate, profit_factor=m.profit_factor,
        mean_r=mean_r, r_ci=[lo, hi], block_len=blk,
        p_return=null.p_value, p_mean_r=null.p_value_mean_r,
        null_note=null.note, exposure_pct=m.exposure_pct,
        avg_holding_bars=m.avg_holding_bars, by_tag=by_tag,
        skip_counts=dict(strat.skip_counts),
    )


def classifier_diag(candles, labels, cfg):
    """Coverage + agreement of the mechanized category vs ground truth."""
    strat = CATStrategy(candles, cfg)
    cat = strat.category
    w = cfg.regime_window
    scored = np.zeros(len(cat), bool)
    scored[w:] = True
    covered = scored & (cat != 0)
    agree_dir = (cat == CAT_DIRECTION) & (labels == 1)
    agree_cons = (cat == CAT_CONSOLIDATION) & (labels == 2)
    return dict(
        coverage=float(covered.sum() / scored.sum()),
        accuracy_when_covered=float((agree_dir | agree_cons)[covered].sum() / covered.sum()),
        share_direction=float((cat[covered] == CAT_DIRECTION).mean()),
        base_rate_direction=float((labels[scored] == 1).mean()),
    )


def main() -> None:
    cfg = CATConfig()
    out: dict = {"config": "CATConfig() defaults == configs/cat_default.toml",
                 "n_bars": N_BARS, "n_sims": N_SIMS, "regime": {}, "null": {},
                 "diagnostics": {}, "cost_sensitivity": {}, "intrabar": {}}

    for seed in SEEDS:
        candles, labels = synthetic_cat_regimes(n=N_BARS, seed=seed)
        out["regime"][seed] = run_one(candles, cfg, ES_COST)
        out["diagnostics"][seed] = classifier_diag(candles, labels, cfg)
        nullc = synthetic_candles(n=N_BARS, seed=seed, trend_strength=0.0,
                                  base_vol=0.0012, start_price=5_000.0)
        out["null"][seed] = run_one(nullc, cfg, ES_COST)
        print(f"seed {seed} done", flush=True)

    candles, _ = synthetic_cat_regimes(n=N_BARS, seed=SEEDS[0])
    out["cost_sensitivity"]["zero"] = run_one(candles, cfg, ZERO_COST, n_sims=0)
    out["cost_sensitivity"]["crypto_1_2_1"] = run_one(
        candles, cfg, dict(spread_bps=1.0, commission_bps=2.0, slippage_bps=1.0), n_sims=0)
    out["intrabar"]["optimistic"] = run_one(candles, cfg, ES_COST, n_sims=0,
                                            policy="optimistic")

    path = Path(__file__).with_name("_cat_results.json")
    path.write_text(json.dumps(out, indent=2))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
