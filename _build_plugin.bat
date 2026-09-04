@echo off
setlocal

set "PLUGIN_PATH=%~1"
if "%PLUGIN_PATH%"=="" set "PLUGIN_PATH=%~dp0unreal_plugin\UnrealMCP.uplugin"

set "PACKAGE_DIR=%~2"
if "%PACKAGE_DIR%"=="" set "PACKAGE_DIR=%~dp0Saved\PluginBuildSmoke\Package"

set "SMOKE_DIR=%~dp0Saved\PluginBuildSmoke"
set "LOCAL_BUILD_LOG=%SMOKE_DIR%\last_build.log"
set "LOCAL_BUILD_RECEIPT=%SMOKE_DIR%\last_build_receipt.json"

set "RUN_UAT=%UE_RUN_UAT%"
if "%RUN_UAT%"=="" set "RUN_UAT=C:\Program Files\Epic Games\UE_5.6\Engine\Build\BatchFiles\RunUAT.bat"

if not exist "%PLUGIN_PATH%" (
    echo Plugin file not found: %PLUGIN_PATH%
    exit /b 2
)

if not exist "%RUN_UAT%" (
    echo Unreal RunUAT.bat not found: %RUN_UAT%
    exit /b 3
)

if not exist "%SMOKE_DIR%" mkdir "%SMOKE_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Continue'; $PluginArg = '-Plugin=' + $env:PLUGIN_PATH; $PackageArg = '-Package=' + $env:PACKAGE_DIR; & $env:RUN_UAT BuildPlugin $PluginArg $PackageArg -TargetPlatforms=Win64 2>&1 | Tee-Object -FilePath $env:LOCAL_BUILD_LOG; exit $LASTEXITCODE"
set "BUILD_EXIT_CODE=%ERRORLEVEL%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ExitCode = [int]$env:BUILD_EXIT_CODE; $Receipt = [ordered]@{ schema = 'unreal_mcp_plugin_build_receipt.v1'; generated_at_utc = (Get-Date).ToUniversalTime().ToString('o'); plugin_path = $env:PLUGIN_PATH; package_dir = $env:PACKAGE_DIR; log_path = $env:LOCAL_BUILD_LOG; run_uat = $env:RUN_UAT; exit_code = $ExitCode; status = $(if ($ExitCode -eq 0) { 'success' } else { 'failed' }); target_platforms = @('Win64') }; $Receipt | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $env:LOCAL_BUILD_RECEIPT"

exit /b %BUILD_EXIT_CODE%
