# PREMISE 1 — Market Intraday Momentum via Dealer Hedging Demand

**Status:** FROZEN 2026-09-08, after literature verification and before any strategy code has read price data. No return statistics of the ES dataset have been examined. Only the data-hygiene pipeline (`build_data.py`) has touched the file.

## Economic mechanism
Option dealers and leveraged/inverse ETF providers are structurally **short gamma** on the S&P 500 on most days. When the index has moved since the previous close, they must rebalance in the *direction of the move* (buy after rallies, sell after declines), and this rebalancing is concentrated **into the cash close** because (a) leveraged ETFs rebalance at the close by construction and (b) dealers hedge end-of-day exposure. Late-informed and benchmark-tracking traders add flow in the same direction. The result is documented **positive autocorrelation between the day-so-far return and the last-half-hour return** — "market intraday momentum" (Gao, Han, Li & Zhou, JFE 2018), with the hedging-demand mechanism established across global index futures including ES (Baltussen, Da, Lammers & Martens, JFE 2021).

Why this should be a *persistent* edge rather than a stale anomaly: the flow is **mechanical and non-discretionary** (fund mandates, dealer risk limits), so it cannot simply be arbitraged away without someone else absorbing the same inventory risk.

## Falsifiable statement
On ES, the return from the previous cash close (16:00 ET) to 15:00 ET **positively predicts** the return from 15:00 ET to 16:00 ET. The effect is **larger in absolute magnitude when the day-so-far move is large relative to recent volatility**.

Predicted sign: **positive** regression coefficient of r(15:00→16:00) on r(prev 16:00→15:00), t > 2 in-sample.

## Where it should fail (pre-stated)
- Low-volatility, small-move days: hedging demand ∝ |move| × gamma, so near-zero day-so-far returns carry no signal. A version that trades every day should be strictly worse than one gated on |move|.
- Days when dealers are net **long** gamma (typically after large option-selling flows, or in prolonged calm regimes) — the effect can reverse. We do not have dealer gamma data; this is an accepted source of noise, not a parameter.
- If the effect has been arbitraged away post-2018 publication, the walk-forward test windows 2019–2024 will show it, and the premise dies at the gate.

## Why it fits the brief
- **1h execution bars**: the trade is entered at the open of the 15:00 ET bar and exited at the 16:00 ET bar open. One decision per day.
- **4h anchor**: realized volatility of 4h bars (CME-session-aligned) defines the volatility unit against which the day-so-far move is measured and sets the position size.
- **Long and short**: direction = sign of the day-so-far return; symmetric by construction.

## Exact rule (to be frozen)
Let σ₄ₕ = std of 4h log-returns over the last **L** 4h bars, scaled to a 22-hour horizon: σ_day = σ₄ₕ · √5.5 (there are ≈5.5 four-hour bars from 16:00 ET to 15:00 ET the next day; use the actual count if the implementer prefers — state which).

At 15:00 ET each RTH weekday:
1. r_sofar = ln(P₁₅:₀₀ / P_prev16:00), where P_prev16:00 is the open of the previous day's 16:00 ET 1h bar (i.e. the 16:00:00 print) and P₁₅:₀₀ is the open of today's 15:00 ET bar.
2. z = r_sofar / σ_day.
3. If |z| ≥ **k**: enter position with sign(z) at the open of the 15:00 bar (fill = open + slippage in the adverse direction). Else: no trade.
4. Exit at the open of the 16:00 ET bar (fill = open − slippage). No stop, no target. Position is never held overnight, so rolls never intersect a position.

Skip days: early closes (day before Thanksgiving, Christmas Eve, etc. — 13:00 ET close) → no trade. Days where the 15:00 or 16:00 bar is missing → no trade. Days where the previous 16:00 bar is missing → no trade.

## Free parameters (2) and their grids
| Param | Meaning | Grid |
|---|---|---|
| k | entry threshold in day-vol units | {0, 0.25, 0.5, 0.75, 1.0} |
| L | 4h-vol lookback in 4h bars | {18, 30, 60} (≈ 3, 5, 10 sessions) |

Nothing else is tunable. Entry/exit times, the predictor start (previous cash close), and the exit rule are fixed by the mechanism.

## Fixed (not tuned)
- Position sizing: constant-vol target **12% annualized** on a **$100k account**, in whole **MES** contracts. Per-trade notional N = (0.12/√252 · 100,000) / σ_1h, where σ_1h = σ₄ₕ / 2 (1h vol from 4h vol). Contracts = round(N / (5 · P)). Cap at 40 MES (= 4 ES, ≈ 12× leverage) as a hard sanity limit; report how often the cap binds.
- Costs: MES $1.00 round-trip fees; slippage 1 tick ($1.25) per side baseline, 2 ticks stress. Backtest on ES prices with MES multiplier ($5/point) — MES tracks ES tick-for-tick.
- Walk-forward: 3y train / 1y test, stepping 1y, over in-sample 2010-06 → 2024-06. Parameters (k, L) chosen per window by **net Sharpe on train**. Stitched test-window equity = in-sample result.

