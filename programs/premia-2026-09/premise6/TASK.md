# Premise 6 — implementation task (fixed rule, class-balanced, stitched calendar, permutation test; no OOS)

Read `../PREMISE_6.md` first — frozen spec, zero free parameters; implement literally. Then `../data_breadth/VALIDATION.md`. This premise is P3's machinery with three differences: universe (38 ETFs, `data_breadth/`), **L = 12 fixed** (no selection), and **class-balanced raw weights**. So: import from `../premise3/strategy.py` (excess returns, EWMA vol/cov, signals, portfolio scaling + 3× cap, `simulate`) and `../premise3/permtest.py` (day-shuffle harness); write only what differs. `ROOT = /Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH`; code in `ROOT/premise6/`. Env: `uv run --with pandas --with pyarrow --with numpy --with statsmodels --with matplotlib python <script>` from ROOT.

## HARD RULES
1. Read ONLY `data_breadth/etf_daily_insample.parquet` / `*_wide_insample.parquet` and `data_breadth/tbill_3m.parquet` (filter < 2024-07-01). Never open any `*_oos*` or combined file. Loader guard: raise if max date ≥ 2024-07-01.
2. Exactly the rule in PREMISE_6.md. The sensitivity numbers (L ∈ {6, COMBO}; 1/N weighting) are computed only for the sensitivity table and feed nothing.
3. ≤ ~200 lines of new code (most is imported). Report numbers as they come out. FAIL is fine.

## Class map (fixed)
equities: SPY QQQ IWM EFA EEM EWJ EWG EWU EWA EWC EWZ EWH EWY FXI · bonds: TLT IEF LQD HYG TIP MBB BWX EMB · commodities: GLD SLV USO UNG DBC DBA DBB · currencies: UUP FXE FXY FXA FXB FXC FXF · real_estate: VNQ RWX.
Costs 5 bp: SPY QQQ IWM EFA EEM TLT IEF LQD HYG GLD VNQ; 10 bp: all others. Borrow 1 %/yr on shorts.

## Raw weights
`w̃_i,t = s_i,t · (0.40/σ_i,t) · (1/n_c(i),t) · (1/C_t)` with n_c,t eligible instruments in class c at t and C_t the number of classes with ≥ 1 eligible instrument. Then λ scaling to 10 % via EWMA cov, 3× gross cap, P3 conventions throughout (eligibility on the 261st valid price; execution at close t+1; missing price → prior weight).

## Files
- `premise6/strategy.py`: class map, `class_balanced_weights(...)`, loaders with guard; everything else imported.
- `premise6/run.py`: CLI → `RESULTS_INSAMPLE.md`, `daily_pnl.csv` (full span with `stitched` flag), `equity.png` (TSMOM vs TSH vs class-balanced risk parity vs 60/40 vs SPY, stitched), `sensitivity.csv`.
- `premise6/permtest.py`: 500 day-shuffles of the 38-column excess-return matrix on dates ≥ the first day all 38 are listed, re-cumulated onto the original index; full pipeline per permutation; stitched Sharpe; p = share ≥ real. Progress every 100.
- `premise6/test_no_lookahead.py`: prefix test at 5 cutoffs.

## Steps
1. **Premise test**: pooled monthly panel `x_i,t+1/σ_i,t ~ sign(Σ x over prior 252 d)`, clustered by month, 38-ETF panel; β, t, R², N overall and per class. Pass: t > 2.
2. **Fixed rule** (L = 12, class-balanced): full span (2007-07-01 → 2024-06-28) and **stitched calendar 2010-07-01 → 2024-06-30** — net Sharpe (baseline / ×1.5), ann. return & vol, max DD, avg gross leverage, cap-binding %, annual turnover, long vs short leg Sharpe and P&L, per-class P&L, **P&L and Sharpe per test year (14 Jul→Jun rows)**.
3. **Benchmarks (stitched, same universe/class balance/sizing/costs)**: TSH (expanding-mean sign), class-balanced risk parity (all +1), 60/40 SPY-IEF, SPY B&H; Sharpe, return, vol, max DD, correlation with the leg and with SPY. Also the leg's correlation with `../premise3/daily_pnl_wf.csv` and, if present, `../premise4/daily_pnl.csv`, `../premise5/daily_pnl.csv`.
4. **Sensitivity table** (report only): stitched Sharpe for {L=6, L=12, COMBO(3/6/12)} × {class-balanced, 1/N}. Mark (L=12, class-balanced) as the rule.
5. **Permutation test** (500) → p, null mean/sd.
6. **No-lookahead test**.
7. **Gate** (report only): (a) stitched Sharpe ≥ 0.5; (b) TSMOM > TSH; (c) ≥ 8/14 positive test years; (d) p < 0.05. Verdict line at top: PASS only if all four hold.

`RESULTS_INSAMPLE.md` ≤ 130 lines, premise3 section style. Report it verbatim plus file line counts, test output, and anything you interpreted.
