# Credits and acknowledgements

This project is scoped exclusively to the **original AOKZOE A1 AR07**. Upstream projects may support other hardware; those capabilities are not a device-support roadmap for this project.

The A1 installer, image-patching guards, setup wizard, presets, rollback logic and tests bring together substantial work by the authors and communities below. We credit each project and its contributors for their own software, assets and research.

## SteamOS, hardware compatibility and recovery

| Party / project | What this project uses |
| --- | --- |
| **[Valve](https://github.com/ValveSoftware)** and SteamOS contributors | The SteamOS operating system, official recovery media and native installation/update flow. Our recovery changes are a narrow local patch to Valve's script. Users obtain the OS from Valve. |
| **[Universal Blue / Bazzite](https://github.com/ublue-os/bazzite)** and contributors to **[bazzite-firmware-nonfree](https://github.com/ublue-os/bazzite-firmware-nonfree)** | The original A1 EDID override and the hardware-setup reference identifying it. The checksum-pinned EDID is fetched from upstream; we do not bundle it. |
| **[ChimeraOS](https://github.com/ChimeraOS/chimeraos)** and **[frzr](https://github.com/ChimeraOS/frzr)** contributors | A1 display/EDID documentation and a reference for ordinary partitioning/filesystem creation. No frzr implementation is copied. |
| **[InnoVision Games](https://github.com/InnoVision-Games/steam-os-custom-install)**, **[sorialexandre](https://github.com/sorialexandre/steam-os-custom-install)** and contributors | The optional dual-boot installer's upstream lineage. We download a pinned InnoVision revision locally and apply our guarded transform; its full script is not bundled. |
| **AOKZOE** and the original-A1 testing community | The hardware and firsthand testing that informed the model/firmware-specific investigation. Runtime standby evidence is distinguished from this release's untested full installation flow. |

## Optional desktop plugins and theme

| Party / project | What this project uses |
| --- | --- |
| **[Steam Deck Homebrew](https://github.com/SteamDeckHomebrew)** and **[Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)** contributors | The optional plugin loader, its service layout, installer reference and plugin ecosystem. |
| **[Aarron Lee](https://github.com/aarron-lee/SimpleDeckyTDP)** and contributors | SimpleDeckyTDP, used for optional TDP controls and our opt-in 30 W default preset. Its license also credits the Steam Deck Homebrew plugin template. |
| **[DeckThemes](https://github.com/DeckThemes/SDH-CssLoader)**, **Jonas Dellinger / [suchmememanyskill](https://github.com/suchmememanyskill)** and contributors | CSS Loader. The reviewed package identifies Jonas Dellinger in its package metadata and DeckThemes in its plugin metadata. |
| **[victor-borges](https://github.com/victor-borges/handheld-controller-glyphs)** and contributors | Handheld Controller Glyphs, with this project's preset selecting AOKZOE A1. The theme's own credits also name **[honjow](https://github.com/honjow/SBP-PS5-to-Handheld)** and **[frazse](https://github.com/frazse/SBP-Legion-Go-Theme)** for upstream theme work/assets. |
| **[Decky plugin store](https://plugins.deckbrew.xyz/plugins)** and its infrastructure maintainers | The CSS Loader package/version metadata and content-addressed download used by optional setup. |

SimpleDeckyTDP's reviewed package also credits **[PowerControl / mengmeet](https://github.com/mengmeet/PowerControl)**, **[hhd-dev/adjustor](https://github.com/hhd-dev/adjustor)**, **[hhd-dev/hwinfo](https://github.com/hhd-dev/hwinfo)**, **[FlyGoat/RyzenAdj](https://github.com/FlyGoat/RyzenAdj)** and the **[SteamFork](https://github.com/SteamFork)** community. We acknowledge that upstream lineage as well. Its downloaded package includes RyzenAdj and its separate license. We do not separately install PowerControl or claim those projects' broader compatibility as our own.

Plugin/theme downloads retain their included upstream license and documentation files. Their repositories contain additional contributor and dependency acknowledgements; those remain authoritative for their own work.

## Windows preparation and optional tools

- **[Pete Batard / Akeo Consulting and Rufus contributors](https://github.com/pbatard/rufus)** — the official portable USB-writing tool, downloaded unmodified on demand. Rufus performs USB selection and write confirmation.
- **[Microsoft and WSL contributors](https://github.com/microsoft/WSL)** — the Windows Subsystem for Linux used by the Windows preparation environment; Microsoft also supplies PowerShell, .NET and Windows Forms used by the launcher.
- **[Canonical and Ubuntu contributors](https://cloud-images.ubuntu.com/wsl/releases/24.04/20240423/)** — the official Ubuntu root filesystem downloaded for the app-managed WSL environment.
- **[OpenAI and Codex contributors](https://github.com/openai/codex)** — the optional official Codex recovery CLI and companion binaries. This feature is independent of the hardware fixes.
- **[balena and Etcher contributors](https://github.com/balena-io/etcher)** — the separately obtained Linux image-writer alternative mentioned in our instructions; it is not integrated or bundled.

## Wi-Fi investigation and system foundations

The optional Wi-Fi helper uses documented **[NetworkManager](https://networkmanager.dev/)** settings and the Linux **[mt76/mt7921](https://github.com/torvalds/linux/tree/master/drivers/net/wireless/mediatek/mt76)** driver interface. Credit to the Linux wireless community, MediaTek driver contributors, **[Mario Limonciello and participants in the power-saving discussion](https://community.frame.work/t/responded-poor-wi-fi-performance-with-amd-rz616/42901/2)**, and Valve's SteamOS Wi-Fi fixes. The trial is our own configuration helper, not a proven A1 throughput fix.

**[isaiahtx's MCS investigation](https://github.com/isaiahtx/mt7922-mt7921-linux-wifi-fix)** and the **[darkremix.net A1 guide](https://wiki.darkremix.net/aokzoe/SteamOS-Guide)** were research references. Their kernel patch and old HoloISO cleanup commands are not installed or copied into this toolkit.

The toolkit also relies on the work of the **Linux kernel**, **Python**, **GNU** (including GRUB, Bash and patch), **util-linux**, **Btrfs/btrfs-progs**, **dosfstools**, **bzip2**, **systemd**, **gamescope**, **PipeWire/WirePlumber**, **KDE** (including KDialog and Konsole), and **freedesktop.org desktop-file-utils** communities. GitHub Actions and its contributors provide the hosted CI infrastructure. These are system/runtime foundations, not software authored by this repository.

## Attribution and source records

This repository's MIT license applies to its original code only. Upstream software and assets retain their own authorship, notices and terms. Credits do not imply endorsement or change those terms.

See [sources and download provenance](docs/SOURCES.md), [pinned plugin downloads](extras/packages.json), [Rufus metadata](windows/rufus.json), [Ubuntu metadata](windows/ubuntu.json) and [dual-boot upstream revision](dualboot/upstream.json) for the exact material used.
