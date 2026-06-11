"""Converter pipeline test using synthetic .dat files in the REAL solver formats.

The synthetic writers live in tools/make_synthetic_bundle.py (single
source of truth, also used to regenerate the committed sample bundle).
They mimic the Quantum-light solver output layouts: leading `it` index
column on time series, long-format bands.dat with `# nkx= nky= n_trunc=`
header, Jt_spin / HHG_spin / quantum_geometry / occupation_kt files, and
a log file named `run`.

Run with:
    pytest tests/test_converter_with_synthetic_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import convert_sbe_run as cv  # noqa: E402
import validate_demo_bundle as vd  # noqa: E402
import sanitize_manifest as san  # noqa: E402
from make_synthetic_bundle import (  # noqa: E402
    write_synthetic_run,
    write_synthetic_band_path,
)


def _convert(run_dir: Path, out_dir: Path, band_path: Path | None = None,
             extra: list[str] | None = None) -> int:
    argv = [
        "--run-dir", str(run_dir),
        "--out-dir", str(out_dir),
        "--max-points-current", "300",
        "--max-points-spectrum", "200",
        "--selected-bands", "3:7",
        "--max-grid", "8",
        "--max-occ-snapshots", "4",
        "--dataset-name", "synthetic_test_dataset",
    ]
    if band_path is not None:
        argv += ["--band-path", str(band_path)]
    return cv.main(argv + (extra or []))


def test_converter_end_to_end(tmp_path: Path) -> None:
    run_dir = tmp_path / "synthetic_run"
    band_path = tmp_path / "wannier" / "CrI3_band.dat"
    band_path.parent.mkdir(parents=True)
    write_synthetic_run(run_dir, nt=600, nkx=8, nky=8, n_bands=12)
    write_synthetic_band_path(band_path, n_k=80, n_bands=10)

    out_dir = tmp_path / "bundle_out"
    assert _convert(run_dir, out_dir, band_path) == 0

    issues = vd.validate(out_dir, max_mb=10, total_max_mb=25)
    assert issues.ok, "\n".join(issues.errors)

    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert manifest["schema"] == "hhgxr-demo-bundle-v0"
    for mod in ("current_time_series", "hhg_spectrum", "band_grid",
                "current_decomposition", "valley_current",
                "spin_current", "hhg_spin", "quantum_geometry",
                "k_space_occupation"):
        assert mod in manifest["available_modules"], f"{mod} should be available"
    for mod in ("interband_coherence_norm", "rho_k_t_full_density_matrix",
                "solver_output_Et_At"):
        assert mod in manifest["missing_modules"], f"{mod} should be missing"

    # gauge label comes from input.nml &method when not overridden
    assert manifest["physics_provenance"]["gauge_method"] == "matrix_vg"
    assert manifest["dimensions"]["n_valence"] == 8

    src = manifest.get("source_paths") or {}
    for v in src.values():
        assert v.startswith("<LOCAL_"), f"source_paths value not sanitized: {v!r}"


def test_time_axis_is_time_not_step_index(tmp_path: Path) -> None:
    """Real Jt.dat starts with an `it` index column; time_fs must come
    from column 1, not column 0. The synthetic time grid starts at
    -20 fs, so index/time confusion is unmistakable."""
    run_dir = tmp_path / "run"
    write_synthetic_run(run_dir, nt=400, nkx=6, nky=6, n_bands=8)
    out_dir = tmp_path / "bundle"
    assert _convert(run_dir, out_dir) == 0

    ds = json.loads((out_dir / "data_small.json").read_text())
    t = ds["time_series"]["time_fs"]
    assert t[0] == pytest.approx(-20.0), "time_fs[0] looks like a step index, not time"
    assert "eta_x" in ds["time_series"] and "eta_y" in ds["time_series"]
    assert "Jx_spin" in ds["time_series"]


def test_bands_long_format_and_geometry(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    write_synthetic_run(run_dir, nt=300, nkx=6, nky=6, n_bands=10)
    out_dir = tmp_path / "bundle"
    assert _convert(run_dir, out_dir) == 0

    ds = json.loads((out_dir / "data_small.json").read_text())
    bgp = ds["band_grid_preview"]
    assert bgp["band_index_base"] == 1
    assert bgp["selected_band_indices"] == [3, 4, 5, 6]
    assert "kx_grid" in bgp and "ky_grid" in bgp, "long format must emit 2D grids"
    n_sel = len(bgp["selected_band_indices"])
    assert len(bgp["energies_eV"]) == n_sel

    qgp = ds["quantum_geometry_preview"]
    assert "berry_curvature_au" in qgp and "trace_quantum_metric_au" in qgp
    assert "valley_id" in qgp
    assert "PT-symmetric" in qgp["note"]


def test_occupation_preview(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    write_synthetic_run(run_dir, nt=300, nkx=6, nky=6, n_bands=8, n_occ_snapshots=6)
    out_dir = tmp_path / "bundle"
    assert _convert(run_dir, out_dir) == 0

    ds = json.loads((out_dir / "data_small.json").read_text())
    occ = ds["occupation_preview"]
    assert 2 <= len(occ["snapshots"]) <= 5  # max-occ-snapshots=4 (+last)
    first = occ["snapshots"][0]
    assert np.allclose(np.asarray(first["delta_n_cond"]), 0.0), \
        "delta_n_cond at the first snapshot must vanish by construction"
    rows = len(occ["kx_grid"])
    assert len(first["n_cond"]) == rows


def test_no_occupation_means_module_missing(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    write_synthetic_run(run_dir, nt=300, nkx=6, nky=6, n_bands=8,
                        with_occupation=False)
    out_dir = tmp_path / "bundle"
    assert _convert(run_dir, out_dir) == 0
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert "k_space_occupation" in manifest["missing_modules"]
    assert "k_space_occupation" not in manifest["available_modules"]


def test_converter_promotes_to_raw_when_Et_dat_present(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_with_raw_field"
    write_synthetic_run(run_dir, nt=400, nkx=6, nky=6, n_bands=8)
    t = np.linspace(-10.0, 10.0, 400)
    ex = 0.005 * np.cos(0.5 * t) * np.exp(-0.01 * t**2)
    ey = np.zeros_like(t)
    ax = -np.cumsum(np.r_[0, 0.5 * (ex[:-1] + ex[1:])] * np.r_[0, np.diff(t)])
    ay = np.zeros_like(t)
    it = np.arange(1, 401)
    np.savetxt(run_dir / "Et.dat", np.column_stack([it, t, ex, ey, ax, ay]),
               header="it  time(fs)  Ex(a.u.)  Ey(a.u.)  Ax(a.u.)  Ay(a.u.)")

    out_dir = tmp_path / "bundle_out_raw"
    assert _convert(run_dir, out_dir) == 0

    manifest = json.loads((out_dir / "manifest.json").read_text())
    data_small = json.loads((out_dir / "data_small.json").read_text())
    assert data_small["field"]["source"] == "raw_solver_output"
    assert "solver_output_Et_At" in manifest["available_modules"]
    assert "solver_output_Et_At" not in manifest["missing_modules"]
    assert data_small["field"]["raw_source_file"].startswith("<LOCAL_SBE_RUN_DIR>")

    issues = vd.validate(out_dir, max_mb=10, total_max_mb=25)
    assert issues.ok, "\n".join(issues.errors)


def test_sanitize_manifest_replaces_absolute_paths(tmp_path: Path) -> None:
    bad = {
        "schema": "hhgxr-demo-bundle-v0",
        "files": {
            "Jt":        r"C:\Users\26507\Documents\sbe\new_sbe\lgcov_k40_nb104\Jt.dat",
            "HHG":       "/home/jiashen/sbe/lgcov_k40_nb104/HHG.dat",
            "band_path": r"\\server\share\wannier\CrI3_band.dat",
        },
    }
    inp = tmp_path / "manifest_hhgxr_v0.json"
    out = tmp_path / "manifest.sanitized.json"
    inp.write_text(json.dumps(bad))

    rc = san.main(["--in", str(inp), "--out", str(out)])
    assert rc == 0
    cleaned = json.loads(out.read_text())
    for v in cleaned["files"].values():
        assert v.startswith("<LOCAL_"), v


def test_validator_flags_private_paths(tmp_path: Path) -> None:
    bundle = tmp_path / "leaky"
    bundle.mkdir()
    manifest = {
        "schema": "hhgxr-demo-bundle-v0",
        "dataset_name": "x",
        "physics_provenance": {"source_class": "Data-driven"},
        "units": {}, "dimensions": {}, "available_modules": [], "missing_modules": [],
        "files": {
            "data_small": "data_small.json",
            "quicklook":  "quicklook_summary.png",
            "Jt":         r"C:\Users\leak\Jt.dat",
        },
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    (bundle / "data_small.json").write_text(json.dumps({"field": {"source": "unavailable"}}))
    (bundle / "quicklook_summary.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    issues = vd.validate(bundle, max_mb=10, total_max_mb=25)
    assert not issues.ok
    assert any("private path leak" in e for e in issues.errors)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
