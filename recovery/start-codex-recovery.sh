#!/bin/bash
set -euo pipefail
bindir="$HOME/.local/share/a1-codex/0.166.0/bin"
if [[ ! -x $bindir/codex ]]; then
  printf 'Optional Codex needs three official downloads (internet required). No sign-in is bundled.\n'
  printf 'Download and install Codex 0.166.0 in your home directory now? [y/N] '
  read -r answer
  [[ $answer = y || $answer = Y ]] || exit 0
  /usr/bin/python3 "${BASH_SOURCE[0]%/*}/install-codex.py"
fi
binary=$(readlink -f -- "$bindir/codex")
bindir=${binary%/*}
for helper in codex-code-mode-host codex-exec-server; do
  [[ -x $bindir/$helper ]] || { printf 'Codex companion missing: %s\n' "$helper"; exit 1; }
done
export PATH="$bindir:$PATH"
mkdir -p "$HOME/SteamOS-Recovery"
exec "$binary" --cd "$HOME/SteamOS-Recovery" "$@"
