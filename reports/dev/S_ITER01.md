> Provenance note (architect, 2026-07-06): this report was delivered by
> the executor via the architect channel; the executor's environment did
> not push to this branch. Archived verbatim below, unedited, so the
> iteration record lives in-repo like every prior one. Adjudication:
> `reports/dev/S_ITER01_ADJUDICATION.md`.

# Program S — Iteration 01 (Stage-1 descriptive battery on burned ES)

**Iteration:** S-01 — Stage-1 descriptive session-anomaly battery (S1–S5)
on the burned ES 15m development set. No strategy backtests, no
parameter exploration, no holdout contact (NQ not fetched).
**Commit:** `535a8d7e7ed2f68f10df61fefd1efb3f875e281d`
**Date:** 2026-07-06
**Wall-clock:** battery (4 windows) 6.1 s; integrity gates ≈ 8 s; preflight
`pytest` 6.9 s.
**Preflight:** at the iteration commit — `uv run pytest -q` = **138/138
passed**; `uv run ruff check src tests` = **All checks passed**.
Governing docs: `reports/PREREGISTRATION_S.md` (binding),
`docs/EXECUTOR_BRIEF.md` (standing rules), `reports/dev/S_ITER01_TASK.md`
(tasking). Frozen library used verbatim: `analytics/session_study.py`
(`run_session_battery` / `render_session_battery`), `data/loader.py`
(`load_candles`), `detectors/killzones.py` (`et_minutes_days`).

> **Two anomalies found and reported (not patched); see §5–§6 and §9.**
> (a) The tasked FOMC-timestamp snippet (`//10**9`) produces 1970
> day-codes on this pandas build → S3 matched 0 events as tasked;
> corrected in my runner to unit-agnostic epoch-seconds (documented
> deviation, architect confirmation requested). (b) 128 sessions dropped
> as incomplete on the full sample vs the task's "~12" heuristic — all
> 128 are genuine early-close/holiday-shortened sessions, not a
> detection bug.

---

## 1. Data integrity

