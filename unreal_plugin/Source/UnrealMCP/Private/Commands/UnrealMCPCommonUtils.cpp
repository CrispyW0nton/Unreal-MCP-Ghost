#include "Commands/UnrealMCPCommonUtils.h"
#include "GameFramework/Actor.h"
#include "Engine/Blueprint.h"
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

    // FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified dereferences
    // Blueprint->GeneratedClass to invalidate the property chain. For
    // newly-created or first-session-access Blueprints, GeneratedClass may be
    // null → EXCEPTION_ACCESS_VIOLATION (manifests as EdGraphNode.h:586
    // assertion or WinError 10053 on Python side).
    if (Blueprint->GeneratedClass && IsValid(Blueprint->GeneratedClass))
    {
        FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    }
    else
    {
        // Safe fallback: mark the UObject dirty for Undo/save without touching
        // GeneratedClass. The editor compiles and regenerates the class on next save.
        Blueprint->Modify();
        UE_LOG(LogTemp, Warning,
            TEXT("[MCP] SafeMarkBlueprintModified: GeneratedClass null for '%s' — using Modify() fallback"),
            *Blueprint->GetName());
    }
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
    auto TryCachedPath = [&](const FString& Path) -> UBlueprint*
    {
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

    if (UBlueprint* BP = TryCachedPath(TEXT("/Game/Blueprints/") + BlueprintName)) return BP;
    if (UBlueprint* BP = TryCachedPath(TEXT("/Game/") + BlueprintName))           return BP;

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
    AR.GetAssetsByClass(UBlueprint::StaticClass()->GetClassPathName(), BlueprintAssets, /*bSearchSubClasses=*/true);

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
    Graph->AddNode(FunctionNode, true);
    FunctionNode->PostPlacedNewNode();
    FunctionNode->AllocateDefaultPins();
    
    return FunctionNode;
}

UK2Node_VariableGet* FUnrealMCPCommonUtils::CreateVariableGetNode(UEdGraph* Graph, UBlueprint* Blueprint, const FString& VariableName, const FVector2D& Position)
{
    if (!Graph || !Blueprint)
    {
        return nullptr;
    }
    
    UK2Node_VariableGet* VariableGetNode = NewObject<UK2Node_VariableGet>(Graph);
    VariableGetNode->VariableReference.SetSelfMember(FName(*VariableName));
    VariableGetNode->NodePosX = Position.X;
    VariableGetNode->NodePosY = Position.Y;
    VariableGetNode->CreateNewGuid();
    Graph->AddNode(VariableGetNode, true);
    VariableGetNode->PostPlacedNewNode();
    VariableGetNode->AllocateDefaultPins();
    
    return VariableGetNode;
}

UK2Node_VariableSet* FUnrealMCPCommonUtils::CreateVariableSetNode(UEdGraph* Graph, UBlueprint* Blueprint, const FString& VariableName, const FVector2D& Position)
{
    if (!Graph || !Blueprint)
    {
        return nullptr;
    }
    
    UK2Node_VariableSet* VariableSetNode = NewObject<UK2Node_VariableSet>(Graph);
    VariableSetNode->VariableReference.SetSelfMember(FName(*VariableName));
    VariableSetNode->NodePosX = Position.X;
    VariableSetNode->NodePosY = Position.Y;
    VariableSetNode->CreateNewGuid();
    Graph->AddNode(VariableSetNode, true);
    VariableSetNode->PostPlacedNewNode();
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
    {
        return nullptr;
    }
    
    UK2Node_Self* SelfNode = NewObject<UK2Node_Self>(Graph);
    SelfNode->NodePosX = Position.X;
    SelfNode->NodePosY = Position.Y;
    SelfNode->CreateNewGuid();
    Graph->AddNode(SelfNode, true);
    SelfNode->PostPlacedNewNode();
    SelfNode->AllocateDefaultPins();
    
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
                FSoftObjectPtr SoftPtr(FoundClass);
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