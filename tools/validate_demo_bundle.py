#!/usr/bin/env python3
"""Validate an HHG-XR Lab demo bundle directory.

Checks:

1. manifest.json and data_small.json both load as JSON.
2. manifest.schema == 'hhgxr-demo-bundle-v0'.
3. Required keys are present (physics_provenance, units, dimensions,
   available_modules, missing_modules, files).
4. No public manifest value contains a private absolute path
   (Windows drive, UNC, or /home /root /mnt absolute path).
5. data_small arrays have consistent lengths inside each module.
6. field.source is one of the allowed labels.
7. No raw .dat/.tb/.hr/.h5/.npy/.npz files larger than --max-mb live
   inside the bundle directory.
8. Bundle does not exceed --max-total-mb total.
9. manifest references files via 'files' that actually exist.
10. missing_modules is listed and is a non-hidden array.

Usage:
    python tools/validate_demo_bundle.py --bundle data/samples/demo_bundle_minimal
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "hhgxr-demo-bundle-v0"

WINDOWS_DRIVE = re.compile(r"[A-Za-z]:[\\/]")
UNC_PATH = re.compile(r"\\\\[^\\]+\\[^\\]+")
UNIX_ABS = re.compile(r"(^|[^A-Za-z0-9_])(/(?:home|root|mnt|media|Users|data|scratch|work|share|var|opt)/[^\"\s]+)")

ALLOWED_FIELD_SOURCES = {
    "raw_solver_output",
    "reconstructed_from_input_nml_not_raw_output",
    "unavailable",
    "solver_native",                              # legacy alias for raw_solver_output
    "reconstructed_from_input_nml_verified",      # legacy, pre-audit
    "reconstructed_from_input_nml_unverified",    # legacy, pre-audit
}

LARGE_EXTS = {".dat", ".tb", ".hr", ".h5", ".hdf5", ".npy", ".npz"}


class Issues:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


# ----------------------------------------------------------------------
# Path leak detection
# ----------------------------------------------------------------------

def walk_strings(node: Any, path: str = "$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def find_private_paths(node: Any) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for jp, s in walk_strings(node):
        if WINDOWS_DRIVE.search(s) or UNC_PATH.search(s) or UNIX_ABS.search(s):
            hits.append((jp, s))
    return hits


# ----------------------------------------------------------------------
# Module-level checks
# ----------------------------------------------------------------------

def check_manifest(manifest: dict[str, Any], issues: Issues) -> None:
    if manifest.get("schema") != SCHEMA:
        issues.err(f"manifest.schema != {SCHEMA!r} (got {manifest.get('schema')!r})")

    for key in ("dataset_name", "physics_provenance", "units", "dimensions",
                "available_modules", "missing_modules", "files"):
        if key not in manifest:
            issues.err(f"manifest missing required key: {key}")

    prov = manifest.get("physics_provenance") or {}
    src_cls = prov.get("source_class")
    if src_cls not in {"Data-driven", "Model-based", "Literature-reproduced", "Conceptual-only"}:
        issues.err(f"physics_provenance.source_class invalid: {src_cls!r}")

    missing = manifest.get("missing_modules")
    if not isinstance(missing, list):
        issues.err("missing_modules must be an explicit list (use [] if truly nothing)")


def check_time_series(ts: dict[str, Any], issues: Issues) -> None:
    if not ts:
        return
    t = ts.get("time_fs")
    if not isinstance(t, list):
        issues.err("time_series.time_fs missing or not a list")
        return
    n = len(t)
    for k, v in ts.items():
        if k == "time_fs":
            continue
        if isinstance(v, list) and len(v) != n:
            issues.err(f"time_series.{k} length {len(v)} != time_fs length {n}")


def check_spectrum(sp: dict[str, Any], issues: Issues) -> None:
    if not sp:
        return
    lens = {k: len(v) for k, v in sp.items() if isinstance(v, list)}
    if not lens:
        return
    n = next(iter(lens.values()))
    for k, ln in lens.items():
        if ln != n:
            issues.err(f"spectrum.{k} length {ln} != reference length {n}")


def check_band_path(bp: dict[str, Any], issues: Issues) -> None:
    if not bp:
        return
    k = bp.get("k_path")
    e = bp.get("energy_eV")
    if not isinstance(k, list) or not isinstance(e, list):
        issues.err("band_path requires k_path and energy_eV lists")
        return
    if len(k) != len(e):
        issues.err(f"band_path.k_path length {len(k)} != energy_eV length {len(e)}")
        return
    if e and isinstance(e[0], list):
        n_bands_row = len(e[0])
        for i, row in enumerate(e):
            if not isinstance(row, list) or len(row) != n_bands_row:
                issues.err(f"band_path.energy_eV[{i}] has length {len(row) if hasattr(row, '__len__') else 'scalar'}, expected {n_bands_row}")
                return
        n_bands_meta = bp.get("n_bands")
        if n_bands_meta is not None and n_bands_meta != n_bands_row:
            issues.err(f"band_path.n_bands={n_bands_meta} but energy_eV row width is {n_bands_row}")
        near = bp.get("near_gap_band_indices") or []
        if not isinstance(near, list) or any(not isinstance(i, int) or not 0 <= i < n_bands_row for i in near):
            issues.err("band_path.near_gap_band_indices contains invalid entries")


def check_field(field: dict[str, Any], issues: Issues) -> None:
    if not field:
        return
    src = field.get("source")
    if src not in ALLOWED_FIELD_SOURCES:
        issues.err(f"field.source invalid: {src!r}")
    if src and src != "unavailable":
        t = field.get("time_fs") or []
        for k in ("Ex", "Ey", "Ax", "Ay"):
            v = field.get(k) or []
            if isinstance(v, list) and v and len(v) != len(t):
                issues.err(f"field.{k} length {len(v)} != time_fs length {len(t)}")
        if src.startswith("reconstructed_from_input_nml") and src != "reconstructed_from_input_nml_not_raw_output":
            issues.warn(
                f"field.source uses legacy label {src!r}; "
                "regenerate via convert_sbe_run.py to get "
                "'reconstructed_from_input_nml_not_raw_output' with cross-check provenance"
            )


def _shape2d(a: Any) -> tuple[int, int] | None:
    if not isinstance(a, list) or not a or not isinstance(a[0], list):
        return None
    return len(a), len(a[0])


def check_grid_block(name: str, block: dict[str, Any], issues: Issues) -> None:
    """Common consistency for blocks carrying kx_grid/ky_grid 2D arrays."""
    if not block:
        return
    ref = _shape2d(block.get("kx_grid"))
    if ref is None:
        return
    if _shape2d(block.get("ky_grid")) != ref:
        issues.err(f"{name}.ky_grid shape != kx_grid shape {ref}")
    for key in ("energies_eV", "berry_curvature_au", "trace_quantum_metric_au"):
        stack = block.get(key)
        if isinstance(stack, list) and stack and isinstance(stack[0], list) \
                and stack and isinstance(stack[0][0], list):
            for bi, grid in enumerate(stack):
                if _shape2d(grid) != ref:
                    issues.err(f"{name}.{key}[{bi}] shape != kx_grid shape {ref}")
    if isinstance(block.get("valley_id"), list) and _shape2d(block["valley_id"]) not in (None, ref):
        issues.err(f"{name}.valley_id shape != kx_grid shape {ref}")


def check_k_snapshots(name: str, block: dict[str, Any],
                      value_keys: tuple[str, ...], issues: Issues) -> None:
    if not block:
        return
    ref = _shape2d(block.get("kx_grid"))
    snaps = block.get("snapshots")
    if not isinstance(snaps, list):
        issues.err(f"{name}.snapshots must be a list")
        return
    for i, s in enumerate(snaps):
        if "time_fs" not in s:
            issues.err(f"{name}.snapshots[{i}] missing time_fs")
        for key in value_keys:
            if ref is not None and _shape2d(s.get(key)) != ref:
                issues.err(f"{name}.snapshots[{i}].{key} shape != kx_grid shape {ref}")


def check_data_small(ds: dict[str, Any], issues: Issues) -> None:
    check_time_series(ds.get("time_series") or {}, issues)
    check_spectrum(ds.get("spectrum") or {}, issues)
    check_spectrum(ds.get("spectrum_spin") or {}, issues)
    check_band_path(ds.get("band_path") or {}, issues)
    check_field(ds.get("field") or {}, issues)
    check_grid_block("band_grid_preview", ds.get("band_grid_preview") or {}, issues)
    check_grid_block("quantum_geometry_preview", ds.get("quantum_geometry_preview") or {}, issues)
    check_k_snapshots("occupation_preview", ds.get("occupation_preview") or {},
                      ("n_val", "n_cond", "delta_n_cond"), issues)
    check_k_snapshots("coherence_preview", ds.get("coherence_preview") or {},
                      ("coherence_norm",), issues)


def check_files_section(bundle: Path, manifest: dict[str, Any], issues: Issues) -> None:
    files = manifest.get("files") or {}
    if not isinstance(files, dict):
        issues.err("manifest.files must be a dict")
        return
    for key, rel in files.items():
        target = bundle / rel
        if not target.exists():
            issues.err(f"manifest.files.{key} -> {rel} does not exist in bundle")


def check_no_large_blobs(bundle: Path, max_mb: int, total_max_mb: int, issues: Issues) -> None:
    total = 0
    for p in bundle.rglob("*"):
        if not p.is_file():
            continue
        size = p.stat().st_size
        total += size
        if p.suffix.lower() in LARGE_EXTS and size > max_mb * 1024 * 1024:
            issues.err(f"raw scientific blob too large for bundle: {p.name} ({size/1e6:.1f} MB)")
        if p.suffix.lower() in LARGE_EXTS and size > 1 * 1024 * 1024:
            issues.warn(f"large binary in bundle: {p.name} ({size/1e6:.1f} MB) -- consider Git LFS")
    if total > total_max_mb * 1024 * 1024:
        issues.err(f"bundle total size {total/1e6:.1f} MB exceeds {total_max_mb} MB")


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------

def validate(bundle: Path, max_mb: int, total_max_mb: int) -> Issues:
    issues = Issues()
    manifest_path = bundle / "manifest.json"
    data_small_path = bundle / "data_small.json"

    if not manifest_path.exists():
        issues.err(f"missing {manifest_path}")
        return issues
    if not data_small_path.exists():
        issues.err(f"missing {data_small_path}")
        return issues

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        issues.err(f"manifest.json invalid JSON: {e}")
        return issues
    try:
        data_small = json.loads(data_small_path.read_text())
    except json.JSONDecodeError as e:
        issues.err(f"data_small.json invalid JSON: {e}")
        return issues

    check_manifest(manifest, issues)
    check_data_small(data_small, issues)
    check_files_section(bundle, manifest, issues)
    check_no_large_blobs(bundle, max_mb, total_max_mb, issues)

    for jp, s in find_private_paths(manifest):
        issues.err(f"private path leak in manifest at {jp}: {s!r}")
    for jp, s in find_private_paths(data_small):
        issues.err(f"private path leak in data_small at {jp}: {s!r}")

    return issues


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bundle", required=True, type=Path)
    p.add_argument("--max-mb", type=int, default=10,
                   help="Per-file size limit for raw scientific blobs.")
    p.add_argument("--max-total-mb", type=int, default=25,
                   help="Total bundle size limit.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    issues = validate(args.bundle, args.max_mb, args.max_total_mb)
    for w in issues.warnings:
        print(f"[warn] {w}")
    for e in issues.errors:
        print(f"[FAIL] {e}", file=sys.stderr)
    if issues.ok:
        print(f"[ok] bundle {args.bundle} passes all checks")
        return 0
    print(f"[FAIL] bundle {args.bundle} has {len(issues.errors)} error(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
