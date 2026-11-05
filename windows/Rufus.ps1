Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function Assert-A1RufusSignature {
    param($Signature, [string]$ExpectedSigner)
    if ([string]$Signature.Status -cne 'Valid' -or $null -eq $Signature.SignerCertificate) { throw 'Rufus Windows signature is not valid. The executable will not be launched.' }
    $cn = '(?:^|,\s*)CN=' + [regex]::Escape($ExpectedSigner) + '(?:,|$)'
    if ([string]$Signature.SignerCertificate.Subject -notmatch $cn) { throw 'Rufus signer differs from the expected official publisher. The executable will not be launched.' }
}
function Assert-A1RufusBinary {
    param([string]$Path, $Spec)
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$Spec.sha256) { throw 'Rufus checksum differs from the reviewed official release. The executable will not be launched.' }
    Assert-A1RufusSignature (Get-AuthenticodeSignature -LiteralPath $Path) ([string]$Spec.signer_cn)
}
function Get-A1Rufus {
    param([string]$CacheDirectory='')
    $spec = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'rufus.json') | ConvertFrom-Json
    if ([string]::IsNullOrEmpty($CacheDirectory)) { $CacheDirectory = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) ('A1-Patcher\tools\Rufus\' + $spec.version) }
    [void][IO.Directory]::CreateDirectory($CacheDirectory)
    $exe = Join-Path $CacheDirectory $spec.file
    if (-not (Test-Path -LiteralPath $exe)) {
        $partial = Join-Path $CacheDirectory (([Guid]::NewGuid().ToString('N')) + '.exe')
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Write-Host ('Downloading official Rufus ' + $spec.version + ' from ' + $spec.url)
            Invoke-WebRequest -UseBasicParsing -Uri $spec.url -OutFile $partial
            Assert-A1RufusBinary $partial $spec
            Move-Item -LiteralPath $partial -Destination $exe
        } finally { if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial } }
    }
    Assert-A1RufusBinary $exe $spec
    return $exe
}
function Assert-A1PatchedImage {
    param([string]$Path)
    $image = Assert-A1RegularPath $Path
    if ($image -notmatch '\.img$') { throw 'Select the generated .img, not the original .img.bz2 or an ISO.' }
    $reportPath = $image + '.json'
    if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) { throw 'Keep the patcher checksum report beside its .img file. Alternatively, select the image manually in Rufus.' }
    $report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
    if ([long]$report.bytes -ne [long](Get-Item -LiteralPath $image).Length -or [string]$report.output_sha256 -notmatch '^[0-9a-f]{64}$' -or (Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$report.output_sha256) { throw 'Patched image differs from its saved checksum report. Rufus will not be opened with this image.' }
    return $image
}
function Open-A1Rufus {
    param([string]$Image)
    $verified = Assert-A1PatchedImage $Image
    $exe = Get-A1Rufus
    Write-Host 'Opening Rufus with the verified image. Select the correct USB, review Rufus warnings and click START yourself. The selected USB will be erased.'
    # Rufus v4.15 source documents -i/--iso as the image-path option; it also accepts raw disk images.
    # No drive selection, extra-device or unattended-write arguments are passed.
    Start-Process -FilePath $exe -Verb RunAs -ArgumentList ('-i "' + $verified + '"')
}
