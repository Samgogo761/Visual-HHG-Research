// HHG-XR Lab demo bundle data types (schema id: hhgxr-demo-bundle-v0).
//
// One USTRUCT per block of data_small.json / manifest.json. 2D and 3D
// numeric tables use row-major flat storage so they remain
// Blueprint-friendly while staying contiguous in memory.
//
// Field-name convention: UpperCamelCase in C++; the JSON keys are the
// snake_case names from docs/DATA_SCHEMA.md and are mapped explicitly
// by HHGXRBundleLoader.cpp.

#pragma once

#include "CoreMinimal.h"
#include "HHGXRTypes.generated.h"


// ---------------------------------------------------------------------
// Numeric container helpers
// ---------------------------------------------------------------------

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRFloatGrid2D
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NumRows = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NumCols = 0;

    /** Row-major flat storage, size = NumRows * NumCols. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    TArray<float> Flat;

    FORCEINLINE float At(int32 Row, int32 Col) const
    {
        return Flat[Row * NumCols + Col];
    }

    FORCEINLINE bool IsValid2D() const
    {
        return NumRows > 0 && NumCols > 0 && Flat.Num() == NumRows * NumCols;
    }
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRIntGrid2D
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NumRows = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NumCols = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    TArray<int32> Flat;

    FORCEINLINE int32 At(int32 Row, int32 Col) const
    {
        return Flat[Row * NumCols + Col];
    }
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRFloatStack3D
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NumSlices = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NumRows = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NumCols = 0;

    /** Row-major flat storage indexed as ((Slice * NumRows) + Row) * NumCols + Col. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    TArray<float> Flat;

    FORCEINLINE float At(int32 Slice, int32 Row, int32 Col) const
    {
        return Flat[(Slice * NumRows + Row) * NumCols + Col];
    }
};


// ---------------------------------------------------------------------
// manifest.json
// ---------------------------------------------------------------------

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRProvenance
{
    GENERATED_BODY()

    /** "Data-driven", "Model-based", "Literature-reproduced", "Conceptual-only". */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FString SourceClass;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FString Material;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FString Model;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FString GaugeMethod;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FString Confidence;
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRDimensions
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 Nt = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 Nkx = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 Nky = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NBands = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NValence = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NOccupationSnapshots = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NCoherenceSnapshots = 0;
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRManifest
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FString Schema;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FString DatasetName;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FHHGXRProvenance Provenance;

    /** Raw stringified key->value (numbers and strings both stringified). */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    TMap<FString, FString> Units;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FHHGXRDimensions Dimensions;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    TArray<FString> AvailableModules;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    TArray<FString> MissingModules;

    /** "data_small", "quicklook", optional "data_arrays" -> bundle-relative path. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    TMap<FString, FString> Files;

    /** Sanitized source paths (always <LOCAL_*> placeholders). */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    TMap<FString, FString> SourcePaths;
};


// ---------------------------------------------------------------------
// data_small.json: time-series and spectra
// ---------------------------------------------------------------------

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRTimeSeries
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> TimeFs;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> Jx;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> Jy;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> JxIntra;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> JyIntra;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> JxInter;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> JyInter;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> JxK;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> JyK;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> JxKp;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> JyKp;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> EtaX;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> EtaY;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> JxSpin;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> JySpin;
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRSpectrum
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> HarmonicOrder;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> OmegaAu;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> HHGx;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> HHGy;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> HHGTotal;
};


