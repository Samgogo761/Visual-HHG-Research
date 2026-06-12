#include "HHGXRBundleLoader.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

DEFINE_LOG_CATEGORY_STATIC(LogHHGXR, Log, All);

namespace
{
    // -----------------------------------------------------------------
    // Low-level JSON readers
    // -----------------------------------------------------------------

    bool ReadJsonObject(const FString& Path, TSharedPtr<FJsonObject>& Out, FString& OutError)
    {
        FString Raw;
        if (!FFileHelper::LoadFileToString(Raw, *Path))
        {
            OutError = FString::Printf(TEXT("Failed to read file: %s"), *Path);
            return false;
        }
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Raw);
        if (!FJsonSerializer::Deserialize(Reader, Out) || !Out.IsValid())
        {
            OutError = FString::Printf(TEXT("Invalid JSON: %s"), *Path);
            return false;
        }
        return true;
    }

    void ReadFloatArray(const TSharedPtr<FJsonObject>& Obj, const FString& Key, TArray<float>& Out)
    {
        Out.Reset();
        if (!Obj.IsValid()) return;
        const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
        if (!Obj->TryGetArrayField(Key, Arr) || !Arr) return;
        Out.Reserve(Arr->Num());
        for (const TSharedPtr<FJsonValue>& V : *Arr)
        {
            Out.Add(static_cast<float>(V->AsNumber()));
        }
    }

    void ReadIntArray(const TSharedPtr<FJsonObject>& Obj, const FString& Key, TArray<int32>& Out)
    {
        Out.Reset();
        if (!Obj.IsValid()) return;
        const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
        if (!Obj->TryGetArrayField(Key, Arr) || !Arr) return;
        Out.Reserve(Arr->Num());
        for (const TSharedPtr<FJsonValue>& V : *Arr)
        {
            Out.Add(static_cast<int32>(V->AsNumber()));
        }
    }

    void ReadStringArray(const TSharedPtr<FJsonObject>& Obj, const FString& Key, TArray<FString>& Out)
    {
        Out.Reset();
        if (!Obj.IsValid()) return;
        const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
        if (!Obj->TryGetArrayField(Key, Arr) || !Arr) return;
        Out.Reserve(Arr->Num());
        for (const TSharedPtr<FJsonValue>& V : *Arr)
        {
            Out.Add(V->AsString());
        }
    }

    void ReadFloatGrid2D(const TSharedPtr<FJsonObject>& Obj, const FString& Key, FHHGXRFloatGrid2D& Out)
    {
        Out = FHHGXRFloatGrid2D();
        if (!Obj.IsValid()) return;
        const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
        if (!Obj->TryGetArrayField(Key, Rows) || !Rows || Rows->Num() == 0) return;

        const int32 NumRows = Rows->Num();
        const TArray<TSharedPtr<FJsonValue>>& Row0 = (*Rows)[0]->AsArray();
        const int32 NumCols = Row0.Num();
        if (NumCols == 0) return;

        Out.NumRows = NumRows;
        Out.NumCols = NumCols;
        Out.Flat.SetNumUninitialized(NumRows * NumCols);
        for (int32 R = 0; R < NumRows; ++R)
        {
            const TArray<TSharedPtr<FJsonValue>>& Row = (*Rows)[R]->AsArray();
            const int32 Cols = FMath::Min(Row.Num(), NumCols);
            for (int32 C = 0; C < Cols; ++C)
            {
                Out.Flat[R * NumCols + C] = static_cast<float>(Row[C]->AsNumber());
            }
            for (int32 C = Cols; C < NumCols; ++C)
            {
                Out.Flat[R * NumCols + C] = 0.0f;
            }
        }
    }

    void ReadIntGrid2D(const TSharedPtr<FJsonObject>& Obj, const FString& Key, FHHGXRIntGrid2D& Out)
    {
        Out = FHHGXRIntGrid2D();
        if (!Obj.IsValid()) return;
        const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
        if (!Obj->TryGetArrayField(Key, Rows) || !Rows || Rows->Num() == 0) return;

        const int32 NumRows = Rows->Num();
        const TArray<TSharedPtr<FJsonValue>>& Row0 = (*Rows)[0]->AsArray();
        const int32 NumCols = Row0.Num();
        if (NumCols == 0) return;

        Out.NumRows = NumRows;
        Out.NumCols = NumCols;
        Out.Flat.SetNumUninitialized(NumRows * NumCols);
        for (int32 R = 0; R < NumRows; ++R)
        {
            const TArray<TSharedPtr<FJsonValue>>& Row = (*Rows)[R]->AsArray();
            const int32 Cols = FMath::Min(Row.Num(), NumCols);
            for (int32 C = 0; C < Cols; ++C)
            {
                Out.Flat[R * NumCols + C] = static_cast<int32>(Row[C]->AsNumber());
            }
            for (int32 C = Cols; C < NumCols; ++C)
            {
                Out.Flat[R * NumCols + C] = 0;
            }
        }
    }

    void ReadFloatStack3D(const TSharedPtr<FJsonObject>& Obj, const FString& Key, FHHGXRFloatStack3D& Out)
    {
        Out = FHHGXRFloatStack3D();
        if (!Obj.IsValid()) return;
        const TArray<TSharedPtr<FJsonValue>>* Slices = nullptr;
        if (!Obj->TryGetArrayField(Key, Slices) || !Slices || Slices->Num() == 0) return;

        const int32 NumSlices = Slices->Num();
        const TArray<TSharedPtr<FJsonValue>>& Slice0 = (*Slices)[0]->AsArray();
        const int32 NumRows = Slice0.Num();
        if (NumRows == 0) return;
        const TArray<TSharedPtr<FJsonValue>>& Row0 = Slice0[0]->AsArray();
        const int32 NumCols = Row0.Num();
        if (NumCols == 0) return;

        Out.NumSlices = NumSlices;
        Out.NumRows = NumRows;
        Out.NumCols = NumCols;
        Out.Flat.SetNumUninitialized(NumSlices * NumRows * NumCols);
        for (int32 S = 0; S < NumSlices; ++S)
        {
            const TArray<TSharedPtr<FJsonValue>>& Slice = (*Slices)[S]->AsArray();
            const int32 Rows = FMath::Min(Slice.Num(), NumRows);
            for (int32 R = 0; R < Rows; ++R)
            {
                const TArray<TSharedPtr<FJsonValue>>& Row = Slice[R]->AsArray();
                const int32 Cols = FMath::Min(Row.Num(), NumCols);
                for (int32 C = 0; C < Cols; ++C)
                {
                    Out.Flat[(S * NumRows + R) * NumCols + C] =
                        static_cast<float>(Row[C]->AsNumber());
                }
            }
        }
    }

    void ReadStringMapAsBest(const TSharedPtr<FJsonObject>& Obj, const FString& Key, TMap<FString, FString>& Out)
    {
        Out.Reset();
        if (!Obj.IsValid()) return;
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Obj->TryGetObjectField(Key, Sub) || !Sub || !Sub->IsValid()) return;
        for (const auto& Pair : (*Sub)->Values)
        {
            if (!Pair.Value.IsValid()) continue;
            switch (Pair.Value->Type)
            {
            case EJson::String:
                Out.Add(Pair.Key, Pair.Value->AsString());
                break;
            case EJson::Number:
                Out.Add(Pair.Key, FString::SanitizeFloat(Pair.Value->AsNumber()));
                break;
            case EJson::Boolean:
                Out.Add(Pair.Key, Pair.Value->AsBool() ? TEXT("true") : TEXT("false"));
                break;
            default:
                break;
            }
        }
    }

    bool TryGetDouble(const TSharedPtr<FJsonObject>& Obj, const FString& Key, double& Out)
    {
        if (!Obj.IsValid() || !Obj->HasField(Key)) return false;
        const TSharedPtr<FJsonValue> V = Obj->TryGetField(Key);
        if (!V.IsValid() || V->Type != EJson::Number) return false;
        Out = V->AsNumber();
        return true;
    }

    EHHGXRFieldSource ParseFieldSource(const FString& Raw)
    {
        if (Raw == TEXT("raw_solver_output") || Raw == TEXT("solver_native"))
            return EHHGXRFieldSource::RawSolverOutput;
        if (Raw == TEXT("reconstructed_from_input_nml_not_raw_output")
         || Raw == TEXT("reconstructed_from_input_nml_unverified")
         || Raw == TEXT("reconstructed_from_input_nml_verified"))
            return EHHGXRFieldSource::ReconstructedNotRaw;
        if (Raw == TEXT("unavailable"))
            return EHHGXRFieldSource::Unavailable;
        return EHHGXRFieldSource::Unknown;
    }


    // -----------------------------------------------------------------
    // manifest.json
    // -----------------------------------------------------------------

    void ParseProvenance(const TSharedPtr<FJsonObject>& Root, FHHGXRProvenance& Out)
    {
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Root->TryGetObjectField(TEXT("physics_provenance"), Sub) || !Sub) return;
        (*Sub)->TryGetStringField(TEXT("source_class"), Out.SourceClass);
        (*Sub)->TryGetStringField(TEXT("material"), Out.Material);
        (*Sub)->TryGetStringField(TEXT("model"), Out.Model);
        (*Sub)->TryGetStringField(TEXT("gauge_method"), Out.GaugeMethod);
        (*Sub)->TryGetStringField(TEXT("confidence"), Out.Confidence);
    }

    void ParseDimensions(const TSharedPtr<FJsonObject>& Root, FHHGXRDimensions& Out)
    {
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Root->TryGetObjectField(TEXT("dimensions"), Sub) || !Sub) return;
        int32 V = 0;
        if ((*Sub)->TryGetNumberField(TEXT("nt"), V))                       Out.Nt = V;
        if ((*Sub)->TryGetNumberField(TEXT("nkx"), V))                      Out.Nkx = V;
        if ((*Sub)->TryGetNumberField(TEXT("nky"), V))                      Out.Nky = V;
        if ((*Sub)->TryGetNumberField(TEXT("n_bands"), V))                  Out.NBands = V;
        if ((*Sub)->TryGetNumberField(TEXT("n_valence"), V))                Out.NValence = V;
        if ((*Sub)->TryGetNumberField(TEXT("n_occupation_snapshots"), V))   Out.NOccupationSnapshots = V;
        if ((*Sub)->TryGetNumberField(TEXT("n_coherence_snapshots"), V))    Out.NCoherenceSnapshots = V;
    }

    bool ParseManifest(const TSharedPtr<FJsonObject>& Root, FHHGXRManifest& Out, FString& OutError)
    {
        Root->TryGetStringField(TEXT("schema"), Out.Schema);
        if (Out.Schema != TEXT("hhgxr-demo-bundle-v0"))
        {
            OutError = FString::Printf(
                TEXT("Unsupported schema: '%s' (expected 'hhgxr-demo-bundle-v0')"),
                *Out.Schema);
            return false;
        }
        Root->TryGetStringField(TEXT("dataset_name"), Out.DatasetName);
        ParseProvenance(Root, Out.Provenance);
        ReadStringMapAsBest(Root, TEXT("units"), Out.Units);
        ParseDimensions(Root, Out.Dimensions);
        ReadStringArray(Root, TEXT("available_modules"), Out.AvailableModules);
        ReadStringArray(Root, TEXT("missing_modules"), Out.MissingModules);
        ReadStringMapAsBest(Root, TEXT("files"), Out.Files);
        ReadStringMapAsBest(Root, TEXT("source_paths"), Out.SourcePaths);
        return true;
    }


    // -----------------------------------------------------------------
    // data_small.json
    // -----------------------------------------------------------------

    void ParseTimeSeries(const TSharedPtr<FJsonObject>& Root, FHHGXRTimeSeries& Out)
    {
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Root->TryGetObjectField(TEXT("time_series"), Sub) || !Sub) return;
        ReadFloatArray(*Sub, TEXT("time_fs"),  Out.TimeFs);
        ReadFloatArray(*Sub, TEXT("Jx"),       Out.Jx);
        ReadFloatArray(*Sub, TEXT("Jy"),       Out.Jy);
        ReadFloatArray(*Sub, TEXT("Jx_intra"), Out.JxIntra);
        ReadFloatArray(*Sub, TEXT("Jy_intra"), Out.JyIntra);
        ReadFloatArray(*Sub, TEXT("Jx_inter"), Out.JxInter);
        ReadFloatArray(*Sub, TEXT("Jy_inter"), Out.JyInter);
        ReadFloatArray(*Sub, TEXT("Jx_K"),     Out.JxK);
        ReadFloatArray(*Sub, TEXT("Jy_K"),     Out.JyK);
        ReadFloatArray(*Sub, TEXT("Jx_Kp"),    Out.JxKp);
        ReadFloatArray(*Sub, TEXT("Jy_Kp"),    Out.JyKp);
        ReadFloatArray(*Sub, TEXT("eta_x"),    Out.EtaX);
        ReadFloatArray(*Sub, TEXT("eta_y"),    Out.EtaY);
        ReadFloatArray(*Sub, TEXT("Jx_spin"),  Out.JxSpin);
        ReadFloatArray(*Sub, TEXT("Jy_spin"),  Out.JySpin);
    }

    void ParseSpectrum(const TSharedPtr<FJsonObject>& Root, const FString& Key, FHHGXRSpectrum& Out)
    {
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Root->TryGetObjectField(Key, Sub) || !Sub) return;
        ReadFloatArray(*Sub, TEXT("harmonic_order"), Out.HarmonicOrder);
        ReadFloatArray(*Sub, TEXT("omega_au"),       Out.OmegaAu);
        ReadFloatArray(*Sub, TEXT("HHG_x"),          Out.HHGx);
        ReadFloatArray(*Sub, TEXT("HHG_y"),          Out.HHGy);
        ReadFloatArray(*Sub, TEXT("HHG_total"),      Out.HHGTotal);
    }

    void ParseBandPath(const TSharedPtr<FJsonObject>& Root, FHHGXRBandPath& Out)
    {
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Root->TryGetObjectField(TEXT("band_path"), Sub) || !Sub) return;
        ReadFloatArray(*Sub, TEXT("k_path"), Out.KPath);
        ReadFloatGrid2D(*Sub, TEXT("energy_eV"), Out.EnergyEv);
        int32 IntTmp = 0;
        if ((*Sub)->TryGetNumberField(TEXT("n_bands"), IntTmp))         Out.NBands = IntTmp;
        if ((*Sub)->TryGetNumberField(TEXT("band_index_base"), IntTmp)) Out.BandIndexBase = IntTmp;
        (*Sub)->TryGetStringField(TEXT("layout"), Out.Layout);
        double DTmp = 0.0;
        if (TryGetDouble(*Sub, TEXT("e_fermi_eV"), DTmp))
        {
            Out.EFermiEv = static_cast<float>(DTmp);
            Out.bHasEFermi = true;
        }
        if (TryGetDouble(*Sub, TEXT("near_gap_window_eV"), DTmp))
        {
            Out.NearGapWindowEv = static_cast<float>(DTmp);
        }
        ReadIntArray(*Sub, TEXT("near_gap_band_indices"), Out.NearGapBandIndices);
    }

    void ParseBandGridPreview(const TSharedPtr<FJsonObject>& Root, FHHGXRBandGridPreview& Out)
    {
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Root->TryGetObjectField(TEXT("band_grid_preview"), Sub) || !Sub) return;
        ReadFloatGrid2D(*Sub, TEXT("kx_grid"), Out.KxGrid);
        ReadFloatGrid2D(*Sub, TEXT("ky_grid"), Out.KyGrid);
        ReadFloatArray(*Sub,  TEXT("kx"), Out.Kx);
        ReadFloatArray(*Sub,  TEXT("ky"), Out.Ky);
        ReadIntArray(*Sub,    TEXT("selected_band_indices"), Out.SelectedBandIndices);
        int32 IntTmp = 0;
        if ((*Sub)->TryGetNumberField(TEXT("band_index_base"), IntTmp)) Out.BandIndexBase = IntTmp;
        ReadFloatStack3D(*Sub, TEXT("energies_eV"), Out.EnergiesEv);
    }

    bool ParseQuantumGeometry(const TSharedPtr<FJsonObject>& Root, FHHGXRQuantumGeometryPreview& Out)
    {
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Root->TryGetObjectField(TEXT("quantum_geometry_preview"), Sub) || !Sub) return false;
        ReadFloatGrid2D(*Sub, TEXT("kx_grid"), Out.KxGrid);
        ReadFloatGrid2D(*Sub, TEXT("ky_grid"), Out.KyGrid);
        ReadIntArray(*Sub,    TEXT("selected_band_indices"), Out.SelectedBandIndices);
        int32 IntTmp = 0;
        if ((*Sub)->TryGetNumberField(TEXT("band_index_base"), IntTmp)) Out.BandIndexBase = IntTmp;
        ReadFloatStack3D(*Sub, TEXT("berry_curvature_au"), Out.BerryCurvatureAu);
        ReadFloatStack3D(*Sub, TEXT("trace_quantum_metric_au"), Out.TraceQuantumMetricAu);
        ReadIntGrid2D(*Sub, TEXT("valley_id"), Out.ValleyId);
        (*Sub)->TryGetStringField(TEXT("note"), Out.Note);
        return true;
    }

    bool ParseOccupationPreview(const TSharedPtr<FJsonObject>& Root, FHHGXROccupationPreview& Out)
    {
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Root->TryGetObjectField(TEXT("occupation_preview"), Sub) || !Sub) return false;
        ReadFloatGrid2D(*Sub, TEXT("kx_grid"), Out.KxGrid);
        ReadFloatGrid2D(*Sub, TEXT("ky_grid"), Out.KyGrid);
        (*Sub)->TryGetStringField(TEXT("definition"), Out.Definition);
        const TArray<TSharedPtr<FJsonValue>>* Snaps = nullptr;
        if ((*Sub)->TryGetArrayField(TEXT("snapshots"), Snaps) && Snaps)
        {
            Out.Snapshots.Reset();
            Out.Snapshots.Reserve(Snaps->Num());
            for (const TSharedPtr<FJsonValue>& SV : *Snaps)
            {
                TSharedPtr<FJsonObject> SObj = SV->AsObject();
                if (!SObj.IsValid()) continue;
                FHHGXROccupationSnapshot Snap;
                double T = 0.0;
                if (TryGetDouble(SObj, TEXT("time_fs"), T))
                {
                    Snap.TimeFs = static_cast<float>(T);
                }
                ReadFloatGrid2D(SObj, TEXT("n_val"),        Snap.NVal);
                ReadFloatGrid2D(SObj, TEXT("n_cond"),       Snap.NCond);
                ReadFloatGrid2D(SObj, TEXT("delta_n_cond"), Snap.DeltaNCond);
                Out.Snapshots.Add(MoveTemp(Snap));
            }
        }
        return true;
    }

    bool ParseCoherencePreview(const TSharedPtr<FJsonObject>& Root, FHHGXRCoherencePreview& Out)
    {
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Root->TryGetObjectField(TEXT("coherence_preview"), Sub) || !Sub) return false;
        ReadFloatGrid2D(*Sub, TEXT("kx_grid"), Out.KxGrid);
        ReadFloatGrid2D(*Sub, TEXT("ky_grid"), Out.KyGrid);
        (*Sub)->TryGetStringField(TEXT("definition"), Out.Definition);
        const TArray<TSharedPtr<FJsonValue>>* Snaps = nullptr;
        if ((*Sub)->TryGetArrayField(TEXT("snapshots"), Snaps) && Snaps)
        {
            Out.Snapshots.Reset();
            Out.Snapshots.Reserve(Snaps->Num());
            for (const TSharedPtr<FJsonValue>& SV : *Snaps)
            {
                TSharedPtr<FJsonObject> SObj = SV->AsObject();
                if (!SObj.IsValid()) continue;
                FHHGXRCoherenceSnapshot Snap;
                double T = 0.0;
                if (TryGetDouble(SObj, TEXT("time_fs"), T))
                {
                    Snap.TimeFs = static_cast<float>(T);
                }
                ReadFloatGrid2D(SObj, TEXT("coherence_norm"), Snap.CoherenceNorm);
                Out.Snapshots.Add(MoveTemp(Snap));
            }
        }
        return true;
    }

    void ParseField(const TSharedPtr<FJsonObject>& Root, FHHGXRFieldBlock& Out)
    {
        const TSharedPtr<FJsonObject>* Sub = nullptr;
        if (!Root->TryGetObjectField(TEXT("field"), Sub) || !Sub) return;
        ReadFloatArray(*Sub, TEXT("time_fs"), Out.TimeFs);
        ReadFloatArray(*Sub, TEXT("Ex"), Out.Ex);
        ReadFloatArray(*Sub, TEXT("Ey"), Out.Ey);
        ReadFloatArray(*Sub, TEXT("Ax"), Out.Ax);
        ReadFloatArray(*Sub, TEXT("Ay"), Out.Ay);
        (*Sub)->TryGetStringField(TEXT("source"), Out.SourceRaw);
        Out.Source = ParseFieldSource(Out.SourceRaw);
        ReadStringArray(*Sub, TEXT("reconstructed_from"), Out.ReconstructedFrom);
        ReadStringArray(*Sub, TEXT("cross_checked_with"), Out.CrossCheckedWith);
        ReadStringMapAsBest(*Sub, TEXT("cross_check"), Out.CrossCheck);
        (*Sub)->TryGetStringField(TEXT("note"), Out.Note);
        (*Sub)->TryGetStringField(TEXT("raw_source_file"), Out.RawSourceFile);
        (*Sub)->TryGetStringField(TEXT("raw_source_columns"), Out.RawSourceColumns);
    }
} // namespace


