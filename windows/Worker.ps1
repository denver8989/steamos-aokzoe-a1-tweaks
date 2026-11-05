param([Parameter(Mandatory=$true)][string]$TaskFile)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\Common.ps1"
. "$PSScriptRoot\Rufus.ps1"
. "$PSScriptRoot\Setup.ps1"
function Write-A1Progress([string]$Stage,[string]$Message) {
    $json = @{stage=$Stage;message=$Message} | ConvertTo-Json
    [IO.File]::WriteAllText(($TaskFile+'.status.tmp'),$json)
    Move-Item -LiteralPath ($TaskFile+'.status.tmp') -Destination ($TaskFile+'.status.json') -Force
    Write-Host $Message
}
$exitCode = 1
try {
    $task = Get-Content -Raw -LiteralPath $TaskFile | ConvertFrom-Json
    Assert-A1TaskAction ([string]$task.action)
    $repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    if ($task.action -eq 'prepare') { $selected = Ensure-A1Backend $repo; Write-A1Progress 'done' 'Preparation component ready.'; $exitCode = 0 }
    elseif ($task.action -eq 'image') {
        $source = Assert-A1RegularPath $task.source
        $output = Assert-A1RegularPath $task.output -New
        if ($source -notmatch '\.img(?:\.bz2)?$' -or $output -notmatch '\.img$') { throw 'Choose a Valve recovery download (.img.bz2 or .img). ISO is not supported.' }
        $selected = Ensure-A1Backend $repo
        Write-A1Progress 'patch' 'Creating your A1 recovery image. Large files can take several minutes...'
        Invoke-A1LinuxBackend $selected $repo 'patch' $source $output ([bool]$task.includeDualBoot)
        $message = "Ready: $output. Use Rufus to write this image to a spare USB."
        if ([bool]$task.openRufus) {
            Write-A1Progress 'rufus' 'Image created. Verifying and opening Rufus...'
            try { Open-A1Rufus $output; $message = 'Image ready. In Rufus, choose your spare USB and click START. The selected USB will be erased.' }
            catch { $message = 'Your image was created successfully, but Rufus could not open. Use Open Rufus below to retry, or download it from rufus.ie. Details: '+$_ }
        }
        Write-A1Progress 'done' $message
        $exitCode = 0
    }
    elseif ($task.action -eq 'rufus') {
        Write-A1Progress 'rufus' 'Verifying the image and opening Rufus...'
        Open-A1Rufus $task.source
        Write-A1Progress 'done' 'In Rufus, choose your spare USB and click START. The selected USB will be erased.'
        $exitCode = 0
    }
} catch {
    Write-Error -ErrorAction Continue $_
    if ([string]$_ -match 'A1_RESTART_REQUIRED') {
        Write-A1Progress 'restart' 'Windows needs a restart to finish setup. Save your work and restart when convenient. Reopen this app and click Continue; your image selection has been saved.'
    } else { Write-A1Progress 'error' ([string]$_) }
}
exit $exitCode
