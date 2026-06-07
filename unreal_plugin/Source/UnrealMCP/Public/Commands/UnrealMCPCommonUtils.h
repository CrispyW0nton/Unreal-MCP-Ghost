#pragma once

#include "CoreMinimal.h"
#include "EdGraph/EdGraphPin.h"
#include "Json.h"
#include "HAL/PlatformMisc.h"

// ---------------------------------------------------------------------------
// MCP_GUARDED_RUN(Body, OutSehCrash)
//
// Wraps an arbitrary statement block in MSVC __try/__except so that a
// hardware exception (e.g. EXCEPTION_ACCESS_VIOLATION) inside the block
// is caught and the editor survives.
//
// USE THIS for any Blueprint / SCS / component-template mutation that may
// indirectly trigger AssetRegistry / Content Browser walks on the *current*
// thread (the deferred-tick crashes are NOT caught by this — see
// SafeMarkBlueprintModifiedDeferred for that case).
//
// Why __except(1) instead of EXCEPTION_EXECUTE_HANDLER:
//   The numeric literal works regardless of <excpt.h> / Windows.h macro
//   ordering in IWYU builds. Both evaluate to the same value.
//
// Clang / clang-cl do NOT support MSVC SEH; on those compilers the body
// runs unguarded.
// ---------------------------------------------------------------------------
#if PLATFORM_WINDOWS && defined(_MSC_VER) && !defined(__clang__)
    #define MCP_GUARDED_RUN(Body, OutSehCrash)              \
        do {                                                 \
            (OutSehCrash) = false;                           \
            __try { Body; }                                  \
            __except (1) { (OutSehCrash) = true; }           \
        } while (0)
#else
    #define MCP_GUARDED_RUN(Body, OutSehCrash)              \
        do { (OutSehCrash) = false; Body; } while (0)
#endif

// Forward declarations
class AActor;
class UBlueprint;
class UEdGraph;
class UEdGraphNode;
class UEdGraphPin;
class UK2Node_Event;
class UK2Node_CallFunction;
class UK2Node_VariableGet;
class UK2Node_VariableSet;
class UK2Node_InputAction;
class UK2Node_Self;
class UFunction;

/**
 * Common utilities for UnrealMCP commands
 */
