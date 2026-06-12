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

### 1.2b verify_obs runs (2026-06)

Two solver baselines now exist:

```
output_verify_obs_nb112_T2_0p5cycle/   (matrix_vg, 46x46, T2_cycles=0.5)
  bands.dat                 (long format: ikx iky n E kx ky)
  HHG.dat / HHG_spin.dat
  Jt.dat / Jt_decomposed.dat / Jt_valley.dat / Jt_spin.dat
  quantum_geometry.dat      (ikx iky band kx ky E Omega gxx gyy gxy valley)
  input.nml / run           (log file named `run`)
  occupation_kt.dat         missing (save_occupation = .false. in this run)
  Et.dat / coherence_kt.dat missing (pre-Item 1/2)

output_verify_obs_exports_20260611/    (lg_cov, 40x40, T2_cycles=1.0,
                                        nt=5045, dt=0.008466 fs, total=42.703 fs)
  all of the above, plus
  occupation_kt.dat         52 snapshots, n_val(t=0)=84, n_cond(t=0)=0   (Item 0)
  Et.dat                    raw solver field after residual-DC correction;
                            max |E_native - E_reconstructed| ~ 5e-14 a.u. (Item 1)
  coherence_kt.dat          52 snapshots, coherence_norm(k,t=0)=0         (Item 2)
  occupation_band_kt.dat    intentionally skipped (full112 plain text is huge)
```

All time-series files carry a leading `it` index column; the converter
handles both this and the legacy time-first layout.

The export verification ran with `T2_cycles = 1.0`. The final
classical-light production baseline will use `T2_cycles = 0.5`.
Bundles produced from the verification run remain Data-driven but the
manifest confidence string and `dataset_name` must record the
verification origin.

### 1.3 Missing data (current)

```
band-resolved occupation rho_nn(k,t)      -> turn occ_band_resolved on selectively
                                              (don't dump full112 as plain text)
full complex density matrix rho_mn(k,t)   -> intentionally not exported (size)
```

**Resolved since the previous PLAN revision:**

- `k_space_occupation` — `occupation_kt.dat` produced (Item 0).
- `solver_output_Et_At`  — `Et.dat` produced (Item 1); converter now
  flips `field.source` to `raw_solver_output` automatically.
- `interband_coherence_norm` — `coherence_kt.dat` produced (Item 2);
  reader plumbed all the way to the `coherence_preview` block.
- Quantum geometry (Berry + metric + valley) was already produced by
  `save_geometry`.

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
1. CC finishes GitHub repo skeleton and convert_sbe_run.py            [done]
2. Current fixed quicklook / sanitized manifest is the baseline       [done]
3. data/samples/demo_bundle_minimal/ regenerated from current scripts [done]
4. validate_demo_bundle.py: no private paths/large blobs/missing keys [done]
5. Solver emits Et.dat -> field label flips to raw_solver_output      [done, Item 1]
6. Solver emits occupation_kt.dat -> k_space_occupation available     [done, Item 0]
7. Solver emits coherence_kt.dat -> interband_coherence_norm available [done, Item 2]
8. Run convert_sbe_run.py over output_verify_obs_exports_20260611
   and review the real Data-driven bundle quicklook                   [next]
9. Final production rerun at T2_cycles=0.5                            [solver side]
10. Desktop Unreal reads data_small.json and renders the four panels  [Phase 1]
11. Only then: Niagara / XR / MCP                                     [Phase 2+]
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
