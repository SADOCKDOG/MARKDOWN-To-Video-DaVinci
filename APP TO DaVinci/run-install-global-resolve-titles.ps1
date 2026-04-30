param(
    [string]$TargetDir,
    [switch]$BuildOnly
)

$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $appDir "pipeline\\install_resolve_global_titles.py"

$argsList = @($pythonScript, "--app-root", $appDir)
if (-not $BuildOnly) {
    $argsList += "--install"
}
if ($TargetDir) {
    $argsList += @("--target-dir", $TargetDir)
}

python @argsList