// ---------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------

bool UHHGXRBundleLoader::LoadBundle(const FString& BundleDirAbs,
                                    FHHGXRBundle& OutBundle,
                                    FString& OutError)
{
    OutBundle = FHHGXRBundle();
    OutError.Empty();
    OutBundle.BundleDir = BundleDirAbs;

    const FString ManifestPath = FPaths::Combine(BundleDirAbs, TEXT("manifest.json"));
    TSharedPtr<FJsonObject> ManifestRoot;
    if (!ReadJsonObject(ManifestPath, ManifestRoot, OutError))
    {
        UE_LOG(LogHHGXR, Warning, TEXT("HHG-XR bundle load failed: %s"), *OutError);
        return false;
    }
    if (!ParseManifest(ManifestRoot, OutBundle.Manifest, OutError))
    {
        UE_LOG(LogHHGXR, Warning, TEXT("HHG-XR bundle load failed: %s"), *OutError);
        return false;
    }

    const FString* DataSmallRel = OutBundle.Manifest.Files.Find(TEXT("data_small"));
    const FString DataSmallFile = DataSmallRel ? *DataSmallRel : TEXT("data_small.json");
    const FString DataSmallPath = FPaths::Combine(BundleDirAbs, DataSmallFile);

    if (const FString* QuicklookRel = OutBundle.Manifest.Files.Find(TEXT("quicklook")))
    {
        OutBundle.QuicklookPath = FPaths::Combine(BundleDirAbs, *QuicklookRel);
    }

    TSharedPtr<FJsonObject> DataRoot;
    if (!ReadJsonObject(DataSmallPath, DataRoot, OutError))
    {
        UE_LOG(LogHHGXR, Warning, TEXT("HHG-XR bundle load failed: %s"), *OutError);
        return false;
    }

    ParseTimeSeries(DataRoot, OutBundle.Data.TimeSeries);
    ParseSpectrum(DataRoot, TEXT("spectrum"), OutBundle.Data.Spectrum);
    if (DataRoot->HasField(TEXT("spectrum_spin")))
    {
        ParseSpectrum(DataRoot, TEXT("spectrum_spin"), OutBundle.Data.SpectrumSpin);
        OutBundle.Data.bHasSpectrumSpin = true;
    }
    ParseBandPath(DataRoot, OutBundle.Data.BandPath);
    ParseBandGridPreview(DataRoot, OutBundle.Data.BandGridPreview);
    OutBundle.Data.bHasQuantumGeometry = ParseQuantumGeometry(DataRoot, OutBundle.Data.QuantumGeometryPreview);
    OutBundle.Data.bHasOccupationPreview = ParseOccupationPreview(DataRoot, OutBundle.Data.OccupationPreview);
    OutBundle.Data.bHasCoherencePreview = ParseCoherencePreview(DataRoot, OutBundle.Data.CoherencePreview);
    ParseField(DataRoot, OutBundle.Data.Field);

    UE_LOG(LogHHGXR, Log,
        TEXT("HHG-XR bundle loaded: %s (dataset='%s', %d available modules, %d missing)"),
        *BundleDirAbs, *OutBundle.Manifest.DatasetName,
        OutBundle.Manifest.AvailableModules.Num(),
        OutBundle.Manifest.MissingModules.Num());

    return true;
}

