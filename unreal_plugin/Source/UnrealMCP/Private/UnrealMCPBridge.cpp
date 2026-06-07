#include "UnrealMCPBridge.h"
#include "MCPServerRunnable.h"
#include "TimerManager.h"
#include "Editor.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "HAL/RunnableThread.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Interfaces/IPv4/IPv4Endpoint.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonWriter.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Camera/CameraActor.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/AssetData.h"
#include "JsonObjectConverter.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "AIController.h"
#include "NavigationSystem.h"
#include "Navigation/PathFollowingComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CapsuleComponent.h"
#include "Components/AudioComponent.h"
#include "Components/ProgressBar.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextBlock.h"
#include "Components/WidgetComponent.h"
#include "Engine/Selection.h"
#include "EngineUtils.h"
#include "DrawDebugHelpers.h"
#include "Kismet/GameplayStatics.h"
PRAGMA_DISABLE_DEPRECATION_WARNINGS
#include "Perception/PawnSensingComponent.h"
PRAGMA_ENABLE_DEPRECATION_WARNINGS
#include "Async/Async.h"
// Add Blueprint related includes
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Factories/BlueprintFactory.h"
#include "EdGraphSchema_K2.h"
#include "K2Node_Event.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/SphereComponent.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
// UE5.5 correct includes
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "UObject/Field.h"
#include "UObject/FieldPath.h"
// Blueprint Graph specific includes
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "K2Node_CallFunction.h"
#include "K2Node_InputAction.h"
#include "K2Node_Self.h"
#include "GameFramework/InputSettings.h"
#include "EditorSubsystem.h"
#include "Subsystems/EditorActorSubsystem.h"
// Include our new command handler classes
#include "Commands/UnrealMCPEditorCommands.h"
#include "Commands/UnrealMCPBlueprintCommands.h"
#include "Commands/UnrealMCPBlueprintNodeCommands.h"
#include "Commands/UnrealMCPProjectCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "Commands/UnrealMCPUMGCommands.h"
#include "Commands/UnrealMCPExtendedCommands.h"
#include "Commands/UnrealMCPGASCommands.h"
#include "Commands/UnrealMCPNetworkCommands.h"
#include "Commands/UnrealMCPAudioCommands.h"
#include "Commands/UnrealMCPChaosCommands.h"
#include "Commands/UnrealMCPMRQCommands.h"
#include "Commands/UnrealMCPOnlineCommands.h"
#include "Commands/UnrealMCPPixelStreamingCommands.h"
#include "Commands/UnrealMCPGeometryCommands.h"
#include "Commands/UnrealMCPMassCommands.h"
#include "Commands/UnrealMCPMotionCommands.h"
#include "HAL/PlatformTime.h"
#include "UnrealMCPModule.h"

// Default settings
#define MCP_SERVER_HOST "127.0.0.1"
#define MCP_SERVER_PORT 55655

namespace
{
    constexpr bool bEnableNativeSithCombatDirector = true;
    constexpr bool bEnableNativeSithRepositioning = true;

    UWorld* FindSithDirectorWorld()
    {
        if (!GEngine)
        {
            return nullptr;
        }

        for (const FWorldContext& Context : GEngine->GetWorldContexts())
        {
            if ((Context.WorldType == EWorldType::PIE || Context.WorldType == EWorldType::Game) && Context.World())
            {
                return Context.World();
            }
        }
        return nullptr;
    }

    bool IsSithTrooperActor(const AActor* Actor)
    {
        return Actor
            && Actor->GetClass()
            && Actor->GetClass()->GetPathName().Contains(TEXT("/Game/EndarSpire/AI/SithV2/BP_SithTrooper."));
    }

    bool IsHeavySithTrooperActor(const AActor* Actor)
    {
        return Actor
            && Actor->GetClass()
            && Actor->GetClass()->GetPathName().Contains(TEXT("/Game/EndarSpire/AI/SithV2/BP_SithHeavyTrooper."));
    }

    bool IsRepublicSoldierActor(const AActor* Actor)
    {
        if (!Actor || !Actor->GetClass())
        {
            return false;
        }

        const FString ClassPath = Actor->GetClass()->GetPathName();
        return ClassPath.Contains(TEXT("/Game/EndarSpire/AI/RepublicV1/BP_RepublicSoldier."))
            || ClassPath.Contains(TEXT("/Game/EndarSpire/AI/RepublicV1/Blueprints/BP_RepublicSoldier."))
            || ClassPath.Contains(TEXT("/Game/EndarSpire/Characters/Friendly/BP_RepublicSoldier."));
    }

    bool IsDarkJediBossActor(const AActor* Actor)
    {
        if (!Actor || !Actor->GetClass())
        {
            return false;
        }

        const FString ClassPath = Actor->GetClass()->GetPathName();
        return ClassPath.Contains(TEXT("/Game/EndarSpire/AI/SithV2/BP_DarkJediBoss."))
            || Actor->GetClass()->GetName().Contains(TEXT("BP_DarkJediBoss_C"));
    }

    bool IsNativeInfantryCombatActor(const AActor* Actor)
    {
        return IsSithTrooperActor(Actor) || IsHeavySithTrooperActor(Actor) || IsRepublicSoldierActor(Actor);
    }

    bool GetBoolProperty(UObject* Object, const FName PropertyName, const bool DefaultValue = false)
    {
        if (!Object)
        {
            return DefaultValue;
        }

        if (const FBoolProperty* Prop = FindFProperty<FBoolProperty>(Object->GetClass(), PropertyName))
        {
            return Prop->GetPropertyValue_InContainer(Object);
        }
        return DefaultValue;
    }

    void SetBoolProperty(UObject* Object, const FName PropertyName, const bool Value)
    {
        if (Object)
        {
            if (const FBoolProperty* Prop = FindFProperty<FBoolProperty>(Object->GetClass(), PropertyName))
            {
                Prop->SetPropertyValue_InContainer(Object, Value);
            }
        }
    }

    void SetRealProperty(UObject* Object, const FName PropertyName, const float Value)
    {
        if (!Object)
        {
            return;
        }

        if (const FFloatProperty* FloatProp = FindFProperty<FFloatProperty>(Object->GetClass(), PropertyName))
        {
            FloatProp->SetPropertyValue_InContainer(Object, Value);
            return;
        }

        if (const FDoubleProperty* DoubleProp = FindFProperty<FDoubleProperty>(Object->GetClass(), PropertyName))
        {
            DoubleProp->SetPropertyValue_InContainer(Object, static_cast<double>(Value));
        }
    }

    float GetRealProperty(UObject* Object, const FName PropertyName, const float DefaultValue)
    {
        if (!Object)
        {
            return DefaultValue;
        }

        if (const FFloatProperty* FloatProp = FindFProperty<FFloatProperty>(Object->GetClass(), PropertyName))
        {
            return FloatProp->GetPropertyValue_InContainer(Object);
        }

        if (const FDoubleProperty* DoubleProp = FindFProperty<FDoubleProperty>(Object->GetClass(), PropertyName))
        {
            return static_cast<float>(DoubleProp->GetPropertyValue_InContainer(Object));
        }

        return DefaultValue;
    }

    void SetIntProperty(UObject* Object, const FName PropertyName, const int32 Value)
    {
        if (Object)
        {
            if (const FIntProperty* Prop = FindFProperty<FIntProperty>(Object->GetClass(), PropertyName))
            {
                Prop->SetPropertyValue_InContainer(Object, Value);
            }
        }
    }

    int32 GetIntProperty(UObject* Object, const FName PropertyName, const int32 DefaultValue)
    {
        if (Object)
        {
            if (const FIntProperty* Prop = FindFProperty<FIntProperty>(Object->GetClass(), PropertyName))
            {
                return Prop->GetPropertyValue_InContainer(Object);
            }
        }
        return DefaultValue;
    }

    void TriggerDarkJediPlayerDeath(AActor* TargetActor)
    {
        if (!TargetActor)
        {
            return;
        }

        SetBoolProperty(TargetActor, TEXT("IsDead"), true);
        SetBoolProperty(TargetActor, TEXT("isDead"), true);
        SetBoolProperty(TargetActor, TEXT("Dead"), true);
        SetBoolProperty(TargetActor, TEXT("bIsDead"), true);

        const FName DeathEventNames[] =
        {
            TEXT("Die"),
            TEXT("Death"),
            TEXT("PlayerDeath"),
            TEXT("PlayerDead"),
            TEXT("HandleDeath"),
            TEXT("OnDeath"),
            TEXT("KillPlayer"),
            TEXT("DeathEvent")
        };

        bool bCalledDeathEvent = false;
        for (const FName DeathEventName : DeathEventNames)
        {
            UFunction* DeathFunction = TargetActor->FindFunction(DeathEventName);
            if (DeathFunction && DeathFunction->NumParms == 0)
            {
                TargetActor->ProcessEvent(DeathFunction, nullptr);
                bCalledDeathEvent = true;
            }
        }

        if (!bCalledDeathEvent)
        {
            UE_LOG(LogMCP, Warning, TEXT("DarkJediBossDirector: Player HP reached zero, but no no-arg death event was found on %s."), *TargetActor->GetName());
        }
    }

    void ApplyDarkJediDamageToPlayer(AActor* TargetActor, const float DamageAmount)
    {
        if (!TargetActor || DamageAmount <= 0.0f)
        {
            return;
        }

        int32 RemainingDamage = FMath::Max(1, FMath::RoundToInt(DamageAmount));
        const bool bHasOvershield = GetBoolProperty(TargetActor, TEXT("HasOvershield?"));
        int32 Overshield = GetIntProperty(TargetActor, TEXT("Overshield"), 0);
        if (bHasOvershield && Overshield > 0)
        {
            const int32 AbsorbedDamage = FMath::Min(Overshield, RemainingDamage);
            Overshield -= AbsorbedDamage;
            RemainingDamage -= AbsorbedDamage;
            SetIntProperty(TargetActor, TEXT("Overshield"), Overshield);
            if (Overshield <= 0)
            {
                SetBoolProperty(TargetActor, TEXT("HasOvershield?"), false);
            }
        }

        if (RemainingDamage > 0)
        {
            const int32 CurrentHP = GetIntProperty(TargetActor, TEXT("HP"), 0);
            const int32 NewHP = FMath::Max(0, CurrentHP - RemainingDamage);
            SetIntProperty(TargetActor, TEXT("HP"), NewHP);
            if (NewHP <= 0)
            {
                TriggerDarkJediPlayerDeath(TargetActor);
            }
        }
    }

    void SetObjectProperty(UObject* Object, const FName PropertyName, UObject* Value)
    {
        if (Object)
        {
            if (const FObjectPropertyBase* Prop = FindFProperty<FObjectPropertyBase>(Object->GetClass(), PropertyName))
            {
                Prop->SetObjectPropertyValue_InContainer(Object, Value);
            }
        }
    }

    void ClearTimerHandleProperty(UObject* Object, const FName PropertyName)
    {
        if (!Object)
        {
            return;
        }

        if (const FStructProperty* Prop = FindFProperty<FStructProperty>(Object->GetClass(), PropertyName))
        {
            if (Prop->Struct == FTimerHandle::StaticStruct())
            {
                FTimerHandle* Handle = Prop->ContainerPtrToValuePtr<FTimerHandle>(Object);
                if (Handle && Handle->IsValid())
                {
                    if (UWorld* World = Object->GetWorld())
                    {
                        World->GetTimerManager().ClearTimer(*Handle);
                    }
                    Handle->Invalidate();
                }
            }
        }
    }

    void CallBlueprintEvent(AActor* Actor, const FName EventName)
    {
        if (!Actor)
        {
            return;
        }

        if (UFunction* Function = Actor->FindFunction(EventName))
        {
            Actor->ProcessEvent(Function, nullptr);
        }
    }

    float CalculateLocalMoveDirectionDegrees(const AActor* Actor, const FVector& Velocity)
    {
        if (!Actor || Velocity.SizeSquared2D() < 1.0f)
        {
            return 0.0f;
        }

        const FVector LocalVelocity = Actor->GetActorTransform().InverseTransformVectorNoScale(Velocity);
        return FMath::RadiansToDegrees(FMath::Atan2(LocalVelocity.Y, LocalVelocity.X));
    }

    UAnimMontage* LoadSithMontage(const TCHAR* Path)
    {
        return LoadObject<UAnimMontage>(nullptr, Path);
    }

    UAnimMontage* LoadFactionMontage(
        const bool bRepublicSoldier,
        const bool bHeavyTrooper,
        const TCHAR* SithPath,
        const TCHAR* RepublicPath,
        const TCHAR* HeavyPath)
    {
        if (bRepublicSoldier)
        {
            return LoadObject<UAnimMontage>(nullptr, RepublicPath);
        }
        if (bHeavyTrooper)
        {
            return LoadObject<UAnimMontage>(nullptr, HeavyPath);
        }
        return LoadSithMontage(SithPath);
    }

    UAnimMontage* LoadDarkJediMontage(const TCHAR* AssetName)
    {
        const FString Path = FString::Printf(
            TEXT("/Game/EndarSpire/Characters/SithWarrior/Animations/Montages/%s.%s"),
            AssetName,
            AssetName);
        return LoadObject<UAnimMontage>(nullptr, *Path);
    }

    const TCHAR* GetDarkJediSlashMontageName(const int32 ComboIndex)
    {
        switch (FMath::Clamp(ComboIndex, 1, 5))
        {
        case 2:
            return TEXT("RT_SW_LightsaberSlash2_Montage");
        case 3:
            return TEXT("RT_SW_LightsaberSlash3_Montage");
        case 4:
            return TEXT("RT_SW_LightsaberSlash4_Montage");
        case 5:
            return TEXT("RT_SW_LightsaberSlash5_Montage");
        case 1:
        default:
            return TEXT("RT_SW_LightsaberSlash1_Montage");
        }
    }

    USoundBase* LoadEndarSpireSound(const TCHAR* AssetName)
    {
        const FString Path = FString::Printf(TEXT("/Game/EndarSpire/Audio/%s.%s"), AssetName, AssetName);
        return LoadObject<USoundBase>(nullptr, *Path);
    }

    void PlayDarkJediSound(UWorld* World, AActor* BossActor, const TCHAR* AssetName)
    {
        if (!World || !BossActor)
        {
            return;
        }

        if (USoundBase* Sound = LoadEndarSpireSound(AssetName))
        {
            UGameplayStatics::PlaySoundAtLocation(World, Sound, BossActor->GetActorLocation());
        }
    }

    UAudioComponent* SpawnDarkJediSaberHum(AActor* BossActor)
    {
        if (!BossActor)
        {
            return nullptr;
        }

        USceneComponent* AttachComponent = BossActor->GetRootComponent();
        USoundBase* Sound = LoadEndarSpireSound(TEXT("saberhum1"));
        if (!AttachComponent || !Sound)
        {
            return nullptr;
        }

        UAudioComponent* AudioComponent = UGameplayStatics::SpawnSoundAttached(Sound, AttachComponent);
        if (AudioComponent)
        {
            AudioComponent->bAutoDestroy = false;
        }
        return AudioComponent;
    }

