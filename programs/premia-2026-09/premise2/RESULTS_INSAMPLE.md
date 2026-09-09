# RESULTS_INSAMPLE.md

**VERDICT: FAIL** -- stitched walk-forward baseline net Sharpe = -0.234 (gate >= 1.0), trades = 1172 (gate >= 800).

## Step 3 -- premise test (pooled in-sample, r_rest ~ r_open, HAC-5)

| beta | t | r2 | n |
|---|---|---|---|
| 0.0801 | 2.015 | 0.005219 | 3355 |

Pass criterion (beta>0 and t>2): PASS

Descriptive add-on (m=1, N=14): mean of sign(breach)*ln(P16/open_t) over breached (d,t) = 3.639 bp (n=5660, share of evaluable (d,t) breached = 0.2819); unconditional mean |ln(P16/open_t)| over the same evaluable set = 36.975 bp.

## Step 4 -- walk-forward window table

| test_start | test_end | m | N | train_sharpe | test_sharpe | test_trades | test_net_pnl |
|---|---|---|---|---|---|---|---|
| 2013-07-01 | 2014-06-30 | 1.5 | 60 | 0.317 | 0.379 | 73 | 3841 |
| 2014-07-01 | 2015-06-30 | 1.5 | 60 | 0.55 | -0.847 | 84 | -8522 |
| 2015-07-01 | 2016-06-30 | 1.5 | 14 | 0.451 | -0.493 | 87 | -6157 |
| 2016-07-01 | 2017-06-30 | 1.5 | 30 | 0.004 | -2.175 | 83 | -2.698e+04 |
| 2017-07-01 | 2018-06-30 | 0.75 | 14 | -0.536 | 0.053 | 167 | 990.8 |
| 2018-07-01 | 2019-06-30 | 1.5 | 60 | -0.402 | -0.507 | 82 | -5320 |
| 2019-07-01 | 2020-06-30 | 1.5 | 60 | -0.093 | 0.877 | 78 | 7662 |
| 2020-07-01 | 2021-06-30 | 1.5 | 60 | 0.471 | -0.172 | 67 | -1239 |
| 2021-07-01 | 2022-06-30 | 1 | 14 | 0.374 | -0.251 | 148 | -3884 |
| 2022-07-01 | 2023-06-30 | 0.75 | 60 | 0.416 | 1.354 | 151 | 1.986e+04 |
| 2023-07-01 | 2024-06-30 | 1 | 14 | 0.888 | -0.826 | 152 | -1.335e+04 |

## Stitched metrics

Baseline (1 tick slip, $1 fee):

| sharpe | maxdd | trades | net_pnl | trades_per_day | flips_per_day | hit_rate | mean_net_per_trade | mean_hold_hours | long_sharpe | long_trades | short_sharpe | short_trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| -0.2341 | -7.244e+04 | 1172 | -3.31e+04 | 0.447 | 0.01449 | 0.5102 | -28.24 | 4.608 | -0.2603 | 615 | -0.4416 | 557 |

Stress (2 tick slip, $1 fee):

| sharpe | maxdd | trades | net_pnl | trades_per_day | flips_per_day | hit_rate | mean_net_per_trade | mean_hold_hours | long_sharpe | long_trades | short_sharpe | short_trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| -0.5842 | -1.089e+05 | 1172 | -8.304e+04 | 0.447 | 0.01449 | 0.4957 | -70.85 | 4.608 | -0.8465 | 615 | -0.9285 | 557 |

Annual net P&L by test year (baseline):

| test_year | net_pnl |
|---|---|
| 2013-2014 | 3841 |
| 2014-2015 | -8522 |
| 2015-2016 | -6157 |
| 2016-2017 | -2.698e+04 |
| 2017-2018 | 990.8 |
| 2018-2019 | -5320 |
| 2019-2020 | 7662 |
| 2020-2021 | -1239 |
| 2021-2022 | -3884 |
| 2022-2023 | 1.986e+04 |
| 2023-2024 | -1.335e+04 |

## References (context only, same stitched period)

(a) fixed m=1, N=14, no walk-forward selection:

