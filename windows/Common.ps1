Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:A1RawBytes = [long]8120172544
$script:A1RawSha = 'f9aa0fa2dd618febf28a5e2a583d1e2b5a8ca3f1205be965da584602ac962f40'

function Assert-A1UsbDisk {
    param($Disk)
    if ([string]$Disk.BusType -ne 'USB' -or $Disk.IsBoot -or $Disk.IsSystem -or $Disk.IsReadOnly -or $Disk.IsOffline) { throw 'Target must be an online, writable USB that is neither a boot disk nor a system disk.' }
    if ([string]$Disk.PartitionStyle -ne 'GPT' -or [long]$Disk.LogicalSectorSize -ne 512 -or [long]$Disk.Size -lt $script:A1RawBytes) { throw 'The USB does not have the expected GPT/512-byte-sector recovery layout or size.' }
    foreach ($name in @('SerialNumber', 'UniqueId', 'Path')) {
        if ([string]::IsNullOrWhiteSpace([string]$Disk.$name)) { throw "USB identity field $name is missing; refusing a raw write." }
    }
}
function Get-A1DiskIdentity {
    param($Disk)
    Assert-A1UsbDisk $Disk
    return [pscustomobject]@{ Number=[int]$Disk.Number; Size=[long]$Disk.Size; SerialNumber=([string]$Disk.SerialNumber).Trim(); UniqueId=([string]$Disk.UniqueId).Trim(); Path=[string]$Disk.Path }
}
function Assert-A1SameDisk {
    param($Expected, $Actual)
    $current = Get-A1DiskIdentity $Actual
    foreach ($name in @('Number', 'Size', 'SerialNumber', 'UniqueId', 'Path')) {
        if ([string]$Expected.$name -cne [string]$current.$name) { throw 'The USB identity changed. Nothing further will be written.' }
    }
}
function Assert-A1RegularPath {
    param([string]$Path, [switch]$New)
    if ($Path -notmatch '^[A-Za-z]:\\' -or $Path -match '^\\\\') { throw 'Choose a local Windows drive path, not a device or network path.' }
    $full = [IO.Path]::GetFullPath($Path)
    if ($New) {
        if (Test-Path -LiteralPath $full) { throw 'Output already exists. Choose a new filename.' }
        $inspect = [IO.DirectoryInfo]([IO.Path]::GetDirectoryName($full))
        if (-not $inspect.Exists) { throw 'The output directory must already exist.' }
    } else {
        $file = Get-Item -LiteralPath $full
        if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Source must be a regular image file.' }
        $inspect = $file.Directory
    }
    while ($null -ne $inspect) {
        if ($inspect.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Symlinks and junctions in image paths are not supported.' }
        $inspect = $inspect.Parent
    }
    return $full
}
function Copy-A1Range {
    param([IO.Stream]$SourceStream, [IO.Stream]$DestinationStream, [long]$Count)
    if ($Count -lt 0) { throw 'Invalid byte count.' }
    $sha = [Security.Cryptography.SHA256]::Create()
    $buffer = New-Object byte[] (1024 * 1024)
    $remaining = $Count
    try {
        while ($remaining -gt 0) {
            $n = $SourceStream.Read($buffer, 0, [int][Math]::Min($buffer.Length, $remaining))
            if ($n -le 0) { throw 'Unexpected end of source; copy stopped.' }
            [void]$sha.TransformBlock($buffer, 0, $n, $buffer, 0)
            if ($null -ne $DestinationStream) { $DestinationStream.Write($buffer, 0, $n) }
            $remaining -= $n
            if ($Count -gt 1048576) { Write-Progress -Activity 'Copying recovery image' -PercentComplete ([int](100 * ($Count - $remaining) / $Count)) }
        }
        [void]$sha.TransformFinalBlock((New-Object byte[] 0), 0, 0)
        return ([BitConverter]::ToString($sha.Hash)).Replace('-', '').ToLowerInvariant()
    } finally { $sha.Dispose(); Write-Progress -Activity 'Copying recovery image' -Completed }
}
function ConvertTo-A1WslPath {
    param([string]$Distro, [string]$WindowsPath)
    $result = @(& wsl.exe --distribution $Distro --user root --exec wslpath -a -u -- $WindowsPath)
    if ($LASTEXITCODE -ne 0 -or $result.Count -ne 1) { throw 'Could not translate a path into WSL.' }
    return [string]$result[0]
}
function Invoke-A1LinuxBackend {
    param([string]$Distro, [string]$Repo, [string]$Action, [string]$Source='', [string]$Output='', [bool]$IncludeDualBoot=$false)
    $linuxRepo = ConvertTo-A1WslPath $Distro $Repo
    $arguments = @('--distribution', $Distro, '--user', 'root', '--exec', '/bin/bash', "$linuxRepo/windows/backend.sh", $Action)
    if ($Action -eq 'patch') { $arguments += @($linuxRepo, (ConvertTo-A1WslPath $Distro $Source), (ConvertTo-A1WslPath $Distro $Output)) }
    if ($Action -eq 'patch' -and $IncludeDualBoot) { $arguments += '--include-dualboot' }
    & wsl.exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "Linux backend stopped (exit $LASTEXITCODE). Read the message above; no success is claimed." }
}
function Initialize-A1VolumeApi {
    if ('A1VolumeApi' -as [type]) { return }
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class A1VolumeApi {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern SafeFileHandle CreateFile(string path, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool DeviceIoControl(SafeFileHandle handle, uint code, IntPtr input, uint inSize, IntPtr output, uint outSize, out uint returned, IntPtr overlapped);
    public static SafeFileHandle Lock(string volume) {
        var handle=CreateFile(volume.TrimEnd('\\'), 0xC0000000, 3, IntPtr.Zero, 3, 0, IntPtr.Zero);
        if(handle.IsInvalid) { handle.Dispose(); throw new Win32Exception(Marshal.GetLastWin32Error()); }
        uint returned;
        if(!DeviceIoControl(handle,0x00090018,IntPtr.Zero,0,IntPtr.Zero,0,out returned,IntPtr.Zero) ||
           !DeviceIoControl(handle,0x00090020,IntPtr.Zero,0,IntPtr.Zero,0,out returned,IntPtr.Zero)) {
            int error=Marshal.GetLastWin32Error(); handle.Dispose(); throw new Win32Exception(error);
        }
        return handle;
    }
}
'@
}
function Lock-A1UsbVolumes {
    param([int]$Number)
    Initialize-A1VolumeApi
    $handles = [Collections.Generic.List[IDisposable]]::new()
    try {
        $volumes = @(Get-Partition -DiskNumber $Number | ForEach-Object { $_.AccessPaths } | Where-Object { $_ -match '^\\\\\?\\Volume\{[^}]+\}\\$' } | Sort-Object -Unique)
        foreach ($volume in $volumes) { $handles.Add([A1VolumeApi]::Lock($volume)) }
        return ,$handles
    } catch { foreach ($handle in $handles) { $handle.Dispose() }; throw }
}
function Assert-A1WorkspaceSeparate {
    param([string]$Path, [int]$DiskNumber)
    $partitions = @(Get-Partition -DriveLetter $Path.Substring(0, 1) -ErrorAction Stop)
    if ($partitions.Count -ne 1 -or [int]$partitions[0].DiskNumber -eq $DiskNumber) { throw 'Choose a workspace on another local disk, not the target USB.' }
}
