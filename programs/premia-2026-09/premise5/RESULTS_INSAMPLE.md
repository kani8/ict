# RESULTS_INSAMPLE.md

**VERDICT: FAIL** -- stitched leg net Sharpe = 0.076 (gate a >= 0.5: False); leg > leg-no-signal Sharpe (-0.119) (gate b: True); positive test years = 7/14 (gate c >=8: False); permutation p=0.4540 (gate d <0.05: False). FX variant fixed at XS (Amendment A1); TS/BOTH below are sensitivity-only.

## Step 1 -- premise test
FX pooled monthly panel (x_i,t+1/sigma_i,t ~ carry_i,t, %-pts, cluster by month):
| beta | t | r2 | n |
|---|---|---|---|
| -0.007009 | -0.9301 | 0.001477 | 1294 |
Bonds (x_j,t+1/sigma_j,t ~ y_j,t-bill_t, per ETF, Newey-West 3 lags):
| etf | beta | t | r2 | n |
|---|---|---|---|---|
| IEF | 0.02499 | 1.604 | 0.01065 | 233 |
| TLT | 0.0207 | 1.448 | 0.01008 | 233 |
Pass (FX t>2 AND IEF t>2): FAIL
## Step 2 -- fixed rule, full span (2007-02-28..2024-06-28)
| sleeve | sharpe | ann_return | ann_vol | maxdd_pct | avg_gross_lev |
|---|---|---|---|---|---|
| leg | 0.1333 | 0.00822 | 0.06173 | -0.2411 | 1.872 |
| FX sleeve | -0.1873 | -0.01943 | 0.1038 | -0.7871 | 2.462 |
| bond sleeve | 0.3547 | 0.03587 | 0.1012 | -0.3575 | 1.282 |
FX annual turnover: 2.568; bond annual turnover: 2.899. Cap-binding %: FX 37.80%, bonds 4.31%.
Missing-rate rate (share of FX-name-months): still-missing (weight 0) = 0.000%, used carry-forward = 0.478%.
## Step 3 -- stitched calendar (2010-07-01..2024-06-30)
Leg, baseline vs 1.5x costs:
| regime | sharpe | ann_return | ann_vol | maxdd_pct | avg_gross_lev |
|---|---|---|---|---|---|
| baseline | 0.07598 | 0.00466 | 0.0614 | -0.2411 | 1.943 |
| stress x1.5 | 0.06254 | 0.003836 | 0.06141 | -0.2503 | 1.943 |
Sleeve Sharpes (stitched):
| sleeve | sharpe | total_pnl |
|---|---|---|
| FX sleeve | -0.1325 | -1.838e+04 |
| bond sleeve | 0.225 | 3.142e+04 |
FX annual turnover: 2.152; bond annual turnover: 2.282. Cap-binding %: FX 41.67%, bonds 3.57%.
FX long vs short contribution:
| leg | sharpe | total_pnl |
|---|---|---|
| FX long | -0.3093 | -4.241e+04 |
| FX short | 0.1703 | 2.403e+04 |
P&L and Sharpe by test year:
| test_year | net_pnl | sharpe |
|---|---|---|
| 2010 | 3300 | 0.69 |
| 2011 | 9996 | 1.995 |
| 2012 | -7926 | -1.299 |
| 2013 | 1616 | 0.292 |
| 2014 | -92 | -0.01 |
| 2015 | 4026 | 0.747 |
| 2016 | -4219 | -0.721 |
| 2017 | -2978 | -0.49 |
| 2018 | 5140 | 0.926 |
| 2019 | -2576 | -0.382 |
| 2020 | 1371 | 0.283 |
| 2021 | -7424 | -1.246 |
| 2022 | -1486 | -0.204 |
| 2023 | 7772 | 1.164 |
Missing-rate rate (stitched): still-missing = 0.000%, used carry-forward = 0.595%.
## Step 4 -- benchmarks (stitched calendar)
| name | sharpe | ann_return | ann_vol | maxdd_pct | corr_vs_leg |
|---|---|---|---|---|---|
| leg (XS, fixed) | 0.07598 | 0.00466 | 0.0614 | -0.2411 | 1 |
| FX no-signal (eq-wt long 6) | -0.4446 | -0.04675 | 0.1053 | -0.9208 | 0.05034 |
| bond no-signal (always long) | 0.2612 | 0.02746 | 0.1053 | -0.4048 | 0.3576 |
| leg no-signal | -0.1195 | -0.009643 | 0.08081 | -0.3668 | 0.2657 |
| SPY B&H | 0.8479 | 0.1442 | 0.1702 | -0.3821 | 0.1404 |
Additional correlations of the leg with: premise3 (daily_pnl_wf.csv)=0.0901, premise4 (daily_pnl.csv)=n/a.
## Step 5 -- sensitivity (FX variant; XS is the fixed rule, TS/BOTH sensitivity-only, changes nothing)
| variant | full_span_sharpe | stitched_sharpe |
|---|---|---|
| XS (fixed) | 0.1333 | 0.07598 |
| TS | -0.005656 | 0.0499 |
| BOTH | 0.08755 | 0.09736 |
Per-test-year leg Sharpe by variant:
| test_year | XS | TS | BOTH |
|---|---|---|---|
| 2010 | 0.69 | 1.018 | 0.95 |
| 2011 | 1.995 | 2.112 | 2.141 |
| 2012 | -1.299 | -1.502 | -1.594 |
| 2013 | 0.292 | 0.791 | 0.62 |
| 2014 | -0.01 | -1.102 | -0.706 |
| 2015 | 0.747 | -0.617 | 0.099 |
| 2016 | -0.721 | -0.63 | -0.582 |
| 2017 | -0.49 | -0.524 | -0.433 |
| 2018 | 0.926 | 1.317 | 1.248 |
| 2019 | -0.382 | 0.739 | 0.232 |
| 2020 | 0.283 | -1.192 | -0.499 |
| 2021 | -1.246 | 0.36 | -0.167 |
| 2022 | -0.204 | -0.146 | -0.124 |
| 2023 | 1.164 | 0.645 | 0.934 |
## Step 6 -- permutation test (500 reps, exogenous-signal scheme, stitched calendar)
Real Sharpe = 0.0760; null mean = 0.0623, null sd = 0.1884; p (share >= real) = 0.4540
## Step 7 -- no-lookahead test
```
OK  cutoff=2011-09-02  month-ends checked=80  (of 234 full-sample)
OK  cutoff=2012-05-02  month-ends checked=88  (of 234 full-sample)
OK  cutoff=2015-11-12  month-ends checked=130  (of 234 full-sample)
OK  cutoff=2018-01-19  month-ends checked=156  (of 234 full-sample)
OK  cutoff=2021-10-05  month-ends checked=201  (of 234 full-sample)
PASS: all 5 cutoffs prefix-consistent (FX-XS + bond sleeve weights)
```
## Implementation choices
- Step 1 premise-test panel spans each instrument's OWN available history (sigma_i,t is NaN, so dropna() excludes, before that name's own first listed price), not the all-8-simultaneously-eligible FULLSPAN_START used for Steps 2/3's leg reporting -- more data-inclusive, and the same per-instrument-eligibility convention premise3 used for its pooled panel. FX panel N=1294 = ~216 avg eligible months/currency x 6; bond N=233 (IEF/TLT both trade since 2005-01, so ~all 234 month-ends minus the final month's shift(-1) edge).
- Eligibility ("first month-end with all 8 instruments eligible"): purely price-listing based (no P3-style N-day warm-up threshold -- PREMISE_5.md defines none); FULLSPAN_START = 2007-02-28 (the month-end after FXY, the last-listed name, appears on 2007-02-13). Pre-FULLSPAN_START month-ends (2005-01..2007-01) still get FX rank/sign weights computed (carry only needs rate data, which predates every ETF listing) but the resulting sizing lambda is NaN whenever the 6x6 FX covariance sub-block is not yet fully populated (not all 6 names trading); verified this never leaks into the reported span -- `simulate()`'s skipna sum silently drops the untradable pre-listing contribution and by FULLSPAN_START itself the covariance block is fully populated (0 NaNs in leg_net from FULLSPAN_START onward, checked directly).
- Missing-rate rule (Amendment A2): implemented as carry-forward per currency (incl. USD) on a monthly grid, `ffill(limit=6)`; a currency's rate is "still missing" only if no observation exists within the trailing 6 months. carry_i(t) is NaN (-> weight 0 that FX name that month, via the `avail` mask in `fx_weights`) if EITHER the foreign or the USD rate is still-missing at lag month m-1 (USD is common to all six carries, so a USD gap zeroes every FX name that month). In-sample this triggers exactly once: USD's one gap>1mo (2020-04, per VALIDATION.md) is recovered by the 6-month carry-forward, so it is a "used carry-forward" event, never a "still-missing" (weight-0) event, for all six names simultaneously -- see the Step 3 line below.
- XS with missing names generalises `rank(carry)-3.5` to `rank(carry)-(n_avail+1)/2` over the currencies with a defined carry that month (reduces to the literal formula when all 6 are available, which is true for all but the one recovered-via-carry-forward month above); Sigma|w|=1 renormalised over the available subset. TS keeps the spec's fixed `/6` denominator (no renormalisation) per the literal formula; a zeroed name simply reduces TS's gross that month. BOTH always renormalises to Sigma|w|=1 after averaging. Since missing-rate events are (documented above) never a weight-0 event in-sample, none of this generalisation is actually exercised on live signal values in-sample.
- Leg = 1/2 x FX-sleeve $P&L + 1/2 x bond-sleeve $P&L, each sleeve run through its own independent EWMA-covariance lambda scaling (its own 6x6 or 2x2 sub-block of the joint 8x8 EWMA covariance) and its own 3x gross cap, each simulated on a $100k book with its own turnover/borrow costs -- mathematically identical to a single simulate() call on the concatenated (0.5x FX w, 0.5x bond w) weight matrix on one $100k book, since turnover cost, borrow cost and gross P&L are all linear in weights. Leg avg gross leverage / annual turnover reported as the same 1/2-1/2 combination; the leg itself is not re-capped after combination (only each sleeve is), so "cap-binding %" is reported per sleeve, not for the leg row.
- Bond premise test: per-ETF simple time series (not pooled/clustered) of `x_j,t+1/sigma_j,t` on the raw spread `y_j,t - bill_t` (not its sign), Newey-West 3 lags, per PREMISE_5.md Step 1 wording; gate uses IEF only (TLT reported alongside).
- FX/bond no-signal benchmarks use the SAME EWMA covariance (from the realised 8-instrument excess-return panel) and the same 3x cap machinery as the timed sleeves; SPY B&H uses a fixed weight of 1.0, 5bp cost, run through the same 1-day-lag `simulate()` for internal consistency (mirrors the P3/P4 SPY benchmark convention).
- Permutation test (Step 6): only the daily excess-return matrix is shuffled (dates >= 2007-02-13, the first day all 8 names are listed); the FX rank weights (`fx_raw`, a function of carry only) are literally invariant to the permutation and computed once; the bond sleeve's per-instrument 0.40/sigma scaling depends on EWMA vol, so sigma/cov and the bond raw weights ARE recomputed on each permuted panel, exactly as PREMISE_5.md's "recompute vol/cov, weights, costs, P&L" specifies.
- Correlation vs premise3/premise4: premise3's `daily_pnl_wf.csv` is present and used; premise4 has not been run yet in this workspace (`/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH/premise4/daily_pnl.csv` does not exist), so that correlation is reported as "not available" rather than fabricated.
## Runtime
6.0s total (data load, premise test, full-span + stitched fixed-rule leg, benchmarks, 500-rep permutation test, sensitivity table, no-lookahead test, I/O).
