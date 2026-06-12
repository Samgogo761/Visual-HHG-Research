#!/usr/bin/env python3
"""Convert a Quantum-light SBE run directory into a sanitized HHG-XR Lab demo bundle.

Column formats follow the writers in the Quantum-light solver
(https://github.com/Samgogo761/Quantum-light, src/mod_current.f90,
mod_hhg.f90, mod_crystal.f90, mod_geometry.f90, mod_spin.f90,
mod_sbe.f90):

    Jt.dat                 # it time(fs) Jx Jy
    Jt_decomposed.dat      # it time(fs) Jx_intra Jy_intra Jx_inter Jy_inter Jx_tot Jy_tot
    Jt_valley.dat          # it time(fs) Jx_K Jy_K Jx_Kp Jy_Kp eta_x eta_y
    Jt_spin.dat            # it time(fs) Jx_spin Jy_spin
    HHG.dat                # harmonic_order omega(a.u.) HHG_x HHG_y HHG_total
    HHG_spin.dat           # same layout as HHG.dat
    bands.dat              # header '# nkx=.. nky=.. n_trunc=..'; rows: ikx iky n E(eV) kx ky
    quantum_geometry.dat   # ikx iky band kx ky E(eV) Omega gxx gyy gxy valley
    occupation_kt.dat      # it time_fs ikx iky kx ky n_val n_cond      (save_occupation)
    occupation_band_kt.dat # it time_fs ikx iky band occupation         (occ_band_resolved)
    coherence_kt.dat       # it time_fs ikx iky kx ky coherence_norm    (save_coherence)
    Et.dat / At.dat        # it time(fs) Ex Ey Ax Ay   (native field export)
    input.nml              # &laser wvl_nm intensity_Wcm2 ncyc ... ; &method gauge_method
    run.log or run         # stdout log (omega0 / T_total / nt scraped when present)

Legacy layouts (time in the first column, wide-format bands.dat rows of
kx ky e1..eN) are still accepted as a fallback.

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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA = "hhgxr-demo-bundle-v0"

RUN_DIR_PLACEHOLDER = "<LOCAL_SBE_RUN_DIR>"
WANNIER_PLACEHOLDER = "<LOCAL_WANNIER_DIR>"

C_NM_PER_FS = 299.792458
AU_TIME_FS = 0.024188843265857   # 1 a.u. of time in fs (matches mod_params.f90)
WCM2_TO_AU = 1.0 / 3.50944758e16  # intensity to E0^2 (matches mod_params.f90)


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
                   help="Slice (a:b) of band indices for grid/geometry previews. "
                        "1-based to match solver band numbering when reading "
                        "long-format files; 0-based for legacy wide format.")
    p.add_argument("--max-grid", type=int, default=40,
                   help="Maximum kx/ky grid points kept in grid previews.")
    p.add_argument("--max-occ-snapshots", type=int, default=8,
                   help="Maximum occupation snapshots kept in data_small.json.")
    p.add_argument("--emit-npz", action="store_true",
                   help="Also write data_arrays.npz at original resolution. Off by default.")
    p.add_argument("--gauge-method", default=None,
                   help="Override gauge label. Default: read &method gauge_method "
                        "from input.nml, else 'unknown'.")
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
# Low-level readers
# ----------------------------------------------------------------------

def _read_columns(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    try:
        arr = np.loadtxt(path, comments=["#", "!"])
        if arr.ndim == 1:
            arr = arr[None, :]
        return arr
    except Exception as exc:
        print(f"[warn] failed to read {path.name}: {exc}", file=sys.stderr)
        return None


def downsample(a: np.ndarray, n_target: int) -> np.ndarray:
    if a.size == 0 or n_target <= 0 or a.shape[0] <= n_target:
        return a
    stride = max(1, math.ceil(a.shape[0] / n_target))
    return a[::stride]


def split_time_table(arr: np.ndarray | None) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Split a time-series table into (time_fs, data_columns).

    Solver format has a leading integer step index:  it time(fs) data...
    Legacy format starts directly with time:          time data...
    """
    if arr is None or arr.ndim != 2 or arr.shape[1] < 2:
        return None, None
    c0 = arr[:, 0]
    looks_like_index = (
        arr.shape[1] >= 3
        and np.allclose(c0, np.round(c0))
        and c0.size >= 2
        and np.allclose(np.diff(c0), 1.0)
    )
    if looks_like_index:
        return arr[:, 1], arr[:, 2:]
    return arr[:, 0], arr[:, 1:]


