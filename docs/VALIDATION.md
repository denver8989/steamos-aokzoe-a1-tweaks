# Validation record

Source validation performed for this preview on 2026-11-05. The A1 and physical boot media were not accessed by this repository task.

Passed:

- 21 Python safety tests: exact-model and firmware refusals, fixed-button wake preservation, deep-sleep/AML guards, nonblocking suspend drop-in, current/changed-kernel GRUB generation, unknown-template fallback, stacked ESP automount handling, configuration backup/rollback/reinstall/undo behavior, service symlink behavior, update allowlist, disk-selection/serial/sector/swap refusals, unknown-image/vendor-script refusal and CPIO framing.
- Bash syntax for shipped shell scripts, gamescope wrapper and GRUB hook; desktop-file-validate for every launcher; Python compilation.
- Original Valve recovery script checksum and exact zero-fuzz transform, expected output checksum and Bash syntax. A mocked full-install action reached normal partitioning flow without invoking NVMe sanitize. Firmware staging blocks are disabled; native filesystem/copy/bootloader steps remain.
- Real pristine compressed image hash, bzip2 expansion, raw image hash/size and GPT CRCs/layout, using `--inspect-only`; the temporary regular image was deleted afterward.
- File-tree integration using private local copies of the actual reviewed Valve script/GRUB template and upstream EDID: correct transform, checksum/CPIO generation, full manifest, enablement symlink, undo baseline and stock display fallback. UUID lookup was mocked; no mounts or disk writes occurred.

Reported prior runtime evidence, not repeated here:

- Original A1 AR07, BIOS 1.30 dated 12/06/2022, installed Valve SteamOS 3.9.5 / kernel 7.2.7-valve2 / systemd 261: 25-second RTC deep-sleep/resume and earlier physical power-button wake passed after disabling only PNP0C0C wake. A normal-button standby remained asleep without an RTC timer. The controller magic-message warning persisted.
- Earlier bundle work tested native updater-equivalent filtering and /etc overlay copy-up. That does not establish a real A/B OS-update result for this release.

Not yet tested:

- Privileged loop mounting, full image patch/write and cleanup on real filesystems.
- Installation/reboot/undo on the physical A1 using this new manager.
- A physical complete recovery reinstall or actual SteamOS A/B update with this release.
- The new optional official Codex download/launcher, sandbox command and live model call.

The release is therefore a preview source/toolkit, not a hardware-certified image. No prepatched OS image is published. Preserve the existing working boot media and compare its files before deploying changes.
