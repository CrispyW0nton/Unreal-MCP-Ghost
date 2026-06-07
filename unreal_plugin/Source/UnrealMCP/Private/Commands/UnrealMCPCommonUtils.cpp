#include "Commands/UnrealMCPCommonUtils.h"
#include "Containers/Ticker.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "GameFramework/Actor.h"
#include "Engine/Blueprint.h"
// CRASH-006: editor autosave suppression
#include "Editor.h"
#include "Editor/UnrealEdEngine.h"
#include "IPackageAutoSaver.h"
#include "UnrealEdGlobals.h"
// CRASH-007: deferred safe compile + save
#include "Kismet2/KismetEditorUtilities.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "UObject/SavePackage.h"
#include "UObject/Package.h"
#include "Misc/PackageName.h"

// ---------------------------------------------------------------------------
// SEH inner helpers (CRASH-005)
//
// MSVC C2712: a function that uses __try/__except cannot also contain any
// C++ object that requires unwinding (FString locals, TWeakObjectPtr,
// captured-by-value lambdas, FString temporaries returned by GetName(), etc.)
// — even AFTER the __try block.
//
// Workaround: each __try lives in a tiny static helper here that takes raw
// pointers/references and contains ZERO objects with destructors. The public
// FUnrealMCPCommonUtils methods then just delegate to these helpers.
//
// On Clang / clang-cl (no MSVC SEH), each helper degrades to a direct call.
// ---------------------------------------------------------------------------
namespace UnrealMCPSehDetail
{
    static bool TryBlueprintModify(UBlueprint* BP)
    {
#if PLATFORM_WINDOWS && defined(_MSC_VER) && !defined(__clang__)
        __try { BP->Modify(); return true; }
        __except (1) { return false; }
#else
        BP->Modify();
        return true;
#endif
    }

    static bool TryMarkPackageDirty(UBlueprint* BP)
    {
#if PLATFORM_WINDOWS && defined(_MSC_VER) && !defined(__clang__)
        __try { BP->MarkPackageDirty(); return true; }
        __except (1) { return false; }
#else
        BP->MarkPackageDirty();
        return true;
#endif
    }

    static bool TrySCSAddNode(USimpleConstructionScript* SCS, USCS_Node* Node)
    {
#if PLATFORM_WINDOWS && defined(_MSC_VER) && !defined(__clang__)
        __try { SCS->AddNode(Node); return true; }
        __except (1) { return false; }
#else
        SCS->AddNode(Node);
        return true;
#endif
    }

    // SetObjectProperty signature pulled in via forward decl rather than
    // a member call so this helper stays a leaf with zero unwinds.
    typedef bool (*FSetObjectPropertyFn)(UObject* /*Object*/,
                                         const FString& /*Name*/,
                                         const TSharedPtr<FJsonValue>& /*Value*/,
                                         FString& /*OutError*/);

    static bool TrySetObjectProperty(FSetObjectPropertyFn Fn,
                                     UObject* Object,
                                     const FString& Name,
                                     const TSharedPtr<FJsonValue>& Value,
                                     FString& OutError,
                                     bool& OutOk)
    {
        // Returns true on no SEH crash; OutOk holds the wrapped bool result.
#if PLATFORM_WINDOWS && defined(_MSC_VER) && !defined(__clang__)
        __try { OutOk = Fn(Object, Name, Value, OutError); return true; }
        __except (1) { return false; }
#else
        OutOk = Fn(Object, Name, Value, OutError);
        return true;
#endif
    }

    // CRASH-007: leaf SEH helper for FKismetEditorUtilities::CompileBlueprint.
    // Kept to a tiny no-unwind function for the same C2712 reason as the
    // helpers above. The compile flags are passed by value (raw enum).
    static bool TryCompileBlueprint(UBlueprint* BP, EBlueprintCompileOptions Flags)
    {
#if PLATFORM_WINDOWS && defined(_MSC_VER) && !defined(__clang__)
        __try { FKismetEditorUtilities::CompileBlueprint(BP, Flags); return true; }
        __except (1) { return false; }
#else
        FKismetEditorUtilities::CompileBlueprint(BP, Flags);
        return true;
#endif
    }

    // CRASH-007: leaf SEH helper for UPackage::SavePackage.
    // Returns true on no SEH crash; OutSaved holds the wrapped bool result.
    // Takes raw const TCHAR* for filename so we hold no FString locals.
    static bool TrySavePackage(UPackage* Package, UObject* Asset,
                               const TCHAR* FileNameRaw,
                               const FSavePackageArgs& Args, bool& OutSaved)
    {
#if PLATFORM_WINDOWS && defined(_MSC_VER) && !defined(__clang__)
        __try
        {
            OutSaved = UPackage::SavePackage(Package, Asset, FileNameRaw, Args);
            return true;
        }
        __except (1) { return false; }
#else
        OutSaved = UPackage::SavePackage(Package, Asset, FileNameRaw, Args);
        return true;
#endif
    }
} // namespace UnrealMCPSehDetail
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "K2Node_Event.h"
#include "K2Node_CustomEvent.h"
#include "K2Node_CallFunction.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "K2Node_InputAction.h"
#include "K2Node_Self.h"
#include "EdGraphSchema_K2.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Components/StaticMeshComponent.h"
#include "Components/LightComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SceneComponent.h"
#include "UObject/UObjectIterator.h"
#include "Engine/Selection.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "BlueprintNodeSpawner.h"
#include "BlueprintActionDatabase.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

// JSON Utilities
TSharedPtr<FJsonObject> FUnrealMCPCommonUtils::CreateErrorResponse(const FString& Message)
{
    TSharedPtr<FJsonObject> ResponseObject = MakeShared<FJsonObject>();
    ResponseObject->SetBoolField(TEXT("success"), false);
    ResponseObject->SetStringField(TEXT("error"), Message);
    return ResponseObject;
}

TSharedPtr<FJsonObject> FUnrealMCPCommonUtils::CreateSuccessResponse(const TSharedPtr<FJsonObject>& Data)
{
    TSharedPtr<FJsonObject> ResponseObject = MakeShared<FJsonObject>();
    ResponseObject->SetBoolField(TEXT("success"), true);
    
    if (Data.IsValid())
    {
        ResponseObject->SetObjectField(TEXT("data"), Data);
    }
    
    return ResponseObject;
}

void FUnrealMCPCommonUtils::GetIntArrayFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName, TArray<int32>& OutArray)
{
    OutArray.Reset();
    
    if (!JsonObject->HasField(FieldName))
    {
        return;
    }
    
    const TArray<TSharedPtr<FJsonValue>>* JsonArray;
    if (JsonObject->TryGetArrayField(FieldName, JsonArray))
    {
        for (const TSharedPtr<FJsonValue>& Value : *JsonArray)
        {
            OutArray.Add((int32)Value->AsNumber());
        }
    }
}

void FUnrealMCPCommonUtils::GetFloatArrayFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName, TArray<float>& OutArray)
{
    OutArray.Reset();
    
    if (!JsonObject->HasField(FieldName))
    {
        return;
    }
    
    const TArray<TSharedPtr<FJsonValue>>* JsonArray;
    if (JsonObject->TryGetArrayField(FieldName, JsonArray))
    {
        for (const TSharedPtr<FJsonValue>& Value : *JsonArray)
        {
            OutArray.Add((float)Value->AsNumber());
        }
    }
}

FVector2D FUnrealMCPCommonUtils::GetVector2DFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName)
{
    FVector2D Result(0.0f, 0.0f);
    
    if (!JsonObject->HasField(FieldName))
    {
        return Result;
    }
    
    const TArray<TSharedPtr<FJsonValue>>* JsonArray;
    if (JsonObject->TryGetArrayField(FieldName, JsonArray) && JsonArray->Num() >= 2)
    {
        Result.X = (float)(*JsonArray)[0]->AsNumber();
        Result.Y = (float)(*JsonArray)[1]->AsNumber();
    }
    
    return Result;
}

FVector FUnrealMCPCommonUtils::GetVectorFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName)
{
    FVector Result(0.0f, 0.0f, 0.0f);
    
    if (!JsonObject->HasField(FieldName))
    {
        return Result;
    }
    
    const TArray<TSharedPtr<FJsonValue>>* JsonArray;
    if (JsonObject->TryGetArrayField(FieldName, JsonArray) && JsonArray->Num() >= 3)
    {
        Result.X = (float)(*JsonArray)[0]->AsNumber();
        Result.Y = (float)(*JsonArray)[1]->AsNumber();
        Result.Z = (float)(*JsonArray)[2]->AsNumber();
    }
    
    return Result;
}

FRotator FUnrealMCPCommonUtils::GetRotatorFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName)
{
    FRotator Result(0.0f, 0.0f, 0.0f);
    
    if (!JsonObject->HasField(FieldName))
    {
        return Result;
    }
    
    const TArray<TSharedPtr<FJsonValue>>* JsonArray;
    if (JsonObject->TryGetArrayField(FieldName, JsonArray) && JsonArray->Num() >= 3)
    {
        Result.Pitch = (float)(*JsonArray)[0]->AsNumber();
        Result.Yaw = (float)(*JsonArray)[1]->AsNumber();
        Result.Roll = (float)(*JsonArray)[2]->AsNumber();
    }
    
    return Result;
}

// Blueprint Utilities
UBlueprint* FUnrealMCPCommonUtils::FindBlueprint(const FString& BlueprintName)
{
    return FindBlueprintByName(BlueprintName);
}

