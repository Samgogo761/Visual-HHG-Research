#include "HHGXRBundleViewerActor.h"

#include "Components/TextRenderComponent.h"
#include "HHGXRBundleLoader.h"
#include "ProceduralMeshComponent.h"

DEFINE_LOG_CATEGORY_STATIC(LogHHGXRViewer, Log, All);

namespace
{
    // Eight visually distinct colours that the band sections cycle through.
    const FLinearColor BandPalette[] = {
        FLinearColor(0.95f, 0.30f, 0.30f),  // red
        FLinearColor(0.95f, 0.60f, 0.20f),  // orange
        FLinearColor(0.90f, 0.90f, 0.20f),  // yellow
        FLinearColor(0.30f, 0.90f, 0.30f),  // green
        FLinearColor(0.20f, 0.85f, 0.85f),  // cyan
        FLinearColor(0.35f, 0.50f, 1.00f),  // blue
        FLinearColor(0.70f, 0.30f, 1.00f),  // purple
        FLinearColor(1.00f, 0.45f, 0.80f),  // pink
    };

    // Nearest-neighbour sample of a 2D grid at a band-vertex index, so the
    // occupation grid and the band grid need not have identical dimensions.
    float SampleGrid(const FHHGXRFloatGrid2D& G, int32 I, int32 J,
                     int32 NumRows, int32 NumCols)
    {
        if (!G.IsValid2D()) return 0.0f;
        const int32 GI = (NumRows <= 1) ? 0
            : FMath::RoundToInt(static_cast<float>(I) * (G.NumRows - 1) / (NumRows - 1));
        const int32 GJ = (NumCols <= 1) ? 0
            : FMath::RoundToInt(static_cast<float>(J) * (G.NumCols - 1) / (NumCols - 1));
        return G.At(FMath::Clamp(GI, 0, G.NumRows - 1),
                    FMath::Clamp(GJ, 0, G.NumCols - 1));
    }
} // namespace


AHHGXRBundleViewerActor::AHHGXRBundleViewerActor()
{
    PrimaryActorTick.bCanEverTick = true;

    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);

    MeshComponent = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("BandSurfaces"));
    MeshComponent->SetupAttachment(Root);
    MeshComponent->bUseAsyncCooking = false;

    ProvenanceBadge = CreateDefaultSubobject<UTextRenderComponent>(TEXT("ProvenanceBadge"));
    ProvenanceBadge->SetupAttachment(Root);
    ProvenanceBadge->SetRelativeLocation(FVector(0.0f, 0.0f, BadgeHeight));
    // Default text faces +X; flip so it reads from the common -X viewpoint.
    ProvenanceBadge->SetRelativeRotation(FRotator(0.0f, 180.0f, 0.0f));
    ProvenanceBadge->SetHorizontalAlignment(EHTA_Center);
    ProvenanceBadge->SetVerticalAlignment(EVRTA_TextBottom);
    ProvenanceBadge->SetTextRenderColor(FColor(220, 220, 220));
    ProvenanceBadge->SetText(FText::FromString(TEXT("HHG-XR (no bundle loaded)")));
    ProvenanceBadge->SetWorldSize(40.0f);
}

void AHHGXRBundleViewerActor::BeginPlay()
{
    Super::BeginPlay();
    bIsPlaying = true;
    AnimAccumSeconds = 0.0f;
    if (!BundleDirAbs.IsEmpty())
    {
        RebuildFromBundle();
    }
}

void AHHGXRBundleViewerActor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bIsPlaying || !bAnimateInPlay || !bShowOccupation) return;

    const int32 NumSnaps = OccCache.Snapshots.Num();
    if (NumSnaps <= 1) return;

    AnimAccumSeconds += DeltaSeconds;
    if (AnimAccumSeconds >= SecondsPerSnapshot)
    {
        AnimAccumSeconds = 0.0f;
        SnapshotIndex = (SnapshotIndex + 1) % NumSnaps;
        ApplySnapshot();
    }
}

#if WITH_EDITOR
void AHHGXRBundleViewerActor::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
    Super::PostEditChangeProperty(PropertyChangedEvent);
    if (!bAutoRebuildInEditor) return;

    if (ProvenanceBadge)
    {
        ProvenanceBadge->SetRelativeLocation(FVector(0.0f, 0.0f, BadgeHeight));
    }

    static const TSet<FName> ColorOnly = {
        TEXT("SnapshotIndex"), TEXT("OccupationGain"),
        TEXT("DimFloor"), TEXT("bShowOccupation")
    };
    const FName Changed = PropertyChangedEvent.GetPropertyName();
    if (ColorOnly.Contains(Changed) && BandCache.Num() > 0)
    {
        ApplySnapshot();
    }
    else if (!BundleDirAbs.IsEmpty())
    {
        RebuildFromBundle();
    }
    else
    {
        ClearMesh();
    }
}
#endif

