#include "Commands/UnrealMCPGeometryCommands.h"

#include "Commands/UnrealMCPCommonUtils.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMeshActor.h"
#include "Editor.h"
#include "EditorAssetLibrary.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GeometryScript/CreateNewAssetUtilityFunctions.h"
#include "GeometryScript/GeometryScriptTypes.h"
#include "GeometryScript/MeshBooleanFunctions.h"
#include "GeometryScript/MeshDeformFunctions.h"
#include "GeometryScript/MeshModelingFunctions.h"
#include "GeometryScript/MeshPrimitiveFunctions.h"
#include "GeometryScript/MeshQueryFunctions.h"
#include "GeometryScript/MeshRemeshFunctions.h"
#include "GeometryScript/MeshSelectionFunctions.h"
#include "GeometryScript/MeshUVFunctions.h"
#include "ScopedTransaction.h"

FUnrealMCPGeometryCommands::FUnrealMCPGeometryCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPGeometryCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("geom_create_dynamic_mesh")) return HandleCreateDynamicMesh(Params);
    if (CommandType == TEXT("geom_boolean_op")) return HandleBooleanOp(Params);
    if (CommandType == TEXT("geom_extrude")) return HandleExtrude(Params);
    if (CommandType == TEXT("geom_remesh")) return HandleRemesh(Params);
    if (CommandType == TEXT("geom_uv_unwrap")) return HandleUVUnwrap(Params);
    if (CommandType == TEXT("geom_bake_to_static_mesh")) return HandleBakeToStaticMesh(Params);
    if (CommandType == TEXT("geom_apply_displacement")) return HandleApplyDisplacement(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown geometry command: %s"), *CommandType));
}

UWorld* FUnrealMCPGeometryCommands::GetEditorWorld() const
{
    return GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
}

ADynamicMeshActor* FUnrealMCPGeometryCommands::FindDynamicMeshActor(const FString& ActorName) const
{
    if (ActorName.IsEmpty())
    {
        return nullptr;
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return nullptr;
    }

    for (TActorIterator<ADynamicMeshActor> It(World); It; ++It)
    {
        ADynamicMeshActor* Actor = *It;
        if (Actor && (Actor->GetActorLabel() == ActorName || Actor->GetName() == ActorName))
        {
            return Actor;
        }
    }
    return nullptr;
}

UDynamicMesh* FUnrealMCPGeometryCommands::GetDynamicMesh(const FString& ActorName, ADynamicMeshActor** OutActor) const
{
    ADynamicMeshActor* Actor = FindDynamicMeshActor(ActorName);
    if (OutActor)
    {
        *OutActor = Actor;
    }
    if (!Actor || !Actor->GetDynamicMeshComponent())
    {
        return nullptr;
    }
    return Actor->GetDynamicMeshComponent()->GetDynamicMesh();
}

FVector FUnrealMCPGeometryCommands::GetVectorField(
    const TSharedPtr<FJsonObject>& Params,
    const TCHAR* FieldName,
    const FVector& DefaultValue) const
{
    if (Params.IsValid() && Params->HasField(FieldName))
    {
        return FUnrealMCPCommonUtils::GetVectorFromJson(Params, FieldName);
    }
    return DefaultValue;
}

