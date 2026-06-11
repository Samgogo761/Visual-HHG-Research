# PLAN.md — HHG-XR Lab / Visual-HHG-Research v0

## 0. Mission

Build the first **data-driven scientific visualization pipeline** for a
future Unreal/XR project that visualizes solid-state high-harmonic
generation (HHG), starting from existing CrI3 SBE/Wannier outputs.

The immediate goal is **not** to build a full XR app or a real-time SBE
solver. The immediate goal is to:

1. organize the GitHub repository;
2. convert existing SBE `.dat` outputs into Unreal-friendly demo data;
3. preserve physics provenance clearly;
4. create a minimal desktop Unreal prototype path;
5. prepare for later k-space occupation / density-matrix visualization.

Working project name: **HHG-XR Lab**.

---

## 1. Current data baseline

### 1.1 First canonical demo dataset

```
lg_cov_k40_nb104_T2_0p5cycle (+N benchmark)
```

Source directory (local, **never committed**):

```
<LOCAL_SBE_RUN_DIR>/lgcov_k40_nb104/
```

Core files used by the converter:

```
input.nml
run.log
Jt.dat
HHG.dat
bands.dat
Jt_decomposed.dat
Jt_valley.dat
```

Optional k-path band file (Wannier export):

```
<LOCAL_WANNIER_DIR>/CrI3_band.dat
```

### 1.2 Known array dimensions

```
Jt.dat:             5045 x 4
HHG.dat:            2523 x 5
bands.dat:          40 x 40 x 104
Jt_decomposed.dat:  5045 x 8
Jt_valley.dat:      5045 x 8
```

Known units:

```
time:        fs
current J:   a.u.
band energy: eV
kx, ky:      1/bohr
omega:       a.u.
HHG:         |J(omega)|^2 with solver-specific scaling
```

### 1.2b Newer verify_obs run (2026-06-10)

A second baseline now exists with the new observables enabled:

```
output_verify_obs_nb112_T2_0p5cycle/   (gauge_method = matrix_vg, nkx=nky=46, bands 1..112, nv=84)
  bands.dat              (~11.7 MB, long format: ikx iky n E kx ky)
  HHG.dat / HHG_spin.dat
  Jt.dat / Jt_decomposed.dat / Jt_valley.dat / Jt_spin.dat
  quantum_geometry.dat   (~23.6 MB: ikx iky band kx ky E Omega gxx gyy gxy valley)
  input.nml / run        (log file named `run`, no extension)
```

All time-series files carry a leading `it` index column; the converter
handles both this and the legacy time-first layout.

### 1.3 Missing data (current)

```
E(t) / A(t) original solver output        -> small solver patch, see docs/SOLVER_EXPORT_REQUESTS.md Item 1
interband coherence |rho_mn(k,t)|         -> small solver patch, Item 2
full complex density matrix rho_mn(k,t)   -> intentionally not exported (size)
```

**Resolved since v0:** k-space occupation `rho_nn(k,t)` is NOT missing
capability — the solver already implements Tier-0 snapshots
(`occupation_kt.dat`, `occupation_band_kt.dat`) behind the
`save_occupation` / `occ_band_resolved` flags in `&output`. The
verify_obs run simply had `save_occupation = .false.`. Re-running with
the flags on requires no code change (Item 0 in
`docs/SOLVER_EXPORT_REQUESTS.md`). Quantum geometry (Berry curvature +
metric + valley map) is likewise now produced by `save_geometry`.

Field reconstruction history:

- v0.1 of the audit script produced a delta-spike `E(t)`. That
  reconstruction was labeled `reconstructed_from_input_nml_unverified`.
- The audit script was fixed locally. It now reproduces a 3200 nm,
  4-cycle, ~42.70 fs cos²-envelope pulse, validated against
  `mod_laser.f90`, `mod_params.f90`, and the `omega0` / `T_total` / `nt`
  values in `run.log`.
- The reconstructed field is therefore now labeled
  `reconstructed_from_input_nml_not_raw_output`: visualization-ready,
  but still not the solver's native `Et.dat` / `At.dat` output.
- When the solver finally emits `Et.dat` / `At.dat` directly, the
  converter picks them up automatically and the label flips to
  `raw_solver_output` with no code change required.

### 1.4 Data policy

Never commit:

