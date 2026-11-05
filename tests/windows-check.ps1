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
$valid=[pscustomobject]@{Number=5;BusType='USB';IsBoot=$false;IsSystem=$false;IsReadOnly=$false;IsOffline=$false;PartitionStyle='GPT';LogicalSectorSize=512;Size=[long]32000000000;SerialNumber='SYNTHETIC';UniqueId='SYNTHETIC-UUID';Path='SYNTHETIC-PNP'}
Assert-A1UsbDisk $valid
$identity=Get-A1DiskIdentity $valid
Assert-A1SameDisk $identity $valid
foreach($entry in @(@('BusType','NVMe'),@('IsBoot',$true),@('IsSystem',$true),@('IsReadOnly',$true),@('IsOffline',$true),@('LogicalSectorSize',4096),@('SerialNumber',''),@('Size',1024))) {
    $changed=$valid.PSObject.Copy(); $changed.($entry[0])=$entry[1]
    Assert-Refused { Assert-A1UsbDisk $changed }
}
$changed=$valid.PSObject.Copy(); $changed.SerialNumber='OTHER'; Assert-Refused { Assert-A1SameDisk $identity $changed }
$bytes=[Text.Encoding]::UTF8.GetBytes('synthetic USB copy fixture')
$source=[IO.MemoryStream]::new($bytes); $dest=[IO.MemoryStream]::new()
try {
    $hash=Copy-A1Range $source $dest $bytes.Length
    Assert-True ([Text.Encoding]::UTF8.GetString($dest.ToArray()) -ceq 'synthetic USB copy fixture') 'Copy changed bytes'
    $dest.Position=0; $check=Copy-A1Range $dest $null $bytes.Length
    Assert-True ($hash -ceq $check) 'Read-back hash differs'
    Assert-Refused { Copy-A1Range $dest $null 1 }
} finally { $source.Dispose(); $dest.Dispose() }
Initialize-A1VolumeApi
Write-Host 'PASS: PowerShell syntax, USB boot/system/read-only/transport/identity/sector/size refusals, bounded copy/hash/read-back, EOF refusal and volume-lock API compilation. No physical storage accessed.'

if ($env:OS -eq 'Windows_NT') { & (Join-Path $repo 'windows/A1-Patcher.ps1') -SmokeTest }
