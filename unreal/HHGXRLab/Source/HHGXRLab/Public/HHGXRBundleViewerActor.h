// HHG-XR Lab reference viewer Actor.
//
// Drop into a level, set BundleDirAbs in the Details panel, and the Actor
// loads the bundle and builds a 3D ProceduralMeshComponent band surface
// per selected band, plus a 3D text provenance badge. Mesh rebuilds on
// editor property change so the workflow is "drop-and-tweak", no Play
// required.
//
// Phase 2 (occupation animation): the band *geometry* is static -- band
// energies do not move. What animates is the per-k occupation
// delta_n_cond(k,t): conduction bands brighten where electrons are
// promoted, valence bands dim where they are depleted. Scrub SnapshotIndex
// in the editor, or press Play to auto-advance through the snapshots.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "UObject/ObjectPtr.h"
#include "ProceduralMeshComponent.h"
#include "HHGXRTypes.h"
#include "HHGXRBundleViewerActor.generated.h"

class UTextRenderComponent;
class UMaterialInterface;
struct FHHGXRBundle;

/** Cached geometry for one band surface so SnapshotIndex re-coloring does
 *  not need to re-read the bundle or rebuild triangles. */
USTRUCT()
struct FHHGXRBandSectionCache
{
    GENERATED_BODY()

    UPROPERTY() int32 GlobalBandIndex = 0;
    UPROPERTY() bool bConduction = false;
    UPROPERTY() FLinearColor BaseColor = FLinearColor::White;
    UPROPERTY() int32 NumRows = 0;
    UPROPERTY() int32 NumCols = 0;
    UPROPERTY() TArray<FVector> Vertices;
    UPROPERTY() TArray<FVector> Normals;
    UPROPERTY() TArray<FVector2D> UV0;
    UPROPERTY() TArray<FProcMeshTangent> Tangents;
};

UCLASS(BlueprintType, meta = (DisplayName = "HHG-XR Bundle Viewer"))
class HHGXRLAB_API AHHGXRBundleViewerActor : public AActor
{
    GENERATED_BODY()

public:
    AHHGXRBundleViewerActor();

    // -----------------------------------------------------------------
    // Bundle + geometry
    // -----------------------------------------------------------------

    /** Absolute path to the demo bundle directory containing manifest.json. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR",
              meta = (DisplayName = "Bundle Dir (absolute path)"))
    FString BundleDirAbs;

    /** World units per (1/bohr) on the k-axes. Default 200 -> a 1.0 BZ width is 2 m. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR|Scale",
              meta = (ClampMin = "1.0"))
    float KScale = 200.0f;

    /** World units per eV on the energy axis. Default 20 -> a 5 eV band reaches 1 m up. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR|Scale",
              meta = (ClampMin = "0.1"))
    float EScale = 20.0f;

    /** Height (cm) of the provenance text badge above the actor origin. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR|Scale")
    float BadgeHeight = 300.0f;

    /** Optional material applied to every band section. Leave None for the engine default. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR")
    TObjectPtr<UMaterialInterface> SurfaceMaterial;

    /** Rebuild the mesh whenever a UPROPERTY changes in the editor. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR")
    bool bAutoRebuildInEditor = true;

    // -----------------------------------------------------------------
    // Occupation animation (k_space_occupation module)
    // -----------------------------------------------------------------

    /** Modulate band colors by delta_n_cond(k,t). Off => flat band palette. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR|Occupation")
    bool bShowOccupation = true;

    /** Which occupation snapshot to display. Scrub this in the editor. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR|Occupation",
              meta = (ClampMin = "0"))
    int32 SnapshotIndex = 0;

    /** Brightness response to delta_n_cond. Higher => hot k-pockets pop sooner. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR|Occupation",
              meta = (ClampMin = "0.0"))
    float OccupationGain = 3.0f;

    /** Floor brightness for unexcited conduction / fully depleted valence (0..1). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR|Occupation",
              meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float DimFloor = 0.2f;

    /** Auto-advance snapshots during PIE (press Play). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR|Occupation")
    bool bAnimateInPlay = true;

    /** Real seconds spent on each snapshot during playback. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HHG-XR|Occupation",
              meta = (ClampMin = "0.01"))
    float SecondsPerSnapshot = 0.6f;

    // -----------------------------------------------------------------
    // Actions (Blueprint + editor button)
    // -----------------------------------------------------------------

    /** Reload the bundle and rebuild every band surface. */
    UFUNCTION(BlueprintCallable, CallInEditor, Category = "HHG-XR")
    void RebuildFromBundle();

    /** Re-color the existing surfaces for the current SnapshotIndex (cheap). */
    UFUNCTION(BlueprintCallable, CallInEditor, Category = "HHG-XR")
    void ApplySnapshot();

    /** Clear all mesh sections without touching BundleDirAbs. */
    UFUNCTION(BlueprintCallable, CallInEditor, Category = "HHG-XR")
    void ClearMesh();

protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

#if WITH_EDITOR
    virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "HHG-XR|Components")
    TObjectPtr<UProceduralMeshComponent> MeshComponent;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "HHG-XR|Components")
    TObjectPtr<UTextRenderComponent> ProvenanceBadge;

private:
    void BuildBandSurfaces(const FHHGXRBundle& Bundle);

    // Cached state so ApplySnapshot avoids re-reading the bundle.
    UPROPERTY(Transient) TArray<FHHGXRBandSectionCache> BandCache;
    UPROPERTY(Transient) FHHGXROccupationPreview OccCache;

    FString ProvenanceBaseText;
    int32 NValence = 0;
    bool bIsPlaying = false;
    float AnimAccumSeconds = 0.0f;
};
