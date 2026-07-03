# M-02 Part A — Temporal robustness of the M1 anti-magnetism cell

**Role:** executor. **Status:** preregistered test executed; verdict recorded below.
**Tasking:** `reports/dev/M1_ADJUDICATION.md` (Part A). **Preregistration:** `reports/PREREGISTRATION_M.md`.

## What was tested

M1 found no support for liquidity magnetism (0/18 cells above 1.0). Post-hoc, the
**2.0–4.0 ATR / horizon-96 cell** came in *below* 1.0 (ci_hi < 1.0, "EXCL-DOWN") on
the full sample of all three datasets — an inverse "anti-magnetism" signal. Part A is
the prospective test of whether that single cell is temporally stable, run under the
symmetric anti-claim rule adopted before this run.

**Ruling object (declared before running):** the 2.0–4.0 ATR / h=96 cell.
**Reading rule (declared before running):** the cell is **CONFIRMED** iff it excludes
1.0 downward (`ci_hi < 1.0`) in **both** temporal halves of **≥2 of the 3 datasets**.
Any other outcome is recorded as **unstable, no claim**. No goalpost may move to h=384
or to another bucket after the fact.

## Invocation

- Tested library only, at M1 defaults. No new study code; no library changes.
- `run_magnetism(candles)` → `swing_k=3, eq_tol_atr=0.25, atr_period=14,`
  `horizons=(96, 384), buckets=((0.5,1.0),(1.0,2.0),(2.0,4.0)), baseline_k=20, seed=42`.
  Block-bootstrap CI internal `n_boot=4000, seed=7` (unchanged).
- Driver: `reports/dev/_m2_parta_runner.py` (thin — loads halves via the library's own
  date-windowed `load_candles(start=, end=)`, calls `run_magnetism`, dumps JSON). Raw
  output: `reports/dev/_m2_parta_results.json`.
- Burned data only (ES 2010–2026, BTC/ETH 2023–2026). No holdouts touched.

## Realized temporal halves

The loader is half-open (`ts >= start & ts < end`). Each dataset is cut at a single
split date, so the two halves are disjoint, gap-free, and their union is exactly the
M1 full sample. H1 = `end=SPLIT`; H2 = `start=SPLIT`.

| dataset | split | H1 window (realized) | H1 bars | H2 window (realized) | H2 bars | H1+H2 | M1 full |
|---|---|---|---|---|---|---|---|
| ES  | 2018-07-01 | 2010-06-06 .. 2018-06-29 | 188574 | 2018-07-01 .. 2026-06-30 | 188194 | 376768 | 376768 |
| BTC | 2024-10-01 | 2023-01-01 .. 2024-09-30 | 61339  | 2024-10-01 .. 2026-06-30 | 61249  | 122588 | 122588 |
| ETH | 2024-10-01 | 2023-01-01 .. 2024-09-30 | 61339  | 2024-10-01 .. 2026-06-30 | 61249  | 122588 | 122588 |

Union == full sample for all three (verified). ES 2018-06-30 is a Saturday, so H1's last
bar is Fri 2018-06-29; this is a labeling note only — no bars are dropped or double-counted.

## Ruling cell — 2.0–4.0 ATR / h=96, exact bounds

| dataset | half | n | ratio | ci_lo | ci_hi | EXCL-DOWN? |
|---|---|---|---|---|---|---|
| ES  | H1 | 7751 | 0.9698 | 0.9537 | 0.9853 | **yes** |
| ES  | H2 | 7778 | 0.9781 | 0.9622 | 0.9942 | **yes** |
| BTC | H1 | 2514 | 0.9920 | 0.9659 | 1.0198 | no |
| BTC | H2 | 2587 | 0.9860 | 0.9596 | 1.0136 | no |
| ETH | H1 | 2608 | 0.9683 | 0.9434 | 0.9947 | **yes** |
| ETH | H2 | 2260 | 0.9694 | 0.9406 | 0.9973 | **yes** |

