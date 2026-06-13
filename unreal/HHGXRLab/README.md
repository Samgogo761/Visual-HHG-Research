# HHGXRLab Unreal plugin

Header-only `USTRUCT` spec for the **`hhgxr-demo-bundle-v0`** schema
plus a `UBlueprintFunctionLibrary` that opens `manifest.json` and
`data_small.json` from disk into those structs. No `.uproject`.

Target engine: **Unreal Engine 5.3 – 5.7+** (the `.uplugin` deliberately
does not pin `EngineVersion`, so any 5.x host loads the plugin without
the "incompatible" popup). The only engine APIs used are
`FJsonSerializer`, `FFileHelper::LoadFileToString`, `FPaths::Combine`,
and the typed `FJsonObject::TryGetXxxField` accessors. The loader
deliberately avoids `FJsonObject::TryGetField` because its return type
changed from `const TSharedPtr<FJsonValue>&` (5.3) to
`const TSharedPtr<FJsonValue>*` (5.4+).

---

## Drop into a UE C++ project

1. Copy this directory into your project's `Plugins/` folder so the
   layout becomes:

   ```
   <YourGame>/
     Plugins/
       HHGXRLab/
         HHGXRLab.uplugin
         Source/HHGXRLab/...
   ```

2. Right-click `<YourGame>.uproject` -> **Generate Visual Studio project
   files** (Windows) or run `<UE5>/GenerateProjectFiles.sh` (Linux).

3. Add `HHGXRLab` to your game module's `PublicDependencyModuleNames`
   in `<YourGame>.Build.cs`:

   ```csharp
   PublicDependencyModuleNames.AddRange(new[]
   {
       "Core", "CoreUObject", "Engine",
       "HHGXRLab",
   });
   ```

4. Rebuild. Open the editor; **Edit > Plugins > Other** should list
   "HHG-XR Lab Bundle Loader" as Enabled.

---

## Quick visual test: 3D band surface (AHHGXRBundleViewerActor)

The plugin ships a reference Actor that loads a bundle and builds one
`UProceduralMeshComponent` band surface per band in
`band_grid_preview.energies_eV`. No editor assets, no Play required.

1. **Window > Place Actors**, search **HHG-XR Bundle Viewer**, drag one
   into your level (or use the **Outliner > +Add** dropdown).
2. With the Actor selected, in the **Details** panel:
   - **Bundle Dir (absolute path)**: e.g. `C:/tmp/hhgxr_first_real_bundle`
     (forward slashes are fine). On save / Enter, the mesh builds
     in-editor.
   - **K Scale** / **E Scale**: world units per (1/bohr) and per eV.
     Defaults 200 / 20 put a `(0.5)^2` BZ slab into a ~2 m square that
     reaches ~1 m up for a 5 eV band; tune to taste.
   - **Surface Material**: leave None for the default gray engine
     material, or drop any material here. The mesh has vertex colors
     keyed to a per-band palette, so a vertex-color-aware material
     (e.g. an emissive that multiplies `VertexColor`) will show the
     bands as distinct colored sheets.
3. Click the **Rebuild From Bundle** button at the top of the Details
   panel to reload after any tweak (also triggered automatically while
   *Auto Rebuild In Editor* is on, the default).

The 3D text component above the surface is the provenance badge: it
shows `<source_class> | <gauge> | field: <raw solver / reconstructed
(not raw) / unavailable>` and is colored green / orange / grey / red to
match the Python quicklook.

### Occupation over time (k_space_occupation module)

When the bundle carries an `occupation_preview`, the band colors animate
with the per-k conduction population change `delta_n_cond(k,t)`:

- **conduction** bands (global band index > `n_valence`) brighten where
  electrons are promoted;
- **valence** bands (index <= `n_valence`) dim where they are depleted;
- at `t = 0` `delta_n_cond` is zero everywhere, so conduction starts
  dim and valence starts bright -- the equilibrium.

Physics-honesty note: the band *geometry never moves*. Band energies are
static; only the occupation field changes. We deliberately do **not**
wobble the band height at the laser frequency, because that would imply
the band structure itself oscillates, which it does not.

Controls (Details panel, category *HHG-XR | Occupation*):

- **Snapshot Index**: scrub through snapshots in the editor; the badge
  shows `t = <fs>  (snap k/N)`.
- **Occupation Gain**: brightness response to `delta_n_cond`; raise it
  to make resonant k-pockets pop sooner.
- **Dim Floor**: how dark an unexcited conduction (or fully depleted
  valence) band gets (0..1).
