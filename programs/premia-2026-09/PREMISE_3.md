# PREMISE 3 — Multi-Asset Time-Series Momentum (Trend Following), Daily ETF Universe

**Status:** FROZEN 2026-09-08 after literature verification and before any strategy code has read the daily dataset. The 20-ETF universe was declared in `build_daily.py` *before* this document and cannot be changed. No return statistic of that dataset has been examined beyond data-hygiene validation.

## Economic / behavioural mechanism
Trends in asset prices arise because information is incorporated slowly and then over-extrapolated: (1) anchoring and the disposition effect make investors under-react to news, so prices drift toward fundamentals over months; (2) herding, performance chasing and confirmation bias then push prices past fundamentals; (3) non-price-sensitive flows — central-bank operations, corporate hedging, risk-parity and vol-target rebalancing, pension glide paths — create persistent one-directional pressure. Because these forces operate in every asset class, the strategy's real edge is **breadth**: many weakly positive, weakly correlated bets, which is how the literature reaches Sharpe > 1 (Moskowitz, Ooi & Pedersen 2012; Hurst, Ooi & Pedersen 2017). It also carries crisis alpha: long-vol-like payoff in prolonged drawdowns (2008, 2022).

## Falsifiable statement
Across a fixed universe of 20 liquid ETFs spanning equities, bonds, commodities, currencies and real estate, **the sign of an instrument's trailing 3–12-month excess return positively predicts its next-month excess return**, and a portfolio that goes long/short each instrument by that sign, vol-scaled and equal-weighted, earns a positive net Sharpe that **exceeds** the Sharpe of the same portfolio driven by the sign of each instrument's *historical mean* return (the Huang–Li–Wang–Zhou "TSH" benchmark). If TSMOM does not beat TSH, the trend premise is unsupported even if P&L is positive.

Predicted: pooled panel t > 2 on the sign predictor; TSMOM Sharpe − TSH Sharpe > 0 in the stitched walk-forward.

## Where it should fail (pre-stated)
- **Trend droughts**: choppy, mean-reverting macro regimes with muted market moves (2010–2018: SG Trend Sharpe 0.05). AQR attributes this to smaller market moves, not lost efficacy — the walk-forward covers exactly this period, so in-sample numbers will be modest.
- **Sharp reversals** after long trends (V-shaped crashes/recoveries: Mar–Apr 2020, Apr 2025 tariff whipsaw) — trend is short-gamma at turning points.
- **High cross-asset correlation regimes** (Baltas & Kosowski): breadth collapses when everything trades as one risk-on/risk-off factor.
- If Huang et al. are right, TSMOM ≈ TSH and the premise dies at the gate by construction.

## Universe (fixed before this premise; see `data_daily/`)
Equities SPY QQQ IWM EFA EEM EWJ · Bonds TLT IEF LQD HYG TIP · Commodities GLD SLV USO DBC · Currencies UUP FXE FXY FXA · Real estate VNQ. An instrument is **eligible** from the first date it has ≥ 260 trading days of history. Known bias, stated: all 20 still exist (mild survivorship in universe selection; they are broad asset-class proxies, so the effect is small).

## Exact rule (frozen)
Daily adjusted-close total returns `r_i,t`; daily risk-free `rf_t` from 3-month T-bill (DTB3/360). Excess return `x_i,t = r_i,t − rf_t`.
- **Volatility**: `σ_i,t` = annualised EWMA std of daily excess returns with center of mass 60 days (MOP Eq. 1), using data to t.
- **Signal at each month-end t** (last trading day of the month), for lookback L (months, 21 trading days each):
  `s_i,t = sign(Σ x_i over the last 21·L days)`; zero → 0.
  COMBO variant: `s_i,t = mean( sign_3m, sign_6m, sign_12m )` ∈ {−1, −⅓, ⅓, 1}.
