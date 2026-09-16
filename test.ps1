param([string]$App = 'voicevault')
$ErrorActionPreference = 'Stop'
& python -B "$PSScriptRoot/scripts/release.py" test --app $App
exit $LASTEXITCODE

