# V3 "Origin" — Development Iteration 04 (ES venue-specificity go/no-go)

**Iteration:** 04 — ES futures forward-return separation test (the go/no-go that decides whether ES development continues)
**Commit:** `396c9a1b286d7e6276b71d5ff90c734ebcdc4495`
**Date:** 2026-07-02
**Wall-clock:** ES forward-return battery ≈ 41 s; single ES funnel/backtest ≈ 88 s.
**Preflight:** verified at iteration commit — `uv run pytest -q` = 106/106, `uv run ruff check src tests` clean; frozen `configs/v3_origin.toml` unchanged on disk (news_csv override applied at runtime only).

Scope this iteration (architect tasking): give ES the **same** forward-return separation test that closed crypto development — narrative bias / structure bias / each factor sign / score quintile forward-return tables at horizons **96 & 384**, plus **one** frozen-config funnel/backtest run on the corrected 16-year ES contract with the extended 2010→2026 high-impact calendar. **No tuning, no levers, no NQ, no holdouts.** If separation is consistent and directional, venue-specificity is alive and ES development proceeds on ~16y in-sample ES; if not, the program concludes with an auditable three-study answer and holdouts stay sealed.

---

## 1. Determinism anchors

| item | value |
|---|---|
| commit | `396c9a1b286d7e6276b71d5ff90c734ebcdc4495` |
| frozen config | `configs/v3_origin.toml` (news_csv="" on disk; extended calendar injected at RUNTIME via `dataclasses.replace(cfg, news_csv=…)` — the file is NEVER edited) |
| forward-return runner | `reports/dev/_forward_returns_es.py` → `reports/dev/_forward_returns_es.json` |
| funnel/backtest runner | `reports/dev/_entrypath_runner_es.py` → `reports/dev/_entrypath_es_results.json` (+ `_entrypath_es.md`) |
| invocations | `uv run python reports/dev/_forward_returns_es.py` · `uv run python reports/dev/_entrypath_runner_es.py` |
| dev data (15m) | `data/es_15m.parquet` — **376,768 rows** |
| dev data (1m intrabar) | `data/es_1m.parquet` — **5,615,435 rows** (adjusted); `data/es_1m_raw.parquet` — 5,615,435 rows (un-adjusted) |
| window | 2010-06-06T22:00:00Z → 2026-07-01T23:59:00Z (1m) / →23:45:00Z (15m); elapsed 16.069 y |
| ES source | GLBX MDP-3 full-product `glbx-mdp3-20100606-20260701.ohlcv-1m.csv.zst`, sha256 `e9ebda22332f27ed31a360bc9d8c8f6dba18f6bec916702ed3bab624b8691000` |
| calendar | `data/calendars/high_impact_2010_2026.csv` — 506 rows, sha256 `98127c1242b67f8fd2cafd16712eec4676fe3c2d6719681d86e351e934f2476e` |
| costs (backtest) | spread 0.4 / commission 0.1 / slippage 0.4 bps; conservative 1m intrabar |
| bars/year | 23,447.4 (session-correct 15m, from integrity audit) |
| null test | `matched_baseline_test`, seed=42, n_sims=500, `eligible_mask=strategy.kz_mask` (runs only if trades ≥ 5) |
| forward-return sampling | non-overlapping windows (`step = horizon_bars`); horizons 96 and 384 bars |

### 1a. ES contract integrity (from `reports/dev/_es_integrity.json`)

| gate | result |
|---|---|
| es_1m adjusted | 5,615,435 rows; monotonic; 0 dupes / 0 backsteps; OHLC violations 0/0/0/0; prices≤0 = 0; min_low 1600.25, max_high 7697.00 |
| es_1m raw | 5,615,435 rows; monotonic; 0 dupes / 0 backsteps; min_low 1002.75, max_high 7636.75 |
| es_15m adjusted | 376,768 rows; first 2010-06-06T22:00:00Z, last 2026-07-01T23:45:00Z; monotonic; 0 dupes/backsteps; OHLC violations 0; min_low 1600.25, max_high 7697.00 |
| 15m ↔ 1m reconcile | 376,768 / 376,768 buckets matched; max_abs_diff (o/h/l/c/v) all 0.0; 0 mismatches |
| roll continuity | 65 / 65 boundaries matched, 0 unmatched; worst offset-step residual vs calendar gap 0.0; max intraday wobble 0.0 |
| gaps (1m) | 33,587 > 1 step = weekend 844 + daily_halt 2,689 + holiday/earlyclose 12 + other 30,042 (low-liquidity missing minutes) — all structural/expected |
| gaps (15m) | 6,595 > 1 step = weekend 844 + daily_halt 3,170 + holiday/earlyclose 12 + other 2,569 |
| bars/year observed | 15m 23,447.4 · 1m 349,464.8 (elapsed 16.069 y) |

