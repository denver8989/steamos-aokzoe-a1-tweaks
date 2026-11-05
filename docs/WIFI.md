# Slow Wi-Fi investigation — 2026-11-05

Status: optional adapter-gated trial implemented in A1 Extras; not a proven A1 throughput fix. The user reported extremely slow Wi-Fi on the original AOKZOE A1. The device is unavailable, its actual adapter/PCI ID remains unverified, and no before/after measurements from that unit are available.

## SteamOS and ChimeraOS scope

The initial power-saving evidence came from Linux/MediaTek reports on other distributions. A matching driver is a reason to offer a controlled trial, not proof of equivalent results on Valve SteamOS.

Further review found a **Valve-native fix**: [Valve's July 3, 2026 release notes](https://www.steamdeck.com/en/news?p=7%2F1000) say SteamOS 3.8.14 stable / 3.8.22 beta corrected Wi-Fi speed limits caused by routers advertising incorrect MCS requirements. This patcher's pinned recovery image is labelled 3.8.14. The notes do not prove the state of every installed kernel, but they make shipping an additional shared mac80211 bypass especially unjustified.

[ChimeraOS issue 288](https://github.com/ChimeraOS/chimeraos/issues/288) discusses old RZ608 driver-ID support, not a confirmed current A1 speed fix. Its [device-specific guide](https://github.com/ChimeraOS/chimeraos/wiki/Device-Specific-Configurations) lists an A1 display override, without an A1 Wi-Fi throughput recipe. No ChimeraOS kernel package or configuration is copied here.

## Findings and candidate fixes

1. **Wi-Fi power saving: preferred first controlled test.** In a [first-party Framework discussion](https://community.frame.work/t/responded-poor-wi-fi-performance-with-amd-rz616/42901/2), an AMD developer points to mt7921 power-saving investigation and recommends testing the setting. This is evidence for a candidate affecting related MediaTek hardware, not proof of an A1 fix. [NetworkManager documents](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html) `802-11-wireless.powersave=2` as disabled, `3` as enabled, `1` as ignore and `0` as global default. A connection-specific change must preserve the previous value for undo. A global default alone does not override a profile explicitly enabling power saving. Any benefit must be measured against idle battery consumption and suspend/resume behavior.
2. **PCIe ASPM: secondary, separate test.** The [upstream mt7921 PCI driver](https://github.com/torvalds/linux/blob/master/drivers/net/wireless/mediatek/mt76/mt7921/pci.c) defines `disable_aspm` and supports MediaTek IDs including 14c3:0608, 14c3:0616, 14c3:7961 and 14c3:7922. This verifies that the switch exists; it does not establish that it fixes this A1. Confirm that the running SteamOS module exposes it before considering use. Do not disable PCIe ASPM globally, combine changes in the first trial or unload an active Wi-Fi driver during an install/download.
3. **Legacy-rate/MCS negotiation fault: specific community patch exists.** The [author's project](https://github.com/isaiahtx/mt7922-mt7921-linux-wifi-fix) reports a mac80211 workaround after observing a 54 Mbit/s legacy link and `required MCSes not supported, disabling HT`. Its implementation bypasses an HT capability check and rebuilds the shared mac80211 kernel module. This is a different fault from power saving. Do not integrate it without the matching log signature, exact Valve kernel/source compatibility review and before/after tests. Its Arch package hooks do not establish SteamOS A/B-update compatibility. Author claims are not independent validation.
4. **Old A1-specific guide is not a current fix.** The [A1 SteamOS guide](https://wiki.darkremix.net/aokzoe/SteamOS-Guide) describes removing legacy `rz608-fixes-git` files to address wake failures on old HoloISO kernels. It provides a lead toward MediaTek/RZ608 hardware in original A1 units, but does not identify this user's adapter or diagnose low throughput on current Valve SteamOS. Do not copy its deletion commands or assume that package is installed.

## Evidence needed when an A1 is available

Collect locally, with network identifiers redacted before sharing:

- Adapter PCI vendor/device ID and bound driver (`lspci -nnk` or sysfs).
- Running SteamOS/kernel/firmware versions; whether the issue starts at boot or after suspend.
- Wireless interface, signal, frequency/channel, negotiated bitrate and power-save state (`iw dev`, `iw dev <interface> link`, `iw dev <interface> get power_save`).
- Relevant kernel warnings, especially HT/MCS downgrade, firmware timeout or reset messages.
- Effective NetworkManager power-save configuration of the active connection, plus any existing overrides. Never export passwords, complete connection profiles, SSIDs, MAC addresses or unfiltered logs into public artifacts.
- Whether the slowdown affects a local-network transfer and other downloads as well as Steam. Compare before/after on the same router, band, location and server. Separate Mbit/s from MB/s (8 Mbit/s = 1 MB/s), and account for Steam disk/decompression bottlenecks.

## Optional A1 Extras trial

After SteamOS is fully installed, open **Set Up A1 Extras**. A separate **Wi-Fi power-saving trial** entry appears only if exactly one wireless adapter has vendor `14c3`, device `0608`, `7961`, `0616` or `7922`, and bound driver `mt7921e`. This covers RZ608/MT7921 and RZ616/MT7922; it does not guess from the A1 model alone or affect an Intel replacement card. The privileged worker repeats detection and the existing exact-original-A1/installed-SteamOS checks before changes.

The trial requires that adapter to be connected. It records the connection UUID, original NetworkManager powersave value and live radio state in the private root-owned `~/.local/state/aokzoe-a1-extras/wifi.json`, then sets this connection's powersave to `2` and turns off live radio power saving. The application verifies both settings without deliberately reconnecting or restarting NetworkManager. Existing Wi-Fi software must provide `nmcli` and `iw`; failures are reported. No driver, firmware, kernel, ASPM, DNS or region setting is changed. If live power saving is already off, it reports that fact and does nothing.

The separate **Restore Wi-Fi setting** action restores the original profile value and, when the same adapter/connection is active, its original live radio state. It remains available if a different card is fitted. A later unrelated profile edit is refused; an unavailable profile or failed restore retains the backup. Repeat trials preserve the first backup. A failed install attempts rollback; a failed rollback retains the original record for retry. Plugin restore and Wi-Fi restore are independent.

Use the same router/band/location and download source to compare results; restore if there is no benefit. Disabling radio power saving can increase idle battery use. One connection is changed per trial; restore it before trying another. Existing SteamOS connection storage provides profile persistence; actual reboot and SteamOS A/B-update persistence have not been validated for this feature.

The option is off until selected and makes no speed guarantee. Its detection, no-op, rollback and restore behavior is tested with fixtures; actual A1 throughput, standby and battery effects remain untested. No device, retained boot media or host networking was changed while implementing it.
