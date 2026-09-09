# PREMISE 5 — Carry: FX Interest Differentials and the US Term Premium

**Status:** FROZEN 2026-09-08 after literature verification and **before the carry dataset (`data_carry/`) has been built**. The data build may perform hygiene checks only; no return statistic conditioned on carry may be computed before this document is frozen. The FX universe below is declared here, before download.

## Economic / behavioural mechanism
Carry is the return an asset earns if its price does not change (Koijen, Moskowitz, Pedersen & Vrugt 2018). It is a compensation for bearing risks that are concentrated in bad times — funding-liquidity and crash risk in currencies (Brunnermeier, Nagel & Pedersen 2009), inflation and duration risk in bonds — plus a behavioural component: uncovered interest parity fails because investors under-react to persistent rate differentials and because high-carry positions are crowded and unwind abruptly. The empirical regularity is that carry predicts returns across asset classes, and that the failure of UIP is one of the most replicated results in international finance (Fama 1984; Lustig, Roussanov & Verdelhan 2011).

## Falsifiable statement
(1) **FX**: across six G10 currency ETFs against the USD, the 3-month interest differential positively predicts next-month excess return, and a rank-weighted long-high-carry / short-low-carry portfolio earns a positive net Sharpe. (2) **Bonds**: the sign of the US term spread (10y/20y constant-maturity yield − 3-month bill) positively predicts the next-month excess return of the corresponding duration ETF, and a sign-timed position earns a higher net Sharpe than always-long. If the carry-timed leg does not beat its no-signal counterpart (equal-weight long basket for FX; always-long for bonds), the carry premise is unsupported even if the P&L is positive.

Predicted: pooled panel t > 2 for FX; t > 2 for bonds; timed leg Sharpe > no-signal counterpart Sharpe.

## Where it should fail (pre-stated)
- **Crash / deleveraging episodes**: 2008, Mar 2020, Aug 2024 (yen carry unwind) — carry is short crash risk; a rank portfolio is long AUD/short JPY exactly then.
- **Rate-compression regimes** (2010–2021): G10 differentials were < 1 %; the FX signal is then mostly noise and costs dominate. This is most of the walk-forward.
- **Bond regime shifts**: the term spread was positive throughout 2009–2018 (the rule is simply long duration) and inverted 2019, 2022–2024; a sign rule gets few independent bets and can lose badly when the curve un-inverts into rising long yields (late 2024).
- Breadth: six currencies and one yield curve give far less diversification than Koijen et al.'s 20+ currencies and 10 bond markets; the literature Sharpe (≈ 0.5–0.9 per class) will not be reached with this breadth.

## Universe and data (fixed)
- **FX**: FXE (EUR), FXY (JPY), FXA (AUD), FXB (GBP), FXC (CAD), FXF (CHF) — the six surviving CurrencyShares trusts (all listed by Feb 2007). Survivorship stated: FXS (SEK), FXM (MXN), FXSG etc. were delisted; they are excluded because their history is not freely available, not because of performance. ETF total returns already embed the foreign deposit rate less fees.
- **Rates**: OECD 3-month interbank rates, monthly (FRED `IR3TIB01xxM156N`) for USD, EUR, JPY, AUD, GBP, CAD, CHF. **Used with a one-month lag** (at month-end m the value for month m−1), which removes any publication-timing question at negligible cost given the persistence of differentials.
- **Bonds**: IEF (7–10y) paired with DGS10; TLT (20y+) paired with DGS20; DTB3 as the short rate (all daily, FRED). Yields observed at month-end t are used for the signal at t (published next business day, covered by the 1-day execution lag).
- Daily rf for excess returns: DTB3/360 as in P3.

## Exact rule (frozen)
Monthly, at the last trading day t of each month; weights traded at the **close of t+1** and held to the next rebalance (P3 convention).

