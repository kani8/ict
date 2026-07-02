# V3 "Origin" — Iteration 02 (executor report)

## 1. Header

| Field | Value |
|---|---|
| Iteration | 02 |
| Study | V3 "Origin" — 5-factor narrative macro stack (development phase) |
| Commit (HEAD at run) | `4835ae4` (calendar CSV; sits atop the adjudication commit `396cc1f` which carried the dol-staleness fix) |
| Date | 2026-07-02 |
| Dev sets | BTCUSDT, ETHUSDT — 15m base + 1m intrabar, 2023-01-01 → 2026-07-01 |
| Holdouts | BNBUSDT 2023-2026, ETHUSDT 2019-2022, SOLUSDT 2023-2026, BTCUSDT 2019-2022, NQ 2023-2026 — **never fetched, inspected, or referenced.** No index data fetched this iteration. |
| Preflight gate | `uv run pytest -q` = **104 passed**; `uv run ruff check src tests` = **All checks passed** (at HEAD `4835ae4`). |
| Costs | default spread 1.0 / commission 2.0 / slippage 1.0 bps; conservative 1m intrabar execution |
| Null test | `matched_baseline_test`, seed 42, n_sims 500, `eligible_mask = strategy.kz_mask`; block-bootstrap CI on trade R only when ≥5 trades |
| Executor wall-clock | matrix (8 runs) + news ablation (2 runs) reuse of the Iter-01 dev parquets (no re-fetch); diagnostics + pytest + ruff sub-minute each |

**What changed since Iter-01.** The only source change between Iter-01 and this
run is the dol-staleness fix carried in `396cc1f` (`dol_lookback_days = 60`,
threaded through `strategy/smc.py` → `NarrativeEngine`). The additional commit
`4835ae4` is **data only** — the committed high-impact calendar CSV
(gitignore-exempt) — and cannot affect the test suite or strategy code.
Strategy weights remain frozen at `(1,1,1,1,1)` and `min_conviction = 0.5`
in the anchor config, unchanged this iteration.

## 2. Data integrity

Reusing the Iter-01 dev parquets (no re-fetch). Row counts and ranges re-verified
against Iter-01 — **byte-identical**:

| Dataset | Rows | Range |
|---|---|---|
| BTCUSDT 15m | 122,588 | 2023-01-01 00:00 → 2026-07-01 00:00 UTC |
| BTCUSDT 1m | 1,838,801 | 2023-01-01 00:00 → 2026-07-01 00:00 UTC |
| ETHUSDT 15m | 122,588 | 2023-01-01 00:00 → 2026-07-01 00:00 UTC |
| ETHUSDT 1m | 1,838,801 | 2023-01-01 00:00 → 2026-07-01 00:00 UTC |

Full integrity (dupes / OHLC violations / grid gaps / 15m↔1m aggregation) was
established in Iter-01 §2 and is not re-litigated here (same files, same bytes).
Iter-01 recorded 0 duplicate timestamps, 0 OHLC violations, and the small
expected 15m/1m grid-count deltas (5 and 80 "missing" bars respectively — the
Binance listing edge, documented previously).

## 3. Results — Iteration-01 matrix re-run at fixed-dol commit (Step 2)

V3 config; conviction ∈ {0.25, 0.50 (frozen), 0.75}; structure-bias variant;
per symbol; 1m intrabar; `--validate 500`. Conviction/structure variants are
driven by **derived temp configs under `reports/dev/`** (CLI has no strategy
override flags); `configs/` untouched. `narrative_weights` stay `(1,1,1,1,1)`
in every row; only `narrative_min_conviction` (conv rows) or `bias_mode`
(structure row) differs from frozen.

### 3.1 Results table

