# PREMISE 4 — Volatility Risk Premium via VIX-Futures Basis Timing

**Status:** FROZEN 2026-09-08 after literature verification (primary sources, see anchors) and **before any VX futures data has been downloaded**. The data build (`build_vx.py`) may perform hygiene checks only (coverage, scaling, calendar); no return statistic, basis statistic beyond a sign-share sanity check, or P&L may be computed before this document is frozen.

## Economic / behavioural mechanism
Investors pay a premium for protection against volatility spikes. In VIX futures that premium shows up as the **basis**: the future trades above spot VIX (contango) most of the time and converges to spot at settlement, so a short position earns the roll as a compensation for bearing spike risk (Eraker & Wu 2017: −40 to −50 %/yr for the 1-month constant-maturity future). The premium is not constant: it collapses or turns negative exactly when risk is highest (Cheng 2019, "low premium-response puzzle"; premium fell from early September 2008), and backwardation then predicts *rising* futures prices. The basis is therefore a real-time, model-free read of the premium's sign and size (Simon & Campasano 2014; Johnson 2017 for the term-structure slope).

## Falsifiable statement
The daily roll yield of the held VIX future, `roll_t = (F_t − VIX_t) / F_t / DTE_t` (fraction of price per business day to expiry), **negatively predicts that contract's next-day return**, and a rule that is short when the roll is above a threshold and long when it is below the negative threshold earns a net Sharpe that **exceeds an always-short position in the same contract with the same sizing and costs**. If timing does not beat always-short, the basis carries no information beyond the unconditional premium and the premise is unsupported even if the P&L is positive.

Predicted: daily regression t < −2 (HAC); timed Sharpe − always-short Sharpe > 0 in the stitched walk-forward; timed max drawdown smaller than always-short.

## Where it should fail (pre-stated)
- **Spike onset with a 1-day execution lag**: the rule is short into the first day of a spike (Feb 2018, Mar 2020, Aug 2024, Apr 2025) and can only react at the next settle. This is the dominant loss mechanism and is not to be patched with intraday execution or stops.
- **Structural change after Volmageddon**: retail short-vol ETPs de-levered in Feb 2018; no peer-reviewed study documents basis-timing performance in 2018–2025. The 2020 and 2022 windows are in the walk-forward; the OOS window contains two spikes.
- **Low-VIX regimes** where the point basis is small: handled by defining the roll in *fractional* terms (a 1-point basis on VIX 10 is a large roll), so this should not be a failure mode; if it is, the point-based rule in the literature was regime-specific.
- Settlement-time mismatch: VX settles 15:00 CT, VIX closes 15:15 CT; the measured basis carries 15 minutes of noise.

