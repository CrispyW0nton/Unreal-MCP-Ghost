[CmdletBinding()]
param(
    [string]$PythonExe = "python",
    [string]$BindHost = "127.0.0.1",
    [string]$HealthHost = "127.0.0.1",
    [int]$Port = 8000,
    [int]$TimeoutSeconds = 180,
    [string]$ReceiptPath = "Saved\ChatCockpit\last_start_receipt.json"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([System.IO.Path]::IsPathRooted($ReceiptPath)) {
    $ResolvedReceiptPath = $ReceiptPath
} else {
    $ResolvedReceiptPath = Join-Path $RepoRoot $ReceiptPath
}

$BaseUrl = "http://$HealthHost`:$Port"
$HealthUrl = "$BaseUrl/chat/history?limit=1"
$McpEndpoint = "$BaseUrl/sse"
$ServerArgs = @(
    "unreal_mcp_server\unreal_mcp_server.py",
    "--transport", "sse",
    "--mcp-host", $BindHost,
    "--mcp-port", [string]$Port
)

function Test-ChatCockpitReady {
    try {
        $Response = Invoke-WebRequest -UseBasicParsing -Uri $HealthUrl -TimeoutSec 2
        if ($Response.StatusCode -ne 200) {
            return $false
        }
        $Payload = $Response.Content | ConvertFrom-Json
        return ($null -ne $Payload.messages)
    } catch {
        return $false
    }
}

function Write-ChatCockpitReceipt {
    param(
        [string]$Status,
        [bool]$ProcessStarted,
        [Nullable[int]]$ProcessId,
        [Nullable[int]]$ExitCode,
        [string]$FailureMode = ""
    )

    $ReceiptDir = Split-Path -Parent $ResolvedReceiptPath
    New-Item -ItemType Directory -Force -Path $ReceiptDir | Out-Null
    $Payload = [ordered]@{
        schema = "unreal_mcp_chat_cockpit_start_receipt.v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        status = $Status
        base_url = $BaseUrl
        health_url = $HealthUrl
        mcp_endpoint = $McpEndpoint
        server_command = @($PythonExe) + $ServerArgs
        process_started = $ProcessStarted
        process_id = $ProcessId
        exit_code = $ExitCode
        failure_mode = $FailureMode
        no_port_kill = $true
        no_editor_mutation = $true
        no_provider_call = $true
        no_git_mutation = $true
        network_required = $false
        spend_required = $false
        unreal_editor_required = $false
    }
    $Payload | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -Path $ResolvedReceiptPath
}

if (Test-ChatCockpitReady) {
    Write-ChatCockpitReceipt -Status "already_running" -ProcessStarted $false -ProcessId $null -ExitCode $null
    Write-Output "CHAT_COCKPIT_STATUS=already_running"
    Write-Output "CHAT_COCKPIT_URL=$BaseUrl"
    Write-Output "CHAT_COCKPIT_RECEIPT=$ReceiptPath"
    exit 0
}

$Process = Start-Process -FilePath $PythonExe -ArgumentList $ServerArgs -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru
$Deadline = (Get-Date).AddSeconds($TimeoutSeconds)

while ((Get-Date) -lt $Deadline) {
    Start-Sleep -Milliseconds 500
    if ($Process.HasExited) {
        Write-ChatCockpitReceipt -Status "failed" -ProcessStarted $true -ProcessId $Process.Id -ExitCode $Process.ExitCode -FailureMode "process_exited_before_health_ready"
        Write-Output "CHAT_COCKPIT_STATUS=failed"
        Write-Output "CHAT_COCKPIT_URL=$BaseUrl"
        Write-Output "CHAT_COCKPIT_RECEIPT=$ReceiptPath"
        exit 1
    }
    if (Test-ChatCockpitReady) {
        Write-ChatCockpitReceipt -Status "started" -ProcessStarted $true -ProcessId $Process.Id -ExitCode $null
        Write-Output "CHAT_COCKPIT_STATUS=started"
        Write-Output "CHAT_COCKPIT_URL=$BaseUrl"
        Write-Output "CHAT_COCKPIT_RECEIPT=$ReceiptPath"
        exit 0
    }
}

$ProcessStillRunning = -not $Process.HasExited
if ($ProcessStillRunning) {
    Stop-Process -Id $Process.Id -ErrorAction SilentlyContinue
    $Process.WaitForExit(5000) | Out-Null
    $Process.Refresh()
    $ProcessStillRunning = -not $Process.HasExited
}
Write-ChatCockpitReceipt -Status "failed" -ProcessStarted $true -ProcessId $Process.Id -ExitCode $(if ($Process.HasExited) { $Process.ExitCode } else { $null }) -FailureMode "health_timeout"
Write-Output "CHAT_COCKPIT_STATUS=failed"
Write-Output "CHAT_COCKPIT_URL=$BaseUrl"
Write-Output "CHAT_COCKPIT_RECEIPT=$ReceiptPath"
Write-Output "CHAT_COCKPIT_PROCESS_STILL_RUNNING=$ProcessStillRunning"
exit 1
