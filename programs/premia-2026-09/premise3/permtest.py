"""Permutation / null-hypothesis machinery for Premise 3.

Two DIFFERENT null tests are implemented here, kept clearly separate in the
report:
  (A) TASK.md Step 4 (original spec): matched null -- flip the sign of each
      instrument's monthly signal independently, keeping sizing/costs fixed.
  (B) PREMISE_3.md Amendment A1 ("Masters' permutation framework", added
      mid-task -- see RESULTS_INSAMPLE.md integrity note): shuffle the ORDER
      of trading days (post 2007-04-11, the first date all 20 names are
      listed) and re-run the ENTIRE pipeline (vol/cov/signals/sizing/costs/
      selection) on the shuffled panel.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy import (GRID, GROSS_CAP, PER_INSTR_SCALE, PORT_VOL_TARGET,
                       _cov_tensor, ewma_vol_cov, sharpe, signals, simulate,
                       target_weights)

PERM_CUTOFF = pd.Timestamp("2007-04-11")  # first date all 20 instruments are listed


def permute_days(x: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Shuffle row order for dates >= PERM_CUTOFF (each day's full cross-section
    moves as a unit); rows before PERM_CUTOFF are untouched. Re-cumulated onto the
    original date index so month-ends/eligibility/windows are unchanged."""
    idx = x.index
    mask = idx >= PERM_CUTOFF
    block = x.loc[mask].to_numpy()
    perm = rng.permutation(len(block))
    out = x.copy()
    out.loc[mask] = block[perm]
    return out


def best_L_over_span(x, elig, me, start, end, cost_mult=1.0):
    """Amendment A1 (i): optimise L over the grid by baseline net Sharpe on a
    single span (no windows). Returns (best_L, best_sharpe, sharpe_by_L)."""
    sigma, cov_pairs = ewma_vol_cov(x)
    sh = {}
    for L in GRID:
        sig = signals(x, L)
        w, _ = target_weights(sig, sigma, cov_pairs, elig, me)
        pnl = simulate(w, x, cost_mult=cost_mult)["net"]
        seg = pnl.loc[(pnl.index >= start) & (pnl.index <= end)]
        sh[L] = sharpe(seg)
    best_L = max(sh, key=lambda L: sh[L] if not np.isnan(sh[L]) else -np.inf)
    return best_L, sh[best_L], sh


def stitched_wf_sharpe(x, elig, me, windows, cost_mult=1.0):
    """Full per-window walk-forward (re-selecting L each window by train Sharpe);
    returns the stitched TEST-period baseline net Sharpe."""
    sigma, cov_pairs = ewma_vol_cov(x)
    pnl_by_L = {}
    for L in GRID:
        sig = signals(x, L)
        w, _ = target_weights(sig, sigma, cov_pairs, elig, me)
        pnl_by_L[L] = simulate(w, x, cost_mult=cost_mult)["net"]
    frames = []
    for ts, te, trs, tre in windows:
        train_sh = {L: sharpe(pnl_by_L[L].loc[(pnl_by_L[L].index >= trs) & (pnl_by_L[L].index <= tre)])
                    for L in GRID}
        best_L = max(train_sh, key=lambda L: train_sh[L] if not np.isnan(train_sh[L]) else -np.inf)
        seg = pnl_by_L[best_L]
        frames.append(seg.loc[(seg.index >= ts) & (seg.index <= te)])
    stitched = pd.concat(frames).sort_index()
    return sharpe(stitched)


def in_sample_permutation_test(x, elig, me, start, end, n_reps, seed, cost_mult=1.0):
    """Amendment A1 (ii): permute (i) n_reps times. p = share of permuted
    best-in-sample Sharpes >= the real one."""
    real_L, real_sh, sh_by_L = best_L_over_span(x, elig, me, start, end, cost_mult)
    rng = np.random.default_rng(seed)
    null_sh = np.empty(n_reps)
    for k in range(n_reps):
        _, null_sh[k], _ = best_L_over_span(permute_days(x, rng), elig, me, start, end, cost_mult)
    p = float((null_sh >= real_sh).mean())
    return real_L, real_sh, sh_by_L, null_sh, p


def wf_permutation_test(x, elig, me, windows, n_reps, seed, cost_mult=1.0):
    """Amendment A1 (iv): permute the full walk-forward (with per-window
    re-selection) n_reps times. p = share of permuted stitched Sharpes >= real."""
    real_sh = stitched_wf_sharpe(x, elig, me, windows, cost_mult)
    rng = np.random.default_rng(seed)
    null_sh = np.empty(n_reps)
    for k in range(n_reps):
        null_sh[k] = stitched_wf_sharpe(permute_days(x, rng), elig, me, windows, cost_mult)
    p = float((null_sh >= real_sh).mean())
    return real_sh, null_sh, p


def matched_null_sign_flip(sign_stitched: pd.DataFrame, sigma: pd.DataFrame,
                            cov_pairs: pd.DataFrame, elig: pd.DataFrame,
                            me_stitched: pd.DatetimeIndex, x: pd.DataFrame,
                            stitch_start: pd.Timestamp, stitch_end: pd.Timestamp,
                            n_reps=2000, seed=13, cost_mult=1.0):
    """TASK.md Step 4 (original): independently flip the sign of each instrument's
    monthly signal (keeping the |0.40/sigma| magnitude, N_t, vol-target and cap
    machinery, and costs, identical), recompute stitched Sharpe. `sign_stitched`
    is the ACTUAL per-window-selected sign at each stitched month-end. Sharpe is
    computed on the [stitch_start, stitch_end] daily slice only (not the full
    pre-2010 history, which would otherwise dilute it with unrelated zero days).
    """
    tickers = list(sign_stitched.columns)
    elig_m = elig.reindex(me_stitched).fillna(False)
    n_elig = elig_m.sum(axis=1).replace(0, np.nan).to_numpy()
    mag = (PER_INSTR_SCALE / sigma.reindex(me_stitched)[tickers]).to_numpy()
    cov_t = _cov_tensor(cov_pairs.reindex(me_stitched), tickers)
    elig_arr = elig_m[tickers].to_numpy()
    S = sign_stitched[tickers].to_numpy()

    def _stitched_sharpe(w_arr):
        wdf = pd.DataFrame(w_arr, index=me_stitched, columns=tickers)
        pnl = simulate(wdf, x, cost_mult=cost_mult)["net"].loc[stitch_start:stitch_end]
        return sharpe(pnl)

    actual_raw = np.where(elig_arr, S * mag, 0.0) / n_elig[:, None]
    actual = _stitched_sharpe(_size_and_cap(actual_raw, cov_t))

    rng = np.random.default_rng(seed)
    null_sh = np.empty(n_reps)
    for k in range(n_reps):
        flip = rng.choice([-1.0, 1.0], size=S.shape)
        raw = np.where(elig_arr, S * flip * mag, 0.0) / n_elig[:, None]
        null_sh[k] = _stitched_sharpe(_size_and_cap(raw, cov_t))
    p = float((null_sh >= actual).mean())
    return actual, null_sh, p


def _size_and_cap(raw: np.ndarray, cov_t: np.ndarray) -> np.ndarray:
    var_p = np.einsum("ti,tij,tj->t", raw, cov_t, raw)
    lam = PORT_VOL_TARGET / np.sqrt(var_p)
    w = raw * lam[:, None]
    gross = np.abs(w).sum(axis=1)
    scale = np.where(gross > GROSS_CAP, GROSS_CAP / gross, 1.0)
    return w * scale[:, None]
