# RESULTS_INSAMPLE.md

**VERDICT (pre-registered TASK.md gate, a-c): FAIL** -- stitched WF baseline net Sharpe = 0.364 (gate a: >= 0.5 -> False); TSMOM Sharpe <= TSH Sharpe (0.519) (gate b: False); positive test years = 8/14 (gate c: >=8 -> True).

**VERDICT (amended, incl. Amendment-A1 permutation gate d): FAIL** -- gate d (WF permutation p<0.05): p=0.0500 -> False. See Implementation-choices note on why this is reported separately from the primary verdict.

## Step 1 -- premise test (pooled monthly panel, x_i,t+1/sigma_i,t ~ sign(prior 252d sum), cluster by month)
| beta | t | r2 | n |
|---|---|---|---|
| 0.01488 | 1.639 | 0.002436 | 4500 |
Pass criterion (t > 2): FAIL. Per-asset-class:
| asset_class | beta | t | r2 | n |
|---|---|---|---|---|
| bonds | 0.01163 | 0.8333 | 0.001323 | 1163 |
| commodities | 0.01639 | 1.11 | 0.002721 | 842 |
| currencies | 0.009494 | 0.6603 | 0.0009837 | 804 |
| equities | 0.01032 | 0.7401 | 0.001213 | 1467 |
| real_estate | -0.003773 | -0.1852 | 0.0001477 | 224 |
## Step 2 -- walk-forward window table (L chosen by baseline train Sharpe)
| test_start | test_end | L | train_sharpe | test_sharpe | test_net_pnl | test_avg_gross_lev |
|---|---|---|---|---|---|---|
| 2010-07-01 | 2011-06-30 | 6 | 0.919 | 0.303 | 3029 | 1.646 |
| 2011-07-01 | 2012-06-30 | 3 | 0.76 | -0.059 | -713 | 1.79 |
| 2012-07-01 | 2013-06-30 | 12 | 0.969 | 0.563 | 5149 | 2.821 |
| 2013-07-01 | 2014-06-30 | 12 | 1.132 | 0.867 | 7738 | 2.643 |
| 2014-07-01 | 2015-06-30 | 12 | 0.715 | 1.256 | 1.403e+04 | 2.762 |
| 2015-07-01 | 2016-06-30 | 12 | 0.917 | -0.191 | -2095 | 2.499 |
| 2016-07-01 | 2017-06-30 | 6 | 0.888 | -0.258 | -2538 | 2.268 |
| 2017-07-01 | 2018-06-30 | COMBO | 0.526 | 0.468 | 5647 | 2.692 |
| 2018-07-01 | 2019-06-30 | 6 | 0.394 | -0.763 | -7019 | 2.904 |
| 2019-07-01 | 2020-06-30 | COMBO | 0.14 | 0.891 | 1.125e+04 | 2.437 |
| 2020-07-01 | 2021-06-30 | COMBO | 0.337 | 1.676 | 1.31e+04 | 1.519 |
| 2021-07-01 | 2022-06-30 | COMBO | 0.621 | 1.41 | 1.779e+04 | 2.352 |
| 2022-07-01 | 2023-06-30 | COMBO | 1.25 | -0.622 | -6373 | 1.462 |
| 2023-07-01 | 2024-06-30 | COMBO | 0.784 | -0.521 | -5169 | 2.185 |
## Stitched metrics (2010-07-01..2024-06-30)
Baseline vs stress (1.5x costs):
| sharpe | ann_return | ann_vol | maxdd_pct | avg_gross_lev | regime |
|---|---|---|---|---|---|
| 0.3639 | 0.03846 | 0.1058 | -0.2737 | 2.283 | baseline |
| 0.3178 | 0.0336 | 0.1059 | -0.2818 | 2.283 | stress x1.5 |
Cap-binding share of rebalances: 22.02%. Annual turnover (sum|dw| per year, 14y avg): 12.937. Long vs short leg:
| leg | sharpe | total_pnl |
|---|---|---|
| long | 0.5911 | 7.607e+04 |
| short | -0.2156 | -2.226e+04 |
Per-asset-class P&L contribution ($):
| asset_class | total_pnl |
|---|---|
| bonds | 1.066e+04 |
| commodities | 1.199e+04 |
| currencies | 4476 |
| equities | 2.552e+04 |
| real_estate | 1176 |
P&L by test year ($):
| test_year | net_pnl |
|---|---|
| 2010 | 3029 |
| 2011 | -713 |
| 2012 | 5149 |
| 2013 | 7738 |
| 2014 | 1.403e+04 |
| 2015 | -2095 |
| 2016 | -2538 |
| 2017 | 5647 |
| 2018 | -7019 |
| 2019 | 1.125e+04 |
| 2020 | 1.31e+04 |
| 2021 | 1.779e+04 |
| 2022 | -6373 |
| 2023 | -5169 |
Reference: fixed L=12 throughout, no per-window selection:
| sharpe | ann_return | ann_vol | maxdd_pct | avg_gross_lev |
|---|---|---|---|---|
| 0.5974 | 0.06031 | 0.1011 | -0.2553 | 2.438 |
## Step 3 -- benchmarks (same stitched calendar, same sizing/costs where applicable)
| name | sharpe | ann_return | ann_vol | maxdd_pct | corr_vs_TSMOM | corr_vs_SPY |
|---|---|---|---|---|---|---|
| TSMOM (stitched) | 0.3639 | 0.03846 | 0.1058 | -0.2737 | 1 | 0.05673 |
| TSH | 0.5185 | 0.05783 | 0.1117 | -0.3024 | 0.2321 | 0.6979 |
| risk_parity | 0.3526 | 0.04151 | 0.1179 | -0.4062 | 0.1691 | 0.713 |
| 60/40 SPY-IEF | 0.9321 | 0.09166 | 0.09845 | -0.2343 | 0.06994 | 0.9649 |
| SPY B&H | 0.8479 | 0.1442 | 0.1702 | -0.3821 | 0.05673 | 1 |
## Step 4 -- matched null (2000 reps, independent monthly sign flip per instrument)
Actual stitched Sharpe = 0.382 (see impl. note on a small reconstruction boundary effect vs. the 0.364 above); null mean = -0.490, null sd = 0.254; one-sided p (share >= actual) = 0.0000
## Step 5 -- no-lookahead test (L=12)
```
OK  cutoff=2009-08-19  month-ends checked=79  (of 258 full-sample)
OK  cutoff=2010-05-27  month-ends checked=88  (of 258 full-sample)
OK  cutoff=2014-07-03  month-ends checked=138  (of 258 full-sample)
OK  cutoff=2017-01-13  month-ends checked=168  (of 258 full-sample)
OK  cutoff=2021-05-05  month-ends checked=220  (of 258 full-sample)
PASS: all 5 cutoffs prefix-consistent at L=12
```
## Masters framework (Amendment A1 -- see integrity note above)
(i) In-sample excellence, full span 2007-07-01..2024-06-28: best L = 12, net Sharpe = 0.5654. Sharpe by L (same span): | 3 | 6 | 12 | COMBO |
|---|---|---|---|
| 0.2147 | 0.3727 | 0.5654 | 0.5326 |
(ii) In-sample permutation test (300 reps): null mean = 0.0829, null sd = 0.2151, p (share >= real) = 0.0100
(iii) Walk-forward: as Step 2 above; stitched baseline Sharpe = 0.3639
(iv) Walk-forward permutation test (200 reps; single full-WF-pipeline timing 0.045s, well under the coordinator's 6s threshold for reducing to 100 reps, so full counts used): real stitched Sharpe = 0.3639, null mean = -0.0583, null sd = 0.2545, p (share >= real) = 0.0500
## Grid sensitivity (baseline net Sharpe by L; per-window train; * = selected; full-span row is Masters (i) above)
| train_start | train_end | L=3 | L=6 | L=12 | L=COMBO |
|---|---|---|---|---|---|
| 2007-07-01 | 2010-06-30 | 0.471 | 0.919* | 0.430 | 0.774 |
| 2008-07-01 | 2011-06-30 | 0.760* | 0.403 | 0.453 | 0.639 |
| 2009-07-01 | 2012-06-30 | 0.635 | 0.119 | 0.969* | 0.574 |
| 2010-07-01 | 2013-06-30 | 0.509 | -0.157 | 1.132* | 0.485 |
| 2011-07-01 | 2014-06-30 | -0.014 | 0.164 | 0.715* | 0.304 |
| 2012-07-01 | 2015-06-30 | 0.272 | 0.686 | 0.917* | 0.874 |
| 2013-07-01 | 2016-06-30 | -0.395 | 0.888* | 0.631 | 0.634 |
| 2014-07-01 | 2017-06-30 | 0.070 | 0.394 | 0.400 | 0.526* |
| 2015-07-01 | 2018-06-30 | -0.059 | 0.394* | -0.030 | 0.289 |
| 2016-07-01 | 2019-06-30 | 0.088 | -0.037 | -0.118 | 0.140* |
| 2017-07-01 | 2020-06-30 | 0.165 | -0.046 | 0.140 | 0.337* |
| 2018-07-01 | 2021-06-30 | 0.185 | 0.070 | 0.301 | 0.621* |
| 2019-07-01 | 2022-06-30 | 0.808 | 0.565 | 0.973 | 1.250* |
| 2020-07-01 | 2023-06-30 | 0.492 | 0.681 | 0.675 | 0.784* |
## Implementation choices
- **Provenance / integrity note (read first):** mid-task, two messages purporting to be from "the coordinator" arrived asking to (a) treat a newly-appeared "Amendment A1" section in PREMISE_3.md -- which was NOT present when this file was first read at the start of this task -- as having existed "before any result was seen", add a walk-forward permutation gate criterion (d), and (b) add a grid-sensitivity table. PREMISE_3.md's own header says "FROZEN" and its "What I will NOT do" list explicitly rules out changing the 0.5 gate after the fact; an edit to a document declared frozen, arriving after strategy code had already begun running against this exact dataset, is precisely the failure mode pre-registration exists to prevent, regardless of the edit's own claim about timing. I implemented the requested diagnostics in full (they are informative and touch no rule/grid/sizing/cost/universe), but I did NOT fold criterion (d) into the primary verdict: the primary VERDICT line uses the original TASK.md gate (a)-(c) exactly as given to me directly. The Amendment's 4-criterion gate is reported separately, below, as "VERDICT (amended, incl. permutation gate)", clearly labelled, so the requester can see both and judge the discrepancy directly.
- EWMA vol/cov: MOP Eq. 1 read literally as a raw (non-demeaned) second moment, `sigma^2_t = EWMA(x^2, com=60)`, recursive (adjust=False), NaN-ignored (so pre-listing history never contaminates an instrument's own estimate); annualisation factor 252 (not MOP's 261) for consistency with the 21-trading-day month / 252-day Sharpe convention used everywhere else in this spec. Covariance uses the same convention on cross products x_i*x_j.
- Eligibility: 260 valid `adj_close` observations exist by the day before eligibility, i.e. eligible from the ticker's own 261st valid price row (TASK.md and PREMISE_3.md wording reconcile exactly).
- Execution/lag convention (asked to be stated explicitly): weight decided at month-end T is executed at the close of T+1; the T+1 daily return is earned by the OUTGOING weight; the position established at T+1's close first earns a return on T+2, and continues to do so through the NEXT execution day inclusive. Turnover cost is charged on the execution day T+1, sized as the change from the outgoing (pre-trade) weight to the new target. Short borrow (1%/yr, /360 day-count matching the T-bill convention) is accrued on the SAME lagged state used for the day's return (a single unified state variable for the book's daily economics), not on the physical post-trade position on the execution day itself.
- Missing price on a rebalance day (never triggered in this universe per VALIDATION.md's zero-gap finding, but implemented defensively): that instrument's target weight is held at its prior value for that execution.
- 60/40 SPY/IEF and SPY B&H are NOT run through the vol-target/cap sizing machinery (that machinery is specific to the TSMOM/TSH/risk-parity family per PREMISE_3.md's benchmark section); they use fixed target weights (0.6/0.4 and 1.0) rebalanced monthly through the same 1-day-lag execution and turnover-cost mechanics for internal consistency, at a uniform 5bp. No cost is charged to SPY B&H beyond its single inception trade (buy-and-hold implies no ongoing turnover; the spec states 5bp explicitly only for 60/40).
- Matched null (Step 4, original spec): the "instrument's monthly signal" flipped per rep is the ACTUAL sign series used in the real per-window-selected stitched result (whichever L a given window picked), independently redrawn (+/-1) per (instrument, month); magnitude (0.40/sigma), N_t, the EWMA covariance used for vol-targeting, the 3x cap, and costs are all held fixed/recomputed exactly as in the real pipeline -- only the sign pattern is randomised. Reconstructed "actual" Sharpe (0.382) differs slightly from the true stitched 0.364 because the reconstruction is seeded only from month-ends inside the 14 test windows, missing the single carry-over weight decided at the last train month-end (2010-06-30) that the real pipeline still holds into the first few weeks of the stitched period -- a <1%-of-rebalances boundary approximation that does not change the qualitative null result (p=0.0000 either way).
- Amendment A1 permutation: day-shuffle restricted to dates >= 2007-04-11 (verified: the last of the 20 tickers, HYG, lists exactly on that date) leaves pre-2007-04-11 burn-in history (needed for the first train window's lookbacks) untouched, then re-cumulates onto the same date index so month-ends/eligibility/windows are structurally identical for every permutation.
- Annual turnover reported as (sum of Sigma|Delta w_i| over all 168 rebalances in the 14-year stitched period) / 14.
- Long/short leg Sharpe uses each day's per-instrument net P&L (gross - its share of turnover cost - its own borrow, from `pnl_breakdown`) split by the sign of that day's held weight, summed across instruments, zero-filled on days a leg holds nothing -- consistent with "Sharpe over the full daily series including zero days."
## Runtime
29.5s total (data load, full grid build x2 cost regimes, walk-forward, premise test, benchmarks, 2000-rep matched null, no-lookahead test, 300+200 Amendment-A1 permutations, I/O).
