param(
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet('local', 'github', 'status', 'resume')]
    [string]$Mode,
    [string]$App = 'voicevault'
)
$ErrorActionPreference = 'Stop'
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw 'Install Python 3.10 or later, then run this command again.' }
& $python.Source -B "$PSScriptRoot/scripts/release.py" $Mode.ToLowerInvariant() --app $App
exit $LASTEXITCODE

