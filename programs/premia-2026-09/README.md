# Program 2 — Systematic premia on free data (2026-09-08)

**Question.** Can a pre-registered, few-parameter systematic strategy on liquid futures/ETFs reach a net Sharpe ≥ 1.5 on a sealed two-year out-of-sample window (2024-07-01 → 2026-07-01), using free data and honest costs?

**Answer: no — and the OOS window was never opened.** Six pre-registered premises were tested in one day; all six failed their pre-stated gates. Two more were rejected at the literature stage; one was frozen but not run when the program was halted. Full record in [`RESULTS.md`](RESULTS.md) (scoreboard, post-mortems, conclusion).

| # | Premise | Data | Stitched Sharpe 2010–24 | Benchmark that beat it | Status |
|---|---|---|---|---|---|
| 1 | ES intraday momentum / dealer hedging (last hour) | ES 1h | −0.41 | — (gross edge 1.35 bp < 2 bp cost) | dead |
| 2 | ES noise-band breakout (trend day) | ES 1h | −0.23 | — (breach continuation 3.6 bp vs 37 bp noise) | dead |
| 3 | TSMOM, 20 ETFs, per-window lookback selection | ETF daily | 0.36 | TSH 0.52; fixed 12m 0.60 | dead |
| 4 | VIX-futures basis timing (VRP) | CBOE VX | 0.42 | always-short 0.49 | dead |
| 5 | FX carry (6 trusts) + US term spread | ETF + FRED | 0.08 | — (FX premise test wrong sign) | dead |
| 6 | Trend breadth: fixed 12m, class-balanced, 38 ETFs | ETF daily | 0.11 | TSH 0.30 | dead |
| 7 | Dash-for-cash turn-of-month, long ES T−3…T+3 | ES daily | not run | — | halted |
| — | Overnight drift, pre-FOMC drift, FOMC-cycle even weeks, news sentiment | — | — | rejected at literature stage | — |

**The finding.** On every shared calendar, the unconditional premium beat the timed version of itself (always-long ES 0.85, 60/40 0.93, always-short VIX 0.49, sign-of-historical-mean 0.52 vs 0.1–0.6 for every rule). Per-bet information was often real (premise-test t ≈ 2–2.6) but too small for the available breadth; Grinold's IR ≈ IC·√breadth reproduces the trend result from its measured IC of 0.05.

## Layout
- `STRATEGY_BRIEF.md` — the brief the program ran under (goal, budgets, stop rules, deliverables).
- `METHODOLOGY.md` — the 11-stage validation protocol (premise test → Masters (i)–(iv) → benchmarks → OOS once → Deflated Sharpe → bootstrap → sizing → paper-trading CUSUM) and the permutation schemes.
- `PREMISE_1.md … PREMISE_7.md` — pre-registrations, frozen before data, with amendments dated and justified in place.
- `RESULTS.md` — scoreboard, post-mortems, literature-stage rejections, program notes, conclusion.
- `TOOLING.md` — what was evaluated and dropped (free-only constraint).
- `premise1/ … premise7/` — code, `RESULTS_INSAMPLE.md`, stitched daily P&L, window tables, equity plots, no-lookahead tests. Each ran in seconds.
- `build/` — data builders (Databento ES 1m → 1h/4h with instrument-id keyed rolls; yfinance ETF universes; CBOE VX per-expiry files with the 2007 rescale; FRED rates/yields; ES daily settles + FOMC calendar).
- `data-validation/` — the hygiene reports each build produced, plus the ES roll schedule and FOMC dates. **No price data is included**: the Databento file is licensed; everything else is rebuilt from free sources by the scripts in `build/`.
- `trader-agent/` — Trail B, a separate discretionary daily-journal agent (playbook, scoring, ledger with dry-run entries only); firewalled from Trail A.

## Process notes worth keeping
- Pre-register before touching data; run a rule-independent premise test before any P&L; make the falsification benchmark "does the signal beat its own unconditional premium?".
- After P3, fixed literature parameters replaced per-window selection: 3-year training windows on a 4-point grid subtracted ~0.24 of Sharpe by selecting noise.
- Prefix-consistency (no-lookahead) tests caught a real σ lookahead in P4. Per-year coverage tables caught a silent 2012–13 gap in the VX build.
- Two process defects on record: an amendment appended to a frozen spec after its implementer had started (flagged by the implementer; both verdicts reported), and the VX merge rule that preferred a newer file format over valid data.
- The OOS window remains sealed for any future program.