### 1b. Roll log (from `reports/dev/_es_roll_calendar.json`)

- **65 rolls**, daily-volume roll on instrument_id membership, quarterly H/M/U/Z. Seed active ESM0 (2010-06-06) → final active ESU6.
- First roll: ESM0 → ESU0, crossover 2010-06-11, effective **2010-06-13** (next trading day), from_vol 716,356 < to_vol 1,779,845, raw_gap −4.5.
- Last roll: ESM6 → ESU6, crossover 2026-06-15, effective 2026-06-16, from_vol 561,673 < to_vol 916,862, raw_gap +64.75.
- Back-adjust: difference/additive (Panama); newest segment offset = 0. Look-ahead-free: crossover on day d → membership moves to the NEXT trading day `days[i+1]`.

**Resolved cosmetic note (65 vs 66):** a distinct-offset-levels heuristic showed 65 distinct offsets across 66 segments. Root cause is benign — **segments 26 and 33 coincidentally share cumulative additive offset 765.5** (signed roll gaps cumulate and the running total revisits a value; no roll has |raw_gap| < 0.2). The decisive per-boundary residual audit is exact and passed 65/65 at residual 0.0, so the back-adjustment is correct.

**Additive-adjustment caveat (reported, not patched):** additive/Panama back-adjustment distorts returns near old rolls and could in principle drive very old adjusted prices ≤ 0. Empirically benign here: adjusted min_low 1600.25 (> 0), raw min_low 1002.75.

### 1c. Scaffolding bugs found & fixed earlier (in MY `reports/dev/` tooling — corrected before this run)

1. Stitch `effective_day` was `crossover_day + 1 calendar day`, landing on non-trading Saturdays for Friday crossovers, so 23 of 66 offset levels never materialized → fixed to `days[i+1]` (next trading day).
2. Integrity `roll_continuity` matched 0/65 because `off_by_day.index` was tz-aware while the compared timestamp was naive → fixed with a `_daykey()` `%Y-%m-%d` normalizer.
3. (Prior) 1-row `es_15m.parquet` from `// 10**9` → fixed to `// 1000` for datetime64[ms].

Cosmetic caveat left in place: `gap_attribution` uses `prev_et = et.to_numpy()` which strips tz; affects only example gap labels, not gap COUNTS.

---

## 2. Calendar provenance (task #15)

Built by `reports/dev/_build_calendar_2010.py` → `data/calendars/high_impact_2010_2026.csv` (+ `reports/dev/_calendar_2010_provenance.json`). Window 2010-06-06 → 2023-01-01 (exclusive); 2023-2026 rows appended VERBATIM.

| item | value |
|---|---|
| total rows | 506 = **402 new (2010-2022)** + **104 existing (2023-2026, byte-identical tail)** |
| event counts (whole file) | CPI 187 · FOMC 133 · NFP 186 |
| FOMC in-window 2010-2022 | 101 (8/yr scheduled statement days; 2020 emergency actions 03-03 / 03-15 excluded) |
| gap anomalies | **0** (monthly NFP & CPI gap-check 20–45 d; FOMC 8/yr) |
| tail byte-identical | True (asserted equal to `high_impact_2023_2026.csv` data rows) |
| output sha256 | `98127c1242b67f8fd2cafd16712eec4676fe3c2d6719681d86e351e934f2476e` |
| existing sha256 | `0bafc9ddb77416b73cbc403e09ce46ab42c62bbac25f3b3cf9dada54ff50f912` |