- **Show Occupation**: off => flat band palette (the old static look).
- **Animate In Play** + **Seconds Per Snapshot**: press **Play** and the
  snapshots auto-advance so the pulse plays out; for
  `verify_obs_exports_20260611` you should see conduction k-pockets
  light up around the pulse peak (~21 fs / mid-snapshot) and stay
  partially lit afterwards (incomplete T2 relaxation).

### Expected look for `verify_obs_exports_20260611`

- 4 sheets (one per `selected_band_indices`, default range 80..90 from
  the converter, capped to 4 by `--max-grid` if you used the smaller
  preview); each is a smooth 40x40 paraboloid-ish surface.
- Above the surface: a yellow / orange line reading
  `Data-driven | lg_cov | field: raw solver`.
- The Output Log prints
  `HHG-XR: built N band surface(s), 40x40 grid, ~12480 triangles total`.

If you see `LOAD FAILED: ...` above the surface, the message is the
reason (bad path / missing manifest / wrong schema id).

## Fastest smoke test (Blueprint, no extra C++)

`DescribeBundle` loads a bundle and returns a one-glance multi-line
summary, so the entire verification is three nodes:

1. Open the **Level Blueprint** (toolbar **Blueprints > Open Level
   Blueprint**).
2. Right-click the graph, add **Event BeginPlay**.
3. Right-click, search **Describe Bundle** (category *HHG-XR | Bundle*),
   add it, and wire BeginPlay -> Describe Bundle.
4. In its **Bundle Dir Abs** field type a bundle directory with forward
   slashes, e.g. `C:/tmp/hhgxr_first_real_bundle`.
5. Drag from the **Return Value** (string) into a **Print String** node;
   wire the exec pins.
6. Press **Play**. The summary prints in the top-left viewport overlay
   and the Output Log.

A healthy real-data readout looks like:

```
schema       : hhgxr-demo-bundle-v0
dataset      : verify_obs_exports_20260611...
source_class : Data-driven
gauge        : lg_cov
dims         : nt=5045 nkx=40 nky=40 n_bands=112 n_val=84
field.source : raw solver
available(13): current_time_series, hhg_spectrum, ...
band_path    : layout=wannier90_long n_bands=112 near_gap=20 eFermi=0.0843
occupation   : 9 snapshots
coherence    : 9 snapshots
```

If you see `LOAD FAILED: ...`, the message is the reason (bad path,
missing manifest.json, or unsupported schema).

## Minimal C++ usage

```cpp
#include "HHGXRBundleLoader.h"

void AMyActor::BeginPlay()
{
    Super::BeginPlay();

    FHHGXRBundle Bundle;
    FString Error;
    const FString BundleDir = FPaths::ProjectContentDir() / TEXT("HHGXR/demo_bundle_minimal");

    if (!UHHGXRBundleLoader::LoadBundle(BundleDir, Bundle, Error))
    {
        UE_LOG(LogTemp, Error, TEXT("HHG-XR load failed: %s"), *Error);
        return;
    }

    const FHHGXRManifest& M = Bundle.Manifest;
    UE_LOG(LogTemp, Log, TEXT("Dataset: %s"), *M.DatasetName);
    UE_LOG(LogTemp, Log, TEXT("Gauge:   %s"), *M.Provenance.GaugeMethod);
    UE_LOG(LogTemp, Log, TEXT("Bands:   %d (Nv=%d)"),
           M.Dimensions.NBands, M.Dimensions.NValence);

    if (UHHGXRBundleLoader::HasModule(M, TEXT("k_space_occupation")))
    {
        const FHHGXROccupationPreview& Occ = Bundle.Data.OccupationPreview;
        UE_LOG(LogTemp, Log, TEXT("Occupation snapshots: %d"), Occ.Snapshots.Num());
    }

    // Provenance badge for a UMG text widget
    const FString Badge = UHHGXRBundleLoader::FieldSourceBadge(Bundle.Data.Field);
    const FLinearColor BadgeColor =
        UHHGXRBundleLoader::FieldSourceColor(Bundle.Data.Field.Source);
}
```

## Minimal Blueprint usage

`LoadBundle`, `HasModule`, `FieldSourceBadge`, and `FieldSourceColor`
are all `UFUNCTION(BlueprintCallable / BlueprintPure)`. From any Actor
or Widget Blueprint:

1. Drag a **Load Bundle** node.
2. Wire its `Bundle Dir Abs` input to a path string. On Windows the
   bundle directory is something like
   `C:/tmp/hhgxr_first_real_bundle`.
3. Use `Bundle.Manifest.Available Modules` to drive panel visibility.
4. Bind `Field Source Badge` text to your provenance label.

---

## Schema and conventions

