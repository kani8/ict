# V3 "Origin" — Development Iteration 01

**Baseline of the 5-factor narrative macro stack on both burned dev sets.**

## 1. Header

| Field | Value |
|---|---|
| Study | V3 "Origin" (development phase) |
| Iteration | 01 — baseline, frozen config, no sweep |
| Commit | `93d686a8cb2de4a906bd4a3e1d42a4b9f2c5af58` |
| Config | `configs/v3_origin.toml` (**unchanged** — no CLI param overrides) |
| Dev sets | BTCUSDT, ETHUSDT — 15m base + 1m intrabar, 2023-01-01 → 2026-07-01 |
| Run date | 2026-07-02 |
| Executor wall-clock | fetch: BTC 1m ~12m17s, ETH 1m ~11m17s (15m fetches sub-minute, prior session); backtests: BTC 51.3s, ETH 63.0s; integrity + diagnostics sub-minute |
| Null test | `--validate 500` → `matched_baseline_test`, **seed=42** (`seed+k` per sim), conservative 1m intrabar execution, default costs |

### Preflight gate (Step 1)
- `git rev-parse HEAD` = `93d686a8…` ✓ (matches the macro-stack commit).
- `uv sync --extra dev --extra fetch` → clean.
- `uv run pytest -q` → **100 passed** (see Anomaly A1 — brief expected 99).
- `uv run ruff check src tests` → clean.
- Verdict: **PASS** (test-count drift documented, not patched).

## 2. Data integrity (Step 4)

Read-only helper `reports/dev/_integrity_check.py` (reuses the tested loader + `resample`). All four burned dev files; **no holdout referenced**.

| Dataset | Rows | Range (UTC) | Dup ts | Non-incr | Expected | Missing | Gap events | OHLC viol | NaN |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT 15m | 122,588 | 2023-01-01 00:00 → 2026-07-01 00:00 | 0 | 0 | 122,593 | 5 | 1 | 0 | 0 |
| BTCUSDT 1m | 1,838,801 | 2023-01-01 00:00 → 2026-07-01 00:00 | 0 | 0 | 1,838,881 | 80 | 1 | 0 | 0 |
| ETHUSDT 15m | 122,588 | 2023-01-01 00:00 → 2026-07-01 00:00 | 0 | 0 | 122,593 | 5 | 1 | 0 | 0 |
| ETHUSDT 1m | 1,838,801 | 2023-01-01 00:00 → 2026-07-01 00:00 | 0 | 0 | 1,838,881 | 80 | 1 | 0 | 0 |

- Missing bars are tiny: 5/122,593 (0.004%) on 15m, 80/1,838,881 (0.004%) on 1m; each concentrated in **1 gap event** per file → consistent with a single Binance exchange outage, not corruption. No duplicates, no non-monotonic steps, no OHLC rule violations, no NaN cells.

**1m → 15m aggregation agreement** (resample 1m→15m, compare OHLC on 122,588 common wall-clock buckets):

| Symbol | open maxreldiff / mism>1e-6 | high | low | close | only_in_15m | only_in_1m_agg |
|---|---|---|---|---|---|---|
| BTCUSDT | 0.0 / 0 | 4.19e-4 / 1 | 2.85e-4 / 1 | 1.02e-3 / 1 | 0 | 0 |
| ETHUSDT | 0.0 / 0 | 1.02e-3 / 1 | 0.0 / 0 | 4.45e-4 / 1 | 0 | 0 |

- Opens reconcile exactly. Every OHLC field agrees to <1e-6 on all buckets **except exactly one** (max ~0.1% relative) — that single bucket coincides with the gap boundary, where the 1m and 15m feeds cover the outage differently. Coverage is otherwise complete (both `only_in_*` = 0). No integrity flag against either run.

## 3. Results (Step 3)

Harness reports: `reports/dev/V3_ITER01_btc.md`, `reports/dev/V3_ITER01_eth.md`. Default costs (spread 1.0 / commission 2.0 / slippage 1.0 bps), conservative 1m-resolved intrabar execution.

| Run | Trades | Total ret | PF | Mean R | Win rate | Max DD | Exposure | Block-boot CI | p(mean R) | p(return) |
|---|---|---|---|---|---|---|---|---|---|---|
| BTC 2023-2026 | **2** | +0.59% | 1.52 | +0.17 | 50.0% | −1.46% | 0.0% | **not emitted (n<5)** | 0.150 | 0.150 |
| ETH 2023-2026 | **1** | −0.19% | 0.00 | −0.18 | 0.0% | −1.31% | 0.0% | **not emitted (n<5)** | 0.234 | 0.234 |

