"""Tests for the strategy-replay visualization bundle and exporter."""

import json

from ict_backtest.core import BULL
from ict_backtest.data import synthetic_candles
from ict_backtest.engine import Backtester, CostModel
from ict_backtest.strategy import SMCConfig, SMCStrategy
from ict_backtest.viz import build_bundle, build_timeline, render_html


def _cfg() -> SMCConfig:
    return SMCConfig(use_killzones=True, avoid_news=True, require_ote=False,
                     require_discount=False, min_rr=1.0, htf_multiplier=8,
                     bias_mode="narrative", narrative_min_conviction=0.25,
                     poi_priority=("ifvg", "fvg", "ob"), entry_confirmation=True)


def test_bundle_schema_and_visibility_honesty():
    candles = synthetic_candles(n=3000, seed=21, base_vol=0.005)
    bundle = build_bundle(candles, _cfg(), multipliers=(1, 4, 16))
    assert bundle["meta"]["bars"] == 3000
    assert [t["label"] for t in bundle["tfs"]] == ["15m", "1h", "4h"]
    for layer in bundle["tfs"]:
        n = len(layer["ts"])
        assert len(layer["o"]) == len(layer["c"]) == len(layer["kz"]) == n
        for g in layer["fvg"]:
            i, lo, hi, _, visible = g[0], g[1], g[2], g[3], g[4]
            assert visible == i + 2          # knowable only at candle i+2
            assert lo < hi
        for o in layer["ob"]:
            assert o[4] >= o[0]              # created at/after the OB candle
        for p in layer["pool"]:
            assert p[3] >= p[2]              # confirmed at/after first swing
            assert p[4] == -1 or p[4] > p[3]  # taken strictly after visible
        for e in layer["ev"]:
            assert e[2] in (0, 1)


def test_timeline_matches_real_backtest():
    candles = synthetic_candles(n=6000, seed=13, base_vol=0.004)
    cfg = _cfg()
    tl = build_timeline(candles, cfg)
    result = Backtester(cost=CostModel(), initial_equity=100_000).run(
        candles, SMCStrategy(candles, cfg))
    assert len(tl["trades"]) == len(result.trades)
    assert [t[0] for t in tl["trades"]] == [t.entry_index for t in result.trades]
    assert len(tl["bias"]) == len(candles) == len(tl["score"])
    assert set(tl["factors"]) == {"struct_mtf", "struct_htf", "struct_wk", "dol", "ipda"}
    # status change-points strictly ordered and non-empty
    idxs = [i for i, _ in tl["status"]]
    assert idxs == sorted(idxs) and len(idxs) > 1
    assert all(isinstance(s, str) and s for _, s in tl["status"])


def test_timeline_structure_mode_has_no_factor_vote():
    candles = synthetic_candles(n=3000, seed=5, base_vol=0.004)
    tl = build_timeline(candles, SMCConfig(use_killzones=False, htf_multiplier=8))
    assert tl["factors"] == {}
    assert tl["score"] == [float(b) for b in tl["bias"]]


def test_render_html_self_contained(tmp_path):
    candles = synthetic_candles(n=1500, seed=2, base_vol=0.005)
    bundle = build_bundle(candles, _cfg(), multipliers=(1, 4))
    out = render_html(bundle, tmp_path / "replay.html")
    html = out.read_text()
    assert "__DATA__" not in html and "__TITLE__" not in html
    assert "ICT Strategy Replay" in html
    assert "http://" not in html and "https://" not in html  # CSP-safe: no external hosts
    payload = html.split('id="bundle">')[1].split("</script>")[0]
    decoded = json.loads(payload.replace("<\\/", "</"))
    assert decoded["meta"]["bars"] == 1500


def test_cli_viz_smoke(tmp_path, capsys):
    from ict_backtest.cli import main
    from ict_backtest.data.fetch import save_candles

    data = tmp_path / "synth.parquet"
    save_candles(synthetic_candles(n=2000, seed=3, base_vol=0.005), data)
    rc = main(["viz", "--data", str(data), "--out", str(tmp_path / "v.html"),
               "--timeframes", "1,4", "--max-bars", "1500"])
    assert rc == 0
    assert (tmp_path / "v.html").stat().st_size > 50_000
    assert "wrote" in capsys.readouterr().out


def test_trade_markers_present_when_strategy_trades():
    candles = synthetic_candles(n=8000, seed=13, base_vol=0.004)
    cfg = SMCConfig(use_killzones=False, require_ote=False, require_discount=False,
                    htf_multiplier=8, min_rr=1.0)
    bundle = build_bundle(candles, cfg, multipliers=(1,))
    trades = bundle["timeline"]["trades"]
    assert len(trades) >= 3
    for t in trades:
        assert t[0] <= t[1]                   # same-bar stop-outs are legitimate
        assert t[2] in (BULL, -BULL)
        assert t[9] in ("sl", "tp", "eod", "strategy")