- **Source of truth:** `docs/DATA_SCHEMA.md` in the parent repository.
- 2D float tables -> `FHHGXRFloatGrid2D` (row-major flat).
- 3D float stacks -> `FHHGXRFloatStack3D`.
- 2D int tables -> `FHHGXRIntGrid2D` (used for `valley_id`).
- `field.source` -> `EHHGXRFieldSource` enum; the raw string is also
  preserved in `FHHGXRFieldBlock::SourceRaw`. Legacy
  `*_verified` / `*_unverified` labels collapse to
  `ReconstructedNotRaw`.
- `band_path.energy_eV` is **always** a 2D `[n_k][n_bands]` table after
  conversion, regardless of whether the source was Wannier90 long or
  legacy wide format.
- `band_path.near_gap_band_indices` is the recommended default render
  subset for HHG-XR datasets with 100+ bands; clients can ignore it.
- Quantum geometry note: PT-symmetric AFM CrI3 has Berry curvature at
  the numerical floor. **Do not rescale** the curvature panel for
  visual interest — that would be fabricating physics. The schema
  carries this caveat in
  `FHHGXRQuantumGeometryPreview::Note`.

## What this plugin deliberately does **not** do

- No rendering. UMG / Niagara / `UProceduralMeshComponent` use is left
  to the consuming project so it stays free to pick layouts.
- No file I/O outside `LoadBundle`. No network. No watchers.
- No `.uproject`. Drop-in only.

## Next steps in this repo

The parent repository's roadmap (`docs/ROADMAP.md`) plans these layers
on top of this plugin:

- A reference `AHHGXRBundleViewerActor` that draws all six panels via
  UMG + a procedural mesh band surface.
- A Niagara emitter driven by `OccupationPreview.Snapshots[s].DeltaNCond`
  and `CoherencePreview.Snapshots[s].CoherenceNorm`.
- A scrubbable timeline UMG widget driven by the snapshot time axis.

None of those ship in this directory yet — this is the
"data-structures + loader" layer only.

---

## Troubleshooting

### "HHGXRLab is incompatible" popup

The `.uplugin` no longer pins `EngineVersion`. If you still see this on
a 5.5+ host, your `Plugins/HHGXRLab/` copy may be stale; recopy from
`unreal/HHGXRLab/` and regenerate project files.

### "HHGXRHost could not be compiled"

This popup is generic — the real error is in the compile log.

- **From the editor**: re-open the project, and when the popup appears
  click **Show Output Log**, then scroll for lines starting with
  `error:` (clang) or `error C\d+:` (MSVC).
- **From Visual Studio**: open the generated `.sln`, set the
  `Development Editor` configuration, and **Build > Build Solution**.
  The Output / Build pane shows the underlying compiler error.
- **From the log directly**: `<YourProject>/Saved/Logs/<YourProject>.log`
  is the most recent run; the most useful section is between the
  `Compile attempt: HHGXRLab` and `BuildEvent` markers.

If the host project is **Blueprint-only**, UE will still try to compile
the plugin's C++ source when it loads. To produce a clean rebuild path:

1. In the editor: **Tools > New C++ Class > None**, accept the default
   names, and let UE create a minimal game C++ module. (You can delete
   the class file afterwards, but the project must keep at least one
   C++ source so the Build target exists.)
2. Close the editor.
3. Right-click `<YourProject>.uproject` again and choose **Generate
   Visual Studio project files**.
4. Open the `.sln`, build, and reopen the editor.

### "Missing HHGXRHost Modules" popup

This is normal the first time the plugin is added. Click **Yes** to
build modules; if that fails, follow the steps above to inspect the
actual compile error.

### `RulesError` / "Expecting to find a type ... named 'X'" with X != HHGXRLab

If the build fails on a *different* plugin name, the host `.uproject`
references a plugin whose source is not present in this engine install.
A common culprit is Microsoft's `VisualStudioTools` plugin, which is
not bundled with a stock UE install:

```
Expecting to find a type to be declared in a module rules named
'VisualStudioTools' ... Result: Failed (RulesError)
```

UnrealBuildTool aborts the whole UE5Rules assembly before it ever
reaches HHGXRLab, so *every* plugin then reports as "incompatible or
missing" — a misleading cascade. The fix is to remove the dangling
reference from `<YourProject>.uproject` (the `Plugins` array), not to
touch HHGXRLab:

```powershell
$proj = "C:/path/to/YourProject.uproject"
Copy-Item $proj "$proj.bak"
$json = Get-Content $proj -Raw | ConvertFrom-Json
$json.Plugins = @($json.Plugins | Where-Object { $_.Name -ne "VisualStudioTools" })
$json | ConvertTo-Json -Depth 10 | Set-Content $proj -Encoding UTF8
```

Then delete `Binaries/` + `Intermediate/` and rebuild.