// ---------------------------------------------------------------------------
// Blueprint name → object-path cache.
//
// The Asset Registry scan (GetAssets with bRecursivePaths on a large project)
// is extremely expensive: on an 8 k-asset project it blocks the GameThread for
// 20-30 s, causing the Python 30 s socket timeout to fire.
//
// Fix:
//   (a) Use AR.GetAssetsByClass() which hits an O(1) class index instead of
//       scanning every asset in the registry.
//   (b) Cache the resolved object path in a static TMap so repeated calls for
//       the same Blueprint cost only a FindObject<> lookup (zero AR scan).
//   (c) Cache NEGATIVE results (blueprint not found) in GBlueprintMissingCache
//       with a timestamp.  Missing-BP queries (e.g. get_blueprint_graphs for a
//       non-existent BP) currently scan ALL blueprint assets every time — on a
//       project with 500+ blueprints this takes 5-30 s.  The negative cache
//       returns an error in O(1) for the next 60 s; after that it re-scans once
//       in case the blueprint was created meanwhile.
//   (d) The positive cache entry is validated with IsValid() before use; stale
//       entries (e.g. after Hot-Reload) are automatically evicted.
// ---------------------------------------------------------------------------
static TMap<FString, FSoftObjectPath> GBlueprintNameCache;

// Negative cache: blueprints confirmed NOT to exist + the time we last scanned.
// Value = FPlatformTime::Seconds() at which we confirmed the BP was missing.
// TTL = 60 s (re-scan after that in case the user created the blueprint).
static TMap<FString, double> GBlueprintMissingCache;
static constexpr double MISSING_CACHE_TTL_SECONDS = 60.0;

void FUnrealMCPCommonUtils::InvalidateBlueprintMissCache(const FString& BlueprintName)
{
    GBlueprintMissingCache.Remove(BlueprintName);
}

void FUnrealMCPCommonUtils::SafeMarkBlueprintModified(UBlueprint* Blueprint)
{
    if (!Blueprint || !IsValid(Blueprint)) return;

    // CRASH GUARD (UE 5.6 / this project):
    // Never call MarkBlueprintAsStructurallyModified from MCP. It can enter
    // UnrealEd/CoreUObject editor notification chains while MassEntityEditor has
    // stale observers registered, causing EXCEPTION_ACCESS_VIOLATION during the
    // command itself or on the next manual save. Modify + MarkPackageDirty keeps
    // the asset editable/saveable without forcing those structural delegates.
    Blueprint->Modify();
    Blueprint->MarkPackageDirty();
    UE_LOG(LogTemp, Display,
        TEXT("[MCP] SafeMarkBlueprintModified: marked '%s' dirty without structural notifications"),
        *Blueprint->GetName());
}

// ---------------------------------------------------------------------------
// SafeMarkBlueprintModifiedDeferred — defers MarkPackageDirty to next end-of-frame.
//
// Background (CRASH-005, "blackhole_ambient_loop AR walk crash" — UECC-Windows-49F65657...):
//   Setting AudioComponent.Sound on an SCS template (BP_BlackHole) and immediately
//   calling MarkPackageDirty() triggered the AssetRegistry to enqueue a dependency
//   rescan of BP_BlackHole. The Content Browser's next tick (~3 s later) walked
//   the BP's outgoing deps via FAssetRegistry::GetDependencies; the freshly-
//   imported USoundWave 'blackhole_ambient_loop' was still mid-PostLoad on a
//   background thread, and the AR's TObjectPtr cache held a stale entry. The
//   walk dereferenced 0x00007ffb3f000298 → EXCEPTION_ACCESS_VIOLATION → editor
//   crash. None of the in-command SEH guards caught it because the AV happened
//   on a later editor tick, after the bridge command had already returned
//   success.
//
// Fix:
//   Modify() runs immediately (it only writes to the editor undo system; no
//   AR side effects). MarkPackageDirty() — which is what fires the AR notifier
//   — is queued via FTSTicker to fire on the next GameThread tick. By that
//   point any synchronous SoundWave / NiagaraSystem / Texture PostLoad
//   triggered by the property write will have completed, and the AR walk
//   sees a fully-initialized dependency.
//
// Multiple deferred calls for the same package within one frame coalesce
// naturally (MarkPackageDirty is idempotent and the delegate handle is one-shot).
// ---------------------------------------------------------------------------
void FUnrealMCPCommonUtils::SafeMarkBlueprintModifiedDeferred(UBlueprint* Blueprint)
{
    if (!Blueprint || !IsValid(Blueprint)) return;

    // Synchronous part — safe; no AssetRegistry broadcast.
    // SEH-wrapped via leaf helper to survive the rare case where Blueprint's
    // transaction system is in an inconsistent state.
    if (!UnrealMCPSehDetail::TryBlueprintModify(Blueprint))
    {
        UE_LOG(LogTemp, Error,
            TEXT("[MCP] SafeMarkBlueprintModifiedDeferred: SEH crash inside Blueprint->Modify() for '%s' — caught, asset NOT marked dirty"),
            *Blueprint->GetName());
        return;
    }

    // Capture as TWeakObjectPtr — Blueprint may be GC'd before the next tick fires
    // (rare, but possible if the user closes the editor or unloads the level).
    TWeakObjectPtr<UBlueprint> WeakBP(Blueprint);
    const FString BpName = Blueprint->GetName();

    // FTSTicker fires on the GameThread on the next tick (delay 0.0). The
    // lambda returns false to auto-deregister after the single fire — no
    // manual handle bookkeeping required.
    FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateLambda([WeakBP, BpName](float /*DeltaTime*/) -> bool
        {
            UBlueprint* BP = WeakBP.Get();
            if (!BP || !IsValid(BP))
            {
                UE_LOG(LogTemp, Verbose,
                    TEXT("[MCP] SafeMarkBlueprintModifiedDeferred: '%s' was GC'd before deferred MarkPackageDirty — skipping"),
                    *BpName);
                return false; // one-shot
            }

            // SEH-guarded MarkPackageDirty via leaf helper — even after a
            // tick deferral, the AR walk can still hit a corrupted dep
            // cache in pathological cases. Catching the crash here keeps
            // the editor alive; the user can re-run the workflow after
            // restarting the AR cache.
            const bool bOk = UnrealMCPSehDetail::TryMarkPackageDirty(BP);
            if (!bOk)
            {
                UE_LOG(LogTemp, Error,
                    TEXT("[MCP] SafeMarkBlueprintModifiedDeferred: deferred MarkPackageDirty crashed for '%s' — caught (AR cache may be inconsistent; restart editor recommended)"),
                    *BpName);
            }
            else
            {
                UE_LOG(LogTemp, Display,
                    TEXT("[MCP] SafeMarkBlueprintModifiedDeferred: dirty flag flushed for '%s' on next tick"),
                    *BpName);
            }
            return false; // one-shot — never re-fire
        }),
        0.0f);

    UE_LOG(LogTemp, Display,
        TEXT("[MCP] SafeMarkBlueprintModifiedDeferred: queued dirty flush for '%s' (fires on next editor tick)"),
        *Blueprint->GetName());
}

// ---------------------------------------------------------------------------
// SetObjectPropertyGuarded — SEH-wrapped property setter.
//
// Lives in its own function so HandleSetComponentProperty (which has a
// std::exception try/catch) can call it without triggering MSVC C2712
// "cannot use __try in functions that require C++ object unwinding".
// ---------------------------------------------------------------------------
bool FUnrealMCPCommonUtils::SetObjectPropertyGuarded(UObject* Object,
                                                     const FString& PropertyName,
                                                     const TSharedPtr<FJsonValue>& Value,
                                                     FString& OutErrorMessage,
                                                     bool& OutSehCrash)
{
    OutSehCrash = false;
    if (!Object)
    {
        OutErrorMessage = TEXT("SetObjectPropertyGuarded: null Object");
        return false;
    }

    // Delegate the SEH guard to a leaf helper that has zero C++ unwind
    // objects (see UnrealMCPSehDetail at top of file). MSVC C2712 forbids
    // __try inside any function that allocates FString locals, so we
    // can't __try here directly — we'd hit the same error if we did.
    bool bOk = false;
    const bool bNoSeh = UnrealMCPSehDetail::TrySetObjectProperty(
        &FUnrealMCPCommonUtils::SetObjectProperty,
        Object, PropertyName, Value, OutErrorMessage, bOk);

    if (!bNoSeh)
    {
        // OutErrorMessage may be in a partially-written state from the AV;
        // overwrite with a clean diagnostic.
        OutSehCrash = true;
        OutErrorMessage = FString::Printf(
            TEXT("SetObjectPropertyGuarded: SEH access violation while setting '%s' on '%s' — caught"),
            *PropertyName, *Object->GetName());
        return false;
    }
    return bOk;
}

// ---------------------------------------------------------------------------
// SCSAddNodeGuarded — SEH-wrapped SCS AddNode.
//
// AddNode triggers PostEditChange on the SCS internally; in pathological
// cases (e.g. a fresh subobject template referencing an asset still in
// async PostLoad) this can AV. Wrapping in SEH keeps the editor alive.
// ---------------------------------------------------------------------------
bool FUnrealMCPCommonUtils::SCSAddNodeGuarded(USimpleConstructionScript* SCS,
                                              USCS_Node* NewNode,
                                              bool& OutSehCrash)
{
    OutSehCrash = false;
    if (!SCS || !NewNode)
    {
        return false;
    }
    // Delegate to leaf SEH helper (see UnrealMCPSehDetail at top of file)
    // for the same C2712 reason as SetObjectPropertyGuarded.
    const bool bNoSeh = UnrealMCPSehDetail::TrySCSAddNode(SCS, NewNode);
    OutSehCrash = !bNoSeh;
    return bNoSeh;
}

