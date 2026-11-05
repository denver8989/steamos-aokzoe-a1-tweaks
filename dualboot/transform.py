#!/usr/bin/env python3
"""Adapt a checksum-pinned upstream script locally; do not redistribute its full source."""
import hashlib,json,pathlib,subprocess
HERE=pathlib.Path(__file__).resolve().parent
def transform(source,destination):
 source=pathlib.Path(source);destination=pathlib.Path(destination);data=source.read_bytes();known=json.loads((HERE/'upstream.json').read_text())
 if hashlib.sha256(data).hexdigest()!=known['sha256']:raise RuntimeError('Unknown InnoVision installer revision; review required')
 s=data.decode();s=s.replace('set -eu','set -Eeuo pipefail\n[[ $EUID = 0 ]] || { echo "Run the guarded A1 dual-boot launcher." >&2; exit 1; }\nOWD="$(cd -- "$(dirname -- "$0")" && pwd)"\n[[ -f ${A1_DUALBOOT_PLAN:-} ]] || { echo "Missing guarded dual-boot plan." >&2; exit 1; }\nsource "$A1_DUALBOOT_PLAN"\na1_frozen=0\nunfreeze_a1() { [[ ${a1_frozen:-0} = 0 ]] || fsfreeze -u / 2>/dev/null || true; }\ntrap unfreeze_a1 EXIT\ntrap \'echo "Dual-boot install stopped at line $LINENO (exit $?)" >&2\' ERR',1)
 a=s.index('prompt_step "Custom SteamOS Install"');z=s.index('##############################################################################\n# Functions to Create',a)
 # No arbitrary disk text, manual partition indices, wipe or sanitize choice remains.
 s=s[:a]+'''# Disk/indices are supplied only by the guarded planner, never by arbitrary prompt text.
writePartitionTable=0
'''+s[z:]
 a=s.index('create_custom_parts() {');z=s.index('\n# Format functions',a)
 s=s[:a]+'''create_custom_parts() {
  /usr/bin/python3 "$OWD/a1-dualboot.py" create --plan "$A1_DUALBOOT_JSON"
}
'''+s[z:]
 a=s.index('  if [[ $writePartitionTable = 1 ]]; then',s.index('repair_steps() {'));z=s.index('\n  # Format the var partitions first',a)
 s=s[:a]+'''  /usr/bin/python3 "$OWD/a1-dualboot.py" verify --plan "$A1_DUALBOOT_JSON"
'''+s[z:]
 # Remove unreachable secure-erase helpers to keep this integration strictly preserve-only.
 a=s.index('# return sanitize state');z=s.index('##############################################################################\n# Configuration',a);s=s[:a]+s[z:]
 s=s.replace('  finalize_part A','  /usr/bin/python3 "$OWD/a1-dualboot.py" verify-boot-mapping --plan "$A1_DUALBOOT_JSON"\n  finalize_part A')
 s=s.replace('prompt_reboot "Custom Install complete."','echo "SteamOS installation completed in new partitions. Existing Windows partitions were retained. Reboot when ready; use the firmware boot menu to select Windows Boot Manager or SteamOS."')
 s=s.replace('  fsfreeze -f /','  a1_frozen=1\n  fsfreeze -f /').replace('  fsfreeze -u /','  fsfreeze -u /\n  a1_frozen=0')
 destination.write_text(s);destination.chmod(0o755);subprocess.run(['bash','-n',str(destination)],check=True)
 if 'sanitize_all' in s or 'sgdisk --new=' in s or 'sfdisk "$DISK"' in s:raise RuntimeError('Unexpected destructive branch remains')
