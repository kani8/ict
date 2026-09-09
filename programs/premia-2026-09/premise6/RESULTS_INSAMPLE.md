# RESULTS_INSAMPLE.md

**VERDICT: FAIL** -- stitched net Sharpe = 0.112 (gate a: >= 0.5 -> False); TSMOM <= TSH (0.304) (gate b: False); positive test years = 6/14 (gate c: >=8 -> False); permutation p = 0.1960 (gate d: <0.05 -> False).

## Step 1 -- premise test (pooled monthly panel, x_i,t+1/sigma_i,t ~ sign(prior 252d sum), cluster by month, 38 ETFs)
| beta | t | r2 | n |
|---|---|---|---|
| 0.01094 | 1.253 | 0.001324 | 8402 |
Pass criterion (t > 2): FAIL. Per-asset-class:
| asset_class | beta | t | r2 | n |
|---|---|---|---|---|
| bonds | 0.0105 | 0.7288 | 0.001031 | 1732 |
| commodities | 0.01772 | 1.583 | 0.003369 | 1430 |
| currencies | -0.00149 | -0.1141 | 2.408e-05 | 1413 |
| equities | 0.007199 | 0.543 | 0.0005887 | 3406 |
| real_estate | -0.008436 | -0.4403 | 0.0006791 | 421 |
## Step 2 -- fixed rule (L=12, class-balanced): full span vs stitched, baseline vs stress (1.5x costs)
| sharpe | ann_return | ann_vol | maxdd_pct | avg_gross_lev | span | regime |
|---|---|---|---|---|---|---|
| 0.1052 | 0.01049 | 0.09985 | -0.4096 | 2.242 | full 2007-07..2024-06 | baseline |
| 0.06363 | 0.006351 | 0.0999 | -0.4358 | 2.242 | full 2007-07..2024-06 | stress x1.5 |
| 0.1117 | 0.01112 | 0.09963 | -0.4096 | 2.508 | stitched 2010-07..2024-06 | baseline |
| 0.066 | 0.006572 | 0.09969 | -0.4358 | 2.508 | stitched 2010-07..2024-06 | stress x1.5 |
Cap-binding share (stitched): 41.67%. Annual turnover (sum|dw|/14y, stitched): 10.290. Long vs short leg (stitched):
| leg | sharpe | total_pnl |
|---|---|---|
| long | 0.2322 | 3.338e+04 |
| short | -0.1565 | -1.782e+04 |
Per-asset-class P&L, stitched ($):
| asset_class | total_pnl |
|---|---|
| bonds | 1.49e+04 |
| commodities | 1.037e+04 |
| currencies | 325.9 |
| equities | 5111 |
| real_estate | -1.515e+04 |
P&L and Sharpe by test year, stitched ($):
| test_year | net_pnl | sharpe |
|---|---|---|
| 2010 | 19681 | 2.197 |
| 2011 | 934 | 0.08187 |
| 2012 | -1717 | -0.193 |
| 2013 | 3794 | 0.4545 |
| 2014 | 4272 | 0.4028 |
| 2015 | 4365 | 0.3892 |
| 2016 | -4864 | -0.5325 |
| 2017 | -3805 | -0.342 |
| 2018 | -8616 | -1.039 |
| 2019 | -4562 | -0.3622 |
| 2020 | -1346 | -0.1545 |
| 2021 | 14132 | 1.295 |
| 2022 | -447 | -0.04547 |
| 2023 | -6262 | -0.7803 |
## Step 3 -- benchmarks (stitched, same universe/class balance/sizing/costs)
| name | sharpe | ann_return | ann_vol | maxdd_pct | corr_vs_leg | corr_vs_SPY |
|---|---|---|---|---|---|---|
| TSMOM (fixed L=12, class-bal.) | 0.1117 | 0.01112 | 0.09963 | -0.4096 | 1 | 0.2232 |
| TSH | 0.3043 | 0.03423 | 0.1126 | -0.3599 | 0.3764 | 0.6927 |
| risk_parity | 0.1107 | 0.01328 | 0.1201 | -0.4751 | 0.3031 | 0.711 |
| 60/40 SPY-IEF | 0.9321 | 0.09166 | 0.09845 | -0.2343 | 0.2198 | 0.9649 |
| SPY B&H | 0.8479 | 0.1442 | 0.1702 | -0.3821 | 0.2232 | 1 |
Correlation of the leg's stitched daily net P&L with: premise3 = 0.6492, premise4 = n/a, premise5 = 0.1438.
## Step 4 -- sensitivity table (report only; changes nothing; L=12/class-balanced is the rule)
| L | weighting | stitched_sharpe | is_rule |
|---|---|---|---|
| 6 | class_balanced | 0.1294 | False |
| 6 | 1/N | 0.0728 | False |
| 12 | class_balanced | 0.1117 | True |
| 12 | 1/N | 0.2381 | False |
| COMBO | class_balanced | 0.1684 | False |
| COMBO | 1/N | 0.2545 | False |
## Step 5 -- permutation test (500 day-shuffle reps, full pipeline, cutoff=2007-12-19)
Real stitched Sharpe = 0.1117; null mean = -0.1047, null sd = 0.2563; one-sided p (share >= real) = 0.1960
## Step 6 -- no-lookahead test (L=12, class-balanced)
```
OK  cutoff=2009-08-19  month-ends checked=79  (of 258 full-sample)
OK  cutoff=2010-05-27  month-ends checked=88  (of 258 full-sample)
OK  cutoff=2014-07-03  month-ends checked=138  (of 258 full-sample)
OK  cutoff=2017-01-13  month-ends checked=168  (of 258 full-sample)
OK  cutoff=2021-05-05  month-ends checked=220  (of 258 full-sample)
PASS: all 5 cutoffs prefix-consistent at L=12
```
## Step 7 -- gate (report only)
(a) stitched Sharpe >= 0.5: 0.112 -> False. (b) TSMOM > TSH: 0.112 vs 0.304 -> False. (c) >=8/14 positive years: 6/14 -> False. (d) p<0.05: 0.1960 -> False. **Verdict: FAIL** (PASS requires all four).
## Implementation choices
- **Sensitivity-table count vs PREMISE_6.md:** TASK.md Step 4 specifies the full cross-product {L=6,12,COMBO} x {class-balanced,1/N} (6 cells); PREMISE_6.md's prose says "four extra numbers." The literal cross-product yields 6 cells, one of which (L=12, class-balanced) is the rule itself already reported in Step 2, leaving 5 "extra," not 4. Followed TASK.md literally (all 6 cells computed and reported; the rule cell flagged) as the more precise and directly-governing instruction; PREMISE_6.md's "four" is treated as loose prose, not a constraint on which cells to compute -- most conservative reading, changes nothing (report-only table).
- **Permutation cutoff:** "first day all 38 are listed" computed from the price panel (`px.notna().idxmax().max()`) = 2007-12-19 (EMB), analogous to P3's PERM_CUTOFF being HYG's first-listed date, not the first date of a complete *excess-return* cross-section (which would be one trading day later, since pct_change's first observation is NaN); this matches P3's own convention exactly.
- **permtest.py / test_no_lookahead.py reimplemented, not imported:** premise3/permtest.py hardcodes a 20-name PERM_CUTOFF and itself does `from strategy import ...`, which would resolve against *this premise's* strategy.py (same generic module name) if premise3/permtest.py were dynamically loaded here, silently pulling in the wrong `target_weights`/`GRID`/etc. Both files were rewritten as minimal, faithful ports of P3's logic (same day-shuffle / prefix-consistency approach), parametrised on this premise's own universe, cutoff and class-balanced weights; see strategy.py's module docstring.
- **Class-balanced weights on non-eligible-but-zero-signal instruments:** `n_c(i),t` and `C_t` are computed from eligibility only (not signal sign), so a class with eligible instruments whose signal is exactly 0 still counts toward `C_t` and dilutes other classes' share -- read directly off the PREMISE_6.md formula, which conditions the raw weight (not the class-count) on `s_i,t`.
- **60/40 and SPY B&H** are not run through the class-balance/vol-target/cap machinery (P3's convention, restated in PREMISE_6.md's benchmark section): fixed monthly target weights, same 1-day-lag execution/turnover-cost mechanics, uniform 5bp (both SPY and IEF are already 5bp in this premise's own COST_BP).
- **Cross-premise correlation:** looks for the sibling's daily net-P&L column under any of "net"/"leg_net"/"net_pnl" (each premise's own script names it differently; premise5's, produced concurrently with this run, uses "leg_net") and reports "n/a" if the file or a recognisable column is missing.
- All other conventions (EWMA vol/cov COM=60, eligibility on the 261st valid price, execution at close t+1, missing price -> prior weight, 252-day/12-month sign lookback, borrow 1%/yr /360, 5bp/10bp cost table, 3x gross cap, 10% vol target) are P3's, imported unchanged via `strategy.p3`.
- **Code budget:** TASK.md's "~200 new lines" was not met (actual: see line counts below). All core math (excess returns, EWMA vol/cov, signals/TSH, simulate/pnl_breakdown, sharpe/max_drawdown, P3's 1/N target_weights) is imported unchanged; the new code is (i) the ~35-line class-balanced weight formula itself, and (ii) orchestration/reporting for 7 TASK.md steps (premise test, full+stitched fixed-rule sim, 4 benchmarks, a 6-cell sensitivity grid, permutation test, no-lookahead test, cross-premise correlations, gate) that could not be imported from premise3/walkforward.py as-is because its helpers close over P3's own hardcoded 20-name UNIVERSE/ASSET_CLASS globals and it self-imports a module literally named "strategy" (which would resolve to this premise's own file, not P3's, if dynamically loaded here -- see strategy.py's docstring). Most of the excess line count is one-line-per-table-row report plumbing, not new strategy logic.
## Runtime
29.5s total (data load, premise test, fixed-rule sim x2 cost regimes, benchmarks x4, 6-cell sensitivity grid, 500-rep permutation test, no-lookahead test, I/O).
