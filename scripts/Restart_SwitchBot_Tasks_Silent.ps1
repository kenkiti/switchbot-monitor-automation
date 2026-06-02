$ErrorActionPreference = 'SilentlyContinue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $ProjectRoot 'logs'
$LogFile = Join-Path $LogDir 'Restart_SwitchBot_Tasks.log'
$StopScript = Join-Path $ScriptDir 'Stop_SwitchBot_Processes.ps1'

function Write-Log {
    param([string]$Message)

    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Path $LogFile -Value "[$stamp] $Message"
}

Write-Log 'Restart started.'

if (Test-Path $StopScript) {
    Write-Log 'Running Stop_SwitchBot_Processes.ps1'
    powershell.exe -ExecutionPolicy Bypass -File $StopScript
}
else {
    Write-Log "Stop script not found: $StopScript"
}

Start-Sleep -Seconds 3

Write-Log 'Starting SwitchBot_ON'
Start-ScheduledTask -TaskName 'SwitchBot_ON'

Start-Sleep -Seconds 1

Write-Log 'Starting SwitchBot_OFF'
Start-ScheduledTask -TaskName 'SwitchBot_OFF'

Start-Sleep -Seconds 2

$onInfo = Get-ScheduledTaskInfo -TaskName 'SwitchBot_ON'
$offInfo = Get-ScheduledTaskInfo -TaskName 'SwitchBot_OFF'

Write-Log ("SwitchBot_ON LastTaskResult={0}" -f $onInfo.LastTaskResult)
Write-Log ("SwitchBot_OFF LastTaskResult={0}" -f $offInfo.LastTaskResult)

Write-Log 'Restart finished.'
