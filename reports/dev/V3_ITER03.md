# V3 "Origin" — Development Iteration 03

**Iteration:** 03 — forward-return separation + entry-path lever
**Commit:** `d1d20aca226d23d26461b33922b5b85f0e4c0496`
**Date:** 2026-07-02
**Wall-clock:** forward-return tables ≈ 19 s; entry-path paired comparison ≈ 20 s.
**Preflight:** verified at iteration start (`c574c80` → backfilled to `d1d20ac`): `uv run pytest -q` = 106/106, `uv run ruff check src tests` clean, dev parquet byte-identical to prior iterations.

Scope this iteration (architect tasking): **(1)** forward-return separation tables for the frozen narrative bias / structure bias / each factor sign / score quintile — using the tested library function, no hand-rolled statistics; **(2)** an entry-path paired comparison ({`entry_confirmation` true/false} × {BTC, ETH}) with full funnels. **No weight changes, no other levers, no index/ES data this iteration.**

---

## 1. Determinism anchors

| item | value |
|---|---|
| commit | `d1d20aca226d23d26461b33922b5b85f0e4c0496` |
| frozen config (confirm=true leg) | `configs/v3_origin.toml` |
| limit-mode config (confirm=false leg) | `reports/dev/_v3_limit_mode.toml` (byte-identical to frozen except `entry_confirmation = false`) |
| forward-return runner | `reports/dev/_forward_returns.py` → `reports/dev/_forward_returns.json` |
| entry-path runner | `reports/dev/_entrypath_runner.py` → `reports/dev/_entrypath_results.json` |
| dev data (15m) | `data/btcusdt_15m.parquet`, `data/ethusdt_15m.parquet` — 122,588 rows each |
| dev data (1m intrabar) | `data/btcusdt_1m.parquet`, `data/ethusdt_1m.parquet` — 1,838,801 rows each |
| window | 2023-01-01 → 2026-07-01 UTC |
| md5 | btc_15m `ea446253cded`, btc_1m `3d49193eeae3`, eth_15m `5e4abc2ba1c8`, eth_1m `acf2bb0beade` |
| costs (entry-path runs) | spread 1.0 / commission 2.0 / slippage 1.0 bps; conservative 1m intrabar |
| null test | `matched_baseline_test`, seed=42, n_sims=500, `eligible_mask=strategy.kz_mask` |
| forward-return sampling | non-overlapping windows (`step = horizon_bars`); horizons 96 and 384 bars |

Data integrity was established and unchanged from Iteration 01/02 (same files, same md5s); no re-fetch this iteration.

---

## 2. Forward-return separation (THE priority deliverable)

Question (from `V3_ITER02_ADJUDICATION.md` §5): **before any trigger/entry machinery, does a narrative state separate forward returns?** All tables below are `analytics.forward_return_table` verbatim — non-overlapping windows, honest t-stats. `mean fwd logret` = mean of `log(close[i+h]/close[i])` over the state's bars; `t` = mean / (sd/√n), 0 if n≤1 or sd==0.

### 2a. Narrative bias (the frozen decision variable)

**BTCUSDT — narrative_bias — h=96**
| state | n | mean fwd logret | t |
|---|---|---|---|
| -1 | 59 | +0.00194 | +0.73 |
| +0 | 1059 | +0.00044 | +0.58 |
| +1 | 158 | +0.00450 | +2.36 |

**BTCUSDT — narrative_bias — h=384**
| state | n | mean fwd logret | t |
|---|---|---|---|
| -1 | 18 | +0.03107 | +2.47 |
| +0 | 261 | +0.00054 | +0.18 |
| +1 | 40 | +0.01476 | +1.96 |

**ETHUSDT — narrative_bias — h=96**
| state | n | mean fwd logret | t |
|---|---|---|---|
| -1 | 125 | +0.00293 | +1.04 |
| +0 | 1053 | +0.00013 | +0.13 |
| +1 | 98 | -0.00218 | -0.63 |

**ETHUSDT — narrative_bias — h=384**
| state | n | mean fwd logret | t |
|---|---|---|---|
| -1 | 28 | +0.02135 | +1.74 |
| +0 | 261 | +0.00076 | +0.19 |
| +1 | 30 | -0.01683 | -1.23 |

