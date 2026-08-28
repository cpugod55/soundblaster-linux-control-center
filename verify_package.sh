#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 -m py_compile "$HERE/app/soundblaster_zse_control.py"
python3 -m unittest discover -s "$HERE/tests" -p 'test_*.py'
bash -n "$HERE/install.sh"
bash -n "$HERE/uninstall.sh"
for f in README.md TROUBLESHOOTING.md CHANGELOG.md LICENSE UPGRADE_NOTES.md; do test -s "$HERE/$f"; done
echo "Package verification passed."
