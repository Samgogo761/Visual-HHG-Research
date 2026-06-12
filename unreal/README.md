# unreal/

Unreal-side code for HHG-XR Lab. Currently:

- [`HHGXRLab/`](./HHGXRLab/) — UE 5.3+ plugin: `USTRUCT` spec for the
  `hhgxr-demo-bundle-v0` schema and a `UBlueprintFunctionLibrary`
  that opens `manifest.json` / `data_small.json` from disk.

There is intentionally **no `.uproject`** in this directory. The
plugin is meant to be dropped into any host UE C++ project's
`Plugins/` folder; see [`HHGXRLab/README.md`](./HHGXRLab/README.md)
for the drop-in steps.

The plugin only provides data structures and a loader. Panels,
procedural meshes, Niagara emitters, and the scrubbable timeline are
Phase 2+ work tracked in [`../docs/ROADMAP.md`](../docs/ROADMAP.md).
