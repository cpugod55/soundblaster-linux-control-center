#!/usr/bin/env bash
set -euo pipefail

VERSION="3.3.36"
APP_ID="soundblaster-zse-control"
HERE="$(cd "$(dirname "$0")" && pwd)"
APP_SRC="$HERE/app/soundblaster_zse_control.py"
ASSET_SRC="$HERE/assets"
LIB_DIR="$HOME/.local/lib/$APP_ID"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"
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
Sound Blaster Linux Control Center $VERSION installer

Usage: ./install.sh [--sink PIPEWIRE_SINK] [--no-restart]

  --sink NAME      Physical 5.1 PipeWire/Pulse sink to receive Sound Blaster EQ output.
                   If omitted, the installer preserves an existing target or
                   tries to detect a 5.1 surround/AC3 sink.
  --no-restart     Install files without restarting the user PipeWire services.
  --no-optical-setup  Do not attempt to install Ubuntu A52/AC3 support when missing.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sink) TARGET="${2:-}"; shift 2 ;;
    --no-restart) RESTART=0; shift ;;
    --no-optical-setup) SETUP_OPTICAL=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

# Distribution-aware dependency setup. The application itself remains user-local;
# only missing host audio/runtime packages are installed.
OS_ID="unknown"
OS_LIKE=""
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  OS_ID="${ID:-unknown}"
  OS_LIKE="${ID_LIKE:-}"
fi

is_bazzite=0
if [[ "$OS_ID" == "bazzite" ]] || grep -qi 'bazzite' /etc/os-release 2>/dev/null; then
  is_bazzite=1
fi

echo "Detected Linux distribution: $OS_ID${OS_LIKE:+ (like $OS_LIKE)}"

