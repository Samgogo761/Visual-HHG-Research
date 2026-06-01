# data/

This directory holds **sanitized**, **small**, public-safe artifacts only.

What lives here:

- `samples/` — tiny example bundles produced by `tools/convert_sbe_run.py`
  or hand-curated from synthetic data.

What never lives here:

- Raw solver outputs (`*.dat`, `*.h5`, `*.npy`, large `*.npz`)
- Wannier/TB files (`CrI3_tb.dat`, `CrI3_hr.dat`)
- Server-side downloaded datasets
- Manifest files that embed private absolute paths

If you need to share a larger artifact, talk to the maintainer about
Git LFS first.
