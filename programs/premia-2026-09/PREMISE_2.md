# PREMISE 2 — Intraday Trend Continuation from the Open (Noise-Band Breakout)

**Status:** FROZEN 2026-09-08 after literature verification, before any strategy code has read price data for this premise. No return statistics relevant to this rule have been examined. (Premise 1's diagnostics touched only the 15:00→16:00 window and the prior-close→15:00 return; nothing about opening ranges or hourly band breaches.)

## Economic mechanism
Some days are *information days*: overnight news or a large open-to-early-session move reveals a shift in fair value or a large flow that must be worked through the session. On those days the move persists to the close because (1) option and leveraged-ETF dealers are net short gamma and must hedge **in the direction of the move**, most heavily into the close (Baltussen, Da, Lammers & Martens 2021 — momentum present only on short-gamma days); (2) institutions execute large orders via VWAP/TWAP schedules, so a latent imbalance leaks into prices over hours, not minutes (Choi, Larsen & Seppi 2021); (3) vol-targeting and leveraged/inverse ETF rebalancing add pro-cyclical end-of-day flow. Days whose price stays inside its normal noise envelope are *noise days* with no such flow, and should not be traded.

The strategy is synthetically **long intraday gamma**: small whipsaw losses on noise days that briefly poke outside the band, larger gains on genuine trend days. The premise is that ES trend days occur more often, and run further, than the noise envelope implies.

## Falsifiable statement
On ES, conditional on an hourly close lying outside the noise band (open/prior-close anchored, sized to the recent time-of-day average absolute move), the return from that point to the 16:00 ET close has **the same sign as the breach**, with a mean large enough to exceed round-trip cost (> 2 bp). Unconditionally, the return from the previous close to 10:00 ET **positively predicts** the return from 10:00 to 16:00 ET.

Predicted: β > 0, t > 2 for the unconditional regression; positive conditional mean.

## Where it should fail (pre-stated)
- Low-volatility, range-bound regimes (2016–17 were the worst years in the source paper; low-vol years were also the weakest for premise 1). Narrow bands get breached by noise; trends don't develop.
- If dealers are net long gamma for extended periods, the hedging flow *dampens* moves and breakouts revert.
- If the 1h decision cadence is too coarse — the paper used 30-min marks and reports no 60-min variant — entries arrive later and exits are slower, eroding the edge. **This is the main design risk and is accepted, not to be patched with 30-min bars.**

## Exact rule (1h decisions, ET; frozen)
Definitions for day d:
- `O` = open of the first 1-minute bar at 09:30 ET on d (from `es_1m_insample.parquet`; a known price at 09:30). Missing → skip d.
- `C_prev` = open of the 16:00 ET 1h bar on the most recent prior trading day (the cash-close proxy used throughout Trail A).
- Decision times `t ∈ {10:00, 11:00, 12:00, 13:00, 14:00, 15:00}`. At time t the decision price is `close` of the 1h bar `[t−1h, t)`; fills occur at `open` of the bar `[t, t+1h)` plus slippage. Positions are always closed at the `open` of the 16:00 bar.
- Noise at time t: `σ_t = mean over the prior N trading days of |close_{d−i, t} / O_{d−i} − 1|` (only days with a valid O and a valid bar close at t count; require N such days).
- `Upper_t = max(O, C_prev) · (1 + m·σ_t)`, `Lower_t = min(O, C_prev) · (1 − m·σ_t)`.
- Position state machine (paper's rule): start flat. At each decision time t, if `close_t > Upper_t` → target position **long**; if `close_t < Lower_t` → target position **short**; otherwise hold the current position. Change of target ⇒ trade at the open of bar t (a flip closes and reopens; costs charged on both legs). Flat at 16:00.
- No entry cutoff, no profit target, no re-sizing within a position except on flip.

## Free parameters (2) and grids
| Param | Meaning | Grid |
|---|---|---|
| m | band multiplier | {0.75, 1.0, 1.5} |
| N | lookback (trading days) for σ_t | {14, 30, 60} |

Nothing else is tunable. Decision times, anchors, the flip rule, and the 16:00 exit are fixed by the source paper and the mechanism.

## Fixed (not tuned)
- **Sizing:** constant-vol target 12 % annualised on a $100k book in whole MES contracts. σ_4h = rolling std of 4h log returns over the last **30** 4h bars whose window ends by 14:00 ET on d (no lookahead; fixed a priori as the grid midpoint used in P1, not chosen from P1 results). Expected hold from entry at t = hours until 16:00, so σ_hold = σ_4h · √(h_remaining/4). Notional = (0.12/√252 · 100,000) / σ_hold; contracts = round(notional / (5·P)); clip [0, 40]; record cap-binding and rounded-to-zero counts. On a flip, the new leg is sized at the flip time.
- **Costs:** MES $1.00 round-trip fees, slippage 1 tick ($1.25) per side baseline, 2 ticks stress. A flip = 2 sides closing + 2 sides opening.
- **Walk-forward:** identical to P1 — train 3y / test 1y, step 1y, 11 test windows 2013-07 → 2024-06; (m, N) chosen per window by baseline net Sharpe on train.
- **Skips (day-level, parameter-free, same spirit as Amendment A1):** no 09:30 1m bar; no 16:00 bar on d (early close — cannot exit at the reference close); prior trading day has RTH bars but no 16:00 bar (day after early close — `C_prev` undefined at the cash close); `instrument_id` of today's bars ≠ that of the `C_prev` bar (roll-crossing; prices unadjusted). Days with fewer than N valid history days for any σ_t → no trades that day (row kept as a zero-P&L day).

## Pass / fail criteria (pre-stated)
1. **Premise test** (independent of the trading rule; pooled in-sample; HAC-5): OLS of `r(10:00→16:00)` on `r(C_prev→10:00)`: **β > 0 and t > 2**. Descriptive add-on: mean of `sign(breach) · r(t→16:00)` over all (d, t) with `close_t` outside the m = 1, N = 14 band, versus the unconditional mean |r(t→16:00)|.
2. **Gate:** stitched walk-forward baseline net Sharpe ≥ 1.0 and ≥ 800 trades (a flip counts as one closed trade plus one new trade). If it fails: dead, OOS stays sealed.
3. **Target:** OOS 2024-07-01 → 2026-07-01, opened once, net Sharpe ≥ 1.5 on the full daily series (flat days = 0), plus max drawdown, hit rate, trades/day, long vs short, flips per day, and cap-binding frequency.
4. **Robustness:** (a) 20-day block bootstrap of daily P&L, 5,000 reps → 5th-pct Sharpe, 95th-pct drawdown; (b) costs/slippage × 0.5 and × 1.5.

## Honest expectations
Source paper (SPY, 2007–2024, 30-min marks): simple variant (opposite-band stop, unlevered) Sharpe **0.61**; vol-targeted variant Sharpe **1.33**; hit ratio 43 %; 1.3–1.8 trades/day; robustness over N (5–90) and m (0.5–2) roughly flat. We are vol-targeted but on 1h marks and on ES. A reasonable prior for the stitched walk-forward is **0.5–1.2**, so the 1.0 gate is a real hurdle, not a formality.

## What I will NOT do
- Add a VWAP trailing stop, relative-volume or VIX filter, entry-time cutoff, or profit target after seeing results — even though the paper's best variant uses some of them.
- Switch to 30-min decisions if the 1h version fails.
- Widen the grids or re-open OOS.

## Literature anchors (verified against primary sources 2026-09-08)
- Zarattini, Aziz & Barbon (2024, rev. 2025), "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", SSRN 4824172 (SFI WP 24-97). Noise-area definition, entry/exit and results as above; worst years 2016 (−12.8 %) and 2017 (−6.9 %); costs $0.0035 + $0.001/share; market-impact rerun Sharpe 1.17. **Not peer-reviewed** — anchor strength medium.
- Baltussen, Da, Lammers & Martens (2021), *JFE* 142(1): `r_ROD` (open+30m → close−30m) predicts the last half hour, β = 4.18 (t = 7.29) on equity-index futures incl. ES; momentum present only on net-short-gamma days. Peer-reviewed mechanism anchor.
- Gao, Han, Li & Zhou (2018), *JFE* 129(2): first half-hour → last half-hour, β(×100) = 6.94. Note: **neither GHLZ nor Baltussen report the rest-of-day-on-opening-return regression** that our premise test runs; continuation across the *whole* day is supported mainly by Zarattini et al. and by mechanism.
- Choi, Larsen & Seppi (2021), *Math. & Fin. Econ.*: VWAP/TWAP benchmark execution creates predictable intraday price pressure.
- Holmberg, Lönnbark & Lundström (2013), *Finance Research Letters* 10(1): ORB on crude futures profitable in-sample but **not robust across sub-periods** — driven by the high-vol period. Counter-evidence on record.
- Rosa (2022), *J. Futures Markets* 42(12): intraday-momentum predictability regime-dependent post-2013. Counter-evidence on record.

## Deviations from the source (forced by the brief, stated before testing)
- Decisions at 60-min marks (10:00–15:00) instead of 30-min. Untested in the paper.
- Instrument is ES futures (MES sizing) not SPY; overnight session exists but the rule only uses O, C_prev and RTH hourly closes.
- Base stop = opposite band (the paper's simple variant), not the VWAP-enhanced stop.
- 4h bars are used for **sizing** (realized-vol targeting), not for the band; the band follows the paper's time-of-day noise definition because it captures intraday vol seasonality that a √time scaling of 4h vol would not.
