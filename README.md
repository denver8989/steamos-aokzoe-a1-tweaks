# SteamOS tweaks for the original AOKZOE A1

Display, rotation, audio and guarded standby support for **AOKZOE A1 AR07** running Valve SteamOS. Includes an installed-system installer and a recovery **`.img.bz2` → new `.img`** patcher. No A1 Pro/A1X support is claimed. This is an independent community project, not a Valve or AOKZOE product.

**Preview release:** the underlying standby wake-policy workaround passed reported physical tests on BIOS 1.30 and SteamOS 3.9.5. This new transactional installer has local safety and file-integration tests; its installation/reboot, a real SteamOS A/B update and the complete mounted-image patch path remain untested. Keep a working recovery USB.

## Install on an A1 already running Valve SteamOS

Download and extract the release source archive on the A1, open a terminal in its folder, then run:

```sh
sudo bash install.sh
```

Alternatively, open `Install-A1-Tweaks.desktop` in KDE and allow execution when KDE asks. It opens a terminal and runs the same installer. It may require your sudo password. The installer checks the exact model, SteamOS and native updater/boot layout before changing configuration. It downloads one checksum-pinned EDID file from Bazzite's firmware repository, generates an initramfs archive, backs up only the configuration paths it manages, and adds its own files under `/etc`. It does not install Codex or require sign-in. An existing upstream EDID can be used offline:

```sh
sudo bash install.sh install --edid /path/to/aokzoea1ar07_edid.bin
```

Reboot when convenient. The first custom GRUB entry is `SteamOS - AOKZOE A1`; ordinary SteamOS entries remain available. Choose an ordinary entry if the custom display configuration fails. Automatic reboot and session restart are deliberately left to you.

```sh
# Inspect configuration and bootstrap status (no root needed):
bash install.sh status
# Restore the original configuration and regenerate the boot menu:
sudo bash install.sh undo
# While installed, this also works without keeping the source folder:
sudo python3 /etc/aokzoe-a1/manage.py undo
```

Undo retains its private baseline in `/etc/aokzoe-a1/state/` so restoration can be retried using the downloaded installer. Reinstall preserves that original baseline. A failed install restores the immediately preceding managed files and attempts boot-menu regeneration. Undo restores the recorded original wake policy only when the firmware safety guard still passes. Reboot after undo to end the running session's rotation/audio settings. Directly deleting this directory would also delete your backup.

## Create a new A1 recovery image

Use Linux with Python 3, util-linux (`losetup`, `mount`, `umount`, `findmnt`, `blkid`), btrfs-progs, GNU patch, Bash and desktop-file-utils. The normal SteamOS installer does not require installing these preparation tools.

1. Download Valve's [recovery image](https://steamdeck-images.steamos.cloud/recovery/steamdeck-oobe-repair-20260707.10-3.8.14.img.bz2). The [official index](https://steamdeck-images.steamos.cloud/recovery/) checked for this release lists this as the latest **Steam Deck** recovery image; the newer Steam Frame image targets different hardware. Unknown images, layouts and vendor scripts are refused until reviewed.
2. Keep at least 9 GiB free in the output filesystem. Disconnect existing recovery media before preparing an image with the same Btrfs identity. Preserve your known working USB separately.
3. In the extracted project folder, run:

```sh
sudo python3 tools/patch-image.py \
  /path/to/steamdeck-oobe-repair-20260707.10-3.8.14.img.bz2 \
  /path/to/new-aokzoe-a1-recovery.img
```

For an offline preparation, append `--edid /path/to/aokzoea1ar07_edid.bin`. The output must be a new regular `.img` file in an existing directory. It cannot be a block-device path or an existing file. The tool checks both compressed and expanded hashes, verifies the GPT layout, mounts only bounded loop ranges of the copy, restores the Btrfs read-only property, unmounts and detaches loops, then writes an output checksum report. It never flashes media or invokes the recovery installer. If cleanup fails, it retains the image and lists the mounts/loops requiring attention; do not remove that directory while anything is mounted.

