param(
    [Parameter(Mandatory = $true)]
    [string]$Project,

    [string]$Episode = "Episodio 01 - Vida espejo y quiralidad",

    [switch]$PrepareOnly,

    [switch]$FullRegenerate
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$pythonScript = Join-Path $scriptDir "pipeline\\execute_production_runtime.py"

$argsList = @($pythonScript, "--root", $rootDir, "--project", $Project, "--episode", $Episode)
if ($PrepareOnly) {
    $argsList += "--prepare-only"
}
if ($FullRegenerate) {
    $argsList += "--full-regenerate"
}

python @argsList
