#!/usr/bin/env python3
"""Materialize the committed synthetic demo bundle.

Generates a synthetic SBE run directory that mimics the *real*
Quantum-light solver output formats (leading `it` index column on time
series, long-format bands.dat with `# nkx= nky= n_trunc=` header,
Jt_spin / HHG_spin / quantum_geometry / occupation_kt files, log file
named `run`), then drives tools/convert_sbe_run.py over it.

This is the single source of truth for regenerating
data/samples/demo_bundle_minimal/ after schema changes, and the writer
functions are imported by tests/test_converter_with_synthetic_data.py.

Usage:
    python tools/make_synthetic_bundle.py [--out-dir data/samples/demo_bundle_minimal]
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))


def write_synthetic_run(run_dir: Path,
                        nt: int = 600,
                        nkx: int = 8,
                        nky: int = 8,
                        n_bands: int = 12,
                        with_spin: bool = True,
                        with_geometry: bool = True,
                        with_occupation: bool = True,
                        with_coherence: bool = True,
                        n_occ_snapshots: int = 6) -> None:
    """Write a synthetic run directory in the solver's real column formats."""
    run_dir.mkdir(parents=True, exist_ok=True)
    it = np.arange(1, nt + 1)
    t = np.linspace(-20.0, 20.0, nt)
    env = np.exp(-0.005 * t**2)
    omega = 0.5
    jx = np.sin(omega * t) * env
    jy = 0.8 * np.cos(omega * t) * env
    jx_intra, jy_intra = 0.6 * jx, 0.6 * jy
    jx_inter, jy_inter = 0.4 * jx, 0.4 * jy
    jx_K = 0.5 * jx + 0.05 * np.sin(3 * omega * t) * env
    jy_K = 0.5 * jy
    jx_Kp, jy_Kp = jx - jx_K, jy - jy_K
    with np.errstate(divide="ignore", invalid="ignore"):
        eta_x = np.where(np.abs(jx) > 1e-30, (jx_K - jx_Kp) / jx, 0.0)
        eta_y = np.where(np.abs(jy) > 1e-30, (jy_K - jy_Kp) / jy, 0.0)

    # Jt.dat: it time Jx Jy
    np.savetxt(run_dir / "Jt.dat", np.column_stack([it, t, jx, jy]),
               header="it   time(fs)   Jx(a.u.)   Jy(a.u.)")
    # Jt_decomposed.dat: it time Jx_intra Jy_intra Jx_inter Jy_inter Jx_tot Jy_tot
    np.savetxt(run_dir / "Jt_decomposed.dat",
               np.column_stack([it, t, jx_intra, jy_intra, jx_inter, jy_inter, jx, jy]),
               header="it  time(fs)  Jx_intra  Jy_intra  Jx_inter  Jy_inter  Jx_tot  Jy_tot")
    # Jt_valley.dat: it time Jx_K Jy_K Jx_Kp Jy_Kp eta_x eta_y
    np.savetxt(run_dir / "Jt_valley.dat",
               np.column_stack([it, t, jx_K, jy_K, jx_Kp, jy_Kp, eta_x, eta_y]),
               header="it  time(fs)  Jx_K  Jy_K  Jx_Kp  Jy_Kp  eta_x  eta_y")
    if with_spin:
        # Jt_spin.dat: it time Jx_spin Jy_spin (two header lines like the solver)
        body = np.column_stack([it, t, 0.1 * jx, 0.05 * jy])
        np.savetxt(run_dir / "Jt_spin.dat", body,
                   header="spin-z current J^{s_z}(t) = (1/2)<{S_z,v}>  (a.u.)\n"
                          "it  time(fs)  Jx_spin  Jy_spin")

    # HHG.dat / HHG_spin.dat: order omega HHG_x HHG_y HHG_total
    n_omega = 200
    order = np.arange(0, n_omega, dtype=float) * 0.1
    omega_au = 0.057 * order
    spec_x = 1.0 / (1.0 + ((order - 7) / 4.0) ** 2)
    cutoff = 15
    spec_x = spec_x * (order <= cutoff) + 1e-4 * np.exp(-(order - cutoff) / 3.0) * (order > cutoff)
    spec_x = spec_x * np.where(np.round(order) % 2 == 1, 1.0, 0.05)
    spec_y = 0.7 * spec_x
    np.savetxt(run_dir / "HHG.dat",
               np.column_stack([order, omega_au, spec_x, spec_y, spec_x + spec_y]),
               header="harmonic_order  omega(a.u.)  HHG_x  HHG_y  HHG_total")
    if with_spin:
        np.savetxt(run_dir / "HHG_spin.dat",
                   np.column_stack([order, omega_au, 0.1 * spec_x, 0.1 * spec_y,
                                    0.1 * (spec_x + spec_y)]),
                   header="harmonic_order  omega(a.u.)  HHG_x  HHG_y  HHG_total")

    # bands.dat long format: ikx iky n E(eV) kx ky, plus solver header
    kxv = np.linspace(-0.5, 0.5, nkx)
    kyv = np.linspace(-0.5, 0.5, nky)
    rows = []
    for iy in range(1, nky + 1):
        for ix in range(1, nkx + 1):
            kx_c = kxv[ix - 1] - 0.15 * kyv[iy - 1]  # sheared (hex-like) cartesian grid
            ky_c = kyv[iy - 1]
            disp = 0.5 * (kx_c**2 + ky_c**2)
            for n in range(1, n_bands + 1):
                rows.append([ix, iy, n, disp + 0.3 * (n - 1) - 1.0, kx_c, ky_c])
    np.savetxt(run_dir / "bands.dat", np.array(rows),
               fmt=["%6d", "%6d", "%6d", "%16.8E", "%16.8E", "%16.8E"],
               header=f"nkx={nkx} nky={nky} n_trunc={n_bands}\n"
                      "ikx iky n  E(eV)  kx(1/bohr)  ky(1/bohr)")

    if with_geometry:
        # quantum_geometry.dat: ikx iky band kx ky E Omega gxx gyy gxy valley
        rows = []
        for iy in range(1, nky + 1):
            for ix in range(1, nkx + 1):
                kx_c = kxv[ix - 1] - 0.15 * kyv[iy - 1]
                ky_c = kyv[iy - 1]
                vid = 1 if kx_c > 0 else 2
                for n in range(1, n_bands + 1):
                    e = 0.5 * (kx_c**2 + ky_c**2) + 0.3 * (n - 1) - 1.0
                    omega_b = 1e-12 * np.sin(n + kx_c)        # PT-symmetric floor
                    gxx = 0.01 / (0.1 + kx_c**2 + ky_c**2)
                    gyy = 0.8 * gxx
                    gxy = 0.05 * gxx
                    rows.append([ix, iy, n, kx_c, ky_c, e, omega_b, gxx, gyy, gxy, vid])
        np.savetxt(run_dir / "quantum_geometry.dat", np.array(rows),
                   fmt=["%6d", "%6d", "%6d"] + ["%16.8E"] * 7 + ["%4d"],
                   header="Band-resolved quantum geometry (length gauge, band basis)\n"
                          "ikx iky band  kx(1/bohr) ky(1/bohr)  E(eV)  Omega(a.u.)  gxx  gyy  gxy  valley")

    snap_its = np.linspace(1, nt, n_occ_snapshots, dtype=int) if (with_occupation or with_coherence) else np.array([], dtype=int)
    if with_occupation:
        # occupation_kt.dat: it time_fs ikx iky kx ky n_val n_cond
        rows = []
        for s_it in snap_its:
            time_fs = t[s_it - 1]
            pump = float(env[s_it - 1])
            for iy in range(1, nky + 1):
                for ix in range(1, nkx + 1):
                    kx_c = kxv[ix - 1] - 0.15 * kyv[iy - 1]
                    ky_c = kyv[iy - 1]
                    exc = 0.02 * pump * np.exp(-8 * (kx_c**2 + ky_c**2))
                    rows.append([s_it, time_fs, ix, iy, kx_c, ky_c,
                                 4.0 - exc, exc])
        np.savetxt(run_dir / "occupation_kt.dat", np.array(rows),
                   fmt=["%7d", "%14.6E", "%5d", "%5d", "%14.6E", "%14.6E",
                        "%16.8E", "%16.8E"],
                   header="k-resolved occupation, valence/conduction sums\n"
                          "it  time_fs  ikx iky  kx ky  n_val n_cond")

    if with_coherence:
        # coherence_kt.dat: it time_fs ikx iky kx ky coherence_norm
        # By construction: coherence_norm(k, t=0) == 0 (equilibrium).
        rows = []
        t0_value = float(t[snap_its[0] - 1]) if snap_its.size else None
        for s_it in snap_its:
            time_fs = float(t[s_it - 1])
            pump = float(env[s_it - 1])
            for iy in range(1, nky + 1):
                for ix in range(1, nkx + 1):
                    kx_c = kxv[ix - 1] - 0.15 * kyv[iy - 1]
                    ky_c = kyv[iy - 1]
                    if t0_value is not None and time_fs == t0_value:
                        coh = 0.0
                    else:
                        coh = 0.01 * pump * np.exp(-4 * (kx_c**2 + ky_c**2))
                    rows.append([s_it, time_fs, ix, iy, kx_c, ky_c, coh])
        np.savetxt(run_dir / "coherence_kt.dat", np.array(rows),
                   fmt=["%7d", "%14.6E", "%5d", "%5d", "%14.6E", "%14.6E", "%16.8E"],
                   header="k-resolved interband coherence norm\n"
                          "coherence_norm(k,t) = sqrt(sum_{m!=n} |rho_mn(k,t)|^2)\n"
                          "it  time_fs  ikx iky  kx ky  coherence_norm")

    # input.nml in the solver's namelist vocabulary
    (run_dir / "input.nml").write_text(
        "&laser\n"
        "  wvl_nm = 3200.0,\n"
        "  intensity_Wcm2 = 8.8e8,\n"
        "  ncyc = 4.0,\n"
        "  env_type = 2,\n"
        "/\n"
        "&bands\n"
        "  nv_orig = 8\n"
        "/\n"
        "&method\n"
        "  gauge_method = 'lg_cov'\n"
        "/\n"
        "&output\n"
        "  save_geometry = .true.\n"
        f"  save_occupation = .{str(with_occupation).lower()}.\n"
        f"  save_coherence  = .{str(with_coherence).lower()}.\n"
        "/\n"
    )
    # log file named `run` (no extension), like the production runs
    (run_dir / "run").write_text(
        "[synthetic] omega0 = 0.01425\n"
        "[synthetic] T_total : 42.696\n"
        "[synthetic] nt = 600\n"
    )