have_tk() { python3 -c 'import tkinter' >/dev/null 2>&1; }
have_a52_runtime() { command -v aplay >/dev/null 2>&1 && aplay -L 2>/dev/null | grep -q '^a52'; }
have_a52_package() { command -v rpm >/dev/null 2>&1 && rpm -q alsa-plugins-a52 >/dev/null 2>&1; }
have_a52() {
  # On Fedora Atomic/Bazzite, package presence is authoritative for dependency
  # installation. `aplay -L` can omit the a52 PCM even when the host RPM is
  # correctly layered, depending on ALSA configuration/device enumeration.
  if [[ $is_bazzite -eq 1 ]]; then
    have_a52_package || have_a52_runtime
  else
    have_a52_runtime
  fi
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
  [[ -f /usr/lib/ladspa/ZaMaximX2-ladspa.so ]] || need+=(zam-plugins)
  if [[ $SETUP_OPTICAL -eq 1 ]] && ! have_a52; then need+=(libasound2-plugins); fi
  if (( ${#need[@]} )); then
    echo "Installing Debian/Ubuntu dependencies: ${need[*]}"
    sudo apt-get update
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
  # Arch ships pcm_a52 in alsa-plugins; ffmpeg supplies the codec dependency.
  if [[ $SETUP_OPTICAL -eq 1 ]] && ! have_a52; then need+=(alsa-plugins ffmpeg); fi
  if (( ${#need[@]} )); then
    echo "Installing Arch/Manjaro dependencies: ${need[*]}"
    sudo pacman -S --needed --noconfirm "${need[@]}"
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
  if [[ $SETUP_OPTICAL -eq 1 ]] && ! have_a52; then missing+=(alsa-plugins-a52); fi
  if (( ${#missing[@]} )); then
    echo ""
    echo "Bazzite/Fedora Atomic detected. The installer will NOT automatically layer host packages."
    echo "Missing host components: ${missing[*]}"
    echo "These components require host integration on Atomic systems. Install all missing host dependencies in one transaction:"
    echo "  sudo rpm-ostree install ${missing[*]}"
    echo "Then reboot once and run this installer again."
    echo "The application itself and its settings remain user-local under ~/.local and ~/.config."
    echo "This avoids silently changing an Atomic deployment."
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
else
  echo "Unknown/unsupported package manager. No system packages will be changed."
  echo "The app can still install if Python 3 + Tk, PipeWire, WirePlumber, pactl and ALSA utilities are already present."
fi

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
  esac
  exit 1
fi

if ! command -v parec >/dev/null 2>&1; then
  echo "NOTE: parec was not found. Audio processing will work, but spectrum/channel meters may be unavailable."
fi

mkdir -p "$LIB_DIR" "$BIN_DIR" "$APP_DIR" "$AUTOSTART_DIR" "$STATE_DIR" "$(dirname "$EQ_CONF")" "$(dirname "$FILL_CONF")"

backup_if_exists() {
  local f="$1"
  if [[ -e "$f" ]]; then
    cp -a "$f" "$f.backup-$STAMP"
    echo "Backup: $f.backup-$STAMP"
  fi
}

backup_if_exists "$EQ_CONF"
backup_if_exists "$FILL_CONF"
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

# Preserve an existing filter target if possible.
if [[ -z "$TARGET" && -f "$EQ_CONF" ]]; then
  TARGET="$(sed -n 's/.*filter\.smart\.target[[:space:]]*=[[:space:]]*{[^}]*node\.name[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$EQ_CONF" | head -n1 || true)"
  if [[ -z "$TARGET" ]]; then
    TARGET="$(sed -n 's/.*target\.object[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$EQ_CONF" | head -n1 || true)"
  fi
elif [[ -z "$TARGET" && -f "$LEGACY_EQ_CONF" ]]; then
  TARGET="$(sed -n 's/.*target\.object[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$LEGACY_EQ_CONF" | head -n1 || true)"
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

cp "$APP_SRC" "$LIB_DIR/control.py"
rm -rf "$LIB_DIR/assets"
if [[ -d "$ASSET_SRC" ]]; then cp -a "$ASSET_SRC" "$LIB_DIR/assets"; fi
chmod +x "$LIB_DIR/control.py"

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
    for obj in json.loads(out):
        props = obj.get("info", {}).get("props", {})
        if props.get("node.name") == target:
            raw = props.get("audio.position", "")
            vals = [str(v) for v in raw] if isinstance(raw, list) else str(raw).strip().strip("[]").replace(",", " ").split()
            allowed = {"FL","FR","FC","LFE","RL","RR","SL","SR"}
            vals = [v.strip() for v in vals if v.strip() in allowed]
            if 2 <= len(vals) <= 6:
                positions = vals
            break
except Exception:
    pass

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

# The application owns the authoritative distro-isolated graph generator.
# On Ubuntu 5.1 this replaces the compatibility graph above with the explicit
# cross-channel Bass Management graph; Bazzite output remains on its verified
# duplicated mono EQ topology.
if [[ "$is_bazzite" != "1" ]]; then
  /usr/bin/python3 "$LIB_DIR/control.py" --generate-eq-config "$TARGET" "$EQ_CONF"
fi

# Ubuntu restores the v3.3.2 global mixer. Bazzite keeps the v3.3.15
# persistent stereo-only pw-loopback sink created by the application.
python3 - "$STATE_DIR/state.json" "$FILL_CONF" "$is_bazzite" <<'PY'
from pathlib import Path
import json, sys
state_path=Path(sys.argv[1]); fill_path=Path(sys.argv[2]); compatibility=sys.argv[3] == '1'
try: data=json.loads(state_path.read_text())
except Exception: data={}
cur=data.get('current',{}) if isinstance(data,dict) else {}
mode=str(cur.get('fill_mode','PSD')).upper()
method='simple' if mode == 'FULL' else 'psd'
upmix='false' if compatibility or mode == 'OFF' else 'true'
rear=float(cur.get('rear_delay',12.0)); width=float(cur.get('stereo_width',0.0)); cutoff=int(cur.get('lfe_cutoff',150))
text=(
    'stream.properties = {\n'
    + ('  # Bazzite: stereo fill uses the dedicated soundblaster_zse_fill sink.\n' if compatibility else
       '  # Ubuntu: v3.3.2 global PipeWire-Pulse Speaker Fill behavior.\n')
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
python3 - "$STATE_DIR/state.json" "$TARGET" <<'PY'
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
data['version']='3.3.36'
tmp=p.with_name(p.name+'.install-tmp')
tmp.write_text(json.dumps(data,indent=2))
json.loads(tmp.read_text())
tmp.replace(p)
PY

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
StartupNotify=true
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
  if [[ "$is_bazzite" -eq 1 ]]; then
    echo "Starting the Sound Blaster EQ service…"
    # Fedora 44 ships this unit with PipeWire. It runs pipewire using
    # filter-chain.conf and therefore consumes ~/.config/pipewire/filter-chain.conf.d/.
    if ! systemctl --user cat filter-chain.service >/dev/null 2>&1; then
      echo "ERROR: PipeWire filter-chain.service is unavailable on this Bazzite deployment." >&2
      exit 1
    fi
    systemctl --user enable --now filter-chain.service >/dev/null
    systemctl --user restart filter-chain.service
  else
    echo "Restarting the user PipeWire stack once…"
    systemctl --user restart pipewire pipewire-pulse wireplumber
  fi
  for _ in {1..40}; do
    pactl list short sinks 2>/dev/null | grep -qF "$TARGET" && pactl list short sinks 2>/dev/null | grep -q $'\tsoundblaster_zse_eq\t' && break
    sleep 0.5
  done
  if ! pactl list short sinks 2>/dev/null | grep -qF "$TARGET"; then
    echo "ERROR: Hardware target did not return after PipeWire restart: $TARGET" >&2; exit 1
  fi
  if ! pactl list short sinks 2>/dev/null | grep -q $'\tsoundblaster_zse_eq\t'; then
    echo "ERROR: Sound Blaster EQ node did not load after PipeWire restart." >&2
    echo "Check: journalctl --user -u pipewire -b --no-pager | tail -80" >&2; exit 1
  fi
  if [[ "$is_bazzite" -eq 1 ]]; then pactl set-default-sink soundblaster_zse_eq || true; else pactl set-default-sink "$TARGET" || true; fi
fi

echo
echo "Installed Sound Blaster Linux Control Center $VERSION"
echo "Launcher: $APP_DIR/soundblaster-zse-control.desktop"
echo "Command:  $BIN_DIR/soundblaster-zse-control"
echo "Restore:  $AUTOSTART_DIR/soundblaster-zse-restore.desktop"
echo "Target:   $TARGET"
echo
echo "Existing EQ gains were preserved. Existing files were backed up before replacement."
if [[ -f "$OLD_SCRIPT" ]]; then
  echo "The old $OLD_SCRIPT was left untouched for rollback."
fi
