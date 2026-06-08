param(
    [string]$EngineRoot = "",
    [string]$PluginPath = "",
    [string]$PackageDir = "",
    [string]$TargetPlatforms = "Win64"
)

$ErrorActionPreference = "Stop"

function Resolve-RunUat {
    param([string]$Root)

    if ($Root) {
        $Candidate = Join-Path $Root "Engine\Build\BatchFiles\RunUAT.bat"
        if (Test-Path -LiteralPath $Candidate) {
            return (Resolve-Path -LiteralPath $Candidate).Path
        }
        throw "RunUAT.bat was not found under EngineRoot: $Root"
    }

    $DefaultRoots = @(
        "C:\Program Files\Epic Games\UE_5.6",
        "C:\Program Files\Epic Games\UE_5.5",
        "C:\Program Files\Epic Games\UE_5.4"
    )
    foreach ($DefaultRoot in $DefaultRoots) {
        $Candidate = Join-Path $DefaultRoot "Engine\Build\BatchFiles\RunUAT.bat"
        if (Test-Path -LiteralPath $Candidate) {
            return (Resolve-Path -LiteralPath $Candidate).Path
        }
    }

    throw "RunUAT.bat was not found. Pass -EngineRoot, for example -EngineRoot 'C:\Program Files\Epic Games\UE_5.6'."
}

$RepoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
if (-not $PluginPath) {
    $PluginPath = Join-Path $RepoRoot "unreal_plugin\UnrealMCP.uplugin"
}
if (-not (Test-Path -LiteralPath $PluginPath)) {
    throw "Plugin descriptor was not found: $PluginPath"
}
$PluginPath = (Resolve-Path -LiteralPath $PluginPath).Path

if (-not $PackageDir) {
    $PackageDir = "C:\uebuild\UnrealMCPBuild_$(Get-Date -Format yyyyMMdd_HHmmss)"
}
if (Test-Path -LiteralPath $PackageDir) {
    throw "PackageDir already exists; choose a fresh output path: $PackageDir"
}

$RunUat = Resolve-RunUat -Root $EngineRoot
Write-Host "RunUAT: $RunUat"
Write-Host "Plugin: $PluginPath"
Write-Host "Package: $PackageDir"
Write-Host "TargetPlatforms: $TargetPlatforms"

& $RunUat BuildPlugin -Plugin="$PluginPath" -Package="$PackageDir" -TargetPlatforms="$TargetPlatforms" -Rocket
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "BUILD_PACKAGE=$PackageDir"
