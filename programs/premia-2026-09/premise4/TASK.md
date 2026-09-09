# Premise 4 — implementation task (fixed rule, stitched calendar, permutation test; no OOS)

Read `../PREMISE_4.md` first — frozen spec **including Amendment A1 (θ fixed at 0.0050, zero free parameters)**; implement it literally. Then `../data_vx/VALIDATION.md`. Reuse from `../premise3/` (`strategy.py`, `walkforward.py`, `permtest.py`) whatever fits: EWMA vol, Sharpe / max-DD / md-table helpers, the permutation harness and report skeleton — import or copy, don't re-derive. `ROOT = /Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH`; code in `ROOT/premise4/`. Env: `uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python <script>` from ROOT.

## HARD RULES
1. Read ONLY `data_vx/vx_daily_insample.parquet`, `data_vx/vx_contracts_insample.parquet`, `data_vx/vix_spot.parquet` (filter date < 2024-07-01 yourself) and `data_daily/adj_close_wide_insample.parquet` (SPY only, for the context benchmark). Never open any `*_oos*` or combined file. Loader guard: raise if max date ≥ 2024-07-01.
2. Implement exactly the rule, sizing, costs and benchmarks in PREMISE_4.md. θ = 0.0050 is fixed; the other three θ values are computed **only** for the sensitivity table and must not feed any selection. No hedge, no filters, no stops, no other roll rule. Ambiguity → most conservative reading, documented under "Implementation choices".
3. ≤ ~250 lines of new code. Plain functions; the state machine may be a simple loop over days.
4. Report numbers as they come out. FAIL is fine.

## Held series (build first, test second)
For each date t: held = f1 if f1_dte ≥ 10 else f2. Held-position return from t to t+1 = settle_{held(t), t+1} / settle_{held(t), t} − 1, taken from `vx_contracts` by (date, expiry). Roll days are exactly the days where held(t) ≠ held(t−1); count them (expect ≈ 12/yr). Days where the held contract has no settle on t+1 → return NaN, position carried, count them. `roll_t = (F_held − VIX_t) / F_held / max(dte_held, 1)`.

## Files
- `premise4/strategy.py`: `load_insample()`, `held_series(vx_daily, contracts)` → DataFrame [date, expiry, settle, dte, ret_next, roll], `positions(roll, theta)` (state machine with θ/2 exit), `size(pos, ret, com=60)` → weights `s · 0.10/σ`, `simulate(weights, ret, F, ticks=1)` applying the 1-day lag (weight decided at t established at settle t+1, earns ret from t+1→t+2 onward) and costs `(0.05·ticks + 0.00125)/F` on |Δnotional| including rolls (a roll = close + reopen of the full notional in the new contract).
- `premise4/run.py`: CLI → `RESULTS_INSAMPLE.md`, `daily_pnl.csv` (full span, with a `stitched` boolean for 2010-07-01..2024-06-30), `equity.png` (timed vs always-short vs always-long vs SPY on the stitched calendar), `sensitivity.csv`.
- `premise4/permtest.py`: 500 permutations of the fixed rule on the stitched calendar, seed fixed. Exogenous-signal scheme: shuffle the order of the held-series daily returns within the stitched span, keep `roll` on its original dates, recompute σ, weights, costs, P&L per permutation. p = share of permuted Sharpes ≥ real. Print progress every 100.
- `premise4/test_no_lookahead.py`: prefix-consistency test at 5 random cutoffs — positions and weights decided strictly before the cutoff must be identical to the full-sample run (exercises EWMA vol and the state machine).

## Steps
1. **Premise test**: `ret_next ~ roll`, Newey–West 5 lags, in-sample span from the first date with 60 days of held returns. Report β, t, R², N; also the 21-day-forward version (overlapping; NW 21 lags) and β/t on the contango half (roll > 0) and backwardation half separately. Pass: daily t < −2.
2. **Fixed rule, full span** (from first valid date to 2024-06-28): Sharpe, ann. return & vol, max DD, worst day, time in market, trades/yr, roll-cost share of total cost.
3. **Stitched calendar 2010-07-01..2024-06-30** (same dates as premise3, no training — the series is simply restricted): net Sharpe at 1 tick and 2 ticks, ann. return & vol, max DD, worst day, time in market, long-leg vs short-leg P&L and Sharpe, **P&L and Sharpe by test year** (Jul→Jun years, 14 rows), cap-binding % (expect 0).
4. **Benchmarks on the stitched calendar**: always-short and always-long (same sizing, costs, rolls), SPY buy-and-hold; correlation of daily returns of the timed leg with SPY and with `../premise3/daily_pnl_wf.csv` on overlapping dates.
5. **Sensitivity table** (`sensitivity.csv` + md): for θ ∈ {0, 0.0025, 0.0050, 0.0075}: full-span Sharpe, stitched Sharpe, and Sharpe per test year. Mark θ = 0.0050 as the fixed choice. This table changes nothing.
6. **Permutation test** (500 reps) → p, null mean/sd.
7. **No-lookahead test** (θ = 0.0050).
8. **Gate** (report only): (a) stitched Sharpe ≥ 0.5; (b) timed > always-short; (c) ≥ 8/14 positive test years; (d) permutation p < 0.05. Verdict line at top of `RESULTS_INSAMPLE.md`: PASS only if all four hold.

`RESULTS_INSAMPLE.md` ≤ 130 lines, same section style as premise3. Report it verbatim plus file line counts, test output, and anything you interpreted.
