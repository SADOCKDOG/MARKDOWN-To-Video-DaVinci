param(
    [Parameter(Mandatory = $true)]
    [string]$Project
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$pythonScript = Join-Path $scriptDir "pipeline\\generate_prompt_catalog.py"

python $pythonScript --root $rootDir --project $Project
