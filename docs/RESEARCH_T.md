# Program T — literature research: diversified time-series momentum

- Date: 2026-07-06 (architect)
- Purpose: after three programs found nothing tradable at *intraday*
  horizons (SMC folklore; its descriptive claims; the best published
  session anomalies — all sub-costs on 16y of ES), select the next
  hypothesis family by fixing the failure mode itself: pick the
  strategy class whose **edge-to-cost ratio** is structurally different.
- The user's brief: an optimized, empirically backed strategy using a
  confluence of ideas, aiming at professional-grade systematic returns.
  The honest translation of "what prop/systematic firms actually do"
  that is reproducible with public data and this harness is
  **diversified trend following with volatility targeting** — the most
  documented systematic strategy in existence.

## Why this family fits where everything intraday failed

The intraday programs died to one number: effects of 0.5–2 bp/day
against ~1.4 bp round-trip costs. Time-series momentum (TSMOM) holds
positions for weeks to months; per-position gross edges are measured in
tens to hundreds of bp against the same ~1.4 bp cost. Costs stop being
the story; whether the signal is real becomes the only question — which
is exactly what this harness is built to answer.

## The evidence, both sides

**For (deep and multi-venue):**
- Moskowitz, Ooi & Pedersen, *Time Series Momentum*, JFE 2012
  ([SSRN 2089463](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2089463),
  [AQR page](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum)):
  58 futures/forwards over 25+ years; trailing 12-month return sign
  predicts the next month across asset classes; diversified portfolio
  Sharpe ≈ 1.28 vs 0.38 buy-and-hold.
- Hurst, Ooi & Pedersen, *A Century of Evidence on Trend-Following
  Investing* ([PDF](https://fairmodel.econ.yale.edu/ec439/hurst.pdf)):
  positive in every decade since 1880; Greyserman & Kaminski extend a
  representative system to ~800 years (Sharpe ≈ 1.16 gross).
- Live, investable confirmation: the
  [SG Trend Index](https://wholesale.banking.societegenerale.com/en/prime-services-indices/)
  of the 10 largest trend CTAs made **≈ +27% in 2022** while the S&P
  fell 18% and bonds fell 13% — crisis convexity documented in
  [Man Group's dispersion work](https://www.man.com/insights/deep-dive-trend-following)
  and the crisis-alpha literature.

**Against (must be designed for, not hidden):**
- Post-publication decay: out-of-sample studies show weaker performance
  since ~2010; recent multi-year stretches are flat-to-negative
  (e.g. SG Trend ≈ −9% YTD by
  [April 2025](https://www.toptradersunplugged.com/trend-following-performance-report-april-2025/)).
- Attribution critique: a substantial share of TSMOM's alpha comes from
  **volatility scaling and diversification** rather than the timing
  signal itself
  ([Kim, Tse & Wald, JEF 2016](https://www.sciencedirect.com/science/article/abs/pii/S1386418116301379)).
  Consequence for design: volatility targeting is part of the
  *hypothesis*, not an optimization afterthought, and the **portfolio**
  (not any single market) is the primary object under test.
- Single-market TSMOM is weak: realistic per-instrument Sharpe ~0.1–0.3;
  the product works through breadth. Our data budget bounds breadth at
  ~5 development + 4 holdout markets, so the honest expectation is a
  net portfolio Sharpe somewhere in 0.2–0.7, **not** double-digit
  prop-desk returns. Anything dramatically better in-sample will be
  treated as a bug until proven otherwise, per house rule.

## Confluence, done honestly

"Confluence" that survives scrutiny is not stacking indicators on one
chart (the SMC program falsified that form); it is **combining
lowly-correlated return streams**: three trend horizons (1/3/12 months)
voting, across five asset-class-diverse markets, under a common
volatility budget. Each additional sleeve (carry, seasonality) is a
*separate future preregistration* once this one's verdict is in —
Koijen et al.'s *Carry* is the natural second sleeve and needs
term-structure data this program does not buy.

## Expectation setting (the part no one likes to write)

If Stage 1 supports the effect and Stage 2 survives costs, a 4–9 market
portfolio at a 10% per-instrument vol target has historically delivered
mid-single-digit annualized excess returns with double-digit drawdowns.
Higher headline returns are a leverage dial on that same Sharpe, paying
proportionally in drawdown. No model — this one included — changes
that arithmetic; what a careful agent adds is not-fooling-yourself,
which is the scarce input. Sizing/leverage decisions are out of scope
for this repository.