| Symbol | Variant | Trades | Total ret | PF | Mean R | Win% | Max DD | Exposure | Block-boot CI (R) | p(mean R) | p(return) | Null |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| BTC | conv 0.25 | 4 | −0.947% | 0.647 | −0.288 | 25.0% | −2.92% | 0.021% | n<5 (4) — not emitted | NaN | 1.000 | skipped (n<5) |
| BTC | **conv 0.50 (frozen)** | **0** | 0.00% | — | — | — | 0.00% | 0.00% | no trades | NaN | 1.000 | skipped (0) |
| BTC | conv 0.75 | 0 | 0.00% | — | — | — | 0.00% | 0.00% | no trades | NaN | 1.000 | skipped (0) |
| BTC | structure-bias | 4 | −0.943% | 0.649 | −0.274 | 25.0% | −2.70% | 0.029% | n<5 (4) — not emitted | NaN | 1.000 | skipped (n<5) |
| ETH | conv 0.25 | 2 | −1.353% | 0.000 | −0.653 | 0.0% | −2.46% | 0.033% | n<5 (2) — not emitted | NaN | 1.000 | skipped (n<5) |
| ETH | **conv 0.50 (frozen)** | **1** | −1.166% | 0.000 | −1.125 | 0.0% | −2.06% | 0.029% | n<5 (1) — not emitted | NaN | 1.000 | skipped (n<5) |
| ETH | conv 0.75 | 0 | 0.00% | — | — | — | 0.00% | 0.00% | no trades | NaN | 1.000 | skipped (0) |
| ETH | structure-bias | 3 | −1.463% | 0.000 | −0.471 | 0.0% | −3.19% | 0.110% | n<5 (3) — not emitted | NaN | 1.000 | skipped (n<5) |

Every row is **underpowered** (n ≤ 4). The null test is *skipped* whenever n<5
(`n_sims=0`), so `p(return)=1.000` and `p(mean R)=NaN` are placeholders, **not
evidence** — they carry no information about edge. No block-bootstrap CI is
emitted anywhere (all n<5). No row is profitable; every trade that occurs is a
loss or a coin-flip on a 1–4 sample.

**Cross-iteration note (frozen anchor).** At Iter-01 (stale dol) the frozen
conv=0.50 run produced **BTC 2 trades (+0.59%)** and **ETH 1 trade (−0.19%)**.
At the fixed-dol commit the same frozen config produces **BTC 0 trades** and
**ETH 1 trade (−1.166%, a *different* trade)**. The defect fix did **not**
increase trade count — on BTC it fell 2→0; on ETH the single surviving trade
changed identity and worsened. See Anomaly A1.

### 3.2 Funnel per run (`strategy.funnel`)

Funnel key order per `smc.py`. Blank = 0. `signals` is the count entering the
bias gate; each `rejected_*` is drop at that gate; `staged_attempts` = setups
passing bias+discount+draw+time; the placement/await columns are terminal.

**BTCUSDT**

| Funnel key | conv 0.25 | conv 0.50 (frozen) | conv 0.75 | structure |
|---|---:|---:|---:|---:|
| signals | 5397 | 5416 | 5423 | 5390 |
| rejected_bias | 4210 | 4980 | 5413 | 2785 |
| rejected_bias2 | 0 | 0 | 0 | 1160 |
| rejected_discount | 923 | 364 | 10 | 1134 |
| rejected_draw | 0 | 0 | 0 | 0 |
| rejected_time | 196 | 53 | 0 | 224 |
| staged_attempts | 68 | 19 | 0 | 87 |
| rejected_no_poi | 0 | 0 | 0 | 0 |
| rejected_ote | 45 | 14 | 0 | 55 |
| rejected_geometry | 3 | 1 | 0 | 4 |
| placed_limit | 0 | 0 | 0 | 0 |
| placed_await | 20 | 4 | 0 | 28 |
| await_triggered | 4 | 0 | 0 | 4 |
| await_abandoned | 16 | 4 | 0 | 24 |

**ETHUSDT**

| Funnel key | conv 0.25 | conv 0.50 (frozen) | conv 0.75 | structure |
|---|---:|---:|---:|---:|
| signals | 5472 | 5484 | 5497 | 5447 |
| rejected_bias | 4345 | 5020 | 5482 | 2851 |
| rejected_bias2 | 0 | 0 | 0 | 1108 |
| rejected_discount | 810 | 361 | 8 | 1084 |
| rejected_draw | 0 | 0 | 0 | 2 |
| rejected_time | 246 | 81 | 7 | 296 |
| staged_attempts | 71 | 22 | 0 | 106 |
| rejected_no_poi | 0 | 0 | 0 | 0 |
| rejected_ote | 48 | 12 | 0 | 67 |
| rejected_geometry | 7 | 2 | 0 | 8 |
| placed_limit | 0 | 0 | 0 | 0 |
| placed_await | 16 | 8 | 0 | 31 |
| await_triggered | 2 | 1 | 0 | 3 |
| await_abandoned | 14 | 7 | 0 | 28 |

