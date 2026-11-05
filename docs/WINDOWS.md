# Windows preparation workflow (preview)

Extract the **ZIP** release on Windows 10/11 x64 and double-click **Start-A1-Patcher-Windows.cmd**. Keep the whole extracted folder together. The launcher uses built-in PowerShell and file dialogs; Python is not required on Windows itself.

## Guided workflow

1. Click **Download SteamOS from Valve**, obtain the reviewed recovery file and accept Valve's terms. It is `.img.bz2` or `.img`, not an ISO. Only the version in SOURCES.md is accepted.
2. Click **Choose recovery file** and select the download directly; no manual decompression is needed.
3. Optionally include the experimental install-alongside-Windows recovery action. Leave **Open Rufus when ready** enabled for the guided flow.
4. Click **Create recovery image**, choose a new output filename and let the app prepare everything. Allow at least 9 GiB for the output plus several GiB for the preparation environment.
5. If Windows requests administrator approval, approve component installation. If a restart is required, save your work and restart when convenient. Reopen the app and click **Continue saved preparation**. The app never restarts the PC automatically.
6. When Rufus opens, choose the correct spare USB and click **START**. This erases that USB. Use a 16 GB or larger spare; its capacity must exceed the 8,120,172,544-byte image. Preserve your previous successful USB.
7. Close Rufus, safely eject the USB and boot the A1.

Progress appears in the app. **View progress logs** opens technical details for troubleshooting. No distribution picker, Linux account, password or terminal commands are required. If a failed image write leaves a partial output, choose a new output filename; existing files are never overwritten.

## Automatic first-use setup

The app uses Microsoft WSL 2 to edit Linux filesystems. It installs the Windows component when missing, downloads a checksum-pinned official Ubuntu 24.04 root filesystem (about 340 MB), imports it as **A1-Patcher-Ubuntu-24.04**, and installs required packages there. The environment stays in `%LOCALAPPDATA%\A1-Patcher\environment` for reuse. No Ubuntu Store first-run wizard is used.

Setup operates on the dedicated environment. A conflicting name/location or WSL 1 registration is refused. It does not convert, unregister or install packages into an existing personal Linux distribution. Hardware virtualization must be available; restricted company PCs or disabled firmware virtualization can prevent setup. The app reports the failure and keeps a log and saved selection. It does not change firmware settings.

The downloaded root filesystem and Rufus are obtained from upstream on demand; neither is bundled. First-use downloads require internet access. Full first-run Windows/WSL and privileged image patching remain untested on a physical Windows PC.

## Optional Rufus handoff

The patcher downloads unmodified portable Rufus 4.15 from its official GitHub release, checks the pinned SHA-256 and Windows Authenticode signature for **Akeo Consulting**, and opens it with the generated image selected. Cached downloads are checked again before launch. Windows requests administrator approval for Rufus. No USB is selected automatically and no unattended write is requested.

The image and adjacent `.img.json` checksum report must stay together for this handoff. The separate **Open Rufus with an existing patched image** button checks the same report. Alternatively, download Rufus yourself and select the generated `.img` manually. A failed Rufus download or launch leaves the successfully generated image available.

Rufus is downloaded on demand, not bundled or modified. Its source and GPLv3-or-later license are linked in `windows/rufus.json`. The patcher has no direct USB capture/write workflow.

## Validation and limits

PowerShell syntax, action refusal, setup lifecycle/reuse/collision/restart handling, signature/publisher checks and launch arguments are tested with fixtures and mocks. Windows CI also constructs the WinForms launcher and downloads/checks official Rufus without running it. Actual interactive GUI behavior, WSL setup/Btrfs mounting, Rufus handoff, USB writing and physical boot remain pending, as does the complete privileged mounted-image patch path.

References: [Valve recovery instructions](https://help.steampowered.com/en/faqs/view/65B4-2AA3-5F37-4227), [official Rufus](https://rufus.ie/en/), [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install), [WSL mounting limitations](https://learn.microsoft.com/en-us/windows/wsl/wsl2-mount-disk).
