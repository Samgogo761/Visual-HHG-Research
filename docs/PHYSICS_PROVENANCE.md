# PHYSICS_PROVENANCE.md — HHG-XR Lab

The HHG-XR Lab visualizes physical quantities that can come from very
different sources: solver outputs, analytical models, literature
reproductions, or conceptual sketches. We use four provenance labels so
that no viewer ever mistakes a model curve for measured data, or a
sketch for a solver result.

Every visualizable quantity in this repository **must** be tagged with
one of the labels below, both in the `manifest.json` and, where
practical, in the corresponding UI element of any downstream Unreal/XR
client.

---

## 1. Provenance labels

### `Data-driven`

The quantity is derived from a solver run or experimental dataset, with
the exact source recorded. No model parameters were tuned to "fix" the
shape.

Examples in v0:
- `J(t)` from `Jt.dat`
- HHG spectrum from `HHG.dat`
- Band energies on the k-grid from `bands.dat`
- Intraband / interband decomposition from `Jt_decomposed.dat`
- Valley-resolved current from `Jt_valley.dat`

### `Model-based`

The quantity is computed from an analytical or numerical model in this
repository, not from a solver dataset. The model parameters are
documented in the manifest. The label does not imply the model is wrong,
only that it is not a direct measurement or solver output.

Examples in v0:
- Reconstructed `E(t)` from `input.nml` parameters
  (until verified against the solver's exact laser model).
- Any toy Berry-curvature surface used for prototyping.

### `Literature-reproduced`

The curve attempts to reproduce a published figure or formula. The
citation and DOI must accompany the data.

Examples in v0:
- None yet.

### `Conceptual-only`

The asset is a hand-drawn or hand-placed illustration with no underlying
quantitative data. These must be visibly marked as conceptual in any
client that displays them.

Examples in v0:
- Any pre-data XR mockups created for layout planning.

---

## 2. Demo provenance map

With the verify_obs-generation solver outputs
(`output_verify_obs_nb112_T2_0p5cycle` and successors), a real run
supports **`Data-driven`** visualization of:

```
J(t)
HHG spectrum (charge and spin-z)
band energies (k-grid and k-path)
intraband/interband current decomposition
valley-resolved current and valley polarization eta
spin-z current J^{s_z}(t)
quantum geometry: Berry curvature, quantum metric trace, valley map
k-space occupation n_val/n_cond(k,t)      [requires save_occupation=.true. in the run]
band-resolved occupation rho_nn(k,t)      [requires occ_band_resolved=.true.]
```

It does **not** yet support `Data-driven` visualization of:

```
native E(t)/A(t)                  (solver patch pending, SOLVER_EXPORT_REQUESTS.md Item 1)
interband coherence |rho_mn(k,t)| (solver patch pending, Item 2)
full density matrix dynamics      (intentionally not exported)
quantum-light statistics          (BSV module exists solver-side; out of v0 scope)
```

These quantities are listed under `missing_modules` in the manifest and
must not be silently faked. If a prototype needs a placeholder rho(k,t),
that placeholder must be labeled `Model-based` (or `Conceptual-only`),
not `Data-driven`.

Physics caveat that viewers must preserve: bilayer CrI3 AFM is
PT-symmetric, so the band-resolved Berry curvature `Omega_n(k)` sits at
the numerical floor. A near-zero Berry curvature panel is the **correct
physical statement** (it proves the anomalous current vanishes), not a
broken dataset. Do not rescale it into something that looks
interesting.

---

## 3. Field reconstruction note

History (kept for the audit trail):

- The first reconstructor produced a delta-spike pulse and was tagged
  `reconstructed_from_input_nml_unverified`.
- The local audit script was then fixed. It now reproduces a sensible
  3200 nm, 4-cycle, ~42.70 fs cos²-envelope pulse, and the reconstructor
  was rechecked against `input.nml`, `mod_laser.f90`, and
  `mod_params.f90` with cross-validation of `omega0`, `T_total`, and
  `nt` from `run.log`.

Current label:

```
field_source = "reconstructed_from_input_nml_not_raw_output"
```

Meaning: `E(t)` and `A(t)` are reconstructed from the solver inputs and
cross-checked against `run.log`, so the curves are visualization-ready
and good enough for the first demo. They are still **not** the solver's
native output. The first demo may show the curves; the UI and the
manifest must keep the label visible.

Upgrade path:

- If the solver starts emitting `Et.dat` / `At.dat` directly (per the
  recommended column layout `# it time_fs Ex_au Ey_au Ax_au Ay_au`),
  the converter picks them up automatically and the label switches to
  `raw_solver_output` with no schema change required.
- The legacy `_unverified` / `_verified` labels are accepted by the
  validator for backward compatibility but are flagged with a warning.
  Older bundles should be regenerated.

---

## 4. Display rules for downstream clients

Any Unreal/XR client that displays an HHG-XR Lab dataset must show the
provenance label prominently. Recommended UI:

- A persistent badge on each panel: `Data-driven`, `Model-based`,
  `Literature-reproduced`, or `Conceptual-only`.
- A "missing modules" notice on any panel that wants to display a
  quantity present in `missing_modules`.
- An "unverified" caveat on any field plot whose
  `field.source` ends in `_unverified`.

---

## 5. Why this matters

A future XR experience for HHG is highly persuasive: a 3D k-space cloud
of population that pulses with the laser field feels true. A correctness
mistake (e.g. labeling a `Model-based` Berry curvature as a measured
quantity) would be very hard to detect by eye. The provenance labels are
the audit trail that lets a reviewer always answer: *where did this
curve come from?*
