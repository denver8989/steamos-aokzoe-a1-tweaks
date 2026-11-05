# Guided Windows 10/11 x64 launcher. Linux setup is managed by the worker.
param([switch]$SmokeTest)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This graphical launcher runs on Windows.' }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
. "$PSScriptRoot\Common.ps1"
[Windows.Forms.Application]::EnableVisualStyles()
$form = New-Object Windows.Forms.Form
$form.Text = 'AOKZOE A1 - create SteamOS recovery media'
$form.Size = New-Object Drawing.Size(760, 640)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'; $form.MaximizeBox = $false
$script:running = $null; $script:taskPath = ''; $script:pending = ''
$script:currentLog = ''; $script:lastStage = ''
function Add-Label([string]$Text,[int]$Top,[int]$Height=45) {
    $label = New-Object Windows.Forms.Label
    $label.Text=$Text; $label.Location=New-Object Drawing.Point(20,$Top); $label.Size=New-Object Drawing.Size(700,$Height)
    $form.Controls.Add($label)
    return $label
}
function Show-Error($Exception) { [void][Windows.Forms.MessageBox]::Show([string]$Exception,'Operation stopped','OK','Error') }
function Add-Button([string]$Text,[int]$Top,[scriptblock]$Action,[int]$Left=20,[int]$Width=700) {
    $button=New-Object Windows.Forms.Button
    $button.Text=$Text; $button.Location=New-Object Drawing.Point($Left,$Top); $button.Size=New-Object Drawing.Size($Width,34)
    $button.Add_Click({ try { & $Action } catch { Show-Error $_ } }.GetNewClosure())
    $form.Controls.Add($button)
    return $button
}
[void](Add-Label 'Create a SteamOS recovery USB for the original AOKZOE A1. Download the Valve recovery file, choose it below, then follow the steps in Rufus.' 15)
$download=Add-Button '1. Download SteamOS from Valve' 65 { Start-Process 'https://store.steampowered.com/steamos/download/?ver=steamdeck' }
[void](Add-Label '2. Choose the downloaded recovery file (.img.bz2 or .img). You can select the compressed download directly.' 110)
$script:source=''
$chosen=Add-Label 'No recovery file selected.' 195 30
$choose=Add-Button 'Choose recovery file...' 157 {
    $dialog=New-Object Windows.Forms.OpenFileDialog
    $dialog.Filter='Valve recovery download (*.img.bz2;*.img)|*.img.bz2;*.img'
    if ($dialog.ShowDialog() -eq 'OK') {
        $script:source=Assert-A1RegularPath $dialog.FileName
        $chosen.Text=[IO.Path]::GetFileName($script:source)
    }
}
$dualBox=New-Object Windows.Forms.CheckBox
$dualBox.Text='Include experimental option to install alongside Windows'
$dualBox.Location=New-Object Drawing.Point(20,233); $dualBox.Size=New-Object Drawing.Size(700,25); $form.Controls.Add($dualBox)
$rufusBox=New-Object Windows.Forms.CheckBox
$rufusBox.Text='Open Rufus when ready (downloads verified official Rufus if needed)'; $rufusBox.Checked=$true
$rufusBox.Location=New-Object Drawing.Point(20,264); $rufusBox.Size=New-Object Drawing.Size(700,25); $form.Controls.Add($rufusBox)
[void](Add-Label 'First use downloads the preparation component (WSL 2 + Ubuntu, about 340 MB plus tools). Windows may ask for administrator approval and a restart. Setup is automatic; no Linux account is needed.' 303 52)
function Launch-Worker($Task,[string]$Existing='') {
    if ($null -ne $script:running) { throw 'Preparation is already running.' }
    $directory=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'A1-Patcher\tasks'
    [void][IO.Directory]::CreateDirectory($directory)
    $script:pending=Join-Path $directory 'pending.txt'
    $file=$Existing
    if (-not $file) {
        $file=Join-Path $directory (([Guid]::NewGuid().ToString())+'.json')
        [IO.File]::WriteAllText($file,($Task | ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
    }
    [IO.File]::WriteAllText($script:pending,$file)
    $script:taskPath=$file; $script:currentLog=$file+'.log'; $script:lastStage=''
    $statusFile=$file+'.status.json'
    if (Test-Path -LiteralPath $statusFile) { Remove-Item -LiteralPath $statusFile }
    $worker=Join-Path $PSScriptRoot 'Worker.ps1'
    $arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$worker+'" -TaskFile "'+$file+'"'
    $script:running=Start-Process powershell.exe -ArgumentList $arguments -WindowStyle Hidden -RedirectStandardOutput $script:currentLog -RedirectStandardError ($file+'.error.log') -PassThru
    $status.Text='Starting preparation...'; $progress.Style='Marquee'
    $create.Enabled=$false; $choose.Enabled=$false; $resume.Enabled=$false; $rufus.Enabled=$false
}
$create=Add-Button '3. Create recovery image' 367 {
    if (-not $script:source) { throw 'Choose your downloaded Valve recovery file first.' }
    $save=New-Object Windows.Forms.SaveFileDialog
    $save.Filter='Recovery image (*.img)|*.img'; $save.FileName='aokzoe-a1-recovery.img'
    if ($save.ShowDialog() -ne 'OK') { return }
    $output=Assert-A1RegularPath $save.FileName -New
    Launch-Worker @{action='image';source=$script:source;output=$output;includeDualBoot=[bool]$dualBox.Checked;openRufus=[bool]$rufusBox.Checked}
}
$status=Add-Label 'Ready. Keep your existing working USB safe; use a spare 16 GB or larger USB.' 413 65
$progress=New-Object Windows.Forms.ProgressBar
$progress.Location=New-Object Drawing.Point(20,481); $progress.Size=New-Object Drawing.Size(700,15); $form.Controls.Add($progress)
$resume=Add-Button 'Continue saved preparation' 509 {
    $saved=Get-Content -Raw -LiteralPath $script:pending
    $task=Get-Content -Raw -LiteralPath $saved | ConvertFrom-Json
    if ($task.action -eq 'image') { [void](Assert-A1RegularPath $task.source); [void](Assert-A1RegularPath $task.output -New) }
    Launch-Worker $task $saved
} 20 340
$resume.Enabled=$false
$log=Add-Button 'View progress logs' 509 {
    if ($script:currentLog) {
        foreach ($path in @($script:currentLog,($script:currentLog -replace '\.log$','.error.log'))) {
            if (Test-Path -LiteralPath $path) { Start-Process notepad.exe -ArgumentList ('"'+$path+'"') }
        }
    }
} 380 340
$rufus=Add-Button 'Open Rufus with an existing patched image...' 553 {
    $dialog=New-Object Windows.Forms.OpenFileDialog; $dialog.Filter='Patched recovery image (*.img)|*.img'
    if ($dialog.ShowDialog() -eq 'OK') { Launch-Worker @{action='rufus';source=(Assert-A1RegularPath $dialog.FileName)} }
}
$timer=New-Object Windows.Forms.Timer; $timer.Interval=500
function Read-A1Status {
    try {
        $file=$script:taskPath+'.status.json'
        if (Test-Path -LiteralPath $file) {
            $state=Get-Content -Raw -LiteralPath $file | ConvertFrom-Json
            $status.Text=$state.message; $script:lastStage=$state.stage
        }
    } catch { } # Atomic status replacement can briefly contend with reads.
}
$timer.Add_Tick({
    if ($null -eq $script:running) { return }
    Read-A1Status
    if ($script:running.HasExited) {
        Read-A1Status
        $script:running.Dispose(); $script:running=$null
        $progress.Style='Blocks'; $progress.Value=0
        $create.Enabled=$true; $choose.Enabled=$true; $rufus.Enabled=$true
        if ($script:lastStage -eq 'done') {
            if (Test-Path -LiteralPath $script:pending) { Remove-Item -LiteralPath $script:pending }
        } else {
            $resume.Enabled=$true
            if ($script:lastStage -notin @('error','restart')) { $status.Text='Preparation stopped unexpectedly. View the progress log for details, then try again.' }
        }
    }
})
$form.Add_FormClosing({ param($sender,$event)
    if ($null -ne $script:running) {
        $event.Cancel=$true
        [void][Windows.Forms.MessageBox]::Show('Preparation is running. Please wait for it to finish before closing this app.','Preparation running','OK','Information')
    }
})
if ($SmokeTest) {
    if ($form.Controls.Count -lt 10 -or -not $rufusBox.Checked) { throw 'Guided launcher controls were not constructed.' }
    $timer.Dispose(); $form.Dispose()
    Write-Host 'PASS: guided Windows launcher constructs without displaying dialogs, querying WSL or accessing storage.'
    return
}
$script:pending=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'A1-Patcher\tasks\pending.txt'
if (Test-Path -LiteralPath $script:pending) {
    $resume.Enabled=$true
    $status.Text='A saved preparation is available. Click Continue to resume after setup or a restart.'
    try { $script:currentLog=(Get-Content -Raw -LiteralPath $script:pending)+'.log' } catch { }
}
$timer.Start()
[void]$form.ShowDialog()
$timer.Dispose(); $form.Dispose()
