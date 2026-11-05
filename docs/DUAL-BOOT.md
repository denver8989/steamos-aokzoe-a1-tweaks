# Install alongside Windows (experimental)

This optional recovery workflow follows the partition-preserving approach of [InnoVision-Games/steam-os-custom-install](https://github.com/InnoVision-Games/steam-os-custom-install). The earlier `steamos-dual-boot` link is a boot-repair cheat sheet, not the installer.

The upstream script is **not run unchanged**. The reviewed revision is `b4bd88e8fd4e3d149cc4eb6b909efc1102c28b45`, SHA-256 `041cfda4e78bf1ca574307a6bd9d4057e77086d561602548db25818918443d59`. It has an undefined partition-table variable in its wipe branch and formats chosen indices without verifying that they are safe new partitions. Our local transform removes wipe, sanitize and arbitrary disk/index prompts, retains its copy/boot-finalization flow, and routes partition creation/verification through our A1 guard.

## Prepare and install

1. Back up Windows and keep the BitLocker recovery key available. Use **Windows Disk Management** to shrink the Windows volume and leave at least **32 GiB of unallocated space at the end of the internal disk**. The integration does not shrink NTFS or BitLocker volumes. More space is needed for a useful games library.
2. When preparing the A1 recovery image on Windows, tick **Include experimental Install Alongside Windows**. On Linux, select the dual-boot option in the image chooser or append `--include-dualboot` to `tools/patch-image.py`.
3. Flash that local image to a spare USB and boot the original A1. On its recovery desktop choose **Install A1 Alongside Windows (Preview)**. Do **not** choose Wipe Device & Install SteamOS when preserving Windows.
4. The guard requires the original A1 and reviewed USB recovery root, exactly one safe writable internal NVMe, an existing GPT with Windows-style EFI/data partitions, no target mounts or swap, 512-byte sectors, stable disk identity and a sufficiently large trailing free extent. Existing SteamOS partition labels are refused; this is a fresh-install workflow, not a repair/reinstall tool for an existing dual boot.
5. Review the target and proposed home size, then type `INSTALL`. A private GPT backup and install log are saved under `/home/deck/SteamOS-Recovery/logs/` on the recovery system. They can contain disk identifiers; review before sharing.
6. The planner allocates eight unused partition indices strictly after the existing partitions, verifies the original GPT entries before and after new entries, and verifies all new nodes before formatting. Before bootloader finalization it also checks that the native chroot helper maps root, ESP and EFI to the planned NEW SteamOS partitions; an unexpected Windows EFI mapping is refused. Windows partitions and their EFI filesystem are not selected for formatting. New SteamOS home fills the planned trailing extent. A failure may leave new SteamOS partitions partially installed; do not follow it with a wipe installer.
7. Boot the installed SteamOS. The copied A1 display/audio/standby/persistence fixes and the optional post-install extras wizard come from the patched recovery root. Use the firmware boot menu to choose Windows Boot Manager or SteamOS. Automatic Windows detection in GRUB and boot ordering are not guaranteed by this preview.

## What is and is not tested

Synthetic tests cover planning, non-overlap, unchanged Windows entries, exact new extents, refusing insufficient space/existing SteamOS/mixed device names/unknown sector layouts, identity changes and partition-table races before any GPT write. The real pinned upstream file passes the guarded transform and Bash syntax checks. **No physical partitioning, Windows preservation, BitLocker boot, bootloader integration or full dual-boot installation has been validated.** Treat this as an experimental source integration requiring device testing, not an established safe installer for arbitrary layouts.

No upstream license file was present in the inspected repository. Its full script is not vendored or included in our release. Selecting this option downloads that fixed upstream revision and transforms it only in the user's locally prepared image. This project's MIT license does not relicense upstream material.
