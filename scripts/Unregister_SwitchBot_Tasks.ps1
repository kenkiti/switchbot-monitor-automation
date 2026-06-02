$ErrorActionPreference = 'Stop'

foreach ($taskName in @('SwitchBot_ON', 'SwitchBot_OFF')) {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "Removed: $taskName"
    } else {
        Write-Host "Not found: $taskName"
    }
}
