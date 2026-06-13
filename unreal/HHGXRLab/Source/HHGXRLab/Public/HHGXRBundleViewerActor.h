// HHG-XR Lab reference viewer Actor.
//
// Drop into a level, set BundleDirAbs in the Details panel, and the Actor
// loads the bundle and builds a 3D ProceduralMeshComponent band surface
// per selected band, plus a 3D text provenance badge. Mesh rebuilds on
// editor property change so the workflow is "drop-and-tweak", no Play
// required.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "UObject/ObjectPtr.h"
#include "HHGXRBundleViewerActor.generated.h"

class UProceduralMeshComponent;
class UTextRenderComponent;
class UMaterialInterface;
struct FHHGXRBundle;

UCLASS(BlueprintType, meta = (DisplayName = "HHG-XR Bundle Viewer"))
class HHGXRLAB_API AHHGXRBundleViewerActor : public AActor
{
    GENERATED_BODY()

public:
    AHHGXRBundleViewerActor();

    // -----------------------------------------------------------------
    // Editable properties
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
    // Actions (Blueprint + editor button)
    // -----------------------------------------------------------------

    /** Reload the bundle and rebuild every band surface. */
    UFUNCTION(BlueprintCallable, CallInEditor, Category = "HHG-XR")
    void RebuildFromBundle();

    /** Clear all mesh sections without touching BundleDirAbs. */
    UFUNCTION(BlueprintCallable, CallInEditor, Category = "HHG-XR")
    void ClearMesh();

protected:
    virtual void BeginPlay() override;

#if WITH_EDITOR
    virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "HHG-XR|Components")
    TObjectPtr<UProceduralMeshComponent> MeshComponent;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "HHG-XR|Components")
    TObjectPtr<UTextRenderComponent> ProvenanceBadge;

private:
    void BuildBandSurfaces(const FHHGXRBundle& Bundle);
    void UpdateProvenanceBadge(const FHHGXRBundle& Bundle);
};
