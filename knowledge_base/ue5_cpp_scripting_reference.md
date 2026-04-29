# UE5 C++ Scripting Reference
> Sources: Li, Marques/Sherry/Pereira/Fozi, Sapio; synthesized for Unreal-MCP-Ghost.
> Updated: 2026-04-29

## Unreal C++ Model

Unreal C++ is engine-integrated scripting: reflection, garbage collection, modules, UHT-generated metadata, and editor exposure matter as much as ordinary C++ syntax. C++ should define stable gameplay types, replicated authority, reusable components, and performance-critical systems; Blueprints should compose authored behavior and designer-facing defaults.

## Common Specifiers

- `UCLASS(Blueprintable, BlueprintType)`: expose classes to Blueprint creation and variables.
- `USTRUCT(BlueprintType)`: expose value structs to Blueprints and data tables.
- `UENUM(BlueprintType)`: expose enums to Blueprint pins and properties.
- `UPROPERTY(EditAnywhere)`: editable on class defaults and instances.
- `UPROPERTY(EditDefaultsOnly)`: editable on class defaults only.
- `UPROPERTY(EditInstanceOnly)`: editable per placed instance only.
- `UPROPERTY(BlueprintReadOnly)` / `BlueprintReadWrite`: Blueprint access.
- `UPROPERTY(VisibleAnywhere)`: visible but not editable, common for owned components.
- `UPROPERTY(Replicated)` / `ReplicatedUsing=OnRep_X`: network replication.
- `UFUNCTION(BlueprintCallable)`: callable from Blueprint graphs.
- `UFUNCTION(BlueprintPure)`: no exec pins, no state changes.
- `UFUNCTION(BlueprintImplementableEvent)`: C++ declares, Blueprint implements.
- `UFUNCTION(BlueprintNativeEvent)`: C++ default with optional Blueprint override.
- `UFUNCTION(Server/Client/NetMulticast, Reliable/Unreliable)`: RPC declarations.

## Component Constructor Pattern

Create default subobjects in constructors, attach scene components with `SetupAttachment`, keep component pointers as `UPROPERTY(VisibleAnywhere)`, and avoid raw unmanaged UObject pointers. Use `BeginPlay` for runtime initialization that needs world state.

## MCP Plugin Implications

- New plugin commands should return structured JSON errors and avoid silent no-ops.
- Use reflection to validate class/property/function names before invoking editor mutations.
- Prefer narrow C++ helpers for repeated Blueprint graph operations that cannot be expressed safely through Python alone.

## Audit Checklist

- Identify custom C++ classes, Blueprint parents, reflected properties, BlueprintCallable functions, and replication/RPC declarations.
- Flag raw pointers lacking `UPROPERTY`, editor-exposed properties with overly broad edit scope, and networked gameplay implemented only on clients.
