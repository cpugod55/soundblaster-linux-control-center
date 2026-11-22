#!/usr/bin/env bash
set -euo pipefail

APP_VERSION="3.3.7"
APP_ID="soundblaster-zse-control"
HERE="$(cd "$(dirname "$0")" && pwd)"
APP_SRC="$HERE/app/soundblaster_zse_control.py"
ASSET_SRC="$HERE/assets"
LIB_DIR="$HOME/.local/lib/$APP_ID"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
STATE_DIR="$HOME/.config/$APP_ID"
EQ_CONF="$HOME/.config/pipewire/filter-chain.conf.d/soundblaster-zse-eq.conf"
LEGACY_EQ_CONF="$HOME/.config/pipewire/filter-chain.conf.d/z5500-eq.conf"
FILL_CONF="$HOME/.config/pipewire/pipewire-pulse.conf.d/10-speaker-fill.conf"
OLD_STATE="$HOME/.config/soundblaster-zse-control.json"
OLD_SCRIPT="$HOME/soundblaster-zse-control.py"
STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET=""
RESTART=1
SETUP_OPTICAL=1
CA0132_CHANNEL_FIX=0
CONNECTION="auto"
SPEAKER_LAYOUT="auto"
A52_PULSE_CONF="$HOME/.config/pipewire/pipewire-pulse.conf.d/20-soundblaster-a52.conf"
CA0132_WP_CONF="$HOME/.config/wireplumber/wireplumber.conf.d/51-ca0132-channel-map.conf"

# This is a user-local installer. Running the installer itself with sudo would
# redirect HOME-owned application/state paths to root and can make an upgrade
# appear to lose the user's settings. Dependency commands below request sudo
# only when a host package actually needs it.
if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "ERROR: Do not run this installer with sudo/root." >&2
  echo "Run it as your normal desktop user: ./install.sh" >&2
  exit 1
fi

usage() {
  cat <<EOF
Sound Blaster Linux Control Center $APP_VERSION installer

Usage: ./install.sh [--sink PIPEWIRE_SINK] [--connection auto|analog|digital] [--layout auto|stereo|2.1|4.0|4.1|5.0|5.1] [--no-restart] [--ca0132-channel-fix]

  --sink NAME      Physical 5.1 PipeWire/Pulse sink to receive Sound Blaster EQ output.
                   If omitted, the installer preserves an existing target or
                   tries to detect a 5.1 surround/AC3 sink.
  --connection MODE  Output connection: auto, analog, or digital. Auto respects the active Sound Blaster profile.
  --layout LAYOUT    Speaker layout: auto, stereo, 2.1, 4.0, 4.1, 5.0, or 5.1.
                     Digital layouts above stereo use A52/AC3 when supported.
  --no-restart     Install files without restarting the user PipeWire services.
  --no-optical-setup  Do not attempt to install Ubuntu A52/AC3 support when missing.
  --ca0132-channel-fix  Apply the verified Sound Blaster Z/CA0132 analog 5.1
                        WirePlumber map [ FL FR FC LFE RL RR ]. This is opt-in
                        until it has been validated on more CA0132 systems.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sink) TARGET="${2:-}"; shift 2 ;;
    --connection) CONNECTION="${2:-}"; shift 2 ;;
    --layout) SPEAKER_LAYOUT="${2:-}"; shift 2 ;;
    --no-restart) RESTART=0; shift ;;
    --no-optical-setup) SETUP_OPTICAL=0; shift ;;
    --ca0132-channel-fix) CA0132_CHANNEL_FIX=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

case "$CONNECTION" in auto|analog|digital) ;; *) echo "ERROR: --connection must be auto, analog, or digital" >&2; exit 2 ;; esac
case "$SPEAKER_LAYOUT" in auto|stereo|2.1|4.0|4.1|5.0|5.1) ;; *) echo "ERROR: unsupported --layout: $SPEAKER_LAYOUT" >&2; exit 2 ;; esac

# Distribution-aware dependency setup. The application itself remains user-local;
# only missing host audio/runtime packages are installed.
OS_ID="unknown"
OS_LIKE=""
if [[ -r /etc/os-release ]]; then
  # Read distro metadata in a subshell so /etc/os-release variables such as
  # VERSION can never overwrite the application's own version stamp.
  OS_ID="$(. /etc/os-release; printf '%s' "${ID:-unknown}")"
  OS_LIKE="$(. /etc/os-release; printf '%s' "${ID_LIKE:-}")"
fi

is_bazzite=0
if [[ "$OS_ID" == "bazzite" ]] || grep -qi 'bazzite' /etc/os-release 2>/dev/null; then
  is_bazzite=1
fi

is_opensuse=0
if [[ "$OS_ID" == opensuse* || "$OS_LIKE" == *"opensuse"* || "$OS_LIKE" == *"suse"* ]] || command -v zypper >/dev/null 2>&1; then
  is_opensuse=1
fi

echo "Detected Linux distribution: $OS_ID${OS_LIKE:+ (like $OS_LIKE)}"

have_tk() { python3 -c 'import tkinter' >/dev/null 2>&1; }
have_a52_runtime() { command -v aplay >/dev/null 2>&1 && aplay -L 2>/dev/null | grep -q '^a52'; }
have_a52_package() { command -v rpm >/dev/null 2>&1 && rpm -q alsa-plugins-a52 >/dev/null 2>&1; }
have_a52_deb_package() { command -v dpkg-query >/dev/null 2>&1 && dpkg-query -W -f='${Status}' libasound2-plugins 2>/dev/null | grep -q 'install ok installed' && find /usr/lib /usr/lib64 -name 'libasound_module_pcm_a52.so' -print -quit 2>/dev/null | grep -q .; }
have_a52() {
  # On Fedora Atomic/Bazzite, package presence is authoritative for dependency
  # installation. `aplay -L` can omit the a52 PCM even when the host RPM is
  # correctly layered, depending on ALSA configuration/device enumeration.
  if command -v rpm >/dev/null 2>&1; then
    # Fedora/Bazzite can have a fully working A52 plugin even when `aplay -L`
    # omits the a52 hint. Package presence is therefore authoritative here.
    have_a52_package || have_a52_runtime
  elif command -v pacman >/dev/null 2>&1; then
    pacman -Q alsa-plugins >/dev/null 2>&1 && find /usr/lib /usr/lib64 -name 'libasound_module_pcm_a52.so' -print -quit 2>/dev/null | grep -q .
  elif command -v dpkg-query >/dev/null 2>&1; then
    # Debian/Ubuntu/Mint can also omit the A52 hint from `aplay -L` even when
    # libasound2-plugins provides a working pcm_a52 encoder.
    have_a52_deb_package || have_a52_runtime
  else
    have_a52_runtime
  fi
}

have_zamaxim() {
  [[ -f /usr/lib/ladspa/ZaMaximX2-ladspa.so ]] ||
  [[ -f /usr/lib64/ladspa/ZaMaximX2-ladspa.so ]] ||
  find /usr/lib /usr/lib64 -type f -path '*/ladspa/ZaMaximX2-ladspa.so' -print -quit 2>/dev/null | grep -q .
}