    UParticleSystem* LoadDarkJediForceParticle(const TCHAR* AssetName)
    {
        FAssetRegistryModule& ARModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
        IAssetRegistry& AssetRegistry = ARModule.Get();
        FARFilter Filter;
        Filter.PackagePaths.Add(FName(TEXT("/Game")));
        Filter.bRecursivePaths = true;
        Filter.ClassPaths.Add(UParticleSystem::StaticClass()->GetClassPathName());

        TArray<FAssetData> Assets;
        AssetRegistry.GetAssets(Filter, Assets);
        for (const FAssetData& Asset : Assets)
        {
            if (Asset.AssetName == FName(AssetName))
            {
                return Cast<UParticleSystem>(Asset.GetAsset());
            }
        }

        const TCHAR* CandidateFolders[] =
        {
            TEXT("/Game/EndarSpire/Effects"),
            TEXT("/Game/EndarSpire/Effects/Particles"),
            TEXT("/Game/EndarSpire/Effects/Force"),
            TEXT("/Game/InfinityBladeEffects/Effects/FX_Mobile"),
            TEXT("/Game/StarterContent/Particles")
        };

        for (const TCHAR* Folder : CandidateFolders)
        {
            const FString Path = FString::Printf(TEXT("%s/%s.%s"), Folder, AssetName, AssetName);
            if (UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr, *Path))
            {
                return Particle;
            }
        }
        return nullptr;
    }

    UNiagaraSystem* LoadDarkJediForceNiagara(const TCHAR* AssetName)
    {
        FAssetRegistryModule& ARModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
        IAssetRegistry& AssetRegistry = ARModule.Get();
        FARFilter Filter;
        Filter.PackagePaths.Add(FName(TEXT("/Game")));
        Filter.bRecursivePaths = true;
        Filter.ClassPaths.Add(UNiagaraSystem::StaticClass()->GetClassPathName());

        TArray<FAssetData> Assets;
        AssetRegistry.GetAssets(Filter, Assets);
        for (const FAssetData& Asset : Assets)
        {
            if (Asset.AssetName == FName(AssetName))
            {
                return Cast<UNiagaraSystem>(Asset.GetAsset());
            }
        }

        const TCHAR* CandidateFolders[] =
        {
            TEXT("/Game/EndarSpire/Effects"),
            TEXT("/Game/EndarSpire/Effects/Particles"),
            TEXT("/Game/EndarSpire/Effects/Force"),
            TEXT("/Game/InfinityBladeEffects/Effects/FX_Mobile"),
            TEXT("/Game/StarterContent/Particles")
        };

        for (const TCHAR* Folder : CandidateFolders)
        {
            const FString Path = FString::Printf(TEXT("%s/%s.%s"), Folder, AssetName, AssetName);
            if (UNiagaraSystem* Niagara = LoadObject<UNiagaraSystem>(nullptr, *Path))
            {
                return Niagara;
            }
        }
        return nullptr;
    }

    void SpawnDarkJediForceParticle(
        UWorld* World,
        const TCHAR* AssetName,
        const FVector& Location,
        const FRotator& Rotation,
        const FVector& Scale)
    {
        if (!World)
        {
            return;
        }

        if (UParticleSystem* Particle = LoadDarkJediForceParticle(AssetName))
        {
            UGameplayStatics::SpawnEmitterAtLocation(World, Particle, Location, Rotation, Scale, true);
            return;
        }

        if (UNiagaraSystem* Niagara = LoadDarkJediForceNiagara(AssetName))
        {
            UNiagaraFunctionLibrary::SpawnSystemAtLocation(World, Niagara, Location, Rotation, Scale, true, true, ENCPoolMethod::None, true);
        }
    }

    FVector GetDarkJediFingertipLocation(USkeletalMeshComponent* Mesh, AActor* BossActor, const bool bRightHand)
    {
        const FName RightSocketNames[] =
        {
            TEXT("index_03_r"),
            TEXT("middle_03_r"),
            TEXT("ring_03_r"),
            TEXT("pinky_03_r"),
            TEXT("hand_r"),
            TEXT("RightHand"),
            TEXT("RightHandSocket"),
            TEXT("WeaponSocket")
        };
        const FName LeftSocketNames[] =
        {
            TEXT("index_03_l"),
            TEXT("middle_03_l"),
            TEXT("ring_03_l"),
            TEXT("pinky_03_l"),
            TEXT("hand_l"),
            TEXT("LeftHand"),
            TEXT("LeftHandSocket")
        };

        const FName* SocketNames = bRightHand ? RightSocketNames : LeftSocketNames;
        const int32 SocketCount = bRightHand ? UE_ARRAY_COUNT(RightSocketNames) : UE_ARRAY_COUNT(LeftSocketNames);
        if (Mesh)
        {
            for (int32 Index = 0; Index < SocketCount; ++Index)
            {
                if (Mesh->DoesSocketExist(SocketNames[Index]))
                {
                    return Mesh->GetSocketLocation(SocketNames[Index]);
                }
            }
        }

        if (!BossActor)
        {
            return FVector::ZeroVector;
        }

        const float SideSign = bRightHand ? 1.0f : -1.0f;
        return BossActor->GetActorLocation()
            + BossActor->GetActorForwardVector() * 115.0f
            + BossActor->GetActorRightVector() * 32.0f * SideSign
            + FVector(0.0f, 0.0f, 100.0f);
    }

    void DrawDarkJediLightningBranch(UWorld* World, const FVector& Start, const FVector& End, const FColor& Color, const float Lifetime, const float Thickness)
    {
        if (!World)
        {
            return;
        }

        const FVector BeamVector = End - Start;
        const float BeamLength = BeamVector.Size();
        if (BeamLength <= 5.0f)
        {
            return;
        }

        const FVector BeamDirection = BeamVector / BeamLength;
        FVector SideAxis = FVector::CrossProduct(FVector::UpVector, BeamDirection).GetSafeNormal();
        if (SideAxis.IsNearlyZero())
        {
            SideAxis = FVector::RightVector;
        }
        const FVector UpAxis = FVector::CrossProduct(BeamDirection, SideAxis).GetSafeNormal();
        const int32 SegmentCount = 9;
        const float MaxJitter = FMath::Clamp(BeamLength * 0.055f, 18.0f, 58.0f);

        FVector PreviousPoint = Start;
        for (int32 SegmentIndex = 1; SegmentIndex <= SegmentCount; ++SegmentIndex)
        {
            const float Alpha = static_cast<float>(SegmentIndex) / static_cast<float>(SegmentCount);
            FVector SegmentPoint = FMath::Lerp(Start, End, Alpha);
            if (SegmentIndex < SegmentCount)
            {
                const float Taper = FMath::Sin(Alpha * PI);
                SegmentPoint += SideAxis * FMath::FRandRange(-MaxJitter, MaxJitter) * Taper;
                SegmentPoint += UpAxis * FMath::FRandRange(-MaxJitter, MaxJitter) * Taper;
            }

            DrawDebugLine(World, PreviousPoint, SegmentPoint, Color, false, Lifetime, 0, Thickness);
            DrawDebugLine(World, PreviousPoint, SegmentPoint, FColor(210, 245, 255), false, Lifetime, 0, FMath::Max(Thickness * 0.45f, 1.5f));
            PreviousPoint = SegmentPoint;
        }
    }

    void SpawnDarkJediProceduralLightning(UWorld* World, USkeletalMeshComponent* Mesh, AActor* BossActor, AActor* TargetActor)
    {
        if (!World || !BossActor || !TargetActor)
        {
            return;
        }

        FVector TargetLocation = TargetActor->GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
        if (const ACharacter* TargetCharacter = Cast<ACharacter>(TargetActor))
        {
            if (const USkeletalMeshComponent* TargetMesh = TargetCharacter->GetMesh())
            {
                TargetLocation = TargetMesh->GetComponentLocation() + FVector(0.0f, 0.0f, 75.0f);
            }
        }

        const FVector RightFingertips = GetDarkJediFingertipLocation(Mesh, BossActor, true);
        const FVector LeftFingertips = GetDarkJediFingertipLocation(Mesh, BossActor, false);
        const float Lifetime = 0.11f;
        DrawDarkJediLightningBranch(World, RightFingertips, TargetLocation, FColor(95, 170, 255), Lifetime, 6.0f);
        DrawDarkJediLightningBranch(World, LeftFingertips, TargetLocation + FVector(0.0f, 0.0f, 18.0f), FColor(160, 225, 255), Lifetime, 4.0f);

        const FVector Midpoint = (RightFingertips + TargetLocation) * 0.5f;
        const FVector BranchEnd = Midpoint + BossActor->GetActorRightVector() * FMath::FRandRange(-160.0f, 160.0f) + FVector(0.0f, 0.0f, FMath::FRandRange(-45.0f, 85.0f));
        DrawDarkJediLightningBranch(World, Midpoint, BranchEnd, FColor(120, 210, 255), Lifetime, 2.0f);
        DrawDebugSphere(World, RightFingertips, 10.0f, 8, FColor(145, 225, 255), false, Lifetime, 0, 2.5f);
        DrawDebugSphere(World, LeftFingertips, 8.0f, 8, FColor(145, 225, 255), false, Lifetime, 0, 2.0f);
        DrawDebugSphere(World, TargetLocation, 18.0f, 10, FColor(85, 160, 255), false, Lifetime, 0, 2.5f);
    }

    float GetDarkJediIncomingDamageAmount(const AActor* DamageActor)
    {
        if (!DamageActor || !DamageActor->GetClass())
        {
            return 0.0f;
        }

        const FString DamageName = DamageActor->GetClass()->GetName();
        const FString DamagePath = DamageActor->GetClass()->GetPathName();
        const FString Key = DamageName + TEXT(" ") + DamagePath;
        if (Key.Contains(TEXT("ApplyDamage_Stasis")))
        {
            return 30.0f;
        }
        if (Key.Contains(TEXT("ApplyMeleeDamage_Bash")) || Key.Contains(TEXT("ShieldBash")))
        {
            return 100.0f;
        }
        if (Key.Contains(TEXT("ApplyMeleeDamage")))
        {
            return 50.0f;
        }
        if (Key.Contains(TEXT("ApplyDamage_Heavy"))
            || Key.Contains(TEXT("Void_Grenade_AOE"))
            || Key.Contains(TEXT("Explosive_AOE"))
            || Key.Contains(TEXT("BP_Grenade")))
        {
            return 100.0f;
        }
        if (Key.Contains(TEXT("ApplyDamage")))
        {
            return 15.0f;
        }
        return 0.0f;
    }

    UClass* LoadRepublicHealthWidgetClass()
    {
        static TWeakObjectPtr<UClass> CachedWidgetClass;
        UClass* WidgetClass = CachedWidgetClass.Get();
        if (!WidgetClass)
        {
            WidgetClass = LoadObject<UClass>(
                nullptr,
                TEXT("/Game/EndarSpire/AI/RepublicV1/Blueprints/BPW_RepublicSoldierHP.BPW_RepublicSoldierHP_C")
            );
            CachedWidgetClass = WidgetClass;
        }
        return WidgetClass;
    }

    UClass* LoadHeavyHealthWidgetClass()
    {
        static TWeakObjectPtr<UClass> CachedWidgetClass;
        UClass* WidgetClass = CachedWidgetClass.Get();
        if (!WidgetClass)
        {
            WidgetClass = LoadObject<UClass>(
                nullptr,
                TEXT("/Game/EndarSpire/AI/SithV2/BPW_SithHeavyTrooperHP.BPW_SithHeavyTrooperHP_C")
            );
            CachedWidgetClass = WidgetClass;
        }
        return WidgetClass;
    }

    UWidgetComponent* FindOrCreateHealthBarWidget(ACharacter* Character, const bool bRepublicSoldier, const bool bHeavyTrooper)
    {
        if (!Character)
        {
            return nullptr;
        }

        TArray<UWidgetComponent*> WidgetComponents;
        Character->GetComponents<UWidgetComponent>(WidgetComponents);
        for (UWidgetComponent* WidgetComponent : WidgetComponents)
        {
            if (WidgetComponent && WidgetComponent->GetFName() == TEXT("HealthBarWidgetComp"))
            {
                return WidgetComponent;
            }
        }

        if (!bRepublicSoldier && !bHeavyTrooper)
        {
            return nullptr;
        }

        UWidgetComponent* WidgetComponent = NewObject<UWidgetComponent>(Character, TEXT("HealthBarWidgetComp"));
        if (!WidgetComponent)
        {
            return nullptr;
        }

        WidgetComponent->SetupAttachment(Character->GetRootComponent());
        WidgetComponent->SetRelativeLocation(FVector(0.0f, 0.0f, 120.0f));
        WidgetComponent->SetWidgetSpace(EWidgetSpace::Screen);
        WidgetComponent->SetDrawSize(FVector2D(120.0f, 25.0f));
        WidgetComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if (UClass* WidgetClass = bHeavyTrooper ? LoadHeavyHealthWidgetClass() : LoadRepublicHealthWidgetClass())
        {
            WidgetComponent->SetWidgetClass(WidgetClass);
        }
        WidgetComponent->RegisterComponent();
        return WidgetComponent;
    }

    void UpdateHealthBarWidget(ACharacter* Character, const bool bRepublicSoldier, const bool bHeavyTrooper, const bool bIsDead)
    {
        UWidgetComponent* HealthBarWidget = FindOrCreateHealthBarWidget(Character, bRepublicSoldier, bHeavyTrooper);
        if (!HealthBarWidget)
        {
            return;
        }

        if (bRepublicSoldier || bHeavyTrooper)
        {
            if (UClass* DesiredWidgetClass = bHeavyTrooper ? LoadHeavyHealthWidgetClass() : LoadRepublicHealthWidgetClass())
            {
                if (HealthBarWidget->GetWidgetClass() != DesiredWidgetClass)
                {
                    HealthBarWidget->SetWidgetClass(DesiredWidgetClass);
                }
            }
            HealthBarWidget->SetWidgetSpace(EWidgetSpace::Screen);
            HealthBarWidget->SetDrawSize(FVector2D(120.0f, 25.0f));
            HealthBarWidget->SetRelativeLocation(FVector(0.0f, 0.0f, 120.0f));
        }

        HealthBarWidget->SetComponentTickEnabled(true);
        HealthBarWidget->SetTickMode(ETickMode::Enabled);
        HealthBarWidget->SetTickWhenOffscreen(true);

        const float Health = GetRealProperty(Character, TEXT("Health"), 0.0f);
        const float MaxHealth = FMath::Max(GetRealProperty(Character, TEXT("MaxHealth"), Health), 1.0f);
        const float HealthPercent = FMath::Clamp(Health / MaxHealth, 0.0f, 1.0f);
        const bool bShouldShow = !bIsDead && HealthPercent < 0.999f;
        HealthBarWidget->SetVisibility(bShouldShow, true);

        if (UUserWidget* Widget = HealthBarWidget->GetUserWidgetObject())
        {
            if (UWidgetTree* WidgetTree = Widget->WidgetTree)
            {
                if (UProgressBar* HealthBar = Cast<UProgressBar>(WidgetTree->FindWidget(TEXT("HealthBar"))))
                {
                    HealthBar->SetPercent(HealthPercent);
                    if (bRepublicSoldier)
                    {
                        HealthBar->SetFillColorAndOpacity(FLinearColor(0.1f, 0.8f, 0.1f, 1.0f));
                    }
                    else if (bHeavyTrooper)
                    {
                        HealthBar->SetFillColorAndOpacity(FLinearColor(0.9f, 0.4f, 0.1f, 1.0f));
                    }
                }

                if (bRepublicSoldier || bHeavyTrooper)
                {
                    const FText DisplayName = FText::FromString(bHeavyTrooper ? TEXT("Sith Heavy Trooper") : TEXT("Republic Marine"));
                    if (UTextBlock* NameText = Cast<UTextBlock>(WidgetTree->FindWidget(TEXT("NameText"))))
                    {
                        NameText->SetText(DisplayName);
                    }

                    WidgetTree->ForEachWidget([DisplayName](UWidget* Widget)
                    {
                        if (UTextBlock* TextBlock = Cast<UTextBlock>(Widget))
                        {
                            const FString ExistingText = TextBlock->GetText().ToString();
                            if (ExistingText.Contains(TEXT("Sith")) || ExistingText.Contains(TEXT("Republic")))
                            {
                                TextBlock->SetText(DisplayName);
                            }
                        }
                    });
                }
            }
        }

        HealthBarWidget->RequestRenderUpdate();
    }

    void StartDeathMontageBeforeRagdoll(
        ACharacter* Character,
        FSithTrooperCombatState& State,
        const bool bRepublicSoldier,
        const bool bHeavyTrooper,
        const float Now)
    {
        if (!Character || State.bDeathRagdollActivated)
        {
            return;
        }

        USkeletalMeshComponent* Mesh = Character->GetMesh();
        if (!State.bDeathMontageStarted)
        {
            if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
            {
                Movement->StopMovementImmediately();
                Movement->DisableMovement();
            }
            if (AController* Controller = Character->GetController())
            {
                Controller->StopMovement();
            }
            if (UCapsuleComponent* Capsule = Character->GetCapsuleComponent())
            {
                Capsule->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            }

            float DelayBeforeRagdoll = 1.6f;
            if (Mesh)
            {
                Mesh->SetSimulatePhysics(false);
                Mesh->SetAllBodiesSimulatePhysics(false);
                Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

                if (UAnimMontage* DeathMontage = LoadFactionMontage(
                    bRepublicSoldier,
                    bHeavyTrooper,
                    TEXT("/Game/EndarSpire/Characters/Sith/Animations/Locomotion/SithRetargeted/A_Sith_Death_Montage.A_Sith_Death_Montage"),
                    TEXT("/Game/EndarSpire/Characters/RepublicSoldier/Animations/Locomotion/RetargetedRepublic/RT_Republic_Death_Montage.RT_Republic_Death_Montage"),
                    TEXT("/Game/EndarSpire/Characters/HeavySithTrooper/Animations/RT_Heavy_Death_Montage.RT_Heavy_Death_Montage")))
                {
                    Character->PlayAnimMontage(DeathMontage, 1.0f);
                    DelayBeforeRagdoll = FMath::Clamp(DeathMontage->GetPlayLength(), 0.8f, 2.25f);
                }
            }

            State.DeathRagdollTime = Now + DelayBeforeRagdoll;
            State.bDeathMontageStarted = true;
        }

        if (Mesh && Now >= State.DeathRagdollTime)
        {
            Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
            Mesh->SetAllBodiesSimulatePhysics(true);
            Mesh->SetSimulatePhysics(true);
            State.bDeathRagdollActivated = true;
        }
    }

    AActor* FindNearestVisibleSithTrooper(UWorld* World, const AActor* Seeker, AAIController* AIController, const float MaxRange)
    {
        if (!World || !Seeker)
        {
            return nullptr;
        }

        AActor* BestTarget = nullptr;
        float BestDistanceSq = FMath::Square(MaxRange);
        const FVector SeekerLocation = Seeker->GetActorLocation();
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            AActor* Candidate = *It;
            if (!(IsSithTrooperActor(Candidate) || IsHeavySithTrooperActor(Candidate)) || GetBoolProperty(Candidate, TEXT("IsDead")))
            {
                continue;
            }

            const float DistanceSq = FVector::DistSquared2D(SeekerLocation, Candidate->GetActorLocation());
            if (DistanceSq >= BestDistanceSq)
            {
                continue;
            }

            if (AIController && !AIController->LineOfSightTo(Candidate))
            {
                continue;
            }

            BestTarget = Candidate;
            BestDistanceSq = DistanceSq;
        }

        return BestTarget;
    }

    AActor* FindNearestVisibleHeavyTarget(UWorld* World, const AActor* Seeker, AAIController* AIController, APawn* PlayerPawn, const float MaxRange)
    {
        if (!World || !Seeker)
        {
            return nullptr;
        }

        AActor* BestTarget = nullptr;
        float BestDistanceSq = FMath::Square(MaxRange);
        const FVector SeekerLocation = Seeker->GetActorLocation();

        auto ConsiderTarget = [&](AActor* Candidate)
        {
            if (!Candidate || Candidate == Seeker || GetBoolProperty(Candidate, TEXT("IsDead")))
            {
                return;
            }

            const float DistanceSq = FVector::DistSquared2D(SeekerLocation, Candidate->GetActorLocation());
            if (DistanceSq >= BestDistanceSq)
            {
                return;
            }

            if (AIController && !AIController->LineOfSightTo(Candidate))
            {
                return;
            }

            BestTarget = Candidate;
            BestDistanceSq = DistanceSq;
        };

        ConsiderTarget(Cast<AActor>(PlayerPawn));
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            AActor* Candidate = *It;
            if (IsRepublicSoldierActor(Candidate))
            {
                ConsiderTarget(Candidate);
            }
        }

        return BestTarget;
    }
}

