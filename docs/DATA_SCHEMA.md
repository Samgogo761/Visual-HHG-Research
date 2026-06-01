# DATA_SCHEMA.md — HHG-XR Lab demo bundle

This document defines the on-disk schema for an HHG-XR Lab **demo
bundle**: the small, sanitized, Unreal-friendly artifact produced by
`tools/convert_sbe_run.py` from a Wannier-SBE solver run.

Schema id (current): **`hhgxr-demo-bundle-v0`**

A demo bundle is a single directory containing:

```
demo_bundle_minimal/
  manifest.json
  data_small.json
  quicklook_summary.png
  data_arrays.npz        # OPTIONAL, only if small
  README.md              # OPTIONAL, human-readable notes
```

---

## 1. `manifest.json`

`manifest.json` is the index. It is always present, always sanitized,
and never embeds private absolute paths.

### 1.1 Required top-level keys

```json
{
  "schema": "hhgxr-demo-bundle-v0",
  "dataset_name": "string",
  "physics_provenance": { ... },
  "units": { ... },
  "dimensions": { ... },
  "available_modules": [ ... ],
  "missing_modules":  [ ... ],
  "files": { ... }
}
```

### 1.2 `physics_provenance`

```json
"physics_provenance": {
  "source_class": "Data-driven",
  "material":     "bilayer CrI3 AFM",
  "model":        "Wannier-SBE",
  "gauge_method": "lg_cov",
  "confidence":   "research-output, visualization-ready for J(t)/HHG/bands; field reconstruction pending verification"
}
```

`source_class` must be one of the four provenance labels defined in
[`PHYSICS_PROVENANCE.md`](./PHYSICS_PROVENANCE.md):

- `Data-driven`
- `Model-based`
- `Literature-reproduced`
- `Conceptual-only`

### 1.3 `units`

```json
"units": {
  "time":    "fs",
  "current": "a.u.",
  "energy":  "eV",
  "k":       "1/bohr",
  "omega":   "a.u.",
  "hhg":     "|J(omega)|^2 solver scaling"
}
```

### 1.4 `dimensions`

Original (pre-downsampling) array dimensions from the source run:

```json
"dimensions": {
  "nt":      5045,
  "nkx":     40,
  "nky":     40,
  "n_bands": 104
}
```

### 1.5 `available_modules` / `missing_modules`

Each entry is a short identifier of a physical module that may be present
or absent in `data_small.json`. Missing modules must be enumerated, not
hidden.

Recommended identifiers:

```
current_time_series
hhg_spectrum
band_grid
band_path
current_decomposition
valley_current
field_time_series
k_space_occupation
rho_k_t
production_lg_cov_berry_curvature
solver_output_Et_At
```

### 1.6 `files`

Relative paths inside the bundle directory only:

```json
"files": {
  "data_small": "data_small.json",
  "quicklook":  "quicklook_summary.png",
  "data_arrays": "data_arrays.npz"
}
```

### 1.7 Optional `source_paths` (sanitized)

If the manifest records where the data came from, use placeholders:

```json
"source_paths": {
  "run_dir":   "<LOCAL_SBE_RUN_DIR>/lgcov_k40_nb104",
  "Jt":        "<LOCAL_SBE_RUN_DIR>/lgcov_k40_nb104/Jt.dat",
  "HHG":       "<LOCAL_SBE_RUN_DIR>/lgcov_k40_nb104/HHG.dat",
  "bands":     "<LOCAL_SBE_RUN_DIR>/lgcov_k40_nb104/bands.dat",
  "band_path": "<LOCAL_WANNIER_DIR>/CrI3_band.dat"
}
```

A manifest with a literal `C:\...`, `D:\...`, `/home/<user>/...`,
`/mnt/...`, or `\\server\\share` segment fails validation.

---

## 2. `data_small.json`

`data_small.json` carries the actual arrays in a JSON-friendly,
**downsampled** form suitable for Unreal/Niagara prototyping.

### 2.1 Top-level keys (all optional, presence advertised by manifest)

```json
{
  "time_series":         { ... },
  "spectrum":            { ... },
  "band_path":           { ... },
  "band_grid_preview":   { ... },
  "field":               { ... }
}
```

### 2.2 `time_series`

```json
"time_series": {
  "time_fs":  [...],
  "Jx":       [...],
  "Jy":       [...],
  "Jx_intra": [...],
  "Jy_intra": [...],
  "Jx_inter": [...],
  "Jy_inter": [...],
  "Jx_K":     [...],
  "Jy_K":     [...],
  "Jx_Kp":    [...],
  "Jy_Kp":    [...],
  "eta_x":    [...],
  "eta_y":    [...]
}
```

