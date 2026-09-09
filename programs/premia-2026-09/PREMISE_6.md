# PREMISE 6 — Trend Breadth: Fixed 12-Month TSMOM with Class-Balanced Risk on 38 ETFs

**Status:** FROZEN 2026-09-08 after the P3 post-mortem and **before `data_breadth/` has been built**. The universe below is declared here, before download. Zero free parameters.

## Why this premise exists after P3 died
P3 registered the prediction that trend's edge is *breadth*. It failed on 20 ETFs with per-window lookback selection (stitched 0.36; TSH 0.52). Two things in that result were pre-specified and point forward: the fixed 12-month rule scored 0.60 with no selection, and TSH's advantage came from a 0.70-correlated long-everything book. P6 tests the breadth prediction properly: **one fixed rule** (no selection noise), **risk balanced across asset classes** (so equity beta cannot dominate the book), on the broadest free ETF universe with history from 2007. Disclosure: choosing L = 12 is informed by P3's in-sample table on the overlapping 20 instruments over the same period (a mild contamination); it is also Moskowitz–Ooi–Pedersen's canonical lookback, which is why it is the one fixed. This premise is a **new trial** and is charged as such in the Deflated Sharpe.

## Economic / behavioural mechanism
As P3: slow information diffusion, anchoring and disposition effects (under-reaction), then herding and performance chasing (over-reaction), plus non-price-sensitive flows. The mechanism is common to all asset classes; the Sharpe of a trend book scales with the number of *independent* trends it can hold, which is why the literature's Sharpe > 1 requires 50+ markets and why a US-equity-heavy ETF book cannot get there.

## Falsifiable statement
Across 38 ETFs in five asset classes with risk equalised across classes, the sign of the trailing 12-month excess return positively predicts next-month excess return, and the resulting long/short portfolio earns a net Sharpe **exceeding the same construction driven by the sign of the historical mean (TSH)**. If TSH ≥ TSMOM again with class-balanced risk, the breadth hypothesis is falsified for ETF-implementable trend and the family is closed.

## Where it should fail (pre-stated)
As P3 (trend droughts, V-reversals, correlation spikes), plus: country and sector ETFs are 0.7–0.9 correlated within class, so the *effective* breadth gain from 20 → 38 may be far below the nominal one; class balancing forces risk into currencies and commodities, whose ETF costs are the highest in the book.

## Universe (declared before download; superset of P3's 20)
- **Equities (14):** SPY QQQ IWM EFA EEM EWJ EWG EWU EWA EWC EWZ EWH EWY FXI
- **Bonds (8):** TLT IEF LQD HYG TIP MBB BWX EMB
- **Commodities (7):** GLD SLV USO UNG DBC DBA DBB
- **Currencies (7):** UUP FXE FXY FXA FXB FXC FXF
- **Real estate (2):** VNQ RWX
Eligibility as P3 (261st valid price). All listed by 2007-12; all still exist (survivorship stated: broad-proxy ETFs that closed — e.g. currency trusts FXS/FXM, some commodity notes — are excluded because their history is not free).

## Exact rule (frozen, zero parameters)
Identical to P3 except where stated.
- `x_i,t` excess returns (DTB3/360); σ_i,t and Σ_t = EWMA (COM 60), P3 conventions (`premise3/strategy.py`).
- **Signal at month-end t:** `s_i,t = sign(Σ x_i over the last 252 days)`; zero → 0. **L = 12, fixed.**
- **Class-balanced raw weights:** for class c with n_c,t eligible instruments and C_t classes with ≥ 1 eligible instrument, `w̃_i,t = s_i,t · (0.40/σ_i,t) · (1/n_c,t) · (1/C_t)` (Hurst–Ooi–Pedersen's equal-risk-across-classes construction; from memory, not re-verified today).
- Portfolio scaling `λ_t = 0.10/√(w̃ᵀΣ_t w̃)`; gross cap 3×; execution at close t+1; costs 5 bp (SPY QQQ IWM EFA EEM TLT IEF LQD HYG GLD VNQ) / 10 bp (all others); borrow 1 %/yr; stress ×1.5.

## Benchmarks (same universe, class balance, sizing, costs, calendar)
- **TSH:** `s_i,t = sign(expanding mean of x_i)` — the falsification benchmark.
- **Class-balanced risk parity:** all `s = +1`.
- 60/40 and SPY for context. Correlations of the leg with SPY, P3 (`premise3/daily_pnl_wf.csv`), P4, P5.

## Tests (stitched calendar 2010-07-01 → 2024-06-30, same as P3/P4/P5)
1. **Premise test:** pooled monthly panel `x_i,t+1/σ_i,t ~ sign(Σ x over prior 252 d)`, clustered by month, on the 38-ETF panel: **t > 2**; report per class.
2. **Fixed rule** full span and stitched: Sharpe (baseline / ×1.5), return, vol, max DD, avg gross leverage, cap-binding %, turnover, long/short legs, per-class P&L, P&L and Sharpe per test year.
3. **Permutation test:** 500 day-shuffles of the 38-column excess-return matrix (rows as units, from the first date all 38 are listed; re-cumulated onto the original dates; the signal is endogenous so it is scrambled automatically); p = share ≥ real. Gate (d).
4. **Sensitivity (report only, changes nothing):** L ∈ {6, 12, COMBO(3/6/12)} and 1/N vs class-balanced weighting, stitched Sharpe each — four extra numbers so the reader can see whether the fixed choice sits on a plateau.
5. **Gate:** (a) stitched Sharpe ≥ 0.5; (b) TSMOM > TSH; (c) ≥ 8/14 positive test years; (d) p < 0.05.

## Honest expectations
Stitched 2010–2024 Sharpe **0.45–0.75**. TSH with class balance will be lower than P3's 0.52 (less equity beta) — perhaps 0.3–0.5. Prior of clearing the gate: **~35 %**. If it passes, its ensemble role is the crisis-alpha / long-gamma leg against P4's short-gamma.

## What I will NOT do
Change L, the class weights, the universe, or rebalance frequency after seeing results; add carry/vol filters; re-open P3; re-open OOS.