Sourcing per `docs/CALENDAR_SOURCES.md` (unedited): BLS Employment Situation (NFP) and CPI actual release dates via Internet Archive Wayback (bls.gov/FRED return 403) — 2010-2016 from yearly `{year}_sched.htm` (monthly Employment Situation matched by title, excluding the annual veterans release; monthly CPI by title), 2017-2022 from rolling `empsit.htm`/`cpi.htm` snapshots unioned & deduped; times 08:30 ET as listed. FOMC = 8 scheduled statement days/yr at 14:00 ET, cross-checked against federalreserve.gov. DST-correct ET→UTC via zoneinfo. Wayback snapshot IDs pinned in the provenance sidecar for determinism.

---

## 3. Forward-return separation (THE go/no-go deliverable)

All tables are `analytics.forward_return_table` verbatim — non-overlapping windows, honest t-stats. `mean fwd logret` = mean of `log(close[i+h]/close[i])` over the state's bars; `t` = mean / (sd/√n), 0 if n≤1 or sd==0. `n_bars` = 376,768. Coverage % = fraction of bars in a non-zero / labeled state.

### 3a. Narrative bias (the frozen decision variable) — coverage 86,948 / 23.077%

**ES — narrative_bias — h=96**
| state | n | mean fwd logret | t |
|---|---|---|---|
| -1 | 206 | +0.0004343 | +0.44 |
| +0 | 3022 | +0.0004427 | +2.94 |
| +1 | 696 | +0.0001229 | +0.62 |

**ES — narrative_bias — h=384**
| state | n | mean fwd logret | t |
|---|---|---|---|
| -1 | 49 | +0.0072736 | +3.20 |
| +0 | 757 | +0.0013057 | +2.22 |
| +1 | 175 | +0.0009595 | +1.40 |

Reading — narrative bull(+1) vs bear(−1) vs neutral(0) forward mean:

| horizon | bull mean | bear mean | neutral mean | bull > bear? | direction |
|---|---|---|---|---|---|
| 96 | +0.0001229 (t=+0.62) | +0.0004343 (t=+0.44) | +0.0004427 (t=+2.94) | **no** | **inverted** — bull is the LOWEST of the three |
| 384 | +0.0009595 (t=+1.40) | +0.0072736 (t=+3.20) | +0.0013057 (t=+2.22) | **no** | **inverted** — bull is the LOWEST; bear the highest and most significant |

At **both** horizons the narrative BULL state under-returns BOTH the BEAR and the neutral state. The only significant separation runs the WRONG way (bear h=384 t=+3.20 ≫ bull t=+1.40). This mirrors the crypto ETH anti-predictive finding.

### 3b. Structure bias vs the 4h MTF factor — the same identity as crypto — coverage 376,510 / 99.932%

**ES — structure_bias — h=96** and **ES — factor_sign::struct_mtf — h=96** are byte-identical:
| state | n | mean fwd logret | t |
|---|---|---|---|
| -1 | 1636 | +0.0004484 | +1.85 |
| +0 | 3 | −0.0020193 | −0.47 |
| +1 | 2285 | +0.0003436 | +2.37 |

**ES — structure_bias / factor_sign::struct_mtf — h=384** (also byte-identical):
| state | n | mean fwd logret | t |
|---|---|---|---|
| -1 | 406 | +0.0020643 | +2.35 |
| +0 | 1 | +0.0120067 | 0.00 |
| +1 | 574 | +0.0011543 | +2.10 |

The `structure_bias ≡ factor_sign::struct_mtf` identity holds on ES exactly as it did on crypto in Iter-03 (structure mode carries exactly the information of the single 4h MTF factor). Direction: bull +0.0003436 < bear +0.0004484 (h=96) and bull +0.0011543 < bear +0.0020643 (h=384) — **bear ≥ bull at both horizons** (inverted).

### 3c. Per-factor sign (bull +1 vs bear −1 forward mean)

| factor | coverage % | h=96 (bull / bear) | h=384 (bull / bear) |
|---|---|---|---|
| struct_mtf | 99.932 | +0.0003436 / +0.0004484 ✗ | +0.0011543 / +0.0020643 ✗ |
| struct_htf | 99.149 | +0.0002562 / +0.0005954 ✗ | +0.0010032 / +0.0024218 ✗ |
| struct_wk | 98.098 | +0.0002713 / +0.0006628 ✗ | +0.0011788 / +0.0024248 ✗ |
| dol | 94.915 | +0.0004461 / +0.0003494 ✓ | +0.0015656 / +0.0014240 ✓ |
| ipda | 86.397 | +0.0002632 / +0.0004736 ✗ | +0.0009002 / +0.0025721 ✗ |