**FX sleeve** — carry_i = i_foreign − i_USD (month m−1). Three variants, one of which is selected per walk-forward window:
- `XS`: rank weights, `w̃_i = rank(carry_i) − 3.5`, normalised so Σ|w̃| = 1 (dollar-neutral; Koijen et al. eq. 5 form).
- `TS`: `w̃_i = sign(carry_i) / 6` (time-series carry against the USD).
- `BOTH`: `w̃ = ½(w̃_XS + w̃_TS)` renormalised to Σ|w̃| = 1.
Then `w = λ w̃`, `λ = 0.10 / √(w̃ᵀ Σ_t w̃)`, Σ_t the annualised EWMA covariance (COM 60) of daily excess returns to t; gross cap 3.0.

**Bond sleeve** — for j ∈ {IEF, TLT}: `s_j = sign(y_j,t − bill_t)`; `w̃_j = s_j · (0.40/σ_j,t) / 2`; then the same 10 % portfolio scaling and 3× cap. σ = annualised EWMA std (COM 60).

**Leg** = ½ × FX-sleeve daily P&L + ½ × bond-sleeve daily P&L (fixed equal weight; each sleeve already targets 10 %). Missing price on a rebalance day → prior weight kept.

**Costs**: FX ETFs 10 bp one-way, bonds 5 bp, on turnover Σ|Δw|; short borrow 1.0 %/yr on short notional (all six FX trusts and both bond ETFs are easy-to-borrow; unverified, stressed). Stress ×1.5. Book $100k.

## Free parameter (1) and grid
| Param | Grid |
|---|---|
| FX variant | {XS, TS, BOTH} |

Nothing else is tunable. The bond sleeve has no parameter. The one-month rate lag, COM 60, 10 % targets, ½/½ sleeve weight, monthly rebalance and cost schedule are fixed.

## Benchmarks (same instruments, sizing, costs, calendar)
- **FX no-signal**: equal-weight long all six (short USD), 10 % vol-scaled — the naive currency premium.
- **Bond no-signal**: always-long IEF + TLT, same sizing — the naive term premium.
- **Leg no-signal**: ½/½ of the two. Gate (b) compares the timed leg to this.
- SPY buy-and-hold for context; correlation of the leg with SPY, with P3 and with P4 stitched series.

