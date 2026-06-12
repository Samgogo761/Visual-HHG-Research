# RHO_EXPORT_SPEC.md — Solver exports for rho(k,t)

This document specifies the density-matrix export path that lets
HHG-XR Lab visualize k-space occupation `f_n(k,t)`, population change
`delta_f_n(k,t)`, and interband coherence on a 2D Brillouin-zone grid.

## 0. What the solver already implements (2026-06 status)

The Quantum-light solver (`src/mod_sbe.f90`) **already contains** a
Tier-0 snapshot exporter, controlled by the `&output` namelist:

```fortran
&output
  save_occupation   = .true.
  occ_stride        = 100      ! 0 => ~40 auto
  occ_band_resolved = .true.
/
```

Existing output formats (plain text, snapshot-appended):

```
occupation_kt.dat        # it time_fs ikx iky kx ky n_val n_cond
occupation_band_kt.dat   # it time_fs ikx iky band occupation
```

`tools/convert_sbe_run.py` reads `occupation_kt.dat` directly and emits
the `occupation_preview` block of `data_small.json`; the manifest then
lists `k_space_occupation` under `available_modules`.

As of the verify_obs_exports_20260611 run the solver also produces
the Item-2 coherence export:

```
coherence_kt.dat         # it time_fs ikx iky kx ky coherence_norm
```

with `coherence_norm(k, t=0) = 0` enforced. The HHG-XR Lab converter
reads it directly and emits the `coherence_preview` block of
`data_small.json`; the manifest then lists `interband_coherence_norm`
under `available_modules`.

What remains genuinely missing solver-side is only the band-windowed
variant of `occupation_band_kt.dat` (skipped for full112 because a
plain-text dump is ~1 GB). When/if it lands, the same JSON layout
below applies; until then the `band_resolved_occupation` module stays
listed under `missing_modules`.

The `.npz`-based snapshot layout below remains the spec for the
*converter-side packaging* of these text files, and for any future
solver that prefers binary output.

---

## 1. Goal

Produce a small set of files per run that:

1. Cover a useful range of time steps (not every step).
2. Are easy to load in Python (`numpy`, `h5py`) and import in Unreal
   (`.npy` or `.npz`).
3. Carry their own metadata so a viewer can reproduce the physical
   meaning of each axis without reading the solver source.
4. Stay small enough to share through the standard HHG-XR Lab demo
   bundle pipeline.

---

## 2. Files emitted per snapshot

For each time index `tXXXX` selected for export:

```
rho_snapshot_manifest.json
rho_f_band_tXXXX.npz         # band-diagonal occupation
rho_coherence_tXXXX.npz      # interband coherence magnitude
```

`XXXX` is a zero-padded integer index into the original time grid.

### 2.1 `rho_f_band_tXXXX.npz`

Recommended arrays:

```
kx                shape (nkx,),           float64, units 1/bohr
ky                shape (nky,),           float64, units 1/bohr
band_indices      shape (n_sel,),         int32
f                 shape (n_sel, nkx, nky), float32, dimensionless [0, 1]
delta_f           shape (n_sel, nkx, nky), float32, f(t) - f(t=0)
time_fs           scalar,                  float64
```

`f` is `Re rho_nn(k,t)` for each selected band.

### 2.2 `rho_coherence_tXXXX.npz`

```
kx, ky, band_indices   (as above)
coherence_norm         shape (nkx, nky), float32
                       coherence_norm = sqrt( sum_{m != n} |rho_mn(k,t)|^2 )
                       summed over the selected band pairs
time_fs                scalar, float64
```

If multiple band pairs are exported separately, use:

```
band_pairs             shape (n_pairs, 2), int32   # (m, n) entries
coherence_norm         shape (n_pairs, nkx, nky), float32
```

### 2.3 `rho_snapshot_manifest.json`

Indexes every snapshot in the run:

```json
{
  "schema": "hhgxr-rho-snapshots-v0",
  "run_id": "lg_cov_k40_nb104_T2_0p5cycle_plusN",
  "stride_steps": 100,
  "time_fs_axis":      [...],
  "snapshots": [
    {
      "t_index": 0,
      "time_fs": 0.0,
      "f_file":  "rho_f_band_t0000.npz",
      "c_file":  "rho_coherence_t0000.npz"
    },
    ...
  ],
  "band_indices_selected": [80, 81, 82, ..., 89],
  "units": {
    "k":   "1/bohr",
    "time": "fs"
  },
  "physics_provenance": {
    "source_class": "Data-driven",
    "model":        "Wannier-SBE",
    "gauge_method": "lg_cov"
  }
}
```

---

## 3. Minimum physical quantities

For the first k-space visualization milestone, the solver should expose:

```
f_n(k,t)              = Re rho_nn(k,t)
delta_f_n(k,t)        = f_n(k,t) - f_n(k,0)
coherence_norm(k,t)   = sqrt( sum_{m != n} |rho_mn(k,t)|^2 )
```

`delta_f_n(k,t)` is what we actually want to render: it makes the
laser-driven population transfer visually obvious because the
equilibrium offset cancels.

---

## 4. Export stride

For a smooth visualization without dumping every time step:

```
write every 50-200 time steps for visualization
```

Recommended defaults:

```
--stride-steps 100
--max-snapshots 200
```

A 5045-step run with `--stride-steps 100` produces ~50 snapshots, which
keeps the entire `rho_snapshot_manifest.json` set under ~10-50 MB
depending on `n_sel`, `nkx`, `nky`, and dtype.

---

## 5. Selecting bands

Exporting all 104 bands per snapshot is unnecessary. Recommended
selection rule:

1. The HOMO-1, HOMO, LUMO, LUMO+1 bands (for the equilibrium gap).
2. Any band that absorbs `> 1%` of the time-integrated photoexcitation.
3. Any band the user explicitly requests via `--selected-bands a:b`.

The selected band indices must be recorded in
`band_indices_selected` of `rho_snapshot_manifest.json`.

---

## 6. Naming

```
output/
  <run_id>/
    rho_snapshot_manifest.json
    rho_f_band_t0000.npz
    rho_f_band_t0100.npz
    ...
    rho_coherence_t0000.npz
    rho_coherence_t0100.npz
    ...
```

The HHG-XR Lab converter will reference the manifest from the run's
`manifest.json` under `available_modules: ["rho_k_t"]` and add a key to
`files`:

```json
"files": {
  "rho_snapshots": "rho_snapshots/rho_snapshot_manifest.json"
}
```

---

## 7. Sanity checks before exporting

The solver should validate before writing:

1. `0 <= f_n(k,t) <= 1` within numerical tolerance.
2. `sum_n f_n(k,t) == sum_n f_n(k,0)` (electron conservation) per `k`.
3. `f_n(k,t=0)` matches the equilibrium occupation of the unperturbed
   Hamiltonian.
4. `coherence_norm(k,t=0)` is approximately zero.

Failures are not silent. The exporter records them in
`rho_snapshot_manifest.json`:

```json
"sanity_checks": {
  "occupation_bounds_ok":  true,
  "electron_conservation": "max_residual=1.3e-9",
  "equilibrium_check":     "ok",
  "coherence_at_t0":       "max=4.1e-12"
}
```

These records become part of the provenance.
