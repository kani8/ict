# RESULTS — Trail A (systematic ES research)

Brief: `STRATEGY_BRIEF.md`. Budget: 4 pre-registered premises. OOS window 2024-07-01 → 2026-07-01 remains **unopened**.

| # | Premise | Pre-registered | Premise test | WF gate (Sharpe ≥ 1.0, ≥ 800 trades) | OOS | Status |
|---|---|---|---|---|---|---|
| 1 | Intraday momentum / dealer hedging demand (prev close → 15:00 predicts 15:00 → 16:00) | 2026-09-08 | β = 0.034, t = 2.06 (bare pass); clause 2 falsified | **FAIL** — Sharpe −0.41, 1,101 trades | not opened | **DEAD** |
| 2 | Intraday trend continuation from the open (noise-band breakout, 1h marks, flip on opposite band, flat at close) | 2026-09-08 | β = 0.080, t = 2.02 (bare pass); breach continuation +3.6 bp vs 37 bp noise | **FAIL** — Sharpe −0.23, 1,172 trades | not opened | **DEAD** |
| 3 | Multi-asset TSMOM, 20 ETFs, monthly, L ∈ {3,6,12,COMBO} selected per window (gate: Sharpe ≥ 0.5, > TSH, ≥ 8/14 yrs, perm p < .05) | 2026-09-08 | β = 0.015, t = 1.64 (**fail**) | **FAIL** — stitched 0.36; TSH 0.52; 8/14 yrs; WF-perm p = 0.050 | not opened | **DEAD** |
| 5 | Carry: XS rank FX carry (6 trusts) + US term-spread sign (IEF/TLT), zero params (gate a–d as P3) | 2026-09-08 | FX β = −0.007, t = −0.93 (**wrong sign**); IEF t = 1.60 | **FAIL** — stitched 0.08; no-signal −0.12; 7/14 yrs; perm p = 0.45 | not opened | **DEAD** |
| 6 | Trend breadth: fixed 12m TSMOM, class-balanced risk, 38 ETFs, zero params (gate a–d as P3) | 2026-09-08 | β = 0.011, t = 1.25 (**fail**) | **FAIL** — stitched 0.11; TSH 0.30; 6/14 yrs; perm p = 0.20 | not opened | **DEAD** |
| 4 | VRP: VIX-futures basis timing, θ fixed 0.005, zero params (gate a–d) | 2026-09-08 | β = −0.50, t = −2.58 (**pass**; backwardation half t = −3.64) | **FAIL** — stitched 0.42; always-short 0.49; 9/14 yrs; perm p = 0.27 | not opened | **DEAD** |
| 7 | Dash for cash: long ES T−3…T+3 only, zero params (gate a–d; benchmark always-long) | 2026-09-08 | not run | not run | not opened | **HALTED** (spec frozen; programme stopped by user before the data build finished) |
| 8 | FOMC cycle | — | rejected at literature stage | — | — | **NOT USED** |

## Programme conclusion — 2026-09-08

**Outcome: negative.** Six pre-registered premises were tested; all six failed their pre-stated gates. Two further candidates were rejected at the literature stage, one (P7) was frozen but not run when the user halted the programme. The OOS window 2024-07-01 → 2026-07-01 was **never opened** and remains sealed for any future programme. Target (net Sharpe ≥ 1.5 OOS) not met; no strategy is recommended for paper trading.

**The finding.** On every common calendar we built, the *unconditional* premium beat the *timed* version of itself: always-long ES/SPY 0.85, 60/40 0.93, always-short VIX futures 0.49, sign-of-historical-mean (TSH) 0.52 — against 0.1–0.6 for every rule that tried to time them. In 2010–2024, on free data, with honest costs and a one-day execution lag, timing subtracted value everywhere we looked. The per-bet information was real in several cases (t ≈ 2–2.6 premise tests) but too small for the breadth available: Grinold's IR ≈ IC × √breadth reproduces P3's 0.6 from its measured IC of 0.05 and ~120 effective bets a year.

**What worked as process.** Pre-registration before data; a rule-independent premise test before any P&L; falsification benchmarks that ask "does the signal beat its own unconditional premium?"; Masters' permutation gates; no-lookahead prefix tests (which caught a real σ-lookahead bug in P4); fixed literature parameters after P3 showed 3-year selection windows add noise; free data only. Two process defects are on record: Amendment A1 to P3 landed after its implementer started (flagged by the implementer), and the first VX build silently dropped 2012–13 settles (caught by the per-year coverage table).

