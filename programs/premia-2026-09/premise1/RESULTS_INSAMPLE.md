# RESULTS_INSAMPLE.md

**VERDICT: FAIL** -- stitched walk-forward baseline net Sharpe = -0.406 (gate >= 1.0), trades = 1101 (gate >= 800).

## Step 3 -- premise test (pooled in-sample, r_trade ~ r_sofar, HAC-5)

| beta | t | r2 | n |
|---|---|---|---|
| 0.03384 | 2.057 | 0.007651 | 3358 |

Pass criterion (beta>0 and t>2): PASS

Terciles of |z| (L=30, descriptive):

| tercile | beta | t | r2 | n |
|---|---|---|---|---|
| low | 0.09589 | 1.354 | 0.003678 | 1118 |
| mid | 0.0675 | 1.316 | 0.01157 | 1118 |
| high | 0.02543 | 1.74 | 0.01093 | 1118 |

Always-long mean r_trade (context): -0.000043

## Step 4 -- walk-forward window table

| test_start | test_end | k | L | train_sharpe | test_sharpe | test_trades | test_net_pnl |
|---|---|---|---|---|---|---|---|
| 2013-07-01 | 2014-06-30 | 1 | 30 | -0.505 | -0.347 | 68 | -1998 |
| 2014-07-01 | 2015-06-30 | 0.75 | 60 | 0.062 | -0.497 | 97 | -4462 |
| 2015-07-01 | 2016-06-30 | 0.75 | 18 | 0.004 | -0.567 | 117 | -6842 |
| 2016-07-01 | 2017-06-30 | 0.75 | 18 | -0.347 | -3.155 | 97 | -2.381e+04 |
| 2017-07-01 | 2018-06-30 | 1 | 30 | -1.046 | -0.173 | 73 | -2145 |
| 2018-07-01 | 2019-06-30 | 1 | 18 | -0.546 | -0.436 | 77 | -4918 |
| 2019-07-01 | 2020-06-30 | 1 | 60 | -0.412 | -0.884 | 77 | -1.048e+04 |
| 2020-07-01 | 2021-06-30 | 0.75 | 60 | -0.263 | -2.446 | 94 | -3.295e+04 |
| 2021-07-01 | 2022-06-30 | 0.5 | 60 | -0.827 | 0.932 | 140 | 1.87e+04 |
| 2022-07-01 | 2023-06-30 | 0.5 | 30 | -0.032 | 1.577 | 130 | 2.391e+04 |
| 2023-07-01 | 2024-06-30 | 0.5 | 30 | 0.378 | -0.742 | 131 | -1.325e+04 |

## Stitched metrics

Baseline (1 tick slip, $1 fee):

| sharpe | maxdd | trades | net_pnl | hit_rate | mean_net_per_trade | mean_abs_z_traded | long_sharpe | long_trades | short_sharpe | short_trades |
|---|---|---|---|---|---|---|---|---|---|---|
| -0.4058 | -1.093e+05 | 1101 | -5.826e+04 | 0.4423 | -52.91 | 1.371 | -0.3761 | 622 | -0.8704 | 479 |

Stress (2 tick slip, $1 fee):

| sharpe | maxdd | trades | net_pnl | hit_rate | mean_net_per_trade | mean_abs_z_traded | long_sharpe | long_trades | short_sharpe | short_trades |
|---|---|---|---|---|---|---|---|---|---|---|
| -0.9586 | -1.661e+05 | 1101 | -1.381e+05 | 0.4196 | -125.4 | 1.371 | -1.436 | 622 | -1.572 | 479 |

Annual net P&L by test year (baseline):

| test_year | net_pnl |
|---|---|
| 2013-2014 | -1998 |
| 2014-2015 | -4462 |
| 2015-2016 | -6842 |
| 2016-2017 | -2.381e+04 |
| 2017-2018 | -2145 |
| 2018-2019 | -4918 |
| 2019-2020 | -1.048e+04 |
| 2020-2021 | -3.295e+04 |
| 2021-2022 | 1.87e+04 |
| 2022-2023 | 2.391e+04 |
| 2023-2024 | -1.325e+04 |

