# UNREAL_IMPORT.md — Reading the HHG-XR Lab demo bundle in Unreal

This document describes how a future desktop Unreal prototype should
read an HHG-XR Lab **demo bundle** and what it should render.

The bundle is on-disk only — there is no network call, no solver, no
real-time SBE. The Unreal client opens a directory and renders the
contents.

---

## 1. Bundle entry point

The single entry point is `manifest.json`. The Unreal client should:

1. Open `manifest.json`.
2. Verify `schema == "hhgxr-demo-bundle-v0"`.
3. Read `physics_provenance`, `units`, `dimensions`,
   `available_modules`, `missing_modules`, and `files`.
4. Open `files.data_small` (`data_small.json`) for arrays.
5. Open `files.quicklook` (`quicklook_summary.png`) for a fallback
   preview texture.
6. Skip any module listed in `missing_modules` or absent from
   `available_modules`.

The client must display the `physics_provenance.source_class` label
(`Data-driven`, `Model-based`, ...) as a persistent badge on every panel.

---

## 2. Recommended panels (v0 prototype)

### Panel A — Band path

Source: `data_small.band_path.{k_path, energy_eV}`.

Render as 2D line plot in a UMG widget or a 3D ribbon along the k-path.

### Panel B — Driving field E(t)

Source: `data_small.field.{time_fs, Ex, Ey}`.
Skip the panel entirely if `field.source == "unavailable"`.
Display a yellow caution badge if `field.source` ends in `_unverified`.

### Panel C — Current J(t)

Source: `data_small.time_series.{time_fs, Jx, Jy}`.

Optional layers:

- `Jx_intra` / `Jx_inter` for intraband/interband decomposition
- `Jx_K` / `Jx_Kp` for valley-resolved current

### Panel D — HHG spectrum

Source: `data_small.spectrum.{harmonic_order, HHG_total}`.

Render as log-scale line. Mark odd harmonic orders explicitly.

### Panel E — 3D k-space band surface preview

Source: `data_small.band_grid_preview.{kx, ky, selected_band_indices, energies_eV}`.

Render as a colored surface mesh built from the `(kx, ky, energy)`
triple, with band index controlling color or stack offset.

### Panel F — Provenance and missing modules

A read-only overlay listing:

- `physics_provenance` fields
- `available_modules` (green check) and `missing_modules` (gray)
- `dataset_name`

---

## 3. Recommended Unreal data flow

```
[Disk: demo_bundle_minimal/]
        │
        ▼
[Editor/Game subsystem] -- JSON parse --> UStruct: FHHGXRBundle
        │
        ▼
[ABundleActor] holds FHHGXRBundle
        │
        ├── BindUMG --> Panel widgets (band path, J(t), HHG)
        ├── BuildPMC --> Procedural mesh for band surface
        └── DispatchProvenance --> Top bar badge
```

Loading should be at editor-construction time or on `BeginPlay`; we are
not optimizing for hot-reload yet.

---

## 4. Numerical safety

The Unreal client should:

1. Cast incoming arrays to `float` only after a range sanity check.
2. Refuse to render an HHG panel whose log-magnitude is `NaN` or
   `+inf` at all sample points.
3. Use `physics_provenance.confidence` text in the panel tooltip rather
   than overwriting the units string.

---

## 5. Niagara / k-space occupation (later)

Once `rho_k_t` is added to `available_modules` (see
[`RHO_EXPORT_SPEC.md`](./RHO_EXPORT_SPEC.md)), the prototype gains a new
panel:

- Niagara particle system seeded from `(kx, ky)` grid.
- Particle attribute `f` driven by `f_n(k,t)` or `delta_f_n(k,t)`.
- Color ramp keyed to `coherence_norm(k,t)`.
- Scrubbable timeline driven by `time_fs_axis` from
  `rho_snapshot_manifest.json`.

The k-space panel must remain disabled while `rho_k_t` is listed in
`missing_modules`. The client should not invent a placeholder occupation
without labeling it `Model-based`.

---

## 6. Texturing the band surface

For 3D band surface preview, build a `UProceduralMeshComponent`:

- Vertices: `(kx[i], ky[j], energy_eV[band, i, j] * z_scale)`
- Triangles: a standard grid index pattern over `(nkx-1) * (nky-1) * 2`
- Vertex colors: lerp on `energy_eV` between two band-specific endpoints
- Material: an unlit master that multiplies vertex color by emissive

Do not normalize `energy_eV` across panels; each band should keep its
own absolute scale and the camera should be initialized to frame the
band of interest.

---

## 7. What the v0 Unreal prototype is *not*

- Not VR. Desktop only.
- Not interactive solving. Read-only data viewer.
- Not Niagara. Procedural mesh + UMG only.
- Not online. No HTTP, no MCP.

These come later, after the data pipeline is reliable.