def write_synthetic_band_path(path: Path, n_k: int = 80, n_bands: int = 8) -> None:
    k = np.linspace(0.0, 1.0, n_k)
    cols = [k]
    for b in range(n_bands):
        cols.append(np.cos(np.pi * k) * 0.3 + 0.4 * b - 1.0)
    np.savetxt(path, np.column_stack(cols))


def main(argv: list[str] | None = None) -> int:
    import convert_sbe_run as cv

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path,
                   default=REPO / "data" / "samples" / "demo_bundle_minimal")
    args = p.parse_args(argv)

    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "synthetic_run"
        band_path = Path(td) / "wannier" / "CrI3_band.dat"
        band_path.parent.mkdir(parents=True)
        write_synthetic_run(run_dir)
        write_synthetic_band_path(band_path)

        return cv.main([
            "--run-dir", str(run_dir),
            "--band-path", str(band_path),
            "--out-dir", str(args.out_dir),
            "--dataset-name", "synthetic_demo_bundle_v0",
            "--max-points-current", "300",
            "--max-points-spectrum", "200",
            "--selected-bands", "3:7",
            "--max-grid", "8",
            "--max-occ-snapshots", "4",
            "--source-class", "Model-based",
            "--confidence",
            "synthetic demo bundle; curves are illustrative only, do not use as physical references",
        ])


if __name__ == "__main__":
    raise SystemExit(main())
