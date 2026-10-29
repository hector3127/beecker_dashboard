param(
    [ValidateSet('Install','Status','Remove')][string]$Action = 'Status',
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot),
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$jobs = @(
    @{Name='Beecker-EVA-CapturaCierre'; Capture=$true; At='23:40'; Description='Captura Azure/Clockify solo el último lunes-jueves del mes.'},
    @{Name='Beecker-EVA-CerrarMes'; Capture=$false; At='00:20'; Description='Congela cierres EVA vencidos desde evidencia local; reintenta cada hora.'}
)
foreach ($job in $jobs) {
    if ($Action -eq 'Status') {
        $task = Get-ScheduledTask -TaskName $job.Name -ErrorAction SilentlyContinue
        if ($task) { $task | Get-ScheduledTaskInfo | Select-Object TaskName,LastRunTime,LastTaskResult,NextRunTime }
        else { Write-Output "$($job.Name): no instalada" }
        continue
    }
    if ($DryRun) { Write-Output "$Action $($job.Name): $($job.At), ventana México; captura=$($job.Capture)"; continue }
    if ($Action -eq 'Remove') { Unregister-ScheduledTask -TaskName $job.Name -Confirm:$false -ErrorAction SilentlyContinue; continue }
    if ((Get-TimeZone).Id -ne 'Central Standard Time (Mexico)') { throw 'Configura la zona de Windows a Ciudad de México antes de instalar.' }
    $runner = Join-Path $ProjectDir 'scripts\run_eva_close.ps1'
    $extra = if ($job.Capture) { ' -Capture' } else { '' }
    $arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runner`" -ProjectDir `"$ProjectDir`"$extra"
    $taskAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $ProjectDir
    if ($job.Capture) { $trigger = New-ScheduledTaskTrigger -Daily -At $job.At }
    else {
        $trigger = New-ScheduledTaskTrigger -Once -At ([datetime]::Today.Add([timespan]::Parse($job.At))) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
    }
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $job.Name -Action $taskAction -Trigger $trigger -Settings $settings -Description $job.Description -Force | Out-Null
    Write-Output "$($job.Name): instalada"
}