An unprivileged source-integrity/GPT check is available. It temporarily expands a file copy and deletes it afterward; it does not produce a patched image:

```sh
python3 tools/patch-image.py /path/to/original.img.bz2 /path/to/check-only.img --inspect-only
```

Flash the resulting `.img` to a **separate spare USB**, using Etcher or Valve's [documented recovery-media method](https://help.steampowered.com/en/faqs/view/65B4-2AA3-5F37-4227). The patcher does not select or write a physical USB. Boot it on the original A1, then choose `Wipe Device & Install SteamOS` only when ready to permanently erase its internal drive. A fresh installed system receives the same persistent hardware bundle via Valve's native copy flow.

### Recovery installer behavior

The A1 launcher requires a SteamOS recovery desktop running from USB. It selects one writable internal NVMe, at least 32 GiB and with 512-byte logical sectors, excludes storage backing the running system and protected mount paths, displays Valve's wipe confirmation, and rechecks the serial, active swap and target mounts before signature removal. It uses ordinary partitioning/formatting instead of requiring NVMe sanitize or secure format. **This destroys target data and is not secure sanitization.** It waits for all eight target partition nodes, then keeps Valve's native filesystem, copy and bootloader steps. Steam Deck BIOS/controller firmware tools are skipped on this third-party device. Other direct vendor-script actions are refused by the transformed script.

Failure output is retained under `/home/deck/SteamOS-Recovery/logs/` on the recovery system. Copy that directory privately before reflashing; logs may contain disk identifiers and should be reviewed before sharing. The exact old terminal failure was not established from the missing stdout; the unsupported-NVMe path was reproduced with mocked commands.

### Optional Codex Recovery

The recovery desktop includes a `Codex Recovery` launcher. At first launch it offers an optional download of the official Linux x86_64 **Codex 0.166.0** binary and its two companion tools, using pinned SHA-256 checksums. Internet access is required; no npm, host account copy or root installation is needed. You sign in separately. Hardware fixes work without Codex.

The launcher resolves the actual native executable, verifies `codex-code-mode-host` and `codex-exec-server` beside it and sets PATH accordingly. It does not disable the sandbox. Complete package download, sandbox launch and model use through this new recovery launcher remain untested. See the [official Codex CLI documentation](https://learn.chatgpt.com/docs/codex/cli).

## What the hardware bundle does

- Adds a shared-ESP EDID archive and an early GRUB entry generated from the **current** Valve kernel/initramfs template. An unknown template leaves stock entries in place.
- Adds panel orientation through a PATH wrapper only if the current gamescope supports `--force-orientation`. The stock boot marker bypasses the wrapper's adjustment.
- Adds an analog-output format/rate rule to the native WirePlumber runtime configuration on 0.5; unfamiliar versions use vendor audio configuration.
- Copies the explicit manifest into SteamOS's writable `/etc` overlay at bootstrap and uses the native atomic-update allowlist, including the pre-suspend drop-in and private undo state. No custom kernel or replacement vendor session script.
- Reapplies the narrowly guarded standby wake policy at boot and immediately before suspend. A refused pre-suspend guard logs the reason and **does not block suspend**.

The standby guard requires exact A1 DMI, BIOS **1.30 / 12/06/2022**, both power-button endpoints, fixed-button wake enabled, `deep` support, ACPI PNP0C0C path `\_SB_.PWRB` and the reviewed `SPTS` AML notification signature. Only PNP0C0C's sysfs wake policy is changed. No firmware is written, no sleep mode is forced and the fixed physical-button wake endpoint is not disabled. On unreviewed firmware the policy is left unchanged. The controller `unable to receive magic message -121` warning is **not fixed** by this project.

## Verification and limitations

Run `python3 -m unittest discover -s tests -v`. See [validation](docs/VALIDATION.md) for exactly what was tested, and [sources](docs/SOURCES.md) for provenance and redistribution boundaries. No physical disk command is executed by the test suite. Updates may change the vendor interfaces; this is guarded persistence, not a promise of compatibility with arbitrary future SteamOS releases. Factory reset/reimage is outside update persistence. No fan or power-limit changes are included.
