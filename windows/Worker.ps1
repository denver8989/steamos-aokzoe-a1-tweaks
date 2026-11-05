param([Parameter(Mandatory=$true)][string]$TaskFile)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\Common.ps1"
. "$PSScriptRoot\Rufus.ps1"
$exitCode = 1
try {
    $task = Get-Content -Raw -LiteralPath $TaskFile | ConvertFrom-Json
    Assert-A1TaskAction ([string]$task.action)
    $repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    if ($task.action -eq 'prepare') { Invoke-A1LinuxBackend $task.distro $repo 'prepare'; $exitCode = 0 }
    elseif ($task.action -eq 'image') {
        $source = Assert-A1RegularPath $task.source
        $output = Assert-A1RegularPath $task.output -New
        if ($source -notmatch '\.img(?:\.bz2)?$' -or $output -notmatch '\.img$') { throw 'Choose .img.bz2/.img input and a new .img output. ISO is not supported.' }
        Invoke-A1LinuxBackend $task.distro $repo 'check'
        Invoke-A1LinuxBackend $task.distro $repo 'patch' $source $output ([bool]$task.includeDualBoot)
        Write-Host "Ready: $output. Flash this image with Rufus to a spare USB."
        $exitCode = 0
        if ([bool]$task.openRufus) {
            try { Open-A1Rufus $output }
            catch { Write-Warning ('Image creation succeeded, but Rufus could not be opened: ' + $_ + '. Download Rufus manually from https://rufus.ie/ and select the generated .img.') }
        }
    }
    elseif ($task.action -eq 'rufus') { Open-A1Rufus $task.source; $exitCode = 0 }
} catch {
    Write-Error -ErrorAction Continue $_
    Write-Host 'Operation stopped. Read the error above. This patcher does not write USB devices.'
} finally {
    Write-Host ''
    [void](Read-Host 'Press Enter to close this progress window')
}
exit $exitCode