(✓ = bull > bear; ✗ = inverted, bear ≥ bull.) **9 of 10** factor/horizon cells are inverted. The sole exception is `dol` (bull nudges above bear at both horizons) — but bull t is not significant (h=96 t=+1.20, h=384 t=+1.15), while several inverted bear cells ARE significant (e.g. struct_htf h=384 bear t=+2.42; ipda h=384 bear t=+3.63; struct_wk h=384 bear t=+2.06). No |t| in any bull cell reaches 2.

### 3d. Score quintile (does higher conviction → higher forward return?) — coverage 315,300 / 83.685%

**ES — score_quintile — h=96**: q0 +0.0010749 (t=+2.34) · q1 +0.0001596 · q2 +0.0005421 · q3 +0.0003393 · q4 +0.0000577 (t=+0.30) — **top quintile is the lowest**; broadly decreasing in score.
**ES — score_quintile — h=384**: q0 +0.0049812 (t=+3.38) · q1 +0.0011623 · q2 +0.0012185 · q3 +0.0005592 · q4 +0.0006109 — **monotonically decreasing**, q0 ≫ q4.

Higher narrative score predicts LOWER forward return at both horizons — the opposite of the design intent, and the same anti-predictive shape seen on crypto ETH.

All means are positive (ES has a secular long drift over 16 y); the point is not the sign of the level but that the frozen bull/high-conviction states sit BELOW the bear/low-conviction states at both horizons.

---

## 4. Single frozen-config funnel / backtest (task #16)

One run on `data/es_15m.parquet` (+ `data/es_1m.parquet` intrabar), frozen `configs/v3_origin.toml`, ES costs 0.4/0.1/0.4 bps, bars/year 23,447.4, extended calendar injected at runtime. Null test + block-bootstrap CI ran (trades ≥ 5).

| symbol | trades | total ret % | PF | mean R | block-boot CI(R) | p(ret) | p(meanR) | max DD % | exposure % | Sharpe | null |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ES | **7** | +2.099 | 1.961 | **−0.084** | [−1.039, +0.824] (bl=2) | 0.226 | 0.363 | −2.602 | 0.0109 | 0.222 | ran (500 sims) |

Over 16 years the frozen strategy fires **7 trades** (exposure 0.011%). Mean R is **negative** (−0.084); the small positive total return is carried by profit factor on a handful of trades, not by a positive expectancy. Neither null p-value approaches significance (p(mean R)=0.363, p(return)=0.226); the block-bootstrap R CI straddles zero. **Not powered, not significant, mean-R negative.**

### 4a. Funnel (authoritative 17-key set; `_subreasons_sum_ok` = True)

| key | value |
|---|---|
| signals | 16,030 |
| rejected_bias | **14,280** |
| rejected_bias2 | 0 |
| rejected_discount | 1,566 |
| rejected_draw | 2 |
| rejected_time | 124 |
| staged_attempts | 58 |
| rejected_no_poi | 0 |
| rejected_ote | 26 |
| rejected_geometry | 5 |
| placed_limit | 0 |
| placed_await | 27 |
| await_triggered | 7 |
| await_abandoned | 20 |
| — await_expired | 20 |
| — await_violated | 0 |
| — await_displaced | 0 |
| **fills (trades)** | **7** |

The dominant bottleneck is again the narrative bias gate: `rejected_bias` = 14,280 / 16,030 ≈ **89%** of signals, starving the funnel before POI/OTE/entry logic. Of 27 stagings routed to the await path, 20 expire (100% of abandonment is `await_expired`) and only 7 fill. The entry-path machinery behaves consistently (`await_abandoned == expired + violated + displaced`).

---

## 5. Anomalies