// ---------------------------------------------------------------------------
// DeferAutoSave (CRASH-006)
//
// Background:
//   Unreal's periodic autosave (UPackageAutoSaver) runs on the GameThread
//   tick. The autosave interval defaults to 10 min and once it elapses,
//   autosave fires on the very next idle tick — which can interleave with
//   bridge SCS-mutation chains. Concrete failure mode (UECC-Windows-C418EA37
//   crash):
//
//     1. Bridge: add_component_to_blueprint           → success
//     2. Bridge: set_component_property Sound          → success
//     3. Bridge: set_component_property bAutoActivate  → success
//     4. Bridge worker queues set_component_property VolumeMultiplier
//     5. ↳ Editor autosave timer expires; GameThread starts UPackage::SavePackage
//        on the half-mutated BP_DangerSenseAI_BlueprintOnly
//     6. ↳ AsyncTask for VolumeMultiplier runs while SavePackage is mid-flight
//     7. Autosave finalizes, hits torn TObjectPtr → AV in CoreUObject
//
//   Address 0x00007ffb3ecccd55, stack: CoreUObject (×4) →
//   FEditorEngine::Tick → FEngineLoop::Tick → main.
//
// Fix:
//   Reset the autosave timer at the top of every bridge command. As long as
//   the user keeps issuing commands faster than the autosave interval
//   (default 10 min), autosave will never fire during a script run.
//   Autosave still fires normally during idle time — this is purely a
//   "push it forward" pattern, not a permanent disable.
//
// Implementation:
//   GUnrealEd->GetPackageAutoSaver() returns IPackageAutoSaver& (ref) in
//   UE 5.6. We call ResetAutoSaveTimer() on it. All access is guarded so
//   the call is harmless if GUnrealEd / GIsEditor is not yet ready.
// ---------------------------------------------------------------------------
void FUnrealMCPCommonUtils::DeferAutoSave()
{
    if (!GIsEditor || !GUnrealEd)
    {
        return;
    }
    // GetPackageAutoSaver() returns IPackageAutoSaver& by reference in
    // UE 5.6. Resetting the timer is cheap (just a float store).
    IPackageAutoSaver& Saver = GUnrealEd->GetPackageAutoSaver();
    Saver.ResetAutoSaveTimer();
    // No log spam — this fires on every command. The previous-autosave
    // timestamp is still tracked internally; only the *next* autosave is
    // pushed forward by one full interval.
}

// ---------------------------------------------------------------------------
// SafeCompileBlueprintDeferred (CRASH-007)
//
// Background:
//   The MCP `compile_blueprint` command historically only marked the BP
//   modified — it explicitly avoided FKismetEditorUtilities::CompileBlueprint
//   because, when invoked synchronously from the bridge's AsyncTask lambda,
//   that call entered the editor's MassEntityEditor observer chain and AV'd.
//
//   Side-effect: after SCS edits (e.g. adding a UAudioComponent template
//   pointing at a freshly imported USoundWave), the Blueprint's GeneratedClass
//   and CDO were never regenerated. The next manual Ctrl+Shift+S then
//   serialised a stale CDO that referenced template subobjects whose post-load
//   path had run — and AV'd in CoreUObject during the post-save reinstancing
//   pass for level actor instances of the Blueprint.
//
// Fix:
//   Run CompileBlueprint OUTSIDE our AsyncTask lambda by deferring it to a
//   FTSTicker tick. The tick fires on the GameThread but in a clean stack
//   frame — no nested AsyncTask, no MCP_GUARDED_RUN bridge frame above it,
//   no in-flight bridge socket. In practice this consistently avoids the
//   MassEntityEditor observer chain crash we historically hit with inline
//   compiles. SEH guard catches any residual AV so the editor survives.
//
//   Compile flags:
//     EBlueprintCompileOptions::SkipGarbageCollection
//       Avoids a GC pass during compile that can race with the deferred
//       MarkPackageDirty tick scheduled by SafeMarkBlueprintModifiedDeferred.
//     EBlueprintCompileOptions::SkipSave
//       Prevents the compile from queuing its own save (we save explicitly
//       via SafeSaveBlueprintPackageDeferred when requested).
// ---------------------------------------------------------------------------
void FUnrealMCPCommonUtils::SafeCompileBlueprintDeferred(UBlueprint* Blueprint)
{
    if (!Blueprint || !IsValid(Blueprint))
    {
        UE_LOG(LogTemp, Warning, TEXT("[MCP] SafeCompileBlueprintDeferred: null/invalid Blueprint"));
        return;
    }

    TWeakObjectPtr<UBlueprint> WeakBP(Blueprint);
    const FString BpName = Blueprint->GetName();

    FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateLambda([WeakBP, BpName](float /*DeltaTime*/) -> bool
        {
            UBlueprint* BP = WeakBP.Get();
            if (!BP || !IsValid(BP))
            {
                UE_LOG(LogTemp, Verbose,
                    TEXT("[MCP] SafeCompileBlueprintDeferred: '%s' was GC'd before deferred compile — skipping"),
                    *BpName);
                return false;
            }
            if (!BP->GeneratedClass || !IsValid(BP->GeneratedClass))
            {
                UE_LOG(LogTemp, Warning,
                    TEXT("[MCP] SafeCompileBlueprintDeferred: '%s' has no valid GeneratedClass — skipping deferred compile"),
                    *BpName);
                return false;
            }

            const EBlueprintCompileOptions Flags =
                  EBlueprintCompileOptions::SkipGarbageCollection
                | EBlueprintCompileOptions::SkipSave;

            const bool bOk = UnrealMCPSehDetail::TryCompileBlueprint(BP, Flags);
            if (!bOk)
            {
                UE_LOG(LogTemp, Error,
                    TEXT("[MCP] SafeCompileBlueprintDeferred: deferred CompileBlueprint AV'd for '%s' — caught by SEH; CDO may still be stale"),
                    *BpName);
            }
            else
            {
                UE_LOG(LogTemp, Display,
                    TEXT("[MCP] SafeCompileBlueprintDeferred: '%s' recompiled successfully (CDO regenerated)"),
                    *BpName);
            }
            return false; // one-shot
        }),
        0.0f);

    UE_LOG(LogTemp, Display,
        TEXT("[MCP] SafeCompileBlueprintDeferred: queued compile for '%s' (fires on next editor tick)"),
        *Blueprint->GetName());
}

// ---------------------------------------------------------------------------
// SafeSaveBlueprintPackageDeferred (CRASH-007)
//
// Two-stage deferred chain:
//   1. Schedule a guarded compile (own tick) so the CDO is regenerated.
//   2. Schedule a guarded UPackage::SavePackage on a SECOND tick so the
//      compile's PostEditChange / reinstancing has finished settling.
//
// Why low-level UPackage::SavePackage instead of UEditorAssetLibrary::SaveAsset
// or UEditorLoadingAndSavingUtils::SavePackages:
//   Both higher-level paths fire the editor's PreSave/PostSave delegate chain
//   which in this project hits the MassEntityEditor observer with stale state
//   and AVs (CRASH-002 / CRASH-007 same root). UPackage::SavePackage on the
//   BP package directly avoids that delegate chain.
//
// SAVE_KeepDirty + manual SetDirtyFlag(false): UE5.6's SavePackage clears the
// dirty flag itself, but only after firing the post-save delegates. We pass
// SAVE_KeepDirty so SavePackage does NOT broadcast PackageDirtyStateChanged
// from inside its serialise critical section, then clear the flag ourselves
// after we know the file is on disk.
// ---------------------------------------------------------------------------
bool FUnrealMCPCommonUtils::SafeSaveBlueprintPackageDeferred(UBlueprint* Blueprint)
{
    if (!Blueprint || !IsValid(Blueprint))
    {
        UE_LOG(LogTemp, Warning, TEXT("[MCP] SafeSaveBlueprintPackageDeferred: null/invalid Blueprint"));
        return false;
    }
    UPackage* Package = Blueprint->GetOutermost();
    if (!Package || !IsValid(Package))
    {
        UE_LOG(LogTemp, Warning, TEXT("[MCP] SafeSaveBlueprintPackageDeferred: '%s' has no valid outer package"),
            *Blueprint->GetName());
        return false;
    }

    // Stage 1 — deferred compile (regenerate CDO).
    SafeCompileBlueprintDeferred(Blueprint);

    // Stage 2 — deferred SavePackage. Capture weak refs so we don't keep the
    // BP alive past a legitimate GC. Capture filename as FString (built once
    // here, not in the hot tick), but pass to the leaf SEH helper as raw TCHAR*
    // (the leaf has no unwind objects per C2712 rules).
    TWeakObjectPtr<UBlueprint> WeakBP(Blueprint);
    TWeakObjectPtr<UPackage> WeakPkg(Package);
    const FString BpName = Blueprint->GetName();
    const FString PackageName = Package->GetName();
    const FString FileName = FPackageName::LongPackageNameToFilename(
        PackageName, FPackageName::GetAssetPackageExtension());

    FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateLambda([WeakBP, WeakPkg, BpName, PackageName, FileName](float /*DeltaTime*/) -> bool
        {
            UBlueprint* BP = WeakBP.Get();
            UPackage* Pkg = WeakPkg.Get();
            if (!BP || !IsValid(BP) || !Pkg || !IsValid(Pkg))
            {
                UE_LOG(LogTemp, Verbose,
                    TEXT("[MCP] SafeSaveBlueprintPackageDeferred: '%s' was GC'd before deferred save — skipping"),
                    *BpName);
                return false;
            }

            FSavePackageArgs SaveArgs;
            SaveArgs.TopLevelFlags      = RF_Public | RF_Standalone;
            // SAVE_KeepDirty: don't broadcast PackageDirtyStateChanged from
            // inside SavePackage's serialise; we clear manually below.
            // SAVE_NoError: do not pop the modal save-error dialog on failure
            // (we log instead — the editor stays interactive).
            SaveArgs.SaveFlags          = SAVE_NoError | SAVE_KeepDirty;
            SaveArgs.bForceByteSwapping = false;
            SaveArgs.bWarnOfLongFilename= true;
            SaveArgs.bSlowTask          = false;
            SaveArgs.Error              = GError;

            bool bSaved = false;
            const bool bNoSeh = UnrealMCPSehDetail::TrySavePackage(
                Pkg, BP, *FileName, SaveArgs, bSaved);

            if (!bNoSeh)
            {
                UE_LOG(LogTemp, Error,
                    TEXT("[MCP] SafeSaveBlueprintPackageDeferred: deferred SavePackage AV'd for '%s' — caught by SEH; file '%s' NOT written"),
                    *BpName, *FileName);
                return false;
            }
            if (!bSaved)
            {
                UE_LOG(LogTemp, Error,
                    TEXT("[MCP] SafeSaveBlueprintPackageDeferred: SavePackage returned false for '%s' (file '%s' not written)"),
                    *BpName, *FileName);
                return false;
            }

            // SAVE_KeepDirty kept the dirty bit; clear it now so the
            // editor UI shows the asset as clean.
            Pkg->SetDirtyFlag(false);
            UE_LOG(LogTemp, Display,
                TEXT("[MCP] SafeSaveBlueprintPackageDeferred: wrote '%s' OK (package '%s' clean)"),
                *FileName, *PackageName);
            return false; // one-shot
        }),
        0.05f); // small delay so the compile tick has fired first

    UE_LOG(LogTemp, Display,
        TEXT("[MCP] SafeSaveBlueprintPackageDeferred: scheduled compile + save chain for '%s' -> '%s'"),
        *Blueprint->GetName(), *FileName);
    return true;
}