UUnrealMCPBridge::UUnrealMCPBridge()
{
    EditorCommands = MakeShared<FUnrealMCPEditorCommands>();
    BlueprintCommands = MakeShared<FUnrealMCPBlueprintCommands>();
    BlueprintNodeCommands = MakeShared<FUnrealMCPBlueprintNodeCommands>();
    ProjectCommands = MakeShared<FUnrealMCPProjectCommands>();
    UMGCommands = MakeShared<FUnrealMCPUMGCommands>();
    ExtendedCommands = MakeShared<FUnrealMCPExtendedCommands>();
}

UUnrealMCPBridge::~UUnrealMCPBridge()
{
    EditorCommands.Reset();
    BlueprintCommands.Reset();
    BlueprintNodeCommands.Reset();
    ProjectCommands.Reset();
    UMGCommands.Reset();
    ExtendedCommands.Reset();
}

// Initialize subsystem
void UUnrealMCPBridge::Initialize(FSubsystemCollectionBase& Collection)
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Initializing"));

    bIsRunning = false;
    ListenerSocket = nullptr;
    ConnectionSocket = nullptr;
    ServerThread = nullptr;
    Port = MCP_SERVER_PORT;
    FIPv4Address::Parse(MCP_SERVER_HOST, ServerAddress);

    // ── Asset Registry warm-up ────────────────────────────────────────────
    // Trigger the AR initial scan now, during plugin startup, so it finishes
    // BEFORE the first MCP command arrives.  Without this, the first call to
    // FindBlueprintByName → AR.GetAssetsByClass() races against the ongoing
    // async disk scan, causing Asset.GetAsset() to dereference a partially-
    // loaded UPackage → EXCEPTION_ACCESS_VIOLATION → WinError 10053 on Python.
    //
    // WaitForCompletion() is a no-op if the scan is already done, so this adds
    // no overhead on subsequent editor restarts with a warm OS disk cache.
    // The call runs on the GameThread during subsystem init — safe and correct.
    {
        FAssetRegistryModule& ARModule =
            FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
        IAssetRegistry& AR = ARModule.Get();
        if (AR.IsLoadingAssets())
        {
            UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Waiting for Asset Registry initial scan to complete..."));
            AR.WaitForCompletion();
            UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Asset Registry scan complete — MCP is ready for first-call commands"));
        }
        else
        {
            UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Asset Registry already complete"));
        }
    }

    // Start the server automatically
    StartServer();

    if (bEnableNativeSithCombatDirector)
    {
        SithCombatTickerHandle = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateUObject(this, &UUnrealMCPBridge::SithCombatDirectorTick),
            0.05f
        );
        UE_LOG(LogMCP, Display, TEXT("UnrealMCPBridge: Sith combat director registered for PIE"));
    }
    else
    {
        UE_LOG(LogMCP, Display, TEXT("UnrealMCPBridge: Sith combat director disabled; BP_SithTrooper uses Blueprint behavior"));
    }

    // ── Watchdog timer: restart the server thread if it dies ─────────────
    // After long sessions (>50 min) the MCPServerRunnable thread can die due to:
    //   (a) An unhandled exception propagating out of the Run() loop.
    //   (b) The GameThread AsyncTask queue filling up, causing FRunnableThread
    //       to time out its join and kill the thread.
    // The watchdog polls every 15 s and calls StartServer() if the thread is gone.
    if (GEditor)
    {
        GEditor->GetTimerManager()->SetTimer(
            WatchdogTimerHandle,
            this,
            &UUnrealMCPBridge::WatchdogTick,
            15.0f,   // check every 15 seconds
            true     // loop
        );
        UE_LOG(LogMCP, Display, TEXT("UnrealMCPBridge: Watchdog timer registered (15 s interval)"));
    }
}

// Watchdog: called every 15 s by GEditor's timer manager.
// Restarts the listener thread if it has crashed or been killed.
void UUnrealMCPBridge::WatchdogTick()
{
    // If the bridge is supposed to be running but the thread is dead, restart.
    if (bIsRunning && (!ServerThread || !ListenerSocket.IsValid()))
    {
        UE_LOG(LogMCP, Warning, TEXT("UnrealMCPBridge: Watchdog detected dead server thread — restarting..."));
        // Full stop to clean up any dangling handles, then restart.
        StopServer();
        StartServer();
        if (bIsRunning)
        {
            UE_LOG(LogMCP, Display, TEXT("UnrealMCPBridge: Server thread restarted successfully"));
        }
        else
        {
            UE_LOG(LogMCP, Error, TEXT("UnrealMCPBridge: Failed to restart server thread!"));
        }
    }
}

// Clean up resources when subsystem is destroyed
void UUnrealMCPBridge::Deinitialize()
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Shutting down"));
    if (SithCombatTickerHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(SithCombatTickerHandle);
        SithCombatTickerHandle.Reset();
    }
    SithCombatStates.Reset();
    DarkJediBossStates.Reset();

    // Cancel the watchdog timer before stopping the server
    if (GEditor && WatchdogTimerHandle.IsValid())
    {
        GEditor->GetTimerManager()->ClearTimer(WatchdogTimerHandle);
    }
    StopServer();
}

