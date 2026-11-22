#!/usr/bin/env bash
set -euo pipefail
APP_ID="soundblaster-zse-control"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
systemctl --user disable --now soundblaster-zse-audio-return.service >/dev/null 2>&1 || true
rm -f "$SYSTEMD_USER_DIR/soundblaster-zse-audio-return.service"
systemctl --user disable --now soundblaster-zse-relaunch-helper.service >/dev/null 2>&1 || true
rm -f "$SYSTEMD_USER_DIR/soundblaster-zse-relaunch-helper.service"
systemctl --user daemon-reload >/dev/null 2>&1 || true
rm -f "$HOME/.local/bin/soundblaster-zse-control"
rm -rf "$HOME/.local/lib/$APP_ID"
rm -f "$HOME/.local/share/applications/soundblaster-zse-control.desktop"
rm -f "$HOME/.config/autostart/soundblaster-zse-restore.desktop"
echo "Application/launchers removed."
echo "Audio configs and saved presets were intentionally kept:"
echo "  $HOME/.config/pipewire/filter-chain.conf.d/soundblaster-zse-eq.conf" "$HOME/.config/pipewire/filter-chain.conf.d/soundblaster-mic-processing.conf" "$HOME/.config/pipewire/filter-chain.conf.d/soundblaster-zse-fill-dsp.conf"
echo "  $HOME/.config/pipewire/pipewire-pulse.conf.d/10-speaker-fill.conf"
echo "  $HOME/.config/$APP_ID/state.json"
echo "Remove those manually only if you also want to remove the EQ configuration and settings."
