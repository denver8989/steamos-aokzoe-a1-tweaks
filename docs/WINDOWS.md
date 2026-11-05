# Windows preparation workflow (preview)

Extract the **ZIP** release on Windows 10/11 and double-click **Start-A1-Patcher-Windows.cmd**. Keep the whole extracted folder together. The launcher uses Windows' built-in PowerShell and file dialogs; Python is not required on Windows itself.

The current backend uses **WSL 2**, with Ubuntu or Debian and a kernel that can load Btrfs. The launcher offers one-time WSL/Ubuntu setup and installation of Linux preparation tools inside the selected distribution. WSL setup can require Windows administrator approval, virtualization support, an internet connection and a restart. Initialize Ubuntu if Windows prompts you, then return and refresh the distribution list. This is a Windows front end with a Linux backend, not a dependency-free native filesystem editor. If Btrfs cannot load, update WSL and restart it; the tool stops rather than installing a custom kernel or Windows filesystem driver.

1. Open Valve's download/license page from the launcher and obtain the official **Steam Deck** recovery image yourself. The reviewed source is `.img.bz2` or its pristine `.img`; no ISO or Steam Frame support is implied.
2. Select the WSL distribution and click **Prepare Linux backend**. This installs Python, util-linux, Btrfs tools, GNU patch, desktop-file-utils and kmod inside that distribution.
3. Optionally select **Include experimental Install Alongside Windows**. This stages a separate preserve-only recovery desktop option; it does not repartition anything during image preparation.
4. Select the original Valve image and choose a **new** `.img` output filename on a local drive. Allow at least 9 GiB free. The progress terminal reports errors and success.
5. Flash the resulting image to a spare USB with Etcher, then boot the A1. Keep your previous successful recovery USB intact.

## Freshly written USB option

The alternative USB workflow is **experimental and has not been exercised on physical Windows storage**. Prefer the image-file route until validated.

It requires administrator approval, an online writable USB with GPT, 512-byte sectors and a nonempty hardware serial/identity. Boot/system/internal disks are excluded. You select the USB, type its disk number to confirm, and choose a workspace on another local disk with at least 18 GiB free.

The worker locks/dismounts recognized target volumes, captures the first 8,120,172,544 bytes, and checks the exact pristine Valve SHA-256 before any USB write. Linux patches that regular-file copy; it never receives a physical Windows disk. The worker then rechecks the USB's identity and original contents, writes the verified patched prefix, flushes and reads back the bytes for hash verification. The original prefix remains in the workspace. Data beyond that prefix is neither backed up nor written.

A customized or previously booted USB may differ from the pristine hash and is refused. **Your retained successful USB should not be used as the target.** A failed write or power loss can leave the selected USB unusable; retain the backup and image. No Windows internal partition is resized or formatted by this preparation tool.

## Validation limits

PowerShell syntax, disk-selection/identity/boot/system/sector refusals, bounded stream copying/hashing, EOF failure and volume-lock API compilation are tested with synthetic data. Windows CI runs those tests without accessing storage. Actual WinForms display, WSL setup/Btrfs mounting, Windows volume locking, USB writing and physical boot remain pending. The complete Linux mounted-image patch path is also still pending physical validation.

References: [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install), [WSL mounting limitations](https://learn.microsoft.com/en-us/windows/wsl/wsl2-mount-disk), [Microsoft's WSL kernel configuration](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.18.y/arch/x86/configs/config-wsl). Direct `wsl --mount` does not support ordinary USB flash media; the file-copy workflow avoids that interface.
