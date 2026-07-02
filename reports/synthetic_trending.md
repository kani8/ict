# SMC Backtest — synthetic trending regime (1y of 15m bars)

- Bars: **35,040** (15m timeframe)
- Initial equity: **100,000**  →  Final: **101,949**

## Performance

| Metric | Value |
|---|---|
| Trades | 4 |
| Win rate | 50.0% |
| Profit factor | 1.86 |
| Avg R multiple | 0.49 |
| Total return | 1.95% |
| CAGR | 1.95% |
| Sharpe | 0.60 |
| Sortino | 0.03 |
| Max drawdown | -3.38% |
| Exposure | 0.1% |
| Avg / median holding (bars) | 8.0 / 7.5 |
- Trade-template null (200 sims: entry timing randomized; side, fractional stop/target geometry, risk sizing, and trade count retained; execution type and realized exposure may differ — see diagnostics): null mean return 0.68% ± 2.95%, strategy 1.95%, p = 0.229 (**not significant at 5%**).
- Same null, mean trade R statistic (risk-normalized, robust to the exposure mismatch): p = 0.229 (**not significant at 5%**).
- Null matching diagnostics: trades 4 vs 4.0 (null mean); exposure 0.09% vs 0.07%; mean holding 8.0 vs 6.5 bars.

## Last trades

| # | Side | Entry bar | Exit bar | R | PnL | Reason |
|---|---|---|---|---|---|---|
| 1 | long | 2076 | 2080 | 1.90 | 1,917.86 | tp |
| 2 | long | 11761 | 11775 | -1.12 | -1,150.00 | sl |
| 3 | short | 24054 | 24057 | -1.09 | -1,108.77 | sl |
| 4 | long | 28398 | 28409 | 2.28 | 2,289.57 | tp |
