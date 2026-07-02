# SMC Backtest — synthetic random-walk null (1y of 15m bars)

- Bars: **35,040** (15m timeframe)
- Initial equity: **100,000**  →  Final: **94,541**

## Performance

| Metric | Value |
|---|---|
| Trades | 27 |
| Win rate | 18.5% |
| Profit factor | 0.76 |
| Avg R multiple | -0.26 |
| Total return | -5.46% |
| CAGR | -5.46% |
| Sharpe | -0.55 |
| Sortino | -0.09 |
| Max drawdown | -13.47% |
| Exposure | 0.7% |
| Avg / median holding (bars) | 8.9 / 7.0 |

## Statistical validity

- Mean trade R: **-0.26**, 95% bootstrap CI **[-0.93, 0.53]** — **cannot reject zero edge**.
- Random-entry null (200 sims, matched frequency/holding/direction/killzones): baseline mean return -1.87% ± 5.33%, strategy -5.46%, p = 0.781 (**not significant at 5%**).

## Last trades

| # | Side | Entry bar | Exit bar | R | PnL | Reason |
|---|---|---|---|---|---|---|
| 1 | short | 13194 | 13201 | -1.10 | -1,074.42 | sl |
| 2 | long | 14189 | 14193 | -1.10 | -1,060.59 | sl |
| 3 | short | 15422 | 15429 | -1.09 | -1,040.45 | sl |
| 4 | short | 15612 | 15625 | -1.09 | -1,023.43 | sl |
| 5 | short | 19536 | 19551 | 2.40 | 2,234.62 | tp |
| 6 | long | 20219 | 20226 | -1.18 | -1,130.35 | sl |
| 7 | long | 21464 | 21483 | -1.10 | -1,034.08 | sl |
| 8 | long | 22506 | 22512 | -1.17 | -1,098.33 | sl |
| 9 | long | 25598 | 25601 | -1.11 | -1,026.18 | sl |
| 10 | long | 26079 | 26080 | -1.09 | -989.52 | sl |
| 11 | short | 28499 | 28502 | -1.08 | -970.99 | sl |
| 12 | long | 30208 | 30243 | -1.06 | -943.92 | sl |
| 13 | short | 30763 | 30773 | 3.71 | 3,270.65 | tp |
| 14 | long | 34318 | 34318 | -2.34 | -434.44 | sl |
| 15 | long | 34894 | 34911 | 4.82 | 4,397.89 | tp |
