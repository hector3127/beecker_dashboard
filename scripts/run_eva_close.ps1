param([Parameter(Mandatory)][string]$ProjectDir, [switch]$Capture)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $ProjectDir
$python = Join-Path $ProjectDir '.venv\Scripts\python.exe'
$logDir = Join-Path $ProjectDir 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logName = if ($Capture) { 'eva-captura-cierre.log' } else { 'eva-cierre-mensual.log' }
$logFile = Join-Path $logDir $logName
Add-Content -LiteralPath $logFile -Encoding UTF8 -Value "`nInicio: $(Get-Date -Format o)"
try {
    if ($Capture) { & $python -u manage.py close_eva_month --capture 2>&1 | Out-File -FilePath $logFile -Append -Encoding UTF8 }
    else { & $python -u manage.py close_eva_month 2>&1 | Out-File -FilePath $logFile -Append -Encoding UTF8 }
    exit $LASTEXITCODE
} catch {
    Add-Content -LiteralPath $logFile -Encoding UTF8 -Value $_.Exception.Message
    exit 1
}
