#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
python3 -m unittest discover -s tests -v
python3 -m py_compile tools/*.py recovery/*.py dualboot/*.py payload/etc/aokzoe-a1/support.py
for script in install.sh recovery/*.sh windows/backend.sh tests/check.sh payload/etc/aokzoe-a1/bin/gamescope payload/etc/grub.d/09_aokzoe_a1; do bash -n "$script"; done
for launcher in ./*.desktop recovery/Desktop/*.desktop; do desktop-file-validate "$launcher"; done
