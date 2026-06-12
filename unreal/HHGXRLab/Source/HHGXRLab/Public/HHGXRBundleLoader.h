// HHG-XR Lab demo bundle loader.
//
// Single Blueprint Function Library so that game code, editor widgets,
// and Blueprints can all share the same on-disk schema parser.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "HHGXRTypes.h"
#include "HHGXRBundleLoader.generated.h"

UCLASS()
class HHGXRLAB_API UHHGXRBundleLoader : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /**
     * Open manifest.json and data_small.json from an HHG-XR Lab demo bundle.
     *
     * @param BundleDirAbs  Absolute path to a directory containing
     *                      manifest.json (schema id: "hhgxr-demo-bundle-v0").
     * @param OutBundle     Filled on success.
     * @param OutError      Human-readable error string on failure.
     * @return true on success.
     */
    UFUNCTION(BlueprintCallable, Category = "HHG-XR|Bundle")
    static bool LoadBundle(const FString& BundleDirAbs,
                           FHHGXRBundle& OutBundle,
                           FString& OutError);

    /** True iff ModuleName appears in Manifest.AvailableModules. */
    UFUNCTION(BlueprintPure, Category = "HHG-XR|Manifest")
    static bool HasModule(const FHHGXRManifest& Manifest, const FString& ModuleName);

    /** Display-friendly badge text driven by EHHGXRFieldSource. */
    UFUNCTION(BlueprintPure, Category = "HHG-XR|Field")
    static FString FieldSourceBadge(const FHHGXRFieldBlock& Field);

    /** Map an EHHGXRFieldSource to a (R, G, B) hint suitable for a UMG color block. */
    UFUNCTION(BlueprintPure, Category = "HHG-XR|Field")
    static FLinearColor FieldSourceColor(EHHGXRFieldSource Source);
};
