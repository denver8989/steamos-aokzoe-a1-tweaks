# Install SteamOS on AOKZOE A1 (AR07)

A community toolkit that prepares **Valve's SteamOS recovery image for the original AOKZOE A1**, ready to write to a USB from Windows or Linux. It adds A1 display, rotation, audio and guarded sleep fixes, plus optional extras after installation.

**Preview:** the complete image-preparation and installation flow still needs testing on a physical A1 and Windows PC. Automated tests pass, but this is not yet a fully tested beginner installer. Back up your files and keep any existing working recovery USB.

**[Download the Windows ZIP](https://github.com/denver8989/steamos-aokzoe-a1-tweaks/releases/download/v0.6.0-preview/steamos-aokzoe-a1-tweaks-v0.6.0-preview.zip)** · [Linux download](https://github.com/denver8989/steamos-aokzoe-a1-tweaks/releases/download/v0.6.0-preview/steamos-aokzoe-a1-tweaks-v0.6.0-preview.tar.gz) · [Release notes](https://github.com/denver8989/steamos-aokzoe-a1-tweaks/releases/tag/v0.6.0-preview)

## Is this for my device?

**This project is exclusively for the original AOKZOE A1 AR07. Other devices are outside its scope; no additional-device support is planned.**

| Device | Support in this project |
| --- | --- |
| **Original AOKZOE A1 — model AOKZOE A1 AR07** | Supported model; preview testing limits apply. |
| AOKZOE A1 Pro, A1X or other handhelds | Unsupported and outside this project’s scope. |

This is an independent community project, not an official Valve or AOKZOE product. We publish the patcher, not a modified SteamOS download. You get SteamOS directly from Valve and patch your own copy.

## Start here on Windows

You need **Windows 10/11 x64 on an Intel/AMD PC**, internet access and a **spare USB of 16 GB or larger**. About **20 GB free on the PC is recommended** for the Valve download, new image and first-use setup. Plug the A1 into power when installing.

1. **Download and extract the ZIP** linked above. Keep the extracted folder together.
2. **Double-click `Start-A1-Patcher-Windows.cmd`.** A setup window opens.
3. **Get the SteamOS recovery file from Valve.** The app has a download/license button. Read [Valve's terms](https://store.steampowered.com/steamos/download/?ver=steamdeck), then use the [reviewed recovery download](https://steamdeck-images.steamos.cloud/recovery/steamdeck-oobe-repair-20260707.10-3.8.14.img.bz2). The accepted filename is `steamdeck-oobe-repair-20260707.10-3.8.14.img.bz2`. Other versions need review before this patcher accepts them.
4. **Click Choose recovery file**, select that download, then **Create recovery image**. Choose where to save the new `.img`. Leave **Open Rufus when ready** enabled.
5. **Let the app prepare everything.** First use downloads its preparation component automatically. Approve the Windows administrator prompt if shown. If Windows needs a restart, save your work, restart, reopen the app and click **Continue saved preparation**. No Linux account or terminal commands are needed.
6. **Write the USB with Rufus.** Rufus opens with the patched image selected. Check the USB drive carefully, then click **START**. **Rufus erases the selected USB.** Close Rufus and safely eject the drive when it finishes.
7. **Boot the A1 from that USB** using its firmware boot menu. For a full reinstall, choose **Wipe Device & Install SteamOS** on the recovery desktop. **This erases the A1's internal drive, including Windows and personal files.** Complete SteamOS setup, then remove the USB when instructed.

The Valve download is a **`.img.bz2`**, not an ISO. Select it directly; you do not need to decompress it yourself. Your new patched file ends in `.img`.

Want to keep Windows? Read the [experimental dual-boot guide](docs/DUAL-BOOT.md) **before preparing the image**. It requires prepared free disk space and a different recovery action. Do not choose Wipe Device when preserving Windows. Physical dual-boot installation is not yet validated.

## Optional extras after SteamOS is installed

Switch to Desktop Mode and open **Set Up A1 Extras**. The patched installation stages this launcher on the standard `deck` user's Desktop. Choose only what you want:

| Option | What it does |
| --- | --- |
| Decky Loader | Adds the Decky plugin menu in Gaming Mode. |
| SimpleDeckyTDP | Adds TDP controls; a separate optional checkbox sets its default profile to **30 W**. |
| CSS Loader + Handheld Controller Glyphs | Enables the **AOKZOE A1** controller-button theme. |
| Wi-Fi power-saving trial | Offered only for a detected matching MediaTek card and driver. A reversible troubleshooting trial; improvement is unproven and battery use may increase. |

Plugin extras and the 30 W preset are not installed automatically. Firmware may limit actual power. Wi-Fi needs no Decky install and has its own **Restore Wi-Fi setting** action. Plugin files/settings have a separate restore option. [Wi-Fi details](docs/WIFI.md) · [Extras versions, backup and commands](docs/ADVANCED.md#plugin-versions-backups-and-terminal-commands)

## Already using SteamOS, or preparing on Linux?

- **SteamOS already installed on the original A1:** extract the release and open **Install-A1-Tweaks.desktop** to add the hardware fixes. This does not reinstall SteamOS.
- **Preparing a recovery USB on Linux/KDE:** extract the Linux archive and open **Patch-A1-Recovery-Image.desktop**. Required preparation packages and terminal instructions are in the [advanced guide](docs/ADVANCED.md#create-a-new-a1-recovery-image). Write the resulting `.img` with Etcher or another suitable image writer.
- KDE may ask you to allow execution of a downloaded launcher. macOS launchers are not provided.

## If something goes wrong

On Windows, use **View progress logs** in the app. Keep the original Valve download and any existing working USB. The [Windows guide](docs/WINDOWS.md) explains setup, saved jobs and Rufus troubleshooting.

On an installed A1, hardware fixes can be undone using the [restore instructions](docs/ADVANCED.md#install-on-an-a1-already-running-valve-steamos). Extras have their own restore actions.

## Testing and further details

The source has **60 passing Python tests**, Windows PowerShell checks and Windows/Linux CI. Full first-use Windows setup, privileged image patching, USB boot/install, a real SteamOS update and live extras/Wi-Fi effects still require hardware validation. Reported earlier standby tests do not validate this entire release. The guarded sleep workaround currently requires BIOS **1.30 / 12/06/2022**; other firmware is left unchanged. The known controller magic-message warning remains unresolved.

[Exactly what was tested](docs/VALIDATION.md) · [Technical reference](docs/ADVANCED.md) · [Sources and licenses](docs/SOURCES.md) · [Distribution model](docs/DISTRIBUTION.md)

## Credits

Built on work by **Valve**, **Universal Blue/Bazzite**, **ChimeraOS**, **InnoVision Games and sorialexandre**, **Steam Deck Homebrew**, **Aarron Lee**, **DeckThemes/Jonas Dellinger**, **victor-borges and the theme’s upstream contributors**, **Pete Batard/Akeo Consulting**, **Microsoft**, **Canonical**, **OpenAI**, and the Linux/open-source communities.

[Full credits and each contribution](CREDITS.md) · [Sources, pinned downloads and license notes](docs/SOURCES.md)
