# SteamOS tweaks for the original AOKZOE A1

Display, rotation, audio and guarded standby support for **AOKZOE A1 AR07** running Valve SteamOS. Includes an installed-system installer and a recovery **`.img.bz2` → new `.img`** patcher. No A1 Pro/A1X support is claimed. This is an independent community project, not a Valve or AOKZOE product.

**Preview release:** the underlying standby wake-policy workaround passed reported physical tests on BIOS 1.30 and SteamOS 3.9.5. This new transactional installer has local safety and file-integration tests; its installation/reboot, a real SteamOS A/B update and the complete mounted-image patch path remain untested. Keep a working recovery USB.

## Windows: start here

Download and extract the **ZIP** release, then double-click **Start-A1-Patcher-Windows.cmd**. Choose your downloaded Valve recovery file (`.img.bz2` or `.img`) and click **Create recovery image**. The app sets up its preparation environment automatically, shows progress, and opens verified official Rufus by default. Choose a spare USB in Rufus and click START. The Valve download/license page is available in the app.

On first use, the app installs WSL 2 and a dedicated Ubuntu preparation environment automatically (about 340 MB plus tools). Windows may request administrator approval and a restart; reopen the app and click **Continue saved preparation** afterward. No Linux account, terminal commands or distribution choice is needed. Preparation edits a local image only. Rufus handles USB selection, confirmation and writing. See [Windows workflow and limits](docs/WINDOWS.md).

The project hosts **patchers and source only, no SteamOS images**. Users obtain Valve's image themselves and apply changes locally. See [distribution model](docs/DISTRIBUTION.md).

## Optional Windows + SteamOS dual boot

The image choosers offer an opt-in **experimental Install Alongside Windows** recovery option based on the corrected [InnoVision custom installer](https://github.com/InnoVision-Games/steam-os-custom-install). It downloads a reviewed upstream revision locally, removes wipe/sanitize/manual-index branches, and requires verified trailing unallocated space. It checks existing partition entries, allocates new indices, saves a GPT backup and refuses native boot-helper mappings that point outside the new SteamOS partitions. It does not shrink or format Windows volumes.

Read [dual-boot preparation and limits](docs/DUAL-BOOT.md) before selecting it. This is a fresh dual-boot workflow, not a repair tool for an existing SteamOS layout. Partitioning and actual Windows/SteamOS boots have not been validated on hardware. The full-wipe recovery icon remains a distinct action and must not be used when preserving Windows.

## Double-click setup

On a Linux/KDE desktop, extract the release archive and open:

| Launcher | When to use it |
| --- | --- |
| **Patch-A1-Recovery-Image.desktop** | Choose Valve's original `.img.bz2` or `.img`, choose a new output name, then enter your password in the progress terminal. |
| **Install-A1-Tweaks.desktop** | Install the hardware fixes on the original A1 after Valve SteamOS is installed. |
| **Set-Up-A1-Extras.desktop** | After SteamOS installation, choose optional Decky plugins and the A1 theme. |

KDE may ask you to allow execution of a downloaded launcher. Keep the extracted folder together. The image launcher needs the preparation tools listed below. It does not accept ISOs or patch a physical USB in place. Flash the generated image to a spare USB with Etcher. The Windows launcher is described above. macOS launchers are not included. Direct USB patching is not offered.

## Optional extras after installation

**Set Up A1 Extras** is a separate desktop wizard. The hardware installer and patched image also stage it locally; bootstrap places its icon on the standard `deck` user's Desktop. It is optional, needs internet, and refuses SteamOS recovery environments. It offers:

- Decky Loader (a detected existing installation is retained).
- SimpleDeckyTDP.
- A separate **30 W default profile** checkbox; it also selects SimpleDeckyTDP. The plugin applies this when it loads. Actual power may be clamped by firmware. Existing per-game profiles and other CPU/GPU settings are retained.
- CSS Loader and Handheld Controller Glyphs, enabled with **Handheld = AOKZOE A1**.

Choose the desired boxes, review the summary, enter your password in the terminal, then reboot and open Decky in Gaming Mode. Nothing is installed into the recovery environment and nothing is silently applied during OS installation. The 30 W preset is not selected automatically. No additional fan, undervolt or firmware changes are made by this setup.

Packages are pinned: Decky 3.3.1, SimpleDeckyTDP 1.0.7, CSS Loader 2.1.3 from the Decky store, and a reviewed Handheld Controller Glyphs commit. Downloads must match recorded SHA-256 checksums before files are replaced. Plugin and theme files/settings are backed up under the user's `.local/state/aokzoe-a1-extras/`; **Restore previous extras** in the same wizard restores them. This is separate from hardware-tweak undo. Existing PowerControl is refused to avoid installing another TDP controller alongside it.

Terminal equivalents, run on the installed A1 as its standard desktop user:

```sh
# Select all optional extras, including the explicitly requested 30 W default:
sudo python3 tools/extras.py install --user deck --decky --tdp --30w --glyphs
# Restore previous extras files/settings, then reboot:
sudo python3 tools/extras.py undo --user deck
```

The extras setup has file-integration and rollback tests, but **Decky, plugin loading, live 30 W behavior and the new desktop dialogs have not been tested on the physical A1**. This remains a preview.

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

1. Download Valve's [recovery image](https://steamdeck-images.steamos.cloud/recovery/steamdeck-oobe-repair-20260707.10-3.8.14.img.bz2). The [official index](https://steamdeck-images.steamos.cloud/recovery/) checked for this release lists this as the latest **Steam Deck** recovery image; the newer Steam Frame image targets different hardware. Unknown images, layouts and vendor scripts are refused until reviewed. To include the experimental preserve-only InnoVision integration, append `--include-dualboot`; this downloads the pinned upstream script into your local image, not into a public release.
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

Run `python3 -m unittest discover -s tests -v`. See [validation](docs/VALIDATION.md) for exactly what was tested, and [sources](docs/SOURCES.md) for provenance and redistribution boundaries. No physical disk command is executed by the test suite. `tests/windows-check.ps1` adds PowerShell parser, action allowlist, Rufus signature/checksum and launch-argument tests without accessing physical storage. Updates may change the vendor interfaces; this is guarded persistence, not a promise of compatibility with arbitrary future SteamOS releases. Factory reset/reimage is outside update persistence. Power-limit changes occur only if the optional 30 W preset is selected. Hardware fixes do not require extras.

## Slow Wi-Fi investigation

A1 Extras offers an optional **Wi-Fi power-saving trial** only for detected matching MediaTek adapters, plus a separate Restore action. It changes the connected network only and requires no Decky installation. This is an unproven troubleshooting trial; it may increase battery use. No Wi-Fi tweak is enabled automatically. See [adapter checks, SteamOS-specific findings and limits](docs/WIFI.md).