void UUnrealMCPBridge::DarkJediBossDirectorTick(
    AActor* BossActor,
    FDarkJediBossCombatState& State,
    APawn* PlayerPawn,
    UNavigationSystemV1* NavSystem,
    const float DeltaTime,
    const float Now)
{
    ACharacter* Character = Cast<ACharacter>(BossActor);
    if (!Character)
    {
        return;
    }

    UWorld* World = BossActor ? BossActor->GetWorld() : nullptr;
    UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
    if (!World || !Movement)
    {
        return;
    }

    if (!State.bAppliedRuntimeSetup)
    {
        State.SpawnLocation = BossActor->GetActorLocation();
        BossActor->SetActorTickEnabled(false);
        BossActor->SetCanBeDamaged(true);
        Character->AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
        Character->AIControllerClass = AAIController::StaticClass();

        if (!Character->GetController())
        {
            Character->SpawnDefaultController();
        }

        Movement->bOrientRotationToMovement = true;
        Movement->bUseControllerDesiredRotation = false;
        Movement->RotationRate = FRotator(0.0f, 720.0f, 0.0f);
        Movement->MaxAcceleration = 4096.0f;
        Movement->BrakingDecelerationWalking = 2048.0f;
        Movement->GroundFriction = 6.0f;

        TArray<UActorComponent*> Components;
        BossActor->GetComponents(Components);
        for (UActorComponent* Component : Components)
        {
            if (!Component)
            {
                continue;
            }

            if (Component->GetFName() == TEXT("PawnSensing"))
            {
PRAGMA_DISABLE_DEPRECATION_WARNINGS
                if (UPawnSensingComponent* PawnSensing = Cast<UPawnSensingComponent>(Component))
                {
                    PawnSensing->SetSensingUpdatesEnabled(false);
                    PawnSensing->SetComponentTickEnabled(false);
                }
PRAGMA_ENABLE_DEPRECATION_WARNINGS
            }
            else if (UWidgetComponent* HealthBarWidget = Cast<UWidgetComponent>(Component))
            {
                if (HealthBarWidget->GetFName() == TEXT("HealthBarWidgetComp"))
                {
                    HealthBarWidget->SetComponentTickEnabled(true);
                    HealthBarWidget->SetTickMode(ETickMode::Enabled);
                    HealthBarWidget->SetTickWhenOffscreen(true);
                    HealthBarWidget->SetVisibility(true, true);
                    HealthBarWidget->RequestRenderUpdate();
                }
            }
            else if (Component->GetFName() == TEXT("LightsaberBlade"))
            {
                if (USceneComponent* Blade = Cast<USceneComponent>(Component))
                {
                    Blade->SetVisibility(true, true);
                    Blade->SetHiddenInGame(true, true);
                }
            }
        }
        if (USkeletalMeshComponent* Mesh = Character->GetMesh())
        {
            if (UAnimInstance* AnimInstance = Mesh->GetAnimInstance())
            {
                AnimInstance->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
            }
        }

        State.CombatState = GetIntProperty(BossActor, TEXT("BossCombatState"), 0);
        const float DoubledMaxHealth = FMath::Max(GetRealProperty(BossActor, TEXT("MaxHealth"), 500.0f), 1.0f) * 2.0f;
        SetRealProperty(BossActor, TEXT("MaxHealth"), DoubledMaxHealth);
        SetRealProperty(BossActor, TEXT("Health"), DoubledMaxHealth);
        SetBoolProperty(BossActor, TEXT("PlayerSeen"), false);
        SetBoolProperty(BossActor, TEXT("bIsAttacking"), false);
        SetObjectProperty(BossActor, TEXT("SaberHumSound"), nullptr);
        SetIntProperty(BossActor, TEXT("BossCombatState"), 0);
        State.bAppliedRuntimeSetup = true;
    }

    AAIController* AIController = Cast<AAIController>(Character->GetController());
    if (!AIController)
    {
        Character->AIControllerClass = AAIController::StaticClass();
        Character->SpawnDefaultController();
        AIController = Cast<AAIController>(Character->GetController());
    }

    const bool bIsDead = GetBoolProperty(BossActor, TEXT("IsDead"));
    UpdateHealthBarWidget(Character, false, false, bIsDead);
    if (bIsDead)
    {
        if (!State.bDeathMontageStarted)
        {
            if (State.SaberHumComponent.IsValid())
            {
                State.SaberHumComponent->Stop();
                State.SaberHumComponent->DestroyComponent();
                State.SaberHumComponent.Reset();
            }
            TArray<UAudioComponent*> AudioComponents;
            BossActor->GetComponents<UAudioComponent>(AudioComponents);
            for (UAudioComponent* AudioComponent : AudioComponents)
            {
                if (AudioComponent && AudioComponent->Sound && AudioComponent->Sound->GetName().Contains(TEXT("saberhum")))
                {
                    AudioComponent->Stop();
                    AudioComponent->DestroyComponent();
                }
            }
            SetBoolProperty(BossActor, TEXT("bSaberActive"), false);
            SetObjectProperty(BossActor, TEXT("SaberHumSound"), nullptr);
            PlayDarkJediSound(World, BossActor, TEXT("enemy_saber_off"));
            TArray<USceneComponent*> SceneComponents;
            BossActor->GetComponents<USceneComponent>(SceneComponents);
            for (USceneComponent* Component : SceneComponents)
            {
                if (Component && Component->GetFName() == TEXT("LightsaberBlade"))
                {
                    Component->SetVisibility(false, true);
                    Component->SetHiddenInGame(true, true);
                    break;
                }
            }
            if (AIController)
            {
                AIController->StopMovement();
                AIController->ClearFocus(EAIFocusPriority::Gameplay);
            }
            Movement->StopMovementImmediately();
            Movement->DisableMovement();
            if (UCapsuleComponent* Capsule = Character->GetCapsuleComponent())
            {
                Capsule->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            }
            if (USkeletalMeshComponent* Mesh = Character->GetMesh())
            {
                Mesh->SetSimulatePhysics(false);
                Mesh->SetAllBodiesSimulatePhysics(false);
                Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                if (UAnimMontage* DeathMontage = LoadDarkJediMontage(TEXT("RT_SW_Death_Montage")))
                {
                    Character->PlayAnimMontage(DeathMontage, 1.0f);
                    State.DeathRagdollTime = Now + FMath::Clamp(DeathMontage->GetPlayLength(), 0.8f, 2.25f);
                }
                else
                {
                    State.DeathRagdollTime = Now + 1.6f;
                }
            }
            State.bDeathMontageStarted = true;
        }

        SetBoolProperty(BossActor, TEXT("PlayerSeen"), false);
        SetBoolProperty(BossActor, TEXT("bIsAttacking"), false);
        SetIntProperty(BossActor, TEXT("BossCombatState"), 8);
        State.CombatState = 8;
        State.Target.Reset();
        if (!State.bDeathRagdollActivated && Now >= State.DeathRagdollTime)
        {
            if (USkeletalMeshComponent* Mesh = Character->GetMesh())
            {
                Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
                Mesh->SetAllBodiesSimulatePhysics(true);
                Mesh->SetSimulatePhysics(true);
            }
            State.bDeathRagdollActivated = true;
        }
        return;
    }

    BossActor->SetCanBeDamaged(true);
    const FVector BossLocation = BossActor->GetActorLocation();

    if (Now >= State.NextIncomingDamageTime)
    {
        float IncomingDamage = 0.0f;
        AActor* DamageCauser = nullptr;
        for (TActorIterator<AActor> DamageIt(World); DamageIt; ++DamageIt)
        {
            AActor* Candidate = *DamageIt;
            const float CandidateDamage = GetDarkJediIncomingDamageAmount(Candidate);
            if (CandidateDamage <= 0.0f)
            {
                continue;
            }

            if (FVector::DistSquared(Candidate->GetActorLocation(), BossLocation) <= FMath::Square(260.0f))
            {
                IncomingDamage = CandidateDamage;
                DamageCauser = Candidate;
                break;
            }
        }

        if (IncomingDamage > 0.0f)
        {
            const float MaxHealth = FMath::Max(GetRealProperty(BossActor, TEXT("MaxHealth"), 500.0f), 1.0f);
            const float CurrentHealth = FMath::Clamp(GetRealProperty(BossActor, TEXT("Health"), MaxHealth), 0.0f, MaxHealth);
            const float NewHealth = FMath::Clamp(CurrentHealth - IncomingDamage, 0.0f, MaxHealth);
            SetRealProperty(BossActor, TEXT("Health"), NewHealth);
            if (NewHealth <= 0.0f)
            {
                CallBlueprintEvent(BossActor, TEXT("Die"));
                SetBoolProperty(BossActor, TEXT("IsDead"), true);
            }
            else
            {
                CallBlueprintEvent(BossActor, TEXT("UpdateBossPhase"));
            }
            State.NextIncomingDamageTime = Now + 0.35f;
        }
    }

    const float SightRange = 2000.0f;
    const float LoseRange = 2600.0f;
    const float MeleeRange = FMath::Max(GetRealProperty(BossActor, TEXT("MeleeRange"), 220.0f), 260.0f);
    const float SlashStartRange = FMath::Clamp(MeleeRange * 0.72f, 175.0f, 215.0f);
    const float AttackCooldown = FMath::Clamp(GetRealProperty(BossActor, TEXT("AttackCooldown"), 0.62f), 0.48f, 0.72f);

    AActor* VisibleTarget = FindNearestVisibleHeavyTarget(World, BossActor, AIController, PlayerPawn, SightRange);
    if (VisibleTarget)
    {
        State.Target = VisibleTarget;
        State.LastSeenTime = Now;
        State.LostSightStartTime = -1.0f;
    }
    else if (State.Target.IsValid())
    {
        const float CurrentTargetDistance = FVector::Dist2D(BossLocation, State.Target->GetActorLocation());
        const bool bCurrentTargetInvalid = GetBoolProperty(State.Target.Get(), TEXT("IsDead"));
        if (State.LostSightStartTime < 0.0f)
        {
            State.LostSightStartTime = Now;
        }
        if (bCurrentTargetInvalid || CurrentTargetDistance > LoseRange || (Now - State.LostSightStartTime) > 3.0f)
        {
            State.Target.Reset();
        }
    }

    AActor* TargetActor = State.Target.Get();
    const float DistanceToTarget = TargetActor ? FVector::Dist2D(BossLocation, TargetActor->GetActorLocation()) : BIG_NUMBER;
    const bool bInCombat = State.Target.IsValid();
    SetBoolProperty(BossActor, TEXT("PlayerSeen"), bInCombat);
    SetObjectProperty(BossActor, TEXT("TargetActor"), bInCombat ? State.Target.Get() : nullptr);

    auto EnterState = [&](const int32 NewState)
    {
        if (State.CombatState != NewState)
        {
            if (NewState == 2 && State.CombatState != 2)
            {
                State.DesiredComboLength = FMath::RandRange(1, 4);
                State.ComboAttempts = 0;
            }
            State.CombatState = NewState;
            State.StateEnterTime = Now;
            State.bIssuedStateMove = false;
            State.bDamageAppliedThisSwing = false;
            State.bForceEffectApplied = false;
            SetIntProperty(BossActor, TEXT("BossCombatState"), NewState);
        }
    };

    auto FaceTarget = [&]()
    {
        if (!State.Target.IsValid())
        {
            return;
        }
        if (State.CombatState == 1 && DistanceToTarget > MeleeRange * 1.25f)
        {
            return;
        }
        FVector LookDirection = State.Target->GetActorLocation() - BossLocation;
        LookDirection.Z = 0.0f;
        if (LookDirection.IsNearlyZero())
        {
            return;
        }
        const FRotator DesiredRotation = LookDirection.Rotation();
        BossActor->SetActorRotation(FMath::RInterpTo(BossActor->GetActorRotation(), DesiredRotation, DeltaTime, 9.0f));
        if (AIController)
        {
            AIController->SetFocus(State.Target.Get());
        }
    };

    auto ActivateSaber = [&]()
    {
        if (State.bSaberActivated)
        {
            return;
        }

        const bool bAlreadyActive = GetBoolProperty(BossActor, TEXT("bSaberActive"));
        if (!bAlreadyActive)
        {
            SetBoolProperty(BossActor, TEXT("bSaberActive"), true);
            if (UAnimMontage* DrawMontage = LoadDarkJediMontage(TEXT("RT_SW_LightsaberDraw_Montage")))
            {
                Character->PlayAnimMontage(DrawMontage, 1.0f);
            }
        }

        TArray<USceneComponent*> SceneComponents;
        BossActor->GetComponents<USceneComponent>(SceneComponents);
        for (USceneComponent* Component : SceneComponents)
        {
            if (Component && Component->GetFName() == TEXT("LightsaberBlade"))
            {
                Component->SetVisibility(true, true);
                Component->SetHiddenInGame(false, true);
                break;
            }
        }

        PlayDarkJediSound(World, BossActor, TEXT("enemy_saber_on"));
        State.SaberHumComponent = SpawnDarkJediSaberHum(BossActor);
        CallBlueprintEvent(BossActor, TEXT("StartTauntLoop"));
        State.bSaberActivated = true;
    };

    if (!bInCombat)
    {
        EnterState(0);
        Movement->MaxWalkSpeed = 0.0f;
        SetBoolProperty(BossActor, TEXT("bIsAttacking"), false);
        if (AIController)
        {
            AIController->StopMovement();
            AIController->ClearFocus(EAIFocusPriority::Gameplay);
        }
    }
    else
    {
        ActivateSaber();
        FaceTarget();

        if (State.CombatState == 0 || State.CombatState == 8)
        {
            EnterState(1);
        }

        if (State.CombatState == 1)
        {
            Movement->MaxWalkSpeed = FMath::Max(GetRealProperty(BossActor, TEXT("ChargeSpeed"), 450.0f), 820.0f);
            Movement->MaxAcceleration = 8192.0f;
            Movement->BrakingDecelerationWalking = 3072.0f;
            Movement->GroundFriction = 4.0f;
            Movement->bOrientRotationToMovement = true;
            Movement->bUseControllerDesiredRotation = false;
            SetBoolProperty(BossActor, TEXT("bIsAttacking"), false);
            if (DistanceToTarget <= SlashStartRange)
            {
                if (AIController)
                {
                    AIController->StopMovement();
                }
                Movement->StopMovementImmediately();
                EnterState(2);
            }
            else if (AIController && State.Target.IsValid() && Now >= State.NextMoveTime)
            {
                AIController->MoveToActor(State.Target.Get(), 80.0f, false, true, true, nullptr, true);
                State.NextMoveTime = Now + 0.2f;
            }

            if (State.Target.IsValid() && DistanceToTarget > SlashStartRange)
            {
                const FVector MoveDirection = (State.Target->GetActorLocation() - BossLocation).GetSafeNormal2D();
                if (!MoveDirection.IsNearlyZero())
                {
                    Character->AddMovementInput(MoveDirection, AIController ? 0.35f : 1.0f, true);
                }
            }
        }

        if (State.CombatState == 2)
        {
            Movement->MaxWalkSpeed = 420.0f;
            Movement->MaxAcceleration = 8192.0f;
            Movement->bOrientRotationToMovement = false;
            Movement->bUseControllerDesiredRotation = false;
            if (AIController)
            {
                AIController->StopMovement();
            }

            if (!State.bIssuedStateMove)
            {
                const int32 SlashIndex = (State.ComboAttempts % 5) + 1;
                if (UAnimMontage* SlashMontage = LoadDarkJediMontage(GetDarkJediSlashMontageName(SlashIndex)))
                {
                    Character->PlayAnimMontage(SlashMontage, 1.45f);
                }
                SetBoolProperty(BossActor, TEXT("bIsAttacking"), true);
                State.bIssuedStateMove = true;
                State.NextAttackTime = Now + AttackCooldown;
                ++State.ComboAttempts;
            }

            const float AttackElapsed = Now - State.StateEnterTime;
            if (State.Target.IsValid() && AttackElapsed <= AttackCooldown * 0.55f && DistanceToTarget > 95.0f)
            {
                const FVector LungeDirection = (State.Target->GetActorLocation() - BossLocation).GetSafeNormal2D();
                if (!LungeDirection.IsNearlyZero())
                {
                    Character->AddMovementInput(LungeDirection, 0.85f, true);
                }
            }
            if (!State.bDamageAppliedThisSwing
                && AttackElapsed >= AttackCooldown * 0.35f
                && AttackElapsed <= AttackCooldown * 0.65f
                && DistanceToTarget <= MeleeRange + 120.0f)
            {
                const float MeleeDamage = GetRealProperty(BossActor, TEXT("MeleeDamage"), 35.0f);
                UGameplayStatics::ApplyDamage(State.Target.Get(), MeleeDamage, Character->GetController(), BossActor, nullptr);
                PlayDarkJediSound(World, BossActor, FMath::RandBool() ? TEXT("saberhit") : TEXT("saberhit1"));
                State.bDamageAppliedThisSwing = true;
            }

            const int32 MaxComboHits = FMath::Clamp(State.DesiredComboLength, 1, 4);
            if (Now >= State.NextAttackTime)
            {
                SetBoolProperty(BossActor, TEXT("bIsAttacking"), false);
                if (DistanceToTarget > MeleeRange * 1.1f)
                {
                    EnterState(1);
                }
                else if (DistanceToTarget <= MeleeRange * 1.25f && State.ComboAttempts < MaxComboHits)
                {
                    EnterState(2);
                    State.bIssuedStateMove = false;
                }
                else
                {
                    State.ComboAttempts = 0;
                    if (DistanceToTarget > MeleeRange * 1.35f)
                    {
                        EnterState(1);
                    }
                    else if (State.LastForceState == 6)
                    {
                        EnterState(FMath::FRand() < 0.35f ? 7 : 5);
                    }
                    else if (State.LastForceState == 7)
                    {
                        EnterState(5);
                    }
                    else
                    {
                        EnterState(5);
                    }
                }
            }
        }

        if (State.CombatState == 3)
        {
            Movement->MaxWalkSpeed = GetRealProperty(BossActor, TEXT("StrafeSpeed"), 220.0f);
            Movement->bOrientRotationToMovement = true;
            Movement->bUseControllerDesiredRotation = false;
            SetBoolProperty(BossActor, TEXT("bIsAttacking"), false);
            if (!State.bIssuedStateMove && State.Target.IsValid())
            {
                FVector Away = (BossLocation - State.Target->GetActorLocation()).GetSafeNormal2D();
                if (Away.IsNearlyZero())
                {
                    Away = -BossActor->GetActorForwardVector();
                }
                const float DisengageDistance = GetRealProperty(BossActor, TEXT("DisengageDistance"), 600.0f);
                FVector Goal = BossLocation + Away * DisengageDistance;
                FNavLocation Projected;
                if (NavSystem && NavSystem->ProjectPointToNavigation(Goal, Projected, FVector(300.0f, 300.0f, 300.0f)))
                {
                    Goal = Projected.Location;
                }
                if (AIController)
                {
                    AIController->MoveToLocation(Goal, 100.0f, true, true, true, false, nullptr, true);
                }
                if (!AIController)
                {
                    Character->AddMovementInput((Goal - BossLocation).GetSafeNormal2D(), 0.8f, true);
                }
                State.bIssuedStateMove = true;
            }
            if ((Now - State.StateEnterTime) > 1.2f || DistanceToTarget >= MeleeRange * 2.4f)
            {
                State.StrafeSign *= -1.0f;
                EnterState(4);
            }
        }

        if (State.CombatState == 4)
        {
            Movement->MaxWalkSpeed = GetRealProperty(BossActor, TEXT("StrafeSpeed"), 220.0f);
            Movement->bOrientRotationToMovement = true;
            Movement->bUseControllerDesiredRotation = false;
            if (!State.bIssuedStateMove && State.Target.IsValid())
            {
                const FVector ToTarget = (State.Target->GetActorLocation() - BossLocation).GetSafeNormal2D();
                const FVector StrafeDir = FVector::CrossProduct(FVector::UpVector, ToTarget).GetSafeNormal2D() * State.StrafeSign;
                FVector Goal = BossLocation + StrafeDir * 360.0f - ToTarget * 80.0f;
                FNavLocation Projected;
                if (NavSystem && NavSystem->ProjectPointToNavigation(Goal, Projected, FVector(300.0f, 300.0f, 300.0f)))
                {
                    Goal = Projected.Location;
                }
                if (AIController)
                {
                    AIController->MoveToLocation(Goal, 90.0f, true, true, true, false, nullptr, true);
                }
                if (!AIController)
                {
                    Character->AddMovementInput((Goal - BossLocation).GetSafeNormal2D(), 0.8f, true);
                }
                State.bIssuedStateMove = true;
            }
            if ((Now - State.StateEnterTime) >= FMath::Clamp(GetRealProperty(BossActor, TEXT("StrafeDuration"), 1.5f), 1.0f, 4.0f))
            {
                EnterState(1);
            }
        }

        if (State.CombatState == 5)
        {
            Movement->MaxWalkSpeed = 0.0f;
            Movement->StopMovementImmediately();
            Movement->bOrientRotationToMovement = false;
            if (AIController)
            {
                AIController->StopMovement();
            }
            FaceTarget();
            if (!State.bIssuedStateMove)
            {
                State.LastForceState = 5;
                if (UAnimMontage* ForceMontage = LoadDarkJediMontage(TEXT("RT_SW_ForcePush_Montage")))
                {
                    Character->PlayAnimMontage(ForceMontage, 1.0f);
                }
                PlayDarkJediSound(World, BossActor, TEXT("push"));
                SpawnDarkJediForceParticle(
                    World,
                    TEXT("P_Shield_Spawn"),
                    BossLocation + BossActor->GetActorForwardVector() * 85.0f,
                    BossActor->GetActorRotation(),
                    FVector(1.6f, 1.6f, 1.6f));
                State.ForceEffectTime = Now + 0.42f;
                State.ForceEndTime = Now + 1.05f;
                State.bIssuedStateMove = true;
            }
            if (!State.bForceEffectApplied && Now >= State.ForceEffectTime && State.Target.IsValid())
            {
                if (ACharacter* TargetCharacter = Cast<ACharacter>(State.Target.Get()))
                {
                    const FVector PushDirection = (TargetCharacter->GetActorLocation() - BossLocation).GetSafeNormal2D();
                    TargetCharacter->LaunchCharacter(PushDirection * 900.0f + FVector(0.0f, 0.0f, 220.0f), true, true);
                }
                UGameplayStatics::ApplyDamage(State.Target.Get(), 35.0f, Character->GetController(), BossActor, nullptr);
                State.bForceEffectApplied = true;
            }
            if (Now >= State.ForceEndTime)
            {
                EnterState(6);
            }
        }

        if (State.CombatState == 6)
        {
            Movement->MaxWalkSpeed = 0.0f;
            Movement->StopMovementImmediately();
            Movement->bOrientRotationToMovement = false;
            if (AIController)
            {
                AIController->StopMovement();
            }
            FaceTarget();
            if (!State.bIssuedStateMove)
            {
                State.LastForceState = 6;
                float LightningDuration = 1.65f;
                if (UAnimMontage* ForceMontage = LoadDarkJediMontage(TEXT("RT_SW_ForceLightning_Montage")))
                {
                    Character->PlayAnimMontage(ForceMontage, 1.0f);
                    LightningDuration = FMath::Clamp(ForceMontage->GetPlayLength(), 1.65f, 3.0f);
                }
                PlayDarkJediSound(World, BossActor, TEXT("lightning"));
                if (State.Target.IsValid())
                {
                    SpawnDarkJediProceduralLightning(World, Character->GetMesh(), BossActor, State.Target.Get());
                    const FVector TargetLocation = State.Target->GetActorLocation();
                    const FRotator LightningRotation = (TargetLocation - BossLocation).Rotation();
                    const float LightningScaleX = FMath::Clamp(FVector::Dist2D(BossLocation, TargetLocation) / 220.0f, 1.6f, 7.0f);
                    const FVector LightningOrigin = BossLocation + BossActor->GetActorForwardVector() * 125.0f + FVector(0.0f, 0.0f, 85.0f);
                    const FVector LightningMidpoint = (BossLocation + TargetLocation) * 0.5f + FVector(0.0f, 0.0f, 55.0f);
                    SpawnDarkJediForceParticle(
                        World,
                        TEXT("P_Dor_Lightning_01"),
                        LightningOrigin,
                        LightningRotation,
                        FVector(LightningScaleX, 1.4f, 1.4f));
                    SpawnDarkJediForceParticle(
                        World,
                        TEXT("P_Dor_Lightning_01"),
                        LightningMidpoint,
                        LightningRotation,
                        FVector(LightningScaleX * 0.6f, 1.2f, 1.2f));
                }
                State.NextLightningTickTime = Now + 0.25f;
                State.NextLightningVfxTime = Now + 0.05f;
                State.ForceEndTime = Now + LightningDuration;
                State.bIssuedStateMove = true;
            }
            if (State.Target.IsValid() && Now >= State.NextLightningVfxTime && Now <= State.ForceEndTime)
            {
                SpawnDarkJediProceduralLightning(World, Character->GetMesh(), BossActor, State.Target.Get());
                const FVector TargetLocation = State.Target->GetActorLocation();
                const FRotator LightningRotation = (TargetLocation - BossLocation).Rotation();
                const float LightningScaleX = FMath::Clamp(FVector::Dist2D(BossLocation, TargetLocation) / 220.0f, 1.6f, 7.0f);
                const FVector LightningOrigin = BossLocation + BossActor->GetActorForwardVector() * 125.0f + FVector(0.0f, 0.0f, 85.0f);
                const FVector LightningMidpoint = (BossLocation + TargetLocation) * 0.5f + FVector(0.0f, 0.0f, 55.0f);
                SpawnDarkJediForceParticle(
                    World,
                    TEXT("P_Dor_Lightning_01"),
                    LightningOrigin,
                    LightningRotation,
                    FVector(LightningScaleX, 1.4f, 1.4f));
                SpawnDarkJediForceParticle(
                    World,
                    TEXT("P_Dor_Lightning_01"),
                    LightningMidpoint,
                    LightningRotation,
                    FVector(LightningScaleX * 0.6f, 1.2f, 1.2f));
                State.NextLightningVfxTime = Now + 0.05f;
            }
            if (State.Target.IsValid() && Now >= State.NextLightningTickTime)
            {
                UGameplayStatics::ApplyDamage(
                    State.Target.Get(),
                    GetRealProperty(BossActor, TEXT("ForceLightningDamage"), 15.0f),
                    Character->GetController(),
                    BossActor,
                    nullptr);
                State.NextLightningTickTime = Now + 0.3f;
            }
            if (Now >= State.ForceEndTime)
            {
                EnterState(1);
            }
        }

        if (State.CombatState == 7)
        {
            Movement->MaxWalkSpeed = 0.0f;
            Movement->StopMovementImmediately();
            Movement->bOrientRotationToMovement = false;
            if (AIController)
            {
                AIController->StopMovement();
            }
            FaceTarget();
            if (!State.bIssuedStateMove)
            {
                State.LastForceState = 7;
                if (UAnimMontage* ForceMontage = LoadDarkJediMontage(TEXT("RT_SW_ForcePull_Montage")))
                {
                    Character->PlayAnimMontage(ForceMontage, 1.0f);
                }
                PlayDarkJediSound(World, BossActor, TEXT("pull"));
                SpawnDarkJediForceParticle(
                    World,
                    TEXT("P_Shield_Spawn"),
                    BossLocation + BossActor->GetActorForwardVector() * 75.0f,
                    BossActor->GetActorRotation(),
                    FVector(1.2f, 1.2f, 1.2f));
                State.ForceEffectTime = Now + 0.38f;
                State.ForceEndTime = Now + 0.95f;
                State.bIssuedStateMove = true;
            }
            if (!State.bForceEffectApplied && Now >= State.ForceEffectTime && State.Target.IsValid())
            {
                const FVector PullGoal = BossLocation + BossActor->GetActorForwardVector() * (MeleeRange + 45.0f);
                if (ACharacter* TargetCharacter = Cast<ACharacter>(State.Target.Get()))
                {
                    const FVector PullVelocity = (PullGoal - TargetCharacter->GetActorLocation()).GetSafeNormal() * 1000.0f;
                    TargetCharacter->LaunchCharacter(PullVelocity, true, true);
                }
                UGameplayStatics::ApplyDamage(State.Target.Get(), 20.0f, Character->GetController(), BossActor, nullptr);
                State.bForceEffectApplied = true;
            }
            if (Now >= State.ForceEndTime)
            {
                EnterState(2);
            }
        }
    }

    const FVector Velocity = Character->GetVelocity();
    const float RawSpeed = Velocity.Size2D();
    const float RawDirection = CalculateLocalMoveDirectionDegrees(BossActor, Velocity);
    State.SmoothedAnimSpeed = FMath::FInterpTo(State.SmoothedAnimSpeed, RawSpeed, DeltaTime, 12.0f);
    const float DirectionDelta = FMath::FindDeltaAngleDegrees(State.SmoothedAnimDirection, RawDirection);
    State.SmoothedAnimDirection = FMath::UnwindDegrees(
        State.SmoothedAnimDirection + FMath::Clamp(DirectionDelta, -360.0f * DeltaTime, 360.0f * DeltaTime));

    SetRealProperty(BossActor, TEXT("Speed"), State.SmoothedAnimSpeed);
    SetRealProperty(BossActor, TEXT("Direction"), State.SmoothedAnimDirection);
    if (USkeletalMeshComponent* Mesh = Character->GetMesh())
    {
        if (UAnimInstance* AnimInstance = Mesh->GetAnimInstance())
        {
            SetRealProperty(AnimInstance, TEXT("Speed"), State.SmoothedAnimSpeed);
            SetRealProperty(AnimInstance, TEXT("Direction"), State.SmoothedAnimDirection);
            SetBoolProperty(AnimInstance, TEXT("IsInCombat"), bInCombat);
            SetBoolProperty(AnimInstance, TEXT("IsAttacking"), GetBoolProperty(BossActor, TEXT("bIsAttacking")));
            SetBoolProperty(AnimInstance, TEXT("IsDead"), bIsDead);
            SetIntProperty(AnimInstance, TEXT("BossCombatState"), State.CombatState);
        }
    }

    State.bWasInCombat = bInCombat;
}

