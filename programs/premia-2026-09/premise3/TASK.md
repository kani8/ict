# Premise 3 — implementation task (in-sample + walk-forward only)

Read `../PREMISE_3.md` first — frozen spec. Then `../data_daily/VALIDATION.md`. Reuse from `../premise1/walkforward.py` / `strategy.py` whatever fits (sharpe, max_drawdown, md_table, make_windows, report skeleton); import or copy, don't re-derive. `ROOT = /Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH`; code in `ROOT/premise3/`. Env: `uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python <script>` from ROOT.

## HARD RULES
1. Read ONLY `data_daily/etf_daily_insample.parquet` (or the `*_wide_insample.parquet` files) and `data_daily/tbill_3m.parquet` (filter to date < 2024-07-01 yourself). Never open any `*_oos*` file or the combined files. Loader guard: raise if max date ≥ 2024-07-01.
2. Implement exactly the rule, grid, sizing, costs and benchmarks in PREMISE_3.md. No extra signals, filters, universe changes, rebalance-frequency changes. Ambiguity → most conservative reading, documented under "Implementation choices".
3. ≤ ~350 lines of new code. Plain functions, vectorised pandas.
4. Report numbers as they come out. FAIL is fine.

## Data notes
`date` is pyarrow date32 → convert to Timestamp. Use `adj_close` for returns. `tbill_3m.parquet` has `date, rate_pct`; daily rf = rate_pct/100/360, forward-filled to trading days. Eligibility: instrument enters on its 261st trading day of data.

## Files
- `premise3/strategy.py`: `daily_excess_returns(...)`, `ewma_vol_cov(x, com=60)`, `signals(x, L)` (L ∈ {3,6,12,'COMBO'}), `target_weights(x, sig, ...)` at month-ends with per-instrument 40 %/σ, 1/N_t, portfolio 10 % vol scaling via EWMA covariance, 3× gross cap; `simulate(weights, x, costs, borrow)` applying the 1-day lag (weights decided at close t become effective from the close of t+1, i.e. earn returns from t+2's return onward — state your exact convention), turnover costs, short borrow, producing a daily P&L / return series on a $100k book.
- `premise3/walkforward.py`: CLI → `RESULTS_INSAMPLE.md`, `wf_windows.csv`, `daily_pnl_wf.csv`, `weights_wf.parquet`, `equity_wf.png` (TSMOM vs TSH vs risk parity vs 60/40 vs SPY, all on the stitched calendar).
- `premise3/test_no_lookahead.py`: prefix-consistency test — truncate the input at 5 random dates; the weights decided on all month-ends strictly before the cutoff must be identical to the full-sample run (exercises EWMA vol/cov, signals, and eligibility).

## Steps
1. **Premise test**: monthly panel, for each eligible (i, month-end t): y = (excess return over the next month) / σ_i,t; x = sign(Σ excess over prior 252 days). OLS with standard errors clustered by month (statsmodels `cov_type='cluster'`). Report β, t, R², N. Pass: t > 2. Also report per-asset-class β/t (equities, bonds, commodities, currencies, REIT).
2. **Walk-forward**: 14 windows per spec. For each, choose L ∈ {3,6,12,COMBO} by baseline net Sharpe on the 3y train; apply to test. `wf_windows.csv`: test_start, test_end, L, train_sharpe, test_sharpe, test_net_pnl, test_avg_gross_lev. Stitched: net Sharpe (baseline and ×1.5 costs), annualised return & vol, max DD, avg gross leverage, cap-binding % of rebalances, annual turnover (Σ|Δw| per year), long-leg vs short-leg Sharpe contribution, per-asset-class P&L contribution, P&L by test year.
3. **Benchmarks on the stitched calendar**, same sizing & costs: TSH (sign of expanding-window mean excess return, using all data from each instrument's first date), risk parity (all +1), 60/40 SPY/IEF monthly rebalanced (5 bp costs), SPY buy-and-hold. Report each's Sharpe, return, vol, max DD, and correlation of daily returns with TSMOM and with SPY.
4. **Matched null**: 2,000 reps — for each rep, randomly flip the sign of each instrument's monthly signal independently (keeping sizing/costs), recompute stitched Sharpe; one-sided p = share ≥ actual. Also report the fixed-L reference (L = 12 throughout, no selection).
5. **No-lookahead test** as above (run with L = 12).
6. **Gate** (report only): (a) stitched net Sharpe ≥ 0.5; (b) TSMOM Sharpe > TSH Sharpe; (c) ≥ 8 of 14 test years positive. Verdict line at top of `RESULTS_INSAMPLE.md`: PASS only if all three hold.

`RESULTS_INSAMPLE.md` ≤ 140 lines, same section style as premise1/2. Report it verbatim plus file line counts, test output, and anything you interpreted.
