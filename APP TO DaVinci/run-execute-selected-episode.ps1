param(
    [Parameter(Mandatory = $true)]
    [string]$Project,

    [Parameter(Mandatory = $true)]
    [string]$Episode,

    [switch]$PrepareOnly,

    [switch]$FullRegenerate
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeLauncher = Join-Path $scriptDir "run-execute-runtime.ps1"

if ($PrepareOnly) {
    if ($FullRegenerate) {
        & $runtimeLauncher -Project $Project -Episode $Episode -PrepareOnly -FullRegenerate
    } else {
        & $runtimeLauncher -Project $Project -Episode $Episode -PrepareOnly
    }
} else {
    if ($FullRegenerate) {
        & $runtimeLauncher -Project $Project -Episode $Episode -FullRegenerate
    } else {
        & $runtimeLauncher -Project $Project -Episode $Episode
    }
}