```
*.dat raw production files
CrI3_tb.dat
CrI3_hr.dat
large Wannier/TB files
server-downloaded raw datasets
private local path inventories
```

Use sanitized sample data and metadata only.

---

## 2. Non-goals for v0

Do **not** implement yet:

1. full Unreal XR interaction;
2. real-time SBE solving inside Unreal;
3. direct import of large `CrI3_tb.dat` into Unreal;
4. MCP integration;
5. quantum-light / TMSV / BSV module;
6. k-space occupation visualization using fake data marked as real;
7. polished visual effects before the data pipeline works.

v0 is about **data integrity and a clean development foundation.**

---

## 3. Task order

Strict execution order:

1. Stabilize the GitHub repository (skeleton, `.gitignore`,
   `.gitattributes`, `README.md`, `PLAN.md`).
2. Implement `tools/convert_sbe_run.py` — parses `Jt.dat`, `HHG.dat`,
   `bands.dat`, `Jt_decomposed.dat`, `Jt_valley.dat`, `input.nml`, and
   optionally `CrI3_band.dat`. Outputs `manifest.json`, `data_small.json`,
   and optionally `data_arrays.npz`.
3. Implement `tools/sanitize_manifest.py` — strips private absolute paths
   and replaces them with placeholders such as `<LOCAL_SBE_RUN_DIR>` and
   `<LOCAL_WANNIER_DIR>`.
4. Implement `tools/validate_demo_bundle.py` — checks schema, key
   completeness, array length consistency, absent absolute paths, and
   file size bounds.
5. Implement `tools/make_quicklook.py` — 4-panel preview PNG
   (band path, E(t) if available, J(t), HHG).
6. Documentation: `docs/DATA_SCHEMA.md`, `docs/PHYSICS_PROVENANCE.md`,
   `docs/RHO_EXPORT_SPEC.md`, `docs/UNREAL_IMPORT.md`,
   `docs/ROADMAP.md`.
7. Sanitized minimal demo bundle in
   `data/samples/demo_bundle_minimal/`.
8. Tests in `tests/`.
9. Only after 1-8 are stable: start the desktop Unreal prototype that
   reads `data_small.json`.

---

## 4. Acceptance criteria

The v0 phase is complete when:

1. `README.md` clearly states the project intent.
2. `PLAN.md` exists in the repository.
3. `tools/convert_sbe_run.py` exists with a working CLI.
4. `tools/sanitize_manifest.py` exists with a working CLI.
5. `tools/validate_demo_bundle.py` passes on the sample bundle.
6. `data/samples/demo_bundle_minimal/manifest.json` exists.
7. `data/samples/demo_bundle_minimal/data_small.json` exists.
8. `data/samples/demo_bundle_minimal/quicklook_summary.png` exists.
9. No raw `.dat`, `.tb`, `.hr`, `.h5`, `.npy`, or large `.npz` files are
   committed.
10. No private absolute local paths appear in public sample manifests.
11. Missing physics modules are explicitly labeled rather than hidden.

---

## 5. Pre-push checklist

```bash
git status
git diff --stat
git ls-files | grep -E '\.(dat|tb|hr|h5|hdf5|npy|npz)$'
```

If the last command lists raw scientific files, stop and fix before
pushing.

---

## 6. Questions to ask the user if blocked

1. The local source data path does not exist.
2. The converter cannot parse `input.nml`.
3. Reconstructed `E(t)` does not resemble the configured pulse
   (e.g. 4-cycle 3200 nm).
4. `CrI3_band.dat` format is ambiguous.
5. A file larger than 10 MB would need to be committed.
6. A public manifest would expose private paths.
7. A real Unreal project should be created in this repository now.

---

## 7. Priority order

```
1. CC finishes GitHub repo skeleton and convert_sbe_run.py
2. The current fixed quicklook / sanitized manifest is the baseline
3. data/samples/demo_bundle_minimal/ is regenerated from current scripts
4. validate_demo_bundle.py: no private paths, no large blobs, no missing keys
5. Desktop Unreal reads data_small.json and renders J(t) / HHG / band path
6. Solver emits Et.dat / At.dat -> field label flips to raw_solver_output
7. Design rho(k,t) snapshot export per docs/RHO_EXPORT_SPEC.md
8. Only then: Niagara / XR / MCP
```

Underlying ordering principle:

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
