# Premise 1 — implementation task (in-sample + walk-forward only)

You are implementing a pre-registered strategy test. Read `../PREMISE_1.md` first; it is frozen and is the spec. Read `../ict/REUSE_NOTES.md` for the block-bootstrap and no-lookahead test pattern. Work in `ROOT = /Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH`, code goes in `ROOT/premise1/`. Use `uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python <script>` or the venv the data pipeline created.

## HARD RULES
1. Read ONLY `ROOT/data/es_1h_insample.parquet` and `ROOT/data/es_4h_insample.parquet`. Never open any `*_oos.parquet` or the combined `es_1h.parquet` / `es_4h.parquet` / `es_1m*.parquet`. Add a guard at load time that raises if `ts_et.max() >= 2024-07-01`.
2. Implement exactly the rule, grids, sizing, and costs in PREMISE_1.md. Do not add filters, do not extend grids, do not try alternative windows, do not "improve" anything. If the spec is ambiguous, take the most conservative reading, write it down under "Implementation choices" in the results file, and continue.
3. Budget: ~350 lines of new code total across all files. No classes unless needed. No config system.
4. Report numbers exactly as they come out, including bad ones.

## Data schema (from build_data.py)
1h and 4h parquet columns: `ts_et` (tz-aware America/New_York, bar START), `ts_utc`, `instrument_id`, `open, high, low, close, volume`, `n_1m` (number of 1-min bars aggregated). 1h bars start at the top of each ET hour. 4h bars are anchored to the 18:00 ET session start (18, 22, 02, 06, 10, 14). Prices are unadjusted front-contract ES; positions are never held across a session boundary so rolls never matter.

## Files to produce
- `premise1/strategy.py` — pure functions: `build_daily_table(h1, h4, k, L) -> DataFrame` and `pnl(daily_table, slippage_ticks, fee_rt) -> DataFrame`. One row per ET weekday date.
- `premise1/walkforward.py` — CLI that runs everything below and writes `premise1/RESULTS_INSAMPLE.md`, `premise1/wf_windows.csv`, `premise1/trades_wf.csv`, `premise1/daily_pnl_wf.csv`, `premise1/equity_wf.png`.
- `premise1/test_no_lookahead.py` — prefix-consistency test (see step 6).

## Step 1 — daily table
For each ET calendar date d (Mon–Fri) in the 1h data:
- `P15` = `open` of the bar with `ts_et == d 15:00`, required `n_1m >= 50`. Missing → no row (day skipped; count skipped days by reason).
- `P16` = `open` of the bar with `ts_et == d 16:00`, required `n_1m >= 1`. Missing → skip.
- `P_prev16` = `open` of the 16:00 bar on the most recent prior date that has one (this is the last cash close; across weekends/holidays it is simply the last such bar). Missing → skip.
- `r_sofar = ln(P15 / P_prev16)`; `r_trade = ln(P16 / P15)` (the target; used for the premise test and P&L).
- Early-close days automatically drop out because the 15:00 bar is absent or thin. Do not hand-code a holiday calendar.
- **Amendment A1 skips (see PREMISE_1.md):** (i) skip d if the `instrument_id` of the 15:00 bar on d differs from the `instrument_id` of the P_prev16 bar (roll-crossing; prices are unadjusted). (ii) skip d if the immediately preceding weekday has any bars with `ts_et.hour` in 9..12 but no 16:00 bar (day after an early close). Count both skip reasons separately.

Volatility from 4h bars, no lookahead: use only 4h bars whose `ts_et <= d 10:00` (the 10:00–14:00 bar closes at 14:00, before the 15:00 decision). `sigma_4h` = rolling std of ln(close/close.shift(1)) over the last L such bars, requiring L valid bars. `sigma_day = sigma_4h * sqrt(5.5)`; `sigma_1h = sigma_4h / 2`. `z = r_sofar / sigma_day`.

Signal: `dir = sign(z) if |z| >= k else 0`.

Sizing (MES, fixed): `notional = (0.12 / sqrt(252) * 100_000) / sigma_1h`; `contracts = round(notional / (5 * P15))`; clip to [0, 40]. If contracts == 0 with dir != 0, record as "rounded to zero" and no trade. Record how often the 40 cap binds.

## Step 2 — P&L
Per trade (MES multiplier $5/pt): `gross = dir * (P16 - P15) * 5 * contracts`; `slippage = slippage_ticks * 0.25 * 5 * 2 * contracts` (per side, both sides); `fees = fee_rt * contracts`; `net = gross - slippage - fees`. Baseline: slippage_ticks = 1, fee_rt = $1.00. Stress: slippage_ticks = 2.
Daily P&L series = net on trade days, 0 on all other rows of the daily table. Sharpe = mean/std * sqrt(252) over that series. Max drawdown on cumulative $ P&L. Also report hit rate, mean net per trade, mean |z| on traded days, long vs short Sharpe and trade counts.

## Step 3 — premise test (pooled in-sample, pre-registered)
OLS `r_trade ~ r_sofar` with Newey–West HAC SE (5 lags) via statsmodels. Report β, t, R², N. Then the same regression within terciles of |z| computed with L = 30 (descriptive; the falsifiable statement says β should grow with |z|). **Pass criterion: β > 0 and t > 2.** Also report the always-long mean of `r_trade` for context.

## Step 4 — walk-forward
Test windows: 2013-07-01→2014-06-30, then stepping one year through 2023-07-01→2024-06-30 (11 windows). Train = the 3 years immediately before each test window. Grid: k ∈ {0, 0.25, 0.5, 0.75, 1.0}, L ∈ {18, 30, 60}. Select (k, L) by baseline **net Sharpe on train** (ties → nothing special; report). Apply to test. Write `wf_windows.csv` with: test_start, test_end, k, L, train_sharpe, test_sharpe, test_trades, test_net_pnl.
Stitched result = concatenated test-window daily P&L. Report Sharpe, MaxDD, trades, hit rate, long/short split, annual P&L by test year, and both cost settings (baseline and stress). Plot cumulative net P&L → `equity_wf.png`.
Also report two references on the same stitched period: (a) fixed k=0, L=30 (no gate, no selection), (b) buy-and-hold ES (log return per test window from close to close, annualised Sharpe) — context only.

## Step 5 — matched null
Take the stitched trade list, randomise `dir` (±1 with equal probability) 2,000 times keeping dates and contract counts fixed, recompute stitched Sharpe each time. Report the fraction of null Sharpes ≥ the actual (one-sided p-value). Reuse the ICT repo's matched-null helper if its interface fits; otherwise this is ~15 lines of numpy.

## Step 6 — no-lookahead test
Adapt the ICT prefix-consistency pattern: build the daily table on the full in-sample data and on the data truncated at 5 random dates; assert the rows for all dates ≤ (truncation date − 1 day) are identical (`pd.testing.assert_frame_equal`). Run with `k=0.5, L=30`. Must pass.

## Gate (from PREMISE_1.md) — just report it, don't act on it
Stitched walk-forward baseline net Sharpe ≥ 1.0 AND ≥ 800 trades → PASS, else FAIL. Write the verdict line at the top of `RESULTS_INSAMPLE.md`.

## Results file structure
`RESULTS_INSAMPLE.md`: verdict line; premise-test table; walk-forward window table; stitched metrics (baseline + stress); references; null p-value; skipped-day counts by reason; sizing stats (median contracts, cap-binding %, rounded-to-zero count); "Implementation choices" list; runtime. Keep it under ~120 lines. Then report the whole file back verbatim plus anything that surprised you.