| sharpe | maxdd | trades | net_pnl | trades_per_day | flips_per_day | hit_rate | mean_net_per_trade | mean_hold_hours | long_sharpe | long_trades | short_sharpe | short_trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| -0.2014 | -8.754e+04 | 1492 | -3.102e+04 | 0.569 | 0.02021 | 0.5168 | -20.79 | 4.607 | 0.2028 | 792 | -0.6933 | 700 |

(b) buy-and-hold ES, one log return per test window, annualised Sharpe: 0.932

## Step 5 -- matched null (2000 reps, randomised leg direction)

Actual stitched baseline Sharpe = -0.234; null mean = -0.497, null sd = 0.304; one-sided p-value (fraction of null Sharpes >= actual) = 0.1955

## Skipped-day counts (by reason, mutually exclusive, priority order below)

| no_0930_bar | no_1600_bar | prev16_missing | roll_crossing | day_after_early_close | kept | candidate_weekdays |
|---|---|---|---|---|---|---|
| 30 | 107 | 1 | 57 | 88 | 3359 | 3642 |

## Sizing stats (stitched walk-forward baseline trades)

Median contracts: 14.0; cap-binding (40 MES) frequency: 7.76%; rounded-to-zero count: 0

## Implementation choices

- sigma_t's "prior N trading days" pool is ALL candidate ET weekdays with a valid O and a valid close_t (bar n_1m>=50), independent of whether that day itself is later skipped for reasons unrelated to O/close_t (no_1600_bar, roll_crossing, day_after_early_close) -- these skips concern exit/anchor integrity, not the trustworthiness of that day's own close_t for the noise-band history.
- "instrument_id of today's bars" (roll-crossing) is read as the instrument of the earliest available hourly bar for date d (hours 9-16, back-filled), compared against the prior kept day's 16:00 bar instrument.
- An unnamed 5th skip, prev16_missing (C_prev has no valid prior 16:00 bar anywhere in history -- fires once, on the first candidate date), is added in the same spirit as premise1's Amendment-A1 precedent; not one of PREMISE_2's 4 named reasons but forced by the ffill mechanics of C_prev.
- Sizing price P in contracts=round(notional/(5*P)) is the fill price (open of bar t), i.e. sized at the actual transaction price at the flip/entry moment, per "sized at the flip time."
- A signal whose sizing rounds to zero contracts executes no leg at all (any existing position is left open unchanged); it only increments the rounded-to-zero counter -- treated as "no trade," not a flip-to-flat.
- trades_wf.csv entry_px/exit_px are raw (unadjusted) bar opens; slippage and fees are separate $ cost columns (slippage_ticks*tick*mult*2*contracts, fee_rt*contracts per leg), mirroring premise1's day-level cost convention rather than adjusting the recorded price.
- A signal with a missing fill_open (bar t open) or missing sigma_4h is treated as "no execution / hold" -- not an explicit spec case, forced by data gaps, resolved conservatively (no trade fabricated).
- Step 3's descriptive add-on (breach mean bp, count, share, unconditional mean |r|) all use the same denominator: (d,t) rows where the m=1,N=14 band is fully evaluable (close_t and sigma_t both valid), not the full 6x(kept days) row count.
- Step 5's matched null randomizes leg-level `dir` (keeping contracts/entry_px/exit_px/dates fixed) then re-aggregates to the daily series (incl. zero-net days) per rep before computing Sharpe -- adapted, not copied, from premise1's matched_null, since here the null-randomization unit (a leg) differs from the Sharpe-aggregation unit (a day).
- sigma_4h is ONE value per day d (from the [10:00,14:00) 4h bar, "known" by 14:00 ET), used to size every decision t=10..15 that day, per PREMISE_2.md/TASK.md non-negotiable #4 verbatim. This means t<14 entries are sized off same-day vol info not causally available until 14:00 -- an artifact of literally reusing P1's fixed sizing-vol timestamp, not a bug; TASK.md's no-lookahead requirement (and the prefix test) is about cross-DATE leakage, which this satisfies.

## Runtime

10.1s (data load + 9 day-frame builds + 18 simulate() calls + walk-forward + premise test + null test + I/O).
