#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "TripoWorkspaceSession.generated.h"

UENUM()
enum class ETripoWorkspaceMode : uint8
{
	TextTo3D UMETA(DisplayName = "Text to 3D"),
	MultiImageTo3D UMETA(DisplayName = "Multi Image to 3D"),
	TexturePaint UMETA(DisplayName = "Texture Paint")
};

UCLASS()
class UNREALMCPEDITOR_API UTripoWorkspaceSession : public UObject
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, Category = "Workspace")
	ETripoWorkspaceMode ActiveMode = ETripoWorkspaceMode::TextTo3D;

	UPROPERTY(EditAnywhere, Category = "Workspace")
	FString PreviewAssetPath = TEXT("/Game/Generated/SM_GeneratedAsset");

	UPROPERTY(EditAnywhere, Category = "Workspace")
	FString OutputFolder = TEXT("/Game/Generated");

	UPROPERTY(EditAnywhere, Category = "Generation")
	FString Provider = TEXT("tripo");

	UPROPERTY(VisibleAnywhere, Category = "Generation")
	FString ApiKeySource = TEXT("missing");

	UPROPERTY(EditAnywhere, Category = "Generation")
	FString Prompt = TEXT("game-ready stylized prop, clean silhouette, PBR textures");

	UPROPERTY(EditAnywhere, Category = "Generation")
	FString ReferenceViews;

	UPROPERTY(EditAnywhere, Category = "Generation|Multi Image to 3D")
	FString FrontImage;

	UPROPERTY(EditAnywhere, Category = "Generation|Multi Image to 3D")
	FString LeftImage;

	UPROPERTY(EditAnywhere, Category = "Generation|Multi Image to 3D")
	FString BackImage;

	UPROPERTY(EditAnywhere, Category = "Generation|Multi Image to 3D")
	FString RightImage;

	UPROPERTY(EditAnywhere, Category = "Generation")
	FString TargetAssetName = TEXT("SM_GeneratedAsset");

	UPROPERTY(VisibleAnywhere, Category = "Generation")
	bool bSmartMeshEnabled = true;

	UPROPERTY(VisibleAnywhere, Category = "Generation")
	int32 FaceLimit = 12000;

	UPROPERTY(VisibleAnywhere, Category = "Generation")
	FString TopologyPolicy = TEXT("Smart Mesh locked on for Unreal game-ready topology");

	UPROPERTY(VisibleAnywhere, Category = "Generative Credits")
	int32 SessionCreditBudget = 0;

	UPROPERTY(VisibleAnywhere, Category = "Generative Credits")
	int32 PendingSpendCredits = 0;

	UPROPERTY(VisibleAnywhere, Category = "Generative Credits")
	bool bSpendConfirmed = false;

	UPROPERTY(VisibleAnywhere, Category = "Generative Credits")
	FString WalletStatus = TEXT("local settings only");

	UPROPERTY(VisibleAnywhere, Category = "Generative Credits")
	FString ApiWalletBalance = TEXT("unknown");

	UPROPERTY(VisibleAnywhere, Category = "Generative Credits")
	FString ApiWalletFrozen = TEXT("unknown");

	UPROPERTY(EditAnywhere, Category = "Texture Paint")
	FString ExistingModelTaskId;

	UPROPERTY(EditAnywhere, Category = "Texture Paint")
	FString TexturePrompt;

	UPROPERTY(EditAnywhere, Category = "Texture Paint")
	FString PaintViewLabel = TEXT("source_view");

	UPROPERTY(EditAnywhere, Category = "Texture Paint")
	float BrushStrength = 0.75f;

	UPROPERTY(EditAnywhere, Category = "Texture Paint")
	float BlendAmount = 0.5f;

	UPROPERTY(EditAnywhere, Category = "Texture Paint")
	float BrushRadius = 0.2f;

	UPROPERTY(EditAnywhere, Category = "Texture Paint")
	bool bUploadPaintSnapshot = false;
};