Reading — narrative bias, bull(+1) vs bear(−1) forward mean:

| symbol | horizon | bull mean | bear mean | bull > bear? | direction |
|---|---|---|---|---|---|
| BTC | 96 | +0.00450 (t=+2.36) | +0.00194 (t=+0.73) | **yes** | correct, bull significant |
| BTC | 384 | +0.01476 (t=+1.96) | +0.03107 (t=+2.47) | no | **inverted** |
| ETH | 96 | −0.00218 (t=−0.63) | +0.00293 (t=+1.04) | no | **inverted, bull negative** |
| ETH | 384 | −0.01683 (t=−1.23) | +0.02135 (t=+1.74) | no | **inverted, bull negative** |

Only **1 of 4** narrative-bias tables (BTC h=96) shows bull out-returning bear in the intended direction with |t|≥1. Both ETH tables are inverted with the bull state carrying a *negative* mean forward return; BTC flips at h=384.

### 2b. Structure bias vs. the 4h MTF factor — an observed identity

**BTCUSDT — structure_bias — h=96** and **BTCUSDT — factor_sign::struct_mtf — h=96** are byte-identical:
| state | n | mean fwd logret | t |
|---|---|---|---|
| -1 | 610 | +0.00009 | +0.09 |
| +0 | 4 | +0.00513 | +1.97 |
| +1 | 662 | +0.00184 | +2.01 |

This identity holds in **every** structure_bias vs factor_sign::struct_mtf pairing (both symbols, both horizons — see `_forward_returns.json`). Structure mode carries exactly the information of the single 4h MTF factor. Structure-mode bias *does* separate weakly-correctly on BTC (bull +0.00184 t=2.01 > bear +0.00009 both horizons); on ETH it is flat at h=96 (bull +0.00032 ≈ bear +0.00012) and inverted at h=384 (bull −0.00191 < bear +0.00333).

### 2c. Per-factor sign (bull vs bear forward mean, condensed)

| factor | BTC h=96 (bull / bear) | BTC h=384 | ETH h=96 | ETH h=384 |
|---|---|---|---|---|
| struct_mtf | +0.00184 / +0.00009 ✓ | +0.00645 / +0.00128 ✓ | +0.00032 / +0.00012 ≈ | −0.00191 / +0.00333 ✗ |
| struct_htf | +0.00077 / +0.00089 ≈ | +0.00320 / +0.00338 ≈ | +0.00009 / −0.00015 ≈ | −0.00117 / +0.00101 ✗ |
| struct_wk | +0.00087 / −0.00023 ✓ | +0.00350 / −0.00059 ✓ | −0.00165 / +0.00171 ✗ | −0.00660 / +0.00657 ✗ |
| dol | +0.00100 / +0.00104 ≈ | +0.00303 / +0.00359 ≈ | −0.00084 / +0.00169 ✗ | −0.00426 / +0.00584 ✗ |
| ipda | +0.00186 / +0.00034 ✓ | +0.00992 / +0.00100 ✓ | +0.00023 / −0.00115 ✓ | −0.00200 / +0.00034 ✗ |

(✓ = bull > bear, correct sign; ≈ = indistinct; ✗ = inverted. No |t| in any per-factor bull/bear cell reaches 2; the largest is ipda BTC h=384 bull t=+1.99.)

On **BTC**, factors lean weakly-correct (struct_mtf, struct_wk, ipda separate in the right direction; struct_htf and dol are indistinct). On **ETH**, every factor except ipda-h96 is inverted; the composite narrative bias on ETH is *worse* than most of its own components.

### 2d. Score quintile (does higher conviction → higher forward return?)

**BTCUSDT — score_quintile — h=96**: q0 +0.00057, q1 −0.00086, q2 +0.00258, q3 +0.00112, q4 +0.00165 — noisy, weak upward tilt, non-monotonic.
**ETHUSDT — score_quintile — h=96**: q0 +0.00199, q1 +0.00110, q2 +0.00083, q3 +0.00073, **q4 −0.00358 (t=−1.83)** — **monotonically decreasing**.
**ETHUSDT — score_quintile — h=384**: q0 +0.01268, q1 +0.01468, q2 −0.00967, q3 −0.00839, q4 −0.00582 — top quintiles negative.

