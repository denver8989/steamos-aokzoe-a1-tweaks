# Windows preparation workflow (preview)

Extract the **ZIP** release on Windows 10/11 x64 and double-click **Start-A1-Patcher-Windows.cmd**. Keep the whole extracted folder together. The launcher uses built-in PowerShell and file dialogs; Python is not required on Windows itself.

The backend uses **WSL 2**, Ubuntu or Debian, and a kernel that can load Btrfs. The launcher offers one-time WSL/Ubuntu setup and installation of preparation tools inside the selected distribution. Setup may require administrator approval, virtualization, internet access and a restart. Initialize Ubuntu if prompted, then refresh the distribution list. If Btrfs cannot load, update WSL and restart it. Actual Windows/WSL image preparation remains untested; this is a preview.

1. Obtain the reviewed original Valve recovery download using the launcher's Valve download/license link. The file is `.img.bz2` or expanded `.img`, **not an ISO**. Only the pinned version listed in SOURCES.md is accepted.
2. Prepare the backend, then select the original download and a **new** output `.img` filename. Allow at least 9 GiB free for the output.
3. Optionally select **Include experimental Install Alongside Windows**. This stages a separate recovery desktop action; image preparation does not repartition anything.
4. Optionally select **Open Rufus when finished**, then create the patched image.
5. In Rufus, select the correct spare USB and click **START**. This erases that USB. A 16 GB or larger spare is recommended; its actual capacity must exceed the image size (8,120,172,544 bytes). Preserve your previous successful USB.
6. Close Rufus, safely eject the USB and boot the A1 from it.

## Optional Rufus handoff

The patcher downloads unmodified portable Rufus 4.15 from its official GitHub release, checks the pinned SHA-256 and Windows Authenticode signature for **Akeo Consulting**, and opens it with the generated image selected. Cached downloads are checked again before launch. Windows requests administrator approval for Rufus. No USB is selected automatically and no unattended write is requested.

The image and adjacent `.img.json` checksum report must stay together for this handoff. The separate **Open Rufus with a patched image** button checks the same report. Alternatively, download Rufus yourself and select the generated `.img` manually. A failed Rufus download or launch leaves the successfully generated image available.

Rufus is downloaded on demand, not bundled or modified. Its source and GPLv3-or-later license are linked in `windows/rufus.json`. The patcher has no direct USB capture/write workflow.

## Validation and limits

PowerShell syntax, action refusal, signature/publisher checks and launch arguments are tested with fixtures and mocks. Windows CI also constructs the WinForms launcher and downloads/checks official Rufus without running it. Actual interactive GUI behavior, WSL setup/Btrfs mounting, Rufus handoff, USB writing and physical boot remain pending, as does the complete privileged mounted-image patch path.

References: [Valve recovery instructions](https://help.steampowered.com/en/faqs/view/65B4-2AA3-5F37-4227), [official Rufus](https://rufus.ie/en/), [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install), [WSL mounting limitations](https://learn.microsoft.com/en-us/windows/wsl/wsl2-mount-disk).
