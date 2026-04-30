param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$pythonScript = Join-Path $scriptDir "pipeline\\davinci_project_orchestrator.py"

$argsList = @($pythonScript, "--root", $rootDir)
if ($Force) {
    $argsList += "--force"
}

python @argsList
