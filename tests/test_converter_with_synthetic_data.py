"""Converter pipeline test using synthetic .dat files.

We do not commit real SBE outputs, so this test materializes synthetic
files in a temporary directory, runs convert_sbe_run.main(), and asserts
that the resulting bundle passes validate_demo_bundle.validate().

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


def _write_synthetic_run(run_dir: Path, nt: int = 600, nkx: int = 8, nky: int = 8, n_bands: int = 12) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    t = np.linspace(-20.0, 20.0, nt)
    jx = np.sin(0.5 * t) * np.exp(-0.005 * t**2)
    jy = np.cos(0.5 * t) * np.exp(-0.005 * t**2)
    np.savetxt(run_dir / "Jt.dat", np.column_stack([t, jx, jy, np.zeros_like(t)]))

    np.savetxt(run_dir / "Jt_decomposed.dat",
               np.column_stack([t, 0.6*jx, 0.6*jy, 0.4*jx, 0.4*jy, jx, jy, 0*jx]))
    np.savetxt(run_dir / "Jt_valley.dat",
               np.column_stack([t, 0.5*jx, 0.5*jy, 0.5*jx, 0.5*jy, jx, jy, 0*jx]))

    n_omega = 200
    order = np.arange(1, n_omega + 1)
    omega_au = 0.057 * order
    spec_x = 1.0 / (1.0 + (order - 11)**2)
    spec_y = 0.6 * spec_x
    spec_t = spec_x + spec_y
    np.savetxt(run_dir / "HHG.dat",
               np.column_stack([order, omega_au, spec_x, spec_y, spec_t]))

    kx = np.linspace(-0.5, 0.5, nkx)
    ky = np.linspace(-0.5, 0.5, nky)
    rows = []
    for i, kxi in enumerate(kx):
        for j, kyj in enumerate(ky):
            energies = [0.5 * (kxi**2 + kyj**2) + 0.3 * b for b in range(n_bands)]
            rows.append([kxi, kyj, *energies])
    np.savetxt(run_dir / "bands.dat", np.array(rows))

    (run_dir / "input.nml").write_text(
        "&laser\n"
        "  lambda_nm = 3200.0,\n"
        "  n_cycles  = 4.0,\n"
        "  E0_au     = 0.005,\n"
        "/\n"
    )
    (run_dir / "run.log").write_text("synthetic test run\n")


def _write_synthetic_band_path(path: Path, n_k: int = 80, n_bands: int = 10) -> None:
    k = np.linspace(0.0, 1.0, n_k)
    cols = [k]
    for b in range(n_bands):
        cols.append(np.cos(np.pi * k) * 0.3 + 0.4 * b)
    np.savetxt(path, np.column_stack(cols))


def test_converter_end_to_end(tmp_path: Path) -> None:
    run_dir = tmp_path / "lgcov_k8_nb12_synthetic"
    band_path = tmp_path / "wannier" / "CrI3_band.dat"
    band_path.parent.mkdir(parents=True)
    _write_synthetic_run(run_dir, nt=600, nkx=8, nky=8, n_bands=12)
    _write_synthetic_band_path(band_path, n_k=80, n_bands=10)

    out_dir = tmp_path / "bundle_out"
    rc = cv.main([
        "--run-dir", str(run_dir),
        "--band-path", str(band_path),
        "--out-dir", str(out_dir),
        "--max-points-current", "300",
        "--max-points-spectrum", "200",
        "--selected-bands", "2:6",
        "--max-grid", "8",
        "--dataset-name", "synthetic_test_dataset",
    ])
    assert rc == 0

    assert (out_dir / "manifest.json").is_file()
    assert (out_dir / "data_small.json").is_file()

    issues = vd.validate(out_dir, max_mb=10, total_max_mb=25)
    assert issues.ok, "\n".join(issues.errors)

    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert manifest["schema"] == "hhgxr-demo-bundle-v0"
    assert "current_time_series" in manifest["available_modules"]
    assert "hhg_spectrum" in manifest["available_modules"]
    assert "band_grid" in manifest["available_modules"]
    assert "rho_k_t" in manifest["missing_modules"]

    src = manifest.get("source_paths") or {}
    for v in src.values():
        assert v.startswith("<LOCAL_") or v == "<LOCAL_SBE_RUN_DIR>", (
            f"source_paths value not sanitized: {v!r}"
        )

    data_small = json.loads((out_dir / "data_small.json").read_text())
    field = data_small.get("field") or {}
    assert field["source"] == "reconstructed_from_input_nml_not_raw_output"
    for k in ("Ex", "Ey", "Ax", "Ay"):
        assert k in field and len(field[k]) == len(field["time_fs"]), (
            f"field.{k} missing or wrong length"
        )
    assert field.get("reconstructed_from") == ["input.nml", "mod_laser.f90", "mod_params.f90"]
    assert "solver_output_Et_At" in manifest["missing_modules"]


def test_converter_promotes_to_raw_when_Et_dat_present(tmp_path: Path) -> None:
    run_dir = tmp_path / "lgcov_with_raw_field"
    _write_synthetic_run(run_dir, nt=400, nkx=6, nky=6, n_bands=8)
    t = np.linspace(-10.0, 10.0, 400)
    ex = 0.005 * np.cos(0.5 * t) * np.exp(-0.01 * t**2)
    ey = np.zeros_like(t)
    ax = -np.cumsum(np.r_[0, 0.5 * (ex[:-1] + ex[1:])] * np.r_[0, np.diff(t)])
    ay = np.zeros_like(t)
    it = np.arange(1, 401)
    np.savetxt(run_dir / "Et.dat", np.column_stack([it, t, ex, ey, ax, ay]),
               header="it time_fs Ex_au Ey_au Ax_au Ay_au")

    out_dir = tmp_path / "bundle_out_raw"
    rc = cv.main([
        "--run-dir", str(run_dir),
        "--out-dir", str(out_dir),
        "--max-points-current", "200",
        "--max-points-spectrum", "150",
        "--selected-bands", "1:4",
        "--max-grid", "6",
        "--dataset-name", "synthetic_raw_field_dataset",
    ])
    assert rc == 0

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