- **Raw weight**: `w̃_i,t = s_i,t · (0.40 / σ_i,t) / N_t` over the N_t eligible instruments (MOP Eq. 5).
- **Portfolio vol targeting** (HOP): scale all weights by `λ_t = 0.10 / √(w̃ᵀ Σ_t w̃)` where Σ_t is the annualised EWMA covariance (COM 60) of daily excess returns to t. Then cap gross leverage: if Σ|w_i| > 3.0, scale down to 3.0. Record cap-binding frequency.
- **Execution**: weights computed at the close of t are traded at the **close of the next trading day t+1** (one full day of lag) and held until the next rebalance. Missing price on a rebalance day → keep the prior weight for that instrument.
- **Costs**: one-way 5 bp on SPY QQQ IWM EFA EEM TLT IEF LQD HYG GLD VNQ; 10 bp on EWJ TIP SLV USO DBC UUP FXE FXY FXA (spread + slippage; commissions $0). Charged on turnover Σ|Δw_i| at each rebalance. **Short borrow 1.0 %/yr** accrued daily on short notional. Fund expense ratios are already inside adjusted prices. Stress: all costs × 1.5.
- Daily portfolio P&L series (flat/zero days included) → Sharpe = mean/std · √252 of daily *excess* P&L on a $100k book.

## Free parameter (1) and grid
| Param | Grid |
|---|---|
| L (signal definition) | {3, 6, 12, COMBO} |

Nothing else is tunable. 40 % per-instrument scaling, 10 % portfolio target, EWMA COM 60, monthly rebalance, 1-day lag, 3× gross cap and the cost schedule are fixed by the literature and by realism.

## Benchmarks (computed alongside, same universe, same sizing, same costs)
- **TSH** (Huang et al.): identical construction with `s_i,t = sign(mean of x_i over all history to t)`.
- **Risk parity / long-only**: `s_i,t = +1` for all eligible instruments.
- **60/40** (SPY/IEF) and **SPY** buy-and-hold for context.

## Walk-forward
Train 3y / test 1y, step 1y. Test windows 2010-07-01→2011-06-30 through 2023-07-01→2024-06-30 (**14 windows**); first train window 2007-07-01→2010-06-30. L chosen per window by baseline net Sharpe on train. Stitched test-window daily P&L = in-sample result. TSH and risk parity are computed on the same stitched calendar (they have no parameter).

## Pass / fail (pre-stated)
1. **Premise test** — pooled monthly panel regression `x_i,t+1 / σ_i,t ~ sign(Σ x_i over prior 252 days)`, standard errors clustered by month: **t > 2**. (Huang et al. show bootstrap critical values are higher; this is a screen, not the decisive test.)
2. **Gate** (open OOS only if all hold): (a) stitched WF net Sharpe **≥ 0.5**; (b) **TSMOM stitched Sharpe > TSH stitched Sharpe**; (c) ≥ 8 of 14 test years with positive net P&L. *Why 0.5 and not 1.0:* the window is the documented trend drought; Hurst–Ooi–Pedersen's 67-futures strategy earned only ≈ 0.75 net-of-cost in 2010–2016 and our 20-ETF universe is less diversified with higher costs. Requiring 1.0 here would reject a strategy the 1880–2016 record supports. This threshold is set now, before any result.
3. **Target**: OOS 2024-07-01→2026-07-01, opened once, **net Sharpe ≥ 1.5**; report alongside TSH, risk parity, 60/40 and SPY over the same window, plus max drawdown, realised vol, average gross leverage, cap-binding %, turnover, long vs short leg contribution, per-asset-class contribution.
4. **Robustness**: (a) 20-day block bootstrap of daily P&L, 5,000 reps → 5th-pct Sharpe, 95th-pct drawdown; (b) costs × 0.5 and × 1.5.

