# RESULTS_INSAMPLE.md

**VERDICT: FAIL** -- stitched net Sharpe (1 tick) = 0.418 (gate a >= 0.5: False); timed <= always-short Sharpe (0.492) (gate b: False); positive test years = 9/14 (gate c >= 8: True); permutation p = 0.2740 (gate d < 0.05: False).

## Step 1 -- premise test (roll_t -> next-day held-contract return, NW-5 lags; span 2004-06-23..2024-06-28)
| beta | t | r2 | n |
|---|---|---|---|
| -0.4961 | -2.581 | 0.002992 | 5022 |
Pass (daily t < -2): PASS. 21-day-forward (overlapping, NW-21):
| beta | t | r2 | n |
|---|---|---|---|
| -7.197 | -1.751 | 0.02113 | 5020 |
Contango half (roll>0) / backwardation half (roll<0), daily NW-5:
| beta | t | r2 | n | half |
|---|---|---|---|---|
| -0.1556 | -0.7934 | 0.0001338 | 4090 | contango |
| -1.448 | -3.641 | 0.01337 | 926 | backwardation |

## Step 2 -- fixed rule (theta=0.0050), full span 2004-06-23..2024-06-28
| sharpe | ann_return | ann_vol | maxdd_pct | worst_day_pct | time_in_mkt |
|---|---|---|---|---|---|
| 0.5027 | 0.03597 | 0.07186 | -0.2068 | -0.08435 | 0.5414 |
trades/yr = 20.49. Roll-cost share of total cost = 37.19%.

## Step 3 -- stitched calendar 2010-07-01..2024-06-30
Baseline (1 tick) vs stress (2 ticks):
| sharpe | ann_return | ann_vol | maxdd_pct | worst_day_pct | time_in_mkt | regime |
|---|---|---|---|---|---|---|
| 0.4185 | 0.02968 | 0.07133 | -0.2068 | -0.05121 | 0.6088 | 1 tick |
| 0.2028 | 0.01442 | 0.07152 | -0.2577 | -0.05121 | 0.6088 | 2 ticks |
Cap-binding share of days: 0.0000% (expect 0). Long vs short leg:
| leg | sharpe | total_pnl |
|---|---|---|
| long | 0.2422 | 1.134e+04 |
| short | 0.4125 | 3.624e+04 |
P&L and Sharpe by test year (Jul->Jun):
| test_year | net_pnl | sharpe |
|---|---|---|
| 2010-2011 | 9292 | 1.453 |
| 2011-2012 | 1.447e+04 | 1.551 |
| 2012-2013 | 6690 | 1.104 |
| 2013-2014 | 9872 | 1.461 |
| 2014-2015 | -2011 | -0.2796 |
| 2015-2016 | 1133 | 0.1318 |
| 2016-2017 | 9986 | 1.458 |
| 2017-2018 | 869.4 | 0.1472 |
| 2018-2019 | -6671 | -1.214 |
| 2019-2020 | 9205 | 1.051 |
| 2020-2021 | -1079 | -0.1459 |
| 2021-2022 | -1.492e+04 | -1.716 |
| 2022-2023 | 6231 | 1.41 |
| 2023-2024 | -1540 | -0.2789 |

## Step 4 -- benchmarks (same stitched calendar, sizing, costs, rolls)
| name | sharpe | ann_return | maxdd_pct | worst_day_pct |
|---|---|---|---|---|
| timed (theta=0.0050) | 0.4185 | 0.02968 | -0.2068 | -0.05121 |
| always-short | 0.4918 | 0.05561 | -0.3708 | -0.1964 |
| always-long | -0.6853 | -0.07747 | -1.087 | -0.05031 |
| SPY B&H | 0.8939 | 0.152 | -0.3816 | -0.1094 |
corr(timed daily net $, SPY daily $) = 0.121. corr(timed, premise3 stitched net $) = 0.178 (n=3522 overlapping days).