install_apt_deps() {
  local need=()
  command -v python3 >/dev/null 2>&1 || need+=(python3)
  have_tk || need+=(python3-tk)
  command -v aplay >/dev/null 2>&1 || need+=(alsa-utils)
  command -v pactl >/dev/null 2>&1 || need+=(pulseaudio-utils)
  command -v pw-cli >/dev/null 2>&1 || need+=(pipewire-bin)
  command -v pw-loopback >/dev/null 2>&1 || need+=(pipewire-bin)
  command -v pw-record >/dev/null 2>&1 || need+=(pipewire-bin)
  command -v wireplumber >/dev/null 2>&1 || need+=(wireplumber)
  have_zamaxim || need+=(zam-plugins)
  if [[ $SETUP_OPTICAL -eq 1 ]] && ! have_a52; then need+=(libasound2-plugins); fi
  if (( ${#need[@]} )); then
    mapfile -t need < <(printf '%s\n' "${need[@]}" | awk '!seen[$0]++')
    echo "Installing Debian/Ubuntu dependencies: ${need[*]}"
    if ! sudo apt-get update; then
      # Mint/Ubuntu Live media may leave an active `deb cdrom:` entry that APT
      # refuses to use. Disable only those stale optical-media entries and retry.
      local changed_cdrom=0
      local src
      for src in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do
        [[ -f "$src" ]] || continue
        if grep -Eq '^[[:space:]]*deb[[:space:]]+cdrom:' "$src"; then
          sudo cp -a "$src" "${src}.soundblaster-backup" 2>/dev/null || true
          sudo sed -i -E '/^[[:space:]]*deb[[:space:]]+cdrom:/s/^/# Sound Blaster installer disabled stale Live-media source: /' "$src"
          changed_cdrom=1
        fi
      done
      if [[ $changed_cdrom -eq 1 ]]; then
        echo "Disabled stale APT cdrom source(s) from the Live environment; retrying package index update."
        sudo apt-get update
      else
        echo "ERROR: apt-get update failed and no stale cdrom source was found to repair." >&2
        exit 1
      fi
    fi
    sudo apt-get install -y "${need[@]}"
  fi
}

install_fedora_deps() {
  local need=()
  command -v python3 >/dev/null 2>&1 || need+=(python3)
  have_tk || need+=(python3-tkinter)
  command -v aplay >/dev/null 2>&1 || need+=(alsa-utils)
  command -v pactl >/dev/null 2>&1 || need+=(pulseaudio-utils)
  command -v pw-cli >/dev/null 2>&1 || need+=(pipewire-utils)
  command -v pw-loopback >/dev/null 2>&1 || need+=(pipewire-utils)
  command -v wireplumber >/dev/null 2>&1 || need+=(wireplumber)
  have_zamaxim || need+=(ladspa-zam-plugins)
  if [[ $SETUP_OPTICAL -eq 1 ]] && ! have_a52; then need+=(alsa-plugins-a52); fi
  if (( ${#need[@]} )); then
    echo "Installing Fedora dependencies: ${need[*]}"
    if command -v dnf5 >/dev/null 2>&1; then
      sudo dnf5 install -y "${need[@]}"
    else
      sudo dnf install -y "${need[@]}"
    fi
  fi
}

install_arch_deps() {
  local need=()
  command -v python3 >/dev/null 2>&1 || need+=(python)
  have_tk || need+=(tk)
  command -v aplay >/dev/null 2>&1 || need+=(alsa-utils)
  command -v pactl >/dev/null 2>&1 || need+=(libpulse)
  command -v pw-cli >/dev/null 2>&1 || need+=(pipewire)
  command -v pw-loopback >/dev/null 2>&1 || need+=(pipewire)
  command -v wireplumber >/dev/null 2>&1 || need+=(wireplumber)
  have_zamaxim || need+=(zam-plugins-ladspa)
  # Arch ships pcm_a52 in alsa-plugins; ffmpeg supplies the codec dependency.
  if [[ $SETUP_OPTICAL -eq 1 ]] && ! have_a52; then need+=(alsa-plugins ffmpeg); fi
  if (( ${#need[@]} )); then
    echo "Installing Arch/Manjaro dependencies: ${need[*]}"
    if ! find /var/lib/pacman/sync -maxdepth 1 -name '*.db' -print -quit 2>/dev/null | grep -q .; then
      echo ""
      echo "ACTION REQUIRED"
      echo "Pacman package databases are not initialized (common on a fresh Live USB)."
      echo "Run:"
      echo "  sudo pacman -Sy"
      echo "Then rerun:"
      echo "  ./install.sh"
      exit 1
    fi
    sudo pacman -S --needed --noconfirm "${need[@]}"
  fi
}

install_opensuse_deps() {
  local need=()
  command -v python3 >/dev/null 2>&1 || need+=(python3)
  have_tk || need+=(python3-tk)
  command -v aplay >/dev/null 2>&1 || need+=(alsa-utils)
  command -v pactl >/dev/null 2>&1 || need+=(pulseaudio-utils)
  command -v pw-cli >/dev/null 2>&1 || need+=(pipewire)
  command -v pw-loopback >/dev/null 2>&1 || need+=(pipewire)
  command -v pw-record >/dev/null 2>&1 || need+=(pipewire)
  command -v wireplumber >/dev/null 2>&1 || need+=(wireplumber)
  have_zamaxim || need+=(ladspa-zam-plugins)
  if [[ $SETUP_OPTICAL -eq 1 ]] && ! have_a52; then need+=(alsa-plugins-a52); fi
  if (( ${#need[@]} )); then
    mapfile -t need < <(printf '%s\n' "${need[@]}" | awk '!seen[$0]++')
    echo "Installing openSUSE dependencies: ${need[*]}"
    sudo zypper --non-interactive install "${need[@]}"
  fi
}

check_bazzite_deps() {
  local missing=()
  command -v python3 >/dev/null 2>&1 || missing+=(python3)
  have_tk || missing+=(python3-tkinter)
  command -v aplay >/dev/null 2>&1 || missing+=(alsa-utils)
  command -v pactl >/dev/null 2>&1 || missing+=(pulseaudio-utils)
  command -v pw-cli >/dev/null 2>&1 || missing+=(pipewire-utils)
  command -v pw-loopback >/dev/null 2>&1 || missing+=(pipewire-utils)
  command -v wireplumber >/dev/null 2>&1 || missing+=(wireplumber)
  have_zamaxim || missing+=(ladspa-zam-plugins)
  if [[ $SETUP_OPTICAL -eq 1 ]] && ! have_a52; then missing+=(alsa-plugins-a52); fi
  if (( ${#missing[@]} )); then
    echo ""
    echo "ACTION REQUIRED"
    echo "Bazzite/Fedora Atomic detected. No host packages were changed."
    echo "Missing host components: ${missing[*]}"
    echo "Install them in one transaction:"
    echo "  sudo rpm-ostree install ${missing[*]}"
    echo ""
    echo "After it completes:"
    echo "  1. Reboot to activate the new rpm-ostree deployment."
    echo "  2. Return to this directory and run ./install.sh again."
    echo "The application and its settings remain user-local under ~/.local and ~/.config."
    exit 1
  fi
}

if [[ $is_bazzite -eq 1 ]]; then
  check_bazzite_deps
elif command -v apt-get >/dev/null 2>&1; then
  install_apt_deps
elif command -v dnf5 >/dev/null 2>&1 || command -v dnf >/dev/null 2>&1; then
  install_fedora_deps
elif command -v pacman >/dev/null 2>&1; then
  install_arch_deps
elif command -v zypper >/dev/null 2>&1; then
  install_opensuse_deps
else
  echo "Unknown/unsupported package manager. No system packages will be changed."
  echo "The app can still install if Python 3 + Tk, PipeWire, WirePlumber, pactl and ALSA utilities are already present."
fi

ensure_debian_audio_ready() {
  if command -v dpkg-query >/dev/null 2>&1 && command -v pactl >/dev/null 2>&1 && ! pactl info >/dev/null 2>&1; then
    echo "Starting Debian user PipeWire audio services..."
    systemctl --user start pipewire.socket pipewire-pulse.socket >/dev/null 2>&1 || true
    systemctl --user start pipewire.service wireplumber.service pipewire-pulse.service >/dev/null 2>&1 || true
    for _ in {1..20}; do
      pactl info >/dev/null 2>&1 && return 0
      sleep 0.25
    done
    echo "ERROR: PipeWire-Pulse is installed but pactl still cannot connect." >&2
    echo "Check: systemctl --user status pipewire.service wireplumber.service pipewire-pulse.service --no-pager -l" >&2
    exit 1
  fi
}

ensure_debian_audio_ready

for cmd in python3 pactl pw-cli pw-dump systemctl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command '$cmd' was not found after dependency setup." >&2
    exit 1
  fi
done

if ! have_tk; then
  echo "ERROR: Python tkinter is missing." >&2
  case "$OS_ID" in
    ubuntu|debian|linuxmint|pop) echo "Install: sudo apt install python3-tk" >&2 ;;
    fedora) echo "Install: sudo dnf install python3-tkinter" >&2 ;;
    arch|manjaro|endeavouros) echo "Install: sudo pacman -S tk" >&2 ;;
    opensuse*) echo "Install: sudo zypper install python3-tk" >&2 ;;
  esac
  exit 1
fi

if ! command -v parec >/dev/null 2>&1; then
  echo "NOTE: parec was not found. Audio processing will work, but spectrum/channel meters may be unavailable."
fi

# Refuse to write through root-owned/unwritable user PipeWire config paths.
# This catches damage left by older installs that were accidentally run with sudo
# and replaces a Python PermissionError traceback with one precise repair command.
check_user_config_path() {
  local p="$1" owner="unknown"
  if [[ -e "$p" && ! -w "$p" ]]; then
    owner="$(stat -c '%U:%G' "$p" 2>/dev/null || echo unknown)"
    echo "ERROR: $p is not writable by $(id -un) (owner: $owner)." >&2
    echo "Repair ownership, then rerun the installer without sudo:" >&2
    echo "  sudo chown -R \"$(id -un):$(id -gn)\" \"$HOME/.config/pipewire\"" >&2
    exit 1
  fi
}
check_user_config_path "$HOME/.config"
check_user_config_path "$HOME/.config/pipewire"
check_user_config_path "$(dirname "$EQ_CONF")"
check_user_config_path "$(dirname "$FILL_CONF")"
if [[ $CA0132_CHANNEL_FIX -eq 1 ]]; then
  check_user_config_path "$HOME/.config/wireplumber"
  check_user_config_path "$(dirname "$CA0132_WP_CONF")"
fi

if ! mkdir -p "$LIB_DIR" "$BIN_DIR" "$APP_DIR" "$AUTOSTART_DIR" "$STATE_DIR" "$(dirname "$EQ_CONF")" "$(dirname "$FILL_CONF")"; then
  echo "ERROR: Could not create user configuration directories." >&2
  echo "If ~/.config/pipewire is root-owned, repair it with:" >&2
  echo "  sudo chown -R \"$(id -un):$(id -gn)\" \"$HOME/.config/pipewire\"" >&2
  exit 1
fi

backup_if_exists() {
  local f="$1"
  if [[ -e "$f" ]]; then
    cp -a "$f" "$f.backup-$STAMP"
    echo "Backup: $f.backup-$STAMP"
  fi
}

backup_if_exists "$EQ_CONF"
backup_if_exists "$FILL_CONF"
backup_if_exists "$A52_PULSE_CONF"
backup_if_exists "$APP_DIR/soundblaster-zse-control.desktop"
backup_if_exists "$AUTOSTART_DIR/soundblaster-zse-restore.desktop"
backup_if_exists "$APP_DIR/z5500-eq.desktop"
backup_if_exists "$AUTOSTART_DIR/z5500-eq-restore.desktop"
backup_if_exists "$LEGACY_EQ_CONF"

# User state is the most valuable upgrade input. Back it up before any
# migration or normalization code can touch it. The timestamped copy is never
# consumed automatically; it is an explicit rollback/recovery checkpoint.
backup_if_exists "$STATE_DIR/state.json"
backup_if_exists "$OLD_STATE"

# Migrate the legacy state only when no modern state exists. Never overwrite a
# current state.json with the legacy file.
if [[ ! -f "$STATE_DIR/state.json" && -f "$OLD_STATE" ]]; then
  cp -a "$OLD_STATE" "$STATE_DIR/state.json"
  echo "Migrated prior settings from $OLD_STATE"
fi

# Discover the Creative card and respect the physical connection the user has selected.
if ! PACTL_CARDS="$(pactl list cards 2>/dev/null)"; then
  echo "ERROR: pactl cannot connect to PipeWire-Pulse, so Sound Blaster hardware cannot be detected." >&2
  echo "Check: systemctl --user status pipewire.service wireplumber.service pipewire-pulse.service --no-pager -l" >&2
  exit 1
fi
SB_CARD="$(printf '%s\n' "$PACTL_CARDS" | awk '/Name: alsa_card\.pci-/{card=$2} /alsa\.mixer_name = "Creative Sound Blaster Z"|CA0132 Sound Core3D|Sound Blaster/{if(card){print card; exit}}')"
SB_ACTIVE_PROFILE=""
if [[ -n "$SB_CARD" ]]; then
  SB_ACTIVE_PROFILE="$(pactl list cards 2>/dev/null | awk -v wanted="$SB_CARD" '$1=="Name:" {in_card=($2==wanted)} in_card && /Active Profile:/ {print $3; exit}')"
fi
if [[ "$CONNECTION" == "auto" ]]; then
  if [[ "$SB_ACTIVE_PROFILE" == *"iec958"* ]]; then CONNECTION="digital"; elif [[ "$SB_ACTIVE_PROFILE" == *"analog"* ]]; then CONNECTION="analog"; fi
fi

# Explicit Digital + stereo uses the normal IEC958 PCM profile.  If a prior
# multichannel selection installed the persistent A52 sink, remove that module
# first so the Creative card can reclaim its IEC958 PCM.
if [[ -z "$TARGET" && "$CONNECTION" == "digital" && "$SPEAKER_LAYOUT" == "stereo" && -n "$SB_CARD" ]]; then
  if [[ -f "$A52_PULSE_CONF" ]]; then
    rm -f "$A52_PULSE_CONF"
    if [[ $RESTART -eq 1 ]]; then systemctl --user restart pipewire-pulse.service 2>/dev/null || true; sleep 0.75; fi
  fi
  DIGITAL_STEREO_PROFILE=""
  if pactl list cards 2>/dev/null | awk -v wanted="$SB_CARD" '
    $1=="Name:" {in_card=($2==wanted)}
    in_card && /output:iec958-stereo\+input:analog-stereo:/ {found=1}
    END {exit !found}'
  then
    DIGITAL_STEREO_PROFILE="output:iec958-stereo+input:analog-stereo"
  elif pactl list cards 2>/dev/null | awk -v wanted="$SB_CARD" '
    $1=="Name:" {in_card=($2==wanted)}
    in_card && /output:iec958-stereo:/ {found=1}
    END {exit !found}'
  then
    DIGITAL_STEREO_PROFILE="output:iec958-stereo"
  fi
  if [[ -n "$DIGITAL_STEREO_PROFILE" ]]; then
    pactl set-card-profile "$SB_CARD" "$DIGITAL_STEREO_PROFILE" >/dev/null 2>&1 || true
    for _ in {1..20}; do
      TARGET="$(pactl list short sinks 2>/dev/null | awk -F '\t' '$2 ~ /iec958-stereo/ {print $2; exit}')"
      [[ -n "$TARGET" ]] && break
      sleep 0.25
    done
    [[ -n "$TARGET" ]] && echo "Using Creative Digital stereo profile: $DIGITAL_STEREO_PROFILE"
  fi
fi

# Prefer a native Creative AC3 5.1 profile when PipeWire/ACP advertises one.
# This preserves the proven Ubuntu path and avoids replacing a native profile
# with the compatibility A52 sink unnecessarily.
if [[ -z "$TARGET" && "$CONNECTION" == "digital" && "$SPEAKER_LAYOUT" != "stereo" && -n "$SB_CARD" ]]; then
  NATIVE_AC3_PROFILE=""
  if pactl list cards 2>/dev/null | awk -v wanted="$SB_CARD" '
    $1=="Name:" {in_card=($2==wanted)}
    in_card && /output:iec958-ac3-surround-51\+input:analog-stereo:/ {found=1}
    END {exit !found}'
  then
    NATIVE_AC3_PROFILE="output:iec958-ac3-surround-51+input:analog-stereo"
  elif pactl list cards 2>/dev/null | awk -v wanted="$SB_CARD" '
    $1=="Name:" {in_card=($2==wanted)}
    in_card && /output:iec958-ac3-surround-51:/ {found=1}
    END {exit !found}'
  then
    NATIVE_AC3_PROFILE="output:iec958-ac3-surround-51"
  fi
  if [[ -n "$NATIVE_AC3_PROFILE" ]]; then
    pactl set-card-profile "$SB_CARD" "$NATIVE_AC3_PROFILE" >/dev/null 2>&1 || true
    for _ in {1..20}; do
      TARGET="$(pactl list short sinks 2>/dev/null | awk -F '\t' '$2 ~ /iec958-ac3-surround-51/ {print $2; exit}')"
      [[ -n "$TARGET" ]] && break
      sleep 0.25
    done
    if [[ -n "$TARGET" ]]; then
      echo "Using native Creative Digital AC3 5.1 profile: $NATIVE_AC3_PROFILE"
    fi
  fi
fi

# Arch/CachyOS, Fedora, and Debian/Ubuntu/Mint do not necessarily advertise an ACP AC3 profile even
# when their pcm_a52 encoder works. For Digital + 5.1, create a persistent
# PipeWire-Pulse ALSA sink backed by the card's real IEC958 PCM. This remains
# capability-driven: card/device numbers are discovered from aplay, never
# hard-coded. Bazzite keeps its separate Atomic-host path.
USE_PERSISTENT_A52=0
if [[ $is_bazzite -eq 0 ]] && {
  command -v pacman >/dev/null 2>&1 ||
  command -v dpkg-query >/dev/null 2>&1 ||
  command -v zypper >/dev/null 2>&1 ||
  [[ "$OS_ID" == "fedora" || "$OS_LIKE" == *"fedora"* || $is_opensuse -eq 1 ]]
}; then
  USE_PERSISTENT_A52=1
fi
if [[ -z "$TARGET" && "$CONNECTION" == "digital" && "$SPEAKER_LAYOUT" != "stereo" && $USE_PERSISTENT_A52 -eq 1 ]] && have_a52; then
  SB_ALSA_PAIR="$(aplay -l 2>/dev/null | sed -nE 's/^card ([0-9]+): Creative .*device ([0-9]+): .*Digital.*/\1 \2/p' | head -n1)"
  SB_ALSA_CARD="${SB_ALSA_PAIR%% *}"
  SB_ALSA_DEV="${SB_ALSA_PAIR#* }"
  if [[ "$SB_ALSA_PAIR" != *" "* ]]; then SB_ALSA_CARD=""; SB_ALSA_DEV=""; fi
  if [[ -n "$SB_ALSA_CARD" && -n "$SB_ALSA_DEV" ]]; then
    # Some CA0132 systems boot with the digital playback switches muted even
    # though the A52 encoder and hardware PCM are valid. Enable any exposed
    # IEC958 playback switches before handing the digital PCM to A52.
    if command -v amixer >/dev/null 2>&1; then
      if amixer -c "$SB_ALSA_CARD" scontrols 2>/dev/null | grep -Fq "'IEC958',0"; then
        if amixer -c "$SB_ALSA_CARD" set IEC958 unmute >/dev/null 2>&1; then
          echo "Enabled Creative IEC958 playback on ALSA card ${SB_ALSA_CARD}."
        else
          echo "WARNING: Creative IEC958 playback switch could not be enabled." >&2
        fi
      fi
      if amixer -c "$SB_ALSA_CARD" scontrols 2>/dev/null | grep -Fq "'IEC958 Default PCM',0"; then
        if amixer -c "$SB_ALSA_CARD" set 'IEC958 Default PCM' unmute >/dev/null 2>&1; then
          echo "Enabled Creative IEC958 Default PCM playback on ALSA card ${SB_ALSA_CARD}."
        else
          echo "WARNING: Creative IEC958 Default PCM playback switch could not be enabled." >&2
        fi
      fi
    fi
    mkdir -p "$(dirname "$A52_PULSE_CONF")"
    if [[ $is_opensuse -eq 1 ]]; then
      # openSUSE's alsa-plugins-a52 accepts plug:a52:<card> even though
      # `aplay -L` does not enumerate an A52 hint.
      cat > "$A52_PULSE_CONF" <<EOF
pulse.cmd = [
  { cmd = "load-module" args = "module-alsa-sink device=plug:a52:${SB_ALSA_CARD} sink_name=alsa_output.soundblaster_a52_51 sink_properties=device.description=Sound_Blaster_Digital_AC3_5.1 channels=6 rate=48000 channel_map=front-left,front-right,rear-left,rear-right,front-center,lfe" }
]
EOF
    else
      cat > "$A52_PULSE_CONF" <<EOF
pulse.cmd = [
  { cmd = "load-module" args = "module-alsa-sink device=plug:{SLAVE=\\"a52:${SB_ALSA_CARD},'hw:${SB_ALSA_CARD},${SB_ALSA_DEV}'\\"} sink_name=alsa_output.soundblaster_a52_51 sink_properties=device.description=Sound_Blaster_Digital_AC3_5.1 channels=6 rate=48000 channel_map=front-left,front-right,rear-left,rear-right,front-center,lfe" }
]
EOF
    fi
    # The normal ACP IEC958 profile and the A52 encoder both open the same
    # S/PDIF PCM. Release the card profile first or module-alsa-sink fails with
    # EBUSY (Device or resource busy). Keep the card off while A52 owns it.
    SB_PROFILE_BEFORE_A52="$SB_ACTIVE_PROFILE"
    if [[ -n "$SB_CARD" ]]; then
      pactl set-card-profile "$SB_CARD" off >/dev/null 2>&1 || true
      sleep 0.25
    fi
    if [[ $RESTART -eq 1 ]]; then systemctl --user restart pipewire-pulse.service 2>/dev/null || true; sleep 1; fi
    for _ in {1..20}; do pactl list short sinks 2>/dev/null | grep -q 'alsa_output.soundblaster_a52_51' && break; sleep 0.25; done
    if pactl list short sinks 2>/dev/null | grep -q 'alsa_output.soundblaster_a52_51'; then
      TARGET="alsa_output.soundblaster_a52_51"
      if [[ $is_opensuse -eq 1 ]]; then
        echo "Digital AC3 5.1 target created from openSUSE A52 PCM plug:a52:${SB_ALSA_CARD}."
      else
        echo "Digital AC3 5.1 target created from Creative IEC958 hw:${SB_ALSA_CARD},${SB_ALSA_DEV}."
      fi
    else
      echo "WARNING: A52 is installed but the persistent AC3 sink did not appear." >&2
      # A failed A52 attempt must not leave the user's Creative card disabled.
      if [[ -n "$SB_CARD" && -n "$SB_PROFILE_BEFORE_A52" && "$SB_PROFILE_BEFORE_A52" != "off" ]]; then
        pactl set-card-profile "$SB_CARD" "$SB_PROFILE_BEFORE_A52" >/dev/null 2>&1 || true
        if [[ $RESTART -eq 1 ]]; then systemctl --user restart pipewire-pulse.service 2>/dev/null || true; sleep 0.5; fi
      fi
    fi
  fi
fi

# Explicit Digital + 5.1 is fail-closed on every non-Atomic supported path.
# Never fall through to a stale/default headset, HDMI, or analog stereo sink.
# Preserve the verified 5.1 fail-closed guard and extend the same policy to
# every other explicit digital multichannel layout.
if [[ "$SPEAKER_LAYOUT" == "5.1" && -z "$TARGET" ]]; then
  if [[ $is_bazzite -eq 0 && "$CONNECTION" == "digital" ]]; then
    echo "ERROR: Digital 5.1 was explicitly requested, but no Creative AC3/A52 5.1 target could be created." >&2
    echo "The installer will not silently fall back to an analog output or another audio device." >&2
    echo "Check: systemctl --user status pipewire-pulse.service --no-pager -l" >&2
    exit 1
  fi
fi
if [[ "$CONNECTION" == "digital" && "$SPEAKER_LAYOUT" != "stereo" && "$SPEAKER_LAYOUT" != "auto" && "$SPEAKER_LAYOUT" != "5.1" && -z "$TARGET" ]]; then
  if [[ $is_bazzite -eq 0 ]]; then
    echo "ERROR: Digital $SPEAKER_LAYOUT was explicitly requested, but no Creative AC3/A52 multichannel target could be created." >&2
    echo "The installer will not silently fall back to an analog output or another audio device." >&2
    echo "Check: systemctl --user status pipewire-pulse.service --no-pager -l" >&2
    exit 1
  fi
fi

# For explicit analog layouts, select the matching advertised Creative profile.
if [[ -z "$TARGET" && "$CONNECTION" == "analog" && -n "$SB_CARD" ]]; then
  case "$SPEAKER_LAYOUT" in
    5.1|auto) WANT_PROFILE="output:analog-surround-51+input:analog-stereo" ;;
    4.1) WANT_PROFILE="output:analog-surround-41+input:analog-stereo" ;;
    4.0) WANT_PROFILE="output:analog-surround-40+input:analog-stereo" ;;
    2.1) WANT_PROFILE="output:analog-surround-21+input:analog-stereo" ;;
    stereo) WANT_PROFILE="output:analog-stereo+input:analog-stereo" ;;
    *) WANT_PROFILE="" ;;
  esac
  if [[ -n "$WANT_PROFILE" ]] && pactl list cards 2>/dev/null | grep -Fq "$WANT_PROFILE"; then
    pactl set-card-profile "$SB_CARD" "$WANT_PROFILE" >/dev/null 2>&1 || true
    # A connection/profile switch replaces the Creative sink node. Resolve the
    # newly-created analog sink now, before the stale EQ target fallback below
    # has a chance to reuse the previous Digital/AC3 node.
    case "$SPEAKER_LAYOUT" in
      5.1|auto) WANT_SINK_SUFFIX="analog-surround-51" ;;
      4.1) WANT_SINK_SUFFIX="analog-surround-41" ;;
      4.0) WANT_SINK_SUFFIX="analog-surround-40" ;;
      2.1) WANT_SINK_SUFFIX="analog-surround-21" ;;
      stereo) WANT_SINK_SUFFIX="analog-stereo" ;;
      *) WANT_SINK_SUFFIX="" ;;
    esac
    if [[ -n "$WANT_SINK_SUFFIX" ]]; then
      SB_PCI="${SB_CARD#alsa_card.}"
      for _ in {1..20}; do
        TARGET="$(pactl list short sinks 2>/dev/null | awk -F '\t' -v pci="$SB_PCI" -v suffix="$WANT_SINK_SUFFIX" '$2 ~ pci && $2 ~ suffix {print $2; exit}')"
        [[ -n "$TARGET" ]] && break
        sleep 0.25
      done
      [[ -n "$TARGET" ]] && echo "Using Creative Analog target: $TARGET"
    fi
  fi
