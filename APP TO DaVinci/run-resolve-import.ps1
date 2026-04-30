param(
    [Parameter(Mandatory = $true)]
    [string]$PlanJson,

    [double]$Fps = 24.0,

    [string]$ProjectName = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir 'pipeline\\resolve_import_semantic_timeline.py'

$moduleCandidates = @(
    'C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules',
    'C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules',
    'C:\Program Files\Blackmagic Design\DaVinci Resolve\Fusion\Modules'
)

$existing = $moduleCandidates | Where-Object { Test-Path $_ }
if ($existing.Count -gt 0) {
    $env:PYTHONPATH = (($existing -join ';') + ';' + $env:PYTHONPATH).Trim(';')
}

if ($ProjectName) {
    python $pythonScript $PlanJson $Fps $ProjectName
} else {
    python $pythonScript $PlanJson $Fps
}
