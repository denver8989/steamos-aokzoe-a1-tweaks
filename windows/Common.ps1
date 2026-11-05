Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-A1TaskAction {
    param([string]$Action)
    if ($Action -cnotin @('prepare','image','rufus')) { throw 'Unsupported action. This patcher handles image files only; use Rufus to write USB media.' }
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
