param(
    [string]$At = '08:00',
    [string]$PythonExecutable = '',
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$sha = [System.Security.Cryptography.SHA256]::Create()
$hash = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($projectRoot))).Replace('-', '').Substring(0, 10)
$taskName = "EconomyNewsDaily-$hash"
if ($Remove) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed task: $taskName"
    exit
}
if ($At -notmatch '^([01][0-9]|2[0-3]):[0-5][0-9]$') { throw 'Use a time such as 08:00.' }
if (-not $PythonExecutable) {
    $PythonExecutable = (& py -3 -c 'import sys; print(sys.executable)' | Select-Object -Last 1)
    if ($LASTEXITCODE -ne 0) { throw 'Python could not be found. Use -PythonExecutable with its full path.' }
}
if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) { throw 'Python executable was not found.' }
$scriptPath = Join-Path $projectRoot 'daily_report.py'
$action = New-ScheduledTaskAction -Execute $PythonExecutable -Argument ('"' + $scriptPath + '"') -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.Add([timespan]::ParseExact($At, 'hh\:mm', $null)))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Daily economic news keywords and selected public article bodies. Reports are saved locally.' -Force | Out-Null
Write-Host "Registered: $taskName at $At (Windows local time)."
Write-Host 'The PC must be on, connected to the internet, and the user must be signed in.'
Write-Host 'Reports: output/latest.html. Keep this project folder in its current location.'
