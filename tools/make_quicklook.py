#!/usr/bin/env python3
"""Render a 4-panel quicklook PNG for an HHG-XR Lab demo bundle.

Panels:
    1. Band path           (data_small.band_path)
    2. Driving field E(t)  (data_small.field, with provenance caveat)
    3. Current J(t)        (data_small.time_series)
    4. HHG spectrum        (data_small.spectrum)

Missing panels render a placeholder text block instead of failing.

Usage:
    python tools/make_quicklook.py --bundle data/samples/demo_bundle_minimal
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _try_import_mpl():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception as exc:
        raise RuntimeError(
            "matplotlib is required for make_quicklook.py "
            "(install with `pip install matplotlib`)"
        ) from exc


def _placeholder(ax, title: str, msg: str) -> None:
    ax.set_title(title)
    ax.text(0.5, 0.5, msg, ha="center", va="center", transform=ax.transAxes,
            fontsize=10, color="#888888")
    ax.set_xticks([])
    ax.set_yticks([])


def _plot_band_path(ax, bp: dict[str, Any]) -> None:
    k = bp.get("k_path") or []
    e = bp.get("energy_eV") or []
    if not k or not e:
        _placeholder(ax, "Band path", "band_path missing")
        return
    e0 = e[0] if isinstance(e[0], list) else [e[0]]
    n_bands = len(e0)
    for b in range(min(n_bands, 30)):
        ax.plot(k, [row[b] for row in e], lw=0.8)
    ax.set_title("Band path  (eV)")
    ax.set_xlabel("k path")
    ax.set_ylabel("E (eV)")


def _plot_field(ax, field: dict[str, Any]) -> None:
    t = field.get("time_fs") or []
    ey = field.get("Ey") or []
    src = field.get("source", "unavailable")
    if src == "unavailable" or not t or not ey:
        _placeholder(ax, "E(t)", f"unavailable ({src})")
        return
    ax.plot(t, ey, lw=0.7, color="#cc6600")
    ax.set_title(f"E(t)  [{src}]", fontsize=9)
    ax.set_xlabel("time (fs)")
    ax.set_ylabel("E (a.u.)")
    if src.endswith("_unverified"):
        ax.text(0.02, 0.95, "unverified", transform=ax.transAxes,
                color="#cc0000", fontsize=8, ha="left", va="top",
                bbox=dict(boxstyle="round", fc="#fff0f0", ec="#cc0000", lw=0.5))


def _plot_current(ax, ts: dict[str, Any]) -> None:
    t = ts.get("time_fs") or []
    jx = ts.get("Jx") or []
    jy = ts.get("Jy") or []
    if not t or (not jx and not jy):
        _placeholder(ax, "J(t)", "time_series missing")
        return
    if jx:
        ax.plot(t, jx, lw=0.6, label="Jx", color="#0077cc")
    if jy:
        ax.plot(t, jy, lw=0.6, label="Jy", color="#cc0077")
    ax.set_title("J(t)  (a.u.)")
    ax.set_xlabel("time (fs)")
    ax.set_ylabel("J")
    ax.legend(loc="upper right", fontsize=8)


def _plot_spectrum(ax, sp: dict[str, Any]) -> None:
    order = sp.get("harmonic_order") or []
    tot = sp.get("HHG_total") or []
    if not order or not tot:
        _placeholder(ax, "HHG spectrum", "spectrum missing")
        return
    pos = [max(v, 1e-30) for v in tot]
    ax.semilogy(order, pos, lw=0.7, color="#333333")
    ax.set_title("HHG spectrum  |J(omega)|^2")
    ax.set_xlabel("harmonic order")
    ax.set_ylabel("|J(omega)|^2")


def render_quicklook(data_small: dict[str, Any], out_png: Path) -> Path:
    plt = _try_import_mpl()
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    _plot_band_path(axes[0, 0], data_small.get("band_path") or {})
    _plot_field(axes[0, 1], data_small.get("field") or {})
    _plot_current(axes[1, 0], data_small.get("time_series") or {})
    _plot_spectrum(axes[1, 1], data_small.get("spectrum") or {})
    fig.suptitle("HHG-XR Lab demo bundle quicklook", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    return out_png


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bundle", required=True, type=Path,
                   help="Path to demo bundle directory containing data_small.json.")
    p.add_argument("--out", type=Path, default=None,
                   help="Output PNG. Defaults to <bundle>/quicklook_summary.png.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data_small_path = args.bundle / "data_small.json"
    if not data_small_path.exists():
        print(f"error: missing {data_small_path}")
        return 2
    data_small = json.loads(data_small_path.read_text())
    out = args.out or (args.bundle / "quicklook_summary.png")
    render_quicklook(data_small, out)
    print(f"[ok] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