bool UUnrealMCPBridge::SithCombatDirectorTick(float DeltaTime)
{
    UWorld* World = FindSithDirectorWorld();
    if (!World || World->bIsTearingDown)
    {
        SithCombatStates.Reset();
        DarkJediBossStates.Reset();
        return true;
    }

    APawn* PlayerPawn = UGameplayStatics::GetPlayerPawn(World, 0);
    UNavigationSystemV1* NavSystem = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    const float Now = World->GetTimeSeconds();
    constexpr int32 MaxNavQueriesPerDirectorTick = 3;
    int32 NavQueriesThisDirectorTick = 0;

    TSet<TWeakObjectPtr<AActor>> SeenThisTick;
    TSet<TWeakObjectPtr<AActor>> SeenDarkJediBossesThisTick;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Trooper = *It;
        if (IsDarkJediBossActor(Trooper))
        {
            SeenDarkJediBossesThisTick.Add(Trooper);
            FDarkJediBossCombatState& BossState = DarkJediBossStates.FindOrAdd(Trooper);
            DarkJediBossDirectorTick(Trooper, BossState, PlayerPawn, NavSystem, DeltaTime, Now);
            continue;
        }

        if (!IsNativeInfantryCombatActor(Trooper))
        {
            continue;
        }

        const bool bRepublicSoldier = IsRepublicSoldierActor(Trooper);
        const bool bHeavyTrooper = IsHeavySithTrooperActor(Trooper);
        SeenThisTick.Add(Trooper);
        FSithTrooperCombatState& State = SithCombatStates.FindOrAdd(Trooper);
        if (State.SpawnLocation.IsNearlyZero())
        {
            State.SpawnLocation = Trooper->GetActorLocation();
        }

        ACharacter* Character = Cast<ACharacter>(Trooper);
        UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
        AAIController* AIController = Character ? Cast<AAIController>(Character->GetController()) : nullptr;
        if (!Character || !Movement)
        {
            continue;
        }

        if (!State.bClearedBlueprintMoveTimer)
        {
            // The old Blueprint RepositionTick timer issues random moves that fight the tactical director.
            ClearTimerHandleProperty(Trooper, TEXT("MoveTimerHandle"));
            State.bClearedBlueprintMoveTimer = true;
        }

        if (!State.bAppliedRuntimeOptimizations)
        {
            // The Blueprint Event Tick still pushes AnimBP variables and calls SetActorRotation.
            // The native director owns both now; leaving BP tick enabled causes visible
            // tug-of-war during repositioning.
            Trooper->SetActorTickEnabled(false);

            TArray<UActorComponent*> Components;
            Trooper->GetComponents(Components);
            for (UActorComponent* Component : Components)
            {
                if (!Component)
                {
                    continue;
                }

                const FName ComponentName = Component->GetFName();
                if (ComponentName == TEXT("HealthBarWidgetComp"))
                {
                    if (UWidgetComponent* HealthBarWidget = Cast<UWidgetComponent>(Component))
                    {
                        HealthBarWidget->SetComponentTickEnabled(true);
                        HealthBarWidget->SetTickMode(ETickMode::Enabled);
                        HealthBarWidget->SetTickWhenOffscreen(true);
                        HealthBarWidget->RequestRenderUpdate();
                    }
                }
                else if (bRepublicSoldier || bHeavyTrooper)
                {
PRAGMA_DISABLE_DEPRECATION_WARNINGS
                    if (UPawnSensingComponent* PawnSensing = Cast<UPawnSensingComponent>(Component))
                    {
                        // Republic and Heavy units are native-director driven. Disabling PawnSensing
                        // prevents duplicated Sith graph logic from fighting faction targeting.
                        PawnSensing->SetSensingUpdatesEnabled(false);
                        PawnSensing->SetComponentTickEnabled(false);
                    }
PRAGMA_ENABLE_DEPRECATION_WARNINGS
                }
                else if (ComponentName == TEXT("Gun") && Component->IsA<UStaticMeshComponent>())
                {
                    Component->SetComponentTickEnabled(false);
                }
            }

            if (USkeletalMeshComponent* Mesh = Character->GetMesh())
            {
                Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
                Mesh->bEnableUpdateRateOptimizations = true;

                if (!bRepublicSoldier)
                {
                    static TWeakObjectPtr<UClass> CachedSithEliteAnimClass;
                    static TWeakObjectPtr<UClass> CachedHeavyAnimClass;
                    UClass* DesiredAnimClass = bHeavyTrooper ? CachedHeavyAnimClass.Get() : CachedSithEliteAnimClass.Get();
                    if (!DesiredAnimClass)
                    {
                        DesiredAnimClass = LoadObject<UClass>(
                            nullptr,
                            bHeavyTrooper
                                ? TEXT("/Game/EndarSpire/AI/SithV2/ABP_SithHeavyTrooper.ABP_SithHeavyTrooper_C")
                                : TEXT("/Game/EndarSpire/AI/SithV2/ABP_SithTrooperElite.ABP_SithTrooperElite_C")
                        );
                        if (bHeavyTrooper)
                        {
                            CachedHeavyAnimClass = DesiredAnimClass;
                        }
                        else
                        {
                            CachedSithEliteAnimClass = DesiredAnimClass;
                        }
                    }

                    if (DesiredAnimClass && Mesh->GetAnimClass() != DesiredAnimClass)
                    {
                        Mesh->SetAnimationMode(EAnimationMode::AnimationBlueprint);
                        Mesh->SetAnimInstanceClass(DesiredAnimClass);
                    }
                }
            }

            State.bAppliedRuntimeOptimizations = true;
        }

        const bool bIsDead = GetBoolProperty(Trooper, TEXT("IsDead"));
        UpdateHealthBarWidget(Character, bRepublicSoldier, bHeavyTrooper, bIsDead);
        if (bIsDead)
        {
            SetBoolProperty(Trooper, TEXT("PlayerSeen"), false);
            SetBoolProperty(Trooper, TEXT("bWeaponRaised"), false);
            SetBoolProperty(Trooper, TEXT("IsShooting?"), false);
            SetBoolProperty(Trooper, TEXT("bIsMoving"), false);
            State.bMoveInProgress = false;
            StartDeathMontageBeforeRagdoll(Character, State, bRepublicSoldier, bHeavyTrooper, Now);
            continue;
        }
        State.bDeathMontageStarted = false;
        State.bDeathRagdollActivated = false;
        State.DeathRagdollTime = 0.0f;

        const FVector TrooperLocation = Trooper->GetActorLocation();
        const float DistanceToPlayer = PlayerPawn ? FVector::Dist2D(TrooperLocation, PlayerPawn->GetActorLocation()) : BIG_NUMBER;
        const float PatrolRadius = GetRealProperty(Trooper, TEXT("PatrolRadius"), 800.0f);
        const float CombatMoveRadius = GetRealProperty(Trooper, TEXT("CombatMoveRadius"), 400.0f);
        const float EngagementDistance = GetRealProperty(Trooper, TEXT("EngagementDistance"), 1500.0f);
        const float MinEngagementDistance = GetRealProperty(Trooper, TEXT("MinEngagementDistance"), 600.0f);
        const float CombatMoveInterval = GetRealProperty(Trooper, TEXT("CombatMoveInterval"), 4.0f);
        const float IdleMoveInterval = GetRealProperty(Trooper, TEXT("IdleMoveInterval"), 6.0f);
        const float TickOptimizationDistance = GetRealProperty(Trooper, TEXT("TickOptimizationDistance"), 5000.0f);
        AActor* VisibleTarget = bRepublicSoldier
            ? FindNearestVisibleSithTrooper(World, Trooper, AIController, 3600.0f)
            : (bHeavyTrooper
                ? FindNearestVisibleHeavyTarget(World, Trooper, AIController, PlayerPawn, 3600.0f)
                : Cast<AActor>(PlayerPawn));
        const FVector TargetLocation = VisibleTarget ? VisibleTarget->GetActorLocation() : FVector::ZeroVector;
        const float DistanceToTarget = VisibleTarget ? FVector::Dist2D(TrooperLocation, TargetLocation) : BIG_NUMBER;
        const bool bTargetInAwarenessRange = VisibleTarget && DistanceToTarget <= 3600.0f;
        const bool bHasLineOfSight = bTargetInAwarenessRange
            && (AIController ? AIController->LineOfSightTo(VisibleTarget) : true);

        if (bHasLineOfSight)
        {
            State.Target = VisibleTarget;
            State.LastSeenTime = Now;
        }

        const bool bStickyCombat = State.Target.IsValid() && (Now - State.LastSeenTime) <= 6.0f;
        const bool bInCombat = bHasLineOfSight || bStickyCombat;
        SetBoolProperty(Trooper, TEXT("PlayerSeen"), bInCombat);
        SetObjectProperty(Trooper, TEXT("TargetActor"), bInCombat ? State.Target.Get() : nullptr);

        const EPathFollowingStatus::Type MoveStatus = AIController ? AIController->GetMoveStatus() : EPathFollowingStatus::Idle;
        const bool bVelocityMoving = Character->GetVelocity().SizeSquared2D() > FMath::Square(10.0f);
        if (State.bMoveInProgress && MoveStatus == EPathFollowingStatus::Idle && !bVelocityMoving)
        {
            State.bMoveInProgress = false;
            State.ArrivalSettleUntil = Now + FMath::RandRange(0.9f, 1.6f);
            State.NextShotTime = State.ArrivalSettleUntil;
            State.BurstsBeforeMove = FMath::RandRange(2, 3);
            State.NextMoveTime = Now + FMath::RandRange(2.4f, 3.8f);
        }
        SetBoolProperty(Trooper, TEXT("bIsMoving"), State.bMoveInProgress);

        if (bInCombat)
        {
            Movement->MaxWalkSpeed = bHeavyTrooper ? 120.0f : (State.bMoveInProgress ? 320.0f : 430.0f);
            Movement->bUseControllerDesiredRotation = bHeavyTrooper;
            Movement->bOrientRotationToMovement = bHeavyTrooper ? false : State.bMoveInProgress;
            Character->bUseControllerRotationYaw = false;
            SetBoolProperty(Trooper, TEXT("bWeaponRaised"), true);

            if (!State.bWasInCombat)
            {
                State.ShotsRemaining = bHeavyTrooper ? MAX_int32 : FMath::RandRange(4, 7);
                State.NextShotTime = Now + (bHeavyTrooper ? 0.25f : FMath::RandRange(0.45f, 0.85f));
                State.NextMoveTime = Now + (bHeavyTrooper ? 0.2f : FMath::RandRange(2.0f, 3.2f));
                State.BurstEndTime = bHeavyTrooper ? Now + FMath::RandRange(6.0f, 10.0f) : Now + 1.8f;
                State.ArrivalSettleUntil = Now + 0.45f;
                State.BurstsBeforeMove = FMath::RandRange(2, 3);
                State.bMoveInProgress = false;
                State.bPlayedRaise = false;
            }

            if (!State.bPlayedRaise)
            {
                if (UAnimMontage* RaiseMontage = LoadFactionMontage(
                    bRepublicSoldier,
                    bHeavyTrooper,
                    TEXT("/Game/EndarSpire/Characters/Sith/Animations/Rifle_Down_To_Aim_Sith_Montage.Rifle_Down_To_Aim_Sith_Montage"),
                    TEXT("/Game/EndarSpire/Characters/RepublicSoldier/Animations/RT_Republic_Rifle_Down_To_Aim_Montage.RT_Republic_Rifle_Down_To_Aim_Montage"),
                    TEXT("/Game/EndarSpire/Characters/HeavySithTrooper/Animations/RT_Heavy_Rifle_Down_To_Aim_Montage.RT_Heavy_Rifle_Down_To_Aim_Montage")))
                {
                    Character->PlayAnimMontage(RaiseMontage, 1.0f);
                }
                State.bPlayedRaise = true;
            }

            if (AIController && State.Target.IsValid() && (bHeavyTrooper || !State.bMoveInProgress))
            {
                AIController->SetFocus(State.Target.Get());
            }
            else if (AIController && State.bMoveInProgress)
            {
                AIController->ClearFocus(EAIFocusPriority::Gameplay);
            }

            const FVector AimLocation = State.Target.IsValid() ? State.Target->GetActorLocation() : TargetLocation;
            FVector LookDirection = AimLocation - TrooperLocation;
            LookDirection.Z = 0.0f;
            if ((bHeavyTrooper || !State.bMoveInProgress) && !LookDirection.IsNearlyZero())
            {
                const FRotator DesiredRotation = LookDirection.Rotation();
                Trooper->SetActorRotation(FMath::RInterpTo(Trooper->GetActorRotation(), DesiredRotation, DeltaTime, 8.0f));
            }

            if (bHeavyTrooper && AIController && State.Target.IsValid() && Now >= State.NextMoveTime)
            {
                SetBoolProperty(Trooper, TEXT("bIsMoving"), true);
                State.bMoveInProgress = true;
                AIController->MoveToLocation(State.Target->GetActorLocation(), 160.0f, true, true, true, false, nullptr, true);
                State.NextMoveTime = Now + 0.4f;
            }
            else if (!bHeavyTrooper && bEnableNativeSithRepositioning && AIController && NavSystem && !State.bMoveInProgress && Now >= State.NextMoveTime)
            {
                if (NavQueriesThisDirectorTick >= MaxNavQueriesPerDirectorTick)
                {
                    State.NextMoveTime = Now + FMath::RandRange(0.08f, 0.25f);
                }
                else
                {
                    ++NavQueriesThisDirectorTick;

                    const FVector ToTarget = (AimLocation - TrooperLocation).GetSafeNormal2D();
                    FVector DesiredMove = TrooperLocation;
                    float SearchRadius = FMath::Clamp(CombatMoveRadius * 0.35f, 120.0f, 220.0f);

                    if (DistanceToTarget < MinEngagementDistance && !ToTarget.IsNearlyZero())
                    {
                        const FVector AwayFromPlayer = -ToTarget;
                        DesiredMove = TrooperLocation + AwayFromPlayer * FMath::RandRange(260.0f, 420.0f);
                        SearchRadius = 140.0f;
                    }
                    else if (VisibleTarget)
                    {
                        const FVector StrafeDirection = FVector::CrossProduct(FVector::UpVector, ToTarget).GetSafeNormal2D();
                        const float Side = FMath::RandBool() ? 1.0f : -1.0f;
                        const float StrafeDistance = FMath::RandRange(240.0f, 380.0f);
                        const float DepthOffset = FMath::RandRange(-80.0f, 120.0f);
                        DesiredMove = TrooperLocation + (StrafeDirection * Side * StrafeDistance) - (ToTarget * DepthOffset);
                    }

                    FNavLocation ProjectedLocation;
                    bool bHasMoveLocation = NavSystem->GetRandomReachablePointInRadius(DesiredMove, SearchRadius, ProjectedLocation);
                    if (!bHasMoveLocation)
                    {
                        bHasMoveLocation = NavSystem->GetRandomReachablePointInRadius(TrooperLocation, 600.0f, ProjectedLocation);
                    }

                    if (bHasMoveLocation)
                    {
                        SetBoolProperty(Trooper, TEXT("IsShooting?"), false);
                        SetBoolProperty(Trooper, TEXT("bIsMoving"), true);
                        ClearTimerHandleProperty(Trooper, TEXT("BurstTimerHandle"));
                        // During repositioning, face movement for stable locomotion.
                        // The director reacquires aim after arrival before firing.
                        AIController->MoveToLocation(ProjectedLocation.Location, 120.0f, true, true, true, false, nullptr, true);
                        State.bMoveInProgress = true;
                        State.NextMoveTime = Now + FMath::RandRange(CombatMoveInterval, CombatMoveInterval * 1.75f);
                        State.NextShotTime = BIG_NUMBER;
                    }
                }
            }

            if ((bHeavyTrooper || !State.bMoveInProgress)
                && Now >= State.ArrivalSettleUntil
                && bHasLineOfSight
                && DistanceToTarget <= (bHeavyTrooper ? 3600.0f : 2600.0f)
                && Now >= State.NextShotTime)
            {
                SetBoolProperty(Trooper, TEXT("IsShooting?"), true);
                SetIntProperty(Trooper, TEXT("BurstShots"), bHeavyTrooper ? 0 : FMath::Max(0, 7 - State.ShotsRemaining));

                if (UAnimMontage* FireMontage = LoadFactionMontage(
                    bRepublicSoldier,
                    bHeavyTrooper,
                    TEXT("/Game/EndarSpire/Characters/Sith/Animations/A_Sith_Fire_Rifle_Montage.A_Sith_Fire_Rifle_Montage"),
                    TEXT("/Game/EndarSpire/Characters/RepublicSoldier/Animations/RT_Republic_Fire_Rifle_Montage.RT_Republic_Fire_Rifle_Montage"),
                    TEXT("/Game/EndarSpire/Characters/HeavySithTrooper/Animations/RT_Heavy_Fire_Rifle_Montage.RT_Heavy_Fire_Rifle_Montage")))
                {
                    Character->PlayAnimMontage(FireMontage, 1.15f);
                }
                CallBlueprintEvent(Trooper, TEXT("FireOneShot"));

                if (bHeavyTrooper)
                {
                    if (Now >= State.BurstEndTime)
                    {
                        SetBoolProperty(Trooper, TEXT("IsShooting?"), false);
                        State.NextShotTime = Now + 0.75f;
                        State.BurstEndTime = State.NextShotTime + FMath::RandRange(6.0f, 10.0f);
                    }
                    else
                    {
                        State.NextShotTime = Now + 0.08f;
                    }
                }
                else
                {
                    --State.ShotsRemaining;
                    if (State.ShotsRemaining <= 0)
                    {
                        SetBoolProperty(Trooper, TEXT("IsShooting?"), false);
                        State.ShotsRemaining = FMath::RandRange(4, 8);
                        State.NextShotTime = Now + FMath::RandRange(0.65f, 1.1f);
                        State.BurstEndTime = State.NextShotTime + 1.5f;
                        --State.BurstsBeforeMove;
                        if (State.BurstsBeforeMove <= 0)
                        {
                            State.NextMoveTime = Now + FMath::RandRange(1.5f, 2.5f);
                            State.BurstsBeforeMove = FMath::RandRange(2, 3);
                        }
                    }
                    else
                    {
                        State.NextShotTime = Now + FMath::RandRange(0.14f, 0.24f);
                        State.BurstEndTime = Now + 0.35f;
                    }
                }
            }
            else if (Now > State.BurstEndTime)
            {
                SetBoolProperty(Trooper, TEXT("IsShooting?"), false);
            }
        }
        else
        {
            if (State.bWasInCombat)
            {
                if (UAnimMontage* LowerMontage = LoadFactionMontage(
                    bRepublicSoldier,
                    bHeavyTrooper,
                    TEXT("/Game/EndarSpire/Characters/Sith/Animations/Rifle_Aim_To_Down_Sith_Montage.Rifle_Aim_To_Down_Sith_Montage"),
                    TEXT("/Game/EndarSpire/Characters/RepublicSoldier/Animations/RT_Republic_Rifle_Aim_To_Down_Montage.RT_Republic_Rifle_Aim_To_Down_Montage"),
                    TEXT("/Game/EndarSpire/Characters/HeavySithTrooper/Animations/RT_Heavy_Rifle_Aim_To_Down_Montage.RT_Heavy_Rifle_Aim_To_Down_Montage")))
                {
                    Character->PlayAnimMontage(LowerMontage, 1.0f);
                }
            }

            SetBoolProperty(Trooper, TEXT("bWeaponRaised"), false);
            SetBoolProperty(Trooper, TEXT("IsShooting?"), false);
            SetBoolProperty(Trooper, TEXT("bIsMoving"), State.bMoveInProgress);
            State.Target.Reset();
            State.ShotsRemaining = 0;
            State.bPlayedRaise = false;

            Movement->MaxWalkSpeed = bHeavyTrooper ? 120.0f : 260.0f;
            Movement->bOrientRotationToMovement = true;

            if (AIController && NavSystem && !State.bMoveInProgress && Now >= State.NextMoveTime)
            {
                if (PlayerPawn && DistanceToPlayer > TickOptimizationDistance)
                {
                    State.NextMoveTime = Now + FMath::RandRange(IdleMoveInterval, IdleMoveInterval * 2.0f);
                }
                else if (NavQueriesThisDirectorTick >= MaxNavQueriesPerDirectorTick)
                {
                    State.NextMoveTime = Now + FMath::RandRange(0.1f, 0.35f);
                }
                else
                {
                    ++NavQueriesThisDirectorTick;

                    FNavLocation WanderLocation;
                    if (NavSystem->GetRandomReachablePointInRadius(State.SpawnLocation, PatrolRadius, WanderLocation))
                    {
                        AIController->MoveToLocation(WanderLocation.Location, 80.0f, true, true, true, false, nullptr, true);
                        State.bMoveInProgress = true;
                        SetBoolProperty(Trooper, TEXT("bIsMoving"), true);
                    }
                    State.NextMoveTime = Now + FMath::RandRange(IdleMoveInterval * 0.5f, IdleMoveInterval * 1.35f);
                }
            }
        }

        const FVector Velocity = Character->GetVelocity();
        const float RawSpeed = Velocity.Size2D();
        // Repositioning now faces movement, so feed the blend space a stable forward-run
        // direction instead of noisy per-frame steering angles.
        const float RawDirection = State.bMoveInProgress ? 0.0f : CalculateLocalMoveDirectionDegrees(Trooper, Velocity);
        if (State.bMoveInProgress)
        {
            State.SmoothedAnimSpeed = RawSpeed;
            State.SmoothedAnimDirection = 0.0f;
        }
        else
        {
            State.SmoothedAnimSpeed = FMath::FInterpTo(State.SmoothedAnimSpeed, RawSpeed, DeltaTime, 12.0f);
            const float DirectionDelta = FMath::FindDeltaAngleDegrees(State.SmoothedAnimDirection, RawDirection);
            State.SmoothedAnimDirection = FMath::UnwindDegrees(
                State.SmoothedAnimDirection + FMath::Clamp(DirectionDelta, -360.0f * DeltaTime, 360.0f * DeltaTime));
        }
        if (USkeletalMeshComponent* Mesh = Character->GetMesh())
        {
            if (UAnimInstance* AnimInstance = Mesh->GetAnimInstance())
            {
                SetRealProperty(AnimInstance, TEXT("Speed"), State.SmoothedAnimSpeed);
                SetRealProperty(AnimInstance, TEXT("Direction"), State.SmoothedAnimDirection);
                SetBoolProperty(AnimInstance, TEXT("IsAiming"), bInCombat && (bHeavyTrooper || !State.bMoveInProgress));
                SetBoolProperty(AnimInstance, TEXT("IsShooting"), GetBoolProperty(Trooper, TEXT("IsShooting?")));
                SetBoolProperty(AnimInstance, TEXT("bIsShooting"), GetBoolProperty(Trooper, TEXT("IsShooting?")));
                SetBoolProperty(AnimInstance, TEXT("IsDead"), bIsDead);
            }
        }

        State.bWasInCombat = bInCombat;
    }

    for (auto It = SithCombatStates.CreateIterator(); It; ++It)
    {
        if (!It.Key().IsValid() || !SeenThisTick.Contains(It.Key()))
        {
            It.RemoveCurrent();
        }
    }

    for (auto It = DarkJediBossStates.CreateIterator(); It; ++It)
    {
        if (!It.Key().IsValid() || !SeenDarkJediBossesThisTick.Contains(It.Key()))
        {
            It.RemoveCurrent();
        }
    }

    return true;
}