Funnel reading: **`rejected_bias` is the dominant sink at every setting.** At
conv=0.75 it consumes essentially all signals (BTC 5413/5423, ETH 5482/5497 →
0 staged). Lowering conviction to 0.25 relaxes the bias gate (BTC rej_bias
4980→4210, ETH 5020→4345) but the freed setups then pile into
`rejected_discount` and `rejected_time`, and the survivors still only convert
to a handful of aborted await-limit placements (BTC await_abandoned 16 of 20).
The structure variant substitutes a two-stage structural bias (a second
`rejected_bias2` gate appears, BTC 1160 / ETH 1108) and stages the most setups
(BTC 87, ETH 106) but converts them no better — 4/3 triggered, the rest
abandoned. **`await_abandoned ≫ await_triggered` in every row that stages
anything**: the limit-await mechanism is where staged intent dies, independent
of the bias setting.

## 4. dol before/after (Step 3)

### 4.1 dol factor distribution — stale (Iter-01) vs fixed (this iteration)

| Symbol | metric | before (stale dol) | after (fixed, `dol_lookback_days=60`) |
|---|---|---:|---:|
| BTC | mean | −0.7072 | **−0.1950** |
| BTC | %bearish (<0) | 98.825% | **58.416%** |
| BTC | %bullish (>0) | 0.235% | 35.789% |
| BTC | %zero (=0) | 0.940% | 5.795% |
| ETH | mean | −0.4481 | **−0.1126** |
| ETH | %bearish (<0) | 82.379% | **51.994%** |
| ETH | %bullish (>0) | 15.037% | 42.367% |
| ETH | %zero (=0) | 2.584% | 5.638% |

The fix removes the monolithic bearish skew: BTC dol goes from ~99% bearish to a
58/36 bear/bull split; ETH from 82% bearish to a near-balanced 52/42. dol is no
longer a near-constant −1 vote.

### 4.2 The other four factors are unchanged (fix is isolated to dol)

Side-by-side of all five factors' sign share confirms **only dol moved**;
`struct_mtf`, `struct_htf`, `struct_wk`, `ipda` are byte-identical before/after
(as expected — the fix touches only the dol lookback):

| Factor | BTC bull/bear/flat, mean (before → after) |
|---|---|
| struct_mtf | 51.607/48.145/0.248, +0.0346 → **identical** |
| struct_htf | 60.061/36.807/3.132, +0.2325 → **identical** |
| struct_wk | 54.818/21.850/23.333, +0.3297 → **identical** |
| dol | 0.235/98.825/0.940, −0.7072 → **35.789/58.416/5.795, −0.1950** |
| ipda | 32.970/44.398/22.632, −0.1041 → **identical** |

(ETH likewise: struct_mtf 49.881/49.897/0.222 −0.0002, struct_htf
48.627/48.710/2.663 −0.0008, struct_wk 44.951/42.132/12.917 +0.0282, ipda
29.837/38.760/31.404 −0.0616 — all identical before/after; only dol moved from
15.037/82.379/2.584 −0.4481 → 42.367/51.994/5.638 −0.1126.)

## 5. Regime-separation tables (recomputed as Iter-01 §5, fixed dol)

### 5.1 Bias states (conviction bite) — before → after

| Symbol | \|score\|≥0.5 (bias exists) | bias bull | bias bear | flat |
|---|---:|---:|---:|---:|
| BTC before | 19.343% | 7.988% | 11.355% | 80.657% |
| **BTC after** | **16.980%** | **12.321%** | **4.660%** | **83.020%** |
| ETH before | 17.437% | 4.581% | 12.856% | 82.563% |
| **ETH after** | **17.829%** | **7.909%** | **9.919%** | **82.171%** |

**Headline regime shift:** with stale dol the tradeable bias was
**bear-dominant** (BTC 8.0% bull vs 11.4% bear; ETH 4.6% vs 12.9%). After the
fix it **flips bull-dominant on BTC** (12.3% bull vs 4.7% bear) and roughly
balances on ETH (7.9% vs 9.9%). The *rate* at which a bias exists barely moves
(BTC 19.3%→17.0%, ETH 17.4%→17.8%) — but its *direction* is materially
different. dol was previously vetoing the structure factors' bull lean; it no
longer does.

### 5.2 Score quintiles / distribution — before → after

Reported as Iter-01 did (mean/std/min/max + 1/5/25/50/75/95/99 percentiles;
these percentiles bracket the quintile boundaries at 25/50/75).

