[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$files = @(Get-ChildItem -LiteralPath $root -Recurse -File -Force)

$forbiddenExtensions = @('.safetensors', '.ckpt', '.pth', '.index', '.bin', '.gguf', '.pyc')
$forbidden = @($files | Where-Object { $forbiddenExtensions -contains $_.Extension.ToLowerInvariant() })
$backupFiles = @($files | Where-Object { $_.Name -match '\.bak$|^before_|\.before_|run_manifest|\.log$' })
$invalidJson = @()

foreach ($file in $files | Where-Object Extension -eq '.json') {
    try {
        $null = Get-Content -Raw -Encoding UTF8 -LiteralPath $file.FullName | ConvertFrom-Json
    }
    catch {
        $invalidJson += [pscustomobject]@{
            Path = $file.FullName.Substring($root.Length + 1)
            Error = $_.Exception.Message
        }
    }
}

$result = [ordered]@{
    Root = $root
    Files = $files.Count
    Bytes = ($files | Measure-Object Length -Sum).Sum
    Json = @($files | Where-Object Extension -eq '.json').Count
    InvalidJson = $invalidJson.Count
    ForbiddenWeightsOrCache = $forbidden.Count
    BackupOrRunLogs = $backupFiles.Count
}

$result.GetEnumerator() | ForEach-Object { '{0}={1}' -f $_.Key, $_.Value }

if ($invalidJson) { $invalidJson | Format-List | Out-String | Write-Host }
if ($forbidden) { $forbidden.FullName | Write-Host }
if ($backupFiles) { $backupFiles.FullName | Write-Host }

if ($invalidJson.Count -or $forbidden.Count -or $backupFiles.Count) {
    throw 'Public release content gate failed.'
}

$guiDir = @(Get-ChildItem -LiteralPath $root -Directory | Where-Object Name -like '02_*')
$nodeDir = @(Get-ChildItem -LiteralPath $root -Directory | Where-Object Name -like '03_*')
if ($guiDir.Count -ne 1 -or $nodeDir.Count -ne 1) {
    throw 'Expected exactly one 02_* directory and one 03_* directory.'
}

$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location $guiDir[0].FullName
try {
    python -m unittest -v test_batch_prompt_tool_v2.py
    if ($LASTEXITCODE -ne 0) { throw 'GUI unit tests failed.' }
}
finally {
    Pop-Location
}

Push-Location $nodeDir[0].FullName
try {
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Custom-node unit tests failed.' }
}
finally {
    Pop-Location
}

Write-Host 'PUBLIC_RELEASE_GATE=PASS'
