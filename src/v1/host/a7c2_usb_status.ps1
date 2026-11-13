param([switch]$AllowDeviceQuery, [switch]$AsJson)
$ErrorActionPreference = 'Stop'
if (-not $AllowDeviceQuery) { throw 'This queries Windows device state. Supply -AllowDeviceQuery explicitly.' }
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
# Host inventory only: no driver changes, device handles, authentication or reset.
# Keep instance IDs (which may contain serials) out of output.
$Rows = @(Get-PnpDevice -PresentOnly | Where-Object {
    $_.InstanceId -match '^USB\\VID_054C&PID_[0-9A-F]{4}\\'
} | ForEach-Object {
    $CameraEntry = $_
    $PidText = [regex]::Match($CameraEntry.InstanceId, 'PID_([0-9A-F]{4})', 'IgnoreCase').Groups[1].Value.ToLowerInvariant()
    $Fields = @{}
    foreach ($Key in @('DEVPKEY_Device_Service', 'DEVPKEY_Device_DriverVersion', 'DEVPKEY_Device_DriverInfPath')) {
        try { $Fields[$Key] = (Get-PnpDeviceProperty -InstanceId $CameraEntry.InstanceId -KeyName $Key -ErrorAction Stop).Data }
        catch { $Fields[$Key] = $null }
    }
    [pscustomobject]@{
        vid = '054c'; pid = $PidText; name = $CameraEntry.FriendlyName; status = [string]$CameraEntry.Status
        service = $Fields['DEVPKEY_Device_Service']
        driver_version = $Fields['DEVPKEY_Device_DriverVersion']
        driver_inf = $Fields['DEVPKEY_Device_DriverInfPath']
    }
})
if ($AsJson) { ConvertTo-Json -InputObject $Rows -Compress }
elseif ($Rows.Count -eq 0) { Write-Output 'No present Sony USB parent device. Select Image Transfer (MSC) on the camera, then run this again.' }
else { $Rows | Format-Table -AutoSize }
