# Slow Wi-Fi investigation — 2026-11-05

Status: research only. No Wi-Fi workaround has been added to the payload or release. The user reported extremely slow Wi-Fi on the original AOKZOE A1. The device is unavailable, its actual adapter/PCI ID has not been verified, and no link measurements or Wi-Fi logs from that unit are available in this task. Whether the problem affects only Steam downloads is also unconfirmed.

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

## Integration decision

A future desktop option can offer a reversible **Wi-Fi troubleshooting** trial after identifying the actual adapter. Start with a single power-save change and save/restore the exact prior setting. Verify actual effective radio state, speed, standby and battery effects; report if power saving was already off. Only retain a measured improvement. Avoid making a generic speed fix part of the default hardware bundle until reproduced on the A1.

No device, retained boot media, host networking, firmware, kernel or NetworkManager setting was changed during this investigation.
