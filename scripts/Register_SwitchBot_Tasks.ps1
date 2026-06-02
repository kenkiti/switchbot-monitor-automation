$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$SrcDir = Join-Path $ProjectRoot 'src'
$OnScript = Join-Path $SrcDir 'SwitchBot_ON.py'
$OffScript = Join-Path $SrcDir 'SwitchBot_OFF.py'

if (-not (Test-Path $OnScript)) {
    throw "Missing file: $OnScript"
}
if (-not (Test-Path $OffScript)) {
    throw "Missing file: $OffScript"
}

$python = Get-Command python -ErrorAction Stop
$pythonExe = $python.Source
$pythonDir = Split-Path $pythonExe -Parent
$pythonwExe = Join-Path $pythonDir 'pythonw.exe'

if (Test-Path $pythonwExe) {
    $exe = $pythonwExe
} else {
    $exe = $pythonExe
}

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances Ignore
$trigger = New-ScheduledTaskTrigger -AtLogOn

$onAction = New-ScheduledTaskAction -Execute $exe -Argument "`"$OnScript`"" -WorkingDirectory $ProjectRoot
$offAction = New-ScheduledTaskAction -Execute $exe -Argument "`"$OffScript`"" -WorkingDirectory $ProjectRoot

if (Get-ScheduledTask -TaskName 'SwitchBot_ON' -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName 'SwitchBot_ON' -Confirm:$false
}
if (Get-ScheduledTask -TaskName 'SwitchBot_OFF' -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName 'SwitchBot_OFF' -Confirm:$false
}

Register-ScheduledTask -TaskName 'SwitchBot_ON' -Action $onAction -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
Register-ScheduledTask -TaskName 'SwitchBot_OFF' -Action $offAction -Trigger $trigger -Principal $principal -Settings $settings | Out-Null

Write-Host "Registered successfully"
Write-Host "Executable: $exe"
Write-Host "ON script : $OnScript"
Write-Host "OFF script: $OffScript"