// Start the MCP server
void UUnrealMCPBridge::StartServer()
{
    if (bIsRunning)
    {
        UE_LOG(LogTemp, Warning, TEXT("UnrealMCPBridge: Server is already running"));
        return;
    }

    // Create socket subsystem
    ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
    if (!SocketSubsystem)
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to get socket subsystem"));
        return;
    }

    // Create listener socket
    TSharedPtr<FSocket> NewListenerSocket = MakeShareable(SocketSubsystem->CreateSocket(NAME_Stream, TEXT("UnrealMCPListener"), false));
    if (!NewListenerSocket.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to create listener socket"));
        return;
    }

    // Allow address reuse for quick restarts
    NewListenerSocket->SetReuseAddr(true);
    NewListenerSocket->SetNonBlocking(true);

    // Bind to address
    FIPv4Endpoint Endpoint(ServerAddress, Port);
    if (!NewListenerSocket->Bind(*Endpoint.ToInternetAddr()))
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to bind listener socket to %s:%d"), *ServerAddress.ToString(), Port);
        return;
    }

    // Start listening
    if (!NewListenerSocket->Listen(5))
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to start listening"));
        return;
    }

    ListenerSocket = NewListenerSocket;
    bIsRunning = true;
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Server started on %s:%d"), *ServerAddress.ToString(), Port);

    // Start server thread
    ServerThread = FRunnableThread::Create(
        new FMCPServerRunnable(this, ListenerSocket),
        TEXT("UnrealMCPServerThread"),
        0, TPri_Normal
    );

    if (!ServerThread)
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to create server thread"));
        StopServer();
        return;
    }
}

