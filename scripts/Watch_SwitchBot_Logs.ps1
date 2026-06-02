$ErrorActionPreference = 'SilentlyContinue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $ProjectRoot 'logs'
$OnLog = Join-Path $LogDir 'SwitchBot_ON.log'
$OffLog = Join-Path $LogDir 'SwitchBot_OFF.log'

if (-not (Test-Path $OnLog)) {
    Write-Host "Missing: $OnLog"
}
if (-not (Test-Path $OffLog)) {
    Write-Host "Missing: $OffLog"
}

Write-Host 'Watching SwitchBot logs...'
Write-Host 'Press Ctrl+C to stop.'
Write-Host '----------------------------------------'

$fsw = New-Object System.IO.FileSystemWatcher
$fsw.Path = $LogDir
$fsw.Filter = '*.log'
$fsw.IncludeSubdirectories = $false
$fsw.EnableRaisingEvents = $true

$script:lastPos = @{}
$script:lastPos[$OnLog] = 0
$script:lastPos[$OffLog] = 0

function Initialize-Position {
    param([string]$Path)

    if (Test-Path $Path) {
        $item = Get-Item $Path
        $script:lastPos[$Path] = $item.Length
    }
}

function Read-NewLines {
    param(
        [string]$Path,
        [string]$Tag
    )

    if (-not (Test-Path $Path)) {
        return
    }

    try {
        $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        try {
            if (-not $script:lastPos.ContainsKey($Path)) {
                $script:lastPos[$Path] = 0
            }

            if ($script:lastPos[$Path] -gt $stream.Length) {
                $script:lastPos[$Path] = 0
            }

            $stream.Seek($script:lastPos[$Path], [System.IO.SeekOrigin]::Begin) | Out-Null
            $reader = New-Object System.IO.StreamReader($stream)

            while (-not $reader.EndOfStream) {
                $line = $reader.ReadLine()
                if ($null -ne $line -and $line -ne '') {
                    $stamp = Get-Date -Format 'HH:mm:ss'
                    Write-Host "[$stamp][$Tag] $line"
                }
            }

            $script:lastPos[$Path] = $stream.Position
        }
        finally {
            $stream.Close()
        }
    }
    catch {
    }
}

Initialize-Position -Path $OnLog
Initialize-Position -Path $OffLog

$action = {
    $path = $Event.SourceEventArgs.FullPath

    Start-Sleep -Milliseconds 150

    if ($path -eq $using:OnLog) {
        Read-NewLines -Path $using:OnLog -Tag 'ON '
    }
    elseif ($path -eq $using:OffLog) {
        Read-NewLines -Path $using:OffLog -Tag 'OFF'
    }
}

$createdSub = Register-ObjectEvent -InputObject $fsw -EventName Created -Action $action
$changedSub = Register-ObjectEvent -InputObject $fsw -EventName Changed -Action $action

try {
    while ($true) {
        Wait-Event -Timeout 1 | Out-Null
    }
}
finally {
    Unregister-Event -SourceIdentifier $createdSub.Name -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier $changedSub.Name -ErrorAction SilentlyContinue
    $fsw.Dispose()
}
