# VALIDATION.md (data_carry)

Universe: ['FXE', 'FXY', 'FXA', 'FXB', 'FXC', 'FXF', 'IEF', 'TLT']. Failed downloads: none. Rates/yields are NOT split into in-sample/OOS (they are signals; consumer filters by date).

## Per-ticker ETF summary (full 2005-01-01..2026-07-01 span)

| ticker | first | last | rows | missing vs union calendar | zero-vol days | |ret|>8% count |
|---|---|---|---|---|---|---|
| FXE | 2005-12-12 | 2026-07-01 | 5,169 | 0 | 0 | 0 |
| FXY | 2007-02-13 | 2026-07-01 | 4,876 | 0 | 0 | 0 |
| FXA | 2006-06-26 | 2026-07-01 | 5,035 | 0 | 2 | 0 |
| FXB | 2006-06-26 | 2026-07-01 | 5,035 | 0 | 6 | 1 |
| FXC | 2006-06-26 | 2026-07-01 | 5,035 | 0 | 0 | 0 |
| FXF | 2006-06-26 | 2026-07-01 | 5,035 | 0 | 0 | 2 |
| IEF | 2005-01-03 | 2026-07-01 | 5,407 | 0 | 0 | 0 |
| TLT | 2005-01-03 | 2026-07-01 | 5,407 | 0 | 0 | 0 |

## Days with |daily close return| > 8%

| ticker | date | ret |
|---|---|---|
| FXB | 2016-06-24 | -8.36% |
| FXF | 2011-09-06 | -8.34% |
| FXF | 2015-01-15 | 17.17% |

## adj_close/close ratio monotonicity

None found -- all tickers consistent.

## Dividend event counts by year (income-component sanity check)

| ticker | total div events | years w/ 0 events | years w/ >=1 event |
|---|---|---|---|
| FXE | 97 | 11 | 11 |
| FXY | 0 | 20 | 0 |
| FXA | 205 | 1 | 20 |
| FXB | 79 | 12 | 9 |
| FXC | 161 | 2 | 19 |
| FXF | 36 | 16 | 5 |
| IEF | 258 | 0 | 22 |
| TLT | 257 | 0 | 22 |
FX trusts (FXE/FXY/FXA/FXB/FXC/FXF) pay monthly income tied to the foreign deposit rate; expect years-w/-0 to cluster in the 2010-2021 near-zero-rate era.

## FRED 3m interbank rates (monthly)

| ccy | series | first | last | count | gap>1mo | last<2026-06-01 |
|---|---|---|---|---|---|---|
| USD | IR3TIB01USM156N | 1964-06-01 | 2026-06-01 | 744 | 1 | no |
| EUR | IR3TIB01EZM156N | 1994-01-01 | 2026-01-01 | 385 | 0 | YES (discontinuation risk) |
| JPY | IR3TIB01JPM156N | 2002-04-01 | 2026-05-01 | 290 | 0 | YES (discontinuation risk) |
| AUD | IR3TIB01AUM156N | 1968-01-01 | 2026-06-01 | 702 | 0 | no |
| GBP | IR3TIB01GBM156N | 1957-01-01 | 2026-01-01 | 829 | 0 | YES (discontinuation risk) |
| CAD | IR3TIB01CAM156N | 1956-01-01 | 2026-06-01 | 846 | 0 | no |
| CHF | IR3TIB01CHM156N | 1999-07-01 | 2026-06-01 | 324 | 0 | no |

- USD (IR3TIB01USM156N): dropped 1 non-numeric '.' row(s)

## FRED daily yields

| series | first | last | rows | NaN count |
|---|---|---|---|---|
| DGS10 | 1962-01-02 | 2026-09-04 | 16,874 | 719 |
| DGS20 | 1962-01-02 | 2026-09-04 | 16,874 | 2408 |
| DTB3 | 1954-01-04 | 2026-09-04 | 18,960 | 799 |

## Notes / interpretations
- Big-move threshold is |daily close return| > 8% (not adjusted close), per spec.
- Monthly rate 'gap>1mo' = any month-to-month step exceeding 45 days.
- OOS ETF split (>= 2024-07-01): 4,016 rows, 2024-07-01 .. 2026-07-01 (counts/range only, per spec).