fi

# Preserve an existing filter target if possible.
if [[ -z "$TARGET" && -f "$EQ_CONF" ]]; then
  TARGET="$(sed -n 's/.*filter\.smart\.target[[:space:]]*=[[:space:]]*{[^}]*node\.name[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$EQ_CONF" | head -n1 || true)"
  if [[ -z "$TARGET" ]]; then
    TARGET="$(sed -n 's/.*target\.object[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$EQ_CONF" | head -n1 || true)"
  fi
elif [[ -z "$TARGET" && -f "$LEGACY_EQ_CONF" ]]; then
  TARGET="$(sed -n 's/.*target\.object[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$LEGACY_EQ_CONF" | head -n1 || true)"
fi

# Never preserve an unrelated USB/HDMI target when a Creative card is present.
if [[ -n "$TARGET" && -n "$SB_CARD" && "$TARGET" != *"soundblaster_a52_51" ]]; then
  SB_PCI="${SB_CARD#alsa_card.}"
  if [[ "$TARGET" != *"${SB_PCI}"* ]]; then
    echo "Ignoring stale target from another audio device: $TARGET"
    TARGET=""
  fi
fi

# Explicit Analog setup must never fall back to a preserved Digital/AC3 target.
# Profile changes replace the Creative sink node asynchronously, so re-resolve
# the requested live analog node after all legacy-target preservation logic.
# This is deliberately fail-closed: if Analog was requested and its matching
# Creative sink is not live, stop instead of regenerating the EQ against the
# previous digital node.
if [[ "$CONNECTION" == "analog" && -n "$SB_CARD" ]]; then
  case "$SPEAKER_LAYOUT" in
    5.1|auto) WANT_ANALOG_SUFFIX="analog-surround-51" ;;
    4.1) WANT_ANALOG_SUFFIX="analog-surround-41" ;;
    4.0) WANT_ANALOG_SUFFIX="analog-surround-40" ;;
    2.1) WANT_ANALOG_SUFFIX="analog-surround-21" ;;
    stereo) WANT_ANALOG_SUFFIX="analog-stereo" ;;
    *) WANT_ANALOG_SUFFIX="" ;;
  esac
  if [[ -n "$WANT_ANALOG_SUFFIX" ]]; then
    SB_PCI="${SB_CARD#alsa_card.}"
    ANALOG_TARGET=""
    for _ in {1..20}; do
      ANALOG_TARGET="$(pactl list short sinks 2>/dev/null | awk -F '\t' -v pci="$SB_PCI" -v suffix="$WANT_ANALOG_SUFFIX" '$2 ~ pci && $2 ~ suffix {print $2; exit}')"
      [[ -n "$ANALOG_TARGET" ]] && break
      sleep 0.25
    done
    if [[ -n "$ANALOG_TARGET" ]]; then
      if [[ "$TARGET" != "$ANALOG_TARGET" ]]; then
        echo "Replacing stale/non-analog target with live Creative Analog target: $ANALOG_TARGET"
      fi
      TARGET="$ANALOG_TARGET"
    else
      echo "ERROR: Analog $SPEAKER_LAYOUT was requested, but no matching live Creative $WANT_ANALOG_SUFFIX sink appeared." >&2
      echo "The installer will not reuse a stale Digital/AC3 EQ target." >&2
      exit 1
    fi
  fi