void AHHGXRBundleViewerActor::ClearMesh()
{
    if (MeshComponent)
    {
        MeshComponent->ClearAllMeshSections();
    }
    BandCache.Reset();
    OccCache = FHHGXROccupationPreview();
    if (ProvenanceBadge)
    {
        ProvenanceBadge->SetText(FText::FromString(TEXT("HHG-XR (no bundle loaded)")));
        ProvenanceBadge->SetTextRenderColor(FColor(220, 220, 220));
    }
}

void AHHGXRBundleViewerActor::RebuildFromBundle()
{
    ClearMesh();
    if (BundleDirAbs.IsEmpty())
    {
        UE_LOG(LogHHGXRViewer, Log, TEXT("BundleDirAbs is empty; nothing to render."));
        return;
    }

    FHHGXRBundle Bundle;
    FString Error;
    if (!UHHGXRBundleLoader::LoadBundle(BundleDirAbs, Bundle, Error))
    {
        UE_LOG(LogHHGXRViewer, Error, TEXT("Bundle load failed: %s"), *Error);
        if (ProvenanceBadge)
        {
            ProvenanceBadge->SetText(FText::FromString(
                FString::Printf(TEXT("LOAD FAILED: %s"), *Error)));
            ProvenanceBadge->SetTextRenderColor(FColor(220, 60, 60));
        }
        return;
    }

    // Cache animation state.
    OccCache = Bundle.Data.OccupationPreview;
    NValence = Bundle.Manifest.Dimensions.NValence;
    ProvenanceBaseText = FString::Printf(TEXT("%s | %s | field: %s"),
        *Bundle.Manifest.Provenance.SourceClass,
        *Bundle.Manifest.Provenance.GaugeMethod,
        *UHHGXRBundleLoader::FieldSourceBadge(Bundle.Data.Field));
    if (ProvenanceBadge)
    {
        const FLinearColor C = UHHGXRBundleLoader::FieldSourceColor(Bundle.Data.Field.Source);
        ProvenanceBadge->SetTextRenderColor(C.ToFColor(/*bSRGB*/ true));
    }

    BuildBandSurfaces(Bundle);
    ApplySnapshot();
}

void AHHGXRBundleViewerActor::BuildBandSurfaces(const FHHGXRBundle& Bundle)
{
    const FHHGXRBandGridPreview& BGP = Bundle.Data.BandGridPreview;
    const FHHGXRFloatStack3D& EStack = BGP.EnergiesEv;

    if (EStack.NumSlices == 0 || EStack.NumRows == 0 || EStack.NumCols == 0)
    {
        UE_LOG(LogHHGXRViewer, Warning,
            TEXT("band_grid_preview is empty; no band surfaces built."));
        return;
    }

    const bool bHave2DGrid = BGP.KxGrid.IsValid2D() && BGP.KyGrid.IsValid2D();
    const bool bHave1DAxes = (BGP.Kx.Num() == EStack.NumRows)
                          && (BGP.Ky.Num() == EStack.NumCols);
    if (!bHave2DGrid && !bHave1DAxes)
    {
        UE_LOG(LogHHGXRViewer, Warning,
            TEXT("band_grid_preview has neither 2D nor 1D k coordinates."));
        return;
    }

    const int32 NumRows = EStack.NumRows;
    const int32 NumCols = EStack.NumCols;
    const int32 NumBands = EStack.NumSlices;
    int32 TotalTris = 0;

    BandCache.Reset();
    BandCache.Reserve(NumBands);

    for (int32 Band = 0; Band < NumBands; ++Band)
    {
        FHHGXRBandSectionCache BC;
        BC.NumRows = NumRows;
        BC.NumCols = NumCols;
        BC.BaseColor = BandPalette[Band % UE_ARRAY_COUNT(BandPalette)];
        BC.GlobalBandIndex = BGP.SelectedBandIndices.IsValidIndex(Band)
            ? BGP.SelectedBandIndices[Band] : (Band + 1);
        // n_val valence bands are 1..NValence; anything above is conduction.
        BC.bConduction = (NValence <= 0) ? true : (BC.GlobalBandIndex > NValence);

        const int32 NumVerts = NumRows * NumCols;
        BC.Vertices.Reserve(NumVerts);
        BC.Normals.Reserve(NumVerts);
        BC.UV0.Reserve(NumVerts);
        BC.Tangents.Reserve(NumVerts);
        TArray<FLinearColor> InitColors;
        InitColors.Reserve(NumVerts);

        for (int32 I = 0; I < NumRows; ++I)
        {
            for (int32 J = 0; J < NumCols; ++J)
            {
                const float Kx = bHave2DGrid ? BGP.KxGrid.At(I, J) : BGP.Kx[I];
                const float Ky = bHave2DGrid ? BGP.KyGrid.At(I, J) : BGP.Ky[J];
                const float E  = EStack.At(Band, I, J);

                BC.Vertices.Add(FVector(Kx * KScale, Ky * KScale, E * EScale));
                BC.Normals.Add(FVector(0.0f, 0.0f, 1.0f));
                BC.UV0.Add(FVector2D(
                    static_cast<float>(I) / static_cast<float>(FMath::Max(1, NumRows - 1)),
                    static_cast<float>(J) / static_cast<float>(FMath::Max(1, NumCols - 1))));
                BC.Tangents.Add(FProcMeshTangent(1.0f, 0.0f, 0.0f));
                InitColors.Add(BC.BaseColor);
            }
        }

        TArray<int32> Triangles;
        Triangles.Reserve((NumRows - 1) * (NumCols - 1) * 6);
        for (int32 I = 0; I < NumRows - 1; ++I)
        {
            for (int32 J = 0; J < NumCols - 1; ++J)
            {
                const int32 V00 = I * NumCols + J;
                const int32 V10 = (I + 1) * NumCols + J;
                const int32 V01 = I * NumCols + (J + 1);
                const int32 V11 = (I + 1) * NumCols + (J + 1);
                Triangles.Add(V00); Triangles.Add(V10); Triangles.Add(V11);
                Triangles.Add(V00); Triangles.Add(V11); Triangles.Add(V01);
            }
        }
        TotalTris += Triangles.Num() / 3;

        MeshComponent->CreateMeshSection_LinearColor(
            Band, BC.Vertices, Triangles, BC.Normals, BC.UV0, InitColors, BC.Tangents,
            /*bCreateCollision*/ false);
        if (SurfaceMaterial)
        {
            MeshComponent->SetMaterial(Band, SurfaceMaterial);
        }

        BandCache.Add(MoveTemp(BC));
    }

    UE_LOG(LogHHGXRViewer, Log,
        TEXT("HHG-XR: built %d band surface(s), %dx%d grid, %d triangles total."),
        NumBands, NumRows, NumCols, TotalTris);
}

