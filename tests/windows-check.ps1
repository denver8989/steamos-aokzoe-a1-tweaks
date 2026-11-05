Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
foreach($file in (Get-ChildItem (Join-Path $repo 'windows/*.ps1'))) {
    $tokens=$null; $errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
    if($errors) { throw ($errors | Out-String) }
}
. (Join-Path $repo 'windows/Common.ps1')
function Assert-True($Condition,[string]$Message) { if(-not $Condition) { throw $Message } }
function Assert-Refused([scriptblock]$Action) { $failed=$false; try { & $Action } catch { $failed=$true }; Assert-True $failed 'Unsafe case was accepted' }
. (Join-Path $repo 'windows/Rufus.ps1')
foreach($action in @('prepare','image','rufus')) { Assert-A1TaskAction $action }
foreach($action in @('usb','write','disk','format','IMAGE','')) { Assert-Refused { Assert-A1TaskAction $action } }
$valid=[pscustomobject]@{Status='Valid';SignerCertificate=[pscustomobject]@{Subject='CN=Akeo Consulting, O=Akeo Consulting, C=IE'}}
Assert-A1RufusSignature $valid 'Akeo Consulting'
foreach($subject in @('CN=Other Publisher, O=Akeo Consulting','CN=Akeo Consulting Fake, O=Other','O=Akeo Consulting')) {
    $bad=[pscustomobject]@{Status='Valid';SignerCertificate=[pscustomobject]@{Subject=$subject}}
    Assert-Refused { Assert-A1RufusSignature $bad 'Akeo Consulting' }
}
Assert-Refused { Assert-A1RufusSignature ([pscustomobject]@{Status='HashMismatch';SignerCertificate=$valid.SignerCertificate}) 'Akeo Consulting' }
Assert-Refused { Assert-A1RufusSignature ([pscustomobject]@{Status='Valid';SignerCertificate=$null}) 'Akeo Consulting' }
& {
    $fixture=Join-Path ([IO.Path]::GetTempPath()) ('a1-rufus-test-'+[Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($fixture)
    try {
        function Assert-A1RegularPath([string]$Path) { return $Path }
        $image=Join-Path $fixture 'patched image.img'
        [IO.File]::WriteAllBytes($image,[byte[]]@(1,2,3,4))
        $hash=(Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant()
        @{bytes=4;output_sha256=$hash} | ConvertTo-Json | Set-Content -LiteralPath ($image+'.json')
        Assert-True ((Assert-A1PatchedImage $image) -eq $image) 'Valid image report rejected'
        @{bytes=5;output_sha256=$hash} | ConvertTo-Json | Set-Content -LiteralPath ($image+'.json')
        Assert-Refused { Assert-A1PatchedImage $image }
        @{bytes=4;output_sha256=('0'*64)} | ConvertTo-Json | Set-Content -LiteralPath ($image+'.json')
        Assert-Refused { Assert-A1PatchedImage $image }
        function Get-AuthenticodeSignature { return $valid }
        Assert-A1RufusBinary $image ([pscustomobject]@{sha256=$hash;signer_cn='Akeo Consulting'})
        Assert-Refused { Assert-A1RufusBinary $image ([pscustomobject]@{sha256=('0'*64);signer_cn='Akeo Consulting'}) }
    } finally { Remove-Item -LiteralPath $fixture -Recurse -Force }
}
& {
    function Assert-A1PatchedImage { return 'C:\synthetic path\patched.img' }
    function Get-A1Rufus { return 'C:\synthetic path\rufus.exe' }
    $script:launchObserved=$false
    function Start-Process($FilePath,$Verb,$ArgumentList) {
        Assert-True ($FilePath -ceq 'C:\synthetic path\rufus.exe') 'Unexpected executable'
        Assert-True ($Verb -ceq 'RunAs') 'Rufus requires elevation'
        Assert-True ($ArgumentList -ceq '-i "C:\synthetic path\patched.img"') 'Unexpected Rufus arguments'
        $script:launchObserved=$true
    }
    Open-A1Rufus 'fixture'
    Assert-True $script:launchObserved 'Rufus handoff was not observed'
}
Write-Host 'PASS: PowerShell syntax, action refusal, Rufus checksum/publisher guards, image reports and mocked launch. No physical disks or executables accessed.'

& (Join-Path $PSScriptRoot 'windows-setup-check.ps1')

if ($env:OS -eq 'Windows_NT') { & (Join-Path $repo 'windows/A1-Patcher.ps1') -SmokeTest }