// Stop the MCP server
void UUnrealMCPBridge::StopServer()
{
    if (!bIsRunning)
    {
        return;
    }

    bIsRunning = false;

    // Clean up thread
    if (ServerThread)
    {
        ServerThread->Kill(true);
        delete ServerThread;
        ServerThread = nullptr;
    }

    // Close sockets
    if (ConnectionSocket.IsValid())
    {
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ConnectionSocket.Get());
        ConnectionSocket.Reset();
    }

    if (ListenerSocket.IsValid())
    {
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ListenerSocket.Get());
        ListenerSocket.Reset();
    }

    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Server stopped"));
}

// Execute a command received from a client
FString UUnrealMCPBridge::ExecuteCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Executing command: %s"), *CommandType);

    // Create a promise to wait for the result
    TPromise<FString> Promise;
    TFuture<FString> Future = Promise.GetFuture();

    // Queue execution on Game Thread
    AsyncTask(ENamedThreads::GameThread, [this, CommandType, Params, Promise = MoveTemp(Promise)]() mutable
    {
        TSharedPtr<FJsonObject> ResponseJson = MakeShareable(new FJsonObject);

        // ---------------------------------------------------------------
        // CRASH-006 guard — push the editor's autosave timer back so that
        // autosave cannot fire in the middle of a multi-step bridge mutation
        // (e.g. add_component → set Sound → set bAutoActivate → set Volume
        // → compile → save). Each command resets the clock; as long as
        // commands keep flowing, the next autosave is always >1 interval
        // away. See FUnrealMCPCommonUtils::DeferAutoSave for the full
        // crash analysis (UECC-Windows-C418EA37 — half-mutated BP saved
        // mid-chain → AV in CoreUObject finalize).
        //
        // Cheap (one float store); safe even if GUnrealEd is not ready.
        // ---------------------------------------------------------------
        FUnrealMCPCommonUtils::DeferAutoSave();

        // ---------------------------------------------------------------
        // Pre-command diagnostic logging so we can trace every MCP action
        // even if Unreal crashes before the command completes.
        // These lines appear in Saved/Logs/UnrealEditor.log.
        // ---------------------------------------------------------------
        UE_LOG(LogMCP, Display, TEXT("[MCP] >>> BEGIN command: '%s'"), *CommandType);

        // Serialize params for debugging (keep it short – first 512 chars)
        {
            FString ParamsStr;
            TSharedRef<TJsonWriter<>> PWriter = TJsonWriterFactory<>::Create(&ParamsStr);
            FJsonSerializer::Serialize(Params.ToSharedRef(), PWriter);
            if (ParamsStr.Len() > 512)
            {
                ParamsStr = ParamsStr.Left(509) + TEXT("...");
            }
            UE_LOG(LogMCP, Display, TEXT("[MCP]   Params: %s"), *ParamsStr);
        }

        const double CommandStartTime = FPlatformTime::Seconds();

        try
        {
            TSharedPtr<FJsonObject> ResultJson;

            if (CommandType == TEXT("ping"))
            {
                ResultJson = MakeShareable(new FJsonObject);
                ResultJson->SetStringField(TEXT("message"), TEXT("pong"));
            }
            // Editor Commands (including actor manipulation)
            else if (CommandType == TEXT("get_actors_in_level") ||
                     CommandType == TEXT("get_actor_identity") ||
                     CommandType == TEXT("find_actors_by_name") ||
                     CommandType == TEXT("find_actors_by_class") ||
                     CommandType == TEXT("spawn_actor") ||
                     CommandType == TEXT("create_actor") ||
                     CommandType == TEXT("delete_actor") ||
                     CommandType == TEXT("set_actor_transform") ||
                     CommandType == TEXT("get_actor_properties") ||
                     CommandType == TEXT("set_actor_property") ||
                     CommandType == TEXT("check_blueprint_generated_class") ||
                     CommandType == TEXT("inspect_input_mapping_context") ||
                     CommandType == TEXT("spawn_blueprint_actor") ||
                     CommandType == TEXT("focus_viewport") ||
                     CommandType == TEXT("take_screenshot") ||
                     CommandType == TEXT("wp_load_region") ||
                     CommandType == TEXT("wp_unload_region") ||
                     CommandType == TEXT("wp_create_data_layer") ||
                     CommandType == TEXT("hlod_generate") ||
                     CommandType == TEXT("hlod_assign_layer") ||
                     CommandType == TEXT("exec_python"))
            {
                if (!EditorCommands.IsValid())
                {
                    UE_LOG(LogMCP, Warning, TEXT("[MCP] Editor command handler was invalid; recreating before '%s'"), *CommandType);
                    EditorCommands = MakeShared<FUnrealMCPEditorCommands>();
                }
                if (EditorCommands.IsValid())
                {
                    ResultJson = EditorCommands->HandleCommand(CommandType, Params);
                }
                else
                {
                    ResultJson = MakeShareable(new FJsonObject);
                    ResultJson->SetBoolField(TEXT("success"), false);
                    ResultJson->SetStringField(TEXT("error"), TEXT("Editor command handler is not initialized"));
                    ResultJson->SetStringField(TEXT("command"), CommandType);
                }
            }
            // Blueprint Commands
            else if (CommandType == TEXT("create_blueprint") ||
                     CommandType == TEXT("add_component_to_blueprint") ||
                     CommandType == TEXT("bp_copy_component") ||
                     CommandType == TEXT("set_component_property") ||
                     CommandType == TEXT("set_physics_properties") ||
                     CommandType == TEXT("compile_blueprint") ||
                     CommandType == TEXT("save_blueprint") ||
                     CommandType == TEXT("set_blueprint_property") ||
                     CommandType == TEXT("set_static_mesh_properties") ||
                     CommandType == TEXT("set_skeletal_mesh_properties") ||
                     CommandType == TEXT("set_component_parent_socket") ||
                     CommandType == TEXT("add_skeleton_socket") ||
                     CommandType == TEXT("set_pawn_properties") ||
                     CommandType == TEXT("set_blueprint_ai_controller"))
            {
                ResultJson = BlueprintCommands->HandleCommand(CommandType, Params);
            }
            // Blueprint Node Commands
            else if (CommandType == TEXT("get_blueprint_nodes") ||
                     CommandType == TEXT("find_blueprint_nodes") ||
                     CommandType == TEXT("get_blueprint_graphs") ||
                     CommandType == TEXT("get_node_by_id") ||
                     CommandType == TEXT("bp_add_node") ||
                     CommandType == TEXT("bp_inspect_node") ||
                     CommandType == TEXT("bp_connect_pins") ||
                     CommandType == TEXT("bp_get_graph_summary") ||
                     CommandType == TEXT("connect_blueprint_nodes") ||
                     CommandType == TEXT("disconnect_blueprint_nodes") ||
                     CommandType == TEXT("delete_blueprint_node") ||
                     CommandType == TEXT("set_node_pin_value") ||
                     CommandType == TEXT("add_blueprint_event_node") ||
                     CommandType == TEXT("add_blueprint_custom_event_node") ||
                     CommandType == TEXT("set_spawn_actor_class") ||
                     CommandType == TEXT("add_blueprint_function_node") ||
                     CommandType == TEXT("add_blueprint_variable_get_node") ||
                     CommandType == TEXT("add_blueprint_variable_set_node") ||
                     CommandType == TEXT("add_blueprint_variable") ||
                     CommandType == TEXT("add_blueprint_input_action_node") ||
                     CommandType == TEXT("add_blueprint_enhanced_input_action_node") ||
                     CommandType == TEXT("add_blueprint_self_reference") ||
                     CommandType == TEXT("add_blueprint_get_self_component_reference") ||
                     CommandType == TEXT("add_blueprint_get_component_node") ||
                     CommandType == TEXT("add_blueprint_set_component_property") ||
                     CommandType == TEXT("add_blueprint_branch_node") ||
                     CommandType == TEXT("add_blueprint_cast_node") ||
                     // Phase 2: structural nodes (L-012)
                     CommandType == TEXT("add_blueprint_for_loop_node") ||
                     CommandType == TEXT("add_blueprint_for_loop_with_break_node") ||
                     CommandType == TEXT("add_blueprint_for_each_loop_node") ||
                     CommandType == TEXT("add_blueprint_sequence_node") ||
                     CommandType == TEXT("add_blueprint_do_once_node") ||
                     CommandType == TEXT("add_blueprint_gate_node") ||
                     CommandType == TEXT("add_blueprint_flip_flop_node") ||
                     CommandType == TEXT("add_blueprint_switch_on_int_node") ||
                     CommandType == TEXT("add_blueprint_spawn_actor_node") ||
                     // Phase 2: comment + reposition (L-018, L-019)
                     CommandType == TEXT("add_blueprint_comment_node") ||
                     CommandType == TEXT("create_comment_box") ||
                     CommandType == TEXT("rename_blueprint_comment_node") ||
                     CommandType == TEXT("move_blueprint_node") ||
                     // Phase 3: variable defaults (L-013)
                     CommandType == TEXT("get_blueprint_variable_defaults") ||
                     CommandType == TEXT("set_blueprint_variable_default") ||
                     // Phase 4: component inspection (L-020)
                     CommandType == TEXT("get_blueprint_components") ||
                     // Phase 5: NavMesh (L-014)
                     CommandType == TEXT("setup_navmesh") ||
                     // Phase 6: variable + function introspection
                     CommandType == TEXT("get_blueprint_variables") ||
                     CommandType == TEXT("get_blueprint_functions") ||
                     CommandType == TEXT("add_blueprint_function_with_pins") ||
                     // BUG-030: per-component ComponentBoundEvent
                     CommandType == TEXT("add_component_overlap_event") ||
                     CommandType == TEXT("add_component_event_node") ||
                     // BUG-035: SCS node inspector
                     CommandType == TEXT("get_scs_nodes"))
            {
                ResultJson = BlueprintNodeCommands->HandleCommand(CommandType, Params);
            }
            // Project Commands
            else if (CommandType == TEXT("create_input_mapping"))
            {
                ResultJson = ProjectCommands->HandleCommand(CommandType, Params);
            }
            // UMG Commands
            else if (CommandType == TEXT("create_umg_widget_blueprint") ||
                     CommandType == TEXT("add_text_block_to_widget") ||
                     CommandType == TEXT("add_button_to_widget") ||
                     CommandType == TEXT("bind_widget_event") ||
                     CommandType == TEXT("set_text_block_binding") ||
                     CommandType == TEXT("add_widget_to_viewport") ||
                     CommandType == TEXT("widget_add_child") ||
                     CommandType == TEXT("widget_set_property") ||
                     CommandType == TEXT("widget_set_anchor") ||
                     CommandType == TEXT("widget_get_children") ||
                     CommandType == TEXT("umg_add_widget_binding"))
            {
                ResultJson = UMGCommands->HandleCommand(CommandType, Params);
            }
            // Gameplay Ability System Commands
            else if (CommandType == TEXT("gas_create_ability") ||
                     CommandType == TEXT("gas_create_gameplay_effect") ||
                     CommandType == TEXT("gas_create_gameplay_cue") ||
                     CommandType == TEXT("gas_create_attribute_set") ||
                     CommandType == TEXT("gas_grant_ability") ||
                     CommandType == TEXT("gas_apply_effect") ||
                     CommandType == TEXT("gas_add_tag") ||
                     CommandType == TEXT("gas_create_ability_task_node"))
            {
                static TSharedPtr<FUnrealMCPGASCommands> GASCommands;
                if (!GASCommands.IsValid())
                {
                    GASCommands = MakeShared<FUnrealMCPGASCommands>();
                }
                ResultJson = GASCommands->HandleCommand(CommandType, Params);
            }
            // Networking & Replication Commands
            else if (CommandType == TEXT("net_set_property_replicated") ||
                     CommandType == TEXT("net_set_function_rpc") ||
                     CommandType == TEXT("net_set_replication_condition") ||
                     CommandType == TEXT("net_add_replicated_component") ||
                     CommandType == TEXT("net_set_role_override") ||
                     CommandType == TEXT("net_get_replication_graph_state"))
            {
                static TSharedPtr<FUnrealMCPNetworkCommands> NetworkCommands;
                if (!NetworkCommands.IsValid())
                {
                    NetworkCommands = MakeShared<FUnrealMCPNetworkCommands>();
                }
                ResultJson = NetworkCommands->HandleCommand(CommandType, Params);
            }
            // MetaSounds & Audio Commands
            else if (CommandType == TEXT("metasound_create_source") ||
                     CommandType == TEXT("metasound_create_patch") ||
                     CommandType == TEXT("metasound_add_node") ||
                     CommandType == TEXT("metasound_connect_pins") ||
                     CommandType == TEXT("metasound_compile") ||
                     CommandType == TEXT("audio_create_soundcue") ||
                     CommandType == TEXT("audio_create_attenuation") ||
                     CommandType == TEXT("audio_create_concurrency"))
            {
                static TSharedPtr<FUnrealMCPAudioCommands> AudioCommands;
                if (!AudioCommands.IsValid())
                {
                    AudioCommands = MakeShared<FUnrealMCPAudioCommands>();
                }
                ResultJson = AudioCommands->HandleCommand(CommandType, Params);
            }
            // Geometry Script / Modeling Commands
            else if (CommandType == TEXT("geom_create_dynamic_mesh") ||
                     CommandType == TEXT("geom_boolean_op") ||
                     CommandType == TEXT("geom_extrude") ||
                     CommandType == TEXT("geom_remesh") ||
                     CommandType == TEXT("geom_uv_unwrap") ||
                     CommandType == TEXT("geom_bake_to_static_mesh") ||
                     CommandType == TEXT("geom_apply_displacement"))
            {
                static TSharedPtr<FUnrealMCPGeometryCommands> GeometryCommands;
                if (!GeometryCommands.IsValid())
                {
                    GeometryCommands = MakeShared<FUnrealMCPGeometryCommands>();
                }
                ResultJson = GeometryCommands->HandleCommand(CommandType, Params);
            }
            // MassEntity / StateTree / SmartObject Commands
            else if (CommandType == TEXT("mass_create_entity_config") ||
                     CommandType == TEXT("mass_add_trait") ||
                     CommandType == TEXT("mass_inspect_entity_config") ||
                     CommandType == TEXT("statetree_create") ||
                     CommandType == TEXT("statetree_add_state") ||
                     CommandType == TEXT("statetree_inspect") ||
                     CommandType == TEXT("smartobject_create_definition") ||
                     CommandType == TEXT("smartobject_add_slot") ||
                     CommandType == TEXT("smartobject_inspect_definition"))
            {
                static TSharedPtr<FUnrealMCPMassCommands> MassCommands;
                if (!MassCommands.IsValid())
                {
                    MassCommands = MakeShared<FUnrealMCPMassCommands>();
                }
                ResultJson = MassCommands->HandleCommand(CommandType, Params);
            }
            // Chaos destruction / cloth Commands
            else if (CommandType == TEXT("chaos_create_solver_actor") ||
                     CommandType == TEXT("chaos_configure_solver_actor") ||
                     CommandType == TEXT("chaos_inspect_geometry_collection") ||
                     CommandType == TEXT("chaos_configure_geometry_collection") ||
                     CommandType == TEXT("chaos_configure_cloth_component"))
            {
                static TSharedPtr<FUnrealMCPChaosCommands> ChaosCommands;
                if (!ChaosCommands.IsValid())
                {
                    ChaosCommands = MakeShared<FUnrealMCPChaosCommands>();
                }
                ResultJson = ChaosCommands->HandleCommand(CommandType, Params);
            }
            // Movie Render Queue Commands
            else if (CommandType == TEXT("mrq_create_job") ||
                     CommandType == TEXT("mrq_add_render_setting") ||
                     CommandType == TEXT("mrq_render_queue"))
            {
                static TSharedPtr<FUnrealMCPMRQCommands> MRQCommands;
                if (!MRQCommands.IsValid())
                {
                    MRQCommands = MakeShared<FUnrealMCPMRQCommands>();
                }
                ResultJson = MRQCommands->HandleCommand(CommandType, Params);
            }
            // Online Subsystem / EOS Commands
            else if (CommandType == TEXT("online_inspect_config") ||
                     CommandType == TEXT("online_configure_default_subsystem") ||
                     CommandType == TEXT("online_create_eos_artifact_config") ||
                     CommandType == TEXT("online_configure_eos_sessions"))
            {
                static TSharedPtr<FUnrealMCPOnlineCommands> OnlineCommands;
                if (!OnlineCommands.IsValid())
                {
                    OnlineCommands = MakeShared<FUnrealMCPOnlineCommands>();
                }
                ResultJson = OnlineCommands->HandleCommand(CommandType, Params);
            }
            // Pixel Streaming / Remote Access Commands
            else if (CommandType == TEXT("pixelstream_inspect_config") ||
                     CommandType == TEXT("pixelstream_configure_plugin") ||
                     CommandType == TEXT("pixelstream_configure_streamer") ||
                     CommandType == TEXT("pixelstream_create_launch_profile"))
            {
                static TSharedPtr<FUnrealMCPPixelStreamingCommands> PixelStreamingCommands;
                if (!PixelStreamingCommands.IsValid())
                {
                    PixelStreamingCommands = MakeShared<FUnrealMCPPixelStreamingCommands>();
                }
                ResultJson = PixelStreamingCommands->HandleCommand(CommandType, Params);
            }
            // Motion Matching / Pose Search / Chooser Commands
            else if (CommandType == TEXT("motion_create_pose_search_schema") ||
                     CommandType == TEXT("motion_create_pose_search_database") ||
                     CommandType == TEXT("motion_add_database_sequence") ||
                     CommandType == TEXT("motion_inspect_pose_search_asset") ||
                     CommandType == TEXT("chooser_create_table") ||
                     CommandType == TEXT("chooser_add_asset_row") ||
                     CommandType == TEXT("chooser_inspect_table"))
            {
                static TSharedPtr<FUnrealMCPMotionCommands> MotionCommands;
                if (!MotionCommands.IsValid())
                {
                    MotionCommands = MakeShared<FUnrealMCPMotionCommands>();
                }
                ResultJson = MotionCommands->HandleCommand(CommandType, Params);
            }
            // Extended Commands ? all 283 tools from Blueprints Visual Scripting for UE5
            else if (ExtendedCommands.IsValid())
            {
                TSharedPtr<FJsonObject> ExtResult = ExtendedCommands->HandleCommand(CommandType, Params);
                if (ExtResult.IsValid())
                {
                    ResultJson = ExtResult;
                }
                else
                {
                    ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                    ResponseJson->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));
                    FString ResultString;
                    TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
                        TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&ResultString);
                    FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
                    Promise.SetValue(ResultString);
                    return;
                }
            }
            else
            {
                ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                ResponseJson->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));

                FString ResultString;
                TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
                    TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&ResultString);
                FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
                Promise.SetValue(ResultString);
                return;
            }

            // Check if the result contains an error
            bool bSuccess = true;
            FString ErrorMessage;

            if (ResultJson->HasField(TEXT("success")))
            {
                bSuccess = ResultJson->GetBoolField(TEXT("success"));
                if (!bSuccess && ResultJson->HasField(TEXT("error")))
                {
                    ErrorMessage = ResultJson->GetStringField(TEXT("error"));
                }
            }

            if (bSuccess)
            {
                // Set success status and include the result
                ResponseJson->SetStringField(TEXT("status"), TEXT("success"));
                ResponseJson->SetObjectField(TEXT("result"), ResultJson);
            }
            else
            {
                // Set error status and include the error message
                ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                ResponseJson->SetStringField(TEXT("error"), ErrorMessage);
            }

            const double ElapsedMs = (FPlatformTime::Seconds() - CommandStartTime) * 1000.0;
            UE_LOG(LogMCP, Display, TEXT("[MCP] <<< END command: '%s' | success=%d | %.1f ms"),
                *CommandType, bSuccess ? 1 : 0, ElapsedMs);
        }
        catch (const std::exception& e)
        {
            const double ElapsedMs = (FPlatformTime::Seconds() - CommandStartTime) * 1000.0;
            UE_LOG(LogMCP, Error, TEXT("[MCP] <<< EXCEPTION in command '%s' after %.1f ms: %s"),
                *CommandType, ElapsedMs, UTF8_TO_TCHAR(e.what()));
            ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
            ResponseJson->SetStringField(TEXT("error"), UTF8_TO_TCHAR(e.what()));
        }
        catch (...)
        {
            // This catch block handles non-std exceptions (e.g. SEH exceptions
            // on Windows that have been translated by _set_se_translator).
            // Note: raw hardware exceptions (EXCEPTION_ACCESS_VIOLATION) do NOT
            // reach here in a normal UE build – they are caught by the engine's
            // crash handler.  But structured exceptions translated to C++
            // exceptions via _set_se_translator WILL land here.
            const double ElapsedMs = (FPlatformTime::Seconds() - CommandStartTime) * 1000.0;
            UE_LOG(LogMCP, Error, TEXT("[MCP] <<< UNKNOWN EXCEPTION in command '%s' after %.1f ms"),
                *CommandType, ElapsedMs);
            ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
            ResponseJson->SetStringField(TEXT("error"),
                FString::Printf(TEXT("Unknown exception in command '%s'"), *CommandType));
        }

        // Use condensed (single-line) JSON so the newline-delimited socket protocol
        // is never confused by embedded newlines inside large actor arrays, etc.
        FString ResultString;
        TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
            TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&ResultString);
        FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
        Promise.SetValue(ResultString);
    });

    // -----------------------------------------------------------------------
    // Per-command GameThread timeout budget.
    //
    // Background:
    //   Without a timeout, Future.Get() blocks the TCP receiver thread forever
    //   when the GameThread handler stalls (AddMemberVariable on 8k-asset project,
    //   StaticLoadObject on cold asset, BP compile with many errors, etc.).
    //   The stalled TCP thread holds the socket; Python times out after 30/90 s
    //   and reconnects, but its AsyncTask is queued BEHIND the still-running
    //   stalled task — causing every subsequent command to wait in line.
    //
    // Per-command budgets:
    //   • compile_blueprint / save_blueprint / exec_python:
    //       80 s  — these legitimately run long; give them the full Python budget.
    //   • add_blueprint_variable / get_blueprint_* / add_component_to_blueprint:
    //       80 s  — AddMemberVariable + MarkStructurallyModified can notify the
    //               ContentBrowser which is expensive on large projects.
    //               FindBlueprint AR scan is slow on cold cache.
    //   • Everything else: 24 s  — frees the socket before Python's 30 s fires.
    // -----------------------------------------------------------------------
    double TimeoutSeconds = 24.0;  // default: fast commands
    if (CommandType == TEXT("exec_python"))
    {
        // exec_python tier-3: factory scripts (BehaviorTree, WidgetBlueprint) can
        // run 60-120 s inside UE5. Give a 140 s budget so C++ never cuts them off
        // before they finish. Python has 150 s (see _VERY_SLOW_COMMANDS).
        TimeoutSeconds = 140.0;
    }
    else if (CommandType == TEXT("compile_blueprint") ||
             CommandType == TEXT("save_blueprint")    ||
             CommandType == TEXT("create_blueprint")  ||
             CommandType == TEXT("add_skeleton_socket") ||
             CommandType == TEXT("gas_create_ability") ||
             CommandType == TEXT("gas_create_gameplay_effect") ||
             CommandType == TEXT("gas_create_gameplay_cue") ||
             CommandType == TEXT("gas_create_attribute_set"))
    {
        TimeoutSeconds = 80.0;   // legitimately slow
    }
    else if (CommandType == TEXT("add_blueprint_variable")    ||
             CommandType == TEXT("get_blueprint_variables")   ||
             CommandType == TEXT("get_blueprint_functions")   ||
             CommandType == TEXT("get_blueprint_graphs")      ||
             CommandType == TEXT("add_component_to_blueprint")||
             CommandType == TEXT("bp_copy_component")         ||
             CommandType == TEXT("get_actors_in_level")       ||
             CommandType == TEXT("focus_viewport"))
    {
        TimeoutSeconds = 80.0;   // AR scan + possible notification chain
    }
    else if (CommandType == TEXT("bt_add_selector_wait") ||
             CommandType == TEXT("build_behavior_tree")  ||
             CommandType == TEXT("add_bt_node")          ||
             CommandType == TEXT("bt_get_info")          ||
             CommandType == TEXT("get_bt_graph_info")    ||
             CommandType == TEXT("attach_bt_sub_node"))
    {
        TimeoutSeconds = 80.0;   // BT graph UpdateAsset + SaveAsset can be slow
    }

    const FTimespan WaitTimeout = FTimespan::FromSeconds(TimeoutSeconds);
    const bool bCompleted = Future.WaitFor(WaitTimeout);
    if (!bCompleted)
    {
        // Return a JSON error immediately so the TCP socket is freed and the
        // next command is not blocked behind this stalled GameThread task.
        TSharedPtr<FJsonObject> TimeoutResponse = MakeShareable(new FJsonObject);
        TimeoutResponse->SetStringField(TEXT("status"), TEXT("error"));
        TimeoutResponse->SetStringField(TEXT("error"),
            FString::Printf(TEXT("GameThread timeout after %.0fs for command '%s'. "
                "The operation may still be running in the background. "
                "Possible causes: (1) AddMemberVariable / MarkStructurallyModified "
                "triggered a ContentBrowser/AssetRegistry refresh on a large project "
                "(8k+ assets); (2) StaticLoadObject blocked on an uncached asset; "
                "(3) Blueprint compile with many errors held the compiler lock. "
                "Retry after a few seconds; if persistent, compile+save the Blueprint "
                "first or restart the UE5 editor."),
                TimeoutSeconds, *CommandType));
        FString TimeoutResultString;
        TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> TWriter =
            TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&TimeoutResultString);
        FJsonSerializer::Serialize(TimeoutResponse.ToSharedRef(), TWriter);
        UE_LOG(LogMCP, Error,
            TEXT("[MCP] <<< TIMEOUT: command '%s' did not complete within %.0fs"),
            *CommandType, TimeoutSeconds);
        return TimeoutResultString;
    }
    return Future.Get();
}