bool FUnrealMCPCommonUtils::EnsureBlueprintGeneratedClass(UBlueprint* Blueprint)
{
    // CRASH-003 guard: validation-only — NO CompileBlueprint call.
    // FKismetEditorUtilities::CompileBlueprint crashes UE5.6 when called from an
    // async-task lambda context (EXCEPTION_ACCESS_VIOLATION via MassEntityEditor observer).
    // Callers that receive false must skip PostPlacedNewNode, ReconstructNode and
    // TrySetDefaultObject, and fall back to direct DefaultObject/DefaultValue assignment.
    if (!Blueprint || !IsValid(Blueprint))
    {
        UE_LOG(LogTemp, Warning, TEXT("[MCP] EnsureBlueprintGeneratedClass: null Blueprint"));
        return false;
    }
    if (Blueprint->GeneratedClass && IsValid(Blueprint->GeneratedClass))
    {
        return true;
    }
    UE_LOG(LogTemp, Warning,
        TEXT("[MCP] EnsureBlueprintGeneratedClass: GeneratedClass null for '%s' — callers must skip PostPlacedNewNode/ReconstructNode"),
        *Blueprint->GetName());
    return false;
}

UBlueprint* FUnrealMCPCommonUtils::FindBlueprintByName(const FString& BlueprintName)
{
    // ── 0. Check the in-memory positive cache first (free after first lookup) ──
    if (const FSoftObjectPath* CachedPath = GBlueprintNameCache.Find(BlueprintName))
    {
        if (UBlueprint* CachedBP = Cast<UBlueprint>(CachedPath->ResolveObject()))
        {
            return CachedBP;
        }
        // Stale entry (e.g. after Hot-Reload) – remove and re-scan below.
        GBlueprintNameCache.Remove(BlueprintName);
        // Also clear the negative cache entry if it exists, to force a fresh scan.
        GBlueprintMissingCache.Remove(BlueprintName);
    }

    // ── 0b. Check the negative cache — skip the expensive AR scan for recently
    //        confirmed-missing blueprints to avoid 5-30 s hangs on invalid names. ──
    if (const double* MissTime = GBlueprintMissingCache.Find(BlueprintName))
    {
        const double Age = FPlatformTime::Seconds() - *MissTime;
        if (Age < MISSING_CACHE_TTL_SECONDS)
        {
            UE_LOG(LogTemp, Verbose,
                TEXT("FindBlueprintByName: '%s' in negative cache (%.1f s ago) — skipping AR scan"),
                *BlueprintName, Age);
            return nullptr;
        }
        // TTL expired — remove stale negative entry and do a fresh scan.
        GBlueprintMissingCache.Remove(BlueprintName);
    }

    // ── 1. Try the two common path conventions first (O(1) FindObject) ──
    //
    // IMPORTANT: never concatenate a raw "/Game/..." package path to another
    // "/Game/..." prefix. CoreUObject fatals on double-slash package names
    // ("Attempted to create a package with name containing double slashes").
    // The sanitiser below skips any candidate that contains "//".
    auto TryCachedPath = [&](const FString& Path) -> UBlueprint*
    {
        // Reject malformed paths (double slashes anywhere after the leading '/').
        if (Path.IsEmpty() || Path.Contains(TEXT("//")))
        {
            return nullptr;
        }
        // FindObject skips I/O; LoadObject falls back to disk only if needed.
        UBlueprint* BP = FindObject<UBlueprint>(nullptr, *Path);
        if (!BP) BP = LoadObject<UBlueprint>(nullptr, *Path);
        if (BP)
        {
            GBlueprintNameCache.Add(BlueprintName, FSoftObjectPath(BP));
            GBlueprintMissingCache.Remove(BlueprintName); // clear any stale negative entry
            return BP;
        }
        return nullptr;
    };

    // If the caller already handed us a full package path ("/Game/..." or
    // "/Engine/..." etc.), use it as-is. Otherwise try the two legacy
    // convenience prefixes that expect a bare asset name.
    const bool bIsFullPath = BlueprintName.StartsWith(TEXT("/"));
    if (bIsFullPath)
    {
        if (UBlueprint* BP = TryCachedPath(BlueprintName)) return BP;
        // Also try with a trailing ".<name>" object path, in case caller
        // passed only the package path (UE accepts both but FindObject prefers
        // the full object path for cached lookup).
        int32 LastSlash = INDEX_NONE;
        if (BlueprintName.FindLastChar(TEXT('/'), LastSlash))
        {
            const FString Leaf = BlueprintName.Mid(LastSlash + 1);
            if (!Leaf.IsEmpty())
            {
                if (UBlueprint* BP = TryCachedPath(BlueprintName + TEXT(".") + Leaf)) return BP;
            }
        }
    }
    else
    {
        if (UBlueprint* BP = TryCachedPath(TEXT("/Game/Blueprints/") + BlueprintName)) return BP;
        if (UBlueprint* BP = TryCachedPath(TEXT("/Game/") + BlueprintName))           return BP;
    }

    // ── 2. Use the Asset Registry class index (fast O(k) where k = # Blueprints) ──
    //
    // GetAssetsByClass() uses a pre-built per-class index — it does NOT scan
    // all 8 k assets. It only visits the ~N Blueprint assets in the project.
    // This is dramatically faster than GetAssets(Filter) with bRecursivePaths.
    FAssetRegistryModule& ARModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
    IAssetRegistry& AR = ARModule.Get();

    // ── FIRST-CALL SAFETY: wait for the AR initial scan to finish ─────────
    // On the very first MCP command of a fresh editor session, the Asset Registry
    // may still be scanning /Game/**. Calling GetAssetsByClass() while the scan
    // is running can intermittently return an incomplete index, which causes
    // Asset.GetAsset() to call StaticLoadObject on packages that are being
    // asynchronously loaded — triggering a GC-unsafe access that manifests as
    // EXCEPTION_ACCESS_VIOLATION → WinError 10053 (WSAECONNABORTED) on Python.
    // WaitForCompletion() blocks until the initial disk scan finishes (< 2 s on
    // a warm filesystem cache) and is a no-op if the scan is already done.
    if (!AR.IsSearchAsync() || AR.IsLoadingAssets())
    {
        UE_LOG(LogTemp, Display, TEXT("FindBlueprintByName: AR still scanning — waiting for completion before '%s' lookup"), *BlueprintName);
        AR.WaitForCompletion();
        UE_LOG(LogTemp, Display, TEXT("FindBlueprintByName: AR scan complete"));
    }

    // ── 2b. Use TagsAndValues filter for O(1) name lookup (UE5.6-compatible) ─
    // FARFilter.TagsAndValues lets us query by the "AssetBundleData" or any
    // asset-searchable tag. However UBlueprint doesn't expose a name tag.
    // Fallback: use GetAssetsByClass (Blueprint class index, O(k)) but convert
    // the FName lookup so C++ comparison is O(1) per asset via FName hash.
    // This is still O(k) total (k = # Blueprints in project) but k << 8k (all assets).
    const FName BlueprintFName(*BlueprintName);

    TArray<FAssetData> BlueprintAssets;
    // bSearchSubClasses=true is needed to catch UAnimBlueprint, UWidgetBlueprint, etc.
    // (subclasses of UBlueprint).  These are common in game projects.
    // The class index is pre-built so this is O(k) — fast after AR warmup.
    AR.GetAssetsByClass(UBlueprint::StaticClass()->GetClassPathName(), BlueprintAssets, /*bSearchSubClasses=*/true);

    // Fast early-exit: if the AR returned no blueprints at all, the project
    // has no blueprints or the scan is incomplete — skip loop entirely.
    if (BlueprintAssets.IsEmpty())
    {
        GBlueprintMissingCache.Add(BlueprintName, FPlatformTime::Seconds());
        UE_LOG(LogTemp, Warning, TEXT("[MCP] FindBlueprintByName: AR returned 0 Blueprint assets (scan incomplete?) for '%s'"), *BlueprintName);
        return nullptr;
    }

    for (const FAssetData& Asset : BlueprintAssets)
    {
        // Fast FName hash comparison — O(1) per asset (no string allocation).
        if (Asset.AssetName != BlueprintFName) continue;

        // ── SAFE ASSET RESOLUTION ─────────────────────────────────────
        // Prefer FindObject (in-memory, no I/O) over Asset.GetAsset()
        // (which calls StaticLoadObject and can crash on first-session access
        // when the UPackage is in a partially-loaded state).
        UBlueprint* BP = FindObject<UBlueprint>(nullptr, *Asset.GetObjectPathString());
        if (!BP)
        {
            // Fall back to GetAsset() only if FindObject failed.
            // This is safe after WaitForCompletion() above because all
            // packages the AR knows about have finished their disk scan.
            BP = Cast<UBlueprint>(Asset.GetAsset());
        }
        if (BP && IsValid(BP))
        {
            GBlueprintNameCache.Add(BlueprintName, FSoftObjectPath(BP));
            GBlueprintMissingCache.Remove(BlueprintName);
            UE_LOG(LogTemp, Display, TEXT("FindBlueprintByName: found '%s' at '%s'"),
                *BlueprintName, *Asset.GetObjectPathString());
            return BP;
        }
    }

    // Record in the negative cache so the next call within 60 s returns O(1).
    GBlueprintMissingCache.Add(BlueprintName, FPlatformTime::Seconds());
    UE_LOG(LogTemp, Warning, TEXT("FindBlueprintByName: could not find blueprint '%s' anywhere under /Game (cached as missing for %.0f s)"),
        *BlueprintName, MISSING_CACHE_TTL_SECONDS);
    return nullptr;
}