- **ES**: both halves EXCL-DOWN → passes.
- **ETH**: both halves EXCL-DOWN → passes.
- **BTC**: neither half EXCL-DOWN — both CIs straddle 1.0. BTC is the thinnest per-half
  dataset here (~2.5k ruling-cell events per half vs ES's ~7.8k); the widened CI is the
  proximate cause. **Does not pass.**

Datasets passing both halves: **ES, ETH → 2/3.**

## VERDICT

**Anti-magnetism cell CONFIRMED** under the predeclared rule (≥2/3 datasets EXCL-DOWN in
both halves): **ES and ETH pass both halves; BTC does not.**

Stated plainly and without inflation: this clears the bar at its **minimum threshold
(exactly 2/3)**, and the one dataset that fails (BTC) does so in *both* halves. The
confirmed effect is a ~2–3% *under*-touch of the ATR-matched baseline in the 2.0–4.0 ATR
band at 96 bars — small, inverse to the folklore magnetism claim, and carried by ES + ETH.
Per the ruling, no claim is extended to h=384 or to any other bucket. BTC h=384 does show
EXCL-DOWN in H1 (`[0.9554, 0.9931]`) but that is outside the declared ruling object and is
reported only for completeness, not as support.

## All cells (exact 4-dp bounds, both halves, all datasets)

| dataset | half | bucket | h | n | ratio | ci_lo | ci_hi | flag |
|---|---|---|---|---|---|---|---|---|
| ES | H1 | 0.5-1.0 | 96 | 9053 | 0.9848 | 0.9773 | 0.9921 | EXCL-DOWN |
| ES | H1 | 0.5-1.0 | 384 | 9044 | 0.9925 | 0.9871 | 0.9978 | EXCL-DOWN |
| ES | H1 | 1.0-2.0 | 96 | 15902 | 0.9946 | 0.9863 | 1.0028 | — |
| ES | H1 | 1.0-2.0 | 384 | 15881 | 0.9966 | 0.9902 | 1.0030 | — |
| ES | H1 | 2.0-4.0 | 96 | 7751 | 0.9698 | 0.9537 | 0.9853 | EXCL-DOWN |
| ES | H1 | 2.0-4.0 | 384 | 7734 | 0.9861 | 0.9743 | 0.9979 | EXCL-DOWN |
| ES | H2 | 0.5-1.0 | 96 | 8980 | 0.9990 | 0.9920 | 1.0060 | — |
| ES | H2 | 0.5-1.0 | 384 | 8966 | 0.9991 | 0.9937 | 1.0043 | — |
| ES | H2 | 1.0-2.0 | 96 | 15133 | 0.9970 | 0.9888 | 1.0053 | — |
| ES | H2 | 1.0-2.0 | 384 | 15103 | 0.9976 | 0.9909 | 1.0040 | — |
| ES | H2 | 2.0-4.0 | 96 | 7778 | 0.9781 | 0.9622 | 0.9942 | EXCL-DOWN |
| ES | H2 | 2.0-4.0 | 384 | 7770 | 0.9864 | 0.9740 | 0.9982 | EXCL-DOWN |
| BTC | H1 | 0.5-1.0 | 96 | 2817 | 0.9948 | 0.9817 | 1.0083 | — |
| BTC | H1 | 0.5-1.0 | 384 | 2808 | 0.9932 | 0.9829 | 1.0026 | — |
| BTC | H1 | 1.0-2.0 | 96 | 5593 | 0.9978 | 0.9845 | 1.0117 | — |
| BTC | H1 | 1.0-2.0 | 384 | 5570 | 1.0088 | 0.9975 | 1.0195 | — |
| BTC | H1 | 2.0-4.0 | 96 | 2514 | 0.9920 | 0.9659 | 1.0198 | — |
| BTC | H1 | 2.0-4.0 | 384 | 2498 | 0.9746 | 0.9554 | 0.9931 | EXCL-DOWN |
| BTC | H2 | 0.5-1.0 | 96 | 2562 | 0.9968 | 0.9824 | 1.0112 | — |
| BTC | H2 | 0.5-1.0 | 384 | 2546 | 0.9972 | 0.9864 | 1.0071 | — |
| BTC | H2 | 1.0-2.0 | 96 | 5437 | 0.9867 | 0.9726 | 1.0012 | — |
| BTC | H2 | 1.0-2.0 | 384 | 5413 | 0.9980 | 0.9867 | 1.0086 | — |
| BTC | H2 | 2.0-4.0 | 96 | 2587 | 0.9860 | 0.9596 | 1.0136 | — |
| BTC | H2 | 2.0-4.0 | 384 | 2574 | 0.9901 | 0.9692 | 1.0100 | — |
| ETH | H1 | 0.5-1.0 | 96 | 2770 | 1.0116 | 0.9990 | 1.0236 | — |
| ETH | H1 | 0.5-1.0 | 384 | 2759 | 1.0062 | 0.9971 | 1.0148 | — |
| ETH | H1 | 1.0-2.0 | 96 | 5598 | 0.9917 | 0.9775 | 1.0056 | — |
| ETH | H1 | 1.0-2.0 | 384 | 5578 | 0.9968 | 0.9854 | 1.0081 | — |
| ETH | H1 | 2.0-4.0 | 96 | 2608 | 0.9683 | 0.9434 | 0.9947 | EXCL-DOWN |
| ETH | H1 | 2.0-4.0 | 384 | 2588 | 0.9855 | 0.9668 | 1.0043 | — |
| ETH | H2 | 0.5-1.0 | 96 | 3010 | 0.9853 | 0.9716 | 0.9985 | EXCL-DOWN |
| ETH | H2 | 0.5-1.0 | 384 | 2994 | 0.9936 | 0.9828 | 1.0041 | — |
| ETH | H2 | 1.0-2.0 | 96 | 5689 | 0.9941 | 0.9804 | 1.0080 | — |
| ETH | H2 | 1.0-2.0 | 384 | 5658 | 0.9998 | 0.9879 | 1.0112 | — |
| ETH | H2 | 2.0-4.0 | 96 | 2260 | 0.9694 | 0.9406 | 0.9973 | EXCL-DOWN |
| ETH | H2 | 2.0-4.0 | 384 | 2249 | 0.9860 | 0.9665 | 1.0054 | — |

## Verification gate

- `pytest`: 117/117 pass.
- `ruff check src tests`: clean.
- `ruff check .` reports one F541 in `reports/dev/_es_stitch.py:306` — a pre-existing,
  untracked scratch file not authored for M-02 and unrelated to this study. Not fixed
  (out of scope); the library gate (`src`/`tests`) is clean.