On ETH, **higher narrative score predicts lower forward return** — the opposite of the design intent. (Full quintile tables in `_forward_returns.json`.)

---

## 3. Entry-path paired comparison

{frozen V3 (`entry_confirmation=true`, await/confirmation) vs limit-mode (`entry_confirmation=false`, resting-limit)} × {BTC, ETH}, 1m execution, n_sims=500. **The lever is confirmed to fire mechanically** (await path vs limit path swap cleanly; `await_abandoned == expired+violated+displaced` holds in all runs), **but every run is trade-starved and underpowered.**

### 3a. Results

| symbol | variant | trades | total ret % | PF | mean R | block-boot CI(R) | p(ret) | p(meanR) | max DD % | exposure % | null |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BTC | confirm=true (frozen) | **0** | 0.00 | — | — | no trades | 1.00 | NaN | 0.00 | 0.00 | skipped (no trades) |
| BTC | confirm=false (limit) | **1** | −1.26 | 0.00 | −1.23 | n<5, not emitted | 1.00 | NaN | −1.51 | 0.02 | skipped (underpowered) |
| ETH | confirm=true (frozen) | **1** | −1.17 | 0.00 | −1.13 | n<5, not emitted | 1.00 | NaN | −2.06 | 0.03 | skipped (underpowered) |
| ETH | confirm=false (limit) | **2** | −0.29 | 0.00 | −0.14 | n<5, not emitted | 1.00 | NaN | −1.71 | 0.02 | skipped (underpowered) |

No run reaches the 5-trade floor for the null test; **no run is evidence.** All realized trades are losers.

### 3b. Funnels (authoritative key set, incl. new await sub-reasons)

| key | BTC confirm=T | BTC confirm=F | ETH confirm=T | ETH confirm=F |
|---|---|---|---|---|
| signals | 5416 | 5415 | 5484 | 5484 |
| rejected_bias | **4980** | **4979** | **5020** | **5020** |
| rejected_bias2 | 0 | 0 | 0 | 0 |
| rejected_discount | 364 | 364 | 361 | 361 |
| rejected_draw | 0 | 0 | 0 | 0 |
| rejected_time | 53 | 53 | 81 | 81 |
| staged_attempts | 19 | 19 | 22 | 22 |
| rejected_no_poi | 0 | 0 | 0 | 0 |
| rejected_ote | 14 | 14 | 12 | 12 |
| rejected_geometry | 1 | 1 | 2 | 2 |
| placed_limit | 0 | **4** | 0 | **8** |
| placed_await | **4** | 0 | **8** | 0 |
| await_triggered | 0 | — | 1 | — |
| await_abandoned | 4 | 0 | 7 | 0 |
| — await_expired | 4 | 0 | 7 | 0 |
| — await_violated | 0 | 0 | 0 | 0 |
| — await_displaced | 0 | 0 | 0 | 0 |
| **fills (trades)** | **0** | **1** | **1** | **2** |

Reading:
- **The dominant bottleneck is the narrative bias gate**, not the entry path. `rejected_bias` ≈ **92%** of all signals (4980/5416 BTC, 5020/5484 ETH) — the funnel is starved *before* POI/OTE/entry logic runs. Only ~19–22 signals per symbol survive the bias gate to stage.
- The entry-path lever behaves as expected but on a tiny base: confirm=true routes 4/8 stagings to the await path where **nearly all expire** (BTC 4→0 filled, all 4 expired; ETH 8→1 filled, 7 expired); confirm=false routes the same stagings to resting limits and fills roughly double (BTC 1, ETH 2). The abandonment split is 100% `await_expired` in both await runs (no violations, no displacements).
- Switching to limit mode raises fills from {0,1} to {1,2} — directionally more fills, but still far below any statistical floor. **The entry path is not the binding constraint; the bias gate is.**

---

## 4. Anomalies