| Symbol | mean | std | min | max | p1 / p5 / p25 / p50 / p75 / p95 / p99 |
|---|---:|---:|---:|---:|---|
| BTC before | −0.0429 | 0.3548 | −0.9644 | +0.7020 | −0.940 / −0.587 / −0.298 / −0.013 / +0.200 / +0.600 / +0.614 |
| **BTC after** | **+0.0596** | 0.3273 | −0.7000 | +0.9333 | −0.600 / −0.480 / −0.200 / **+0.067** / +0.267 / +0.600 / +0.667 |
| ETH before | −0.0965 | 0.3389 | −0.9250 | +0.7091 | −0.829 / −0.637 / −0.354 / −0.093 / +0.133 / +0.474 / +0.615 |
| **ETH after** | **−0.0294** | 0.3326 | −0.9556 | +0.7429 | −0.743 / −0.552 / −0.250 / **−0.067** / +0.200 / +0.581 / +0.600 |

The whole score distribution shifts right (BTC median −0.013→+0.067; ETH
−0.093→−0.067) and its lower tail compresses (BTC min −0.964→−0.700) — the fix
removed the permanent dol drag pulling scores negative.

### 5.3 Per-factor sign agreement — before → after

| Symbol | ≥1 factor active | unanimous among active | all-5 active | all-5 active AND agree |
|---|---:|---:|---:|---:|
| BTC before | 99.752% | 7.883% | 60.535% | 2.428% |
| **BTC after** | 99.752% | 5.077% | 57.011% | **0.509%** |
| ETH before | 99.778% | 7.087% | 57.794% | 2.062% |
| **ETH after** | 99.778% | 4.699% | 57.245% | **0.744%** |

Counter-intuitively, **making dol more balanced *lowers* full-stack unanimity**
(BTC all-5-agree 2.43%→0.51%, ETH 2.06%→0.74%). Reason: previously dol was an
almost-always-bearish vote, so on the ~11–13% of bars where the stack leaned
bear, dol reliably joined → unanimity was inflated by a near-constant factor.
Now dol splits ~50/50 and frequently dissents, so genuine 5-way agreement is
rarer. The stack now "speaks with one voice" only ~0.5–0.7% of the time.

## 6. Calendar assembly + news-filter ablation (Step 4)

### 6.1 Calendar built and committed

`data/calendars/high_impact_2023_2026.csv` — committed as `4835ae4` (data-only;
`.gitignore` exempts `data/calendars/`; **no AI attribution** in the message per
project convention). **104 events**: FOMC=32, NFP=36, CPI=36. Header
`datetime,impact,event`; all `impact=high`; sorted ascending; first
`2023-01-06T13:30:00Z,high,NFP`, last `2026-12-09T19:00:00Z,high,FOMC`.

Provenance (per `docs/CALENDAR_SOURCES.md`): FOMC decision days from
federalreserve.gov (14:00 ET); NFP/CPI release dates from bls.gov schedules
**retrieved via the Wayback Machine** because bls.gov / FRED return HTTP 403 to
this environment — the archived pages are snapshots of the *primary source*, not
a re-aggregator. Each ET wall-clock time is localized with
`zoneinfo America/New_York` and converted to UTC (correct DST): winter 08:30 ET
= 13:30Z, summer = 12:30Z; winter 14:00 ET = 19:00Z, summer = 18:00Z (spot-checked).
The 2025 US-government-shutdown disruptions are encoded: NFP Sept→Nov 20, no
standalone Oct, Nov→Dec 16; CPI Sept→Oct 24, no Oct-ref, Nov→Dec 18. Parser
round-trip via `load_news_csv` returns 104 sorted epoch-seconds.

### 6.2 Ablation (V3 frozen, `news_csv` → committed calendar)

`news_csv` **replaces** the built-in default events (built-in = NFP + FOMC only)
with the assembled FOMC + NFP + CPI set (called without `impact_filter`, so all
104 rows apply). All other fields identical to frozen (`avoid_news=true`,
`news_before_min=30`, `news_after_min=60`, `news_day_blackout=true`).

| Symbol | Trades | Total ret | Mean R | vs frozen (built-in calendar) |
|---|---:|---:|---:|---|
| BTC | 0 | 0.00% | — | **funnel byte-identical to frozen** (see below) |
| ETH | 1 | −1.166% | −1.125 | same single trade; funnel reshuffled by one staged setup |

