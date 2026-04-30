param(
    [string]$Episode,
    [switch]$All,
    [switch]$DryRun,
    [int]$Clips = 0,
    [int]$QueryLimit = 0,
    [int]$PerSource = 0,
    [string]$Sources = "pexels_v,pixabay_v,nasa_v,nasa_svs,archive_v,coverr,wikimedia_v",
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "pipeline\\semantic_sciclip_bridge.py"

if ($ProjectRoot) {
    $env:VIDA_ESPEJO_ROOT = $ProjectRoot
}

$argsList = @($pythonScript, "--sources", $Sources)
if ($Clips -gt 0) {
    $argsList += @("--clips", "$Clips")
}
if ($QueryLimit -gt 0) {
    $argsList += @("--query-limit", "$QueryLimit")
}
if ($PerSource -gt 0) {
    $argsList += @("--per-source", "$PerSource")
}
if ($All) {
    $argsList += "--all"
} elseif ($Episode) {
    $argsList += @("--episode", $Episode)
} else {
    throw "Usa -Episode o -All."
}
if ($DryRun) {
    $argsList += "--dry-run"
}

python @argsList