**What would change the answer.** Breadth (hundreds of instruments), negative execution cost (liquidity provision), shorter horizons with order-book data, or proprietary data — none available under this brief. A realistic product of this setup is a diversified 0.7–1.0 portfolio of honest premia, not a 1.5.

---

## Premise 1 — post-mortem (2026-09-08)

Spec: `PREMISE_1.md` (frozen, with Amendment A1). Code and full tables: `premise1/`. Runtime 1.2 s. No-lookahead prefix test passed at 5 cutoffs. OOS guard verified to refuse the combined file.

**What the data said**
- Pooled in-sample regression of the last-hour return on the day-so-far return: β = 0.034 (t = 2.06, HAC-5), R² = 0.77 %, N = 3,358. The literature reports β ≈ 0.042–0.069 and R² ≈ 1.5–2.5 % for the last *half*-hour. So the effect exists on ES at the 1h horizon at roughly half the documented strength.
- Independent zero-cost check (always trade sign of day-so-far, 1 unit): **+1.35 bp/day gross**, annualised Sharpe 0.56 before costs, hit rate 48.3 %. Round-trip cost at 1-tick slippage on MES ≈ 2 bp. **Gross edge < cost.** This is the cause of death; the walk-forward only made it visible.
- Falsifiable clause 2 ("larger when |move| is large relative to vol") is **not supported**: β by |z| tercile = 0.096 / 0.068 / 0.025 (low → high). The |z| gate therefore selected the *weaker* part of the distribution.
- Walk-forward (3y/1y, 11 windows): stitched net Sharpe −0.41 baseline, −0.96 at 2-tick stress; net P&L −$58k on a $100k book; losing in 9 of 11 test years. Reference "always trade k = 0": Sharpe −0.87. Matched-null p = 0.13 — indistinguishable from random direction.
- Year-by-year gross edge flips sign constantly (−4.9 bp 2010 … +5.2 bp 2022 … −3.0 bp 2024). Consistent with Rosa (2022): regime-dependent, no stable OOS predictability.

**What was right about the process**
- The premise test threshold (t > 2) was met, so the gate did real work: a premise can be statistically "there" and still economically dead. Gate ordering (premise test → WF gate → OOS) was correct.
- Amendment A1 skips (roll-crossing, day after early close) fired 57 and 88 times — the second more than estimated because ES prints on Globex during SIFMA half-days too. Both are parameter-free and only removed days.

**What I will not do**
- Switch to the 15:30–16:00 window, add a VIX/FOMC/day-of-week filter, or re-open the grid. All pre-excluded.

**Carry-forward for later premises**
- **Cost hurdle:** any single-decision 1h ES trade needs > ~2 bp gross per trade at MES costs (≈ 1–1.7 bp at ES size) just to break even; a credible premise should plausibly deliver > 4–5 bp per trade *gross* or it is not worth a slot.
- Sizing: 12 % vol target on a 1h hold capped at 40 MES in 38 % of trades; on a losing strategy max drawdown exceeded the notional book. Any surviving premise needs an equity-based throttle before paper trading (not a parameter — a risk control).
- Note for Trail B: ES's last-hour return has been ≈ flat on average (−0.5 bp/day always-long) in this sample.

## Premise 2 — post-mortem (2026-09-08)

Spec: `PREMISE_2.md`. Code and tables: `premise2/`. Runtime 10 s. No-lookahead prefix test passed at 5 cutoffs (exercises σ_t and σ_4h). Premise regression verified identical across all 9 grid points.

**What the data said**
- Unconditional: r(prev close → 10:00) predicts r(10:00 → 16:00) with β = 0.080, t = 2.02, R² = 0.5 %. Present, weak.
- Conditional (the actual trade): over 5,660 hourly band breaches (m = 1, N = 14; 28 % of decision points), mean continuation to the close = **+3.6 bp**, against an unconditional mean |move-to-close| of 37 bp. Round-trip cost ≈ 2 bp; whipsaw flips add more. **Signal-to-noise ≈ 0.1; gross edge ≈ cost.**
- Walk-forward: stitched net Sharpe −0.23 (stress −0.58), net −$33k, 0.45 trades/day, hit rate 51 %, mean net −$28/trade, mean hold 4.6 h. Reference fixed m = 1, N = 14: −0.20. Long-only leg +0.20, short leg −0.69 — downside breaches reverted in 2013–2024. Matched-null p = 0.20.
- Losing years cluster in low-vol regimes (2014–17) and 2023–24; the only strong year is 2022–23. Same regime signature as premise 1 and as the source paper's own worst years.

