# SMC Backtest — synthetic trending regime (1y of 15m bars)

- Bars: **35,040** (15m timeframe)
- Initial equity: **100,000**  →  Final: **108,354**

## Performance

| Metric | Value |
|---|---|
| Trades | 12 |
| Win rate | 50.0% |
| Profit factor | 2.19 |
| Avg R multiple | 0.69 |
| Total return | 8.35% |
| CAGR | 8.36% |
| Sharpe | 1.27 |
| Sortino | 0.11 |
| Max drawdown | -5.15% |
| Exposure | 0.2% |
| Avg / median holding (bars) | 6.9 / 4.0 |

## Statistical validity

- Mean trade R: **0.69**, 95% bootstrap CI **[-0.33, 1.77]** — **cannot reject zero edge**.
- Random-entry null (200 sims, matched frequency/holding/direction/killzones): baseline mean return -0.56% ± 2.88%, strategy 8.35%, p = 0.005 (significant at 5%).

## Last trades

| # | Side | Entry bar | Exit bar | R | PnL | Reason |
|---|---|---|---|---|---|---|
| 1 | long | 2076 | 2080 | 1.90 | 1,917.86 | tp |
| 2 | long | 7766 | 7770 | -1.15 | -1,188.03 | sl |
| 3 | long | 8692 | 8705 | 1.88 | 1,915.35 | tp |
| 4 | long | 9569 | 9570 | -1.22 | -1,280.60 | sl |
| 5 | long | 11486 | 11488 | -1.11 | -1,137.35 | sl |
| 6 | long | 11761 | 11775 | -1.12 | -1,130.93 | sl |
| 7 | long | 14349 | 14349 | -1.10 | -1,101.92 | sl |
| 8 | short | 18402 | 18413 | 2.48 | 2,453.61 | tp |
| 9 | short | 22318 | 22335 | 3.96 | 4,003.68 | tp |
| 10 | short | 22920 | 22923 | 2.51 | 2,647.36 | tp |
| 11 | short | 24054 | 24057 | -1.09 | -1,178.43 | sl |
| 12 | long | 28398 | 28409 | 2.28 | 2,433.43 | tp |