All arrays in `time_series` must have the same length as `time_fs`.

### 2.3 `spectrum`

```json
"spectrum": {
  "harmonic_order": [...],
  "omega_au":       [...],
  "HHG_x":          [...],
  "HHG_y":          [...],
  "HHG_total":      [...]
}
```

All arrays in `spectrum` must have the same length.

### 2.4 `band_path`

```json
"band_path": {
  "k_path":    [...],          // shape: [n_k_path]
  "energy_eV": [[...], ...]    // shape: [n_k_path][n_bands_selected]
}
```

### 2.5 `band_grid_preview`

A small slice of the band grid suitable for a quick 3D preview:

```json
"band_grid_preview": {
  "kx":                    [...],   // length nkx
  "ky":                    [...],   // length nky
  "selected_band_indices": [...],
  "energies_eV":           [[[...], ...], ...]  // shape: [n_sel][nkx][nky]
}
```

### 2.6 `field`

The field block now always carries both `E(t)` and `A(t)`. When
`source = "raw_solver_output"`, the arrays come directly from the
solver's `Et.dat` / `At.dat` (column layout
`# it time_fs Ex_au Ey_au Ax_au Ay_au`). When `source` is the
reconstructed label, the arrays come from `input.nml` +
`mod_laser.f90` + `mod_params.f90` and are cross-checked against
`omega0`, `T_total`, `nt` in `run.log`.

Raw solver form:

```json
"field": {
  "time_fs": [...],
  "Ex": [...], "Ey": [...],
  "Ax": [...], "Ay": [...],
  "source": "raw_solver_output",
  "raw_source_file":    "<LOCAL_SBE_RUN_DIR>/Et.dat",
  "raw_source_columns": "it, time_fs, Ex_au, Ey_au, Ax_au, Ay_au"
}
```

Reconstructed form (current first-demo baseline):

```json
"field": {
  "time_fs": [...],
  "Ex": [...], "Ey": [...],
  "Ax": [...], "Ay": [...],
  "source": "reconstructed_from_input_nml_not_raw_output",
  "reconstructed_from":  ["input.nml", "mod_laser.f90", "mod_params.f90"],
  "cross_checked_with":  ["run.log"],
  "cross_check":         {"omega0_au": "match", "T_total_fs": "match", "nt": "match"},
  "note": "Reconstructed from solver inputs and cross-checked against run.log; not raw solver output."
}
```

`source` is required and must be one of:

```
raw_solver_output
reconstructed_from_input_nml_not_raw_output
unavailable
```

Legacy labels (accepted by the validator with a warning, used by older
bundles before the audit script existed):

```
solver_native                              -> alias for raw_solver_output
reconstructed_from_input_nml_verified      -> pre-audit, deprecated
reconstructed_from_input_nml_unverified    -> pre-audit, deprecated
```

Upgrade path: any bundle that still uses an `_unverified` or `_verified`
label should be regenerated with `tools/convert_sbe_run.py`. When the
solver starts emitting `Et.dat` / `At.dat`, the converter will pick them
up automatically and switch the label to `raw_solver_output` with no CLI
change required.

---

## 3. Optional `data_arrays.npz`

Only generate `data_arrays.npz` if every contained array is small enough
to be safely shared. The default for the publicly committed sample
bundle is **no** `data_arrays.npz`.

If present, recommended keys mirror `data_small.json` but at full
resolution:

```
time_fs, Jx, Jy, Jx_intra, Jy_intra, Jx_inter, Jy_inter,
Jx_K, Jy_K, Jx_Kp, Jy_Kp,
omega_au, HHG_x, HHG_y, HHG_total,
kx, ky, energies_eV
```

---

## 4. Downsampling policy

`tools/convert_sbe_run.py` accepts:

```
--max-points-current   N    # default 1200
--max-points-spectrum  N    # default 800
--selected-bands       a:b  # band index slice for the grid preview
```

Downsampling is uniform stride over the original sample index, not a
Fourier filter. The original full-resolution dimensions are recorded in
`manifest.dimensions`, so downstream consumers always know what was
truncated.

---

## 5. Why raw `.dat` and `.tb` files are not committed

1. `CrI3_tb.dat` and `CrI3_hr.dat` can be ~1 GB.
2. Raw solver `.dat` outputs are not yet provenance-clean and may carry
   solver-specific scaling that downstream consumers should not silently
   trust.
3. Public sample bundles must remain small and reviewable.
4. GitHub is not the right host for production solver outputs; those
   should live on the SBE/HPC side and be referenced by sanitized
   metadata only.

For ad hoc large transfers, prefer Git LFS or out-of-band sharing rather
than direct commits. Even with LFS, the safety checks in
`tools/validate_demo_bundle.py` still apply.
