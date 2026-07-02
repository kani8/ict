"""Render an annotation bundle into the self-contained HTML viewer."""

from __future__ import annotations

import json
from pathlib import Path

_TEMPLATE = Path(__file__).parent / "template.html"


def render_html(bundle: dict, out_path: str | Path) -> Path:
    payload = json.dumps(bundle, separators=(",", ":")).replace("</", "<\\/")
    html = _TEMPLATE.read_text()
    html = html.replace("__TITLE__", bundle["meta"]["title"])
    html = html.replace("__DATA__", payload)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out