UEdGraph* FUnrealMCPCommonUtils::FindOrCreateEventGraph(UBlueprint* Blueprint)
{
    if (!Blueprint)
    {
        return nullptr;
    }
    
    // Try to find the event graph
    for (UEdGraph* Graph : Blueprint->UbergraphPages)
    {
        if (Graph->GetName().Contains(TEXT("EventGraph")))
        {
            return Graph;
        }
    }
    
    // Create a new event graph if none exists
    UEdGraph* NewGraph = FBlueprintEditorUtils::CreateNewGraph(Blueprint, FName(TEXT("EventGraph")), UEdGraph::StaticClass(), UEdGraphSchema_K2::StaticClass());
    FBlueprintEditorUtils::AddUbergraphPage(Blueprint, NewGraph);
    return NewGraph;
}

// ─── Event-name alias table ────────────────────────────────────────────────
// Many callers use the friendly "BeginPlay" / "Tick" names. UE5 stores the
// override function under the UFUNCTION name on AActor / UActorComponent, which
// is sometimes different (e.g. "ReceiveBeginPlay" vs "BeginPlay").
// We resolve in this order:
//   1. Check existing nodes so we never duplicate (return existing node).
//   2. Look up alias → canonical UE5 function name.
//   3. Search the Blueprint's parent class hierarchy (not GeneratedClass,
//      which may be null for newly-created BPs) for the UFunction.
//   4. If not found in parent hierarchy, fall back to a custom event.
static const struct { const TCHAR* Alias; const TCHAR* UE5Name; const TCHAR* OwnerClass; }
GEventAliases[] =
{
    // AActor overrideable events
    { TEXT("BeginPlay"),          TEXT("ReceiveBeginPlay"),          TEXT("Actor") },
    { TEXT("EndPlay"),            TEXT("ReceiveEndPlay"),            TEXT("Actor") },
    { TEXT("Tick"),               TEXT("ReceiveTick"),               TEXT("Actor") },
    { TEXT("ActorBeginOverlap"),  TEXT("ReceiveActorBeginOverlap"),  TEXT("Actor") },
    { TEXT("ActorEndOverlap"),    TEXT("ReceiveActorEndOverlap"),    TEXT("Actor") },
    { TEXT("ActorHit"),           TEXT("ReceiveActorHit"),           TEXT("Actor") },
    { TEXT("Destroyed"),          TEXT("ReceiveDestroyed"),          TEXT("Actor") },
    { TEXT("AnyDamage"),          TEXT("ReceiveAnyDamage"),          TEXT("Actor") },
    { TEXT("PointDamage"),        TEXT("ReceivePointDamage"),        TEXT("Actor") },
    { TEXT("RadialDamage"),       TEXT("ReceiveRadialDamage"),       TEXT("Actor") },
    // APawn
    { TEXT("SetupPlayerInput"),   TEXT("ReceiveInput"),              TEXT("Pawn")  },
    // UActorComponent overrideable events
    { TEXT("InitializeComponent"),TEXT("ReceiveInitializeComponent"),TEXT("ActorComponent") },
    { TEXT("BeginDestroy"),       TEXT("ReceiveBeginDestroy"),       TEXT("ActorComponent") },
    // Direct UE5 names (no alias needed — included so they still work)
    { TEXT("ReceiveBeginPlay"),   TEXT("ReceiveBeginPlay"),          TEXT("Actor") },
    { TEXT("ReceiveEndPlay"),     TEXT("ReceiveEndPlay"),            TEXT("Actor") },
    { TEXT("ReceiveTick"),        TEXT("ReceiveTick"),               TEXT("Actor") },
};

// Blueprint node utilities
UK2Node_Event* FUnrealMCPCommonUtils::CreateEventNode(UEdGraph* Graph, const FString& EventName, const FVector2D& Position)
{
    if (!Graph)
        return nullptr;

    UBlueprint* Blueprint = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (!Blueprint)
        return nullptr;

    FName EventFName(*EventName);

    // ── 1. Return existing node to avoid duplicates ──────────────────────────
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        UK2Node_Event* EventNode = Cast<UK2Node_Event>(Node);
        if (EventNode && EventNode->EventReference.GetMemberName() == EventFName)
        {
            UE_LOG(LogTemp, Display, TEXT("[MCP] CreateEventNode: returning existing node '%s' (ID: %s)"),
                *EventName, *EventNode->NodeGuid.ToString());
            return EventNode;
        }
    }

    // ── 2. Resolve alias → canonical UE5 function name ───────────────────────
    FString CanonicalName = EventName;
    for (const auto& A : GEventAliases)
    {
        if (EventName.Equals(A.Alias, ESearchCase::IgnoreCase))
        {
            CanonicalName = A.UE5Name;
            break;
        }
    }
    FName CanonicalFName(*CanonicalName);

    // ── 3. Walk the parent class hierarchy (safe — no GeneratedClass needed) ─
    //       Blueprint->ParentClass is always valid; GeneratedClass may be null
    //       for newly-created BPs that haven't been compiled yet.
    UFunction* EventFunction  = nullptr;
    UClass*    OwnerClass     = nullptr;

    UClass* SearchClass = Blueprint->ParentClass;
    while (SearchClass)
    {
        UFunction* F = SearchClass->FindFunctionByName(CanonicalFName, EIncludeSuperFlag::ExcludeSuper);
        if (F)
        {
            EventFunction = F;
            OwnerClass    = SearchClass;
            break;
        }
        SearchClass = SearchClass->GetSuperClass();
    }

    UK2Node_Event* EventNode = nullptr;

    if (EventFunction && OwnerClass)
    {
        // Standard override event — use bOverrideFunction so UE5 knows this
        // is an overridden event, not a new custom event.
        EventNode = NewObject<UK2Node_Event>(Graph);
        EventNode->EventReference.SetExternalMember(CanonicalFName, OwnerClass);
        EventNode->bOverrideFunction = true;
        EventNode->NodePosX = (int32)Position.X;
        EventNode->NodePosY = (int32)Position.Y;
        EventNode->CreateNewGuid();
        Graph->AddNode(EventNode, true);
        EventNode->PostPlacedNewNode();
        EventNode->AllocateDefaultPins();
        UE_LOG(LogTemp, Display, TEXT("[MCP] CreateEventNode: override event '%s' on %s (ID: %s)"),
            *CanonicalName, *OwnerClass->GetName(), *EventNode->NodeGuid.ToString());
    }
    else
    {
        // ── 4. Fall back: create a custom event with the requested name ───────
        //       This covers project-specific events not in the parent class.
        UE_LOG(LogTemp, Warning, TEXT("[MCP] CreateEventNode: '%s' not found in parent hierarchy — creating custom event"),
            *CanonicalName);

        UK2Node_CustomEvent* CustomNode = NewObject<UK2Node_CustomEvent>(Graph);
        if (!CustomNode)
        {
            UE_LOG(LogTemp, Error, TEXT("[MCP] CreateEventNode: failed to create custom event '%s'"), *CanonicalName);
            return nullptr;
        }
        CustomNode->CustomFunctionName = CanonicalFName;
        CustomNode->NodePosX = (int32)Position.X;
        CustomNode->NodePosY = (int32)Position.Y;
        CustomNode->CreateNewGuid();
        Graph->AddNode(CustomNode, true);
        CustomNode->PostPlacedNewNode();
        CustomNode->AllocateDefaultPins();
        // UK2Node_CustomEvent IS a UK2Node_Event subclass
        EventNode = Cast<UK2Node_Event>(CustomNode);
        UE_LOG(LogTemp, Display, TEXT("[MCP] CreateEventNode: custom event '%s' (ID: %s)"),
            *CanonicalName, EventNode ? *EventNode->NodeGuid.ToString() : TEXT("null"));
    }

    return EventNode;
}

UK2Node_CallFunction* FUnrealMCPCommonUtils::CreateFunctionCallNode(UEdGraph* Graph, UFunction* Function, const FVector2D& Position)
{
    if (!Graph || !Function)
    {
        return nullptr;
    }
    
    UK2Node_CallFunction* FunctionNode = NewObject<UK2Node_CallFunction>(Graph);
    FunctionNode->SetFromFunction(Function);
    FunctionNode->NodePosX = Position.X;
    FunctionNode->NodePosY = Position.Y;
    FunctionNode->CreateNewGuid();
    // CRASH-003 pattern: PostPlacedNewNode→MarkBlueprintAsStructurallyModified crashes UE5.6.
    // AddNode(bFromUI=false) then AllocateDefaultPins() — SetFromFunction already set the
    // function reference so AllocateDefaultPins() produces all typed pins correctly.
    Graph->AddNode(FunctionNode, /*bFromUI=*/false, /*bSelectNewNode=*/false);
    FunctionNode->AllocateDefaultPins();

    // Some project/module functions can come through as unresolved zero-pin call nodes
    // when SetFromFunction alone does not bind the external member reference.
    auto CountValidPins = [](const UK2Node_CallFunction* Node) -> int32
    {
        int32 Count = 0;
        for (UEdGraphPin* Pin : Node->Pins)
        {
            if (Pin)
            {
                ++Count;
            }
        }
        return Count;
    };
    if (CountValidPins(FunctionNode) == 0)
    {
        if (UClass* OwnerClass = Function->GetOuterUClass())
        {
            FunctionNode->FunctionReference.SetExternalMember(Function->GetFName(), OwnerClass);
            FunctionNode->ReconstructNode();
        }
    }

    return FunctionNode;
}