fi

# A preserved EQ target can outlive its card profile. If the saved target is
# specifically an analog-stereo node and the exact same device now exposes a
# live analog-surround-51 sibling, follow that live sibling. This closes the
# upgrade hole where a stale stereo target could regenerate a 2-channel EQ
# even though PipeWire and the card were already running 5.1.
if [[ -n "$TARGET" && "${TARGET,,}" == *"analog-stereo"* ]]; then
  SURROUND_SIBLING="${TARGET/analog-stereo/analog-surround-51}"
  if [[ "$SURROUND_SIBLING" != "$TARGET" ]] && pactl list short sinks 2>/dev/null | awk -F '\t' -v n="$SURROUND_SIBLING" '$2 == n {found=1} END {exit !found}'; then
    echo "Replacing stale stereo target with live 5.1 sibling: $SURROUND_SIBLING"
    TARGET="$SURROUND_SIBLING"
  fi
fi

# On Bazzite/Fedora Atomic, prefer the Sound Blaster AC3 5.1 card profile when
# it is advertised as available. Preserve analog input where possible.
if [[ "$is_bazzite" -eq 1 ]] && command -v pactl >/dev/null 2>&1; then
  SB_CARD="$(pactl list cards 2>/dev/null | awk '/Name: alsa_card\.pci-/{card=$2} /alsa\.mixer_name = "Creative Sound Blaster Z"/{print card; exit}')"
  if [[ -n "$SB_CARD" ]] && pactl list cards 2>/dev/null | grep -q 'output:iec958-ac3-surround-51+input:analog-stereo'; then
    pactl set-card-profile "$SB_CARD" 'output:iec958-ac3-surround-51+input:analog-stereo' >/dev/null 2>&1 || true
    for _ in {1..20}; do
      pactl list short sinks 2>/dev/null | grep -q 'iec958-ac3-surround-51' && break
      sleep 0.25
    done
    AC3_TARGET="$(pactl list short sinks 2>/dev/null | awk -F '\t' '$2 ~ /iec958-ac3-surround-51/ {print $2; exit}')"
    if [[ -n "$AC3_TARGET" ]]; then TARGET="$AC3_TARGET"; fi
  fi
