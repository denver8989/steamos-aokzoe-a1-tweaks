# Windows 10/11 launcher. All Linux filesystem work runs inside the chosen WSL distro.
param([switch]$SmokeTest)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This graphical launcher runs on Windows.' }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
. "$PSScriptRoot\Common.ps1"
[Windows.Forms.Application]::EnableVisualStyles()
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$form = New-Object Windows.Forms.Form
$form.Text = 'AOKZOE A1 - prepare SteamOS recovery media'
$form.Size = New-Object Drawing.Size(760, 635)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
function Add-Label([string]$Text, [int]$Top, [int]$Height=45) {
    $label = New-Object Windows.Forms.Label
    $label.Text = $Text; $label.Location = New-Object Drawing.Point(20, $Top); $label.Size = New-Object Drawing.Size(700, $Height)
    $form.Controls.Add($label)
}
function Show-Error($Exception) { [void][Windows.Forms.MessageBox]::Show([string]$Exception, 'Operation stopped', 'OK', 'Error') }
function Add-Button([string]$Text, [int]$Top, [scriptblock]$Action, [int]$Left=20, [int]$Width=700) {
    $button = New-Object Windows.Forms.Button
    $button.Text = $Text; $button.Location = New-Object Drawing.Point($Left, $Top); $button.Size = New-Object Drawing.Size($Width, 34)
    $button.Add_Click({ try { & $Action } catch { Show-Error $_ } }.GetNewClosure())
    $form.Controls.Add($button)
}
Add-Label 'Use your own official Valve .img.bz2/.img. This toolkit does not host SteamOS. ISO files are not supported.' 15
Add-Button '1. Open Valve download and license page' 63 { Start-Process 'https://store.steampowered.com/steamos/download/?ver=steamdeck' }
Add-Label '2. One-time Linux backend: WSL 2 + Ubuntu/Debian. Windows setup may need administrator access and a restart. The backend must load Btrfs.' 108
Add-Button 'Install WSL + Ubuntu (one-time)' 159 {
    if ([Windows.Forms.MessageBox]::Show('This enables Microsoft WSL and installs Ubuntu. It may require a restart. Continue?', 'Install WSL', 'YesNo', 'Question') -eq 'Yes') {
        Start-Process wsl.exe -Verb RunAs -ArgumentList @('--install','-d','Ubuntu','--no-launch')
    }
} 20 340
Add-Button 'Open WSL setup instructions' 159 { Start-Process 'https://learn.microsoft.com/en-us/windows/wsl/install' } 380 340
$distro = New-Object Windows.Forms.ComboBox
$distro.Location = New-Object Drawing.Point(20, 211); $distro.Size = New-Object Drawing.Size(430, 30); $distro.DropDownStyle = 'DropDownList'; $form.Controls.Add($distro)
function Refresh-Distros {
    $distro.Items.Clear()
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { return }
    $names = @(& wsl.exe --list --quiet)
    if ($LASTEXITCODE -ne 0) { return }
    foreach ($name in $names) {
        $clean = ([string]$name).Replace([string][char]0, '').Trim()
        if ($clean -and $clean -notmatch '^docker-desktop') { [void]$distro.Items.Add($clean) }
    }
    if ($distro.Items.Count -gt 0) { $distro.SelectedIndex = 0 }
}
Add-Button 'Refresh WSL distributions' 205 { Refresh-Distros } 470 250
function Selected-Distro {
    if ($null -eq $distro.SelectedItem) { throw 'Install and initialize Ubuntu, restart if requested, then refresh this list.' }
    return [string]$distro.SelectedItem
}
function Launch-Worker($Task) {
    $directory = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'A1-Patcher\tasks'
    [void][IO.Directory]::CreateDirectory($directory)
    $file = Join-Path $directory (([Guid]::NewGuid().ToString()) + '.json')
    [IO.File]::WriteAllText($file, ($Task | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    $script = Join-Path $PSScriptRoot 'Worker.ps1'
    # Windows filenames cannot contain quotes. -File parses these as path arguments, not script text.
    $arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $script + '" -TaskFile "' + $file + '"'
    Start-Process powershell.exe -ArgumentList $arguments
}
Add-Button 'Prepare Linux backend (install tools in selected WSL distribution)' 251 {
    $selected = Selected-Distro
    if ([Windows.Forms.MessageBox]::Show("Install the required Linux packages inside $selected? This uses apt and internet access. No Windows disk is repartitioned.", 'Prepare backend', 'YesNo', 'Question') -eq 'Yes') {
        Launch-Worker @{action='prepare';distro=$selected}
    }
}
Add-Label '3. Patch a local image, then write that image with Rufus, following Valve''s Windows instructions. Keep your known working USB intact.' 302
$dualBox = New-Object Windows.Forms.CheckBox
$dualBox.Text = 'Include experimental Install Alongside Windows option (32+ GiB trailing unallocated space)'
$dualBox.Location = New-Object Drawing.Point(20, 350); $dualBox.Size = New-Object Drawing.Size(700, 25); $form.Controls.Add($dualBox)
$rufusBox = New-Object Windows.Forms.CheckBox
$rufusBox.Text = 'Open Rufus when finished (download the verified official portable release if needed)'
$rufusBox.Location = New-Object Drawing.Point(20, 381); $rufusBox.Size = New-Object Drawing.Size(700, 25); $form.Controls.Add($rufusBox)
Add-Button 'Choose Valve image and create A1 recovery image' 417 {
    $selected = Selected-Distro
    $open = New-Object Windows.Forms.OpenFileDialog
    $open.Filter = 'Valve recovery image (*.img.bz2;*.img)|*.img.bz2;*.img'
    if ($open.ShowDialog() -ne 'OK') { return }
    $save = New-Object Windows.Forms.SaveFileDialog
    $save.Filter = 'Disk image (*.img)|*.img'; $save.FileName = 'aokzoe-a1-recovery.img'; $save.OverwritePrompt = $true
    if ($save.ShowDialog() -ne 'OK') { return }
    $source = Assert-A1RegularPath $open.FileName
    $output = Assert-A1RegularPath $save.FileName -New
    Launch-Worker @{action='image';distro=$selected;source=$source;output=$output;includeDualBoot=[bool]$dualBox.Checked;openRufus=[bool]$rufusBox.Checked}
}
Add-Button 'Open Rufus for an already patched image (official download if needed)' 465 {
    $open = New-Object Windows.Forms.OpenFileDialog
    $open.Filter = 'Patched recovery image (*.img)|*.img'
    if ($open.ShowDialog() -ne 'OK') { return }
    Launch-Worker @{action='rufus';source=(Assert-A1RegularPath $open.FileName)}
}
Add-Label '4. In Rufus, verify the USB and patched image, then click START. Rufus will erase the selected USB. This patcher does not select or write physical disks. After booting the USB, choose full reinstall or the optional dual-boot workflow.' 512 70
if ($SmokeTest) {
    if ($form.Controls.Count -lt 10) { throw 'Launcher controls were not constructed.' }
    $form.Dispose()
    Write-Host 'PASS: Windows Forms launcher constructs without displaying dialogs, querying WSL or accessing storage.'
    return
}
Refresh-Distros
[void]$form.ShowDialog()