## Instrument and data (fixed)
CBOE VX monthly futures, per-expiry daily settles (free CBOE files, 2004–present; pre-2007-03-26 prices ÷ 10 for the contract rescale), spot VIX daily close. Business days to expiry are counted on the VIX trading calendar. **Held contract**: the front month while it has ≥ 10 business days to expiry, otherwise the second month (Simon & Campasano's liquidity rule). Daily return of the held position = same-contract settle-to-settle return; on a roll day the outgoing contract's return is taken to that settle and the new contract is held from it (no P&L jump). Live instrument: VX or VXM (micro, $100 × index).

## Exact rule (frozen)
At each daily settle t:
- `roll_t = (F_t − VIX_t) / F_t / DTE_t` for the held contract (DTE in business days ≥ 1).
- State machine with threshold θ and exit at θ/2 (hysteresis taken from Simon & Campasano's $100 entry / $50 exit; not a free parameter):
  - flat → **short** if `roll_t > θ`; flat → **long** if `roll_t < −θ`;
  - short → flat if `roll_t < θ/2`; long → flat if `roll_t > −θ/2`;
  - short → long directly if `roll_t < −θ` (and vice versa).
  - θ = 0 degenerates to `s_t = −sign(roll_t)`.
- **Sizing**: `w_t = s_t · 0.10 / σ_t`, σ_t = annualised EWMA std (COM 60) of the held-series daily returns to t; gross cap 3.0 (should never bind). Book $100k; VX P&L is an excess return (collateral earns rf).
- **Execution**: the position decided at settle t is established at settle t+1 and earns the held-contract return from t+1 to t+2 onward (identical convention to P3). Rolls happen at the settle on which the front drops below 10 business days.
- **Costs**: one-way cost per unit notional = (1 tick 0.05 pt + $1.25 commission ⇒ 0.05125 pt) / F_t, charged on |Δ notional| including both legs of every roll. Stress: 2 ticks. No borrow (futures).
- Daily P&L series (flat days included) → Sharpe = mean/std · √252.

## Free parameter (1) and grid
| Param | Grid |
|---|---|
| θ (roll threshold, fraction of price per business day) | {0, 0.0025, 0.0050, 0.0075} |

At VIX ≈ 20, 0.0050/day ≈ Simon & Campasano's $100/day. Nothing else is tunable: the 10-day roll rule, θ/2 exit, COM 60, 10 % target, 1-day lag and cost schedule are fixed.

## Benchmarks (same held series, sizing, costs, calendar)
- **Always-short** (`s_t = −1`): the falsification benchmark — the unconditional VRP.
- **Always-long** (`s_t = +1`) for symmetry; **SPY buy-and-hold** for context; report the daily correlation of the timed leg with SPY and with P3's stitched series.

## Walk-forward and permutation tests
Train 3y / test 1y, step 1y; the **same 14 test windows as P3** (2010-07-01 → 2024-06-30; first train 2007-07-01 → 2010-06-30). θ chosen per window by baseline net Sharpe on train. Grid-sensitivity table for every window.
- **(i)** best θ over the full in-sample span and its Sharpe; **(ii)** repeat on 300 permutations; **(iii)** walk-forward as above; **(iv)** full walk-forward on 200 permutations.
- **Permutation scheme (exogenous signal)**: shuffle the order of the held-series daily returns (from the first date with a valid held contract and 60-day EWMA warm-up); re-cumulate onto the original date index; the `roll_t` series stays on its original dates. Vol, sizing, costs and per-window selection are re-run on each permutation. The null is "the roll has no predictive relation to the held-contract return"; drift (the unconditional premium) is preserved under the null, so (iv) measures the *timing* contribution — the same question the always-short benchmark asks directly. Caveat, stated: both series are autocorrelated, so the permutation p is slightly anti-conservative; it is a gate, not the sole test.

## Pass / fail (pre-stated)
1. **Premise test**: `r_{t→t+1} ~ roll_t` (held-series next-day return on today's roll), Newey–West 5 lags, over the in-sample span: **t < −2**. Also report the 21-day-forward version (Simon & Campasano's horizon) and β by contango / backwardation halves.
2. **Gate** (all must hold): (a) stitched WF net Sharpe **≥ 0.5**; (b) timed Sharpe **> always-short** Sharpe; (c) ≥ 8 of 14 test years positive; (d) WF permutation **p < 0.05**. *Why 0.5:* the literature's ~0.8–1.0 is 2007–2016, before Volmageddon, with hedging; our window includes 2018, 2020 and 2022 unhedged with a 1-day lag.
3. **Target**: enters the ensemble per Programme v2; OOS opened once with the ensemble. Report Sharpe, max DD, worst day, time-in-market, long vs short contribution, roll cost share of turnover, cap-binding %.
4. **Robustness**: 20-day block bootstrap (5,000 reps); costs × 0.5 / × 1.5 (2 ticks).

## Honest expectations
Stitched 2010–2024 net Sharpe **0.4–0.9**, with a fat left tail (worst days −10 to −20 % of book despite 10 % target vol; ex-ante EWMA vol understates spike risk). Prior of clearing the gate: **~45 %**. OOS: two spikes in the first ten months, steep contango otherwise — the realised print could be anywhere from −0.5 to 1.5. Its ensemble value is a return stream nearly uncorrelated with trend on average and negatively correlated in crises (short-gamma vs long-gamma), which is exactly what the combination rule needs.

## What I will NOT do
- Add an ES hedge (would be a second instrument and a fitted hedge ratio), a VIX-level filter, stops, intraday execution, Cheng's model-based premium, the second-month slope as an extra signal, or a different roll rule after seeing results. Not re-open OOS.

## Literature anchors (verified against primary sources 2026-09-08)
- Simon & Campasano (2014), *J. Derivatives* 21(3): 2007–2011; basis predicts futures price changes (coef −0.79, R² ≈ 10 %) but not VIX; short when contango and roll > $100/day, long when roll < −$100/day, exit at $50; 62 short trades hedged Sortino 1.26, 40 long trades Sortino 1.03; costs ≈ $140/trade round trip.
- Cheng (2019), *RFS* 32(1): premium ≡ risk-neutral − physical expected VIX, mean +0.70 pt; premium falls as risk rises (Sept 2008); Sharpe: always-short 0.57, cash/short 0.87, long/short alpha 14.6 %/yr; S&P 0.41.
- Eraker & Wu (2017), *JFE* 125: 1-month constant-maturity VX −39 %/yr geometric 2006–2013; VXX −97 % Jan 2009 → Mar 2013.
- Johnson (2017), *JFQA* 52(6): term-structure slope predicts next-day VX returns (t ≈ −3), 33/36 coefficients significant across maturities.
- Augustin, Cheng & Van den Bergen (2021), *FAJ* 77(3): Volmageddon mechanics; premium-sign conditioning cleaner than contango conditioning; **no** quantification of basis timing through Feb 2018 — unverified. No peer-reviewed evidence for 2020–2025 — unverified.
- Costs: CFE VX multiplier $1,000, tick 0.05 = $50; VXM $100, tick $5. Spread ≈ 1 tick at the front (Simon & Campasano report 0.06–0.068 pt average closing spread). Vendor figures for 2024–26 not verified.

## Deviations / interpretations stated before testing
- Fractional roll instead of dollar roll (scale invariance across VIX regimes); unhedged instead of ES-hedged (one instrument, no fitted ratio); symmetric long/short.
- 1-day settle-to-settle execution lag is conservative relative to a trader executing at the 16:15 ET print; it is kept for comparability with P3 and to avoid an intraday fill model.

## Amendment A1 — 2026-09-08, before `data_vx/` existed and before any VX return was seen: zero free parameters
Motivated by the P3 post-mortem (fixed literature lookback 0.60 vs per-window-selected 0.36 on 3-year training windows; `RESULTS.md`). This amendment is applied to a different premise and a dataset that has not yet been downloaded; it is recorded as an amendment rather than an edit so the sequence is auditable.
- **θ is fixed at 0.0050** (Simon & Campasano's $100/day at VIX ≈ 20), exit at θ/2. There is no per-window selection; the strategy has **no free parameters**.
- The grid {0, 0.0025, 0.0050, 0.0075} is retained as a **sensitivity table only** (full-span and per-test-year Sharpe for each θ). It cannot be used to change θ. If the fixed θ is the worst of the four, that is reported and the verdict stands.
- Consequences for the Masters tests: with nothing to optimise, (i) is the fixed rule's full-span Sharpe, (iii) is the same series restricted to the stitched calendar 2010-07-01 → 2024-06-30 (kept so the leg shares P3/P5/P6's calendar), and (ii)/(iv) collapse into **one permutation test: 500 permutations of the fixed rule on the stitched calendar, p = share ≥ real**, which is gate (d). Gates (a)–(c) are computed on the stitched calendar.
- Trial count for the Deflated Sharpe: 1 for this premise (the sensitivity table is not a selection).