## References (context only, same stitched period)

(a) fixed k=0, L=30, no walk-forward selection:

| sharpe | maxdd | trades | net_pnl | hit_rate | mean_net_per_trade | mean_abs_z_traded | long_sharpe | long_trades | short_sharpe | short_trades |
|---|---|---|---|---|---|---|---|---|---|---|
| -0.8745 | -2.245e+05 | 2609 | -1.703e+05 | 0.4511 | -65.26 | 0.7842 | -1.324 | 1445 | -0.4016 | 1164 |

(b) buy-and-hold ES, one log return per test window, annualised Sharpe: 0.932

## Step 5 -- matched null (2000 reps, randomised trade direction)

Actual stitched baseline Sharpe = -0.406; null mean = -0.767, null sd = 0.312; one-sided p-value (fraction of null Sharpes >= actual) = 0.1260

## Skipped-day counts (by reason, mutually exclusive, priority order below)

| p15_missing_or_thin | p16_missing | prev16_missing | roll_crossing | day_after_early_close | kept | candidate_weekdays |
|---|---|---|---|---|---|---|
| 138 | 0 | 1 | 57 | 88 | 3358 | 3642 |

## Sizing stats (stitched walk-forward baseline trades)

Median contracts: 31.0; cap-binding (40 MES) frequency: 37.78%; rounded-to-zero count: 0

## Implementation choices

- sigma_day = sigma_4h * sqrt(5.5) used literally as the fixed constant given in the spec (not the 'actual count of 4h bars' alternative PREMISE_1.md offers as an option).
- Skip reasons are made mutually exclusive by checking in this priority order so counts sum exactly to the candidate-weekday count: p15_missing_or_thin, p16_missing, prev16_missing, roll_crossing, day_after_early_close.
- Rows with insufficient 4h history for L (sigma_4h NaN) are NOT counted as a skipped day: the daily-table row is kept (r_sofar/r_trade are still valid), z is NaN, and dir/contracts resolve to 0/no-trade, contributing a legitimate zero-P&L day to Sharpe -- consistent with 'Sharpe over the full daily series including zero days'.
- Amendment A1(ii) ('day after an early close') is implemented exactly as the mechanical rule in TASK.md (prior weekday has a 9-12 ET bar but no 16:00 bar), with no day-of-week or holiday special-casing; this also fires after full-closure holidays with a partial overnight Globex print (e.g. Thanksgiving), not just classic 13:00 half-days -- see report notes.
- Buy-and-hold reference per window = ln(P16 of the window's last kept date / P_prev16 of the window's first kept date) -- the most literal close-to-close return spanning exactly the test window (using the same 16:00 cash-close convention as the rest of the strategy).
- Walk-forward (k,L) is selected once per window using the baseline daily table build/cost; the stress-cost stitched result reruns pnl() with slippage_ticks=2 on the SAME selected (k,L) and SAME dir/contracts per window (costs are not part of selection).
- Matched-null p-value is reported as the raw fraction of 2000 null Sharpes >= actual, with no add-one continuity correction (not specified in the task).
- ICT repo's matched_baseline_test/random_baseline_test were not reused: their interface is built around ict_backtest.engine Candles/Backtester/BacktestResult objects and a stop/target trade-template null, which does not fit this two-fills-per-trade, direction-only vectorised strategy; step 5 is instead ~15 lines of numpy directly on the stitched pnl frame.
- hit_rate, mean_net_per_trade, mean_abs_z_traded and long/short Sharpe are diagnostic sub-statistics computed over trade days only for that subset (not zero-padded); long/short Sharpe still uses the same mean/std*sqrt(252) annualisation as the full-series headline Sharpe, for comparability, even though trade days are a sparser, irregular subset of the calendar.

## Runtime

1.2s (data load + 15 daily-table builds + full walk-forward + premise test + null test + I/O).
