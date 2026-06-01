# data/samples/

Tiny, public-safe demo bundles. Each subdirectory is one bundle and
follows the on-disk schema in
[`docs/DATA_SCHEMA.md`](../../docs/DATA_SCHEMA.md).

## Current bundles

### `demo_bundle_minimal/`

A small synthetic bundle that demonstrates the schema and lets downstream
clients (validators, Unreal loader) be tested without access to the real
SBE/Wannier data. It contains:

```
manifest.json
data_small.json
quicklook_summary.png
README.md
```

The manifest declares this as a synthetic bundle, with
`physics_provenance.source_class = "Model-based"` so no consumer
mistakes the synthetic curves for `Data-driven` results. The real
data-driven bundle (`lg_cov_k40_nb104_T2_0p5cycle_plusN`) is produced
locally with `tools/convert_sbe_run.py` and is **not** committed here.

## Adding a new bundle

1. Generate it with `tools/convert_sbe_run.py` (or hand-curate for
   synthetic samples).
2. Run `tools/sanitize_manifest.py --in-place` if any path slipped in.
3. Run `tools/validate_demo_bundle.py --bundle <dir>`.
4. Commit only the JSON, PNG, and small CSV files; never `.npz`/`.dat`
   blobs without prior discussion.
