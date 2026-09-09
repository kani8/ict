# Premise 5 — implementation task (fixed rule, stitched calendar, permutation test; no OOS)

Read `../PREMISE_5.md` first — frozen spec **including Amendment A1 (FX variant fixed at XS, zero free parameters)**; implement it literally. Then `../data_carry/VALIDATION.md`. Reuse from `../premise3/strategy.py` (EWMA vol/cov, portfolio 10 % scaling with 3× cap, `simulate` with 1-day lag / turnover costs / borrow) and `../premise3/permtest.py` (day-shuffle harness) — import where the signatures fit, otherwise copy the minimum. `ROOT = /Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH`; code in `ROOT/premise5/`. Env: `uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python <script>` from ROOT.

## HARD RULES
1. Read ONLY `data_carry/etf_daily_insample.parquet` (or `*_wide_insample`), `data_carry/rates_3m_monthly.parquet`, `data_carry/yields_daily.parquet`, `data_daily/tbill_3m.parquet` and `data_daily/adj_close_wide_insample.parquet` (SPY only). Filter every signal series to date < 2024-07-01 yourself. Never open any `*_oos*` or combined ETF file. Loader guard: raise if max date ≥ 2024-07-01.
2. Implement exactly the rule, sizing, costs and benchmarks in PREMISE_5.md. XS is fixed; TS and BOTH are computed **only** for the sensitivity table. No overlays, no universe changes. Ambiguity → most conservative reading, documented under "Implementation choices".
3. ≤ ~300 lines of new code. Plain functions, vectorised pandas.
4. Report numbers as they come out. FAIL is fine.

## Signals (exact)
- FX carry at month-end t: `carry_i = rate_ccy(m−1) − rate_USD(m−1)` where m is the month containing t (one-month lag, both from `rates_3m_monthly`). Missing rate → carry forward the last observation up to 6 months (Amendment A2); beyond that the instrument gets weight 0 that month (report how often either happens; in-sample it should be never or nearly never).
- Bond signal at month-end t: `s_IEF = sign(DGS10_t − DTB3_t)`, `s_TLT = sign(DGS20_t − DTB3_t)` using the last non-NaN yield on or before t.
- XS weights: `w̃_i = rank(carry_i) − 3.5` over the six currencies (ties → average rank), normalised Σ|w̃| = 1. TS: `sign(carry_i)/6`. BOTH: ½(XS + TS) renormalised.
- Sleeve scaling exactly as P3: FX `λ = 0.10/√(w̃ᵀΣw̃)`; bonds `w̃_j = s_j·(0.40/σ_j)/2` then the same λ scaling; 3× gross cap each. Leg = ½ FX + ½ bonds (daily P&L). Execution at close t+1 (P3 convention), costs 10 bp FX / 5 bp bonds one-way on turnover, borrow 1 %/yr on short notional (/360).

## Files
- `premise5/strategy.py`: loaders with guard, `fx_weights(carry, variant)`, `bond_weights(yields)`, sleeve sizing, `simulate` (imported or copied), leg assembly.
- `premise5/run.py`: CLI → `RESULTS_INSAMPLE.md`, `daily_pnl.csv` (full span with `stitched` flag), `equity.png` (leg vs leg-no-signal vs SPY, stitched), `sensitivity.csv`.
- `premise5/permtest.py`: 500 permutations on the stitched calendar. Exogenous-signal scheme: shuffle the order of trading days for the 8-instrument daily excess-return matrix (rows move as units), re-cumulate onto the original date index, keep carry and yield signals on their original dates; recompute vol/cov, weights, costs, P&L. p = share ≥ real. Progress every 100.
- `premise5/test_no_lookahead.py`: prefix test at 5 cutoffs — weights decided before the cutoff identical to the full run.

## Steps
1. **Premise test**: (FX) pooled monthly panel `x_i,t+1/σ_i,t ~ carry_i,t` (next-month excess return over vol; carry in %-points), SE clustered by month → β, t, R², N; (bonds) `x_j,t+1/σ_j,t ~ (y_j,t − bill_t)` per ETF, Newey–West 3 lags. Pass: FX t > 2 AND IEF t > 2.
2. **Fixed rule, full span** (first month-end with all 8 instruments eligible → 2024-06-28): leg and each sleeve — Sharpe, return, vol, max DD, avg gross leverage, cap-binding %, annual turnover.
3. **Stitched calendar 2010-07-01..2024-06-30**: leg net Sharpe at baseline and ×1.5 costs, return, vol, max DD, sleeve Sharpes, long/short contribution in FX, **P&L and Sharpe by test year (14 Jul→Jun rows)**, share of months with missing rates.
4. **Benchmarks (stitched)**: FX no-signal (equal-weight long six, same scaling), bond no-signal (always-long IEF+TLT, same scaling), leg no-signal (½/½), SPY buy-and-hold; correlations of the leg with SPY, `../premise3/daily_pnl_wf.csv`, and `../premise4/daily_pnl.csv` if present.
5. **Sensitivity table**: variant ∈ {XS, TS, BOTH}: full-span and stitched leg Sharpe, Sharpe per test year; XS marked fixed. Changes nothing.
6. **Permutation test** (500) → p, null mean/sd.
7. **No-lookahead test**.
8. **Gate** (report only): (a) stitched leg Sharpe ≥ 0.5; (b) leg > leg-no-signal; (c) ≥ 8/14 positive test years; (d) p < 0.05. Verdict line at top: PASS only if all four hold.

`RESULTS_INSAMPLE.md` ≤ 130 lines, premise3 section style. Report it verbatim plus file line counts, test output, and anything you interpreted.