fi

# Detect a likely 5.1 hardware sink if there was no existing target.
if [[ -z "$TARGET" ]]; then
  TARGET="$(pactl list short sinks 2>/dev/null | awk -F '\t' '$2 != "soundblaster_zse_eq" && $2 != "z5500_eq" && ($2 ~ /surround-51/ || tolower($2) ~ /ac3/) {print $2; exit}')"
fi
if [[ -z "$TARGET" ]]; then
  D="$(pactl get-default-sink 2>/dev/null || true)"
  if [[ -n "$D" && "$D" != "soundblaster_zse_eq" && "$D" != "z5500_eq" ]]; then TARGET="$D"; fi
fi
if [[ -z "$TARGET" ]]; then
  TARGET="$(pactl list short sinks 2>/dev/null | awk -F '\t' '$2 != "soundblaster_zse_eq" && $2 != "z5500_eq" {print $2; exit}')"
fi

if [[ -z "$TARGET" ]]; then
  echo "ERROR: Could not detect a physical audio sink." >&2
  echo "Run 'pactl list short sinks' and reinstall with: ./install.sh --sink <name>" >&2
  exit 1
fi

echo "Hardware target: $TARGET"

if [[ $CA0132_CHANNEL_FIX -eq 1 ]]; then
  if [[ "$TARGET" != *"analog-surround-51"* ]]; then
    echo "ERROR: --ca0132-channel-fix requires an analog-surround-51 target; detected: $TARGET" >&2
    exit 1
  fi
  if ! pactl list cards 2>/dev/null | grep -Eqi 'CA0132|Sound Blaster|Sound Core3D|Recon3D'; then
    echo "ERROR: --ca0132-channel-fix requested, but no CA0132/Sound Blaster card was detected." >&2
    exit 1
  fi
  mkdir -p "$(dirname "$CA0132_WP_CONF")"
  backup_if_exists "$CA0132_WP_CONF"
  cat > "$CA0132_WP_CONF" <<'EOF'