The burned ES development set was **not re-stitched** this iteration.
Re-invoking `reports/dev/_es_stitch.py` would rebuild `data/es_1m*.parquet`,
which the tasking explicitly forbids ("the 1m file … do not rebuild
it"); the stitch script writes all three parquets and derives the 15m by
resampling the freshly-written adjusted 1m, so the 1m and 15m rebuilds
are coupled in that script. Instead I proved the on-disk artifacts are
the deterministic output of the pinned recipe and ran the read-only
integrity gates (`reports/dev/_es_integrity.py`).

**Determinism chain (recorded stitch-meta sha256 == on-disk sha256):**

| item | value |
|---|---|
| GLBX source | `data/GLBX-20260702-TBF7DT8KTH/glbx-mdp3-20100606-20260701.ohlcv-1m.csv.zst` |
| source sha256 | `e9ebda22332f27ed31a360bc9d8c8f6dba18f6bec916702ed3bab624b8691000` ✓ (matches pin) |
| `data/es_15m.parquet` sha256 | `a3fc183db2a464410d54b9ce6fab442cacbf1ac390a99515a23efc1b38cdd478` (== `_es_stitch_meta.json`) |
| `data/es_1m.parquet` sha256 | `20998ac6b8c10a77c2789bce745cf5a5f4443a86bb360a00756dfcb7d53b7bc7` (== meta) |
| `data/es_1m_raw.parquet` sha256 | `00fc93c2524970747079c50c882024d2fccf2f5bd13965bca2f9ca0781c41753` (== meta) |
| stitch-meta n_15m_rows / n_rolls | 376,768 / 65 |

### 1a. ES contract integrity gates (from `reports/dev/_es_integrity.json`) — matches V3_ITER04 §1a verbatim

| gate | result |
|---|---|
| es_1m adjusted | 5,615,435 rows; 2010-06-06T22:00:00Z → 2026-07-01T23:59:00Z; monotonic; 0 dupes / 0 backsteps; OHLC violations 0/0/0; prices≤0 = 0; min_low 1600.25, max_high 7697.00 |
| es_1m raw | 5,615,435 rows; monotonic; 0 dupes / 0 backsteps; min_low 1002.75, max_high 7636.75 |
| **es_15m adjusted** | **376,768 rows**; first **2010-06-06T22:00:00Z**, last **2026-07-01T23:45:00Z**; monotonic; **0 dupes / 0 backsteps**; **OHLC violations 0**; min_low 1600.25, max_high 7697.00 |
| 15m ↔ 1m reconcile | 376,768 / 376,768 buckets matched; max_abs_diff (o/h/l/c/v) all 0.0; **0 mismatches** |
| roll continuity | **65 / 65** boundaries matched, 0 unmatched; max intraday offset wobble 0.0; worst offset-step residual vs calendar 0.0 |
| gaps (1m) | 33,587 > 1 step = weekend 844 + daily_halt 2,689 + holiday/earlyclose 12 + other 30,042 (structural/expected) |
| bars/year observed | 15m 23,447.4 · 1m 349,464.8 (elapsed 16.069 y) |

All gates pass and are identical to V3_ITER04 §1a. **No gate failure.**

---

## 2. Runs — four batteries, rendered verbatim

`run_session_battery(candles, fomc_ts=fomc_ts)` at library defaults;
`render_session_battery` output pasted verbatim. Per-battery `[meta]`
line (n_sessions, dropped-incomplete) follows each render. FOMC events =
the 133 `event=="FOMC"` rows of the audited calendar, converted to epoch
seconds (see §5/§6 deviation).

### ES full

**ES full** — session battery (4000 complete sessions)

*S1 intraday momentum (signed last-30m; support = CI > 0)*

| predictor | subset | n | mean logret | 95% CI |
|---|---|---|---|---|
| fh | all | 3954 | -0.00001 | [-0.00009, +0.00007] |
| fh | low_vol | 1302 | -0.00002 | [-0.00009, +0.00006] |
| fh | mid_vol | 1310 | -0.00004 | [-0.00013, +0.00005] |
| fh | high_vol | 1323 | +0.00003 | [-0.00015, +0.00023] |
| rod | all | 3968 | +0.00007 | [-0.00001, +0.00015] |
| rod | low_vol | 1306 | +0.00002 | [-0.00005, +0.00008] |
| rod | mid_vol | 1318 | -0.00000 | [-0.00009, +0.00009] |
| rod | high_vol | 1324 | +0.00020 | [+0.00002, +0.00039] |
| both | all | 2943 | +0.00004 | [-0.00005, +0.00014] |
| both | low_vol | 986 | -0.00000 | [-0.00008, +0.00008] |
| both | mid_vol | 985 | -0.00003 | [-0.00013, +0.00007] |
| both | high_vol | 962 | +0.00016 | [-0.00006, +0.00040] |

*S2 opening-range breakout (signed break-to-close; support = CI > 0)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| all | 3065 | +0.00006 | [-0.00014, +0.00027] |
| narrow_range | 1511 | +0.00012 | [-0.00009, +0.00034] |

*S3 pre-FOMC 24h drift into 14:00 ET*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| fomc_days | 129 | +0.00070 | [-0.00063, +0.00198] |
| other_days | 3870 | +0.00037 | [+0.00012, +0.00061] |

*S4 IBS quintiles vs next-session RTH return (support = q1_minus_q5 CI > 0)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| q1 | 800 | +0.00057 | [+0.00005, +0.00111] |
| q2 | 797 | +0.00010 | [-0.00037, +0.00060] |
| q3 | 799 | -0.00004 | [-0.00048, +0.00040] |
| q4 | 803 | +0.00003 | [-0.00039, +0.00043] |
| q5 | 800 | +0.00007 | [-0.00040, +0.00053] |
| q1_minus_q5 | 1600 | +0.00049 | [-0.00020, +0.00121] |

*S5 overnight vs intraday decomposition (descriptive)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| overnight | 3999 | +0.00024 | [+0.00006, +0.00040] |
| intraday | 3999 | +0.00015 | [-0.00003, +0.00031] |

`[meta] candles=376,768 · range 2010-06-06T22:00:00Z → 2026-07-01T23:45:00Z · candidate_rth_days=4128 · n_sessions=4000 · dropped_incomplete=128`

### ES half A (→ 2018-06-30 23:59)

**ES half A** — session battery (2010 complete sessions)

*S1 intraday momentum (signed last-30m; support = CI > 0)*

| predictor | subset | n | mean logret | 95% CI |
|---|---|---|---|---|
| fh | all | 1976 | -0.00000 | [-0.00009, +0.00009] |
| fh | low_vol | 648 | +0.00002 | [-0.00005, +0.00010] |
| fh | mid_vol | 654 | +0.00001 | [-0.00011, +0.00013] |
| fh | high_vol | 655 | -0.00003 | [-0.00022, +0.00018] |
| rod | all | 1985 | +0.00007 | [-0.00002, +0.00015] |
| rod | low_vol | 655 | +0.00003 | [-0.00005, +0.00011] |
| rod | mid_vol | 655 | +0.00001 | [-0.00012, +0.00013] |
| rod | high_vol | 655 | +0.00017 | [-0.00002, +0.00036] |
| both | all | 1496 | +0.00004 | [-0.00006, +0.00015] |
| both | low_vol | 504 | +0.00004 | [-0.00006, +0.00013] |
| both | mid_vol | 490 | +0.00001 | [-0.00014, +0.00017] |
| both | high_vol | 492 | +0.00009 | [-0.00013, +0.00034] |

*S2 opening-range breakout (signed break-to-close; support = CI > 0)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| all | 1541 | -0.00001 | [-0.00021, +0.00019] |
| narrow_range | 750 | +0.00004 | [-0.00018, +0.00025] |

*S3 pre-FOMC 24h drift into 14:00 ET*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| fomc_days | 65 | +0.00051 | [-0.00052, +0.00161] |
| other_days | 1944 | +0.00037 | [+0.00012, +0.00062] |

*S4 IBS quintiles vs next-session RTH return (support = q1_minus_q5 CI > 0)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| q1 | 402 | +0.00029 | [-0.00030, +0.00089] |
| q2 | 402 | -0.00014 | [-0.00058, +0.00028] |
| q3 | 396 | +0.00013 | [-0.00027, +0.00054] |
| q4 | 407 | +0.00040 | [+0.00001, +0.00082] |
| q5 | 402 | +0.00007 | [-0.00040, +0.00050] |
| q1_minus_q5 | 804 | +0.00023 | [-0.00051, +0.00099] |

*S5 overnight vs intraday decomposition (descriptive)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| overnight | 2009 | +0.00022 | [+0.00007, +0.00036] |
| intraday | 2009 | +0.00015 | [-0.00004, +0.00035] |

`[meta] candles=188,574 · range 2010-06-06T22:00:00Z → 2018-06-29T21:00:00Z · candidate_rth_days=2065 · n_sessions=2010 · dropped_incomplete=55`

### ES half B (2018-07-01 00:00 →)

**ES half B** — session battery (1990 complete sessions)

*S1 intraday momentum (signed last-30m; support = CI > 0)*

| predictor | subset | n | mean logret | 95% CI |
|---|---|---|---|---|
| fh | all | 1977 | -0.00002 | [-0.00014, +0.00012] |
| fh | low_vol | 648 | -0.00008 | [-0.00022, +0.00005] |
| fh | mid_vol | 654 | +0.00006 | [-0.00012, +0.00024] |
| fh | high_vol | 655 | -0.00003 | [-0.00033, +0.00029] |
| rod | all | 1983 | +0.00007 | [-0.00005, +0.00021] |
| rod | low_vol | 652 | -0.00003 | [-0.00016, +0.00010] |
| rod | mid_vol | 655 | +0.00005 | [-0.00010, +0.00021] |
| rod | high_vol | 656 | +0.00019 | [-0.00010, +0.00053] |
| both | all | 1447 | +0.00004 | [-0.00011, +0.00020] |
| both | low_vol | 493 | -0.00008 | [-0.00022, +0.00006] |
| both | mid_vol | 457 | +0.00008 | [-0.00012, +0.00028] |
| both | high_vol | 484 | +0.00011 | [-0.00026, +0.00051] |

*S2 opening-range breakout (signed break-to-close; support = CI > 0)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| all | 1524 | +0.00012 | [-0.00023, +0.00050] |
| narrow_range | 750 | +0.00021 | [-0.00015, +0.00059] |

*S3 pre-FOMC 24h drift into 14:00 ET*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| fomc_days | 64 | +0.00090 | [-0.00153, +0.00298] |
| other_days | 1925 | +0.00037 | [-0.00008, +0.00078] |

*S4 IBS quintiles vs next-session RTH return (support = q1_minus_q5 CI > 0)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| q1 | 398 | +0.00076 | [-0.00010, +0.00169] |
| q2 | 398 | +0.00030 | [-0.00055, +0.00121] |
| q3 | 396 | -0.00014 | [-0.00093, +0.00063] |
| q4 | 399 | -0.00032 | [-0.00102, +0.00035] |
| q5 | 398 | +0.00008 | [-0.00077, +0.00086] |
| q1_minus_q5 | 796 | +0.00068 | [-0.00050, +0.00193] |

*S5 overnight vs intraday decomposition (descriptive)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| overnight | 1989 | +0.00025 | [-0.00006, +0.00053] |
| intraday | 1989 | +0.00013 | [-0.00017, +0.00043] |

`[meta] candles=188,194 · range 2018-07-01T22:00:00Z → 2026-07-01T23:45:00Z · candidate_rth_days=2063 · n_sessions=1990 · dropped_incomplete=73`

### ES 2021+ (descriptive) (2021-01-01 00:00 →)

**ES 2021+ (descriptive)** — session battery (1369 complete sessions)

*S1 intraday momentum (signed last-30m; support = CI > 0)*

| predictor | subset | n | mean logret | 95% CI |
|---|---|---|---|---|
| fh | all | 1362 | -0.00004 | [-0.00017, +0.00010] |
| fh | low_vol | 446 | -0.00009 | [-0.00027, +0.00008] |
| fh | mid_vol | 448 | +0.00009 | [-0.00015, +0.00033] |
| fh | high_vol | 449 | -0.00009 | [-0.00036, +0.00017] |
| rod | all | 1365 | -0.00002 | [-0.00013, +0.00010] |
| rod | low_vol | 447 | -0.00008 | [-0.00024, +0.00008] |
| rod | mid_vol | 449 | -0.00001 | [-0.00018, +0.00016] |
| rod | high_vol | 449 | +0.00005 | [-0.00020, +0.00030] |
| both | all | 972 | -0.00004 | [-0.00018, +0.00011] |
| both | low_vol | 328 | -0.00012 | [-0.00030, +0.00005] |
| both | mid_vol | 305 | +0.00006 | [-0.00017, +0.00030] |
| both | high_vol | 322 | -0.00003 | [-0.00034, +0.00028] |

*S2 opening-range breakout (signed break-to-close; support = CI > 0)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| all | 1051 | +0.00029 | [-0.00015, +0.00077] |
| narrow_range | 504 | +0.00052 | [+0.00007, +0.00098] |

*S3 pre-FOMC 24h drift into 14:00 ET*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| fomc_days | 44 | +0.00177 | [-0.00070, +0.00417] |
| other_days | 1324 | +0.00034 | [-0.00014, +0.00079] |

*S4 IBS quintiles vs next-session RTH return (support = q1_minus_q5 CI > 0)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| q1 | 274 | +0.00069 | [-0.00031, +0.00189] |
| q2 | 272 | -0.00038 | [-0.00127, +0.00051] |
| q3 | 275 | +0.00039 | [-0.00052, +0.00126] |
| q4 | 273 | -0.00007 | [-0.00094, +0.00075] |
| q5 | 274 | +0.00043 | [-0.00050, +0.00131] |
| q1_minus_q5 | 548 | +0.00026 | [-0.00106, +0.00174] |

*S5 overnight vs intraday decomposition (descriptive)*

| subset | n | mean logret | 95% CI |
|---|---|---|---|
| overnight | 1368 | +0.00017 | [-0.00014, +0.00044] |
| intraday | 1368 | +0.00022 | [-0.00013, +0.00057] |

`[meta] candles=129,696 · range 2021-01-03T23:00:00Z → 2026-07-01T23:45:00Z · candidate_rth_days=1417 · n_sessions=1369 · dropped_incomplete=48`

---

## 3. Results — preregistered support-rule arithmetic (no adjudication; the ruling is the architect's)

Each line states only the arithmetic: whether the block-bootstrap 95% CI
excludes 0 upward (i.e. `ci_lo > 0`), across the windows named in the
support rule. Seeds: `block_bootstrap_ci` seed=7, IBS-spread seed=7.

- **S1 primary — intraday momentum, predictor `rod`, subset `all`**
  (rule: CI > 0 on full **and** both halves):
  - full `[-0.00001, +0.00015]` — `ci_lo = -0.00001 < 0`, does **not** exclude 0 upward.
  - half A `[-0.00002, +0.00015]` — does **not** exclude 0 upward.
  - half B `[-0.00005, +0.00021]` — does **not** exclude 0 upward.
  → CI excludes 0 upward in **0 of 3** windows.

- **S2 — opening-range breakout, subset `all`** (rule: CI > 0 on full **and** both halves):
  - full `[-0.00014, +0.00027]` — does **not** exclude 0 upward.
  - half A `[-0.00021, +0.00019]` — does **not** exclude 0 upward.
  - half B `[-0.00023, +0.00050]` — does **not** exclude 0 upward.
  → CI excludes 0 upward in **0 of 3** windows.

- **S3 — pre-FOMC 24h drift into 14:00 ET** (rule: CI > 0 upward **and** FOMC mean ≥ 2× other-days mean; halves descriptive):
  - full: FOMC `[-0.00063, +0.00198]` — does **not** exclude 0 upward; FOMC mean `+0.00070` vs 2× other-days `2 × +0.00037 = +0.00074` → `+0.00070 < +0.00074`, ratio ≈ **1.9×** (< 2×).
  - descriptive halves: half A FOMC `+0.00051 [-0.00052, +0.00161]` vs other `+0.00037`; half B FOMC `+0.00090 [-0.00153, +0.00298]` vs other `+0.00037`; 2021+ FOMC `+0.00177 [-0.00070, +0.00417]` vs other `+0.00034`.
  → neither S3 condition met on the full sample.

- **S4 — IBS reversion, subset `q1_minus_q5`** (rule: CI > 0 on full **and** both halves):
  - full `[-0.00020, +0.00121]` — does **not** exclude 0 upward.
  - half A `[-0.00051, +0.00099]` — does **not** exclude 0 upward.
  - half B `[-0.00050, +0.00193]` — does **not** exclude 0 upward.
  → CI excludes 0 upward in **0 of 3** windows.

- **S5 — overnight/intraday** (descriptive, no claim): overnight full `+0.00024 [+0.00006, +0.00040]`; intraday full `+0.00015 [-0.00003, +0.00031]`.

---

## 4. (Exploratory cells — reported, never promoted to support)

Recorded as facts, usable per the preregistration only to *narrow* a
predeclared Stage-2 ablation; no claim is opened here.

- **S1 `rod` high_vol** is the one preregistered-predictor cell whose CI
  excludes 0 upward on the full sample: `+0.00020 [+0.00002, +0.00039]`
  (half A `+0.00017 [-0.00002, +0.00036]`, half B `+0.00019 [-0.00010, +0.00053]`, 2021+ `+0.00005 [-0.00020, +0.00030]`). The volatility conditioning direction matches Gao et al. / Baltussen et al. (effect strongest on high-vol days), but it is exploratory and not the primary rule.
- **S2 narrow_range, 2021+**: `+0.00052 [+0.00007, +0.00098]` (CI excludes 0 up) — the only ORB cell to do so, and only in the descriptive 2021+ cut; full-sample narrow_range `+0.00012 [-0.00009, +0.00034]` does not.
- **S4 q1 (full)**: `+0.00057 [+0.00005, +0.00111]` (CI excludes 0 up); q5 flat `+0.00007`. The q1 tail carries the reversion signal, but the preregistered q1−q5 spread CI includes 0.

---

## 5. Diagnostics

### 5a. Dropped-incomplete sessions — all early closes, not a detection bug

Full sample: 4,128 candidate RTH days (distinct ET days with ≥1 bar in
minute ∈ [570, 960)), 4,000 complete, **128 dropped**. Characterizing
each dropped day by its present anchor minutes
(`reports/dev/_s01_diag.py`):

| bucket | count |
|---|---|
| early-close (09:30 open present, session ends before 13:45 → missing anchors 825/915/930/945) | **128** |
| no 09:30 open | 0 |
| partial-late (has 13:45, missing 15:15–15:45) | 0 |
| mid-session gap | 0 |
| other | 0 |

Every dropped day is a holiday-shortened / early-close session (e.g.
2010-07-05 obs. Independence Day, max RTH bar 11:15; 2010-11-26 day
after Thanksgiving, max RTH bar 13:00). Per-year counts are stable at
**4–10/yr** (2010:4, 2011:7, 2012:8, 2013:3, 2014:7, 2015:8, 2016:7,
2017:8, 2018:9, 2019:9, 2020:10, 2021:7, 2022:8, 2023:9, 2024:10,
2025:10, 2026:4) — the true US equity holiday/early-close cadence seen
through ES Globex (≈8/yr × 16y ≈ 128), with no anomalous single-year
spike. `session_table` is correctly dropping incomplete sessions; the
task's "~12" was a low estimate, not a symptom.

### 5b. S3 FOMC timestamp unit — tasked snippet yields 1970 day-codes

The tasked runner snippet converts FOMC times with
`pd.to_datetime(...).astype("int64") // 10**9`, which assumes nanosecond
datetime resolution. On this environment pandas parses the calendar's
ISO strings to **`datetime64[us, UTC]`** (microsecond), so `astype(int64)`
already yields microseconds and `// 10**9` under-divides by 1,000:
`2010-06-23T18:00Z` → `1277316` s ≈ **1970-01-15**. `et_minutes_days`
then returns `ev_day = 19700115…` for every event, none of which match
any session day → **S3 `fomc_days` n = 0 in all four windows** as
tasked. `analytics.session_study.fomc_rows` is itself correct — the
fault is only in the timestamp-unit conversion of the tasked snippet.
`candles.ts` and `et_minutes_days` both operate in epoch **seconds**, so
seconds is the intended unit. The runner therefore converts
unit-agnostically via `int(Timestamp.timestamp())`, giving
`ev_day = 20100623, 20100810, 20100921, …` (correct) and the S3 tables
in §2/§3. Both the as-tasked and corrected day-codes are recorded in
`reports/dev/_s01_results.json → fomc_ts_deviation`.

---

## 6. Anomalies

1. **Tasked S3 snippet is resolution-fragile (deviation taken).** As
   written (`//10**9`) it produces 1970 FOMC day-codes under pandas
   `datetime64[us]` parsing and matches 0 events. I deviated in my own
   runner (allowed under the write boundary) to the unit-agnostic
   `int(Timestamp.timestamp())` seconds conversion so S3 is evaluable;
   the deviation is documented in code and in the JSON. **This is the
   one deviation from the tasked recipe; see the blocking question in
   §9.** No frozen library code was changed.
2. **128 dropped sessions vs the "~12" heuristic** — investigated per
   the tasking ("a large number … stop and report"); §5a shows all 128
   are legitimate early-close/holiday sessions at the expected ~8/yr
   cadence, not a session-detection fault. Reporting rather than
   silently proceeding, but the battery numbers stand (they are computed
   only on the 4,000 complete sessions).
3. No too-good result. Every preregistered support-rule CI includes 0
   on the full sample (§3); the two CI-excludes-0 cells (S1 rod high_vol,
   S2 narrow_range 2021+) are exploratory and within the noise expected
   across dozens of cells.

---

## 7. Observations (facts) vs Proposals (for the architect)

**Observations**
- Arithmetically, none of S1/S2/S3/S4 meets its preregistered
  CI-excludes-0 condition on the full sample; every primary CI straddles
  0. The signs are mostly the literature-predicted sign but the
  magnitudes are ~0.5–2 bp with CIs an order wider.
- The strongest preregistered-direction signal is the volatility
  conditioning: S1 `rod` high_vol is positive with CI>0 on the full
  sample and positive (CI-straddling) in both halves — consistent with
  Gao et al./Baltussen et al. that intraday momentum concentrates on
  high-vol days. `rod` all-days is a stable `+0.00007` across full/half
  A/half B but never separates from 0.
- Overnight return (S5) is significantly positive on the full sample
  (`+0.00024 [+0.00006, +0.00040]`) and exceeds RTH-intraday — the
  classic overnight-drift decomposition, descriptive only.
- S3 pre-FOMC drift is positive and monotonically larger in more recent
  cuts (full FOMC +0.00070 → 2021+ +0.00177) but with n=44–129 the CIs
  are far too wide to separate from 0 or from the ≈+0.00037 other-days
  baseline; the ~1.9× ratio on the full sample sits just under the 2×
  bar. This matches the literature's "positive but weakened/mixed
  post-publication" reading.

**Proposals** (architect decides; no action taken)
- Confirm or reject the §5b/§9 FOMC-timestamp deviation. If the intended
  behavior is strictly "run the snippet verbatim," S3 is unevaluable
  as-tasked (n=0) and should be recorded as such; the corrected S3 in
  §2/§3 would then be an out-of-band supplement.
- Consider stating the expected dropped-session count as ≈8/yr (~128
  over the 16y sample) in the tasking/preregistration so the "large
  number → stop" tripwire is calibrated to the real early-close cadence.

---

## 8. Determinism anchors

| item | value |
|---|---|
| commit | `535a8d7e7ed2f68f10df61fefd1efb3f875e281d` |
| runner | `reports/dev/_s01_runner.py` → `reports/dev/_s01_results.json` (+ verbatim stdout `reports/dev/_s01_stdout.txt`) |
| integrity | `reports/dev/_es_integrity.py` → `reports/dev/_es_integrity.json` (read-only; no re-stitch) |
| drop diagnostic | `reports/dev/_s01_diag.py` |
| invocations | `uv run python reports/dev/_es_integrity.py` · `uv run python reports/dev/_s01_runner.py` |
| dev data (15m) | `data/es_15m.parquet` — 376,768 rows, 2010-06-06T22:00:00Z → 2026-07-01T23:45:00Z, sha256 `a3fc183db2a464410d54b9ce6fab442cacbf1ac390a99515a23efc1b38cdd478` |
| source GLBX sha256 | `e9ebda22332f27ed31a360bc9d8c8f6dba18f6bec916702ed3bab624b8691000` |
| calendar | `data/calendars/high_impact_2010_2026.csv` — 506 rows, sha256 `98127c1242b67f8fd2cafd16712eec4676fe3c2d6719681d86e351e934f2476e`; FOMC rows = 133 |
| FOMC unit | epoch seconds via `int(Timestamp.timestamp())` (deviation from tasked `//10**9`; see §5b/§6/§9) |
| seeds | `block_bootstrap_ci` seed=7 (library default); IBS-spread seed=7 (library) |
| windows | full (all); half A (end `2018-06-30 23:59`); half B (start `2018-07-01 00:00`); 2021+ (start `2021-01-01 00:00`); `load_candles` slice is end-exclusive |
| n_sessions / dropped | full 4000/128 · half A 2010/55 · half B 1990/73 · 2021+ 1369/48 |
| wall-clock | battery 6.1 s; integrity ≈ 8 s; pytest 6.9 s |

---

## 9. Questions blocking the next iteration

1. **FOMC timestamp deviation — confirm the fix or rule S3 unevaluable
   as-tasked.** The tasked snippet's `//10**9` produces 1970 day-codes
   under this environment's `datetime64[us]` calendar parsing → S3 n=0.
   I corrected my runner to unit-agnostic epoch-seconds
   (`int(Timestamp.timestamp())`), giving the S3 tables in §2/§3 (full
   FOMC n=129). Please confirm this is the intended S3 result, or direct
   that S3 be recorded as unevaluable-as-tasked. No frozen code was
   touched; only the runner's FOMC-time conversion. This is the sole
   deviation and does not affect S1/S2/S4/S5.