## Amendment A1 — 2026-09-08, before any result of this premise was seen: Masters' permutation framework
Added at the user's request, in addition to (not replacing) the tests above. Permutation scheme: shuffle the **order of trading days** (each day's cross-sectional vector of excess returns moves as a unit, preserving marginal distributions and cross-asset correlation, destroying serial dependence and trends), restricted to dates ≥ 2007-04-11 (the first date on which all 20 instruments are listed; earlier data is left untouched and only feeds the beginning of the first train window). Permuted returns are re-cumulated onto the original date index so month-ends, eligibility and walk-forward windows are unchanged. All pipeline steps (vol, covariance, signals, sizing, costs, per-window selection) are re-run on each permutation exactly as on real data.
- **(i) In-sample excellence:** optimise L over the full in-sample span 2007-07 → 2024-06; report the best L and its net Sharpe.
- **(ii) In-sample permutation test:** repeat (i) on 300 permutations; p = share of permuted best-in-sample Sharpes ≥ the real one.
- **(iii) Walk-forward:** as specified.
- **(iv) Walk-forward permutation test:** re-run the full walk-forward (with per-window re-selection of L) on 200 permutations; p = share of permuted stitched Sharpes ≥ the real one.
Note: day-shuffling preserves each instrument's drift, so a long-biased strategy still earns risk premia under the null. This is intended — (iv) then measures the *trend-specific* contribution over and above drift, which is the same question the TSH benchmark asks by a different route.
**Gate criterion (d), added:** walk-forward permutation p < 0.05. The gate now requires (a)–(d).

## Honest expectations
Stitched walk-forward 2010–2024 net Sharpe: **0.3–0.7**. OOS 2024-07→2026-07: contains a strong gold trend and a violent April-2025 reversal; 1.5 is possible only if the long-leg trends dominated. Prior probability of clearing 1.5: **~20 %**. The more likely valuable outcome is a Sharpe 0.7–1.0 portfolio with near-zero equity correlation, which is what this family actually delivers.

## What I will NOT do
- Add carry, value, or vol filters after seeing results; change rebalance frequency; alter the universe; use daily rebalancing "to reduce lag"; change the 0.5 gate after the fact; re-open OOS.

## Literature anchors (verified against primary sources 2026-09-08)
- Moskowitz, Ooi & Pedersen (2012), *JFE* 104(2): 58 futures 1965–2009; 12m sign × 40 %/σ, EWMA COM 60; diversified TSMOM realised vol 12 %, Sharpe > 1 gross; predictive lags 1–12 positive, 13–60 reversal.
- Hurst, Ooi & Pedersen (2017), *JPM* 44(1): 67 markets 1880–2016, 1/3/12 equal combo at 10 % vol; net-of-cost, gross-of-fee ≈ 1.1; **2010–2016 ≈ 0.75 net-of-cost (0.41 after 2/20 fees)**.
- Babu et al. (2020), *JOIM*: 12m trend Sharpe 1.17 (traditional) / 1.60 (all 82 + factors) through 2017. AQR (2020) *JPM* "You Can't Always Trend": SG Trend Sharpe 0.05 in 2010–2018, attributed to muted market moves.
- **Counter-evidence on record:** Huang, Li, Wang & Zhou (2020), *JFE* 135(3): only 8/55 assets show significant TSMOM predictability; pooled t = 4.34 is below bootstrap critical values; TSH ≈ TSMOM. Baltas & Kosowski (2013): post-2008 breadth loss via correlations.
- ETF implementations: Faber (2007/2013) 10m-SMA Sharpe 0.55 vs 0.32 B&H (costs excluded); Antonacci (2012) long/T-bill dual momentum Sharpe 0.73–0.97 with ~5 bp/yr costs. ETF spread/borrow figures are **unverified from primary sources**; the cost schedule above is chosen conservative and stressed × 1.5.

## Deviations / interpretations stated before testing
- ETFs proxy futures. Costs are higher (spreads, borrow) and leverage is capped at 3×; a live version would use micro futures for most of the universe, so the ETF backtest is the conservative case.
- Monthly rebalance with a 1-day lag rather than daily rebalancing with smoothing: cheaper, unambiguous, slightly slower.
- The 4h/1h framing of premises 1–2 does not apply; this is a daily strategy by scope decision.
