param([switch]$GitHubOnly)
$ErrorActionPreference = 'Stop'
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw 'Install Python 3.10 or later, then run setup.ps1 again.' }
$options = @()
if ($GitHubOnly) { $options += '--github-only' }
& $python.Source -B "$PSScriptRoot/scripts/release.py" setup @options
exit $LASTEXITCODE