// ---------------------------------------------------------------------
// data_small.json: band_path (Wannier90 long format or wide)
// ---------------------------------------------------------------------

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRBandPath
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    TArray<float> KPath;

    /** Shape: [n_k][n_bands]. EnergyEv.NumRows = KPath.Num(). */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FHHGXRFloatGrid2D EnergyEv;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 NBands = 0;

    /** "wannier90_long" or "wide". */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    FString Layout;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    float EFermiEv = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    bool bHasEFermi = false;

    /** Default render subset (0-based). Capped by converter --max-near-gap-bands. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    TArray<int32> NearGapBandIndices;

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    float NearGapWindowEv = 5.0f;

    /** 0 for wide layout, 0 for wannier90_long, present for API symmetry. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR")
    int32 BandIndexBase = 0;
};


// ---------------------------------------------------------------------
// data_small.json: band_grid / geometry / occupation / coherence previews
// ---------------------------------------------------------------------

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRBandGridPreview
{
    GENERATED_BODY()

    /** 2D cartesian k grids (long-format solver output). */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D KxGrid;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D KyGrid;

    /** Separable 1D fallback for the legacy wide bands.dat layout. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> Kx;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> Ky;

    /** Solver band numbers (1-based for long, 0-based for wide). */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<int32> SelectedBandIndices;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") int32 BandIndexBase = 1;

    /** Shape: [n_sel][nkx][nky]. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatStack3D EnergiesEv;
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRQuantumGeometryPreview
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D KxGrid;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D KyGrid;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<int32> SelectedBandIndices;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") int32 BandIndexBase = 1;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatStack3D BerryCurvatureAu;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatStack3D TraceQuantumMetricAu;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRIntGrid2D ValleyId;

    /** Mandatory rendering caveat for AFM datasets (PT symmetry forces Omega ~ 0). */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FString Note;
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXROccupationSnapshot
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") float TimeFs = 0.0f;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D NVal;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D NCond;
    /** n_cond(t) - n_cond(t0). Recommended primary render channel. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D DeltaNCond;
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXROccupationPreview
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D KxGrid;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D KyGrid;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<FHHGXROccupationSnapshot> Snapshots;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FString Definition;
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRCoherenceSnapshot
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") float TimeFs = 0.0f;
    /** coherence_norm(k,t) = sqrt(sum_{m!=n} |rho_mn|^2). Zero at t=0 by construction. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D CoherenceNorm;
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRCoherencePreview
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D KxGrid;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFloatGrid2D KyGrid;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<FHHGXRCoherenceSnapshot> Snapshots;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FString Definition;
};


// ---------------------------------------------------------------------
// data_small.json: field block (E(t), A(t))
// ---------------------------------------------------------------------

UENUM(BlueprintType)
enum class EHHGXRFieldSource : uint8
{
    RawSolverOutput      UMETA(DisplayName = "Raw solver output"),
    ReconstructedNotRaw  UMETA(DisplayName = "Reconstructed (not raw)"),
    Unavailable          UMETA(DisplayName = "Unavailable"),
    Unknown              UMETA(DisplayName = "Unknown")
};

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRFieldBlock
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> TimeFs;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> Ex;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> Ey;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> Ax;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<float> Ay;

    /** Raw label as written into JSON (e.g. "raw_solver_output"). */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FString SourceRaw;

    /** Parsed enum; legacy *_verified / *_unverified labels collapse to ReconstructedNotRaw. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") EHHGXRFieldSource Source = EHHGXRFieldSource::Unknown;

    /** Populated when Source == ReconstructedNotRaw. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<FString> ReconstructedFrom;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TArray<FString> CrossCheckedWith;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") TMap<FString, FString> CrossCheck;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FString Note;

    /** Populated when Source == RawSolverOutput. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FString RawSourceFile;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FString RawSourceColumns;
};


// ---------------------------------------------------------------------
// data_small.json top-level container
// ---------------------------------------------------------------------

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRDataSmall
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRTimeSeries TimeSeries;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRSpectrum Spectrum;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRSpectrum SpectrumSpin;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") bool bHasSpectrumSpin = false;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRBandPath BandPath;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRBandGridPreview BandGridPreview;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRQuantumGeometryPreview QuantumGeometryPreview;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") bool bHasQuantumGeometry = false;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXROccupationPreview OccupationPreview;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") bool bHasOccupationPreview = false;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRCoherencePreview CoherencePreview;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") bool bHasCoherencePreview = false;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRFieldBlock Field;
};


// ---------------------------------------------------------------------
// Manifest + data + bundle paths
// ---------------------------------------------------------------------

USTRUCT(BlueprintType)
struct HHGXRLAB_API FHHGXRBundle
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRManifest Manifest;
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FHHGXRDataSmall Data;

    /** Absolute path passed to LoadBundle. */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FString BundleDir;

    /** Resolved quicklook PNG path (empty when missing). */
    UPROPERTY(BlueprintReadOnly, Category = "HHG-XR") FString QuicklookPath;
};