**Spec defect (mine):** σ_4h for sizing was taken from the 4h bar ending 14:00 ET and applied to entries at 10:00–13:00 — a same-day *sizing* lookahead (direction unaffected). Cannot rescue a losing rule; corrected in future specs by using the last 4h bar that *ends before the decision time*.

**Family-level conclusion.** Premises 1 and 2 are two expressions of the same mechanism — intraday flow-driven continuation (dealer gamma, execution algos, close rebalancing). On ES 2010–2024 at 1h granularity the effect is real (both premise tests pass with t ≈ 2) but delivers **1–4 bp gross per decision against ~2 bp cost**. The literature's headline results live at 30-minute granularity, on SPY, and in 2007–2013 / 2020–2022 vol regimes. This family is closed for this brief; no 30-min re-runs (pre-excluded).

## Candidates rejected at the literature stage (no slot used, no data touched)

| Candidate | Why rejected |
|---|---|
| Overnight drift at the European open, long ES 02:00–03:00 ET (Boyarchenko, Larsen & Whelan, *RFS* 2023) | Authors' own strategy test: pre-cost Sharpe 1.1, **post-cost −0.5**; 01:30–03:30 variant post-cost 0.3. Authors' July 2026 follow-up: effect **≈ zero in 2021–2025** (closing-imbalance dispersion collapsed 6.5 % → 2.9 %; NightShares ETFs closed after 14 months). That window is our OOS. Bondarenko & Muravyev (*JFQA*) 4h European-open window Sharpe 1.6 is the same phenomenon, pre-2021. |
| Pre-FOMC drift / macro-announcement premium (Lucca & Moench 2015; Savor & Wilson 2013) | Long-only; pre-FOMC drift documented as decayed post-2015; ~30 events/yr cannot reach Sharpe 1.5 alone. |
| News / social-sentiment / finfluencer signals | No free point-in-time history → untestable; finfluencer literature finds majority anti-skilled. Routed to Trail B as a forward-only journal. |
| FOMC-cycle even weeks (Cieslak, Morse & Vissing-Jorgensen, *JF* 2019; candidate P8) | Even-week Sharpe 0.92 vs 0.45 always-in, 1994–2016 — but Uppal's replication through 2023 finds the effect lost significance around 2004, when the Board's biweekly meetings (the proposed informal-communication channel) ended; post-crisis coefficients ≈ 0 or negative. The documented cause was gone before our 2010 in-sample starts. Rejected 2026-09-08; the eighth slot is not used. |

## Scope change — 2026-09-08 (user decision)

