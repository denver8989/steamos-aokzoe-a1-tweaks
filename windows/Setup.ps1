Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:A1Distro = 'A1-Patcher-Ubuntu-24.04'
function Get-A1DistroRegistration {
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
    if (Test-Path $key) {
        foreach ($entry in (Get-ChildItem $key)) {
            $value = Get-ItemProperty $entry.PSPath
            if ($value.DistributionName -ceq $script:A1Distro) { return $value }
        }
    }
    return $null
}
function Assert-A1ManagedRegistration {
    param($Registration, [string]$Directory)
    if ($null -eq $Registration) { throw 'The preparation environment was not registered. See the progress log.' }
    $actual = ([string]$Registration.BasePath) -replace '^\\\\\?\\',''
    if ($actual.TrimEnd('\') -ine $Directory.TrimEnd('\') -or [int]$Registration.Version -ne 2) {
        throw 'An environment with this name already exists in another location or uses WSL 1. It has been left untouched. Contact support with the progress log.'
    }
}
function Assert-A1SetupExit {
    param([int]$Code)
    if ($Code -in @(3010,1641)) { throw 'A1_RESTART_REQUIRED' }
    if ($Code -ne 0) { throw 'Windows could not finish installing the preparation component. Restart Windows and try Continue. If this persists, check that virtualization is enabled or contact support with the log.' }
}
function Ensure-A1Backend {
    param([string]$Repo,[string]$BaseDirectory='')
    if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'This preview requires 64-bit Intel/AMD Windows.' }
    $base = $BaseDirectory
    if (-not $base) { $base = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'A1-Patcher' }
    $directory = Join-Path $base 'environment'
    Write-A1Progress 'setup' 'Checking the preparation component...'
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw 'Windows is missing its WSL installer. Install current Windows updates, restart, then reopen this app.' }
    & wsl.exe --status | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-A1Progress 'setup' 'Installing the Windows preparation component. Approve the Windows administrator prompt. A restart may be needed.'
        $process = Start-Process wsl.exe -Verb RunAs -ArgumentList @('--install','--no-distribution','--no-launch') -PassThru -Wait
        Assert-A1SetupExit ([int]$process.ExitCode)
        & wsl.exe --status | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'A1_RESTART_REQUIRED' }
    }
    $registration = Get-A1DistroRegistration
    if ($null -eq $registration) {
        $spec = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'ubuntu.json') | ConvertFrom-Json
        [void][IO.Directory]::CreateDirectory($base)
        $archive = Join-Path $base $spec.file
        Write-A1Progress 'setup' 'Downloading the preparation environment (about 340 MB, first use only)...'
        if (-not (Test-Path -LiteralPath $archive)) {
            $partial = $archive + '.download'
            try {
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                $ProgressPreference = 'SilentlyContinue'
                Invoke-WebRequest -UseBasicParsing -Uri $spec.url -OutFile $partial
                Assert-A1EnvironmentArchive $partial $spec.sha256
                Move-Item -LiteralPath $partial -Destination $archive
            } finally { if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial } }
        }
        Assert-A1EnvironmentArchive $archive $spec.sha256
        # Never import over a partially created or unrelated directory.
        if (Test-Path -LiteralPath $directory) { throw 'An incomplete preparation environment exists. Contact support with the log; no files were removed.' }
        Write-A1Progress 'setup' 'Preparing the environment. No Linux account or password is needed...'
        & wsl.exe --import $script:A1Distro $directory $archive --version 2 | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'The preparation environment could not start. Restart Windows and try again. If this persists, virtualization may need enabling in the PC settings. See the log for details.' }
        $registration = Get-A1DistroRegistration
    }
    Assert-A1ManagedRegistration $registration $directory
    Write-A1Progress 'setup' 'Checking image preparation tools...'
    try { Invoke-A1LinuxBackend $script:A1Distro $Repo 'check' | Out-Host }
    catch {
        Write-A1Progress 'setup' 'Installing image preparation tools (first use only)...'
        Invoke-A1LinuxBackend $script:A1Distro $Repo 'prepare' | Out-Host
    }
    return $script:A1Distro
}
function Assert-A1EnvironmentArchive {
    param([string]$Path,[string]$Sha256)
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Sha256) {
        throw 'The preparation download did not pass verification. No environment was imported. Contact support or retry after removing the cached download.'
    }
}
