# Premise 7 — implementation task (fixed calendar rule on ES, stitched calendar, permutation test; no OOS)

Read `../PREMISE_7.md` first — frozen, zero free parameters; implement literally. Then `../data_calendar/VALIDATION.md`. Reuse helpers from `../premise3/strategy.py` (EWMA vol, `sharpe`, `max_drawdown`, `md_table`) and the permutation pattern from `../premise4/permtest.py` or `../premise6/permtest.py` (load by file path to avoid the `strategy` module-name collision, as premise5/6 did). `ROOT = /Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH`; code in `ROOT/premise7/`. Env: `uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python <script>` from ROOT.

## HARD RULES
1. Read ONLY `data_calendar/es_daily_front_insample.parquet`, `data_calendar/es_settles_insample.parquet`, `data_calendar/trading_days.csv` (filter < 2024-07-01), and `data_daily/adj_close_wide_insample.parquet` (SPY only). Never open any `*_oos*` or combined file. Loader guard: raise if max date ≥ 2024-07-01.
2. Exactly the rule, sizing, costs and benchmarks in PREMISE_7.md. The context variants feed only the sensitivity table. No filters, no window shifts.
3. ≤ ~220 lines of new code. Report numbers as they come out. FAIL is fine.

## Daily return series (build first)
`r_t` = same-contract settle-to-settle return of the front contract: `front_settle_t / prev_settle − 1` where on the first date after a roll the numerator is `prev_front_settle_today` (the outgoing contract's settle on t) and the denominator is the outgoing contract's settle on t−1; otherwise both are the current front's settles. NaN where unavailable (count). Also flag `roll_day_t`.

## Calendar
From `trading_days.csv`: `tdom_from_end` (0 = T). Window indicator `in_win_t = 1` for tdom_from_end ∈ {3, 2, 1, 0} on the month's last days and `tdom` ∈ {1, 2, 3} on the next month's first days (i.e. T−3…T+3). Entry date = the day with tdom_from_end = 4 (T−4); exit at the settle of T+3. Assert exactly 7 in-window days per month-turn except where the sample starts/ends; report any month with a different count.

## Files
- `premise7/strategy.py`: loaders with guard, `daily_returns(...)`, `window_indicator(...)`, `weights(...)` (0.10/σ at T−4, held through the window; σ = annualised EWMA std COM 60 of `r_t` to T−4), `simulate(...)` charging `(0.25 + 0.10)/P_t` per side of notional on entry, exit and roll days inside a window (×2 for stress), producing daily P&L on a $100k book.
- `premise7/run.py`: CLI → `RESULTS_INSAMPLE.md`, `daily_pnl.csv` (full span with `stitched` flag), `equity.png` (rule vs always-long vs SPY, stitched), `sensitivity.csv`.
- `premise7/permtest.py`: 500 shuffles of `r_t` on the stitched calendar, window fixed; σ, weights, costs recomputed; p = share ≥ real; progress every 100.
- `premise7/test_no_lookahead.py`: prefix test at 5 cutoffs (σ and weights before the cutoff identical).

## Steps
1. **Premise test**: `r_t ~ 1[in_win_t]`, Newey–West 5 lags → b, t, N. Table of mean daily return (bp) and HAC t by bucket: T−8…T−4, T−3…T−1, T…T+3, T+4…T+8, other.
2. **Fixed rule, stitched 2010-07-01 → 2024-06-30**: Sharpe at 1 and 2 ticks, ann. return & vol, max DD, time in market, mean |w|, P&L and Sharpe per test year (14 Jul→Jun rows), P&L split T−3…T−1 vs T…T+3, number of windows, cost as % of gross P&L.
3. **Benchmarks (stitched, same sizing/costs)**: always-long vol-targeted ES (w re-set at each T−4); SPY buy-and-hold; correlations of the rule's daily P&L with SPY, `../premise4/daily_pnl.csv` (if present), `../premise3/daily_pnl_wf.csv`.
4. **Sensitivity (report only)**: long T…T+3; long T−3…T−1; rule + short T−8…T−4; always-long — Sharpe each; rule row marked.
5. **Permutation test** (500) → p, null mean/sd.
6. **No-lookahead test**.
7. **Gate** (report only): (a) stitched Sharpe ≥ 0.5; (b) rule > always-long; (c) ≥ 8/14 positive test years; (d) p < 0.05. Verdict line at top: PASS only if all four hold.

`RESULTS_INSAMPLE.md` ≤ 120 lines, premise3 section style. Report it verbatim plus file line counts, test output, and anything you interpreted.
