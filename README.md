# Visual-HHG-Research — HHG-XR Lab

An early-stage research-visualization project that turns solid-state
**high-harmonic generation (HHG)** outputs from a Wannier-SBE solver
into a clean, sanitized, Unreal-friendly data bundle.

The working name of the project is **HHG-XR Lab**.

> Status: v0 — data pipeline and provenance scaffolding. **No XR build yet.**

---

## What this repository is

This repository is **not** a real-time SBE solver and **not** a full XR
application. It is the data and documentation layer that sits between:

```
solid-state SBE solver outputs   →   sanitized demo bundle   →   Unreal / XR prototypes
        (Jt.dat, HHG.dat, ...)        (data_small.json, manifest.json, quicklook.png)
```

The current target material is **bilayer CrI3 (AFM)** with a Wannier-SBE
model in the `lg_cov` gauge.

## What this repository is *not* (yet)

- Not a real-time SBE solver
- Not a finished Unreal/XR experience
- Not a host for raw `*.dat`, `*.tb`, `*.hr` Wannier/TB files
- Not a place to commit private absolute filesystem paths

See [PLAN.md](./PLAN.md) for the full scope and the v0 non-goals.

---

## Repository layout

```
Visual-HHG-Research/
  README.md
  PLAN.md
  .gitignore
  .gitattributes

  docs/
    DATA_SCHEMA.md          # manifest.json + data_small.json schema
    PHYSICS_PROVENANCE.md   # provenance labels and what is real vs. reconstructed
    UNREAL_IMPORT.md        # how an Unreal client reads the bundle
    RHO_EXPORT_SPEC.md      # future solver export spec for rho(k,t)
    ROADMAP.md              # phased roadmap

  tools/
    convert_sbe_run.py      # raw .dat -> data_small.json + manifest.json
    sanitize_manifest.py    # strip private absolute paths from any manifest
    make_quicklook.py       # 4-panel preview PNG
    validate_demo_bundle.py # schema + safety checks on a bundle

  configs/
    demo_lgcov_k40_nb104.sample.yaml

  data/
    README.md
    samples/
      README.md
      demo_bundle_minimal/
        manifest.json
        data_small.json
        quicklook_summary.png
        README.md

  tests/
    test_schema.py
    test_converter_with_synthetic_data.py

  unreal/
    README.md               # target prototype description; no project yet
```

---

## Quick start

### 1. Convert a local SBE run into a sanitized bundle

```bash
python tools/convert_sbe_run.py \
  --run-dir   "<LOCAL_SBE_RUN_DIR>" \
  --band-path "<LOCAL_WANNIER_DIR>/CrI3_band.dat" \
  --out-dir   "data/samples/demo_bundle_minimal" \
  --max-points-current 1200 \
  --max-points-spectrum 800 \
  --selected-bands 80:90
```

This produces:

```
data/samples/demo_bundle_minimal/manifest.json
data/samples/demo_bundle_minimal/data_small.json
data/samples/demo_bundle_minimal/quicklook_summary.png
```

### 2. Sanitize an existing manifest that leaks paths

```bash
python tools/sanitize_manifest.py \
  --in  manifest_hhgxr_v0.json \
  --out data/samples/demo_bundle_minimal/manifest.json
```

This replaces absolute Windows/Linux paths with placeholders such as
`<LOCAL_SBE_RUN_DIR>` and `<LOCAL_WANNIER_DIR>`.

### 3. Validate a bundle before committing

```bash
python tools/validate_demo_bundle.py \
  --bundle data/samples/demo_bundle_minimal
```

Validation checks:

- JSON files load
- required keys exist
- arrays have matching lengths
- no absolute private paths leaked
- `field_source` is explicitly labeled
- `missing_modules` is present and non-hidden
- no large raw `.dat`/`.npz`/`.tb` files inside the bundle directory

---

## Data and provenance policy (short form)

1. **Never** commit raw scientific outputs (`*.dat`, `*.tb`, `*.hr`,
   `*.h5`, `*.npy`, large `*.npz`) to this repository.
2. **Never** commit private absolute filesystem paths inside public
   manifest files.
3. Always tag each physical quantity with a provenance label from
   [`docs/PHYSICS_PROVENANCE.md`](./docs/PHYSICS_PROVENANCE.md).
4. If `E(t)` / `A(t)` are reconstructed from `input.nml` (plus
   `mod_laser.f90`, `mod_params.f90`) and cross-checked against `run.log`,
   tag them as `reconstructed_from_input_nml_not_raw_output`. Tag them
   `raw_solver_output` only when the solver itself emits `Et.dat` /
   `At.dat`. Older bundles using `_unverified` / `_verified` labels
   should be regenerated.

## Priority order

```
physics provenance
  > safe repository hygiene
  > reproducible data conversion
  > small Unreal-readable demo bundle
  > quicklook validation
  > documentation
  > desktop Unreal prototype
  > Niagara / XR / MCP later
```

The point of this repository is reliable physics-to-Unreal data flow.
Visual polish comes after the data pipeline is trustworthy.