monitor.alsa.rules = [
  {
    matches = [
      {
        alsa.id = "Creative"
        api.alsa.path = "surround51:0"
        device.profile.name = "analog-surround-51"
      }
    ]
    actions = {
      update-props = {
        audio.position = [ "FL", "FR", "FC", "LFE", "RL", "RR" ]
      }
    }
  }
]
EOF
  echo "Installed opt-in CA0132 analog 5.1 WirePlumber channel-map correction."
  systemctl --user restart wireplumber
  for _ in {1..20}; do
    pactl list short sinks 2>/dev/null | grep -qF "$TARGET" && break
    sleep 0.25
  done
fi

cp "$APP_SRC" "$LIB_DIR/control.py"
cp "$HERE/app/relaunch_helper.py" "$LIB_DIR/relaunch_helper.py"
cp "$HERE/app/audio_return_helper.py" "$LIB_DIR/audio_return_helper.py"
# Keep a self-contained setup payload for in-app connection/layout changes.
# Stage it first so rerunning the installed helper never deletes its own source
# before the replacement copy is complete.
SETUP_STAGE="$(mktemp -d)"
trap 'rm -rf "$SETUP_STAGE"' EXIT
cp "$HERE/install.sh" "$SETUP_STAGE/install.sh"
cp -a "$HERE/app" "$SETUP_STAGE/app"
if [[ -d "$HERE/assets" ]]; then cp -a "$HERE/assets" "$SETUP_STAGE/assets"; fi
rm -rf "$LIB_DIR/setup"
mkdir -p "$LIB_DIR/setup"
cp -a "$SETUP_STAGE/." "$LIB_DIR/setup/"
chmod +x "$LIB_DIR/setup/install.sh"
rm -rf "$LIB_DIR/assets"
if [[ -d "$ASSET_SRC" ]]; then cp -a "$ASSET_SRC" "$LIB_DIR/assets"; fi
chmod +x "$LIB_DIR/control.py" "$LIB_DIR/relaunch_helper.py" "$LIB_DIR/audio_return_helper.py"

cat > "$BIN_DIR/soundblaster-zse-control" <<EOF
#!/usr/bin/env bash
exec /usr/bin/python3 "$LIB_DIR/control.py" "\$@"
EOF
chmod +x "$BIN_DIR/soundblaster-zse-control"

