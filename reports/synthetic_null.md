# SMC Backtest — synthetic random-walk null (1y of 15m bars)

- Bars: **35,040** (15m timeframe)
- Initial equity: **100,000**  →  Final: **109,266**

## Performance

| Metric | Value |
|---|---|
| Trades | 14 |
| Win rate | 35.7% |
| Profit factor | 1.96 |
| Avg R multiple | 0.52 |
| Total return | 9.27% |
| CAGR | 9.27% |
| Sharpe | 1.32 |
| Sortino | 0.16 |
| Max drawdown | -3.67% |
| Exposure | 0.3% |
| Avg / median holding (bars) | 7.2 / 4.0 |

## Statistical validity

- Mean trade R: **0.52**, 95% block-bootstrap CI **[-0.34, 1.30]** (block length 2, preserves trade clustering) — **cannot reject zero edge**.
- Matched-trade null (200 sims: the strategy's own trades — side, stop/target geometry, risk sizing — replayed at random eligible times): null mean return -1.39% ± 6.20%, strategy 9.27%, p = 0.050 (significant at 5%).
- Null matching diagnostics: trades 14 vs 14.0 (null mean); exposure 0.29% vs 0.30%; mean holding 7.2 vs 7.5 bars.

## Last trades

| # | Side | Entry bar | Exit bar | R | PnL | Reason |
|---|---|---|---|---|---|---|
| 1 | short | 829 | 834 | -1.12 | -1,132.06 | sl |
| 2 | short | 3887 | 3888 | -1.14 | -1,137.99 | sl |
| 3 | long | 4754 | 4756 | 4.81 | 4,802.70 | tp |
| 4 | short | 6402 | 6404 | -1.13 | -1,174.20 | sl |
| 5 | long | 7062 | 7064 | -1.09 | -1,108.35 | sl |
| 6 | long | 8591 | 8594 | -1.11 | -1,128.68 | sl |
| 7 | short | 9550 | 9575 | 2.77 | 2,767.81 | tp |
| 8 | short | 13125 | 13134 | -1.06 | -1,080.67 | sl |
| 9 | short | 19536 | 19551 | 2.40 | 2,441.53 | tp |
| 10 | long | 20219 | 20226 | -1.18 | -1,235.01 | sl |
| 11 | short | 28499 | 28502 | -1.08 | -1,110.21 | sl |
| 12 | short | 30763 | 30773 | 3.71 | 3,780.05 | tp |
| 13 | long | 34318 | 34318 | -2.34 | -502.11 | sl |
| 14 | long | 34894 | 34911 | 4.82 | 5,082.87 | tp |