## Pass / fail criteria (pre-stated)
1. **Premise test** (independent of the trading rule): pooled in-sample OLS of r(15→16) on r_sofar, HAC standard errors: coefficient > 0, t > 2. If this fails, the premise is dead regardless of any backtest.
2. **Gate**: stitched walk-forward net Sharpe ≥ 1.0 with ≥ 800 trades. If it fails, dead; no OOS look.
3. **Target**: OOS (2024-07-01 → 2026-07-01) net Sharpe ≥ 1.5, computed as mean(daily P&L)/std(daily P&L)·√252 over all trading days (flat days count as 0). Also report: max drawdown, hit rate, long vs short Sharpe, average |z| of traded days, cap-binding frequency.
4. **Robustness**: (a) block bootstrap of daily P&L (block = 20 days), 5,000 reps → 5th-percentile Sharpe and 95th-percentile drawdown; (b) costs and slippage ×0.5 and ×1.5.

## What I will NOT do
- Add filters (day-of-week, VIX level, FOMC days, month-end) after seeing results.
- Change the predictor start time or the trade window after seeing results.
- Try 15:30–16:00 "because the paper used half-hours" after the 1h version fails. If 1h fails, the premise fails for this brief.
- Re-open OOS.

## Amendment A1 — 2026-09-08, after data validation, before any strategy result
Two predictor-continuity skips, forced by facts of the dataset discovered in `data/VALIDATION.md` and the SPY cross-check (not by any P&L):
1. **Roll-crossing days:** prices are unadjusted; on the first session after a roll the previous 16:00 bar belongs to the old contract and today's 15:00 bar to the new one, so `r_sofar` would contain the calendar spread (median 7.5 pts, max 73.75 pts ≈ 1.2%). Rule: skip day d if `instrument_id(15:00 bar on d) ≠ instrument_id(prev 16:00 bar)`. ≈65 days over 14 years.
2. **Day after an early close:** if the immediately preceding weekday has RTH bars but no 16:00 bar (13:00 ET early close), the last LETF rebalance was at that 13:00 close, not at the 16:00 bar two sessions back, so the predictor no longer matches the mechanism. Rule: skip d. ≈3 days per year.
Neither rule has a parameter. Both only remove days; they cannot add trades.

## Literature anchors (verified against primary sources 2026-09-08)
- Gao, Han, Li, Zhou (2018), "Market Intraday Momentum", *JFE* 129(2). SPY 1993–2013. Predictor r1 is measured **from the previous close** to 10:00 ET (includes overnight gap). β(r1)=6.94 (×100), R²=1.6%. r1 timing strategy on the last half-hour: 6.67%/yr, SD 6.19%, **Sharpe 1.08**, hit rate 54.4%. Effect concentrated in high-vol tercile (R² 3.3% vs 0.6% low-vol) and crisis periods.
- Baltussen, Da, Lammers, Martens (2021), "Hedging Demand and Market Intraday Momentum", *JFE* 142(1). 60+ futures incl. **ES**, to May 2020. Preferred predictor r_ROD = **prior close → 30 min before close**; target = last 30 min. Pooled equity-futures β_ROD=4.18 (t=7.29). Equity-futures timing strategy **Sharpe 1.73** (6.86%/yr, SD 3.96%). Momentum present only on net-short-gamma days (β=6.63, t=4.78) and absent on long-gamma days (β=0.82, t=1.03). No decay 2000–2020. Positive net Sharpe for S&P futures at one-tick cost.
- **Counter-evidence, stated up front:** Rosa (2022), *J. Futures Markets* 42(12): using S&P futures with the GHLZ-style signal, out-of-sample predictability **disappears** under standard calendar-time tests; a regime-switching model finds the effect in only one regime. This is the main known risk to the premise and is exactly what the walk-forward gate is designed to detect.

## Deviations from the papers (forced by the brief, stated before testing)
- Predictor cut-off and trade window are **60 min** before the 16:00 ET cash close (15:00→16:00), not 30 min, because execution is on 1h bars. This dilutes the signal relative to the papers and is a conservative variant. I will not switch to 30-min windows if the 1h version fails.
- "Close" = 16:00 ET (cash close / LETF rebalance print), not the 16:15 ET futures settlement.
- The |z| ≥ k gate operationalises the papers' "stronger on high-vol / large-move days" finding with a single threshold rather than dealer-gamma data, which we do not have.