**BTC:** the assembled calendar leaves the funnel **byte-for-byte identical** to
the frozen built-in run (signals 5416 … await_abandoned 4). Adding CPI dates and
correcting the 2025 NFP schedule changed **no** BTC trade decision.

**ETH:** the single completed trade is **identical** (−1.166%, −1.125 R, 35-bar
hold). The funnel differs only downstream: `rejected_ote` 12→11, `placed_await`
8→9, `await_abandoned` 7→8 (`staged_attempts` unchanged at 22). One setup that
the built-in calendar's *phantom* first-Friday NFP blackout had suppressed
becomes eligible under the shutdown-corrected calendar, passes OTE, is placed,
then abandoned. Net effect on realized P&L: **zero.**

Interpretation: at the frozen baseline's trade density (0–1 trades/symbol), a
richer news calendar is **near-inert** — it cannot change a strategy that
essentially does not trade. The one observable difference (ETH's reshuffled
staged setup) actually flows from the corrected calendar being *less* restrictive
on 2025's non-existent first-Friday NFP dates, not from the added CPI blackouts.
This is an observation, not a defect.

## 7. ES / NQ sourcing scope (Step 5 — no purchases, no fetch, no NQ contact)

**No index data was fetched this iteration** (constraint honored). The
assessment below is from vendor knowledge + the loader's format contract; no
market-data endpoint was contacted. Context: even the *free macro* primary
sources (bls.gov, FRED) return HTTP 403 to this environment, so any
account/key-gated futures API is a fortiori unreachable from here without
credentials the sandbox does not hold.

### 7.1 Reachability of ES continuous-contract 15m + 1m sources

| Source | Reachable from this env? | Cost model | Roll options offered | Native export |
|---|---|---|---|---|
| **Databento** (CME Globex) | No — API key required; no key present | Pay-as-you-go (~$/GB; ES 1m multi-year ≈ tens of USD) | Continuous symbology `ES.c.0`/`ES.v.0`: calendar, **open-interest**, or volume roll; raw or adjusted | CSV or DBN; `ohlcv-1m`/`ohlcv-15m` schema `ts_event`(ns),open,high,low,close,volume |
| **FirstRate Data** | No — manual purchase + download | One-time (~low-tens USD for ES 1m history) | Continuous: OI/volume roll; ratio-adjusted or unadjusted variants | CSV `timestamp,open,high,low,close,volume` (ET) |
| **Polygon.io** (futures) | No — API key required | Subscription tier | Front-month continuous; roll per their futures spec | CSV/JSON, epoch-ms ts |
| **Kibot / Norgate / CME DataMine** | No — account/subscription or desktop app | Subscription / one-time | Continuous with configurable roll + back-adjust | CSV (vendor layout) |
| **Interactive Brokers TWS API** | No from sandbox (needs funded account + local gateway) | Free w/ funded acct | `CONTFUT` continuous; 1m limited to ~6 mo/request → must stitch | API objects → user-serialized |
| **Yahoo `ES=F` via yfinance** | Partially (network), but **unusable**: 1m intraday only ~last 60 days | Free | Front-month only, no roll control | — (history too short for 2023-2026 dev window) |

**Conclusion: no source can deliver ES continuous 15m + 1m for 2023-01-01 →
2026-07-01 from this environment without a purchase or credentials** (both
excluded by the constraint). The viable path is a **user-provided export**.

### 7.2 Exact file format the user should export (loader contract)

`load_candles` (`src/ict_backtest/data/loader.py`) accepts **CSV or Parquet**,
column names case-insensitive with aliases:

- timestamp: any of `ts | timestamp | time | date | datetime | open_time`
- OHLC: `open|o`, `high|h`, `low|l`, `close|c`; `volume|vol|v` (optional, defaults 0)
- timestamp values: **epoch seconds or milliseconds** (auto-detected; >10^10 ⇒
  treated as ms), **or** an ISO-8601 string (parsed as UTC; a naive string is
  assumed UTC).
- timeframe is inferred from the **median** inter-bar gap (robust to session
  gaps), or can be passed explicitly.

**Recommended export spec (two files per instrument, 15m and 1m):**

```
datetime,open,high,low,close,volume
2023-01-03T14:30:00Z,3850.25,3852.00,3849.50,3851.75,12345
...
```

- `datetime` in **ISO-8601 UTC with `Z`** (least ambiguous; loader-native). If
  the platform can only emit epoch, use **seconds or milliseconds — not
  microseconds/nanoseconds** (the loader's ms heuristic mis-scales ns, e.g.
  Databento `ts_event`; convert ns→s or export ISO instead).