bool UHHGXRBundleLoader::HasModule(const FHHGXRManifest& Manifest, const FString& ModuleName)
{
    return Manifest.AvailableModules.Contains(ModuleName);
}

FString UHHGXRBundleLoader::FieldSourceBadge(const FHHGXRFieldBlock& Field)
{
    switch (Field.Source)
    {
    case EHHGXRFieldSource::RawSolverOutput:     return TEXT("raw solver");
    case EHHGXRFieldSource::ReconstructedNotRaw: return TEXT("reconstructed (not raw)");
    case EHHGXRFieldSource::Unavailable:         return TEXT("unavailable");
    case EHHGXRFieldSource::Unknown:
    default:                                     return TEXT("unknown");
    }
}

FLinearColor UHHGXRBundleLoader::FieldSourceColor(EHHGXRFieldSource Source)
{
    switch (Source)
    {
    case EHHGXRFieldSource::RawSolverOutput:     return FLinearColor(0.0f, 0.6f, 0.2f);  // green
    case EHHGXRFieldSource::ReconstructedNotRaw: return FLinearColor(0.85f, 0.45f, 0.0f); // orange
    case EHHGXRFieldSource::Unavailable:         return FLinearColor(0.4f, 0.4f, 0.4f);  // grey
    case EHHGXRFieldSource::Unknown:
    default:                                     return FLinearColor(0.7f, 0.0f, 0.0f);  // red
    }
}