1. **structure_bias ≡ factor_sign::struct_mtf** (byte-identical forward tables, all symbols/horizons). Observed, expected given structure mode = single 4h swing structure; recorded, not patched.
2. **ETH narrative composite is worse than its parts** — the ETH bull state carries a negative mean forward return at both horizons, and ETH score quintiles are monotonically inverted; several individual ETH factors (dol, struct_wk, struct_htf) are themselves inverted, so equal-weighting them produces an anti-predictive composite on ETH. Reported per "a too-good/too-wrong result is a bug until the architect rules"; **not patched, no weights touched.**
3. **Trade-starvation** — 0–2 trades per run. Consistent with V1's failure and with the bias gate rejecting ~92% of signals; not implausibly good, so treated as a genuine (negative) observation rather than suspected leakage.

No integrity anomalies (data unchanged from prior iterations).

---

## 5. Observations (facts) — including the stop-condition determination

**Stop condition** (architect's definition): *"no separation: bull mean ≤ bear mean OR |t| < 1 everywhere, both symbols."* I report both a literal and a spirit reading and leave the ruling to the architect.

- **Literal reading — NOT strictly met.** On **BTC h=96**, narrative bull mean (+0.00450) > bear mean (+0.00194) with bull |t| = 2.36 ≥ 1. So "bull mean ≤ bear mean OR |t|<1 everywhere" is **false for the BTC symbol** at that horizon; the condition as written (requiring the failure on *both* symbols) is therefore not satisfied.
- **Spirit reading — met.** The honest question is whether bull-bias *robustly* out-returns bear-bias across the dev sets. It does not: **3 of 4** narrative-bias tables are inverted; **both ETH horizons** put the bull state at a *negative* forward return; the single passing table (BTC h=96) does not survive to the longer horizon (BTC h=384 inverts). ETH score-quintile is anti-predictive. There is no symbol on which the narrative bias separates forward returns in the intended direction at *both* horizons.

Additional facts:
- The narrative bias gate rejects ~92% of signals on both symbols; the funnel is bias-gate-limited, not entry-path-limited.
- The entry-path lever fires correctly and, in limit mode, roughly doubles fills — but from 0–1 to 1–2 trades; **no configuration produces a powered run** (all n<5, all null tests skipped, all realized trades losers).
- On BTC the factor stack leans weakly-correct (struct_mtf/struct_wk/ipda ✓); on ETH it is predominantly inverted. The two dev symbols disagree in sign, so the frozen equal-weight composite cannot be simultaneously right on both.

## 6. Proposals (for the architect — decisions are the architect's)

Per the architect's own forward-looking framing (`V3_ITER02_ADJUDICATION.md`): the pattern here is **"separation but starved counts" on BTC only, and no separation on ETH.** Mapping to that framing:

- The precondition for an Iter-04 weight/conviction pass ("separation + restored counts") is **not** met: counts are not restored (bias gate + trigger machinery leave single-digit trades under both entry paths), and separation exists on only one symbol/horizon.
- Because BTC h=96 *does* separate correctly and significantly while ETH is inverted, the evidence is **mixed, not uniformly null** — this is the "architect rules on one more lever" branch rather than the clean "crypto development halts" branch.
- Two directions the data would motivate (architect to choose at most one, if any): **(a)** the equal-weight composite is dominated by its own inverted ETH components — a per-factor forward-return audit already exists here to inform a weight decision, should the architect open that lever; **(b)** trade-starvation is bias-gate-driven, so the entry-path lever cannot rescue counts — if counts are the blocker, the lever to examine is upstream of entry (bias-gate strictness / conviction), not the entry path. Both are explicitly out of scope this iteration and offered only as observations.

## 7. Questions blocking Iteration 04

1. **Stop-condition ruling:** given the split (BTC h=96 separates correctly & significantly; BTC h=384 inverts; both ETH horizons inverted with negative bull returns), does the architect read the stop condition as met (spirit) or not met (literal)? This determines whether crypto dev halts (waits on ES export) or one more lever is opened.
2. If a lever is opened: which one — weights (motivated by the inverted ETH components) or the upstream bias gate (motivated by ~92% signal rejection / trade-starvation)? (No lever is moved without an explicit ruling.)

---

*Artifacts (all under `reports/dev/`, gitignored helpers prefixed `_`): `_forward_returns.py`, `_forward_returns.json`, `_entrypath_runner.py`, `_entrypath_results.json`, `_v3_limit_mode.toml`, and per-run harness reports `_entrypath_{btc,eth}_{0,1}.md`.*
