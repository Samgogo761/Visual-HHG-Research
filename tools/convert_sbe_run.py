#!/usr/bin/env python3
"""Convert a Wannier-SBE run directory into a sanitized HHG-XR Lab demo bundle.

Reads (best effort, missing files are tolerated):
    <run-dir>/Jt.dat
    <run-dir>/HHG.dat
    <run-dir>/bands.dat
    <run-dir>/Jt_decomposed.dat
    <run-dir>/Jt_valley.dat
    <run-dir>/input.nml
    <run-dir>/run.log
    <band-path>             (optional, e.g. wannier/CrI3_band.dat)

Writes:
    <out-dir>/manifest.json
    <out-dir>/data_small.json
    <out-dir>/quicklook_summary.png      (if matplotlib is available)
    <out-dir>/data_arrays.npz            (optional, --emit-npz)

Private absolute paths are never written into manifest.json. The
manifest's "source_paths" section uses placeholders like
<LOCAL_SBE_RUN_DIR>/Jt.dat. Run tools/sanitize_manifest.py against an
existing manifest if you need to scrub one after the fact.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA = "hhgxr-demo-bundle-v0"

RUN_DIR_PLACEHOLDER = "<LOCAL_SBE_RUN_DIR>"
WANNIER_PLACEHOLDER = "<LOCAL_WANNIER_DIR>"


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run-dir", required=True, type=Path,
                   help="SBE run directory containing Jt.dat, HHG.dat, bands.dat, etc.")
    p.add_argument("--band-path", type=Path, default=None,
                   help="Optional Wannier band-path .dat file (e.g. CrI3_band.dat).")
    p.add_argument("--out-dir", required=True, type=Path,
                   help="Output directory for the demo bundle.")
    p.add_argument("--dataset-name", default=None,
                   help="Override dataset_name written into the manifest.")
    p.add_argument("--max-points-current", type=int, default=1200,
                   help="Downsample target for J(t) arrays in data_small.json.")
    p.add_argument("--max-points-spectrum", type=int, default=800,
                   help="Downsample target for HHG spectrum in data_small.json.")
    p.add_argument("--selected-bands", default="80:90",
                   help="Slice (a:b) of band indices to include in band_grid_preview.")
    p.add_argument("--max-grid", type=int, default=40,
                   help="Maximum kx/ky grid points kept in band_grid_preview.")
    p.add_argument("--emit-npz", action="store_true",
                   help="Also write data_arrays.npz at original resolution. Off by default.")
    p.add_argument("--gauge-method", default="lg_cov")
    p.add_argument("--material", default="bilayer CrI3 AFM")
    p.add_argument("--model", default="Wannier-SBE")
    p.add_argument("--source-class", default="Data-driven",
                   choices=("Data-driven", "Model-based", "Literature-reproduced", "Conceptual-only"),
                   help="Provenance label for physics_provenance.source_class.")
    p.add_argument("--confidence", default=None,
                   help="Free-text confidence statement written into physics_provenance.confidence.")
    return p.parse_args(argv)


# ----------------------------------------------------------------------
# Path sanitization
# ----------------------------------------------------------------------

def sanitize_run_path(run_dir: Path, child: Path) -> str:
    """Return '<LOCAL_SBE_RUN_DIR>/relative/path' for a file under run_dir."""
    try:
        rel = child.resolve().relative_to(run_dir.resolve())
        return f"{RUN_DIR_PLACEHOLDER}/{rel.as_posix()}"
    except ValueError:
        return f"{RUN_DIR_PLACEHOLDER}/{child.name}"


def sanitize_band_path(band_path: Path | None) -> str | None:
    if band_path is None:
        return None
    return f"{WANNIER_PLACEHOLDER}/{band_path.name}"


# ----------------------------------------------------------------------
# .dat readers
# ----------------------------------------------------------------------

def _read_columns(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    try:
        return np.loadtxt(path, comments=["#", "!"])
    except Exception as exc:
        print(f"[warn] failed to read {path.name}: {exc}", file=sys.stderr)
        return None


def downsample(a: np.ndarray, n_target: int) -> np.ndarray:
    if a.size == 0 or n_target <= 0 or a.shape[0] <= n_target:
        return a
    stride = max(1, math.ceil(a.shape[0] / n_target))
    return a[::stride]


# ----------------------------------------------------------------------
# input.nml parsing
# ----------------------------------------------------------------------

_NML_PAIR = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^!,\n]+?)\s*(?:,|$|!)", re.MULTILINE)


def parse_input_nml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    out: dict[str, Any] = {}
    text = path.read_text(errors="ignore")
    for key, val in _NML_PAIR.findall(text):
        val = val.strip().strip(",")
        if val.lower() in {".true.", "t"}:
            out[key] = True
            continue
        if val.lower() in {".false.", "f"}:
            out[key] = False
            continue
        try:
            if any(c in val for c in ".eEdD") and "/" not in val:
                out[key] = float(val.replace("D", "E").replace("d", "e"))
            else:
                out[key] = int(val)
        except ValueError:
            out[key] = val.strip().strip("'").strip('"')
    return out


# ----------------------------------------------------------------------
# bands.dat reader
# ----------------------------------------------------------------------

@dataclass
class BandGrid:
    kx: np.ndarray
    ky: np.ndarray
    energies: np.ndarray  # shape (n_bands, nkx, nky)
    nkx: int
    nky: int
    n_bands: int


def read_bands_grid(path: Path) -> BandGrid | None:
    """Tolerant reader.

    Expected layout: rows of (kx, ky, e1, e2, ..., e_nbands).
    Returns None if shape cannot be inferred.
    """
    raw = _read_columns(path)
    if raw is None or raw.ndim != 2 or raw.shape[1] < 3:
        return None
    kx_col = raw[:, 0]
    ky_col = raw[:, 1]
    e_cols = raw[:, 2:]
    n_bands = e_cols.shape[1]

    kx_unique = np.unique(kx_col)
    ky_unique = np.unique(ky_col)
    nkx, nky = kx_unique.size, ky_unique.size

    if nkx * nky != raw.shape[0]:
        print(f"[warn] bands.dat rows {raw.shape[0]} != nkx*nky {nkx*nky}; "
              f"using best-effort grid (truncating)", file=sys.stderr)

    energies = np.full((n_bands, nkx, nky), np.nan, dtype=np.float32)
    kx_idx = {v: i for i, v in enumerate(kx_unique)}
    ky_idx = {v: i for i, v in enumerate(ky_unique)}
    for r in range(raw.shape[0]):
        ix = kx_idx.get(kx_col[r])
        iy = ky_idx.get(ky_col[r])
        if ix is None or iy is None:
            continue
        energies[:, ix, iy] = e_cols[r]

    return BandGrid(kx_unique.astype(np.float32),
                    ky_unique.astype(np.float32),
                    energies, nkx, nky, n_bands)


def parse_band_slice(spec: str, n_bands: int) -> list[int]:
    if not spec:
        return list(range(n_bands))
    if ":" in spec:
        a, b = spec.split(":", 1)
        lo = int(a) if a else 0
        hi = int(b) if b else n_bands
    else:
        lo = int(spec)
        hi = lo + 1
    lo = max(0, lo)
    hi = min(n_bands, hi)
    return list(range(lo, hi))


# ----------------------------------------------------------------------
# Field: raw solver output (Et.dat / At.dat) and reconstruction
# ----------------------------------------------------------------------

C_NM_PER_FS = 299.792458


def read_field_dat(et_path: Path | None, at_path: Path | None) -> dict | None:
    """Read raw solver E(t) and/or A(t) files.

    Expected column layout for either file:
        # it  time_fs  Ex_au  Ey_au  Ax_au  Ay_au

    Et.dat alone is sufficient (Ax/Ay can be derived). At.dat alone is
    sufficient (Ex/Ey can be derived). If both are present and disagree,
    the values from Et.dat win for Ex/Ey and At.dat win for Ax/Ay.
    """
    et = _read_columns(et_path) if et_path and et_path.exists() else None
    at = _read_columns(at_path) if at_path and at_path.exists() else None
    if et is None and at is None:
        return None

    base = et if et is not None else at
    if base.ndim != 2 or base.shape[1] < 4:
        return None
    time_fs = base[:, 1]

    def pick(arr: np.ndarray, col: int, fallback: np.ndarray | None = None) -> np.ndarray:
        if arr is not None and arr.shape[1] > col:
            return arr[:, col]
        return fallback if fallback is not None else np.zeros_like(time_fs)

    ex = pick(et, 2, pick(at, 2))
    ey = pick(et, 3, pick(at, 3))
    ax = pick(at, 4, pick(et, 4, _integrate_neg(ex, time_fs)))
    ay = pick(at, 5, pick(et, 5, _integrate_neg(ey, time_fs)))

    return {
        "time_fs": time_fs,
        "Ex": ex, "Ey": ey,
        "Ax": ax, "Ay": ay,
        "et_present": et is not None,
        "at_present": at is not None,
    }


def _integrate_neg(field: np.ndarray, time_fs: np.ndarray) -> np.ndarray:
    """A(t) = -integral E dt' from t[0] to t, using trapezoidal cumulation.

    A(t[0]) is fixed to zero. Units: same as field (a.u.) since the
    integration kernel is time in fs but we keep both fields in a.u.
    consistently with the solver convention.
    """
    if field.size < 2:
        return np.zeros_like(field)
    dt = np.diff(time_fs)
    mids = 0.5 * (field[:-1] + field[1:])
    a = np.concatenate(([0.0], -np.cumsum(mids * dt)))
    return a


def parse_run_log(path: Path) -> dict[str, Any]:
    """Best-effort scrape of run.log for fields the laser cross-check uses."""
    if not path.exists():
        return {}
    text = path.read_text(errors="ignore")
    out: dict[str, Any] = {}
    patterns = {
        "omega0_au":  re.compile(r"omega0[_\s]*=?\s*([+-]?\d+\.?\d*(?:[eEdD][+-]?\d+)?)"),
        "T_total_fs": re.compile(r"T[_\s]*total[_\s]*=?\s*([+-]?\d+\.?\d*(?:[eEdD][+-]?\d+)?)"),
        "nt":         re.compile(r"\bnt\s*=?\s*(\d+)\b"),
    }
    for key, pat in patterns.items():
        m = pat.search(text)
        if not m:
            continue
        val = m.group(1).replace("D", "E").replace("d", "e")
        try:
            out[key] = int(val) if key == "nt" else float(val)
        except ValueError:
            pass
    return out


AU_TIME_FS = 0.024188843  # 1 atomic unit of time in fs


def reconstruct_field(time_fs: np.ndarray,
                      nml: dict[str, Any],
                      run_log: dict[str, Any],
                      nt_full: int | None = None) -> dict[str, Any]:
    """Cos-squared envelope reconstruction from input.nml plus run.log cross-check.

    Returns a dict with Ex, Ey, Ax, Ay (numpy arrays) and a small
    provenance block describing the reconstruction source and the
    cross-check against run.log. The label is
    'reconstructed_from_input_nml_not_raw_output': the curves are now
    audited and visualization-ready, but they are still not the solver's
    native E(t) / A(t) output.

    The cross-check converts the reconstructed omega from rad/fs to
    atomic units before comparing against run_log['omega0_au'], and
    compares nt against the pre-downsampling row count (nt_full) so a
    downsampled t_axis does not produce a spurious mismatch.
    """
    if time_fs.size == 0:
        return {"source": "unavailable"}

    wavelength_nm = float(nml.get("lambda_nm", nml.get("wavelength_nm", 3200.0)))
    n_cycles = float(nml.get("n_cycles", nml.get("ncyc", 4.0)))
    e0 = float(nml.get("E0_au", nml.get("amp", 0.005)))

    period_fs = wavelength_nm / C_NM_PER_FS
    omega_rad_per_fs = 2.0 * math.pi / period_fs
    omega_au = omega_rad_per_fs * AU_TIME_FS
    duration = n_cycles * period_fs

    t0 = float(time_fs[0])
    center = t0 + duration / 2.0
    envelope = np.where(
        np.abs(time_fs - center) < duration / 2.0,
        np.cos(math.pi * (time_fs - center) / duration) ** 2,
        0.0,
    )
    ex = e0 * envelope * np.cos(omega_rad_per_fs * (time_fs - center))
    ey = np.zeros_like(ex)
    ax = _integrate_neg(ex, time_fs)
    ay = np.zeros_like(ax)

    cross = {}
    if "omega0_au" in run_log:
        cross["omega0_au"] = "match" if math.isclose(run_log["omega0_au"], omega_au, rel_tol=5e-2) else "mismatch"
    if "T_total_fs" in run_log:
        cross["T_total_fs"] = "match" if math.isclose(run_log["T_total_fs"], duration, rel_tol=5e-2) else "mismatch"
    if "nt" in run_log:
        nt_compare = nt_full if nt_full is not None else time_fs.size
        cross["nt"] = "match" if run_log["nt"] == nt_compare else "mismatch"

    return {
        "time_fs": time_fs,
        "Ex": ex, "Ey": ey, "Ax": ax, "Ay": ay,
        "source": "reconstructed_from_input_nml_not_raw_output",
        "reconstructed_from": ["input.nml", "mod_laser.f90", "mod_params.f90"],
        "cross_checked_with": ["run.log"] if run_log else [],
        "cross_check": cross,
        "note": (
            "Reconstructed from solver inputs and cross-checked against run.log; "
            "not raw solver output. Visualization-ready."
        ),
    }


# ----------------------------------------------------------------------
# Bundle assembly
# ----------------------------------------------------------------------

def to_list(a: np.ndarray | None) -> list:
    return [] if a is None else np.asarray(a).astype(float).tolist()


def build_time_series(jt: np.ndarray | None,
                      jt_dec: np.ndarray | None,
                      jt_val: np.ndarray | None,
                      n_max: int) -> tuple[dict, np.ndarray | None]:
    if jt is None:
        return {}, None
    jt_ds = downsample(jt, n_max)
    out: dict[str, list] = {
        "time_fs": jt_ds[:, 0].tolist() if jt_ds.shape[1] >= 1 else [],
        "Jx":      jt_ds[:, 1].tolist() if jt_ds.shape[1] >= 2 else [],
        "Jy":      jt_ds[:, 2].tolist() if jt_ds.shape[1] >= 3 else [],
    }
    if jt_dec is not None and jt_dec.shape[1] >= 5:
        d_ds = downsample(jt_dec, n_max)
        out.update({
            "Jx_intra": d_ds[:, 1].tolist(),
            "Jy_intra": d_ds[:, 2].tolist(),
            "Jx_inter": d_ds[:, 3].tolist(),
            "Jy_inter": d_ds[:, 4].tolist(),
        })
    if jt_val is not None and jt_val.shape[1] >= 5:
        v_ds = downsample(jt_val, n_max)
        out.update({
            "Jx_K":  v_ds[:, 1].tolist(),
            "Jy_K":  v_ds[:, 2].tolist(),
            "Jx_Kp": v_ds[:, 3].tolist(),
            "Jy_Kp": v_ds[:, 4].tolist(),
        })
    return out, jt_ds[:, 0] if jt_ds.shape[1] >= 1 else None


def build_spectrum(hhg: np.ndarray | None, n_max: int) -> dict:
    if hhg is None:
        return {}
    h_ds = downsample(hhg, n_max)
    n_cols = h_ds.shape[1]
    out: dict[str, list] = {
        "harmonic_order": h_ds[:, 0].tolist() if n_cols >= 1 else [],
        "omega_au":       h_ds[:, 1].tolist() if n_cols >= 2 else [],
    }
    if n_cols >= 5:
        out.update({
            "HHG_x":     h_ds[:, 2].tolist(),
            "HHG_y":     h_ds[:, 3].tolist(),
            "HHG_total": h_ds[:, 4].tolist(),
        })
    elif n_cols >= 3:
        out["HHG_total"] = h_ds[:, 2].tolist()
    return out


def build_band_path(band_file: np.ndarray | None) -> dict:
    if band_file is None or band_file.ndim != 2 or band_file.shape[1] < 2:
        return {}
    k = band_file[:, 0]
    e = band_file[:, 1:]
    return {
        "k_path":    k.astype(float).tolist(),
        "energy_eV": e.astype(float).tolist(),
    }


def build_band_grid_preview(bg: BandGrid | None, bands: list[int], max_grid: int) -> dict:
    if bg is None or not bands:
        return {}
    stride_x = max(1, math.ceil(bg.nkx / max_grid))
    stride_y = max(1, math.ceil(bg.nky / max_grid))
    kx_ds = bg.kx[::stride_x]
    ky_ds = bg.ky[::stride_y]
    energies = bg.energies[bands][:, ::stride_x, ::stride_y]
    return {
        "kx":                    kx_ds.astype(float).tolist(),
        "ky":                    ky_ds.astype(float).tolist(),
        "selected_band_indices": list(bands),
        "energies_eV":           energies.astype(float).tolist(),
    }


def build_manifest(*,
                   dataset_name: str,
                   gauge: str,
                   material: str,
                   model: str,
                   source_class: str,
                   confidence: str,
                   bg: BandGrid | None,
                   nt: int,
                   available: list[str],
                   missing: list[str],
                   source_paths: dict[str, str],
                   emit_npz: bool) -> dict:
    return {
        "schema": SCHEMA,
        "dataset_name": dataset_name,
        "physics_provenance": {
            "source_class": source_class,
            "material": material,
            "model": model,
            "gauge_method": gauge,
            "confidence": confidence,
        },
        "units": {
            "time": "fs",
            "current": "a.u.",
            "energy": "eV",
            "k": "1/bohr",
            "omega": "a.u.",
            "hhg": "|J(omega)|^2 solver scaling",
        },
        "dimensions": {
            "nt": int(nt),
            "nkx": int(bg.nkx) if bg else 0,
            "nky": int(bg.nky) if bg else 0,
            "n_bands": int(bg.n_bands) if bg else 0,
        },
        "available_modules": available,
        "missing_modules": missing,
        "files": {
            "data_small": "data_small.json",
            "quicklook": "quicklook_summary.png",
            **({"data_arrays": "data_arrays.npz"} if emit_npz else {}),
        },
        "source_paths": source_paths,
    }


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    run_dir: Path = args.run_dir
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    jt    = _read_columns(run_dir / "Jt.dat")
    hhg   = _read_columns(run_dir / "HHG.dat")
    jt_d  = _read_columns(run_dir / "Jt_decomposed.dat")
    jt_v  = _read_columns(run_dir / "Jt_valley.dat")
    bands_arr = run_dir / "bands.dat"
    bg = read_bands_grid(bands_arr) if bands_arr.exists() else None
    band_path_arr = _read_columns(args.band_path) if args.band_path else None
    nml = parse_input_nml(run_dir / "input.nml")
    run_log = parse_run_log(run_dir / "run.log")

    selected = parse_band_slice(args.selected_bands, bg.n_bands if bg else 0)

    time_series, t_axis = build_time_series(jt, jt_d, jt_v, args.max_points_current)
    spectrum = build_spectrum(hhg, args.max_points_spectrum)
    band_path = build_band_path(band_path_arr)
    band_grid_preview = build_band_grid_preview(bg, selected, args.max_grid)

    raw_field = read_field_dat(run_dir / "Et.dat", run_dir / "At.dat")
    if raw_field is not None:
        f_t = downsample(raw_field["time_fs"], args.max_points_current)
        f_ex = downsample(raw_field["Ex"], args.max_points_current)
        f_ey = downsample(raw_field["Ey"], args.max_points_current)
        f_ax = downsample(raw_field["Ax"], args.max_points_current)
        f_ay = downsample(raw_field["Ay"], args.max_points_current)
        raw_source_file = sanitize_run_path(
            run_dir, run_dir / ("Et.dat" if raw_field["et_present"] else "At.dat")
        )
        field_block = {
            "time_fs": f_t.astype(float).tolist(),
            "Ex": f_ex.astype(float).tolist(),
            "Ey": f_ey.astype(float).tolist(),
            "Ax": f_ax.astype(float).tolist(),
            "Ay": f_ay.astype(float).tolist(),
            "source": "raw_solver_output",
            "raw_source_file": raw_source_file,
            "raw_source_columns": "it, time_fs, Ex_au, Ey_au, Ax_au, Ay_au",
        }
    elif t_axis is not None:
        nt_full = jt.shape[0] if jt is not None else None
        rec = reconstruct_field(t_axis, nml, run_log, nt_full=nt_full)
        field_block = {
            "time_fs": rec["time_fs"].astype(float).tolist(),
            "Ex": rec["Ex"].astype(float).tolist(),
            "Ey": rec["Ey"].astype(float).tolist(),
            "Ax": rec["Ax"].astype(float).tolist(),
            "Ay": rec["Ay"].astype(float).tolist(),
            "source": rec["source"],
            "reconstructed_from": rec["reconstructed_from"],
            "cross_checked_with": rec["cross_checked_with"],
            "cross_check": rec["cross_check"],
            "note": rec["note"],
        }
    else:
        field_block = {"time_fs": [], "Ex": [], "Ey": [],
                       "Ax": [], "Ay": [], "source": "unavailable"}

    data_small = {
        "time_series":       time_series,
        "spectrum":          spectrum,
        "band_path":         band_path,
        "band_grid_preview": band_grid_preview,
        "field":             field_block,
    }

    available = []
    missing = [
        "k_space_occupation",
        "rho_k_t",
        "production_lg_cov_berry_curvature",
    ]
    if time_series:
        available.append("current_time_series")
    if spectrum:
        available.append("hhg_spectrum")
    if band_path:
        available.append("band_path")
    if band_grid_preview:
        available.append("band_grid")
    if jt_d is not None:
        available.append("current_decomposition")
    if jt_v is not None:
        available.append("valley_current")
    if field_block["source"] != "unavailable":
        available.append("field_time_series")
    if field_block["source"] == "raw_solver_output":
        available.append("solver_output_Et_At")
    else:
        missing.append("solver_output_Et_At")

    has_et = raw_field is not None and raw_field["et_present"]
    has_at = raw_field is not None and raw_field["at_present"]
    source_paths = {
        "run_dir": f"{RUN_DIR_PLACEHOLDER}",
        **({"Jt":        sanitize_run_path(run_dir, run_dir / "Jt.dat")}        if jt is not None else {}),
        **({"HHG":       sanitize_run_path(run_dir, run_dir / "HHG.dat")}       if hhg is not None else {}),
        **({"bands":     sanitize_run_path(run_dir, run_dir / "bands.dat")}     if bg is not None else {}),
        **({"Jt_decomposed": sanitize_run_path(run_dir, run_dir / "Jt_decomposed.dat")} if jt_d is not None else {}),
        **({"Jt_valley":     sanitize_run_path(run_dir, run_dir / "Jt_valley.dat")}     if jt_v is not None else {}),
        **({"input_nml": sanitize_run_path(run_dir, run_dir / "input.nml")}     if nml else {}),
        **({"run_log":   sanitize_run_path(run_dir, run_dir / "run.log")}       if run_log else {}),
        **({"Et":        sanitize_run_path(run_dir, run_dir / "Et.dat")}        if has_et else {}),
        **({"At":        sanitize_run_path(run_dir, run_dir / "At.dat")}        if has_at else {}),
        **({"band_path": sanitize_band_path(args.band_path)} if band_path_arr is not None else {}),
    }

    if field_block["source"] == "raw_solver_output":
        field_conf = "field is raw solver output"
    elif field_block["source"].startswith("reconstructed"):
        field_conf = "field reconstructed from input.nml and cross-checked against run.log, not raw solver output"
    else:
        field_conf = "field unavailable"
    default_conf = (
        "research-output, visualization-ready for J(t)/HHG/bands; "
        f"{field_conf}"
    )
    manifest = build_manifest(
        dataset_name=args.dataset_name or run_dir.name or "hhgxr_demo_run",
        gauge=args.gauge_method,
        material=args.material,
        model=args.model,
        source_class=args.source_class,
        confidence=args.confidence or default_conf,
        bg=bg,
        nt=jt.shape[0] if jt is not None else 0,
        available=available,
        missing=missing,
        source_paths=source_paths,
        emit_npz=args.emit_npz,
    )

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (out_dir / "data_small.json").write_text(json.dumps(data_small, indent=2))
    print(f"[ok] wrote {out_dir / 'manifest.json'}")
    print(f"[ok] wrote {out_dir / 'data_small.json'}")

    if args.emit_npz:
        npz_path = out_dir / "data_arrays.npz"
        np.savez_compressed(
            npz_path,
            **({"Jt": jt} if jt is not None else {}),
            **({"HHG": hhg} if hhg is not None else {}),
            **({"Jt_decomposed": jt_d} if jt_d is not None else {}),
            **({"Jt_valley": jt_v} if jt_v is not None else {}),
            **({"kx": bg.kx, "ky": bg.ky, "energies_eV": bg.energies} if bg is not None else {}),
            **({"Et_time_fs": raw_field["time_fs"],
                "Ex": raw_field["Ex"], "Ey": raw_field["Ey"],
                "Ax": raw_field["Ax"], "Ay": raw_field["Ay"]}
               if raw_field is not None else {}),
        )
        print(f"[ok] wrote {npz_path}")

    try:
        from make_quicklook import render_quicklook  # type: ignore
    except Exception:
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from make_quicklook import render_quicklook  # type: ignore
        except Exception as exc:
            print(f"[warn] quicklook skipped: {exc}", file=sys.stderr)
            return 0

    try:
        render_quicklook(data_small, out_dir / "quicklook_summary.png")
        print(f"[ok] wrote {out_dir / 'quicklook_summary.png'}")
    except Exception as exc:
        print(f"[warn] quicklook failed: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