1. **structure_bias ≡ factor_sign::struct_mtf** on ES (byte-identical forward tables at both horizons) — the same identity observed on crypto in Iter-03. Expected given structure mode = single 4h swing structure; recorded, not patched.
2. **ES narrative composite is anti-predictive** — the bull state under-returns both bear and neutral at both horizons; 9/10 per-factor cells are inverted; score quintiles decrease in conviction. Reported per "a too-wrong result is a bug until the architect rules"; **not patched, no weights/levers touched.**
3. **Trade-starvation** — 7 trades over 16 y; ~89% of signals rejected at the bias gate. Consistent with the crypto funnels and V1; a genuine (negative) observation, not implausibly good.
4. No DATA integrity anomalies: all §6 gates pass (OHLC 0 violations, 65/65 roll continuity at residual 0.0, 15m↔1m reconcile exact). The 65-vs-66 offset heuristic and the additive-adjustment caveat are resolved/benign (§1b) and the three scaffolding bugs were mine and are fixed (§1c).

---

## 6. Observations (facts) — including the go/no-go reading

**Go/no-go criterion** (architect's definition): venue-specificity is alive iff the narrative-bias / structure / factor-sign / quintile forward-return tables separate **consistently and directionally** across horizons 96 & 384. I report the facts; the ruling is the architect's.

- **Narrative bias:** inverted at both horizons — bull is the lowest of {bull, bear, neutral} at both h=96 and h=384; the only significant cell (bear h=384, t=+3.20) runs the wrong way.
- **Structure bias (≡ struct_mtf):** bear ≥ bull at both horizons.
- **Per-factor sign:** 9 of 10 cells inverted; the one non-inverted factor (dol) has no significant bull cell.
- **Score quintile:** monotonically decreasing in conviction at h=384 and top-quintile-lowest at h=96 — higher score → lower forward return.
- **Every state family points the same way on ES:** bear/low-conviction ≥ bull/high-conviction. There is no state, at either horizon, on which the frozen decision variable separates forward returns in the intended direction. This is not a mixed/one-symbol split (as crypto Iter-03 was on BTC h=96); on ES the separation is uniformly absent/inverted.
- **The single backtest confirms the read downstream:** 7 trades / 16 y, mean R −0.084, both null p-values non-significant, R CI straddling zero — no evidence of edge; the bias gate rejects ~89% of signals, so the funnel is bias-gate-limited exactly as on crypto.
- **This completes the auditable three-study answer.** Study 1 (V1 canonical ICT) failed confirmatory. Study 2 (V3 crypto forward-return separation) closed with no consistent separation and ETH anti-predictive. Study 3 (this iteration, ES futures — ICT's home session-based venue) shows the SAME anti-predictive pattern on 16 years of the market the venue-specificity hypothesis most favored. Venue-specificity does not rescue the edge.

## 7. Proposals (for the architect — the decision is the architect's)

- The go/no-go precondition for continuing ES development ("consistent, directional forward-return separation") is **not met**: separation is uniformly inverted/absent across all four state families and both horizons, and the single funnel run is unpowered with negative mean R. On the read given to the prior crypto iteration ("no separation → development halts"), the corresponding branch here is **conclude V3 / conclude the program**: ES development does not open, and all reserved holdouts (BNBUSDT, ETHUSDT 2019-2022, SOLUSDT, BTCUSDT 2019-2022, **NQ**) stay sealed.
- If the architect nonetheless wishes to record a residual: the only non-inverted factor is `dol`, and it is not significant — it does not motivate a weight lever, and no lever is in scope this iteration regardless.
- Per protocol this is one iteration = one report; no tuning, no follow-on experiments were run. The three studies now stand as an auditable "no."

## 8. Questions blocking any Iteration 05

1. **Go/no-go ruling:** given uniform inversion across narrative bias, structure, all five factor signs (dol excepted but non-significant), and score quintile at BOTH horizons — plus an unpowered, negative-mean-R single backtest — does the architect rule venue-specificity **dead** (conclude the program, holdouts stay sealed), or is there a further pre-specified branch? No lever is moved and no data is touched without an explicit ruling.
2. If the program is concluded: confirm the holdouts (incl. NQ) remain permanently sealed and no further price contact is authorized.

---

*Artifacts (all under `reports/dev/`, gitignored helpers prefixed `_`): `_forward_returns_es.py`, `_forward_returns_es.json`, `_entrypath_runner_es.py`, `_entrypath_es_results.json`, `_entrypath_es.md`, `_build_calendar_2010.py`, `_calendar_2010_provenance.json`, `_es_stitch.py`, `_es_stitch_meta.json`, `_es_roll_calendar.json`, `_es_integrity.py`, `_es_integrity.json`. Committed data path: `data/calendars/high_impact_2010_2026.csv`.*