UK2Node_VariableGet* FUnrealMCPCommonUtils::CreateVariableGetNode(UEdGraph* Graph, UBlueprint* Blueprint, const FString& VariableName, const FVector2D& Position)
{
    if (!Graph || !Blueprint)
        return nullptr;

    UK2Node_VariableGet* VariableGetNode = NewObject<UK2Node_VariableGet>(Graph);
    VariableGetNode->VariableReference.SetSelfMember(FName(*VariableName));
    VariableGetNode->NodePosX = Position.X;
    VariableGetNode->NodePosY = Position.Y;
    VariableGetNode->CreateNewGuid();
    // CRASH-003 pattern: PostPlacedNewNode→MarkBlueprintAsStructurallyModified crashes UE5.6.
    // Use AddNode(bFromUI=false) + AllocateDefaultPins() only — variable pins are fully
    // materialised by AllocateDefaultPins(); the VariableReference is set above.
    Graph->AddNode(VariableGetNode, /*bFromUI=*/false, /*bSelectNewNode=*/false);
    VariableGetNode->AllocateDefaultPins();
    return VariableGetNode;
}

UK2Node_VariableSet* FUnrealMCPCommonUtils::CreateVariableSetNode(UEdGraph* Graph, UBlueprint* Blueprint, const FString& VariableName, const FVector2D& Position)
{
    if (!Graph || !Blueprint)
        return nullptr;

    UK2Node_VariableSet* VariableSetNode = NewObject<UK2Node_VariableSet>(Graph);
    VariableSetNode->VariableReference.SetSelfMember(FName(*VariableName));
    VariableSetNode->NodePosX = Position.X;
    VariableSetNode->NodePosY = Position.Y;
    VariableSetNode->CreateNewGuid();
    // CRASH-003 pattern: PostPlacedNewNode→MarkBlueprintAsStructurallyModified crashes UE5.6.
    Graph->AddNode(VariableSetNode, /*bFromUI=*/false, /*bSelectNewNode=*/false);
    VariableSetNode->AllocateDefaultPins();
    return VariableSetNode;
}

UK2Node_InputAction* FUnrealMCPCommonUtils::CreateInputActionNode(UEdGraph* Graph, const FString& ActionName, const FVector2D& Position)
{
    if (!Graph)
        return nullptr;

    UK2Node_InputAction* InputActionNode = NewObject<UK2Node_InputAction>(Graph);
    InputActionNode->InputActionName = FName(*ActionName);
    InputActionNode->NodePosX = (int32)Position.X;
    InputActionNode->NodePosY = (int32)Position.Y;
    InputActionNode->CreateNewGuid();

    // AddNode with bFromUI=false to skip the OnNodeAdded notification chain
    // that validates the action name against Project Input Settings (slow on
    // projects that haven't loaded Input Settings yet — can take 20-30s).
    Graph->AddNode(InputActionNode, /*bFromUI=*/false, /*bSelectNewNode=*/false);
    // Skip PostPlacedNewNode() — it triggers input settings validation.
    // Call AllocateDefaultPins() directly to set up Pressed/Released exec pins.
    InputActionNode->AllocateDefaultPins();

    UE_LOG(LogTemp, Display, TEXT("[MCP] CreateInputActionNode: created legacy InputAction node '%s'"), *ActionName);
    return InputActionNode;
}

UK2Node_Self* FUnrealMCPCommonUtils::CreateSelfReferenceNode(UEdGraph* Graph, const FVector2D& Position)
{
    if (!Graph)
        return nullptr;

    UK2Node_Self* SelfNode = NewObject<UK2Node_Self>(Graph);
    SelfNode->NodePosX = (int32)Position.X;
    SelfNode->NodePosY = (int32)Position.Y;
    SelfNode->CreateNewGuid();
    // AddNode with bFromUI=false + bSelectNewNode=false avoids the
    // OnNodeAdded path that calls PostPlacedNewNode() → GetSchema() →
    // GetGraphType() → dereferences Blueprint->GeneratedClass, which can
    // block 20-45 s if the Blueprint is in an intermediate compile state.
    Graph->AddNode(SelfNode, /*bFromUI=*/false, /*bSelectNewNode=*/false);
    // Skip PostPlacedNewNode() for the same reason.
    SelfNode->AllocateDefaultPins();
    UE_LOG(LogTemp, Display, TEXT("[MCP] CreateSelfReferenceNode: created Self node (ID: %s)"),
        *SelfNode->NodeGuid.ToString());
    return SelfNode;
}

bool FUnrealMCPCommonUtils::ConnectGraphNodes(UEdGraph* Graph, UEdGraphNode* SourceNode, const FString& SourcePinName, 
                                           UEdGraphNode* TargetNode, const FString& TargetPinName)
{
    FString Discard;
    return ConnectGraphNodes(Graph, SourceNode, SourcePinName, TargetNode, TargetPinName, Discard);
}

bool FUnrealMCPCommonUtils::ConnectGraphNodes(UEdGraph* Graph, UEdGraphNode* SourceNode, const FString& SourcePinName,
                                           UEdGraphNode* TargetNode, const FString& TargetPinName, FString& OutError)
{
    OutError.Empty();

    if (!Graph || !SourceNode || !TargetNode)
    {
        OutError = TEXT("ConnectGraphNodes: null Graph, SourceNode, or TargetNode");
        return false;
    }
    
    // Try directional search first; retry direction-agnostic if not found.
    // Each pin is retried INDEPENDENTLY so that finding one doesn't block the other.
    UEdGraphPin* SourcePin = FindPin(SourceNode, SourcePinName, EGPD_Output);
    if (!SourcePin) SourcePin = FindPin(SourceNode, SourcePinName, EGPD_MAX);

    UEdGraphPin* TargetPin = FindPin(TargetNode, TargetPinName, EGPD_Input);
    if (!TargetPin) TargetPin = FindPin(TargetNode, TargetPinName, EGPD_MAX);

    if (!SourcePin)
    {
        OutError = FString::Printf(TEXT("Pin '%s' not found on source node '%s'"),
            *SourcePinName, *SourceNode->GetName());
        return false;
    }
    if (!TargetPin)
    {
        OutError = FString::Printf(TEXT("Pin '%s' not found on target node '%s'"),
            *TargetPinName, *TargetNode->GetName());
        return false;
    }

    // Prefer schema-based connection  -  it handles type compatibility, breaks
    // existing exclusive links (exec pins), and fires property-change notifies.
    const UEdGraphSchema_K2* K2Schema = Cast<const UEdGraphSchema_K2>(Graph->GetSchema());
    if (K2Schema)
    {
        // CanCreateConnection returns a response with a Message on failure.
        const FPinConnectionResponse Response = K2Schema->CanCreateConnection(SourcePin, TargetPin);
        if (Response.Response == CONNECT_RESPONSE_DISALLOW)
        {
            // Schema explicitly forbids this connection.  Do NOT fall back to
            // raw MakeLinkTo  -  that produces broken graphs that crash on compile.
            OutError = FString::Printf(
                TEXT("Schema disallows '%s'.'%s' -> '%s'.'%s': %s"),
                *SourceNode->GetName(), *SourcePinName,
                *TargetNode->GetName(), *TargetPinName,
                *Response.Message.ToString());
            UE_LOG(LogTemp, Warning, TEXT("ConnectGraphNodes: %s"), *OutError);
            return false;
        }

        // TryCreateConnection also calls BreakSinglePinLink for exclusive connections.
        K2Schema->TryCreateConnection(SourcePin, TargetPin);
        return true;
    }

    // Fallback: raw link (no type validation  -  only reached when no K2 schema)
    SourcePin->MakeLinkTo(TargetPin);
    return true;
}

