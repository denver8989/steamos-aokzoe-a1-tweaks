# Fixture-only setup lifecycle tests. Never calls Windows/WSL executables or registry.
. (Join-Path $repo 'windows/Setup.ps1')
Assert-A1SetupExit 0
foreach($code in @(1,-1,50)) { Assert-Refused { Assert-A1SetupExit $code } }
foreach($code in @(3010,1641)) {
    $message=''; try { Assert-A1SetupExit $code } catch { $message=[string]$_ }
    Assert-True ($message -ceq 'A1_RESTART_REQUIRED') 'Restart request not recognized'
}
Assert-A1ManagedRegistration ([pscustomobject]@{BasePath='\\?\C:\fixture\environment';Version=2}) 'C:\fixture\environment'
Assert-Refused { Assert-A1ManagedRegistration ([pscustomobject]@{BasePath='C:\unrelated';Version=2}) 'C:\fixture\environment' }
Assert-Refused { Assert-A1ManagedRegistration ([pscustomobject]@{BasePath='C:\fixture\environment';Version=1}) 'C:\fixture\environment' }
Assert-Refused { Assert-A1ManagedRegistration $null 'C:\fixture\environment' }
& {
    $fixture=Join-Path ([IO.Path]::GetTempPath()) ('a1-setup-test-'+[Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($fixture)
    $oldArchitecture=$env:PROCESSOR_ARCHITECTURE
    try {
        $env:PROCESSOR_ARCHITECTURE='AMD64'
        $archive=Join-Path $fixture 'ubuntu-noble-wsl-amd64-24.04lts.rootfs.tar.gz'
        [IO.File]::WriteAllBytes($archive,[byte[]]@(5,6,7))
        $hash=(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
        Assert-A1EnvironmentArchive $archive $hash
        Assert-Refused { Assert-A1EnvironmentArchive $archive ('0'*64) }
        $script:calls=@(); $script:registration=$null; $script:verified=$false
        function Write-A1Progress($Stage,$Message) { }
        function Get-A1DistroRegistration { return $script:registration }
        function Assert-A1EnvironmentArchive($Path,$Sha256) { $script:verified=$true }
        function Invoke-WebRequest { throw 'Unexpected network access in setup test' }
        function wsl.exe {
            $script:calls+=($args -join '|')
            $global:LASTEXITCODE=0
            if ($args[0] -eq '--import') {
                Assert-True $script:verified 'Archive not verified before import'
                Assert-True (($args -join '|') -ceq ('--import|A1-Patcher-Ubuntu-24.04|'+(Join-Path $fixture 'environment')+'|'+$archive+'|--version|2')) 'Unsafe import arguments'
                $script:registration=[pscustomobject]@{BasePath=(Join-Path $fixture 'environment');Version=2}
            }
        }
        function Invoke-A1LinuxBackend($Distro,$Repo,$Action) {
            Assert-True ($Distro -ceq 'A1-Patcher-Ubuntu-24.04') 'Unexpected environment modified'
            $script:calls+=('backend|'+$Action)
            if ($Action -eq 'check') { throw 'Tools missing (fixture)' }
        }
        $selected=Ensure-A1Backend $repo $fixture
        Assert-True ($selected -ceq 'A1-Patcher-Ubuntu-24.04') 'Environment return mixed with command output'
        Assert-True ($script:calls -contains 'backend|prepare') 'Missing tools were not prepared'
        # Reuse should skip import and download entirely.
        $script:calls=@(); $script:verified=$false
        [void](Ensure-A1Backend $repo $fixture)
        Assert-True (-not $script:verified) 'Existing environment unexpectedly downloaded again'
        Assert-True (@($script:calls | Where-Object { $_ -like '--import*' }).Count -eq 0) 'Existing environment imported again'
        # Refuse someone else's environment before any backend changes.
        $script:registration=[pscustomobject]@{BasePath='C:\unrelated';Version=2}
        $script:calls=@()
        Assert-Refused { Ensure-A1Backend $repo $fixture }
        Assert-True (@($script:calls | Where-Object { $_ -like 'backend*' }).Count -eq 0) 'Unrelated environment modified'
        # Windows restart request stops before download, import or preparation.
        function wsl.exe { $global:LASTEXITCODE=1 }
        function Start-Process($FilePath,$Verb,$ArgumentList,[switch]$PassThru,[switch]$Wait) {
            Assert-True ($FilePath -ceq 'wsl.exe' -and $Verb -ceq 'RunAs') 'Unexpected setup elevation'
            Assert-True (($ArgumentList -join '|') -ceq '--install|--no-distribution|--no-launch') 'Unexpected WSL install arguments'
            return [pscustomobject]@{ExitCode=3010}
        }
        $message=''; try { Ensure-A1Backend $repo $fixture } catch { $message=[string]$_ }
        Assert-True ($message -ceq 'A1_RESTART_REQUIRED') 'Setup did not stop for restart'
    } finally {
        $env:PROCESSOR_ARCHITECTURE=$oldArchitecture
        Remove-Item -LiteralPath $fixture -Recurse -Force
    }
}
Write-Host 'PASS: managed setup, checksum refusal, environment reuse/collision refusal, missing tools, elevation and restart handling (all mocked).'
