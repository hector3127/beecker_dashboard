<#
.SYNOPSIS
Programa en el Programador de tareas de Windows las sincronizaciones del panel.

.DESCRIPTION
Crea cuatro tareas (ver docs/ejecucion-programada.md):
  Beecker-Sync-Horario  cada hora (minuto 05): hojas de Sheets, Azure DevOps y catalogos
  Beecker-Sync-Diario   cada dia a las 06:00:  horas de Clockify y catalogos
  Beecker-WarmCache     cada 10 minutos:       precalienta las pantallas
  Beecker-Revisar       cada hora (minuto 40): falla si algo esta atrasado

Cada tarea escribe su salida en logs\ y no se lanza otra vez mientras la
anterior sigue corriendo. Se puede ejecutar de nuevo: reemplaza las tareas.

.PARAMETER Action
Install (por defecto), Remove o Status.

.PARAMETER DryRun
Muestra lo que haria sin crear ni borrar nada.

.EXAMPLE
.\scripts\schedule_windows.ps1 -DryRun
.\scripts\schedule_windows.ps1
.\scripts\schedule_windows.ps1 -Action Status
.\scripts\schedule_windows.ps1 -Action Remove
#>
#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('Install', 'Remove', 'Status')]
    [string]$Action = 'Install',
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot),
    [string]$Python,
    [string]$DailyAt = '06:00',
    [string]$Prefix = 'Beecker',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
if (-not $Python) { $Python = Join-Path $ProjectDir '.venv\Scripts\python.exe' }
$LogDir = Join-Path $ProjectDir 'logs'

# Nombre, argumentos de manage.py, cada cuanto, tiempo maximo y bitacora.
$Jobs = @(
    @{
        Name = "$Prefix-Sync-Horario"
        Args = 'manage.py sync_datastore --pasos hojas,azure,lecturas,catalogos'
        EveryMinutes = 60; StartAt = '00:05'; Limit = (New-TimeSpan -Hours 1)
        Log = 'sync-horario.log'
        Text = 'Guarda las hojas de Sheets, Azure DevOps y los catalogos en la base.'
    },
    @{
        Name = "$Prefix-Sync-Diario"
        Args = 'manage.py sync_datastore --pasos clockify,catalogos'
        DailyAt = $DailyAt; Limit = (New-TimeSpan -Hours 3)
        Log = 'sync-diario.log'
        Text = 'Descarga las horas de Clockify (ventana abierta y meses que cambiaron).'
    },
    @{
        Name = "$Prefix-WarmCache"
        Args = 'manage.py warm_cache'
        EveryMinutes = 10; StartAt = '00:00'; Limit = (New-TimeSpan -Minutes 30)
        Log = 'warm-cache.log'
        Text = 'Precalienta las pantallas del portal leyendo de la base.'
    },
    @{
        Name = "$Prefix-Revisar"
        Args = 'manage.py check_datastore --lecturas'
        EveryMinutes = 60; StartAt = '00:40'; Limit = (New-TimeSpan -Minutes 10)
        Log = 'revisar.log'
        Text = 'Termina con error si hojas, Azure o Clockify se quedaron atrasados (ver "Ultimo resultado" en Status).'
    }
)

function Get-Command-Line([hashtable]$Job) {
    # cmd /c permite mandar la salida a una bitacora; las comillas externas
    # las quita cmd, por eso van dobles al inicio y al final.
    $log = Join-Path $LogDir $Job.Log
    return "/c `"`"$Python`" $($Job.Args) >> `"$log`" 2>&1`""
}

switch ($Action) {
    'Status' {
        Get-ScheduledTask -TaskName "$Prefix-*" -ErrorAction SilentlyContinue |
            Get-ScheduledTaskInfo |
            Select-Object TaskName, LastRunTime, LastTaskResult, NextRunTime |
            Format-Table -AutoSize
        if (-not (Get-ScheduledTask -TaskName "$Prefix-*" -ErrorAction SilentlyContinue)) {
            Write-Host "No hay tareas '$Prefix-*' programadas."
        }
    }
    'Remove' {
        foreach ($job in $Jobs) {
            if ($DryRun) { Write-Host "[DryRun] Se borraria la tarea $($job.Name)"; continue }
            Unregister-ScheduledTask -TaskName $job.Name -Confirm:$false -ErrorAction SilentlyContinue
            Write-Host "Tarea $($job.Name) borrada (si existia)."
        }
    }
    'Install' {
        if (-not $DryRun -and -not (Test-Path $Python)) {
            throw "No existe $Python. Pasa -Python con la ruta del Python del proyecto."
        }
        if (-not $DryRun) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }
        foreach ($job in $Jobs) {
            $commandLine = Get-Command-Line $job
            if ($job.DailyAt) {
                $trigger = New-ScheduledTaskTrigger -Daily -At $job.DailyAt
                $when = "todos los dias a las $($job.DailyAt)"
            }
            else {
                $first = [datetime]::Today.Add([timespan]::Parse($job.StartAt))
                $trigger = New-ScheduledTaskTrigger -Once -At $first `
                    -RepetitionInterval (New-TimeSpan -Minutes $job.EveryMinutes) `
                    -RepetitionDuration (New-TimeSpan -Days 3650)
                $when = "cada $($job.EveryMinutes) min desde las $($job.StartAt)"
            }
            if ($DryRun) {
                Write-Host "[DryRun] $($job.Name): $when"
                Write-Host "         cmd.exe $commandLine"
                Write-Host "         carpeta: $ProjectDir | tiempo maximo: $($job.Limit)"
                continue
            }
            $taskAction = New-ScheduledTaskAction -Execute 'cmd.exe' `
                -Argument $commandLine -WorkingDirectory $ProjectDir
            # IgnoreNew: si la anterior sigue corriendo, no se lanza otra encima.
            $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
                -StartWhenAvailable -ExecutionTimeLimit $job.Limit `
                -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
            Register-ScheduledTask -TaskName $job.Name -Action $taskAction `
                -Trigger $trigger -Settings $settings -Description $job.Text -Force | Out-Null
            Write-Host "Tarea $($job.Name) lista: $when"
        }
        if (-not $DryRun) {
            Write-Host "`nSalida de cada tarea en: $LogDir"
            Write-Host "Estado: .\scripts\schedule_windows.ps1 -Action Status"
        }
    }
}
