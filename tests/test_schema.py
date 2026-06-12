"""Schema sanity tests for the committed demo bundle.

Run with:
    pytest tests/test_schema.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "data" / "samples" / "demo_bundle_minimal"

sys.path.insert(0, str(REPO / "tools"))

import validate_demo_bundle as vd  # noqa: E402


def test_bundle_files_exist() -> None:
    assert (BUNDLE / "manifest.json").is_file()
    assert (BUNDLE / "data_small.json").is_file()
    assert (BUNDLE / "quicklook_summary.png").is_file()


def test_manifest_schema_id() -> None:
    manifest = json.loads((BUNDLE / "manifest.json").read_text())
    assert manifest["schema"] == "hhgxr-demo-bundle-v0"


def test_manifest_required_keys() -> None:
    manifest = json.loads((BUNDLE / "manifest.json").read_text())
    for key in ("dataset_name", "physics_provenance", "units", "dimensions",
                "available_modules", "missing_modules", "files"):
        assert key in manifest, f"missing manifest key: {key}"


def test_missing_modules_is_explicit() -> None:
    manifest = json.loads((BUNDLE / "manifest.json").read_text())
    assert isinstance(manifest["missing_modules"], list)
    for must in ("rho_k_t_full_density_matrix",):
        assert must in manifest["missing_modules"], (
            f"v0 demo must declare {must} as missing; do not hide it"
        )


def test_occupation_module_in_sample_bundle() -> None:
    """The committed synthetic bundle ships an occupation_preview so the
    Unreal loader can be developed against the k_space_occupation module
    before the real solver rerun lands."""
    manifest = json.loads((BUNDLE / "manifest.json").read_text())
    data_small = json.loads((BUNDLE / "data_small.json").read_text())
    assert "k_space_occupation" in manifest["available_modules"]
    occ = data_small.get("occupation_preview") or {}
    assert occ.get("snapshots"), "occupation_preview.snapshots must be non-empty"
    assert "definition" in occ


def test_coherence_module_in_sample_bundle() -> None:
    """Item 2 (coherence_kt.dat) shipped on the solver side; the sample
    bundle must light it up so the Unreal loader has something to
    target before the production rerun."""
    manifest = json.loads((BUNDLE / "manifest.json").read_text())
    data_small = json.loads((BUNDLE / "data_small.json").read_text())
    assert "interband_coherence_norm" in manifest["available_modules"]
    coh = data_small.get("coherence_preview") or {}
    assert coh.get("snapshots"), "coherence_preview.snapshots must be non-empty"
    assert "coherence_norm" in coh["snapshots"][0]


def test_field_source_label_is_allowed() -> None:
    data_small = json.loads((BUNDLE / "data_small.json").read_text())
    field = data_small.get("field") or {}
    assert field.get("source") in vd.ALLOWED_FIELD_SOURCES


def test_field_uses_current_label_vocabulary() -> None:
    data_small = json.loads((BUNDLE / "data_small.json").read_text())
    src = (data_small.get("field") or {}).get("source")
    assert src in {
        "raw_solver_output",
        "reconstructed_from_input_nml_not_raw_output",
        "unavailable",
    }, f"committed bundle still uses legacy label {src!r}; regenerate it"


def test_field_block_carries_Ex_Ey_Ax_Ay() -> None:
    data_small = json.loads((BUNDLE / "data_small.json").read_text())
    field = data_small.get("field") or {}
    if field.get("source") == "unavailable":
        return
    n = len(field.get("time_fs") or [])
    for k in ("Ex", "Ey", "Ax", "Ay"):
        v = field.get(k) or []
        assert isinstance(v, list) and len(v) == n, f"field.{k} length {len(v)} != time_fs {n}"


def test_bundle_has_no_private_paths() -> None:
    manifest = json.loads((BUNDLE / "manifest.json").read_text())
    data_small = json.loads((BUNDLE / "data_small.json").read_text())
    assert vd.find_private_paths(manifest) == []
    assert vd.find_private_paths(data_small) == []


def test_full_validator_passes() -> None:
    issues = vd.validate(BUNDLE, max_mb=10, total_max_mb=25)
    assert issues.ok, "\n".join(issues.errors)
