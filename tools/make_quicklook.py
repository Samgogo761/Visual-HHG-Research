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

    nested = isinstance(e[0], list)
    e0 = e[0] if nested else [e[0]]
    n_bands_total = len(e0)

    near_gap = bp.get("near_gap_band_indices") or []
    if near_gap:
        indices = [b for b in near_gap if 0 <= b < n_bands_total]
        suffix = f"  near-gap [{len(indices)}/{n_bands_total}]"
    else:
        indices = list(range(min(n_bands_total, 30)))
        suffix = "" if n_bands_total <= 30 else f"  first 30/{n_bands_total}"

    if nested:
        for b in indices:
            ax.plot(k, [row[b] for row in e], lw=0.8)
    else:
        ax.plot(k, e, lw=0.8)

    fermi = bp.get("e_fermi_eV")
    if fermi is not None:
        ax.axhline(fermi, color="#888888", lw=0.6, linestyle="--", alpha=0.6,
                   label=f"E_F = {fermi:+.3f} eV")
        ax.legend(loc="lower right", fontsize=7, frameon=False)

    ax.set_title(f"Band path  (eV){suffix}")
    ax.set_xlabel("k path")
    ax.set_ylabel("E (eV)")


def _plot_field(ax, field: dict[str, Any]) -> None:
    t = field.get("time_fs") or []
    ex = field.get("Ex") or []
    ey = field.get("Ey") or []
    ax_arr = field.get("Ax") or []
    e_main = ex if ex else ey
    src = field.get("source", "unavailable")
    if src == "unavailable" or not t or not e_main:
        _placeholder(ax, "E(t) / A(t)", f"unavailable ({src})")
        return
    ax.plot(t, e_main, lw=0.7, color="#cc6600", label="E (a.u.)")
    if ax_arr and len(ax_arr) == len(t):
        ax2 = ax.twinx()
        ax2.plot(t, ax_arr, lw=0.7, color="#005599", linestyle="--", label="A (a.u.)")
        ax2.set_ylabel("A (a.u.)", color="#005599")
        ax2.tick_params(axis="y", colors="#005599")
    ax.set_title(f"E(t) / A(t)  [{src}]", fontsize=8)
    ax.set_xlabel("time (fs)")
    ax.set_ylabel("E (a.u.)", color="#cc6600")
    if src == "raw_solver_output":
        badge = ("raw solver", "#006600", "#f0fff0")
    elif src == "reconstructed_from_input_nml_not_raw_output":
        badge = ("reconstructed (not raw)", "#cc6600", "#fff8f0")
    elif src.endswith("_unverified"):
        badge = ("unverified", "#cc0000", "#fff0f0")
    else:
        badge = (src, "#444444", "#f4f4f4")
    ax.text(0.02, 0.95, badge[0], transform=ax.transAxes,
            color=badge[1], fontsize=7, ha="left", va="top",
            bbox=dict(boxstyle="round", fc=badge[2], ec=badge[1], lw=0.5))


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
