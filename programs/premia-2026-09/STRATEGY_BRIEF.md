# ES Futures Strategy Research Brief

## Goal
Find, validate, and paper-trade **one** systematic strategy on CME E-mini S&P 500 futures (ES) that:
- trades on **1-hour bars** with a **4-hour anchor** timeframe for bias/regime,
- takes **both longs and shorts**,
- achieves **annualized Sharpe ≥ 1.5, net of costs, on the locked out-of-sample window 2024-07-01 → 2026-07-01**.

Work autonomously. Ping me only at the checkpoints at the end, or when blocked.

## What you have
- `glbx-mdp3-20100606-20260701.ohlcv-1m.csv.zst` — Databento GLBX.MDP3, 1-minute OHLCV, all ES contracts, 2010-06-06 → 2026-07-01, ~8.6M rows, UTC timestamps. Gotchas:
  - It is **per-contract, not continuous** — you must build the continuous series. Roll on volume crossover (front → next when next's daily volume exceeds front's). Account for roll P&L explicitly; don't back-adjust prices.
  - **151 of the 191 symbols are calendar spreads** (contain `-`). Drop them.
  - Only 40 outright symbol codes exist (ESH0…ESZ9) and they **repeat every decade** — key on `instrument_id`, never on `symbol`.
  - `condition.json` flags data-quality gaps. Read it.
  - ES: $50/point, 0.25 tick = $12.50. MES (micro): 1/10th size, same prices.
- https://github.com/kani8/ict — my prior research. Its ICT/"smart money" premise was tested honestly and **rejected**; do not resurrect it. But its infrastructure is tested and reusable — **reuse it instead of writing new**: pessimistic intrabar fill engine (`engine/`), no-lookahead prefix-consistency tests (`tests/test_no_lookahead.py`), block-bootstrap CIs and matched null models (`analytics/`), resampling (`core.py`).

## Process — in this order
1. **Premise first.** Read institutional/academic sources only: SSRN working papers, AQR / Man / Two Sigma research, peer-reviewed journals. Ignore YouTube, Twitter, Reddit, ICT/SMC, and anything selling a course. Starting points relevant to a 1h/4h ES strategy: intraday momentum (Gao, Han, Li & Zhou 2018), overnight-vs-intraday return asymmetry (Lou, Polk & Skouras 2019), short-horizon time-series momentum (Moskowitz, Ooi & Pedersen 2012 and successors), opening-range breakout (Zarattini & Aziz 2023). Write **one** premise as a falsifiable statement: the economic or behavioral mechanism, the expected sign, and the conditions under which it should fail — **before touching the data**. Pre-register the exact rule, the ≤ 4 free parameters with ranges, and pass/fail criteria in `PREMISE_<n>.md`.
2. **Data split.** Lock **2024-07-01 → 2026-07-01** as out-of-sample. Do not load it until step 6. Everything before it is in-sample.
3. **Build the minimum.** Continuous 1h and 4h series from the 1-min data. State your session convention (CME trading day starts 17:00 CT; anchor 4h bars to it). Strategy as a pure function of past bars. Run the ICT repo's no-lookahead tests against it.
4. **Realistic costs.** Fills at the **next 1h bar's open**. Commission + exchange + NFA fees: **$4.50 round-trip per ES contract** (verify current rates; MES ≈ $1.00). Slippage: **1 tick per side baseline, 2 ticks stress**. Do **not** model latency beyond next-bar-open — at 1h bars it is irrelevant and modeling it is wasted effort.
5. **Walk-forward.** Rolling windows over in-sample: **3y train / 1y test, step 1y** (≈ 11 test years). Parameters chosen per window on train only. Report the stitched test-window equity curve — that is your in-sample result. Do not tune the walk-forward scheme itself. **Gate: only proceed to step 6 if stitched walk-forward Sharpe ≥ 1.0.** Otherwise the premise is dead already; don't burn the OOS window on it.
6. **Out-of-sample — once.** Freeze the rule. Run it on the locked window **exactly once**. Report annualized Sharpe = mean(daily P&L) / std(daily P&L) · √252, net of costs, plus max drawdown, trade count, long/short breakdown, and average holding time. Note: Sharpe 1.5 over 2 years is a t-stat of ≈ 2.1 — treat OOS as *confirmation* of the walk-forward result, not as discovery. A premise that fails OOS is dead; do not re-tune it.
7. **Robustness.** Exactly two tests: (a) block-bootstrap reshuffle of the trade sequence (already in the ICT repo) → Sharpe and drawdown distributions; (b) cost + slippage perturbation ±50%. Do not build synthetic market generators or regime simulators.
8. **Position sizing.** Constant-volatility targeting at **12% annualized**, sized in **whole MES contracts on a $100k account** (ES rounds to 0–1 contracts at this size, which hides the sizing behavior). Use the MES fee schedule in the cost model. Fixed-fractional at 1% risk per trade is the acceptable alternative — pick one, not both.
9. **Paper trade.** Run the frozen rule live on a broker paper account (IBKR paper or Tradovate sim — ping me for credentials) for **≥ 4 weeks**. Log every signal, intended fill, and actual fill. Compare realized slippage and P&L to backtest assumptions. Only then is it a candidate for real capital.

## Tooling
- Spend **≤ 30 minutes** evaluating the Jesse MCP server (docs.jesse.trade/docs/mcp). It is crypto-native (Binance/Bybit perps). Unless it ingests CME futures with roll handling out of the box, drop it — **do not write an adapter**. Same rule for any other framework.
- Default stack: Python, pandas/numpy, the ICT repo's modules. No new backtesting framework, no database, no dashboard, no config system beyond one TOML file.

## Budget and stopping rules
- Test **at most 4 premises**, sequentially, each pre-registered before its data is touched. If none clears the bar, **stop and deliver the honest negative result** with what you learned — that is a valid, useful outcome, and the ICT repo is the model for how to write one. Searching past 4 is pattern-hunting by another name.
- ≤ 4 free parameters per strategy. One walk-forward scheme. Two robustness tests. One sizing method.
- If a step needs more than ~200 lines of new code, you are probably over-building. Stop and reconsider.
- A simple rule with a boring Sharpe of 1.5 beats a complex one with 2.5 — the second is overfit.

## Deliverables
1. `PREMISE_<n>.md` per premise — written before its data is touched.
2. `RESULTS.md` — walk-forward equity curve, OOS metrics, robustness results, sizing, and an explicit list of every discretionary choice you made along the way.
3. Reproducible code with a single entry point; no-lookahead tests passing.
4. Paper-trading log and backtest-vs-paper comparison.

## Ping me when
- You need broker / paper-trading credentials.
- A premise passes the step-5 gate (before you open OOS) and again if it passes OOS.
- You've exhausted 4 premises.
- You're stuck for more than an hour on anything.