After two dead premises and one literature-stage rejection, the evidence is that single-instrument ES intraday edges are sub-cost. Sharpe ≥ 1.5 in the literature is reached by **pooling many markets**. Decision: remaining slots (3, 4) move to **multi-asset daily trend / carry** on free daily data (liquid ETF proxies for equity indices, bonds, commodities, currencies). Unchanged: the Sharpe ≥ 1.5 OOS target, the sealed OOS window 2024-07-01 → 2026-07-01, 3y/1y walk-forward, ≤ 4 parameters, pre-registration before data, constant-vol sizing, block-bootstrap and cost robustness, paper trading before capital. Dropped: the 1h/4h ES-only framing (the user's original brief left instrument choice open; the 1h/4h spec was added later and has now been tested to its limit).

## Programme v2 — 2026-09-08 (user: strict Sharpe ≥ 1.5 target, large token budget)

The unit of delivery changes from *one strategy* to a **pre-registered ensemble of uncorrelated return sources** — the only construction with a documented route to Sharpe 1.5. Rules, fixed now:
- Legs: P3 Trend (running); P4 Volatility risk premium (VIX-futures basis timing); P5 Carry (FX interest differentials + bond term premium); optional P6 Trend-breadth (the frozen P3 rule on a ~45-ETF universe, testing the breadth prediction). Premise cap raised **4 → 6** to accommodate legs; every trial is charged in the Deflated Sharpe at OOS.
- Each leg passes the full `METHODOLOGY.md` protocol on its own (premise test, in-sample and walk-forward permutation gates, falsification benchmark).
- **Combination rule, fixed before any OOS look:** equal risk weight across passing legs, each leg scaled to 10 % ex-ante vol on its own stitched series, ensemble re-scaled to 10 % ex-ante vol monthly, 3× gross cap. No leg weights are optimised.
- **OOS is opened exactly once**, for the ensemble and its legs together. If only one leg passes its gates, the deliverable is that one leg.
- Reporting fact, stated up front: a 2-year Sharpe has standard error ≈ 1.0. The OOS number will be reported with its bootstrap CI and Deflated Sharpe; a single 2-year print above or below 1.5 is weak evidence either way, and we will say so.

## Premise 3 — post-mortem (2026-09-08)

Spec: `PREMISE_3.md` (frozen, Amendment A1). Code and tables: `premise3/` (800 lines incl. the permutation harness — over the ~350 budget, disclosed by the implementer; the permutation and grid-sensitivity code is reusable by P4–P6). Runtime 30 s. No-lookahead prefix test passed at 5 cutoffs.

**What the data said**
- Premise test: pooled monthly panel β = 0.015, **t = 1.64**, R² = 0.24 %, N = 4,500 — below the t > 2 screen. No asset class individually above t = 1.1. On 20 ETFs 2007–2024 the sign of the trailing 12-month return is only weakly informative about the next month.
- Walk-forward (14 windows, L selected per window): stitched net Sharpe **0.36** (0.32 at ×1.5 costs), ann. return 3.8 %, vol 10.6 %, max DD −27 %, avg gross leverage 2.3×, cap binding 22 % of rebalances. Long leg Sharpe 0.59, **short leg −0.22**. 8/14 positive years.
- **TSH 0.52 > TSMOM 0.36**: the falsification clause fired. Huang–Li–Wang–Zhou's critique holds on this universe — the sign of the historical mean (i.e. long the risk premia) beats the sign of the trend. Note TSH's SPY correlation is 0.70 vs TSMOM's 0.06; TSH is mostly a long-everything portfolio in a 14-year bull market.
- Masters (i)–(iv): full-span best L = 12, Sharpe 0.57; in-sample permutation p = 0.010; walk-forward permutation **p = 0.050** (gate d requires < 0.05 — fails on the boundary). Matched sign-flip null p < 0.001.
- **Pre-specified reference (TASK.md step 4): fixed L = 12 throughout, no selection → Sharpe 0.60**, max DD −26 %. Selection among four near-equivalent lookbacks on 3-year training windows *subtracted* ~0.24 of Sharpe. Grid-sensitivity table confirms it: selected-L train Sharpes are spiky (0.14–1.25), and the chosen L flips 6→3→12→…→COMBO across windows.
- Per-window test Sharpes range −0.76 (2018–19) to +1.68 (2020–21); 2022–24 negative — the April-2025-style reversal problem already visible.

**Process note — recorded verbatim in spirit.** Amendment A1 (Masters (i)–(iv), gate (d)) was appended to `PREMISE_3.md` after the implementer had started coding but before any result existed; it *added* a gate criterion (stricter) and diagnostics and touched no rule, grid, sizing, cost or universe. The implementer flagged the mid-task edit to a document marked FROZEN as a pre-registration violation and reported both verdicts separately. The flag is correct in form: amendments to a frozen spec must be complete before an implementer is launched. Both verdicts are FAIL, so nothing turns on it here; P4–P6 specs are complete, including (i)–(iv), before any implementer starts.

**What I will not do**
- Re-score P3 on the fixed-L reference (0.60 would pass gates a–c) — that is exactly the post-hoc switch pre-registration forbids. P3 is dead as registered. The fixed-rule lesson is applied *forward*, to premises whose data has not been touched.

**Carry-forward**
- **Fixed literature parameters beat 3-year-window selection when the grid is small and near-equivalent.** P4 and P5 are amended (before data) to zero free parameters: the literature value is fixed and the grid becomes a sensitivity table. P6 is pre-registered the same way.
- The short leg of ETF trend lost money for 14 years; long-biased premia dominated. Any surviving trend leg is likely to be a long-tilted diversifier, not a Sharpe-1.5 engine.
- Breadth on this universe was ~15 effective bets; the TSH comparison needs a universe where "long everything" is less of a free lunch — P6 tests that with class-balanced risk on 38 ETFs.

## Premise 4 — post-mortem (2026-09-08)

Spec: `PREMISE_4.md` (frozen; A1 zero-parameter). Code: `premise4/` (517 lines). No-lookahead PASS at 5 cutoffs — and it caught a real bug during implementation (σ initially computed from a return series indexed by its start date, leaking t+1's settle; fixed to `EWMA(ret.shift(1))`). Data: CBOE per-expiry VX 2004–2024 with the 2007 rescale and the 2012–13 settle gap repaired.

**What the data said**
- Premise test **passes**: next-day held-contract return on today's roll, β = −0.50, **t = −2.58**, R² 0.3 %, N = 5,022. Split: contango half t = −0.79, **backwardation half t = −3.64**. The basis carries information mainly when the curve is inverted — i.e. it tells you when to be *long* VIX futures in a panic.
- Stitched 2010–2024, θ = 0.005: net Sharpe **0.42** (1 tick), **0.20** at 2 ticks; ann. return 3.0 % on 7.1 % vol (the 10 % target is not reached because time-in-market is 61 %); max DD −21 %; worst day −5.1 %; 20 trades/yr; roll cost 37 % of total cost. Long leg 0.24, short leg 0.41. 9/14 positive years; 2021–22 −$15k, 2018–19 −$6.7k.
- **Always-short: 0.49** with max DD −37 % and worst day −19.6 % (Feb 2018). Gate (b) fails: timing lowered the drawdown but did not raise the Sharpe. Permutation p = 0.27. Sensitivity: θ = 0.0075 would have scored 0.49 — equal to always-short, still not above it; θ = 0 (pure sign) 0.30. Nothing on the grid beats the unconditional premium.
- Correlation with SPY 0.12, with P3 0.18 — it would have diversified.

**Why, in one line.** With a 1-day settle-to-settle lag and a tick-per-side cost on every entry, exit and roll, the basis rule spends its edge on turnover and on being late into and out of spikes; the unconditional short earns the same premium with fewer trades. The literature's Sortino 1.0–1.3 came from 2007–2011, with an ES hedge and a $/day threshold in a higher-VIX regime.

**Not done, deliberately.** No ES hedge (S&C's version; a second instrument and a fitted ratio), no intraday execution at the 16:15 print, no Cheng model-based premium. Each would be a new premise, and the family's unconditional Sharpe of ~0.5 caps what timing could add.

## Premise 6 — post-mortem (2026-09-08)

Spec: `PREMISE_6.md` (zero parameters). Code: `premise6/` (500 lines; P3's math imported, orchestration rewritten because P3's report helpers close over its 20-name universe). No-lookahead PASS.

- Premise test on 38 ETFs: β = 0.011, **t = 1.25**; no class above t = 1.6 (commodities). Stitched Sharpe **0.11**, TSH 0.30, 6/14 positive years, permutation p = 0.20, max DD −41 %, cap binding 42 % of rebalances.
- **Breadth falsified for ETF trend.** Sensitivity (report-only): 1/N L = 12 on 38 names 0.24 vs 0.60 on P3's 20; class-balanced worse still. The added names (country funds at 0.8 correlation to each other, UNG/USO contango decay, low-vol MBB forcing the leverage cap, RWX −$15k) reduced, not raised, the Sharpe. Class balancing pushed risk into 3 %-vol bond ETFs and bound the 3× cap 42 % of the time, which distorts the whole book.
- Correlation with P3 0.65 — same bets, more noise.

**Family closed.** Trend on free ETF data: the only construction that scored ≥ 0.5 was the fixed 12-month rule on the original 20 names (0.60, P3's pre-specified reference), and P3 as registered failed. No further trend variants.

## Programme note — 2026-09-08 (user decision): premise cap 6 → 8
With P1–P3, P5, P6 dead and P4 running, the user chose to add two zero-parameter **calendar premia on the existing ES data** rather than stop: P7 "dash for cash" (Etula–Rinne–Suominen–Vaittinen 2020) and P8 FOMC cycle (Cieslak–Morse–Vissing-Jorgensen 2019). Stated confidence at the time of the decision: ~10–15 % that the OOS print clears 1.5, < 5 % that the true Sharpe does. Sequence unchanged: literature verification (agent without data access) → frozen spec → hygiene-only data build → implementer.

## Premise 5 — post-mortem (2026-09-08)

Spec: `PREMISE_5.md` (frozen; A1 zero-parameter, A2 missing-rate rule). Code: `premise5/` (≈ 610 lines, mostly imports of `premise3/strategy.py` via importlib). No-lookahead PASS at 5 cutoffs. Missing-rate rule fired once in-sample (USD, 2020-04), never a zero-weight event.

**What the data said**
- FX premise test: pooled panel β = −0.007, **t = −0.93 — the wrong sign**. In 2007–2024, on six G10 currencies, higher 3-month differentials did not predict higher next-month excess returns; if anything the reverse. Bond premise test: IEF t = 1.60, TLT t = 1.45 — right sign, below the screen.
- Stitched 2010–2024 leg Sharpe **0.08** (FX sleeve −0.19 full span, bond sleeve 0.36); leg no-signal −0.12 (gate b technically passes because the naive benchmark is worse, not because the leg is good); 7/14 positive years; permutation **p = 0.45**. Sensitivity: TS and BOTH variants 0.05–0.10 — nothing on the grid works, so Amendment A1's fixing of XS cost nothing.
- Correlation with P3 stitched: 0.09 — it would have been a diversifier, of nothing.

**Why, in one line.** G10 rate dispersion was < 1 % for eleven of the fourteen years; with six currencies and 10 bp costs the signal is noise, and the 2022–24 dispersion revival is long-USD, which a dollar-neutral rank portfolio cannot express. The pre-stated failure mode ("rate-compression regimes") is the whole story.

**Carry-forward.** Carry on free ETF data is closed for this brief. No re-runs with more currencies (not free), commodity curves (no free per-contract data except VX) or international bonds (short history).

## Premises 4 and 5 — frozen 2026-09-08 before data download

Literature verification (subagent, primary sources only; 72 fetches):
- **P4 VRP / VIX basis** (`PREMISE_4.md`): Simon & Campasano 2014 verified — basis predicts VX futures changes (coef −0.79, R² ≈ 10 %), not VIX itself; $100/$50-per-day entry/exit; hedged Sortino 1.26 short / 1.03 long, 2007–2011; ≈ $140 round-trip cost. Cheng 2019 verified — premium-sign timing Sharpe 0.87 vs always-short 0.57; premium *falls* as risk rises. Eraker & Wu 2017, Johnson 2017 verified. **Gap on record:** no peer-reviewed quantification of basis timing through Feb 2018, Mar 2020 or 2022–2025. Cheng's model-based premium rejected for our use (needs a VIX forecast model → extra parameters); the model-free basis is used with one threshold parameter.
- **P5 Carry** (`PREMISE_5.md`): Koijen et al. 2018 and the UIP-failure literature (not re-verified today; marked in the spec). Data: FRED `IR3TIB01` monthly interbank rates live for all seven currencies; DGS10/DGS20/DTB3 daily; six surviving CurrencyShares trusts (survivorship stated).
- **Data facts found:** CBOE per-expiry VX files are free from the 2004 launch (archive naming `CFE_<M><YY>_VX.csv`, new naming `VX_<expiry>.csv` from 2013); pre-2007-03-26 settles are 10× (contract rescale) and are divided by 10 in the build. Spot VIX free from 1990. Yahoo's VXX history starts at the 2018 re-issue and SVXY changed leverage in Feb 2018 — ETN proxies are unusable for a backtest, which is why the leg is built on the futures themselves.

Both specs use the same 14 walk-forward windows as P3 so the three stitched series share a calendar for the ensemble. Parameters: P4 θ ∈ {0, .0025, .005, .0075}; P5 FX variant ∈ {XS, TS, BOTH}. Gates identical in form to P3: (a) stitched Sharpe ≥ 0.5, (b) beats its no-signal benchmark (always-short; equal-weight/always-long), (c) ≥ 8/14 positive years, (d) WF permutation p < 0.05. Priors: P4 ≈ 45 %, P5 ≈ 25 %.
