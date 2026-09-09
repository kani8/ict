# Premise 2 — implementation task (in-sample + walk-forward only)

Read `../PREMISE_2.md` first — it is frozen and is the spec. Then read `../premise1/strategy.py` and `../premise1/walkforward.py`: **reuse** their loader (with the OOS guard), walk-forward driver, matched-null, block structure and report writer by importing or copying; do not re-derive them. `ROOT = /Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH`; code goes in `ROOT/premise2/`. Env: `uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python <script>` from ROOT.

## HARD RULES
1. Read ONLY `data/es_1m_insample.parquet` (for the 09:30 open only), `data/es_1h_insample.parquet`, `data/es_4h_insample.parquet`. Never open any `*_oos.parquet` or combined file. Keep the loader guard (`ts_et.max() < 2024-07-01` or raise).
2. Implement exactly the rule, grids, sizing, costs and skips in PREMISE_2.md. No extra filters, cutoffs, targets, grid points or "quick experiments". Ambiguity → most conservative reading, listed under "Implementation choices".
3. ≤ ~300 lines of *new* code (reuse counts for free). Plain functions.
4. Report the numbers as they come out. FAIL is fine.

## Data schema
1h/4h parquet: `ts_et` (tz-aware America/New_York, bar START), `ts_utc`, `instrument_id`, `open, high, low, close, volume`, `n_1m`. 1m parquet same plus per-minute rows; the 09:30 open is the `open` of the row with `ts_et == d 09:30`.

## Files
- `premise2/strategy.py`: `build_day_frame(m1, h1, h4, m, N) -> DataFrame` with one row per (date, decision_hour) carrying O, C_prev, close_t, Upper_t, Lower_t, sigma_t, target position; and `simulate(day_frame, slippage_ticks, fee_rt) -> (trades_df, daily_pnl_df)` implementing the state machine, fills at next bar open ± slippage, sizing, and the 16:00 exit.
- `premise2/walkforward.py`: CLI producing `RESULTS_INSAMPLE.md`, `wf_windows.csv`, `trades_wf.csv`, `daily_pnl_wf.csv`, `equity_wf.png`.
- `premise2/test_no_lookahead.py`: prefix-consistency test as in premise1 — truncate the 1m/1h/4h inputs at 5 random dates and assert the day_frame rows for earlier dates are identical. Must exercise σ_t (uses prior N days) and σ_4h.

## Step 1 — day frame
Per date d (ET weekday) apply the skips from PREMISE_2.md (count each reason). For t in 10..15: `close_t` = close of the 1h bar starting at t−1 (require `n_1m ≥ 50` for that bar, else that (d,t) is "no decision" — hold current position). `σ_t` = mean over the prior N valid days of `|close_{d−i,t}/O_{d−i} − 1|`. Bands per the spec. Target = +1 if close_t > Upper_t, −1 if close_t < Lower_t, else NaN (hold).

## Step 2 — simulation
Per day: pos = 0. For t in 10..15: if target_t is ±1 and ≠ pos: close the existing leg at `open` of bar t (adverse slippage), open the new leg at the same open (adverse slippage), size per spec using `σ_4h` (last 30 4h bars ending by 14:00 ET on d) and `h_remaining = 16 − t`. At 16:00: close any open leg at the `open` of the 16:00 bar. One trades row per leg: date, entry_t, exit_t, dir, contracts, entry_px, exit_px, gross, slippage, fees, net, exit_reason ∈ {flip, close}. Daily P&L = sum of leg nets (0 on no-trade days). Sharpe over all kept days incl. zeros. Also report: trades/day, flips/day, hit rate, mean net per trade, mean hold hours, long vs short.

## Step 3 — premise test
OLS `r_rest ~ r_open` with `r_open = ln(close_{[09:00,10:00)} / C_prev)` and `r_rest = ln(P16 / close_{[09:00,10:00)})`, P16 = open of the 16:00 bar; HAC-5. Report β, t, R², N. Pass: β > 0, t > 2. Descriptive: with m = 1, N = 14, over all (d,t) with close_t outside the band, mean of `sign(breach) · ln(P16 / open_of_bar_t)` in bp, the count, and the share of (d,t) breached; versus unconditional mean |ln(P16/open_of_bar_t)|.

## Step 4 — walk-forward
Same 11 windows as premise1. Grid m ∈ {0.75, 1.0, 1.5} × N ∈ {14, 30, 60}. Select by baseline net train Sharpe. `wf_windows.csv`: test_start, test_end, m, N, train_sharpe, test_sharpe, test_trades, test_net_pnl. Stitched metrics baseline + stress; annual P&L; references: (a) fixed m = 1, N = 14; (b) buy-and-hold ES per window as in premise1. Plot equity.

## Step 5 — matched null
Randomise the sign of each *day's* net P&L? No — randomise `dir` per leg (±1) keeping dates, times, contracts and prices fixed, recompute P&L and stitched Sharpe, 2,000 reps; one-sided p.

## Step 6 — no-lookahead test
As above. Run with m = 1, N = 14.

## Gate — report only
Stitched baseline net Sharpe ≥ 1.0 AND ≥ 800 trades → PASS else FAIL. Verdict line at the top of `RESULTS_INSAMPLE.md`. Same section structure as `premise1/RESULTS_INSAMPLE.md`, ≤ 130 lines. Report the file verbatim, file line counts, test output, and anything you had to interpret.
