# Tooling decisions

**Jesse MCP — evaluated 2026-09-08, dropped (≈5 min).** Jesse's backtesting data sources are crypto exchanges only (Binance, Bybit, Coinbase, Kraken Futures, KuCoin, Gate.io, Bitfinex). No CSV/Parquet import path, no CME/Databento connector, no notion of contract expiry or rolling. Using it for ES would require writing a data adapter and faking an "exchange", which the brief forbids. Its MCP features (Monte Carlo, significance tests) are replaceable with ~50 lines of numpy plus the ICT repo's block bootstrap.

**Stack in use:** Python 3, pandas / numpy / pyarrow, `uv` for env. Reused from `ict/`: block-bootstrap analytics and the no-lookahead prefix-consistency test pattern. The ICT fill engine is *not* used for premise 1 — the strategy has exactly two fills per trade (bar open in, bar open out) with no intrabar stops, so a stateful fill engine adds complexity without changing a single fill; vectorised P&L is exact here. Revisit if a later premise needs intrabar stops.

**Not used, deliberately:** databases, dashboards, config frameworks, notebooks as deliverables, any backtesting library.

## Constraint: zero budget for external tooling (user, 2026-09-08). Free/OSS only.

Evaluated under that constraint:

| Tool | Verdict | Why |
|---|---|---|
| Jesse (+MCP) | drop | crypto-only data model; see above |
| vectorbt / backtesting.py / backtrader / nautilus / Lean | drop | premise 1 has two fills per trade and no intrabar logic; vectorised pandas P&L is exact. A framework adds surface area, not correctness. Revisit only if a premise needs intrabar stops, and even then the ICT engine is already here and tested |
| statsmodels (HAC OLS), numpy bootstrap | use | free, ~0 integration cost |
| Free data cross-checks: SPY daily (Stooq/yfinance), VIX history (CBOE CSV) | use for validation only | daily-return correlation of our ES continuous series vs SPY should be ≈0.98+; cheap roll-correctness check. Not used as a signal input |
| Finance/paper MCPs (yfinance-mcp, arxiv-mcp etc.) | drop | schema token overhead exceeds the value of what a WebFetch already does |
| Paper trading venues | decide at step 9 | IBKR paper, Tradovate demo, NinjaTrader sim accounts are free, but **real-time CME data usually is not** (≈$10–15/mo bundles). The 15:00 ET decision needs a live 15:00 print, so delayed data is not acceptable. Resolution: ask the user which broker accounts/data entitlements they already have before step 9 — that is the cheapest path, and it is on the ping list. User's initial preference: **NinjaTrader** sim (2026-09-08); to be worked out if/when a premise passes OOS |