- **Column flag (as the plan instructed):** the block-bootstrap CI column is *structurally absent* from both harness reports. `render_report` gates the "Statistical validity" section on `len(rs) >= 5` trades; with 2 and 1 trades it is skipped. This is not a harness defect — it is a direct consequence of the degenerate trade count (§5, A2). No substitute computed.
- Null diagnostics (matched-template, 500 sims): BTC trades 2 vs 2.0 null mean, exposure 0.02% vs 0.01%, holding 9.5 vs 5.9 bars; ETH trades 1 vs 1.0, exposure 0.00% vs 0.01%, holding 5.0 vs 9.3 bars. With n∈{1,2} these p-values (0.150, 0.234) are uninformative — a 2-trade sample cannot separate skill from luck regardless of value.

## 4. Diagnostics — per-factor + conviction (Step 5)

Read-only `reports/dev/_diagnostics.py`, reconstructing `NarrativeEngine` with the exact `strategy/smc.py` argument mapping from the frozen config (nothing hardcoded). Both dev 15m series, n=122,588 base bars each.

Config echo: `bias_mode=narrative`, `weights=(1,1,1,1,1)`, `min_conviction=0.5`, `ipda_windows=(20,40,60)`.

### BTCUSDT — per-factor sign share (bull>0 / bear<0 / flat=0) and mean
| Factor | bull | bear | flat | mean |
|---|---|---|---|---|
| struct_mtf (4h) | 51.607% | 48.145% | 0.248% | +0.0346 |
| struct_htf (daily) | 60.061% | 36.807% | 3.132% | +0.2325 |
| struct_wk (weekly) | 54.818% | 21.850% | 23.333% | +0.3297 |
| **dol** | **0.235%** | **98.825%** | 0.940% | **−0.7072** |
| ipda | 32.970% | 44.398% | 22.632% | −0.1041 |

score: mean −0.0429, std 0.3548, min −0.9644, max +0.7020; pct 1/5/25/50/75/95/99 = −0.940 / −0.587 / −0.298 / −0.013 / +0.200 / +0.600 / +0.614.
conviction |score|≥0.5: **19.343%**; bias bull 7.988% / bear 11.355% / flat 80.657%.
cross-factor: ≥1 active 99.752%, unanimous-among-active 7.883%, all-5-active 60.535%, all-5-active-AND-agree **2.428%**.

### ETHUSDT — per-factor sign share and mean
| Factor | bull | bear | flat | mean |
|---|---|---|---|---|
| struct_mtf (4h) | 49.881% | 49.897% | 0.222% | −0.0002 |
| struct_htf (daily) | 48.627% | 48.710% | 2.663% | −0.0008 |
| struct_wk (weekly) | 44.951% | 42.132% | 12.917% | +0.0282 |
| **dol** | 15.037% | **82.379%** | 2.584% | **−0.4481** |
| ipda | 29.837% | 38.760% | 31.404% | −0.0616 |

score: mean −0.0965, std 0.3389, min −0.9250, max +0.7091; pct 1/5/25/50/75/95/99 = −0.829 / −0.637 / −0.354 / −0.093 / +0.133 / +0.474 / +0.615.
conviction |score|≥0.5: **17.437%**; bias bull 4.581% / bear 12.856% / flat 82.563%.
cross-factor: ≥1 active 99.778%, unanimous-among-active 7.087%, all-5-active 57.794%, all-5-active-AND-agree **2.062%**.

## 5. Anomalies

