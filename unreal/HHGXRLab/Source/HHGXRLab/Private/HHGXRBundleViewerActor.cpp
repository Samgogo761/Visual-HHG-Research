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
} // namespace


AHHGXRBundleViewerActor::AHHGXRBundleViewerActor()
{
    PrimaryActorTick.bCanEverTick = false;

    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);

    MeshComponent = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("BandSurfaces"));
    MeshComponent->SetupAttachment(Root);
    MeshComponent->bUseAsyncCooking = false;

    ProvenanceBadge = CreateDefaultSubobject<UTextRenderComponent>(TEXT("ProvenanceBadge"));
    ProvenanceBadge->SetupAttachment(Root);
    ProvenanceBadge->SetRelativeLocation(FVector(0.0f, 0.0f, BadgeHeight));
    ProvenanceBadge->SetHorizontalAlignment(EHTA_Center);
    ProvenanceBadge->SetVerticalAlignment(EVRTA_TextBottom);
    ProvenanceBadge->SetTextRenderColor(FColor(220, 220, 220));
    ProvenanceBadge->SetText(FText::FromString(TEXT("HHG-XR (no bundle loaded)")));
    ProvenanceBadge->SetWorldSize(40.0f);
}

void AHHGXRBundleViewerActor::BeginPlay()
{
    Super::BeginPlay();
    if (!BundleDirAbs.IsEmpty())
    {
        RebuildFromBundle();
    }
}

#if WITH_EDITOR
void AHHGXRBundleViewerActor::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
    Super::PostEditChangeProperty(PropertyChangedEvent);
    if (bAutoRebuildInEditor)
    {
        if (ProvenanceBadge)
        {
            ProvenanceBadge->SetRelativeLocation(FVector(0.0f, 0.0f, BadgeHeight));
        }
        if (!BundleDirAbs.IsEmpty())
        {
            RebuildFromBundle();
        }
        else
        {
            ClearMesh();
        }
    }
}
#endif

void AHHGXRBundleViewerActor::ClearMesh()
{
    if (MeshComponent)
    {
        MeshComponent->ClearAllMeshSections();
    }
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

    BuildBandSurfaces(Bundle);
    UpdateProvenanceBadge(Bundle);
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

    for (int32 Band = 0; Band < NumBands; ++Band)
    {
        TArray<FVector> Vertices;
        TArray<int32> Triangles;
        TArray<FVector> Normals;
        TArray<FVector2D> UV0;
        TArray<FProcMeshTangent> Tangents;
        TArray<FLinearColor> VertexColors;

        const int32 NumVerts = NumRows * NumCols;
        Vertices.Reserve(NumVerts);
        VertexColors.Reserve(NumVerts);
        Normals.Reserve(NumVerts);
        UV0.Reserve(NumVerts);
        Tangents.Reserve(NumVerts);

        const FLinearColor BandColor = BandPalette[Band % UE_ARRAY_COUNT(BandPalette)];

        for (int32 I = 0; I < NumRows; ++I)
        {
            for (int32 J = 0; J < NumCols; ++J)
            {
                const float Kx = bHave2DGrid ? BGP.KxGrid.At(I, J) : BGP.Kx[I];
                const float Ky = bHave2DGrid ? BGP.KyGrid.At(I, J) : BGP.Ky[J];
                const float E  = EStack.At(Band, I, J);

                Vertices.Add(FVector(Kx * KScale, Ky * KScale, E * EScale));
                VertexColors.Add(BandColor);
                Normals.Add(FVector(0.0f, 0.0f, 1.0f));
                UV0.Add(FVector2D(
                    static_cast<float>(I) / static_cast<float>(FMath::Max(1, NumRows - 1)),
                    static_cast<float>(J) / static_cast<float>(FMath::Max(1, NumCols - 1))));
                Tangents.Add(FProcMeshTangent(1.0f, 0.0f, 0.0f));
            }
        }

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
            Band, Vertices, Triangles, Normals, UV0, VertexColors, Tangents,
            /*bCreateCollision*/ false);

        if (SurfaceMaterial)
        {
            MeshComponent->SetMaterial(Band, SurfaceMaterial);
        }
    }

    UE_LOG(LogHHGXRViewer, Log,
        TEXT("HHG-XR: built %d band surface(s), %dx%d grid, %d triangles total."),
        NumBands, NumRows, NumCols, TotalTris);
}

void AHHGXRBundleViewerActor::UpdateProvenanceBadge(const FHHGXRBundle& Bundle)
{
    if (!ProvenanceBadge) return;

    const FHHGXRManifest& M = Bundle.Manifest;
    const FString Badge = FString::Printf(
        TEXT("%s | %s | field: %s"),
        *M.Provenance.SourceClass,
        *M.Provenance.GaugeMethod,
        *UHHGXRBundleLoader::FieldSourceBadge(Bundle.Data.Field));

    ProvenanceBadge->SetText(FText::FromString(Badge));

    const FLinearColor C = UHHGXRBundleLoader::FieldSourceColor(Bundle.Data.Field.Source);
    ProvenanceBadge->SetTextRenderColor(C.ToFColor(/*bSRGB*/ true));
}
