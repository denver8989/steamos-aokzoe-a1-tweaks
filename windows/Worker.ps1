param([Parameter(Mandatory=$true)][string]$TaskFile)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\Common.ps1"
$exitCode = 1
try {
    $task = Get-Content -Raw -LiteralPath $TaskFile | ConvertFrom-Json
    $repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    if ($task.action -eq 'prepare') { Invoke-A1LinuxBackend $task.distro $repo 'prepare'; $exitCode = 0 }
    elseif ($task.action -eq 'image') {
        $source = Assert-A1RegularPath $task.source
        $output = Assert-A1RegularPath $task.output -New
        if ($source -notmatch '\.img(?:\.bz2)?$' -or $output -notmatch '\.img$') { throw 'Choose .img.bz2/.img input and a new .img output. ISO is not supported.' }
        Invoke-A1LinuxBackend $task.distro $repo 'check'
        Invoke-A1LinuxBackend $task.distro $repo 'patch' $source $output ([bool]$task.includeDualBoot)
        Write-Host "Ready: $output. Flash this image with Etcher to a spare USB."
        $exitCode = 0
    }
    elseif ($task.action -eq 'usb') {
        $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
        if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'USB work requires administrator access.' }
        $number = [int]$task.disk.Number
        Assert-A1SameDisk $task.disk (Get-Disk -Number $number)
        $backup = Assert-A1RegularPath $task.source -New
        $patched = Assert-A1RegularPath $task.output -New
        Assert-A1WorkspaceSeparate $backup $number
        Assert-A1WorkspaceSeparate $patched $number
        $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($backup))
        if ($drive.AvailableFreeSpace -lt (2 * $script:A1RawBytes + 1073741824)) { throw 'Allow at least 18 GiB free for the USB backup and patched image.' }
        Invoke-A1LinuxBackend $task.distro $repo 'check'
        $physical = '\\.\PhysicalDrive' + $number
        $locks = Lock-A1UsbVolumes $number
        try {
            Assert-A1SameDisk $task.disk (Get-Disk -Number $number)
            $raw = [IO.File]::Open($physical, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
            try {
                $file = [IO.File]::Open($backup, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
                try { $hash = Copy-A1Range $raw $file $script:A1RawBytes; $file.Flush($true) } finally { $file.Dispose() }
            } finally { $raw.Dispose() }
        } finally { foreach ($handle in $locks) { $handle.Dispose() } }
        if ($hash -ne $script:A1RawSha) { throw "This USB is not the pristine reviewed Valve image. It may already contain your working fixes. No USB write was performed. The captured prefix is at $backup" }
        Invoke-A1LinuxBackend $task.distro $repo 'patch' $backup $patched ([bool]$task.includeDualBoot)
        $report = Get-Content -Raw -LiteralPath ($patched + '.json') | ConvertFrom-Json
        if ([long](Get-Item -LiteralPath $patched).Length -ne $script:A1RawBytes -or (Get-FileHash -LiteralPath $patched -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$report.output_sha256) { throw 'Patched image verification failed; USB has not been written.' }
        Assert-A1SameDisk $task.disk (Get-Disk -Number $number)
        $locks = Lock-A1UsbVolumes $number
        try {
            Assert-A1SameDisk $task.disk (Get-Disk -Number $number)
            # Recheck pristine bytes immediately before writing, not only before a long patch run.
            $raw = [IO.File]::Open($physical, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::ReadWrite)
            try {
                if ((Copy-A1Range $raw $null $script:A1RawBytes) -cne $script:A1RawSha) { throw 'USB contents changed during preparation. Refusing write.' }
                $raw.Position = 0
                $file = [IO.File]::OpenRead($patched)
                try { $written = Copy-A1Range $file $raw $script:A1RawBytes; $raw.Flush($true) } finally { $file.Dispose() }
                $raw.Position = 0
                $readBack = Copy-A1Range $raw $null $script:A1RawBytes
                if ($written -cne [string]$report.output_sha256 -or $readBack -cne $written) { throw 'USB read-back mismatch. Keep the backup and do not assume this media is ready.' }
            } finally { $raw.Dispose() }
        } finally { foreach ($handle in $locks) { $handle.Dispose() } }
        Write-Host "USB patched and read-back verified. Original first 8.1 GB retained at $backup. The remaining device space was not backed up or written."
        $exitCode = 0
    } else { throw 'Unknown task.' }
} catch {
    Write-Error -ErrorAction Continue $_
    Write-Host 'Operation stopped. Preserve any backup/image files. A failed USB write can leave the media unusable until restored.'
} finally {
    Write-Host ''
    [void](Read-Host 'Press Enter to close this progress window')
}
exit $exitCode