- **A1 — pytest count drift 99 → 100 (benign).** Brief/plan expected 99/99; actual is 100 passed, ruff clean. Root cause = the macro-stack commit added a test in `tests/test_narrative.py` (5-factor parametrization). All green; no failure. **Not patched** (per brief: report, don't fix). Preflight still PASS.
- **A2 — degenerate trade count (headline).** The frozen config produces **2 trades on BTC and 1 on ETH across 3.5 years**. This is not a "too-good" result — it is "too-few-to-evaluate": with n∈{1,2} no edge statistic is meaningful, the block-bootstrap CI cannot be emitted, and the null p-values are uninformative. Observationally traceable, not a suspected leak (see below). **Flagged, not tuned.**
- **A3 — `dol` factor near-degenerate / persistently bearish.** On BTC `dol` is bearish on **98.8%** of bars (mean −0.71); on ETH 82.4% bearish (mean −0.45). It is the only factor that is not roughly balanced, and with equal weights (1,1,1,1,1) it single-handedly pulls the mean score negative even when the three structure factors lean bull (BTC struct_htf +0.23, struct_wk +0.33). This biases the narrative bearish and, combined with the many hard gates, contributes to A2. **Observation only.**

### Leakage check (per guardrail "a too-good result is a bug")
No leakage indicator present: returns are ~0 (BTC +0.59%, ETH −0.19%), PF≈1, nulls non-significant, exposure ~0%. The result is *under*-powered, not implausibly good — consistent with V1's finding that these setups are rare/edgeless, not contradicting it. No STOP condition triggered on leakage grounds; the STOP-worthy issue is the opposite (near-zero sample), surfaced here for the architect rather than resolved by tuning.

## 6. Observations vs. Proposals

### Observations (facts)
1. The 5-factor stack itself expresses a tradeable bias on ~17–19% of bars (conviction bite-rate), but the **full strategy** fires only 1–2 times in 3.5 years. The collapse from ~19% biased bars to ~0 trades happens in the *downstream gate stack*, not the narrative vote alone.
2. The gate stack in `v3_origin.toml` is deep and conjunctive: narrative bias-dominance **AND** (`use_htf_bias`) structure-event agreement **AND** `require_htf_discount` **AND** `require_draw` **AND** killzone membership **AND** no news blackout **AND** OTE band **AND** `entry_confirmation` retest-and-close. Each is individually plausible; stacked, they leave almost no eligible bar+event.
3. `dol` is the dominant, near-constant contributor (A3); the other four factors are close to balanced. With equal weights the aggregate is effectively "dol with noise."
4. All-5-factor unanimous agreement occurs on only ~2% of bars — the stack rarely speaks with one voice, so `min_conviction=0.5` is met mostly by 3–4 factors overpowering a near-silent remainder.

### Proposals (for the architect to decide — not executed this iteration)
- **P1 — decide the trade-count floor.** If <5 trades/dev-symbol is disqualifying for the preregistration's null-test power (500 sims, p<0.025 gate), iter 02 likely needs a *deliberate* loosening of exactly one gate, chosen a priori, rather than continued baseline runs. The architect should name which gate (or `min_conviction`) is the single lever.
- **P2 — `dol` warrants scrutiny before any weight change.** Its 82–99% bearish skew suggests either (a) a genuine structural asymmetry in "untaken pools + unfilled FVGs above vs below close," or (b) a normalization/sign artifact. A targeted `dol`-only ablation *would* diagnose this — but that is a separate, architect-approved experiment (explicitly the non-chosen option this round). Flagging, not doing.
- **P3 — the preregistration PASS bar (both holdouts total-return ≥0, mean R>0, ≥1 null p<0.025) is unreachable at this trade frequency.** Whatever iter 02 does, it must raise trade count enough for the null test to have power, without touching holdouts.

## 7. Questions blocking iter 02
1. Is the near-zero trade count itself the stop condition (halt V3 as over-gated), or the motivation to loosen one preregistered lever? If the latter — **which single lever**, and does changing it require a new preregistration amendment before running?
2. Should `dol` be investigated (P2 ablation) before any other change, given it dominates the aggregate score?
3. Does the ≥5-trade requirement for the block-bootstrap CI (and the 500-sim null's power) impose a minimum-trade gate the architect wants me to check *before* running the full null next time?

## 8. Determinism record

- **Commit:** `93d686a8cb2de4a906bd4a3e1d42a4b9f2c5af58`
- **Config:** `configs/v3_origin.toml` (unchanged; `bias_mode=narrative`, `htf_multiplier=16`→4h, `bias_htf2_multiplier=96`→daily, weekly derived 7d, `narrative_weights=[1,1,1,1,1]`, `narrative_min_conviction=0.5`, `ipda_windows=[20,40,60]`, `ipda_hold_days=10`).
- **Exact CLI invocations:**
  ```
  uv run ict-backtest fetch --symbol BTCUSDT --interval 15m --start 2023-01-01 --end 2026-07-01 --out data/btcusdt_15m.parquet
  uv run ict-backtest fetch --symbol BTCUSDT --interval 1m  --start 2023-01-01 --end 2026-07-01 --out data/btcusdt_1m.parquet
  uv run ict-backtest fetch --symbol ETHUSDT --interval 15m --start 2023-01-01 --end 2026-07-01 --out data/ethusdt_15m.parquet
  uv run ict-backtest fetch --symbol ETHUSDT --interval 1m  --start 2023-01-01 --end 2026-07-01 --out data/ethusdt_1m.parquet
  uv run python reports/dev/_integrity_check.py
  uv run python reports/dev/_diagnostics.py
  uv run ict-backtest run --data data/btcusdt_15m.parquet --intrabar-data data/btcusdt_1m.parquet --config configs/v3_origin.toml --validate 500 --report reports/dev/V3_ITER01_btc.md
  uv run ict-backtest run --data data/ethusdt_15m.parquet --intrabar-data data/ethusdt_1m.parquet --config configs/v3_origin.toml --validate 500 --report reports/dev/V3_ITER01_eth.md
  ```
- **Data:** all four files 2023-01-01 00:00 → 2026-07-01 00:00 UTC; 15m = 122,588 rows, 1m = 1,838,801 rows (per symbol).
- **Seeds:** matched-baseline null `seed=42` (per-sim `seed+k`, 500 sims); block-bootstrap `seed=7` (not exercised — n<5 trades). Fetch/backtest are otherwise deterministic (no RNG in the strategy path).
- **Holdouts:** BNBUSDT 2023-2026, ETHUSDT 2019-2022, SOLUSDT 2023-2026, BTCUSDT 2019-2022 — **never fetched, inspected, or referenced.**
