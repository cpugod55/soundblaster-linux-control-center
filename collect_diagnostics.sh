#!/usr/bin/env bash
set -u

OUT="soundblaster-diagnostics-$(date +%Y%m%d-%H%M%S).txt"

{
    echo "Sound Blaster Linux Control Center Diagnostic Report"
    echo "Generated: $(date)"
    echo

    echo "=== SYSTEM ==="
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "Operating System: ${PRETTY_NAME:-unknown}"
    fi
    echo "Kernel: $(uname -sr)"
    echo "Architecture: $(uname -m)"

    if command -v hostnamectl >/dev/null 2>&1; then
        VENDOR="$(hostnamectl 2>/dev/null | sed -n 's/^Hardware Vendor:[[:space:]]*//p')"
        MODEL="$(hostnamectl 2>/dev/null | sed -n 's/^Hardware Model:[[:space:]]*//p')"
        [ -n "$VENDOR" ] && echo "Hardware Vendor: $VENDOR"
        [ -n "$MODEL" ] && echo "Hardware Model: $MODEL"
    fi

    echo
    echo "=== DISTRIBUTION ==="
    if [ -f /etc/os-release ]; then
        grep -E '^(PRETTY_NAME|NAME|VERSION_ID|VERSION_CODENAME|ID|ID_LIKE)=' /etc/os-release
    fi

    echo
    echo "=== KERNEL ==="
    uname -srmo

    echo
    echo "=== VERSIONS ==="

    if command -v python3 >/dev/null 2>&1; then
        echo "Python: $(python3 --version 2>&1)"
    fi

    if command -v pipewire >/dev/null 2>&1; then
        PIPEWIRE_VERSION="$(pipewire --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)"
        echo "PipeWire: ${PIPEWIRE_VERSION:-unknown}"
    fi

    if command -v wireplumber >/dev/null 2>&1; then
        WIREPLUMBER_VERSION="$(wireplumber --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)"
        echo "WirePlumber: ${WIREPLUMBER_VERSION:-unknown}"
    fi

    if command -v wpctl >/dev/null 2>&1; then
        echo "wpctl: available"
    fi

    if command -v pactl >/dev/null 2>&1; then
        echo "pactl: $(pactl --version 2>&1 | head -n 1)"
    fi

    echo
    echo "=== AUDIO DEVICES ==="
    pactl list short cards 2>/dev/null || true

    echo
    echo "=== AUDIO SINKS ==="
    pactl list short sinks 2>/dev/null || true

    echo
    echo "=== AUDIO SOURCES ==="
    pactl list short sources 2>/dev/null || true

    echo
    echo "=== PIPEWIRE STATUS ==="
    wpctl status 2>/dev/null         | sed -E             -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9._-]+/[USER-REDACTED]/g'             -e 's/cookie:[0-9]+/cookie:[ID-REDACTED]/g'             -e 's/, pid:[0-9]+/, pid:[PID-REDACTED]/g'         || true

    echo
    echo "=== SOUNDBLASTER APPLICATION ==="

    if [ -x "$HOME/.local/bin/soundblaster-zse-control" ]; then
        echo "Launcher: installed"
    else
        echo "Launcher: not found"
    fi

    APP="$HOME/.local/lib/soundblaster-zse-control/control.py"

    if [ -f "$APP" ]; then
        echo "Application: installed"
        grep -m1 -E '^[[:space:]]*VERSION[[:space:]]*=' "$APP" 2>/dev/null || true
    else
        echo "Application: not found"
    fi

    echo
    echo "=== SOUNDBLASTER CONFIGURATION ==="

    STATE="$HOME/.config/soundblaster-zse-control/state.json"

    if [ -f "$STATE" ]; then
        echo "State file: present"
        grep -m1 '"version"' "$STATE" 2>/dev/null || true
    else
        echo "State file: not found"
    fi

    echo
    echo "=== END REPORT ==="

} > "$OUT"

# Privacy cleanup.
# The diagnostic report intentionally does not collect hostname,
# machine ID, boot ID, systemd status, journal output, or process IDs.

sed -i -E \
    -e "s|/home/[^ /]+|/home/[REDACTED]|g" \
    -e "s/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/[EMAIL-REDACTED]/g" \
    -e "s/[0-9a-fA-F]{32,}/[ID-REDACTED]/g" \
    "$OUT"

echo
echo "Diagnostic report created:"
echo "$OUT"
echo
echo "Review the report before attaching it to a GitHub issue."
