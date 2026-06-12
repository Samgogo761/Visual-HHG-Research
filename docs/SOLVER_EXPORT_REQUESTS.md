# SOLVER_EXPORT_REQUESTS.md — Concrete asks for the Quantum-light solver

This document is the hand-off list for the solver side
(https://github.com/Samgogo761/Quantum-light). It replaces a vague
"please optimize the SBE solver" request with three precisely scoped
items, ordered by cost. Items 0 requires **no code change at all**.

Source-code references below are against the solver tree as of
2026-06-11 (`src/mod_sbe.f90`, `src/mod_laser.f90`, `src/main.f90`,
`src/mod_params.f90`).

---

## Status as of 2026-06-11 (verify_obs_exports_20260611 run)

**All three items have been completed on the solver side and accepted
by the HHG-XR Lab converter.** Run parameters:

```
output_verify_obs_exports_20260611
  gauge_method = lg_cov, full112, nkx = nky = 40, T2_cycles = 1.0
  nt = 5045, dt = 0.008466 fs, total = 42.703 fs
```

Caveat: this is an *export-interface verification* run, not the final
production benchmark. The final classical-light production baseline
will use `T2_cycles = 0.5`. Until that production rerun lands the
manifest still records the verification run in its `dataset_name` and
the confidence string.

| Item | File | Format | Acceptance |
|------|------|--------|------------|
| 0    | `occupation_kt.dat` (~7.65 MB) | `it time_fs ikx iky kx ky n_val n_cond` | 52 snapshots, 40x40 grid; `n_val(t=0)=84`, `n_cond(t=0)=0` for every k |
| 1    | `Et.dat` (~0.50 MB)            | `it time_fs Ex Ey Ax Ay`                 | `Ax(t0)=Ax(tN)=0` (residual-DC correction applied); native vs reconstructed `max |dE| ~ 5e-14 a.u.`; HHG-XR Lab converter promotes `field.source` to `raw_solver_output` |
| 2    | `coherence_kt.dat` (~6.32 MB)  | `it time_fs ikx iky kx ky coherence_norm` | `coherence_norm(k, t=0) = 0` for every k; nonzero response inside the pulse |

Solver log notes (`run.log`):

```
Initial current |J(t=0)| = 4.3971e-18    (machine zero, equilibrium current floor)
```

Intentionally not produced by this run:

```
occupation_band_kt.dat   # too large for full112 as plain text; defer to a
                         # windowed or NPZ variant if/when needed.
```

### First real bundle physics audit (local, 2026-06-12)

Run `convert_sbe_run.py` against the verify_obs_exports run reproduced
the expected physics end-to-end:

- **E(t) shape**: 1009 sample points, t in [0, 42.67] fs; 8 zero
  crossings ~ 4 optical cycles at 3200 nm (T_opt = 10.67 fs);
  envelope center at t ~ 21.33 fs. Confirms `ncyc = 4` drives the
  pulse length; `T2_cycles = 1.0` affects only dephasing.
- **HHG low order**: H1 = 2.47e-2, H3 = 5.73e-4, H5 = 2.73e-6,
  H7 = 1.82e-6 (clean odd-harmonic decay).
- **HHG high order**: dominant peaks near H253 (odd) and H505
  (likely numerical alias) — sanity but not core for v1 visualization.
- **band_path** (audit caught the converter bug — fixed in this commit):
  CrI3_band.dat is Wannier90 long format, 71456 rows = 638 k-pts x
  112 bands. The pre-fix converter flattened it into a single polyline;
  the fix reshapes to a (n_k, n_bands) table and ships
  `near_gap_band_indices` plus `e_fermi_eV` for client-side
  filtering.
- **delta_n_cond**: mean over k-grid rises from 0 at t=0 to 0.476 at
  t ~ 35.6 fs (occupied conduction snapshots). Peak lags the field
  amplitude peak by ~14 fs, consistent with cumulative excitation
  modulated by T2 ~ 10.7 fs dephasing; nonzero residual at t ~ 42 fs
  confirms incomplete relaxation. Physically correct.

Bundle size for this run was ~8 MB local (no `.npz`). After the
band_path reshape fix it drops by ~1.5 MB.

Below is the original work plan, kept for reference.

---

## Item 0 — Enable the occupation export that already exists (no code change)

**Status: already implemented in the solver. Just flip the flags.**

`mod_sbe.f90` already contains a Tier-0 diagnostic that snapshots
`rho_nn(k,t)` during propagation (`write_occupation_snapshot`,
called from the `propagate` loop). It is controlled by the `&output`
namelist in `input.nml` (`mod_params.f90`, line ~106):

```fortran
&output
  save_geometry     = .true.
  save_occupation   = .true.   ! <-- was .false. in output_verify_obs_nb112
  occ_stride        = 100      ! snapshot every N steps (0 => ~40 auto)
  occ_band_resolved = .true.   ! also dump per-band rho_nn(k,t)
/
```

Outputs produced:

```
occupation_kt.dat        # it time_fs ikx iky kx ky n_val n_cond
occupation_band_kt.dat   # it time_fs ikx iky band occupation     (if occ_band_resolved)
```

Size estimate for the nb112 / 46x46 production setup, occ_stride=100,
nt ~ 5000 (50 snapshots):

- `occupation_kt.dat`: 50 x 2116 rows x ~110 bytes ≈ **12 MB** — fine.
- `occupation_band_kt.dat`: 50 x 2116 x 112 rows ≈ **1.2 GB** — too
  big as text. Either raise `occ_stride` (e.g. 500 → ~240 MB), restrict
  to a band window (see Item 2), or accept it as a local-only file.
  Never commit either file to GitHub; the HHG-XR Lab converter
  downsamples them into `data_small.json`.

The HHG-XR Lab converter (`tools/convert_sbe_run.py`) already reads
`occupation_kt.dat` and flips the `k_space_occupation` module from
missing to available automatically.

**This closes the "no real k-space occupation" gap for v1 visualization.**

---

## Item 1 — Native E(t) / A(t) export (≈ 25 lines, biggest value per line)

**Status: not implemented.** `Et_vec(nt,3)` and `At_vec(nt,3)` are fully
computed in `mod_laser.f90 :: generate_field_sample` — including the
trapezoidal `A(t) = -∫E dt'` and the residual-DC ramp correction —
but never written to disk. Until they are, the visualization side must
reconstruct the field and label it
`reconstructed_from_input_nml_not_raw_output`. Reconstruction can never
reproduce the DC correction exactly, so the native export is the only
way to reach the `raw_solver_output` label.

Suggested drop-in subroutine (e.g. in `mod_laser.f90`):

```fortran
  subroutine write_field(filename)
    character(*), intent(in) :: filename
    integer :: u, it
    if (.not. allocated(Et_vec)) return
    open(newunit=u, file=filename, status='replace', action='write')
    write(u, '(A)') '# it  time(fs)  Ex(a.u.)  Ey(a.u.)  Ax(a.u.)  Ay(a.u.)'
    do it = 1, nt
      write(u, '(I8, 5ES18.10)') it, (it-1)*dt*au_to_fs, &
        Et_vec(it,1), Et_vec(it,2), At_vec(it,1), At_vec(it,2)
    end do
    close(u)
    write(*,'(A,A)') '  Field written to ', trim(filename)
  end subroutine write_field
```

Call site in `main.f90`, classical path, right after `generate_field()`:

```fortran
    call generate_field()
    call write_field("Et.dat")
```

Column convention `# it time_fs Ex Ey Ax Ay` is what the HHG-XR Lab
converter already expects (`read_field_dat` in
`tools/convert_sbe_run.py`). One file is enough; a separate `At.dat`
is also accepted but unnecessary.

For the BSV ensemble path, write one file per sample only if needed
later; the classical single-trajectory file is the v1 ask.

---

## Item 2 — Interband coherence norm export (small, second priority)

**Status: not implemented.** The solver exports only the diagonal
`rho_nn`. For the k-space coherence visualization
(docs/RHO_EXPORT_SPEC.md) we need one scalar per k per snapshot:

```
coherence_norm(k,t) = sqrt( sum_{m != n} |rho_mn(k,t)|^2 )
```

Cheap implementation: Frobenius norm squared minus the diagonal part,
inside the existing snapshot routine (`mod_sbe.f90`,
`write_occupation_snapshot` already loops over `ikx, iky` with `rho`
in scope):

```fortran
    ! inside the iky/ikx loop, after n_val/n_cond:
    coh2 = 0.0_dp
    do n = 1, n_trunc
      do m = 1, n_trunc
        if (m /= n) coh2 = coh2 + abs(rho(m, n, ikx, iky))**2
      end do
    end do
    ! write sqrt(coh2) as an extra column or a separate coherence_kt.dat
```

Preferred output (separate file, same snapshot cadence):

```
coherence_kt.dat   # it time_fs ikx iky kx ky coherence_norm
```

Gate it behind a new `&output` flag (e.g. `save_coherence`) so the
default cost stays zero. Size is the same as `occupation_kt.dat`
(~12 MB for the production case above).

---

## Item 3 — Optional, later: band-windowed rho exports

Only if/when the full `occupation_band_kt.dat` proves too large in
practice: add `occ_band_min` / `occ_band_max` to `&output` so only a
window (e.g. bands 80–90 around the gap) is dumped. This is an
optimization of Item 0, not a prerequisite for anything.

---

## What we are NOT asking the solver to do

- No real-time coupling to Unreal.
- No HDF5/NPZ migration — plain-text `.dat` in the current style is fine;
  the converter handles packaging.
- No full complex density-matrix dump (size explodes; the three scalars
  above cover the v1–v2 visualizations).
- No changes to propagation, gauges, or physics.

## Acceptance checks per item

- Item 0: rerun the nb112 case with the flags on; `occupation_kt.dat`
  exists; `python tools/convert_sbe_run.py --run-dir <dir> ...` reports
  `k_space_occupation` under `available_modules`.
- Item 1: `Et.dat` exists; converter output `field.source ==
  "raw_solver_output"`; reconstructed-vs-native max |ΔE| reported once
  for the record.
- Item 2: `coherence_kt.dat` exists; `coherence_norm(k, t=0) ≈ 0`
  everywhere (equilibrium has no interband coherence).
