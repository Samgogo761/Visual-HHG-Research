# ROADMAP.md — HHG-XR Lab

A phased plan. Each phase has a single primary deliverable and a hard
non-goal list to prevent scope creep.

---

## Phase 0 — Repo and pipeline foundations (current)

**Primary deliverable:** a sanitized demo bundle produced by a
reproducible converter, validated by an automated script.

In scope:

- Repository skeleton (README, PLAN, docs, tools, configs, tests).
- `tools/convert_sbe_run.py` for `Jt.dat`, `HHG.dat`, `bands.dat`,
  `Jt_decomposed.dat`, `Jt_valley.dat`, `input.nml`, `CrI3_band.dat`.
- `tools/sanitize_manifest.py` for stripping private paths.
- `tools/validate_demo_bundle.py` for safety and schema checks.
- `tools/make_quicklook.py` for the 4-panel preview PNG.
- Documentation of the bundle schema, physics provenance, future
  rho-export interface, and Unreal import.

Out of scope:

- Any Unreal project files.
- Real-time SBE solving.
- Niagara, XR, MCP.

Exit criterion: the acceptance checklist in `PLAN.md` is fully green.

---

## Phase 1 — Desktop Unreal prototype (read-only viewer)

**Primary deliverable:** a small Unreal project that opens
`data/samples/demo_bundle_minimal/manifest.json` and renders the band
path (near-gap subset by default), J(t), HHG spectrum, and E(t)/A(t).

In scope:

- A single Unreal project under `unreal/HHGXRLab/`.
- A bundle-loader module that parses JSON into Unreal structs.
- UMG widgets for the four core panels.
- A near-gap band slice with a fallback toggle to the full set.
- Click-on-harmonic-peak interaction on the HHG panel that surfaces
  the harmonic order and omega from `data_small.spectrum`.
- A `UProceduralMeshComponent` for the band surface preview.
- A persistent provenance badge that reflects
  `manifest.physics_provenance.source_class` and the new
  `field.source` vocabulary (raw solver / reconstructed not-raw /
  unavailable).

Out of scope:

- Niagara particle systems.
- VR support.
- Online data loading.
- Direct import of TB / WC `*.dat` files.

Exit criterion: a screenshot of all four panels driven by the sample
bundle, plus a short test that the loader survives a bundle whose
`available_modules` is a strict subset of the maximum set.

---

## Phase 2 — k-space occupation panel

**Primary deliverable:** the Unreal prototype renders `f_n(k,t)` and
`delta_f_n(k,t)` for a small subset of bands over the run timeline.

Prerequisites (solver side):

- The Wannier-SBE solver exports rho snapshots per
  [`RHO_EXPORT_SPEC.md`](./RHO_EXPORT_SPEC.md).
- The converter accepts `--rho-snapshots-dir` and adds `rho_k_t` to
  `available_modules`.

In scope:

- A scrubbable timeline UMG slider driven by `time_fs_axis`.
- A 2D heatmap or 3D occupation mesh for `delta_f_n(k,t)`.
- A coherence channel optionally driving emissive color.

Out of scope:

- VR.
- Full density matrix (off-diagonal complex phases) at this stage.

Exit criterion: a clip of the timeline scrub with the laser pulse
clearly correlated to occupation transfer.

---

## Phase 3 — Niagara particle visualization

**Primary deliverable:** replace or augment the heatmap with a Niagara
particle system that maps k-points to particles whose attributes are
driven by `f_n`, `delta_f_n`, and coherence.

In scope:

- Niagara emitter authored from a k-grid skeletal mesh or location event.
- Mapping from snapshot files to Niagara attribute updates.

Out of scope:

- VR (still desktop).
- Anything that requires more than one rho snapshot file open at a time
  if memory becomes a problem.

Exit criterion: stable 60 fps on a single GPU when scrubbing through the
full snapshot timeline at `n_sel <= 4`.

---

## Phase 4 — XR (VR/MR) interaction

**Primary deliverable:** a VR or MR experience that lets a viewer walk
around the 3D k-space band surface and the population cloud.

In scope:

- Headset-friendly UI re-layout.
- Controller-driven scrub and band-selection.
- A reduced LOD for headset render budgets.

Out of scope:

- Multi-user.
- Cloud streaming.
- Live solver coupling.

Exit criterion: a recorded headset-pov clip of the full visualization.

---

## Phase 5 — Quantum-light statistics, TMSV/BSV

**Primary deliverable:** a separate `available_modules` family for
quantum-light observables, with its own schema and its own provenance
rules.

This phase is intentionally far away and intentionally underspecified.

---

## Phase 6 — Live solver coupling and MCP (very later)

Only after Phases 0-3 are stable. The solver remains the source of
truth; the Unreal client stays a consumer.

The MCP layer, if it appears, is for orchestrating runs and importing
bundles, not for embedding solver state in the prompt context.
