$ErrorActionPreference = 'SilentlyContinue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$SrcDir = Join-Path $ProjectRoot 'src'

Write-Host 'Stopping scheduled tasks...'
Stop-ScheduledTask -TaskName 'SwitchBot_ON'
Stop-ScheduledTask -TaskName 'SwitchBot_OFF'

Start-Sleep -Seconds 2

Write-Host 'Stopping Python processes for SwitchBot scripts...'

$targets = @(
    (Join-Path $SrcDir 'SwitchBot_ON.py'),
    (Join-Path $SrcDir 'SwitchBot_OFF.py')
)

$procs = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -ieq 'python.exe' -or $_.Name -ieq 'pythonw.exe' -or $_.Name -ieq 'py.exe' -or $_.Name -ieq 'pyw.exe') -and
    $_.CommandLine
}

$matched = @()

foreach ($p in $procs) {
    foreach ($t in $targets) {
        if ($p.CommandLine -like "*$t*") {
            $matched += $p
            break
        }
    }
}

if ($matched.Count -eq 0) {
    Write-Host 'No matching SwitchBot Python processes found.'
}
else {
    $matched | Sort-Object ProcessId -Unique | ForEach-Object {
        Write-Host ("Killing PID {0} : {1}" -f $_.ProcessId, $_.CommandLine)
        Stop-Process -Id $_.ProcessId -Force
    }
}

Write-Host 'Done.'