## Step 5 -- sensitivity table (theta grid; full sensitivity.csv has per-test-year columns too)
| theta | fixed_choice | full_span_sharpe | stitched_sharpe |
|---|---|---|---|
| 0 | False | 0.3693 | 0.2958 |
| 0.0025 | False | 0.4077 | 0.3643 |
| 0.005 | True | 0.5027 | 0.4185 |
| 0.0075 | False | 0.5151 | 0.4892 |
This table changes nothing (theta = 0.0050 is fixed regardless of rank here).

## Step 6 -- permutation test (500 reps, seed=42, stitched calendar)
Real Sharpe = 0.4185, null mean = 0.2993, null sd = 0.2175, p (share >= real) = 0.2740

## Step 7 -- no-lookahead test (theta = 0.0050)
```
OK  cutoff=2009-12-30  rows checked=1452  (of 5116 full-sample)
OK  cutoff=2010-10-04  rows checked=1643  (of 5116 full-sample)
OK  cutoff=2014-10-20  rows checked=2661  (of 5116 full-sample)
OK  cutoff=2017-04-21  rows checked=3291  (of 5116 full-sample)
OK  cutoff=2021-07-22  rows checked=4361  (of 5116 full-sample)
PASS: all 5 cutoffs prefix-consistent at theta=0.005
```
## Implementation choices
- vix_spot.parquet is read and guarded (Hard Rule 1) and cross-checked equal to vx_daily's own `vix_close` on every overlapping date (0 mismatches) then not reused: `held_series(vx_daily, contracts)`'s signature (per TASK.md) takes no vix_spot argument, and vx_daily.vix_close IS spot VIX close.
- ret_next(t) is looked up in `vx_contracts` at (t+1, held_expiry(t)), not vx_daily's own f1/f2 columns at t+1 -- on a roll day the outgoing contract is no longer f1 or f2 the next day, so only the raw per-expiry contracts table has its price.
- **EWMA sigma lookahead fix**: sigma_t must use only returns realized by t. Since `ret_next` is indexed by its START date (t -> t+1, per the held-series spec), sigma_t = EWMA(ret_next.shift(1)) -- using ret_next unshifted would leak t+1's settle into the weight decided at t. Caught by design intent of the no-lookahead test.
- Roll-day cost: `simulate()`'s signature is extended with a `roll_day` flag beyond TASK.md's suggested (weights,ret,F,ticks) -- required to distinguish "close+reopen full notional" (roll day) from "trade |Delta notional|" (normal day); TASK.md's own cost description needs this flag, its suggested signature just omitted it. Both legs of a roll are costed at the post-roll contract's own settle (F_t), a simplification since the spec gives one F_t, not separate outgoing/incoming prices.
- 21-day-forward regression: NaN (no-VX-settle) days' return treated as 0 for compounding only (~35/5116 rows); the daily regression and P&L never do this (NaN stays NaN, position carried, per VALIDATION.md).
- "First valid date" = the date by which >=60 non-null ret_next have accumulated since inception (2004-03-26); used as the start of the full-span reporting window (Steps 1-2) and the sensitivity table's full-span column. The state machine/EWMA itself runs continuously from inception (no truncation upstream) -- only the reporting window is trimmed.
- Time-in-market uses the 2-day-lagged active position (what is actually earning that day's P&L), not the raw same-day decided `pos`. Trades/yr = count of days `pos` changes (entry/exit/flip), divided by span years.
- Always-short/-long benchmarks are constant s_t in {-1,+1} with no state machine or NaN-carry logic (trivial by construction); same sizing/cost/roll machinery otherwise. SPY B&H is a pure 100%-weight daily-return series, no cost (context only, per spec).
## Runtime
0.7s total (data load+guards, held-series build, premise regressions, fixed-rule full-span + stitched (2 cost regimes), benchmarks, 4-theta sensitivity, 500-rep permutation, no-lookahead test, I/O).
