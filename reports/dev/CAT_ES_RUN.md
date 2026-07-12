# CAT Backtest — es_15m

- Bars: **376,768** (15m timeframe)
- Initial equity: **100,000**  →  Final: **0**

## Performance

| Metric | Value |
|---|---|
| Trades | 47387 |
| Win rate | 46.5% |
| Profit factor | 0.62 |
| Avg R multiple | -0.34 |
| Total return | -100.00% |
| CAGR | -86.02% |
| Sharpe | -10.89 |
| Sortino | -6.78 |
| Max drawdown | -100.00% |
| Exposure | 6.6% |
| Avg / median holding (bars) | 0.5 / 0.0 |

## Statistical validity

- Mean trade R: **-0.34**, 95% block-bootstrap CI **[-0.35, -0.33]** (block length 36, preserves trade clustering) — negative edge.
- Trade-template null (500 sims: entry timing randomized; side, fractional stop/target geometry, risk sizing, and trade count retained; execution type and realized exposure may differ — see diagnostics): null mean return -100.00% ± 0.00%, strategy -100.00%, p = 0.054 (**not significant at 5%**).
- Same null, mean trade R statistic (risk-normalized, robust to the exposure mismatch): p = 0.830 (**not significant at 5%**).
- Null matching diagnostics: trades 47387 vs 47,386.7 (null mean); exposure 6.56% vs 28.57%; mean holding 0.5 vs 2.3 bars.

## Last trades

| # | Side | Entry bar | Exit bar | R | PnL | Reason |
|---|---|---|---|---|---|---|
| 1 | long | 376624 | 376627 | 0.59 | 0.00 | tp |
| 2 | short | 376630 | 376630 | -1.21 | -0.00 | sl |
| 3 | short | 376632 | 376632 | 0.78 | 0.00 | tp |
| 4 | short | 376633 | 376633 | 0.56 | 0.00 | tp |
| 5 | long | 376635 | 376636 | -1.15 | -0.00 | sl |
| 6 | long | 376638 | 376638 | 0.71 | 0.00 | tp |
| 7 | long | 376639 | 376639 | 0.74 | 0.00 | tp |
| 8 | long | 376661 | 376661 | 0.62 | 0.00 | tp |
| 9 | long | 376673 | 376676 | 0.81 | 0.00 | tp |
| 10 | short | 376713 | 376715 | -1.15 | -0.00 | sl |
| 11 | short | 376717 | 376717 | -1.22 | -0.00 | sl |
| 12 | short | 376719 | 376719 | -1.20 | -0.00 | sl |
| 13 | short | 376722 | 376722 | 0.57 | 0.00 | tp |
| 14 | short | 376723 | 376723 | 0.71 | 0.00 | tp |
| 15 | short | 376724 | 376724 | 0.73 | 0.00 | tp |