UEdGraphPin* FUnrealMCPCommonUtils::FindPin(UEdGraphNode* Node, const FString& PinName, EEdGraphPinDirection Direction)
{
    if (!Node)
    {
        return nullptr;
    }
    
    // Log all pins for debugging
    UE_LOG(LogTemp, Display, TEXT("FindPin: Looking for pin '%s' (Direction: %d) in node '%s'"), 
           *PinName, (int32)Direction, *Node->GetName());
    
    for (UEdGraphPin* Pin : Node->Pins)
    {
        UE_LOG(LogTemp, Display, TEXT("  - Available pin: '%s', Direction: %d, Category: %s"), 
               *Pin->PinName.ToString(), (int32)Pin->Direction, *Pin->PinType.PinCategory.ToString());
    }

    // ----------------------------------------------------------------
    // Build alias list: some callers say "execute" when the pin is named
    // "then" and vice-versa, or use alternate capitalisation.
    // ----------------------------------------------------------------
    TArray<FString> Candidates;
    Candidates.Add(PinName);

    // Common exec-pin alias pairs
    FString PinLower = PinName.ToLower();
    if (PinLower == TEXT("execute") || PinLower == TEXT("exec"))
    {
        Candidates.Add(TEXT("execute")); Candidates.Add(TEXT("exec")); Candidates.Add(TEXT("then"));
    }
    else if (PinLower == TEXT("then"))
    {
        Candidates.Add(TEXT("execute")); Candidates.Add(TEXT("exec"));
    }
    else if (PinLower == TEXT("returnvalue") || PinLower == TEXT("return_value") || PinLower == TEXT("return value"))
    {
        // "return value" variants
        Candidates.Add(TEXT("ReturnValue")); Candidates.Add(TEXT("return value"));
    }

    // ---- 1. Exact name match (with aliases) ----
    for (const FString& Candidate : Candidates)
    {
        for (UEdGraphPin* Pin : Node->Pins)
        {
            if (Pin && Pin->PinName.ToString() == Candidate &&
                (Direction == EGPD_MAX || Pin->Direction == Direction))
            {
                UE_LOG(LogTemp, Display, TEXT("  - Found exact matching pin: '%s'"), *Pin->PinName.ToString());
                return Pin;
            }
        }
    }

    // ---- 2. Case-insensitive match (with aliases) ----
    for (const FString& Candidate : Candidates)
    {
        for (UEdGraphPin* Pin : Node->Pins)
        {
            if (Pin && Pin->PinName.ToString().Equals(Candidate, ESearchCase::IgnoreCase) &&
                (Direction == EGPD_MAX || Pin->Direction == Direction))
            {
                UE_LOG(LogTemp, Display, TEXT("  - Found case-insensitive matching pin: '%s'"), *Pin->PinName.ToString());
                return Pin;
            }
        }
    }

    // ---- 3. Fallback: first data output pin on VariableGet nodes ----
    if (Direction == EGPD_Output && Cast<UK2Node_VariableGet>(Node) != nullptr)
    {
        for (UEdGraphPin* Pin : Node->Pins)
        {
            if (Pin && Pin->Direction == EGPD_Output &&
                Pin->PinType.PinCategory != UEdGraphSchema_K2::PC_Exec)
            {
                UE_LOG(LogTemp, Display, TEXT("  - Found fallback data output pin: '%s'"), *Pin->PinName.ToString());
                return Pin;
            }
        }
    }
    
    UE_LOG(LogTemp, Warning, TEXT("  - No matching pin found for '%s'"), *PinName);
    return nullptr;
}

// Actor utilities
TSharedPtr<FJsonValue> FUnrealMCPCommonUtils::ActorToJson(AActor* Actor)
{
    if (!Actor)
    {
        return MakeShared<FJsonValueNull>();
    }
    
    TSharedPtr<FJsonObject> ActorObject = MakeShared<FJsonObject>();
    ActorObject->SetStringField(TEXT("name"), Actor->GetName());
    ActorObject->SetStringField(TEXT("class"), Actor->GetClass()->GetName());
    
    FVector Location = Actor->GetActorLocation();
    TArray<TSharedPtr<FJsonValue>> LocationArray;
    LocationArray.Add(MakeShared<FJsonValueNumber>(Location.X));
    LocationArray.Add(MakeShared<FJsonValueNumber>(Location.Y));
    LocationArray.Add(MakeShared<FJsonValueNumber>(Location.Z));
    ActorObject->SetArrayField(TEXT("location"), LocationArray);
    
    FRotator Rotation = Actor->GetActorRotation();
    TArray<TSharedPtr<FJsonValue>> RotationArray;
    RotationArray.Add(MakeShared<FJsonValueNumber>(Rotation.Pitch));
    RotationArray.Add(MakeShared<FJsonValueNumber>(Rotation.Yaw));
    RotationArray.Add(MakeShared<FJsonValueNumber>(Rotation.Roll));
    ActorObject->SetArrayField(TEXT("rotation"), RotationArray);
    
    FVector Scale = Actor->GetActorScale3D();
    TArray<TSharedPtr<FJsonValue>> ScaleArray;
    ScaleArray.Add(MakeShared<FJsonValueNumber>(Scale.X));
    ScaleArray.Add(MakeShared<FJsonValueNumber>(Scale.Y));
    ScaleArray.Add(MakeShared<FJsonValueNumber>(Scale.Z));
    ActorObject->SetArrayField(TEXT("scale"), ScaleArray);
    
    return MakeShared<FJsonValueObject>(ActorObject);
}

TSharedPtr<FJsonObject> FUnrealMCPCommonUtils::ActorToJsonObject(AActor* Actor, bool bDetailed)
{
    if (!Actor)
    {
        return nullptr;
    }
    
    TSharedPtr<FJsonObject> ActorObject = MakeShared<FJsonObject>();
    ActorObject->SetStringField(TEXT("name"), Actor->GetName());
    ActorObject->SetStringField(TEXT("class"), Actor->GetClass()->GetName());
    
    FVector Location = Actor->GetActorLocation();
    TArray<TSharedPtr<FJsonValue>> LocationArray;
    LocationArray.Add(MakeShared<FJsonValueNumber>(Location.X));
    LocationArray.Add(MakeShared<FJsonValueNumber>(Location.Y));
    LocationArray.Add(MakeShared<FJsonValueNumber>(Location.Z));
    ActorObject->SetArrayField(TEXT("location"), LocationArray);
    
    FRotator Rotation = Actor->GetActorRotation();
    TArray<TSharedPtr<FJsonValue>> RotationArray;
    RotationArray.Add(MakeShared<FJsonValueNumber>(Rotation.Pitch));
    RotationArray.Add(MakeShared<FJsonValueNumber>(Rotation.Yaw));
    RotationArray.Add(MakeShared<FJsonValueNumber>(Rotation.Roll));
    ActorObject->SetArrayField(TEXT("rotation"), RotationArray);
    
    FVector Scale = Actor->GetActorScale3D();
    TArray<TSharedPtr<FJsonValue>> ScaleArray;
    ScaleArray.Add(MakeShared<FJsonValueNumber>(Scale.X));
    ScaleArray.Add(MakeShared<FJsonValueNumber>(Scale.Y));
    ScaleArray.Add(MakeShared<FJsonValueNumber>(Scale.Z));
    ActorObject->SetArrayField(TEXT("scale"), ScaleArray);
    
    return ActorObject;
}

UK2Node_Event* FUnrealMCPCommonUtils::FindExistingEventNode(UEdGraph* Graph, const FString& EventName)
{
    if (!Graph)
    {
        return nullptr;
    }

    // Look for existing event nodes
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        UK2Node_Event* EventNode = Cast<UK2Node_Event>(Node);
        if (EventNode && EventNode->EventReference.GetMemberName() == FName(*EventName))
        {
            UE_LOG(LogTemp, Display, TEXT("Found existing event node with name: %s"), *EventName);
            return EventNode;
        }
    }

    return nullptr;
}