## Walk-forward and permutation tests
Same 14 test windows as P3/P4 (2010-07-01 → 2024-06-30; first train 2007-07-01 → 2010-06-30). FX variant chosen per window by baseline net Sharpe of the *leg* on train. Grid-sensitivity table per window.
- **(i)** best variant on the full in-sample span; **(ii)** 300 permutations; **(iii)** walk-forward; **(iv)** 200 permutations of the full walk-forward.
- **Permutation scheme (exogenous signal)**: shuffle the order of trading days for the 8-instrument daily excess-return matrix (each day's cross-sectional vector moves as a unit, preserving cross-asset correlation), re-cumulated onto the original date index; the carry and term-spread signal series stay on their original dates. Restricted to dates from the first day all eight instruments are listed. Vol, covariance, sizing, costs and per-window selection re-run on each permutation. Drift is preserved under the null, so (iv) measures the carry-*timing* contribution — the same question gate (b) asks directly.

## Pass / fail (pre-stated)
1. **Premise test**: (FX) pooled monthly panel `x_i,t+1 / σ_i,t ~ carry_i,t`, SE clustered by month, **t > 2**; (bonds) monthly `x_j,t+1 / σ_j,t ~ (y_j,t − bill_t)`, Newey–West 3 lags, **t > 2** for at least IEF. Report both; the premise passes only if both do.
2. **Gate** (all must hold): (a) stitched WF net Sharpe of the leg **≥ 0.5**; (b) leg Sharpe **> leg no-signal** Sharpe; (c) ≥ 8 of 14 test years positive; (d) WF permutation **p < 0.05**. Sleeve-level Sharpes are reported but do not gate.
3. **Target**: enters the ensemble per Programme v2; OOS opened once with the ensemble.
4. **Robustness**: 20-day block bootstrap (5,000 reps); costs × 0.5 / × 1.5.

## Honest expectations
Stitched 2010–2024 net Sharpe **0.2–0.6**: rate compression makes the FX sleeve weak for a decade, and the bond sleeve is mostly a long-duration bet that did well until 2021 and badly after. Prior of clearing the gate: **~25 %**. This is the lowest-prior leg; it is included because carry is the third canonical, economically distinct premium, and a passing leg with ρ ≈ 0.1 to trend and VRP is worth more to the ensemble than another trend variant. A failed leg costs tokens, nothing else.

## What I will NOT do
- Add momentum or value overlays, currency-vol filters, more currencies from paid sources, international bond ETFs (BWX/IGOV: short history, one signal source), change the rate lag, sleeve weights or rebalance frequency after seeing results. Not re-open OOS.

## Literature anchors (verified against primary sources 2026-09-08 unless marked)
- Koijen, Moskowitz, Pedersen & Vrugt (2018), *JFE* 127(2): carry predicts returns in every asset class; rank-weighted portfolios; currency carry Sharpe ≈ 0.7 and global bond carry ≈ 0.9 (1983–2012 gross, 20 currencies / 10 bond markets); carry drawdowns coincide with global recessions and liquidity crises. (Figures from the published paper; not re-verified today — marked.)
- Brunnermeier, Nagel & Pedersen (2009), *NBER Macro Annual*: carry trades are short crash risk; unwind when funding liquidity dries up. (Not re-verified today.)
- Lustig, Roussanov & Verdelhan (2011), *RFS* 24(11): carry returns are a priced slope factor. (Not re-verified today.)
- Fama & Bliss (1987), Campbell & Shiller (1991): forward spread / term spread predicts bond excess returns. (Classic; not re-verified today.)
- Data availability verified 2026-09-08: FRED `IR3TIB01` monthly series live for all seven currencies (USD from 1964, EUR from 1994, CHF from 1999, JPY from 2002); DGS10 from 1962, DGS2 from 1976; CurrencyShares ETF listings 2005–2007 (yfinance; last-observation dates to be reported by the data build).

## Deviations / interpretations stated before testing
- Currency ETFs proxy spot + deposit positions; costs are higher than FX forwards; short borrow assumed available.
- Six currencies and a single yield curve; breadth is far below the literature — the expectation section already discounts for this.
- The bond sleeve's term spread omits roll-down (second-order; would need a full curve) — stated simplification.

## Amendment A1 — 2026-09-08, before `data_carry/` existed and before any carry-conditioned return was seen: zero free parameters
Same motivation and same form as P4 Amendment A1 (P3 post-mortem: fixed literature parameter 0.60 vs per-window-selected 0.36).
- **FX variant is fixed at XS** (rank-weighted, dollar-neutral — Koijen et al.'s canonical construction). No per-window selection; the leg has **no free parameters**.
- {XS, TS, BOTH} is retained as a **sensitivity table only** (full-span and per-test-year Sharpe of the leg under each variant). It cannot change the variant.
- Masters tests: (i) fixed rule full-span; (iii) the same series on the stitched calendar 2010-07-01 → 2024-06-30; (ii)/(iv) collapse into **one permutation test, 500 permutations on the stitched calendar** (exogenous-signal scheme as specified), gate (d). Gates (a)–(c) on the stitched calendar.
- Trial count for the Deflated Sharpe: 1.

## Amendment A2 — 2026-09-08, on receipt of `data_carry/VALIDATION.md` (hygiene only; no return seen): missing-rate rule
The OECD series for EUR and GBP end 2026-01 and JPY 2026-05 (in-sample complete). Rule fixed now for all periods: **a missing monthly rate is carried forward from the last observation for up to 6 months; beyond that the instrument's carry is undefined and its weight is 0**. Rate differentials are persistent enough that a ≤ 6-month carry-forward is a negligible approximation; this affects only OOS/live months and the fix is the same as a live trader sourcing the fixing manually.
