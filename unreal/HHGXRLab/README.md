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