# Generate/upgrade the smart 10-band filter while preserving existing gains.
# WirePlumber transparently inserts this filter whenever an application targets
# the selected physical Sound Blaster sink.
python3 - "$EQ_CONF" "$TARGET" "$LEGACY_EQ_CONF" "$is_bazzite" <<'PY'
from pathlib import Path
import json, re, subprocess, sys
path = Path(sys.argv[1]); target = sys.argv[2]; legacy = Path(sys.argv[3]); compatibility = sys.argv[4] == "1"
bands = [31,62,125,250,500,1000,2000,4000,8000,16000]
old = path.read_text() if path.exists() else (legacy.read_text() if legacy.exists() else "")
gains = {}
for f in bands:
    m = re.search(rf'name\s*=\s*eq_{f}\b.*?"Gain"\s*=\s*(-?\d+(?:\.\d+)?)', old, re.S)
    if not m:
        m = re.search(rf'freq\s*=\s*{f}\s+gain\s*=\s*(-?\d+(?:\.\d+)?)', old)
    gains[f] = float(m.group(1)) if m else 0.0

positions = ["FL","FR","RL","RR","FC","LFE"]
try:
    out = subprocess.check_output(["pw-dump"], text=True)
    allowed = {"FL","FR","FC","LFE","RL","RR","SL","SR"}
    canonical_51 = ["FL","FR","RL","RR","FC","LFE"]
    candidates = []
    for obj in json.loads(out):
        props = obj.get("info", {}).get("props", {})
        if props.get("node.name") != target:
            continue
        raw = props.get("audio.position", "")
        if isinstance(raw, list):
            vals = [str(v).strip().strip('\"\'') for v in raw]
        else:
            vals = re.findall(r"\b(?:FL|FR|FC|LFE|RL|RR|SL|SR)\b", str(raw or ""))
        vals = [v for v in vals if v in allowed]
        try:
            channels = int(str(props.get("audio.channels", "0")).strip('\"'))
        except Exception:
            channels = 0
        score = (
            1 if str(props.get("media.class", "")) == "Audio/Sink" else 0,
            max(channels, len(vals)),
            len(vals),
        )
        candidates.append((score, channels, vals))

    if candidates:
        _, channels, vals = max(candidates, key=lambda item: item[0])
        if channels == 6 or (len(vals) == 6 and set(vals) == set(canonical_51)):
            positions = canonical_51
        elif 2 <= len(vals) <= 8:
            positions = vals

    # Never let a transient/stale stereo pw-dump object downgrade an actual
    # 5.1 surround profile.  The EQ sink uses canonical semantic positions;
    # PipeWire maps those labels onto the physical sink's hardware ordering.
    if ("analog-surround-51" in target.lower() or "surround-51" in target.lower()):
        positions = canonical_51
except Exception:
    if "analog-surround-51" in target.lower() or "surround-51" in target.lower():
        positions = ["FL","FR","RL","RR","FC","LFE"]

nodes=[
    '          {\n            type = builtin\n            name = preamp\n            label = linear\n            control = { "Mult" = 1.00000000 "Add" = 0.0 }\n          }'
]; links=[]
for i,f in enumerate(bands):
    nodes.append('          {\n            type = builtin\n            name = eq_%d\n            label = bq_peaking\n            control = { "Freq" = %.1f "Q" = 1.4 "Gain" = %.1f }\n          }' % (f,float(f),gains[f]))
    if i:
        links.append('          { output = "eq_%d:Out" input = "eq_%d:In" }' % (bands[i-1],f))
    else:
        links.append('          { output = "preamp:Out" input = "eq_%d:In" }' % f)
pos=' '.join(positions); channels=len(positions)
text = '''context.modules = [
  {
    name = libpipewire-module-filter-chain
    args = {
      node.description = "Sound Blaster Linux EQ"
      media.name = "Sound Blaster Linux Control Center 5.1 EQ"

      filter.graph = {
        nodes = [
%s
        ]

        links = [
%s
        ]
        # inputs/outputs intentionally omitted so PipeWire duplicates this
        # one-channel graph to match the stream's 2/6-channel layout.
      }

      capture.props = {
        node.name = "soundblaster_zse_eq"
        node.description = "Sound Blaster Linux EQ"
        media.class = "Audio/Sink"
%s
        audio.channels = %d
        audio.position = [ %s ]
      }

      playback.props = {
        node.name = "soundblaster_zse_eq_output"
        node.description = "Sound Blaster Linux EQ Output"
%s        node.passive = true
        stream.dont-remix = true
        audio.channels = %d
        audio.position = [ %s ]
      }
    }
  }
]
''' % ('\n'.join(nodes), '\n'.join(links), ('' if compatibility else '        filter.smart = true\n        filter.smart.name = \"soundblaster-zse-control-eq\"\n        filter.smart.targetable = false\n        filter.smart.target = { node.name = \"%s\" }' % target), channels, pos, ('        target.object = \"%s\"\n' % target if compatibility else ''), channels, pos)
path.write_text(text)
print("Smart-filter channel map:", pos)
PY

# Persist the requested logical Speaker Setup before the application regenerates
# the EQ graph.  Digital 2.1/4.x/5.0 still rides the physical AC3 5.1 carrier,
# while the virtual EQ exposes only the requested logical channels.
python3 - "$STATE_DIR/state.json" "$CONNECTION" "$SPEAKER_LAYOUT" <<'PYSEL'
from pathlib import Path
import json, sys
p=Path(sys.argv[1])
try: data=json.loads(p.read_text()) if p.exists() else {}
except Exception: data={}
if not isinstance(data,dict): data={}
cur=data.setdefault('current',{})
cur['output_connection']=sys.argv[2]
cur['speaker_layout']=sys.argv[3]
p.parent.mkdir(parents=True,exist_ok=True)
t=p.with_suffix('.tmp'); t.write_text(json.dumps(data,indent=2)); t.replace(p)
PYSEL

# The application owns the authoritative distro-isolated graph generator.
# On Ubuntu 5.1 this replaces the compatibility graph above with the explicit
# cross-channel Bass Management graph; Bazzite output remains on its verified
# duplicated mono EQ topology.
if [[ "$is_bazzite" != "1" ]]; then
  /usr/bin/python3 "$LIB_DIR/control.py" --generate-eq-config "$TARGET" "$EQ_CONF"
fi

# Global mixer is used on normal targets. Bazzite and Arch/CachyOS A52
# use the persistent stereo-only pw-loopback sink created by the application,
# avoiding a pipewire-pulse restart that would tear down the AC3 hardware sink.
python3 - "$STATE_DIR/state.json" "$FILL_CONF" "$is_bazzite" "$TARGET" <<'PY'
from pathlib import Path
import json, sys
state_path=Path(sys.argv[1]); fill_path=Path(sys.argv[2])
target=sys.argv[4] if len(sys.argv) > 4 else ''
compatibility=(sys.argv[3] == '1' or target == 'alsa_output.soundblaster_a52_51')
try: data=json.loads(state_path.read_text())
except Exception: data={}
cur=data.get('current',{}) if isinstance(data,dict) else {}
mode=str(cur.get('fill_mode','PSD')).upper()
method='simple' if mode == 'FULL' else 'psd'
upmix='false' if compatibility or mode == 'OFF' else 'true'
rear=float(cur.get('rear_delay',12.0)); width=float(cur.get('stereo_width',0.0)); cutoff=int(cur.get('lfe_cutoff',150))
text=(
    'stream.properties = {\n'
    + ('  # Stable route: stereo fill uses the dedicated soundblaster_zse_fill sink.\n' if compatibility else
       '  # Global PipeWire-Pulse Speaker Fill behavior.\n')
    + f'  channelmix.upmix = {upmix}\n'
    f'  channelmix.upmix-method = "{method}"\n'
    f'  channelmix.rear-delay = {rear:.1f}\n'
    f'  channelmix.stereo-widen = {width:.2f}\n'
    f'  channelmix.lfe-cutoff = {cutoff}\n'
    '}\n'
)
fill_path.parent.mkdir(parents=True,exist_ok=True)
tmp=fill_path.with_suffix(fill_path.suffix+'.tmp'); tmp.write_text(text); tmp.replace(fill_path)
PY