void AHHGXRBundleViewerActor::ApplySnapshot()
{
    if (BandCache.Num() == 0)
    {
        if (!BundleDirAbs.IsEmpty())
        {
            RebuildFromBundle();
        }
        return;
    }

    const int32 NumSnaps = OccCache.Snapshots.Num();
    const bool bUseOcc = bShowOccupation && NumSnaps > 0;
    if (bUseOcc)
    {
        SnapshotIndex = FMath::Clamp(SnapshotIndex, 0, NumSnaps - 1);
    }

    const FHHGXRFloatGrid2D* Delta = nullptr;
    float TimeFs = 0.0f;
    if (bUseOcc)
    {
        Delta = &OccCache.Snapshots[SnapshotIndex].DeltaNCond;
        TimeFs = OccCache.Snapshots[SnapshotIndex].TimeFs;
    }

    for (int32 S = 0; S < BandCache.Num(); ++S)
    {
        const FHHGXRBandSectionCache& BC = BandCache[S];
        TArray<FLinearColor> Colors;
        Colors.SetNumUninitialized(BC.Vertices.Num());

        for (int32 I = 0; I < BC.NumRows; ++I)
        {
            for (int32 J = 0; J < BC.NumCols; ++J)
            {
                const int32 V = I * BC.NumCols + J;
                float Bright = 1.0f;
                if (bUseOcc && Delta)
                {
                    const float Occ = SampleGrid(*Delta, I, J, BC.NumRows, BC.NumCols);
                    const float Drive = FMath::Clamp(OccupationGain * Occ, 0.0f, 1.0f);
                    Bright = BC.bConduction
                        ? FMath::Lerp(DimFloor, 1.0f, Drive)   // conduction lights up
                        : FMath::Lerp(1.0f, DimFloor, Drive);  // valence depletes
                }
                FLinearColor C = BC.BaseColor * Bright;
                C.A = 1.0f;
                Colors[V] = C;
            }
        }

        MeshComponent->UpdateMeshSection_LinearColor(
            S, BC.Vertices, BC.Normals, BC.UV0, Colors, BC.Tangents);
    }

    if (ProvenanceBadge)
    {
        FString Text = ProvenanceBaseText;
        if (bUseOcc)
        {
            Text += FString::Printf(TEXT("\nt = %.1f fs   (snap %d/%d)"),
                TimeFs, SnapshotIndex + 1, NumSnaps);
        }
        ProvenanceBadge->SetText(FText::FromString(Text));
    }
}