- **Single continuous series** (not one file per expiry), same **roll rule for
  both** the 15m and 1m files, and the roll rule **documented** (recommend
  **open-interest roll**, the ES convention).
- **Session choice documented and matched** between 15m and 1m (23h Globex vs
  RTH-only) — the strategy's killzones use `America/New_York`; a mismatched or
  mislabeled session will misplace killzone masks.
- **Timezone normalized to UTC** before export (broker exports are frequently in
  Exchange/CT or platform-local; the crypto dev files are UTC, and killzone
  mapping assumes correct absolute time).

**Adjustment caveat for the architect (not decided here):** ICT geometry
(FVG/OB/OTE) depends on absolute price relationships across bars, so **raw
(unadjusted) continuous data carries a price gap at each roll** that can create
spurious gaps/levels, while **back-adjustment** (ratio or difference/Panama)
removes the gap but shifts historical absolute prices. Neither is strictly
correct for this strategy; the choice is an architect call. **NQ was not
contacted; no index data fetched.**

## 8. Anomalies

- **A1 — the dol fix reduced/di­d-not-increase trade count.** Frozen conv=0.50:
  BTC **2→0** trades, ETH single trade **changed identity** (−0.19% → −1.166%).
  Mechanism is traceable, not a leak: the fix flipped BTC's tradeable bias from
  bear-dominant to bull-dominant (§5.1) and shifted the score distribution right
  (§5.2); the specific bars that previously cleared all downstream gates in a
  *bearish* direction no longer do, and the newly-bullish bars do not clear them
  either. **Flagged, not tuned.** (Weights remain `(1,1,1,1,1)` per standing
  instruction to hold them until the fixed-dol regime tables are seen — which
  this report now provides.)
- **A2 — degenerate trade count persists (headline, carried from Iter-01).**
  Every matrix cell is n ≤ 4 over 3.5 years × 2 symbols; conv=0.75 is 0/0.
  With n ≤ 4 the null test is skipped, no CI is emitted, and p-values are
  placeholders. This is "too-few-to-evaluate," **not** "too-good" — consistent
  with V1's rare/edgeless finding, no leakage indicator (returns ≈0 to slightly
  negative, PF ≤ ~0.65, exposure ~0%). **Flagged, not tuned.**
- **A3 — `await_abandoned ≫ await_triggered` universally.** In every row that
  stages setups, the limit-await placements overwhelmingly abandon rather than
  trigger (e.g. BTC structure 24 abandoned / 4 triggered; ETH structure 28/3).
  The dominant conversion loss is at the await stage, not the bias vote.
  **Observation for the architect.**
- No STOP-worthy leakage condition triggered. The STOP-worthy issue remains the
  opposite pole (near-zero sample), surfaced not resolved.

## 9. Observations (facts) vs Proposals (for the architect)

**Observations**

1. The dol-staleness fix is **isolated and correct in its stated effect**: only
   the dol factor changed; it went from ~99%/82% bearish (BTC/ETH) to
   58%/52% (§4). The other four factors are byte-identical.
2. The fix's downstream effect on *trading* is **negative-to-neutral**: BTC
   frozen 2→0 trades, ETH's one trade worsened (§3.1, A1). Removing the dol drag
   did not unlock trades; it re-pointed the bias (bull-dominant on BTC) into a
   region the gate stack rejects just as hard.
3. **`rejected_bias` is the primary throttle at every conviction level**; at 0.75
   it is total (0 staged). At 0.25 the bias gate relaxes but losses move to
   `rejected_discount`/`rejected_time` and then to `await_abandoned` — the trade
   count does not scale up with looser conviction (BTC 4, ETH 2 at conv 0.25).
4. **Full-stack unanimity fell** after the fix (all-5-agree BTC 2.43%→0.51%),
   because a near-constant bearish dol had been inflating apparent agreement.
5. The assembled 104-event calendar is **near-inert at this trade density**
   (BTC funnel byte-identical; ETH same single trade). It is a fidelity upgrade
   (real CPI dates, shutdown-corrected NFP, whole-day blackouts) with no
   measurable P&L effect *because the strategy barely trades*.
6. No ES continuous 15m+1m source is reachable here without purchase/credentials;
   a user broker-export (spec in §7.2) is the only viable path.

**Proposals** (architect decides; nothing changed)

