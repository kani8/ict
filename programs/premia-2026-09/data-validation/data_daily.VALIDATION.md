# VALIDATION.md

Universe: 20 tickers. Failed downloads: none.
3m T-bill source: FRED DTB3.

## Per-ticker in-sample (date < 2024-07-01) summary

| ticker | first date | last in-sample date | in-sample rows | gaps vs SPY calendar | max abs adj return | date of max | days abs(ret)>15% |
|---|---|---|---|---|---|---|---|
| SPY | 2003-01-02 | 2024-06-28 | 5,409 | 0 | 14.52% | 2008-10-13 | 0 |
| QQQ | 2003-01-02 | 2024-06-28 | 5,409 | 0 | 12.16% | 2008-10-13 | 0 |
| IWM | 2003-01-02 | 2024-06-28 | 5,409 | 0 | 13.27% | 2020-03-16 | 0 |
| EFA | 2003-01-02 | 2024-06-28 | 5,409 | 0 | 15.89% | 2008-10-13 | 1 |
| EEM | 2003-04-14 | 2024-06-28 | 5,339 | 0 | 22.77% | 2008-10-13 | 3 |
| EWJ | 2003-01-02 | 2024-06-28 | 5,409 | 0 | 15.82% | 2008-10-13 | 1 |
| TLT | 2003-01-02 | 2024-06-28 | 5,409 | 0 | 7.52% | 2020-03-20 | 0 |
| IEF | 2003-01-02 | 2024-06-28 | 5,409 | 0 | 3.43% | 2009-03-18 | 0 |
| LQD | 2003-01-02 | 2024-06-28 | 5,409 | 0 | 9.77% | 2008-09-30 | 0 |
| HYG | 2007-04-11 | 2024-06-28 | 4,335 | 0 | 12.27% | 2008-10-13 | 0 |
| TIP | 2003-12-05 | 2024-06-28 | 5,175 | 0 | 4.45% | 2020-03-20 | 0 |
| GLD | 2004-11-18 | 2024-06-28 | 4,935 | 0 | 11.29% | 2008-09-17 | 0 |
| SLV | 2006-04-28 | 2024-06-28 | 4,573 | 0 | 17.99% | 2008-10-10 | 1 |
| USO | 2006-04-10 | 2024-06-28 | 4,586 | 0 | 25.32% | 2020-03-09 | 5 |
| DBC | 2006-02-06 | 2024-06-28 | 4,630 | 0 | 7.94% | 2022-03-09 | 0 |
| UUP | 2007-03-01 | 2024-06-28 | 4,363 | 0 | 4.06% | 2007-06-21 | 0 |
| FXE | 2005-12-12 | 2024-06-28 | 4,667 | 0 | 3.67% | 2009-03-18 | 0 |
| FXY | 2007-02-13 | 2024-06-28 | 4,374 | 0 | 4.35% | 2008-10-28 | 0 |
| FXA | 2006-06-26 | 2024-06-28 | 4,533 | 0 | 7.74% | 2008-10-13 | 0 |
| VNQ | 2004-09-29 | 2024-06-28 | 4,971 | 0 | 19.51% | 2008-12-01 | 5 |

## Days with |adjusted daily return| > 15%

| ticker | date | return |
|---|---|---|
| EEM | 2008-10-13 | 22.77% |
| EEM | 2008-10-15 | -16.17% |
| EEM | 2008-10-28 | 20.93% |
| EFA | 2008-10-13 | 15.89% |
| EWJ | 2008-10-13 | 15.82% |
| SLV | 2008-10-10 | -17.99% |
| USO | 2020-03-09 | -25.32% |
| USO | 2020-03-18 | -17.51% |
| USO | 2020-04-02 | 16.67% |
| USO | 2020-04-03 | 15.46% |
| USO | 2020-04-21 | -25.07% |
| VNQ | 2008-10-28 | 15.64% |
| VNQ | 2008-11-24 | 17.01% |
| VNQ | 2008-12-01 | -19.51% |
| VNQ | 2009-03-23 | 16.17% |
| VNQ | 2020-03-16 | -17.73% |

## adj_close/close ratio monotonicity (must be non-decreasing forward in time; a decrease flags a dividend/split-adjustment inconsistency)

None found -- adjustments are dividend/split-consistent for all tickers.

## SPY vs IVV sanity check (IVV is a one-off pull, not part of the saved universe)

Correlation of SPY vs IVV in-sample daily adjusted returns (5,409 overlapping days, 2003-01-02 .. 2024-06-28): 0.9945 (PASS, threshold 0.97).

## Timing

- Universe download time (20 tickers): 15.4s
- Total script wall time (download + T-bill + IVV sanity + validation): 16.4s
