# ПОЛИМАТ-ГЕН: обёртка для Windows (PowerShell)
# Использование: .\scripts\polymath.ps1 examples\task.demo.yaml
param(
    [Parameter(Mandatory=$true)][string]$Task,
    [string]$Backend = "auto",
    [string]$Llm = "auto",
    [int]$Rounds = 2
)
$RepoRoot = Split-Path (Split-Path $PSScriptRoot)
Set-Location $RepoRoot
python -m polymath_gen.cli $Task --backend $Backend --llm $Llm --rounds $Rounds
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nОткрываю последний прогон..." -ForegroundColor Green
    $latest = Get-ChildItem runs -Directory | Sort-Object Name -Descending | Select-Object -First 1
    Start-Process explorer.exe $latest.FullName
}