- **P1 — the trade-count floor is now the binding constraint, confirmed at fixed
  dol.** Across a full conviction sweep + structure variant, no dev-symbol cell
  reaches n≥5, so the preregistration's 500-sim null test can never gain power.
  Iter-03 likely needs a **single, a-priori-named gate relaxation** (the
  architect names the lever), not further baseline runs. The funnel points at
  **the await mechanism** (A3) and **`rejected_discount`/`require_htf_discount`**
  as the highest-yield candidates, since `rejected_bias` at conv≥0.5 is doing the
  intended job.
- **P2 — with the fixed-dol regime tables now in hand (§4–§5), the standing hold
  on weights `(1,1,1,1,1)` can be revisited.** dol is now a balanced factor, so
  equal weighting is defensible; but note that equal weights + balanced dol
  *reduced* trades, so a weight change alone is unlikely to fix trade count — it
  changes *direction*, not *frequency*. Recommend the architect treat weights and
  the trade-count lever (P1) as separate decisions.
- **P3 — ES onboarding:** if the architect wants ES in-scope, request the user
  export per §7.2 (two files, ISO-8601 UTC, OI-roll continuous, documented
  session). The adjustment choice (raw vs back-adjusted) should be decided before
  export, as it changes the price series the geometry sees.

## 10. Questions (blocking Iter-03)

1. **Which single gate is the a-priori lever for trade count?** Given the funnel,
   is it (a) `require_htf_discount` / `require_discount`, (b) the sweep→MSS /
   order-expiry await window (A3), or (c) `min_conviction`? One should be named
   before Iter-03 runs, to avoid a multiple-comparisons sweep.
2. **Weights:** now that the fixed-dol regime tables show a balanced dol, do
   weights stay `(1,1,1,1,1)`, or does the architect want a specific reweight
   tested alongside (P2)? (No change made this iteration.)
3. **ES scope:** proceed to request a user broker-export (§7.2), and if so, **raw
   or back-adjusted** continuous, and **RTH-only or 23h Globex**?
4. Is a **dol-only ablation** (Iter-01 P2, still un-run) wanted before any weight
   change, or is the dol question considered settled by the fix + §4–§5?

## 11. Determinism / reproduction

- **Commit:** `4835ae4` (data-only, atop `396cc1f` = dol fix). Preflight at HEAD:
  pytest 104 passed, ruff clean.
- **Anchor config:** `configs/v3_origin.toml` (frozen; `bias_mode=narrative`,
  `narrative_weights=[1,1,1,1,1]`, `narrative_min_conviction=0.5`,
  `dol_lookback_days=60`, `ipda_windows=[20,40,60]`, `ipda_hold_days=10`,
  `avoid_news=true`, `news_before_min=30`, `news_after_min=60`,
  `news_day_blackout=true`, no `news_csv`).
- **Derived temp configs (under `reports/dev/`, `configs/` untouched):**
  `_matrix_v3_conv025.toml`, `_matrix_v3_conv075.toml`, `_matrix_v3_structure.toml`
  (conv/bias_mode only), `_matrix_v3_news.toml` (frozen + `news_csv=
  data/calendars/high_impact_2023_2026.csv`).
- **Runners (read-only, `reports/dev/`):** `_matrix_runner.py` (8-cell matrix →
  `_matrix_results.json`), `_news_runner.py` (ablation → `_news_results.json`,
  run from repo root so the CWD-relative `news_csv` resolves), `_diagnostics.py`
  (fixed-dol regime tables), `_build_calendar.py` (calendar generator).
- **Data:** `data/{btc,eth}usdt_{15m,1m}.parquet`, 2023-01-01→2026-07-01,
  122,588 (15m) / 1,838,801 (1m) rows each, reused byte-identical from Iter-01.
- **Cost model:** `CostModel(spread_bps=1.0, commission_bps=2.0, slippage_bps=1.0)`;
  `Backtester(initial_equity=100_000, intrabar_policy="conservative", intrabar=1m)`.
- **Null:** `matched_baseline_test(..., eligible_mask=strategy.kz_mask, n_sims=500)`;
  skipped (`n_sims=0`) whenever n<5.
- **Holdouts:** BNBUSDT 2023-2026, ETHUSDT 2019-2022, SOLUSDT 2023-2026,
  BTCUSDT 2019-2022, NQ 2023-2026 — never fetched, inspected, or referenced. No
  index data fetched this iteration.