TSharedPtr<FJsonObject> FUnrealMCPGeometryCommands::MakeMeshResult(
    const FString& StageName,
    ADynamicMeshActor* Actor,
    UDynamicMesh* Mesh) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), Actor != nullptr && Mesh != nullptr);
    Result->SetStringField(TEXT("stage"), StageName);
    if (Actor)
    {
        Result->SetStringField(TEXT("actor_name"), Actor->GetActorLabel());
        Result->SetStringField(TEXT("actor_path"), Actor->GetPathName());
        const FVector Location = Actor->GetActorLocation();
        Result->SetStringField(TEXT("location"), Location.ToString());
    }
    if (Mesh)
    {
        Result->SetNumberField(TEXT("triangle_count"), Mesh->GetTriangleCount());
        Result->SetNumberField(TEXT("vertex_count"), UGeometryScriptLibrary_MeshQueryFunctions::GetVertexCount(Mesh));
        Result->SetStringField(TEXT("mesh_info"), UGeometryScriptLibrary_MeshQueryFunctions::GetMeshInfoString(Mesh));
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPGeometryCommands::HandleCreateDynamicMesh(const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FString ActorName = TEXT("DM_GeneratedMesh");
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    if (ActorName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));
    }

    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    if (ADynamicMeshActor* ExistingActor = FindDynamicMeshActor(ActorName))
    {
        if (!bOverwrite)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("DynamicMesh actor already exists: %s"), *ActorName));
        }
        ExistingActor->Destroy();
    }

    FString Primitive = TEXT("box");
    Params->TryGetStringField(TEXT("primitive"), Primitive);
    Primitive = Primitive.ToLower();

    const FVector Dimensions = GetVectorField(Params, TEXT("dimensions"), FVector(100.0, 100.0, 100.0));
    const FVector Location = GetVectorField(Params, TEXT("location"), FVector::ZeroVector);
    const FRotator Rotation = Params->HasField(TEXT("rotation"))
        ? FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation"))
        : FRotator::ZeroRotator;

    int32 RadialSteps = 16;
    Params->TryGetNumberField(TEXT("radial_steps"), RadialSteps);
    int32 HeightSteps = 0;
    Params->TryGetNumberField(TEXT("height_steps"), HeightSteps);

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Create Dynamic Mesh")));
    ADynamicMeshActor* Actor = World->SpawnActor<ADynamicMeshActor>(Location, Rotation);
    if (!Actor || !Actor->GetDynamicMeshComponent())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn DynamicMesh actor"));
    }
    Actor->SetActorLabel(ActorName);

    UDynamicMesh* Mesh = Actor->GetDynamicMeshComponent()->GetDynamicMesh();
    if (!Mesh)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("DynamicMesh actor has no UDynamicMesh"));
    }
    Mesh->Reset();

    FGeometryScriptPrimitiveOptions PrimitiveOptions;
    PrimitiveOptions.UVMode = EGeometryScriptPrimitiveUVMode::Uniform;
    const FTransform MeshTransform = FTransform::Identity;
    const int32 SafeRadialSteps = FMath::Max(3, RadialSteps);
    const int32 SafeHeightSteps = FMath::Max(0, HeightSteps);

    if (Primitive == TEXT("empty"))
    {
        // Leave the mesh empty for workflows that append or copy geometry later.
    }
    else if (Primitive == TEXT("sphere"))
    {
        UGeometryScriptLibrary_MeshPrimitiveFunctions::AppendSphereLatLong(
            Mesh, PrimitiveOptions, MeshTransform, FMath::Max(1.0, Dimensions.X), FMath::Max(3, SafeRadialSteps / 2), SafeRadialSteps);
    }
    else if (Primitive == TEXT("cylinder"))
    {
        UGeometryScriptLibrary_MeshPrimitiveFunctions::AppendCylinder(
            Mesh, PrimitiveOptions, MeshTransform, FMath::Max(1.0, Dimensions.X), FMath::Max(1.0, Dimensions.Z), SafeRadialSteps, SafeHeightSteps);
    }
    else if (Primitive == TEXT("plane") || Primitive == TEXT("rectangle"))
    {
        UGeometryScriptLibrary_MeshPrimitiveFunctions::AppendRectangleXY(
            Mesh, PrimitiveOptions, MeshTransform, FMath::Max(1.0, Dimensions.X), FMath::Max(1.0, Dimensions.Y), FMath::Max(0, SafeHeightSteps), FMath::Max(0, SafeHeightSteps));
    }
    else
    {
        UGeometryScriptLibrary_MeshPrimitiveFunctions::AppendBox(
            Mesh, PrimitiveOptions, MeshTransform, FMath::Max(1.0, Dimensions.X), FMath::Max(1.0, Dimensions.Y), FMath::Max(1.0, Dimensions.Z), SafeHeightSteps, SafeHeightSteps, SafeHeightSteps);
        Primitive = TEXT("box");
    }

    Actor->GetDynamicMeshComponent()->NotifyMeshUpdated();
    TSharedPtr<FJsonObject> Result = MakeMeshResult(TEXT("geom_create_dynamic_mesh"), Actor, Mesh);
    Result->SetStringField(TEXT("primitive"), Primitive);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPGeometryCommands::HandleBooleanOp(const TSharedPtr<FJsonObject>& Params)
{
    FString TargetName;
    FString ToolName;
    Params->TryGetStringField(TEXT("target_actor"), TargetName);
    Params->TryGetStringField(TEXT("tool_actor"), ToolName);
    if (TargetName.IsEmpty() || ToolName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'target_actor' or 'tool_actor' parameter"));
    }

    ADynamicMeshActor* TargetActor = nullptr;
    ADynamicMeshActor* ToolActor = nullptr;
    UDynamicMesh* TargetMesh = GetDynamicMesh(TargetName, &TargetActor);
    UDynamicMesh* ToolMesh = GetDynamicMesh(ToolName, &ToolActor);
    if (!TargetMesh || !ToolMesh || !TargetActor || !ToolActor)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Both target_actor and tool_actor must be DynamicMesh actors"));
    }

    FString OperationName = TEXT("subtract");
    Params->TryGetStringField(TEXT("operation"), OperationName);
    OperationName = OperationName.ToLower();
    EGeometryScriptBooleanOperation Operation = EGeometryScriptBooleanOperation::Subtract;
    if (OperationName == TEXT("union")) Operation = EGeometryScriptBooleanOperation::Union;
    else if (OperationName == TEXT("intersection") || OperationName == TEXT("intersect")) Operation = EGeometryScriptBooleanOperation::Intersection;
    else if (OperationName == TEXT("trim_inside")) Operation = EGeometryScriptBooleanOperation::TrimInside;
    else if (OperationName == TEXT("trim_outside")) Operation = EGeometryScriptBooleanOperation::TrimOutside;

    FGeometryScriptMeshBooleanOptions Options;
    Params->TryGetBoolField(TEXT("fill_holes"), Options.bFillHoles);
    Params->TryGetBoolField(TEXT("simplify_output"), Options.bSimplifyOutput);
    FString OutputSpace = TEXT("target");
    Params->TryGetStringField(TEXT("output_space"), OutputSpace);
    OutputSpace = OutputSpace.ToLower();
    if (OutputSpace == TEXT("tool"))
    {
        Options.OutputTransformSpace = EGeometryScriptBooleanOutputSpace::ToolTransformSpace;
    }
    else if (OutputSpace == TEXT("shared"))
    {
        Options.OutputTransformSpace = EGeometryScriptBooleanOutputSpace::SharedTransformSpace;
    }

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Geometry Boolean")));
    UGeometryScriptLibrary_MeshBooleanFunctions::ApplyMeshBoolean(
        TargetMesh,
        TargetActor->GetActorTransform(),
        ToolMesh,
        ToolActor->GetActorTransform(),
        Operation,
        Options);

    bool bHideTool = false;
    Params->TryGetBoolField(TEXT("hide_tool"), bHideTool);
    if (bHideTool)
    {
        ToolActor->SetActorHiddenInGame(true);
        ToolActor->SetIsTemporarilyHiddenInEditor(true);
    }

    TargetActor->GetDynamicMeshComponent()->NotifyMeshUpdated();
    TSharedPtr<FJsonObject> Result = MakeMeshResult(TEXT("geom_boolean_op"), TargetActor, TargetMesh);
    Result->SetStringField(TEXT("operation"), OperationName);
    Result->SetStringField(TEXT("tool_actor"), ToolActor->GetActorLabel());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPGeometryCommands::HandleExtrude(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    ADynamicMeshActor* Actor = nullptr;
    UDynamicMesh* Mesh = GetDynamicMesh(ActorName, &Actor);
    if (!Actor || !Mesh)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'actor_name' must reference a DynamicMesh actor"));
    }

    FGeometryScriptMeshLinearExtrudeOptions Options;
    Params->TryGetNumberField(TEXT("distance"), Options.Distance);
    Options.Direction = GetVectorField(Params, TEXT("direction"), FVector(0, 0, 1));
    FString DirectionMode = TEXT("fixed");
    Params->TryGetStringField(TEXT("direction_mode"), DirectionMode);
    DirectionMode = DirectionMode.ToLower();
    if (DirectionMode == TEXT("average_face_normal") || DirectionMode == TEXT("normal"))
    {
        Options.DirectionMode = EGeometryScriptLinearExtrudeDirection::AverageFaceNormal;
    }
    FString AreaMode = TEXT("entire_selection");
    Params->TryGetStringField(TEXT("area_mode"), AreaMode);
    AreaMode = AreaMode.ToLower();
    if (AreaMode == TEXT("per_polygroup"))
    {
        Options.AreaMode = EGeometryScriptPolyOperationArea::PerPolygroup;
    }
    else if (AreaMode == TEXT("per_triangle"))
    {
        Options.AreaMode = EGeometryScriptPolyOperationArea::PerTriangle;
    }
    Params->TryGetNumberField(TEXT("uv_scale"), Options.UVScale);
    Params->TryGetBoolField(TEXT("solids_to_shells"), Options.bSolidsToShells);

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Geometry Extrude")));
    FGeometryScriptMeshSelection Selection;
    UGeometryScriptLibrary_MeshSelectionFunctions::CreateSelectAllMeshSelection(
        Mesh,
        Selection,
        EGeometryScriptMeshSelectionType::Triangles);
    UGeometryScriptLibrary_MeshModelingFunctions::ApplyMeshLinearExtrudeFaces(Mesh, Options, Selection);
    Actor->GetDynamicMeshComponent()->NotifyMeshUpdated();

    TSharedPtr<FJsonObject> Result = MakeMeshResult(TEXT("geom_extrude"), Actor, Mesh);
    Result->SetNumberField(TEXT("distance"), Options.Distance);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPGeometryCommands::HandleRemesh(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    ADynamicMeshActor* Actor = nullptr;
    UDynamicMesh* Mesh = GetDynamicMesh(ActorName, &Actor);
    if (!Actor || !Mesh)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'actor_name' must reference a DynamicMesh actor"));
    }

    FGeometryScriptRemeshOptions RemeshOptions;
    Params->TryGetBoolField(TEXT("discard_attributes"), RemeshOptions.bDiscardAttributes);
    Params->TryGetBoolField(TEXT("reproject"), RemeshOptions.bReprojectToInputMesh);
    Params->TryGetNumberField(TEXT("iterations"), RemeshOptions.RemeshIterations);

    FGeometryScriptUniformRemeshOptions UniformOptions;
    Params->TryGetNumberField(TEXT("target_triangle_count"), UniformOptions.TargetTriangleCount);
    double TargetEdgeLength = 0.0;
    Params->TryGetNumberField(TEXT("target_edge_length"), TargetEdgeLength);
    if (TargetEdgeLength > 0.0)
    {
        UniformOptions.TargetType = EGeometryScriptUniformRemeshTargetType::TargetEdgeLength;
        UniformOptions.TargetEdgeLength = static_cast<float>(TargetEdgeLength);
    }

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Geometry Remesh")));
    UGeometryScriptLibrary_RemeshingFunctions::ApplyUniformRemesh(Mesh, RemeshOptions, UniformOptions);
    Actor->GetDynamicMeshComponent()->NotifyMeshUpdated();

    TSharedPtr<FJsonObject> Result = MakeMeshResult(TEXT("geom_remesh"), Actor, Mesh);
    Result->SetNumberField(TEXT("target_triangle_count"), UniformOptions.TargetTriangleCount);
    Result->SetNumberField(TEXT("target_edge_length"), UniformOptions.TargetEdgeLength);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPGeometryCommands::HandleUVUnwrap(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    ADynamicMeshActor* Actor = nullptr;
    UDynamicMesh* Mesh = GetDynamicMesh(ActorName, &Actor);
    if (!Actor || !Mesh)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'actor_name' must reference a DynamicMesh actor"));
    }

    int32 UVChannel = 0;
    Params->TryGetNumberField(TEXT("uv_channel"), UVChannel);
    FString Method = TEXT("xatlas");
    Params->TryGetStringField(TEXT("method"), Method);
    Method = Method.ToLower();

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Geometry UV Unwrap")));
    if (Method == TEXT("patch_builder"))
    {
        FGeometryScriptPatchBuilderOptions Options;
        Params->TryGetBoolField(TEXT("auto_pack"), Options.bAutoPack);
        UGeometryScriptLibrary_MeshUVFunctions::AutoGeneratePatchBuilderMeshUVs(Mesh, UVChannel, Options);
    }
    else if (Method == TEXT("recompute"))
    {
        FGeometryScriptRecomputeUVsOptions Options;
        FGeometryScriptMeshSelection EmptySelection;
        UGeometryScriptLibrary_MeshUVFunctions::RecomputeMeshUVs(Mesh, UVChannel, Options, EmptySelection);
    }
    else if (Method == TEXT("layout"))
    {
        FGeometryScriptLayoutUVsOptions Options;
        Params->TryGetNumberField(TEXT("texture_resolution"), Options.TextureResolution);
        FGeometryScriptMeshSelection EmptySelection;
        UGeometryScriptLibrary_MeshUVFunctions::LayoutMeshUVs(Mesh, UVChannel, Options, EmptySelection);
    }
    else
    {
        FGeometryScriptXAtlasOptions Options;
        Params->TryGetNumberField(TEXT("max_iterations"), Options.MaxIterations);
        UGeometryScriptLibrary_MeshUVFunctions::AutoGenerateXAtlasMeshUVs(Mesh, UVChannel, Options);
        Method = TEXT("xatlas");
    }

    Actor->GetDynamicMeshComponent()->NotifyMeshUpdated();
    TSharedPtr<FJsonObject> Result = MakeMeshResult(TEXT("geom_uv_unwrap"), Actor, Mesh);
    Result->SetNumberField(TEXT("uv_channel"), UVChannel);
    Result->SetStringField(TEXT("method"), Method);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPGeometryCommands::HandleBakeToStaticMesh(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    ADynamicMeshActor* Actor = nullptr;
    UDynamicMesh* Mesh = GetDynamicMesh(ActorName, &Actor);
    if (!Actor || !Mesh)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'actor_name' must reference a DynamicMesh actor"));
    }

    FString AssetPath = TEXT("/Game/Geometry/SM_BakedDynamicMesh");
    Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    if (AssetPath.Contains(TEXT(".")))
    {
        AssetPath.LeftInline(AssetPath.Find(TEXT(".")));
    }
    if (!AssetPath.StartsWith(TEXT("/Game/")))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("asset_path must be under /Game"));
    }

    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    const FString ObjectPath = FString::Printf(TEXT("%s.%s"), *AssetPath, *FPaths::GetBaseFilename(AssetPath));
    if (UEditorAssetLibrary::DoesAssetExist(ObjectPath))
    {
        if (!bOverwrite)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Asset already exists: %s"), *ObjectPath));
        }
        UEditorAssetLibrary::DeleteAsset(ObjectPath);
    }

    int32 LastSlash = INDEX_NONE;
    if (AssetPath.FindLastChar(TEXT('/'), LastSlash))
    {
        UEditorAssetLibrary::MakeDirectory(AssetPath.Left(LastSlash));
    }

    FGeometryScriptCreateNewStaticMeshAssetOptions Options;
    Params->TryGetBoolField(TEXT("enable_nanite"), Options.bEnableNanite);
    Params->TryGetBoolField(TEXT("enable_collision"), Options.bEnableCollision);
    Params->TryGetBoolField(TEXT("recompute_normals"), Options.bEnableRecomputeNormals);
    Params->TryGetBoolField(TEXT("recompute_tangents"), Options.bEnableRecomputeTangents);

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Bake Dynamic Mesh")));
    EGeometryScriptOutcomePins Outcome = EGeometryScriptOutcomePins::Failure;
    UStaticMesh* StaticMesh = UGeometryScriptLibrary_CreateNewAssetFunctions::CreateNewStaticMeshAssetFromMesh(
        Mesh,
        AssetPath,
        Options,
        Outcome);
    if (!StaticMesh || Outcome != EGeometryScriptOutcomePins::Success)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Failed to create StaticMesh asset: %s"), *AssetPath));
    }

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(ObjectPath, false);
    }

    TSharedPtr<FJsonObject> Result = MakeMeshResult(TEXT("geom_bake_to_static_mesh"), Actor, Mesh);
    Result->SetStringField(TEXT("asset_path"), AssetPath);
    Result->SetStringField(TEXT("object_path"), ObjectPath);
    Result->SetStringField(TEXT("asset_class"), StaticMesh->GetClass()->GetPathName());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPGeometryCommands::HandleApplyDisplacement(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    ADynamicMeshActor* Actor = nullptr;
    UDynamicMesh* Mesh = GetDynamicMesh(ActorName, &Actor);
    if (!Actor || !Mesh)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'actor_name' must reference a DynamicMesh actor"));
    }

    FGeometryScriptPerlinNoiseOptions Options;
    Params->TryGetNumberField(TEXT("magnitude"), Options.BaseLayer.Magnitude);
    Params->TryGetNumberField(TEXT("frequency"), Options.BaseLayer.Frequency);
    Params->TryGetNumberField(TEXT("seed"), Options.BaseLayer.RandomSeed);
    Params->TryGetBoolField(TEXT("along_normal"), Options.bApplyAlongNormal);
    Options.EmptyBehavior = EGeometryScriptEmptySelectionBehavior::FullMeshSelection;

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Geometry Displacement")));
    FGeometryScriptMeshSelection EmptySelection;
    UGeometryScriptLibrary_MeshDeformFunctions::ApplyPerlinNoiseToMesh(Mesh, EmptySelection, Options);
    Actor->GetDynamicMeshComponent()->NotifyMeshUpdated();

    TSharedPtr<FJsonObject> Result = MakeMeshResult(TEXT("geom_apply_displacement"), Actor, Mesh);
    Result->SetNumberField(TEXT("magnitude"), Options.BaseLayer.Magnitude);
    Result->SetNumberField(TEXT("frequency"), Options.BaseLayer.Frequency);
    return Result;
}
