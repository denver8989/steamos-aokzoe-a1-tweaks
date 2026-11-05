#!/bin/bash
set -uo pipefail
[[ $EUID = 0 ]] || exec sudo -- "$0" "$@"
logdir=/home/deck/SteamOS-Recovery/logs
mkdir -p "$logdir"
logfile=$(mktemp "$logdir/install-$(date +%Y%m%d-%H%M%S)-XXXX.log")
chmod 644 "$logfile"
exec > >(tee -a "$logfile") 2>&1
printf 'SteamOS AOKZOE A1 installation. Log: %s\n' "$logfile"
"${BASH_SOURCE[0]%/*}"/repair_device.sh all
rc=$?
if [[ $rc != 0 ]]; then
  printf '\nInstallation stopped (exit %s). The drive error above was saved in:\n%s\n' "$rc" "$logfile"
  printf '\nCodex Recovery is available on the desktop. Press Enter to close this window.\n'
  read -r _ || true
fi
exit "$rc"
