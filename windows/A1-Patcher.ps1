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
$form.Size = New-Object Drawing.Size(760, 660)
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
function Launch-Worker($Task, [switch]$Admin) {
    $directory = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'A1-Patcher\tasks'
    [void][IO.Directory]::CreateDirectory($directory)
    $file = Join-Path $directory (([Guid]::NewGuid().ToString()) + '.json')
    [IO.File]::WriteAllText($file, ($Task | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    $script = Join-Path $PSScriptRoot 'Worker.ps1'
    # Windows filenames cannot contain quotes. -File parses these as path arguments, not script text.
    $arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $script + '" -TaskFile "' + $file + '"'
    if ($Admin) { Start-Process powershell.exe -Verb RunAs -ArgumentList $arguments }
    else { Start-Process powershell.exe -ArgumentList $arguments }
}
Add-Button 'Prepare Linux backend (install tools in selected WSL distribution)' 251 {
    $selected = Selected-Distro
    if ([Windows.Forms.MessageBox]::Show("Install the required Linux packages inside $selected? This uses apt and internet access. No Windows disk is repartitioned.", 'Prepare backend', 'YesNo', 'Question') -eq 'Yes') {
        Launch-Worker @{action='prepare';distro=$selected}
    }
}
Add-Label '3. Recommended: create a patched image file, then flash it to a spare USB with Etcher. Keep your known working USB intact.' 302
Add-Button 'Choose Valve image and create A1 recovery image' 353 {
    $selected = Selected-Distro
    $open = New-Object Windows.Forms.OpenFileDialog
    $open.Filter = 'Valve recovery image (*.img.bz2;*.img)|*.img.bz2;*.img'
    if ($open.ShowDialog() -ne 'OK') { return }
    $save = New-Object Windows.Forms.SaveFileDialog
    $save.Filter = 'Disk image (*.img)|*.img'; $save.FileName = 'aokzoe-a1-recovery.img'; $save.OverwritePrompt = $true
    if ($save.ShowDialog() -ne 'OK') { return }
    $source = Assert-A1RegularPath $open.FileName
    $output = Assert-A1RegularPath $save.FileName -New
    Launch-Worker @{action='image';distro=$selected;source=$source;output=$output;includeDualBoot=[bool]$dualBox.Checked}
}
$dualBox = New-Object Windows.Forms.CheckBox
$dualBox.Text = 'Include experimental Install Alongside Windows option (32+ GiB trailing unallocated space)'
$dualBox.Location = New-Object Drawing.Point(20, 396); $dualBox.Size = New-Object Drawing.Size(700, 25); $form.Controls.Add($dualBox)
Add-Label 'Alternative (experimental): patch a freshly written, unmodified Valve USB. Requires administrator access, a hardware serial, a separate workspace with 18 GiB free, and full image verification. Previously customized USBs are refused.' 428 55
Add-Button 'Select a fresh Valve USB to patch (experimental)' 493 {
    $selected = Selected-Distro
    $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        $script = Join-Path $PSScriptRoot 'A1-Patcher.ps1'
        Start-Process powershell.exe -Verb RunAs -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "' + $script + '"')
        return
    }
    $choices = @(Get-Disk | Where-Object { try { Assert-A1UsbDisk $_; $true } catch { $false } })
    if ($choices.Count -eq 0) { throw 'No eligible USB found. Use the image-file workflow instead.' }
    $picker = New-Object Windows.Forms.Form
    $picker.Text='Select USB - no internal disks'; $picker.Size=New-Object Drawing.Size(650,240); $picker.StartPosition='CenterParent'
    $list=New-Object Windows.Forms.ComboBox; $list.DropDownStyle='DropDownList'; $list.Location=New-Object Drawing.Point(20,20); $list.Size=New-Object Drawing.Size(590,30)
    foreach($disk in $choices) { [void]$list.Items.Add(('Disk {0}: {1}, {2:N1} GiB, serial {3}' -f $disk.Number,$disk.FriendlyName,($disk.Size/1GB),$disk.SerialNumber)) }
    $list.SelectedIndex=0; $picker.Controls.Add($list)
    $label=New-Object Windows.Forms.Label; $label.Text='Type PATCH followed by the disk number (for example PATCH 4):'; $label.Location=New-Object Drawing.Point(20,65); $label.Size=New-Object Drawing.Size(590,25); $picker.Controls.Add($label)
    $confirm=New-Object Windows.Forms.TextBox; $confirm.Location=New-Object Drawing.Point(20,95); $confirm.Size=New-Object Drawing.Size(590,25); $picker.Controls.Add($confirm)
    $ok=New-Object Windows.Forms.Button; $ok.Text='Continue'; $ok.DialogResult='OK'; $ok.Location=New-Object Drawing.Point(460,140); $picker.Controls.Add($ok)
    if($picker.ShowDialog($form) -ne 'OK') { return }
    $disk=$choices[$list.SelectedIndex]
    if($confirm.Text -cne ('PATCH '+$disk.Number)) { throw 'Confirmation did not match. No USB write was requested.' }
    $folder=New-Object Windows.Forms.FolderBrowserDialog; $folder.Description='Choose a workspace on another disk with at least 18 GiB free.'
    if($folder.ShowDialog() -ne 'OK') { return }
    $id=[Guid]::NewGuid().ToString('N')
    $source=Join-Path $folder.SelectedPath ('valve-original-prefix-'+$id+'.img')
    $output=Join-Path $folder.SelectedPath ('a1-patched-'+$id+'.img')
    Launch-Worker @{action='usb';distro=$selected;source=$source;output=$output;includeDualBoot=[bool]$dualBox.Checked;disk=(Get-A1DiskIdentity $disk)} -Admin
}
Add-Label 'After booting the USB: choose the matching install workflow. Optional Decky/TDP/theme setup runs only after SteamOS is fully installed. Preview: Windows hardware validation is pending.' 543 70
if ($SmokeTest) {
    if ($form.Controls.Count -lt 10) { throw 'Launcher controls were not constructed.' }
    $form.Dispose()
    Write-Host 'PASS: Windows Forms launcher constructs without displaying dialogs, querying WSL or accessing storage.'
    return
}
Refresh-Distros
[void]$form.ShowDialog()