class UNREALMCP_API FUnrealMCPCommonUtils
{
public:
    // JSON utilities
    static TSharedPtr<FJsonObject> CreateErrorResponse(const FString& Message);
    static TSharedPtr<FJsonObject> CreateSuccessResponse(const TSharedPtr<FJsonObject>& Data = nullptr);
    static void GetIntArrayFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName, TArray<int32>& OutArray);
    static void GetFloatArrayFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName, TArray<float>& OutArray);
    static FVector2D GetVector2DFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName);
    static FVector GetVectorFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName);
    static FRotator GetRotatorFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName);

    // Actor utilities
    static TSharedPtr<FJsonValue> ActorToJson(AActor* Actor);
    static TSharedPtr<FJsonObject> ActorToJsonObject(AActor* Actor, bool bDetailed = false);

    // Blueprint utilities
    static UBlueprint* FindBlueprint(const FString& BlueprintName);
    static UBlueprint* FindBlueprintByName(const FString& BlueprintName);
    /** Remove a blueprint name from the negative-miss cache so it can be found
     *  immediately after creation (e.g. right after create_blueprint). */
    static void InvalidateBlueprintMissCache(const FString& BlueprintName);

    /**
     * Mark a Blueprint dirty without firing structural editor notifications.
     *
     * In this project, MarkBlueprintAsStructurallyModified can enter UnrealEd /
     * CoreUObject notification chains while MassEntityEditor has stale observers,
     * causing EXCEPTION_ACCESS_VIOLATION during MCP edits or on the next save.
     * This wrapper intentionally uses Modify + MarkPackageDirty only.
     *
     * NOTE: For SCS / component template mutations (especially ones that change
     * outgoing asset dependencies — e.g. setting AudioComponent.Sound,
     * StaticMeshComponent.StaticMesh, NiagaraComponent.Asset), prefer
     * SafeMarkBlueprintModifiedDeferred() instead. The synchronous variant
     * triggers the AssetRegistry to immediately re-walk outgoing dependencies,
     * which can race with a freshly-imported referenced asset that is still
     * mid-load and crash the next Content Browser tick.
     */
    static void SafeMarkBlueprintModified(UBlueprint* Blueprint);

    /**
     * Same as SafeMarkBlueprintModified, but defers the MarkPackageDirty()
     * notification to the next editor end-of-frame.
     *
     * Why deferred:
     *   MarkPackageDirty broadcasts UPackage::PackageDirtyStateChangedEvent →
     *   the AssetRegistry → ContentBrowserAssetDataSource queues a dependency
     *   rescan of the modified package. If a referenced asset (e.g. the new
     *   AudioComponent's Sound or NiagaraComponent's Asset) was just imported
     *   moments earlier, its USoundWave / UNiagaraSystem may still be in
     *   half-loaded state when the Content Browser ticks; the AR walk
     *   dereferences a TObjectPtr whose target object hasn't finished
     *   PostLoad and crashes with EXCEPTION_ACCESS_VIOLATION inside
     *   FAssetRegistry::GetDependencies / ContentBrowser::Tick.
     *
     *   By deferring the broadcast to the end of the current frame, we let
     *   the referenced asset's async load complete; the AR walk then sees
     *   a fully-initialized dependency and the Content Browser refreshes
     *   cleanly.
     *
     * Calls Blueprint->Modify() synchronously (safe; editor-undo only),
     * then schedules Blueprint->MarkPackageDirty() on the next end-of-frame
     * via FCoreDelegates::OnEndFrame using a TWeakObjectPtr for safety
     * across GC.
     */
    static void SafeMarkBlueprintModifiedDeferred(UBlueprint* Blueprint);

    /**
     * Validation-only check that Blueprint->GeneratedClass is non-null and valid.
     *
     * Returns true  — GeneratedClass exists; callers MAY proceed with PostPlacedNewNode,
     *                  ReconstructNode, or TrySetDefaultObject when appropriate.
     * Returns false — GeneratedClass is null; callers MUST skip those callbacks to
     *                  avoid EXCEPTION_ACCESS_VIOLATION in the MassEntityEditor observer.
     *
     * NOTE: This function intentionally does NOT call FKismetEditorUtilities::CompileBlueprint.
     * CompileBlueprint crashes UE5.6 when invoked from an async-task lambda context
     * (EXCEPTION_ACCESS_VIOLATION via MassEntityEditor observer). Callers that receive
     * false should fall back to direct pin DefaultObject/DefaultValue assignment.
     */
    static bool EnsureBlueprintGeneratedClass(UBlueprint* Blueprint);

    static UEdGraph* FindOrCreateEventGraph(UBlueprint* Blueprint);

    // Blueprint node utilities
    static UK2Node_Event* CreateEventNode(UEdGraph* Graph, const FString& EventName, const FVector2D& Position);
    static UK2Node_CallFunction* CreateFunctionCallNode(UEdGraph* Graph, UFunction* Function, const FVector2D& Position);
    static UK2Node_VariableGet* CreateVariableGetNode(UEdGraph* Graph, UBlueprint* Blueprint, const FString& VariableName, const FVector2D& Position);
    static UK2Node_VariableSet* CreateVariableSetNode(UEdGraph* Graph, UBlueprint* Blueprint, const FString& VariableName, const FVector2D& Position);
    static UK2Node_InputAction* CreateInputActionNode(UEdGraph* Graph, const FString& ActionName, const FVector2D& Position);
    static UK2Node_Self* CreateSelfReferenceNode(UEdGraph* Graph, const FVector2D& Position);
    /** Connect two nodes via the K2 schema.  Returns true on success.
     *  The OutError overload additionally fills OutError with the schema's
     *  reason when the connection is disallowed. */
    static bool ConnectGraphNodes(UEdGraph* Graph, UEdGraphNode* SourceNode, const FString& SourcePinName,
                                UEdGraphNode* TargetNode, const FString& TargetPinName);
    static bool ConnectGraphNodes(UEdGraph* Graph, UEdGraphNode* SourceNode, const FString& SourcePinName,
                                UEdGraphNode* TargetNode, const FString& TargetPinName, FString& OutError);
    static UEdGraphPin* FindPin(UEdGraphNode* Node, const FString& PinName, EEdGraphPinDirection Direction = EGPD_MAX);
    static UK2Node_Event* FindExistingEventNode(UEdGraph* Graph, const FString& EventName);

    // Property utilities
    static bool SetObjectProperty(UObject* Object, const FString& PropertyName,
                                 const TSharedPtr<FJsonValue>& Value, FString& OutErrorMessage);

    /**
     * SEH-wrapped variant of SetObjectProperty.
     *
     * Why this exists in a separate function:
     *   MSVC does not allow __try/__except in the same function as a C++
     *   try/catch (compiler error C2712). HandleSetComponentProperty has a
     *   try/catch for std::exception, so it cannot use __try directly.
     *   This wrapper isolates the SEH guard in its own stack frame.
     *
     * Why we need SEH here:
     *   FObjectProperty::SetPropertyValue on an SCS template, when the value
     *   is a freshly-imported asset (USoundWave / UNiagaraSystem / UStaticMesh),
     *   can call LoadObject internally; if the target asset is mid-async-load,
     *   the resulting TObjectPtr write hits a torn pointer and AVs.
     *
     * @param Object         Component template / UObject to mutate.
     * @param PropertyName   FName of the property to set.
     * @param Value          JSON payload (numbers, strings, arrays, etc.).
     * @param OutErrorMessage Error string on logical failure.
     * @param OutSehCrash    True if MSVC SEH caught an AV in the property write.
     * @return true on logical success, false on logical failure or SEH crash.
     */
    static bool SetObjectPropertyGuarded(UObject* Object, const FString& PropertyName,
                                         const TSharedPtr<FJsonValue>& Value,
                                         FString& OutErrorMessage, bool& OutSehCrash);

    /**
     * SEH-wrapped variant of USimpleConstructionScript::AddNode.
     *
     * AddNode() calls PostEditChange() on the SCS internally; in pathological
     * cases this can synchronously walk dependent assets and AV. Wrapping
     * in SEH prevents an editor crash.
     *
     * @param SCS         The SCS to mutate.
     * @param NewNode     Node to add (must be valid).
     * @param OutSehCrash True if MSVC SEH caught an AV.
     * @return true on success, false if SCS/NewNode null or SEH caught a crash.
     */
    static bool SCSAddNodeGuarded(class USimpleConstructionScript* SCS,
                                  class USCS_Node* NewNode, bool& OutSehCrash);

    /**
     * Schedule a guarded FKismetEditorUtilities::CompileBlueprint on the next
     * GameThread tick.
     *
     * CRASH-007 root cause:
     *   Historically `compile_blueprint` was intentionally a no-op (it only
     *   called Modify+MarkPackageDirty) because inline CompileBlueprint would
     *   crash via the MassEntityEditor observer chain when invoked from the
     *   bridge's AsyncTask lambda. Side-effect: after SCS mutations the
     *   Blueprint's GeneratedClass/CDO were never regenerated, so the next
     *   manual Ctrl+Shift+S serialised a stale CDO that referenced freshly
     *   created UAudioComponent templates, AV'ing in CoreUObject post-save.
     *
     * Fix:
     *   - Defer the compile via FTSTicker so it runs in its own clean frame
     *     (NOT nested inside our AsyncTask lambda — that frame is what trips
     *     the MassEntityEditor observer in this project).
     *   - Wrap the compile in MCP_GUARDED_RUN so any residual AV is caught
     *     and the editor survives.
     *   - Pass SkipGarbageCollection | SkipSave to keep the call cheap and
     *     prevent it from triggering a save that would re-enter our chain.
     *
     * The caller's Python side does not block on the result; it should sleep
     * a few hundred ms before issuing dependent commands. In practice the
     * tick fires within < 50 ms.
     */
    static void SafeCompileBlueprintDeferred(UBlueprint* Blueprint);

    /**
     * Schedule a guarded UPackage::SavePackage on the next GameThread tick,
     * after first scheduling a deferred compile (so the CDO is regenerated
     * before serialisation).
     *
     * Why low-level SavePackage instead of UEditorAssetLibrary::SaveAsset or
     * UEditorLoadingAndSavingUtils::SavePackages:
     *   Both higher-level paths fire the editor's PreSave/PostSave delegate
     *   chain, which in this project hits the MassEntityEditor observer with
     *   stale state and AVs (CRASH-002 / CRASH-007 same root). UPackage::
     *   SavePackage on the BP package directly skips that chain.
     *
     * Sequence (each step on its own deferred tick):
     *   tick N+1: FKismetEditorUtilities::CompileBlueprint (guarded)
     *   tick N+2: UPackage::SavePackage (guarded), SetDirtyFlag(false) on success
     *
     * @param Blueprint   The Blueprint whose package should be persisted.
     * @return            Always true if scheduling succeeded; the actual save
     *                    result is logged but not surfaced (the bridge command
     *                    returns "scheduled"). Callers can poll the file's
     *                    mtime or re-issue the command with only_if_dirty=true
     *                    to confirm.
     */
    static bool SafeSaveBlueprintPackageDeferred(UBlueprint* Blueprint);

    /**
     * Push the editor's autosave timer back by the full autosave interval.
     *
     * CRASH-006 (autosave-mid-mutation): Unreal's periodic autosave can fire
     * on the GameThread in the middle of a bridge SCS-mutation chain (e.g.
     * between two consecutive set_component_property calls on the same BP).
     * The autosave then runs UPackage::SavePackage on a half-mutated BP and
     * AVs deep inside CoreUObject during serialize / finalize.
     *
     * Calling ResetAutoSaveTimer() at the top of every bridge command means
     * that as long as commands keep flowing faster than the autosave
     * interval (default 10 min), autosave can never fire during a script run.
     * It still fires normally during idle time — we never disable it
     * permanently.
     *
     * Safe to call from any thread; internally checks GUnrealEd / GIsEditor
     * and is a no-op when those are not ready (e.g. during early startup).
     */
    static void DeferAutoSave();
};
