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

## 2. First-demo provenance map

The first demo bundle (`lg_cov_k40_nb104_T2_0p5cycle (+N benchmark)`)
supports **`Data-driven`** visualization of:

```
J(t)
HHG spectrum
band energies
intraband/interband current decomposition
valley-resolved current
```

It does **not** yet support `Data-driven` visualization of:

```
k-space occupation rho(k,t)
band-resolved population f_n(k,t)
interband coherence |rho_mn(k,t)|
full density matrix dynamics
quantum-light statistics
production-route Berry curvature in lg_cov
```

These quantities are listed under `missing_modules` in the manifest and
must not be silently faked. If a prototype needs a placeholder rho(k,t),
that placeholder must be labeled `Model-based` (or `Conceptual-only`),
not `Data-driven`.

---

## 3. Field reconstruction note

The reconstructed driving field `E(t)` produced from `input.nml` is
currently labeled:

```
field_source = "reconstructed_from_input_nml_unverified"
```

The reconstructed quicklook may appear suspiciously spike-like. **Do not
treat the reconstructed field as physically trusted until it is verified
against the exact solver laser model.** Once verified, the label changes
to `reconstructed_from_input_nml_verified`. If the solver itself emits
`E(t)` / `A(t)`, the label becomes `solver_native`.

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