bool FUnrealMCPCommonUtils::SetObjectProperty(UObject* Object, const FString& PropertyName, 
                                     const TSharedPtr<FJsonValue>& Value, FString& OutErrorMessage)
{
    if (!Object)
    {
        OutErrorMessage = TEXT("Invalid object");
        return false;
    }

    FProperty* Property = Object->GetClass()->FindPropertyByName(*PropertyName);
    if (!Property)
    {
        OutErrorMessage = FString::Printf(TEXT("Property not found: %s"), *PropertyName);
        return false;
    }

    void* PropertyAddr = Property->ContainerPtrToValuePtr<void>(Object);
    
    // Handle different property types
    if (Property->IsA<FBoolProperty>())
    {
        ((FBoolProperty*)Property)->SetPropertyValue(PropertyAddr, Value->AsBool());
        return true;
    }
    else if (Property->IsA<FIntProperty>())
    {
        int32 IntValue = static_cast<int32>(Value->AsNumber());
        FIntProperty* IntProperty = CastField<FIntProperty>(Property);
        if (IntProperty)
        {
            IntProperty->SetPropertyValue_InContainer(Object, IntValue);
            return true;
        }
    }
    else if (Property->IsA<FFloatProperty>())
    {
        ((FFloatProperty*)Property)->SetPropertyValue(PropertyAddr, Value->AsNumber());
        return true;
    }
    else if (Property->IsA<FStrProperty>())
    {
        ((FStrProperty*)Property)->SetPropertyValue(PropertyAddr, Value->AsString());
        return true;
    }
    else if (Property->IsA<FByteProperty>())
    {
        FByteProperty* ByteProp = CastField<FByteProperty>(Property);
        UEnum* EnumDef = ByteProp ? ByteProp->GetIntPropertyEnum() : nullptr;
        
        // If this is a TEnumAsByte property (has associated enum)
        if (EnumDef)
        {
            // Handle numeric value
            if (Value->Type == EJson::Number)
            {
                uint8 ByteValue = static_cast<uint8>(Value->AsNumber());
                ByteProp->SetPropertyValue(PropertyAddr, ByteValue);
                
                UE_LOG(LogTemp, Display, TEXT("Setting enum property %s to numeric value: %d"), 
                      *PropertyName, ByteValue);
                return true;
            }
            // Handle string enum value
            else if (Value->Type == EJson::String)
            {
                FString EnumValueName = Value->AsString();
                
                // Try to convert numeric string to number first
                if (EnumValueName.IsNumeric())
                {
                    uint8 ByteValue = FCString::Atoi(*EnumValueName);
                    ByteProp->SetPropertyValue(PropertyAddr, ByteValue);
                    
                    UE_LOG(LogTemp, Display, TEXT("Setting enum property %s to numeric string value: %s -> %d"), 
                          *PropertyName, *EnumValueName, ByteValue);
                    return true;
                }
                
                // Handle qualified enum names (e.g., "Player0" or "EAutoReceiveInput::Player0")
                if (EnumValueName.Contains(TEXT("::")))
                {
                    EnumValueName.Split(TEXT("::"), nullptr, &EnumValueName);
                }
                
                int64 EnumValue = EnumDef->GetValueByNameString(EnumValueName);
                if (EnumValue == INDEX_NONE)
                {
                    // Try with full name as fallback
                    EnumValue = EnumDef->GetValueByNameString(Value->AsString());
                }
                
                if (EnumValue != INDEX_NONE)
                {
                    ByteProp->SetPropertyValue(PropertyAddr, static_cast<uint8>(EnumValue));
                    
                    UE_LOG(LogTemp, Display, TEXT("Setting enum property %s to name value: %s -> %lld"), 
                          *PropertyName, *EnumValueName, EnumValue);
                    return true;
                }
                else
                {
                    // Log all possible enum values for debugging
                    UE_LOG(LogTemp, Warning, TEXT("Could not find enum value for '%s'. Available options:"), *EnumValueName);
                    for (int32 i = 0; i < EnumDef->NumEnums(); i++)
                    {
                        UE_LOG(LogTemp, Warning, TEXT("  - %s (value: %d)"), 
                               *EnumDef->GetNameStringByIndex(i), EnumDef->GetValueByIndex(i));
                    }
                    
                    OutErrorMessage = FString::Printf(TEXT("Could not find enum value for '%s'"), *EnumValueName);
                    return false;
                }
            }
        }
        else
        {
            // Regular byte property
            uint8 ByteValue = static_cast<uint8>(Value->AsNumber());
            ByteProp->SetPropertyValue(PropertyAddr, ByteValue);
            return true;
        }
    }
    else if (Property->IsA<FEnumProperty>())
    {
        FEnumProperty* EnumProp = CastField<FEnumProperty>(Property);
        UEnum* EnumDef = EnumProp ? EnumProp->GetEnum() : nullptr;
        FNumericProperty* UnderlyingNumericProp = EnumProp ? EnumProp->GetUnderlyingProperty() : nullptr;
        
        if (EnumDef && UnderlyingNumericProp)
        {
            // Handle numeric value
            if (Value->Type == EJson::Number)
            {
                int64 EnumValue = static_cast<int64>(Value->AsNumber());
                UnderlyingNumericProp->SetIntPropertyValue(PropertyAddr, EnumValue);
                
                UE_LOG(LogTemp, Display, TEXT("Setting enum property %s to numeric value: %lld"), 
                      *PropertyName, EnumValue);
                return true;
            }
            // Handle string enum value
            else if (Value->Type == EJson::String)
            {
                FString EnumValueName = Value->AsString();
                
                // Try to convert numeric string to number first
                if (EnumValueName.IsNumeric())
                {
                    int64 EnumValue = FCString::Atoi64(*EnumValueName);
                    UnderlyingNumericProp->SetIntPropertyValue(PropertyAddr, EnumValue);
                    
                    UE_LOG(LogTemp, Display, TEXT("Setting enum property %s to numeric string value: %s -> %lld"), 
                          *PropertyName, *EnumValueName, EnumValue);
                    return true;
                }
                
                // Handle qualified enum names
                if (EnumValueName.Contains(TEXT("::")))
                {
                    EnumValueName.Split(TEXT("::"), nullptr, &EnumValueName);
                }
                
                int64 EnumValue = EnumDef->GetValueByNameString(EnumValueName);
                if (EnumValue == INDEX_NONE)
                {
                    // Try with full name as fallback
                    EnumValue = EnumDef->GetValueByNameString(Value->AsString());
                }
                
                if (EnumValue != INDEX_NONE)
                {
                    UnderlyingNumericProp->SetIntPropertyValue(PropertyAddr, EnumValue);
                    
                    UE_LOG(LogTemp, Display, TEXT("Setting enum property %s to name value: %s -> %lld"), 
                          *PropertyName, *EnumValueName, EnumValue);
                    return true;
                }
                else
                {
                    // Log all possible enum values for debugging
                    UE_LOG(LogTemp, Warning, TEXT("Could not find enum value for '%s'. Available options:"), *EnumValueName);
                    for (int32 i = 0; i < EnumDef->NumEnums(); i++)
                    {
                        UE_LOG(LogTemp, Warning, TEXT("  - %s (value: %d)"), 
                               *EnumDef->GetNameStringByIndex(i), EnumDef->GetValueByIndex(i));
                    }
                    
                    OutErrorMessage = FString::Printf(TEXT("Could not find enum value for '%s'"), *EnumValueName);
                    return false;
                }
            }
        }
    }
    
    else if (FObjectProperty* ObjProp = CastField<FObjectProperty>(Property))
    {
        // Hard UObject* reference (e.g. USkeletalMesh*, UMaterialInterface*, UTexture*).
        // BUG-E FIX: Use UEditorAssetLibrary::LoadAsset (consistent with rest of codebase)
        //   instead of StaticLoadObject(UObject::StaticClass(), ...) which skips type checks.
        if (Value->Type != EJson::String)
        {
            OutErrorMessage = FString::Printf(
                TEXT("FObjectProperty '%s' requires a string asset path"), *PropertyName);
            return false;
        }
        FString AssetPath = Value->AsString();
        UObject* LoadedAsset = UEditorAssetLibrary::LoadAsset(AssetPath);
        if (!LoadedAsset)
        {
            // Fallback: FindObject (already-loaded assets, e.g. engine defaults).
            LoadedAsset = FindObject<UObject>(nullptr, *AssetPath);
        }
        if (!LoadedAsset)
        {
            OutErrorMessage = FString::Printf(
                TEXT("Asset not found for FObjectProperty '%s': %s"), *PropertyName, *AssetPath);
            return false;
        }
        ObjProp->SetObjectPropertyValue(PropertyAddr, LoadedAsset);
        UE_LOG(LogTemp, Display,
            TEXT("SetObjectProperty: set FObjectProperty '%s' to '%s'"),
            *PropertyName, *AssetPath);
        return true;
    }
    else if (FSoftObjectProperty* SoftProp = CastField<FSoftObjectProperty>(Property))
    {
        // BUG-F FIX: FSoftObjectProperty is NOT a subclass of FObjectProperty — it IS-A
        //   FObjectPropertyBase.  The original code put this branch inside the
        //   FObjectPropertyBase block after the FObjectProperty cast, so it was
        //   unreachable (if ObjProp cast succeeded we returned; if it failed the
        //   SoftProp cast was never reached because they are siblings, not parent/child).
        //   Fix: promote to a top-level else-if so it is always evaluated.
        if (Value->Type != EJson::String)
        {
            OutErrorMessage = FString::Printf(
                TEXT("FSoftObjectProperty '%s' requires a string asset path"), *PropertyName);
            return false;
        }
        FString AssetPath = Value->AsString();
        // Use brace-init to avoid the Most Vexing Parse:
        // FSoftObjectPtr SoftRef(FSoftObjectPath(AssetPath)) is parsed by MSVC
        // as a function declaration, not a constructor call, causing C2664.
        FSoftObjectPtr SoftRef{FSoftObjectPath{AssetPath}};
        SoftProp->SetPropertyValue(PropertyAddr, SoftRef);
        UE_LOG(LogTemp, Display,
            TEXT("SetObjectProperty: set FSoftObjectProperty '%s' to '%s'"),
            *PropertyName, *AssetPath);
        return true;
    }
    else if (Property->IsA<FClassProperty>())
    {
        FClassProperty* ClassProp = CastField<FClassProperty>(Property);
        if (ClassProp && Value->Type == EJson::String)
        {
            FString ClassName = Value->AsString();

            // Try to find the class by name (short name or full path)
            UClass* FoundClass = nullptr;

            // First try as a full object path (nullptr outer searches all packages in UE5.6+)
            FoundClass = FindObject<UClass>(nullptr, *ClassName);

            // If not found, try searching all loaded classes by short name
            if (!FoundClass)
            {
                for (TObjectIterator<UClass> It; It; ++It)
                {
                    if (It->GetName() == ClassName || It->GetFName() == FName(*ClassName))
                    {
                        // Make sure the class is compatible with the property's meta class
                        if (!ClassProp->MetaClass || It->IsChildOf(ClassProp->MetaClass))
                        {
                            FoundClass = *It;
                            break;
                        }
                    }
                }
            }

            if (FoundClass)
            {
                ClassProp->SetPropertyValue(PropertyAddr, FoundClass);
                UE_LOG(LogTemp, Display, TEXT("Setting class property %s to class: %s"),
                       *PropertyName, *FoundClass->GetName());
                return true;
            }
            else
            {
                OutErrorMessage = FString::Printf(TEXT("Could not find class: %s for property %s"), *ClassName, *PropertyName);
                return false;
            }
        }
    }
    else if (Property->IsA<FSoftClassProperty>())
    {
        FSoftClassProperty* SoftClassProp = CastField<FSoftClassProperty>(Property);
        if (SoftClassProp && Value->Type == EJson::String)
        {
            FString ClassName = Value->AsString();
            UClass* FoundClass = FindObject<UClass>(nullptr, *ClassName);
            if (!FoundClass)
            {
                for (TObjectIterator<UClass> It; It; ++It)
                {
                    if (It->GetName() == ClassName)
                    {
                        if (!SoftClassProp->MetaClass || It->IsChildOf(SoftClassProp->MetaClass))
                        {
                            FoundClass = *It;
                            break;
                        }
                    }
                }
            }
            if (FoundClass)
            {
                // Build the soft path from the class's package+object path,
                // then brace-init FSoftObjectPtr to avoid MSVC Most Vexing Parse (C2664).
                FSoftObjectPath SoftPath(FoundClass);
                FSoftObjectPtr SoftPtr{SoftPath};
                SoftClassProp->SetPropertyValue(PropertyAddr, SoftPtr);
                return true;
            }
            else
            {
                OutErrorMessage = FString::Printf(TEXT("Could not find class: %s for property %s"), *ClassName, *PropertyName);
                return false;
            }
        }
    }

    OutErrorMessage = FString::Printf(TEXT("Unsupported property type: %s for property %s"), 
                                    *Property->GetClass()->GetName(), *PropertyName);
    return false;
} 