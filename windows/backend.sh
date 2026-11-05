#!/usr/bin/env bash
# Linux backend for the Windows launcher. Runs inside the selected WSL distro only.
set -euo pipefail
mode=${1:?mode required}
if [[ $mode = prepare ]]; then
  [[ $EUID = 0 ]] || { echo 'The backend preparation needs root inside WSL.' >&2; exit 1; }
  command -v apt-get >/dev/null || { echo 'Choose an Ubuntu or Debian WSL distribution.' >&2; exit 1; }
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3 util-linux btrfs-progs patch desktop-file-utils kmod
fi
[[ $EUID = 0 ]] || { echo 'Run the backend as WSL root.' >&2; exit 1; }
for tool in python3 losetup mount umount findmnt blkid btrfs patch bash desktop-file-validate; do
  command -v "$tool" >/dev/null || { echo "Missing $tool. The app will install required preparation tools." >&2; exit 1; }
done
if ! grep -qw btrfs /proc/filesystems; then
  modprobe btrfs || { echo 'This WSL kernel cannot load Btrfs. Update WSL, restart WSL and try again. A missing kernel module cannot be fixed by installing btrfs-progs alone.' >&2; exit 1; }
fi
[[ $mode = prepare || $mode = check ]] && { echo 'Linux backend ready.'; exit 0; }
[[ $mode = patch ]] || { echo 'Unknown backend action.' >&2; exit 1; }
repo=${2:?repository required}; source=${3:?source required}; output=${4:?output required}
# Only regular local image paths are passed to Linux.
extra=()
if [[ ${5:-} = --include-dualboot ]]; then extra+=(--include-dualboot); fi
exec python3 "$repo/tools/patch-image.py" "$source" "$output" "${extra[@]}"