# ----------------------------------------------------------------------
# input.nml / run log parsing
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


def parse_run_log(run_dir: Path) -> dict[str, Any]:
    """Best-effort scrape of the run log (run.log or run) for cross-check values."""
    path = run_dir / "run.log"
    if not path.exists():
        path = run_dir / "run"
    if not path.exists():
        return {}
    text = path.read_text(errors="ignore")
    out: dict[str, Any] = {}
    patterns = {
        "omega0_au":  re.compile(r"omega0[_\s:]*=?\s*([+-]?\d+\.?\d*(?:[eEdD][+-]?\d+)?)"),
        "T_total_fs": re.compile(r"T[_\s]*total\s*[:=]\s*([+-]?\d+\.?\d*(?:[eEdD][+-]?\d+)?)"),
        "nt":         re.compile(r"\bnt\s*[:=]?\s*(\d+)\b"),
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


# ----------------------------------------------------------------------
# bands.dat reader (solver long format + legacy wide fallback)
# ----------------------------------------------------------------------

@dataclass
class BandGrid:
    energies: np.ndarray             # (n_bands, nkx, nky), eV
    nkx: int
    nky: int
    n_bands: int
    kx: np.ndarray | None = None     # (nkx,) legacy separable grid
    ky: np.ndarray | None = None     # (nky,)
    kx_grid: np.ndarray | None = None  # (nkx, nky) cartesian, non-separable lattices
    ky_grid: np.ndarray | None = None
    layout: str = "long"


_BANDS_HEADER = re.compile(r"nkx\s*=\s*(\d+).*?nky\s*=\s*(\d+).*?n_trunc\s*=\s*(\d+)")


def _read_bands_header(path: Path) -> tuple[int, int, int] | None:
    try:
        with path.open(errors="ignore") as fh:
            for _ in range(5):
                line = fh.readline()
                if not line:
                    break
                m = _BANDS_HEADER.search(line)
                if m:
                    return int(m.group(1)), int(m.group(2)), int(m.group(3))
    except OSError:
        pass
    return None


def read_bands_grid(path: Path) -> BandGrid | None:
    """Read bands.dat.

    Solver long format: '# nkx=.. nky=.. n_trunc=..' header, then rows of
        ikx iky n E(eV) kx(1/bohr) ky(1/bohr)
    Legacy wide format: rows of  kx ky e1 e2 ... eN.
    """
    raw = _read_columns(path)
    if raw is None or raw.ndim != 2 or raw.shape[1] < 3:
        return None

    int_like = [
        np.allclose(raw[:, c], np.round(raw[:, c])) for c in range(min(3, raw.shape[1]))
    ]
    if raw.shape[1] == 6 and all(int_like):
        ikx = raw[:, 0].astype(int)
        iky = raw[:, 1].astype(int)
        n   = raw[:, 2].astype(int)
        hdr = _read_bands_header(path)
        if hdr:
            nkx, nky, n_bands = hdr
        else:
            nkx, nky, n_bands = ikx.max(), iky.max(), n.max()
        energies = np.full((n_bands, nkx, nky), np.nan, dtype=np.float32)
        kx_grid = np.full((nkx, nky), np.nan, dtype=np.float32)
        ky_grid = np.full((nkx, nky), np.nan, dtype=np.float32)
        energies[n - 1, ikx - 1, iky - 1] = raw[:, 3]
        kx_grid[ikx - 1, iky - 1] = raw[:, 4]
        ky_grid[ikx - 1, iky - 1] = raw[:, 5]
        return BandGrid(energies=energies, nkx=nkx, nky=nky, n_bands=n_bands,
                        kx_grid=kx_grid, ky_grid=ky_grid, layout="long")

    # legacy wide format
    kx_col = raw[:, 0]
    ky_col = raw[:, 1]
    e_cols = raw[:, 2:]
    n_bands = e_cols.shape[1]
    kx_unique = np.unique(kx_col)
    ky_unique = np.unique(ky_col)
    nkx, nky = kx_unique.size, ky_unique.size
    if nkx * nky != raw.shape[0]:
        print(f"[warn] bands.dat rows {raw.shape[0]} != nkx*nky {nkx*nky}; "
              f"best-effort wide-format grid", file=sys.stderr)
    energies = np.full((n_bands, nkx, nky), np.nan, dtype=np.float32)
    kx_idx = {v: i for i, v in enumerate(kx_unique)}
    ky_idx = {v: i for i, v in enumerate(ky_unique)}
    for r in range(raw.shape[0]):
        ix = kx_idx.get(kx_col[r])
        iy = ky_idx.get(ky_col[r])
        if ix is None or iy is None:
            continue
        energies[:, ix, iy] = e_cols[r]
    return BandGrid(energies=energies, nkx=nkx, nky=nky, n_bands=n_bands,
                    kx=kx_unique.astype(np.float32),
                    ky=ky_unique.astype(np.float32), layout="wide")


def parse_band_slice(spec: str, n_bands: int, one_based: bool) -> list[int]:
    """Return 0-based band indices. For long-format (solver) files the CLI
    slice is interpreted 1-based to match solver band numbering."""
    if n_bands <= 0:
        return []
    if not spec:
        return list(range(n_bands))
    if ":" in spec:
        a, b = spec.split(":", 1)
        lo = int(a) if a else (1 if one_based else 0)
        hi = int(b) if b else n_bands
    else:
        lo = int(spec)
        hi = lo + 1
    if one_based:
        lo, hi = lo - 1, hi - 1
    lo = max(0, lo)
    hi = min(n_bands, hi)
    return list(range(lo, hi))


# ----------------------------------------------------------------------
# quantum_geometry.dat reader
# ----------------------------------------------------------------------

@dataclass
class QuantumGeometry:
    nkx: int
    nky: int
    n_bands: int
    kx_grid: np.ndarray             # (nkx, nky)
    ky_grid: np.ndarray
    berry: np.ndarray               # (n_bands, nkx, nky)  Omega_n(k), a.u.
    tr_metric: np.ndarray           # (n_bands, nkx, nky)  gxx+gyy, a.u.
    valley_id: np.ndarray           # (nkx, nky) int


def read_quantum_geometry(path: Path) -> QuantumGeometry | None:
    """Read quantum_geometry.dat:
        ikx iky band kx ky E(eV) Omega gxx gyy gxy valley
    """
    raw = _read_columns(path)
    if raw is None or raw.ndim != 2 or raw.shape[1] < 11:
        return None
    ikx = raw[:, 0].astype(int)
    iky = raw[:, 1].astype(int)
    n   = raw[:, 2].astype(int)
    nkx, nky, n_bands = ikx.max(), iky.max(), n.max()
    kx_grid = np.full((nkx, nky), np.nan, dtype=np.float32)
    ky_grid = np.full((nkx, nky), np.nan, dtype=np.float32)
    berry = np.full((n_bands, nkx, nky), np.nan, dtype=np.float32)
    trg = np.full((n_bands, nkx, nky), np.nan, dtype=np.float32)
    valley = np.zeros((nkx, nky), dtype=np.int32)
    kx_grid[ikx - 1, iky - 1] = raw[:, 3]
    ky_grid[ikx - 1, iky - 1] = raw[:, 4]
    berry[n - 1, ikx - 1, iky - 1] = raw[:, 6]
    trg[n - 1, ikx - 1, iky - 1] = raw[:, 7] + raw[:, 8]
    valley[ikx - 1, iky - 1] = raw[:, 10].astype(int)
    return QuantumGeometry(nkx=nkx, nky=nky, n_bands=n_bands,
                           kx_grid=kx_grid, ky_grid=ky_grid,
                           berry=berry, tr_metric=trg, valley_id=valley)


# ----------------------------------------------------------------------
# occupation_kt.dat reader (Tier-0 diagnostic snapshots)
# ----------------------------------------------------------------------

@dataclass
class KSnapshots:
    """k-resolved snapshot stack shared by occupation and coherence outputs.

    The solver writes one row per (it, ikx, iky) per file:
        occupation_kt.dat:  it time_fs ikx iky kx ky n_val n_cond
        coherence_kt.dat:   it time_fs ikx iky kx ky coherence_norm
    """
    times_fs: np.ndarray            # (n_snap,)
    nkx: int
    nky: int
    kx_grid: np.ndarray             # (nkx, nky)
    ky_grid: np.ndarray
    values: dict[str, np.ndarray]   # name -> (n_snap, nkx, nky)


def _read_k_snapshots(path: Path, value_columns: dict[str, int],
                      min_cols: int) -> KSnapshots | None:
    raw = _read_columns(path)
    if raw is None or raw.ndim != 2 or raw.shape[1] < min_cols:
        return None
    it = raw[:, 0].astype(int)
    snap_ids = np.unique(it)
    ikx = raw[:, 2].astype(int)
    iky = raw[:, 3].astype(int)
    nkx, nky = ikx.max(), iky.max()
    n_snap = snap_ids.size
    times = np.zeros(n_snap)
    kx_grid = np.full((nkx, nky), np.nan, dtype=np.float32)
    ky_grid = np.full((nkx, nky), np.nan, dtype=np.float32)
    values = {name: np.full((n_snap, nkx, nky), np.nan, dtype=np.float32)
              for name in value_columns}
    id_to_pos = {s: i for i, s in enumerate(snap_ids)}
    for r in range(raw.shape[0]):
        s = id_to_pos[it[r]]
        ix, iy = ikx[r] - 1, iky[r] - 1
        times[s] = raw[r, 1]
        kx_grid[ix, iy] = raw[r, 4]
        ky_grid[ix, iy] = raw[r, 5]
        for name, col in value_columns.items():
            values[name][s, ix, iy] = raw[r, col]
    return KSnapshots(times_fs=times, nkx=nkx, nky=nky,
                      kx_grid=kx_grid, ky_grid=ky_grid, values=values)


def read_occupation_kt(path: Path) -> KSnapshots | None:
    """Read occupation_kt.dat: it time_fs ikx iky kx ky n_val n_cond."""
    return _read_k_snapshots(path, {"n_val": 6, "n_cond": 7}, min_cols=8)


def read_coherence_kt(path: Path) -> KSnapshots | None:
    """Read coherence_kt.dat: it time_fs ikx iky kx ky coherence_norm.

    coherence_norm(k,t) = sqrt(sum_{m!=n} |rho_mn(k,t)|^2). The solver
    fixes coherence_norm(k, t=0) == 0; rendering n>0 entries at t>0 is
    safe.
    """
    return _read_k_snapshots(path, {"coherence_norm": 6}, min_cols=7)


# ----------------------------------------------------------------------
# Field: raw solver output (Et.dat / At.dat) and reconstruction
# ----------------------------------------------------------------------

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


def _integrate_neg(field_arr: np.ndarray, time_fs: np.ndarray) -> np.ndarray:
    """A(t) = -integral E dt' via trapezoidal cumulation, A(t0)=0."""
    if field_arr.size < 2:
        return np.zeros_like(field_arr)
    dt = np.diff(time_fs)
    mids = 0.5 * (field_arr[:-1] + field_arr[1:])
    return np.concatenate(([0.0], -np.cumsum(mids * dt)))


def reconstruct_field(time_fs: np.ndarray,
                      nml: dict[str, Any],
                      run_log: dict[str, Any],
                      nt_full: int | None = None) -> dict[str, Any]:
    """Cos-squared envelope reconstruction from input.nml plus run.log cross-check.

    Parameter names follow the solver namelist (&laser): wvl_nm,
    intensity_Wcm2 (E0 = sqrt(I * Wcm2_to_au)), ncyc. Legacy keys
    (lambda_nm, n_cycles, E0_au) remain accepted.

    The label is 'reconstructed_from_input_nml_not_raw_output': audited
    and visualization-ready, but not the solver's native E(t)/A(t).
    Note the solver additionally applies a residual-DC ramp correction
    to A(t) (mod_laser.f90), which this reconstruction does not.
    """
    if time_fs.size == 0:
        return {"source": "unavailable"}

    wavelength_nm = float(nml.get("wvl_nm", nml.get("lambda_nm", nml.get("wavelength_nm", 3200.0))))
    n_cycles = float(nml.get("ncyc", nml.get("n_cycles", 4.0)))
    if "intensity_Wcm2" in nml:
        e0 = math.sqrt(float(nml["intensity_Wcm2"]) * WCM2_TO_AU)
    else:
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
# Bundle blocks
# ----------------------------------------------------------------------

def build_time_series(jt: np.ndarray | None,
                      jt_dec: np.ndarray | None,
                      jt_val: np.ndarray | None,
                      jt_spin: np.ndarray | None,
                      n_max: int) -> tuple[dict, np.ndarray | None]:
    t, d = split_time_table(jt)
    if t is None:
        return {}, None
    keep = downsample(np.column_stack([t, d]), n_max)
    t_ds = keep[:, 0]
    out: dict[str, list] = {
        "time_fs": t_ds.tolist(),
        "Jx":      keep[:, 1].tolist() if keep.shape[1] >= 2 else [],
        "Jy":      keep[:, 2].tolist() if keep.shape[1] >= 3 else [],
    }

    def add(table: np.ndarray | None, names: list[str]) -> None:
        tt, dd = split_time_table(table)
        if tt is None:
            return
        dd_ds = downsample(dd, n_max)
        for i, name in enumerate(names):
            if i < dd_ds.shape[1]:
                out[name] = dd_ds[:, i].tolist()

    # Jt_decomposed.dat: Jx_intra Jy_intra Jx_inter Jy_inter Jx_tot Jy_tot
    add(jt_dec, ["Jx_intra", "Jy_intra", "Jx_inter", "Jy_inter"])
    # Jt_valley.dat: Jx_K Jy_K Jx_Kp Jy_Kp eta_x eta_y
    add(jt_val, ["Jx_K", "Jy_K", "Jx_Kp", "Jy_Kp", "eta_x", "eta_y"])
    # Jt_spin.dat: Jx_spin Jy_spin
    add(jt_spin, ["Jx_spin", "Jy_spin"])
    return out, t_ds


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
    return {
        "k_path":    band_file[:, 0].astype(float).tolist(),
        "energy_eV": band_file[:, 1:].astype(float).tolist(),
    }


def _grid_strides(nkx: int, nky: int, max_grid: int) -> tuple[int, int]:
    return (max(1, math.ceil(nkx / max_grid)),
            max(1, math.ceil(nky / max_grid)))


def build_band_grid_preview(bg: BandGrid | None, bands: list[int], max_grid: int) -> dict:
    if bg is None or not bands:
        return {}
    sx, sy = _grid_strides(bg.nkx, bg.nky, max_grid)
    energies = bg.energies[bands][:, ::sx, ::sy]
    out: dict[str, Any] = {
        "selected_band_indices": [b + 1 for b in bands] if bg.layout == "long" else list(bands),
        "band_index_base": 1 if bg.layout == "long" else 0,
        "energies_eV": np.nan_to_num(energies).astype(float).tolist(),
    }
    if bg.layout == "long":
        out["kx_grid"] = np.nan_to_num(bg.kx_grid[::sx, ::sy]).astype(float).tolist()
        out["ky_grid"] = np.nan_to_num(bg.ky_grid[::sx, ::sy]).astype(float).tolist()
    else:
        out["kx"] = bg.kx[::sx].astype(float).tolist()
        out["ky"] = bg.ky[::sy].astype(float).tolist()
    return out


def build_quantum_geometry_preview(qg: QuantumGeometry | None,
                                   bands: list[int],
                                   max_grid: int) -> dict:
    if qg is None:
        return {}
    bands = [b for b in bands if 0 <= b < qg.n_bands] or list(range(min(4, qg.n_bands)))
    sx, sy = _grid_strides(qg.nkx, qg.nky, max_grid)
    return {
        "selected_band_indices": [b + 1 for b in bands],
        "band_index_base": 1,
        "kx_grid": np.nan_to_num(qg.kx_grid[::sx, ::sy]).astype(float).tolist(),
        "ky_grid": np.nan_to_num(qg.ky_grid[::sx, ::sy]).astype(float).tolist(),
        "berry_curvature_au": np.nan_to_num(qg.berry[bands][:, ::sx, ::sy]).astype(float).tolist(),
        "trace_quantum_metric_au": np.nan_to_num(qg.tr_metric[bands][:, ::sx, ::sy]).astype(float).tolist(),
        "valley_id": qg.valley_id[::sx, ::sy].astype(int).tolist(),
        "note": (
            "PT-symmetric AFM: Omega_n(k) ~ 0 at the numerical floor is the "
            "physically correct result, not a data error."
        ),
    }


def _select_snapshot_indices(n_snap: int, max_snapshots: int) -> list[int]:
    if n_snap <= 0:
        return []
    stride = max(1, math.ceil(n_snap / max_snapshots))
    snap_ids = list(range(0, n_snap, stride))
    if (n_snap - 1) not in snap_ids:
        snap_ids.append(n_snap - 1)
    return snap_ids


def build_occupation_preview(occ: KSnapshots | None,
                             max_snapshots: int,
                             max_grid: int) -> dict:
    if occ is None:
        return {}
    snap_ids = _select_snapshot_indices(occ.times_fs.size, max_snapshots)
    sx, sy = _grid_strides(occ.nkx, occ.nky, max_grid)
    n_val = occ.values["n_val"]
    n_cond = occ.values["n_cond"]
    n_cond0 = n_cond[0]
    snapshots = []
    for s in snap_ids:
        snapshots.append({
            "time_fs": float(occ.times_fs[s]),
            "n_val":   np.nan_to_num(n_val[s, ::sx, ::sy]).astype(float).tolist(),
            "n_cond":  np.nan_to_num(n_cond[s, ::sx, ::sy]).astype(float).tolist(),
            "delta_n_cond": np.nan_to_num(
                (n_cond[s] - n_cond0)[::sx, ::sy]).astype(float).tolist(),
        })
    return {
        "kx_grid": np.nan_to_num(occ.kx_grid[::sx, ::sy]).astype(float).tolist(),
        "ky_grid": np.nan_to_num(occ.ky_grid[::sx, ::sy]).astype(float).tolist(),
        "snapshots": snapshots,
        "definition": (
            "n_val = sum_n<=nv Re rho_nn(k,t); n_cond = sum_n>nv Re rho_nn(k,t); "
            "delta_n_cond = n_cond(t) - n_cond(t0). Source: solver Tier-0 "
            "occupation_kt.dat (save_occupation)."
        ),
    }


def build_coherence_preview(coh: KSnapshots | None,
                            max_snapshots: int,
                            max_grid: int) -> dict:
    if coh is None:
        return {}
    snap_ids = _select_snapshot_indices(coh.times_fs.size, max_snapshots)
    sx, sy = _grid_strides(coh.nkx, coh.nky, max_grid)
    cn = coh.values["coherence_norm"]
    snapshots = []
    for s in snap_ids:
        snapshots.append({
            "time_fs":        float(coh.times_fs[s]),
            "coherence_norm": np.nan_to_num(cn[s, ::sx, ::sy]).astype(float).tolist(),
        })
    return {
        "kx_grid": np.nan_to_num(coh.kx_grid[::sx, ::sy]).astype(float).tolist(),
        "ky_grid": np.nan_to_num(coh.ky_grid[::sx, ::sy]).astype(float).tolist(),
        "snapshots": snapshots,
        "definition": (
            "coherence_norm(k,t) = sqrt(sum_{m != n} |rho_mn(k,t)|^2). "
            "Equilibrium check: coherence_norm(k, t=0) == 0. "
            "Source: solver coherence_kt.dat (save_coherence)."
        ),
    }


def build_manifest(*,
                   dataset_name: str,
                   gauge: str,
                   material: str,
                   model: str,
                   source_class: str,
                   confidence: str,
                   dimensions: dict[str, int],
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
            "berry_curvature": "a.u.",
            "quantum_metric": "a.u.",
            "occupation": "electrons per k-point (dimensionless)",
        },
        "dimensions": dimensions,
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

    jt      = _read_columns(run_dir / "Jt.dat")
    hhg     = _read_columns(run_dir / "HHG.dat")
    hhg_sp  = _read_columns(run_dir / "HHG_spin.dat")
    jt_d    = _read_columns(run_dir / "Jt_decomposed.dat")
    jt_v    = _read_columns(run_dir / "Jt_valley.dat")
    jt_s    = _read_columns(run_dir / "Jt_spin.dat")
    bg      = read_bands_grid(run_dir / "bands.dat") if (run_dir / "bands.dat").exists() else None
    qg      = read_quantum_geometry(run_dir / "quantum_geometry.dat")
    occ     = read_occupation_kt(run_dir / "occupation_kt.dat")
    coh     = read_coherence_kt(run_dir / "coherence_kt.dat")
    occ_band_file = run_dir / "occupation_band_kt.dat"
    band_path_arr = _read_columns(args.band_path) if args.band_path else None
    nml     = parse_input_nml(run_dir / "input.nml")
    run_log = parse_run_log(run_dir)

    one_based = bg is not None and bg.layout == "long"
    selected = parse_band_slice(args.selected_bands, bg.n_bands if bg else (qg.n_bands if qg else 0), one_based)

    time_series, t_axis = build_time_series(jt, jt_d, jt_v, jt_s, args.max_points_current)
    spectrum = build_spectrum(hhg, args.max_points_spectrum)
    spectrum_spin = build_spectrum(hhg_sp, args.max_points_spectrum)
    band_path = build_band_path(band_path_arr)
    band_grid_preview = build_band_grid_preview(bg, selected, args.max_grid)
    geometry_preview = build_quantum_geometry_preview(qg, selected, args.max_grid)
    occupation_preview = build_occupation_preview(occ, args.max_occ_snapshots, args.max_grid)
    coherence_preview = build_coherence_preview(coh, args.max_occ_snapshots, args.max_grid)

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
        "time_series":              time_series,
        "spectrum":                 spectrum,
        **({"spectrum_spin":        spectrum_spin} if spectrum_spin else {}),
        "band_path":                band_path,
        "band_grid_preview":        band_grid_preview,
        **({"quantum_geometry_preview": geometry_preview} if geometry_preview else {}),
        **({"occupation_preview":   occupation_preview} if occupation_preview else {}),
        **({"coherence_preview":    coherence_preview} if coherence_preview else {}),
        "field":                    field_block,
    }

    available: list[str] = []
    missing: list[str] = []

    def module(name: str, present: bool) -> None:
        (available if present else missing).append(name)

    module("current_time_series", bool(time_series))
    module("hhg_spectrum", bool(spectrum))
    module("band_path", bool(band_path))
    module("band_grid", bool(band_grid_preview))
    module("current_decomposition", jt_d is not None)
    module("valley_current", jt_v is not None)
    module("spin_current", jt_s is not None)
    module("hhg_spin", bool(spectrum_spin))
    module("quantum_geometry", bool(geometry_preview))
    module("k_space_occupation", bool(occupation_preview))
    module("band_resolved_occupation", occ_band_file.exists())
    module("interband_coherence_norm", bool(coherence_preview))
    module("field_time_series", field_block["source"] != "unavailable")
    module("solver_output_Et_At", field_block["source"] == "raw_solver_output")
    missing.append("rho_k_t_full_density_matrix")

    has_et = raw_field is not None and raw_field["et_present"]
    has_at = raw_field is not None and raw_field["at_present"]
    source_paths = {
        "run_dir": f"{RUN_DIR_PLACEHOLDER}",
        **({"Jt":        sanitize_run_path(run_dir, run_dir / "Jt.dat")}        if jt is not None else {}),
        **({"HHG":       sanitize_run_path(run_dir, run_dir / "HHG.dat")}       if hhg is not None else {}),
        **({"HHG_spin":  sanitize_run_path(run_dir, run_dir / "HHG_spin.dat")}  if hhg_sp is not None else {}),
        **({"bands":     sanitize_run_path(run_dir, run_dir / "bands.dat")}     if bg is not None else {}),
        **({"Jt_decomposed": sanitize_run_path(run_dir, run_dir / "Jt_decomposed.dat")} if jt_d is not None else {}),
        **({"Jt_valley":     sanitize_run_path(run_dir, run_dir / "Jt_valley.dat")}     if jt_v is not None else {}),
        **({"Jt_spin":       sanitize_run_path(run_dir, run_dir / "Jt_spin.dat")}       if jt_s is not None else {}),
        **({"quantum_geometry": sanitize_run_path(run_dir, run_dir / "quantum_geometry.dat")} if qg is not None else {}),
        **({"occupation_kt":    sanitize_run_path(run_dir, run_dir / "occupation_kt.dat")}    if occ is not None else {}),
        **({"occupation_band_kt": sanitize_run_path(run_dir, occ_band_file)} if occ_band_file.exists() else {}),
        **({"coherence_kt":     sanitize_run_path(run_dir, run_dir / "coherence_kt.dat")}     if coh is not None else {}),
        **({"input_nml": sanitize_run_path(run_dir, run_dir / "input.nml")}     if nml else {}),
        **({"run_log":   sanitize_run_path(run_dir, run_dir / "run.log")}       if run_log else {}),
        **({"Et":        sanitize_run_path(run_dir, run_dir / "Et.dat")}        if has_et else {}),
        **({"At":        sanitize_run_path(run_dir, run_dir / "At.dat")}        if has_at else {}),
        **({"band_path": sanitize_band_path(args.band_path)} if band_path_arr is not None else {}),
    }

    gauge = args.gauge_method or str(nml.get("gauge_method", "unknown"))

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

    dimensions = {
        "nt": int(jt.shape[0]) if jt is not None else 0,
        "nkx": int(bg.nkx) if bg else (int(qg.nkx) if qg else 0),
        "nky": int(bg.nky) if bg else (int(qg.nky) if qg else 0),
        "n_bands": int(bg.n_bands) if bg else (int(qg.n_bands) if qg else 0),
        **({"n_valence": int(nml["nv_orig"])} if "nv_orig" in nml else {}),
        **({"n_occupation_snapshots": int(occ.times_fs.size)} if occ else {}),
        **({"n_coherence_snapshots":  int(coh.times_fs.size)} if coh else {}),
    }

    manifest = build_manifest(
        dataset_name=args.dataset_name or run_dir.name or "hhgxr_demo_run",
        gauge=gauge,
        material=args.material,
        model=args.model,
        source_class=args.source_class,
        confidence=args.confidence or default_conf,
        dimensions=dimensions,
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
            **({"HHG_spin": hhg_sp} if hhg_sp is not None else {}),
            **({"Jt_decomposed": jt_d} if jt_d is not None else {}),
            **({"Jt_valley": jt_v} if jt_v is not None else {}),
            **({"Jt_spin": jt_s} if jt_s is not None else {}),
            **({"energies_eV": bg.energies} if bg is not None else {}),
            **({"berry": qg.berry, "tr_metric": qg.tr_metric,
                "valley_id": qg.valley_id} if qg is not None else {}),
            **({"occ_times_fs": occ.times_fs,
                "occ_n_val": occ.values["n_val"],
                "occ_n_cond": occ.values["n_cond"]} if occ is not None else {}),
            **({"coh_times_fs": coh.times_fs,
                "coh_norm": coh.values["coherence_norm"]} if coh is not None else {}),
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
