"""Command-line interface.

    ict-backtest fetch  --symbol BTCUSDT --interval 15m --start 2023-01-01 --out data/btc.parquet
    ict-backtest synth  --bars 30000 --out data/synth.parquet
    ict-backtest run    --data data/btc.parquet [--config configs/default.toml]
                        [--validate 200] [--report report.md]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analytics import compute_metrics, random_baseline_test, render_report
from .data import load_candles, synthetic_candles
from .engine import Backtester, CostModel
from .strategy import SMCConfig, SMCStrategy


def _cmd_fetch(args: argparse.Namespace) -> int:
    from .data.fetch import fetch_binance, save_candles

    candles = fetch_binance(symbol=args.symbol, interval=args.interval,
                            start=args.start, end=args.end)
    save_candles(candles, args.out)
    print(f"saved {len(candles):,} candles to {args.out}")
    return 0


def _cmd_synth(args: argparse.Namespace) -> int:
    from .data.fetch import save_candles

    candles = synthetic_candles(n=args.bars, timeframe_s=args.timeframe_s, seed=args.seed)
    save_candles(candles, args.out)
    print(f"saved {len(candles):,} synthetic candles to {args.out}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    candles = load_candles(args.data, start=args.start, end=args.end)
    config = SMCConfig.from_toml(args.config) if args.config else SMCConfig()
    cost = CostModel(spread_bps=args.spread_bps, commission_bps=args.commission_bps,
                     slippage_bps=args.slippage_bps)
    backtester = Backtester(cost=cost, initial_equity=args.equity,
                            intrabar_policy=args.intrabar_policy)
    strategy = SMCStrategy(candles, config)
    result = backtester.run(candles, strategy)
    metrics = compute_metrics(result)

    baseline = None
    if args.validate:
        baseline = random_baseline_test(candles, result, backtester,
                                        eligible_mask=strategy.kz_mask, n_sims=args.validate)

    report = render_report(result, metrics, baseline,
                           title=f"SMC Backtest — {Path(args.data).stem}")
    print(report)
    if args.report:
        Path(args.report).write_text(report)
        print(f"(report written to {args.report})", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ict-backtest",
                                     description="SMC/ICT strategy backtesting harness")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch", help="download Binance klines")
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--interval", default="15m")
    p.add_argument("--start", default="2023-01-01")
    p.add_argument("--end", default=None)
    p.add_argument("--out", required=True)
    p.set_defaults(func=_cmd_fetch)

    p = sub.add_parser("synth", help="generate synthetic candles")
    p.add_argument("--bars", type=int, default=30_000)
    p.add_argument("--timeframe-s", type=int, default=900)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", required=True)
    p.set_defaults(func=_cmd_synth)

    p = sub.add_parser("run", help="run the SMC backtest")
    p.add_argument("--data", required=True)
    p.add_argument("--config", default=None)
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--equity", type=float, default=100_000.0)
    p.add_argument("--spread-bps", type=float, default=1.0)
    p.add_argument("--commission-bps", type=float, default=2.0)
    p.add_argument("--slippage-bps", type=float, default=1.0)
    p.add_argument("--intrabar-policy", choices=["conservative", "optimistic"],
                   default="conservative")
    p.add_argument("--validate", type=int, default=0, metavar="N_SIMS",
                   help="run the random-entry null test with N simulations")
    p.add_argument("--report", default=None, help="write the markdown report here")
    p.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
