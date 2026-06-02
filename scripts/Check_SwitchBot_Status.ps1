$ErrorActionPreference = 'SilentlyContinue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $ProjectRoot 'logs'
$StateDir = Join-Path $ProjectRoot 'state'
$StateFile = Join-Path $StateDir 'switchbot_state.json'
$logFiles = @(
    (Join-Path $LogDir 'SwitchBot_ON.log'),
    (Join-Path $LogDir 'SwitchBot_OFF.log'),
    (Join-Path $LogDir 'Restart_SwitchBot_Tasks.log')
)
$targets = @('SwitchBot_ON.py', 'SwitchBot_OFF.py')

Write-Host '=== Scheduled Tasks ==='
foreach ($taskName in @('SwitchBot_ON', 'SwitchBot_OFF')) {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        $info = Get-ScheduledTaskInfo -TaskName $taskName
        [pscustomobject]@{
            TaskName = $taskName
            State = $task.State
            LastRunTime = $info.LastRunTime
            LastTaskResult = $info.LastTaskResult
            NextRunTime = $info.NextRunTime
        } | Format-List
    } else {
        Write-Host "Task not found: $taskName"
    }
}

Write-Host "`n=== Python Processes ==="
$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(\.exe|w\.exe)?$|^py\.exe$' -and $_.CommandLine
}
$found = $false
foreach ($p in $procs) {
    foreach ($target in $targets) {
        if ($p.CommandLine -like "*$target*") {
            $found = $true
            [pscustomobject]@{
                PID = $p.ProcessId
                Name = $p.Name
                CommandLine = $p.CommandLine
            } | Format-List
            break
        }
    }
}
if (-not $found) {
    Write-Host 'No matching SwitchBot python processes found.'
}

Write-Host "`n=== Shared State ==="
if (Test-Path $StateFile) {
    Get-Content $StateFile -Raw | Write-Host
} else {
    Write-Host "State file not found: $StateFile"
}

Write-Host "`n=== Log Files ==="
foreach ($logFile in $logFiles) {
    [pscustomobject]@{
        Exists = Test-Path $logFile
        Path = $logFile
    } | Format-List
}