# Ensure the packaged state knows the selected hardware sink while preserving old settings.
python3 - "$STATE_DIR/state.json" "$TARGET" "$CONNECTION" "$SPEAKER_LAYOUT" <<'PY'
from pathlib import Path
import json, math, sys
p=Path(sys.argv[1]); target=sys.argv[2]
try: data=json.loads(p.read_text()) if p.exists() else {}
except Exception: data={}
if not isinstance(data,dict): data={}
cur=data.setdefault('current',{})
old_version=str(data.get('version',''))
cur['hardware_sink']=target
if old_version == '2.2.0': cur['preamp']=0.0
else: cur.setdefault('preamp',0.0)
# v3.3.25 replaces -12..+12 dB speaker trims with OS-style 0..100%.
# Preserve legacy attenuation; positive legacy boosts clamp to 100%.
try: parts=tuple(int(x) for x in old_version.split('.')[:3]) if old_version else (999,999,999)
except Exception: parts=(999,999,999)
if parts <= (3,3,24):
    for key in ('fl','fr','fc','lfe','rl','rr'):
        if key in cur:
            cur[key]=max(0.0,min(100.0,math.pow(10.0,float(cur[key])/60.0)*100.0))
cur.setdefault('safe_headroom',True); cur.setdefault('auto_reconnect',True)
cur['output_connection']=sys.argv[3] if len(sys.argv)>3 else cur.get('output_connection','auto')
cur['speaker_layout']=sys.argv[4] if len(sys.argv)>4 else cur.get('speaker_layout','auto')
cur.setdefault('fill_engine','application')
data['version']='3.3.7'
tmp=p.with_name(p.name+'.install-tmp')
tmp.write_text(json.dumps(data,indent=2))
json.loads(tmp.read_text())
tmp.replace(p)
PY

mkdir -p "$SYSTEMD_USER_DIR"
cat > "$SYSTEMD_USER_DIR/soundblaster-zse-relaunch-helper.service" <<EOF
[Unit]
Description=Sound Blaster Linux Control Center relaunch helper
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $LIB_DIR/relaunch_helper.py
Restart=on-failure
RestartSec=1

[Install]
WantedBy=default.target
EOF

# Separate background observer: no GUI and no takeover of other audio devices.
cat > "$SYSTEMD_USER_DIR/soundblaster-zse-audio-return.service" <<EOF
[Unit]
Description=Sound Blaster audio return observer (PipeWire/WirePlumber)
After=pipewire-pulse.service wireplumber.service
Wants=pipewire-pulse.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 $LIB_DIR/audio_return_helper.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload >/dev/null 2>&1 || true
systemctl --user enable --now soundblaster-zse-audio-return.service >/dev/null 2>&1 || true
systemctl --user restart soundblaster-zse-audio-return.service >/dev/null 2>&1 || true
systemctl --user enable --now soundblaster-zse-relaunch-helper.service >/dev/null 2>&1 || true
# Always restart on upgrade so the running daemon uses the just-installed helper.
systemctl --user restart soundblaster-zse-relaunch-helper.service >/dev/null 2>&1 || true

cat > "$APP_DIR/soundblaster-zse-control.desktop" <<EOF
[Desktop Entry]
Name=Sound Blaster Linux Control Center
Comment=adaptive 2.0-5.1 PipeWire equalizer and routing control
Exec=$BIN_DIR/soundblaster-zse-control
Icon=audio-card
Terminal=false
Type=Application
Categories=AudioVideo;Audio;
StartupWMClass=SoundBlasterLinuxControl
StartupNotify=false
EOF

cat > "$AUTOSTART_DIR/soundblaster-zse-restore.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Sound Blaster Linux Control Restore
Exec=$BIN_DIR/soundblaster-zse-control --restore
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

# Retire legacy Z-5500-named integration files after backing them up.
# Leaving the old PipeWire config active would create a second virtual EQ sink.
rm -f "$APP_DIR/z5500-eq.desktop" "$AUTOSTART_DIR/z5500-eq-restore.desktop"
if [[ -f "$LEGACY_EQ_CONF" && "$LEGACY_EQ_CONF" != "$EQ_CONF" ]]; then
  rm -f "$LEGACY_EQ_CONF"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

if [[ $RESTART -eq 1 ]]; then
  echo "Starting/reloading the Sound Blaster EQ path…"
  systemctl --user daemon-reload >/dev/null 2>&1 || true

  if systemctl --user cat filter-chain.service >/dev/null 2>&1; then
    # Fedora, Arch/CachyOS and Bazzite can provide this user unit. Prefer it
    # over restarting the entire desktop PipeWire stack. Enable when possible
    # so the EQ client is present on the next login too.
    systemctl --user enable filter-chain.service >/dev/null 2>&1 || true
    if ! systemctl --user restart filter-chain.service; then
      systemctl --user reset-failed filter-chain.service >/dev/null 2>&1 || true
      if ! systemctl --user restart filter-chain.service; then
        echo "ERROR: filter-chain.service could not be started." >&2
        systemctl --user status filter-chain.service --no-pager >&2 || true
        exit 1
      fi
    fi
    # The unit is known to be loaded at this point; clear any stale failed state.
    systemctl --user reset-failed filter-chain.service >/dev/null 2>&1 || true
    if ! systemctl --user is-active --quiet filter-chain.service; then
      echo "ERROR: filter-chain.service is not active after restart." >&2
      systemctl --user status filter-chain.service --no-pager >&2 || true
      exit 1
    fi
  else
    echo "No filter-chain.service user unit found; restarting the user PipeWire stack once…"
    systemctl --user restart pipewire pipewire-pulse wireplumber
  fi

  for _ in {1..40}; do
    pactl list short sinks 2>/dev/null | grep -qF "$TARGET" && pactl list short sinks 2>/dev/null | grep -q $'\tsoundblaster_zse_eq\t' && break
    sleep 0.5
  done
  if ! pactl list short sinks 2>/dev/null | grep -qF "$TARGET"; then
    echo "ERROR: Hardware target did not return after audio reload: $TARGET" >&2; exit 1
  fi
  if ! pactl list short sinks 2>/dev/null | grep -q $'\tsoundblaster_zse_eq\t'; then
    echo "ERROR: Sound Blaster EQ node did not load after audio reload." >&2
    echo "Check: systemctl --user status filter-chain.service --no-pager" >&2
    echo "       journalctl --user -u filter-chain.service -b --no-pager | tail -80" >&2
    exit 1
  fi
  # Keep the user's verified physical fallback as default on smart-filter
  # installs; Bazzite compatibility mode routes directly through the EQ sink.
  if [[ "$is_bazzite" -eq 1 ]]; then pactl set-default-sink soundblaster_zse_eq || true; else pactl set-default-sink "$TARGET" || true; fi
fi

echo
echo "Installed Sound Blaster Linux Control Center $APP_VERSION"
echo "Launcher: $APP_DIR/soundblaster-zse-control.desktop"
echo "Command:  $BIN_DIR/soundblaster-zse-control"
echo "Restore:  $AUTOSTART_DIR/soundblaster-zse-restore.desktop"
echo "Target:   $TARGET"
echo
echo "Existing EQ gains were preserved. Existing files were backed up before replacement."
if [[ -f "$OLD_SCRIPT" ]]; then
  echo "The old $OLD_SCRIPT was left untouched for rollback."
fi
