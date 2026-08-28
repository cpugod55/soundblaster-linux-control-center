#!/usr/bin/env python3
import fcntl
import json
import math
import cmath
import array
import os
import re
import shutil
import socket
import subprocess
import signal
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

APP_NAME = "Sound Blaster Linux Control Center"
APP_ID = "soundblaster-zse-control"
VERSION = "3.3.35"
SINK = "soundblaster_zse_eq"
OUTPUT_NODE = "soundblaster_zse_eq_output"
FILL_SINK = "soundblaster_zse_fill"
FILL_OUTPUT_NODE = "soundblaster_zse_fill_output"
FILL_LOOP_NAME = "soundblaster_zse_fill_loop"
BANDS = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]

CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
STATE_DIR = CONFIG_HOME / APP_ID
STATE_FILE = STATE_DIR / "state.json"
RESTORE_LOG = STATE_DIR / "restore.log"
EQ_CONFIG = CONFIG_HOME / "pipewire/filter-chain.conf.d/soundblaster-zse-eq.conf"
FILL_CONFIG = CONFIG_HOME / "pipewire/pipewire-pulse.conf.d/10-speaker-fill.conf"
MIC_CONFIG = CONFIG_HOME / "pipewire/filter-chain.conf.d/soundblaster-mic-processing.conf"
MIC_SOURCE = "soundblaster_processed_mic"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/{os.getuid()}"))
SOCKET_PATH = RUNTIME_DIR / f"{APP_ID}.sock"
LOCK_PATH = RUNTIME_DIR / f"{APP_ID}.lock"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
SIGNATURE_IMAGE = ASSET_DIR / "zeus_signature.png"

CHANNEL_KEYS = ["fl", "fr", "fc", "lfe", "rl", "rr"]
CHANNEL_LABELS = {
    "fl": "Front Left", "fr": "Front Right", "fc": "Center",
    "lfe": "Sub / LFE", "rl": "Rear Left", "rr": "Rear Right",
}

DEFAULT_CURRENT = {
    "preamp": 0.0,
    "eq": {str(f): 0.0 for f in BANDS},
    "fl": 100.0, "fr": 100.0, "fc": 100.0, "lfe": 100.0, "rl": 100.0, "rr": 100.0,
    "fill_mode": "PSD",
    "rear_delay": 12.0,
    "stereo_width": 0.0,
    "lfe_cutoff": 150,
    "bass_management": False,
    "bass_crossover": 80,
    "lfe_lowpass": 120,
    "speaker_highpass": 80,
    "lfe_trim": 0.0,
    "bass_slope": "24",
    "bass_routing": "REDIRECT",
    "safe_headroom": True,
    "auto_reconnect": False,
    "hardware_sink": "",
    "last_preset": "Current",
    "input_level": 100.0,
    "mic_boost_db": 0.0,
    "mic_processing": False,
    "mic_noise_reduction": True,
    "mic_noise_strength": 50.0,
    "mic_eq_low": 0.0,
    "mic_eq_mid": 0.0,
    "mic_eq_high": 0.0,
    "mic_source": "",
}

BUILTIN_PRESETS = {
    # Presets are intentionally sound-shaping only. Speaker/channel trims are
    # room calibration and stay persistent when presets are changed.
    "Flat": {
        "eq": {str(f): 0.0 for f in BANDS},
    },
    "Gaming": {
        "eq": {"31": 1, "62": 1, "125": 0, "250": -2, "500": -1, "1000": 0,
               "2000": 2, "4000": 3, "8000": 2, "16000": 1},
    },
    "Music": {
        "eq": {"31": 2, "62": 2, "125": 1, "250": 0, "500": 0, "1000": 0,
               "2000": 0, "4000": 1, "8000": 2, "16000": 2},
    },
    "Movies": {
        "eq": {"31": 2, "62": 2, "125": 1, "250": 0, "500": -1, "1000": 0,
               "2000": 1, "4000": 2, "8000": 1, "16000": 0},
    },
    "Night": {
        "eq": {"31": -3, "62": -2, "125": -1, "250": 0, "500": 1, "1000": 1,
               "2000": 2, "4000": 2, "8000": 1, "16000": 0},
    },
}

DEFAULT_DATA = {
    "version": VERSION,
    "current": DEFAULT_CURRENT.copy(),
    "custom_presets": {
        str(i): {"name": f"Custom {i}", "settings": None} for i in range(1, 6)
    },
}


def run(cmd, check=False, capture=False):
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def deep_default():
    return json.loads(json.dumps(DEFAULT_DATA))


def legacy_channel_db_to_percent(db):
    """Convert the <=3.3.24 channel dB trim to PulseAudio's displayed percent."""
    return max(0.0, min(100.0, math.pow(10.0, float(db) / 60.0) * 100.0))


def load_data():
    data = deep_default()
    try:
        saved = json.loads(STATE_FILE.read_text())
        if not isinstance(saved, dict):
            return data
        old_current = saved.get("current", saved)
        if isinstance(old_current, dict):
            # Migration from the earlier center/rear/lfe model.
            migrated = dict(old_current)
            # 2.2.0 implemented Master Preamp by attenuating/boosting the
            # virtual sink. That gain model was defective on the AC3 smart
            # filter path; start migrated 2.2.0 installs at true unity.
            if str(saved.get("version", "")) == "2.2.0":
                migrated["preamp"] = 0.0
            if "center" in old_current and "fc" not in migrated:
                migrated["fc"] = old_current.get("center", 0.0)
            if "rear" in old_current:
                migrated.setdefault("rl", old_current.get("rear", 0.0))
                migrated.setdefault("rr", old_current.get("rear", 0.0))
            if "lfe" in old_current:
                migrated.setdefault("lfe", old_current.get("lfe", 0.0))
            # v3.3.25 changes speaker calibration from -12..+12 dB trims to
            # OS-style 0..100% per-channel volumes. Preserve the effective
            # attenuation of existing installs; legacy boosts clamp to 100%.
            saved_version = str(saved.get("version", ""))
            if saved_version and saved_version != VERSION:
                try:
                    parts = tuple(int(x) for x in saved_version.split(".")[:3])
                except Exception:
                    parts = (999, 999, 999)
                if parts <= (3, 3, 24):
                    for channel_key in ("fl", "fr", "fc", "lfe", "rl", "rr"):
                        if channel_key in migrated:
                            migrated[channel_key] = legacy_channel_db_to_percent(migrated[channel_key])
            for k in DEFAULT_CURRENT:
                if k in migrated:
                    data["current"][k] = migrated[k]
        if isinstance(saved.get("custom_presets"), dict):
            for slot, entry in saved["custom_presets"].items():
                if slot in data["custom_presets"] and isinstance(entry, dict):
                    data["custom_presets"][slot].update(entry)
    except Exception:
        pass
    return data


def save_data(data):
    """Atomically persist state while retaining the previous valid file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    data["version"] = VERSION
    payload = json.dumps(data, indent=2)
    tmp = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
    backup = STATE_FILE.with_name(STATE_FILE.name + ".backup-last")
    tmp.write_text(payload)
    # Validate the complete temporary file before it can replace live state.
    json.loads(tmp.read_text())
    if STATE_FILE.exists():
        shutil.copy2(STATE_FILE, backup)
    tmp.replace(STATE_FILE)


def db_to_percent(db):
    return math.pow(10.0, db / 20.0) * 100.0


def list_sinks():
    result = run(["pactl", "list", "short", "sinks"], capture=True)
    sinks = []
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                sinks.append(parts[1])
    return sinks


def sink_exists(name=SINK):
    return name in list_sinks()


def wait_for_sink(name=SINK, timeout=12):
    end = time.time() + timeout
    while time.time() < end:
        if sink_exists(name):
            return True
        time.sleep(0.4)
    return False


def default_sink_name():
    result = run(["pactl", "get-default-sink"], capture=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def set_default_sink(name=SINK):
    if sink_exists(name):
        run(["pactl", "set-default-sink", name])


def move_playback_streams(name):
    """Move existing Pulse/PipeWire playback streams to a sink.

    Changing the default sink only affects newly-created streams.  Moving
    current sink-inputs keeps already-running games/media on the same route
    when the EQ is activated.
    """
    if not sink_exists(name):
        return 0
    result = run(["pactl", "list", "short", "sink-inputs"], capture=True)
    if result.returncode != 0:
        return 0
    moved = 0
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        try:
            idx = int(parts[0])
        except Exception:
            continue
        r = run(["pactl", "move-sink-input", str(idx), name], capture=True)
        if r.returncode == 0:
            moved += 1
    return moved


def activate_eq_route(move_existing=True):
    """Make the virtual EQ the authoritative playback route when available."""
    if not sink_exists(SINK):
        return False
    set_default_sink(SINK)
    if move_existing:
        move_playback_streams(SINK)
    return default_sink_name() == SINK


def activate_hardware_fallback():
    """Use the saved physical sink only when the EQ route is unavailable."""
    target = DATA.get("current", {}).get("hardware_sink", "") if "DATA" in globals() else ""
    if target and sink_exists(target):
        set_default_sink(target)
        return default_sink_name() == target
    return False


def get_sink_mute(name=SINK):
    if not sink_exists(name):
        return False
    result = run(["pactl", "get-sink-mute", name], capture=True)
    return result.returncode == 0 and "yes" in result.stdout.lower()


def set_sink_mute(value, name=SINK):
    if sink_exists(name):
        run(["pactl", "set-sink-mute", name, "1" if value else "0"])


def detect_hardware_sink():
    sinks = list_sinks()
    # Prefer non-EQ 5.1 digital sinks; otherwise current default; otherwise first non-EQ sink.
    preferred = [s for s in sinks if s not in (SINK, FILL_SINK) and ("surround-51" in s or "ac3" in s.lower())]
    if preferred:
        return preferred[0]
    d = default_sink_name()
    if d and d not in (SINK, FILL_SINK):
        return d
    for s in sinks:
        if s != SINK:
            return s
    return ""


def normalize_channel_positions(value):
    """Return a PipeWire channel map like ["FL", "FR", ...] from pw-dump data."""
    if isinstance(value, list):
        vals = [str(v).strip() for v in value]
    else:
        text = str(value or "").strip().strip("[]")
        vals = [v.strip().strip(',') for v in text.replace(',', ' ').split()]
    allowed = {"FL", "FR", "FC", "LFE", "RL", "RR", "SL", "SR"}
    vals = [v for v in vals if v in allowed]
    return vals


def sink_channel_positions(name):
    result=run(["pw-dump"],capture=True)
    if result.returncode==0:
        try:
            for obj in json.loads(result.stdout):
                props=obj.get("info",{}).get("props",{})
                if props.get("node.name")==name:
                    vals=normalize_channel_positions(props.get("audio.position"))
                    if 2 <= len(vals) <= 6: return vals
        except Exception: pass
    return ["FL","FR"]

def channel_key_for_position(pos):
    return {"FL":"fl","FR":"fr","FC":"fc","LFE":"lfe","RL":"rl","RR":"rr","SL":"rl","SR":"rr"}.get(pos)

def layout_name(pos):
    n=len(pos); lfe="LFE" in pos
    return "2.0" if n==2 else "2.1" if n==3 and lfe else "4.0" if n==4 else "4.1" if n==5 and lfe else "5.1" if n==6 else f"{n}-channel"

def is_bazzite():
    try:
        text = Path("/etc/os-release").read_text().lower()
        return "bazzite" in text
    except Exception:
        return False


MAIN_BASS_POSITIONS = ("FL", "FR", "RL", "RR", "FC")
BASS_SUM_GAIN = 1.0 / math.sqrt(5.0)


def bass_dsp_controls(settings):
    """Return live control values for the explicit Ubuntu 5.1 bass graph."""
    mode = str(settings.get("bass_routing", "REDIRECT")).upper()
    enabled = bool(settings.get("bass_management", False))
    synth = enabled and mode in ("REDIRECT", "DUPLICATE")
    redirect = enabled and mode == "REDIRECT"
    slope24 = str(settings.get("bass_slope", "24")) == "24"
    crossover = float(settings.get("bass_crossover", 80))
    q = 0.70710678 if slope24 else 0.5
    controls = {}
    for pos in MAIN_BASS_POSITIONS:
        for kind in ("hp", "lp"):
            controls[f"{kind}1_{pos}:Freq"] = crossover
            controls[f"{kind}1_{pos}:Q"] = q
            controls[f"{kind}2_{pos}:Freq"] = crossover
            controls[f"{kind}2_{pos}:Q"] = 0.70710678
        controls[f"main_select_{pos}:Gain 1"] = 0.0 if redirect else 1.0
        controls[f"main_select_{pos}:Gain 2"] = 1.0 if redirect and not slope24 else 0.0
        controls[f"main_select_{pos}:Gain 3"] = 1.0 if redirect and slope24 else 0.0
        controls[f"bass_select_{pos}:Gain 1"] = BASS_SUM_GAIN if synth and not slope24 else 0.0
        controls[f"bass_select_{pos}:Gain 2"] = BASS_SUM_GAIN if synth and slope24 else 0.0
    controls["native_lfe_trim:Mult"] = math.pow(10.0, float(settings.get("lfe_trim", 0.0)) / 20.0)
    return controls


def ubuntu_bass_eq_graph(gains, preamp_db, settings):
    """Build an explicit six-channel graph capable of main-to-LFE routing."""
    nodes, links, inputs, outputs = [], [], [], []
    controls = bass_dsp_controls(settings)
    preamp_mult = math.pow(10.0, float(preamp_db) / 20.0)
    for pos in (*MAIN_BASS_POSITIONS, "LFE"):
        pre = f"preamp_{pos}"
        nodes.append(f'          {{ type = builtin name = {pre} label = linear control = {{ "Mult" = {preamp_mult:.8f} "Add" = 0.0 }} }}')
        inputs.append(f'"{pre}:In"')
        previous = f"{pre}:Out"
        for freq in BANDS:
            name = f"eq_{pos}_{freq}"
            nodes.append(f'          {{ type = builtin name = {name} label = bq_peaking control = {{ "Freq" = {float(freq):.1f} "Q" = 1.4 "Gain" = {float(gains.get(freq, 0.0)):.1f} }} }}')
            links.append(f'          {{ output = "{previous}" input = "{name}:In" }}')
            previous = f"{name}:Out"
        if pos == "LFE":
            trim = controls["native_lfe_trim:Mult"]
            nodes.append(f'          {{ type = builtin name = native_lfe_trim label = linear control = {{ "Mult" = {trim:.8f} "Add" = 0.0 }} }}')
            links.append(f'          {{ output = "{previous}" input = "native_lfe_trim:In" }}')
            links.append('          { output = "native_lfe_trim:Out" input = "lfe_sum:In 1" }')
            continue
        for kind, label in (("hp", "bq_highpass"), ("lp", "bq_lowpass")):
            for stage in (1, 2):
                name = f"{kind}{stage}_{pos}"
                nodes.append(f'          {{ type = builtin name = {name} label = {label} control = {{ "Freq" = {controls[f"{name}:Freq"]:.1f} "Q" = {controls[f"{name}:Q"]:.8f} }} }}')
            links.append(f'          {{ output = "{previous}" input = "{kind}1_{pos}:In" }}')
            links.append(f'          {{ output = "{kind}1_{pos}:Out" input = "{kind}2_{pos}:In" }}')
        mg = [controls[f"main_select_{pos}:Gain {i}"] for i in (1,2,3)]
        bg = [controls[f"bass_select_{pos}:Gain {i}"] for i in (1,2)]
        nodes.append(f'          {{ type = builtin name = main_select_{pos} label = mixer control = {{ "Gain 1" = {mg[0]:.1f} "Gain 2" = {mg[1]:.1f} "Gain 3" = {mg[2]:.1f} }} }}')
        nodes.append(f'          {{ type = builtin name = bass_select_{pos} label = mixer control = {{ "Gain 1" = {bg[0]:.1f} "Gain 2" = {bg[1]:.1f} }} }}')
        links.extend([
            f'          {{ output = "{previous}" input = "main_select_{pos}:In 1" }}',
            f'          {{ output = "hp1_{pos}:Out" input = "main_select_{pos}:In 2" }}',
            f'          {{ output = "hp2_{pos}:Out" input = "main_select_{pos}:In 3" }}',
            f'          {{ output = "lp1_{pos}:Out" input = "bass_select_{pos}:In 1" }}',
            f'          {{ output = "lp2_{pos}:Out" input = "bass_select_{pos}:In 2" }}',
            f'          {{ output = "bass_select_{pos}:Out" input = "lfe_sum:In {MAIN_BASS_POSITIONS.index(pos)+2}" }}',
        ])
        outputs.append(f'"main_select_{pos}:Out"')
    nodes.append('          { type = builtin name = lfe_sum label = mixer control = { "Gain 1" = 1.0 "Gain 2" = 1.0 "Gain 3" = 1.0 "Gain 4" = 1.0 "Gain 5" = 1.0 "Gain 6" = 1.0 } }')
    nodes.append('          { type = ladspa name = lfe_limiter plugin = ZaMaximX2-ladspa label = ZaMaximX2 control = { "Release" = 50.0 "Output Ceiling" = -0.5 "Threshold" = -0.5 } }')
    links.append('          { output = "lfe_sum:Out" input = "lfe_limiter:Audio Input 1" }')
    links.append('          { output = "lfe_sum:Out" input = "lfe_limiter:Audio Input 2" }')
    outputs.append('"lfe_limiter:Audio Output 1"')
    return nodes, links, inputs, outputs


def eq_config_text(target_sink, gains=None, positions=None, preamp_db=0.0, settings=None, compatibility=None):
    if compatibility is None:
        compatibility = is_bazzite()
    gains = gains or {f: 0.0 for f in BANDS}
    positions = positions or sink_channel_positions(target_sink)
    channel_count = len(positions)
    position_text = " ".join(positions)
    explicit_bass = not compatibility and positions == ["FL", "FR", "RL", "RR", "FC", "LFE"]
    if explicit_bass:
        nodes, links, inputs, outputs = ubuntu_bass_eq_graph(gains, preamp_db, settings or DEFAULT_CURRENT)
        graph_ports = "        inputs = [ " + " ".join(inputs) + " ]\n        outputs = [ " + " ".join(outputs) + " ]\n"
    else:
        graph_ports = ""
    if not explicit_bass:
        nodes = [
            "          {\n"
            "            type = builtin\n"
            "            name = preamp\n"
            "            label = linear\n"
            f'            control = {{ "Mult" = {math.pow(10.0, float(preamp_db) / 20.0):.8f} "Add" = 0.0 }}\n'
            "          }"
        ]
        links = []
        first_link = "preamp:Out"
    if not explicit_bass and not compatibility and settings and settings.get("bass_management", False):
        nodes.append("""          {
            type = builtin
            name = bass_mgmt
            label = copy
          }""")
        links.append("          { output = \"preamp:Out\" input = \"bass_mgmt:In\" }")
        first_link = "bass_mgmt:Out"
    if not explicit_bass:
        for i, freq in enumerate(BANDS):
            nodes.append(
                "          {\n"
                "            type = builtin\n"
                f"            name = eq_{freq}\n"
                "            label = bq_peaking\n"
                f'            control = {{ "Freq" = {float(freq):.1f} "Q" = 1.4 "Gain" = {float(gains.get(freq, 0.0)):.1f} }}\n'
                "          }"
            )
            if i:
                links.append(f'          {{ output = "eq_{BANDS[i-1]}:Out" input = "eq_{freq}:In" }}')
            else:
                links.append(f'          {{ output = "{first_link}" input = "eq_{freq}:In" }}')
    smart_lines = "" if compatibility else (
        "        filter.smart = true\n"
        f'        filter.smart.name = "{APP_ID}-eq"\n'
        "        filter.smart.targetable = false\n"
        f'        filter.smart.target = {{ node.name = "{target_sink}" }}\n'
    )
    target_line = f'        target.object = "{target_sink}"\n' if compatibility else ""
    return (
        "context.modules = [\n"
        "  {\n"
        "    name = libpipewire-module-filter-chain\n"
        "    args = {\n"
        f'      node.description = "{APP_NAME} {layout_name(positions)} EQ"\n'
        f'      media.name = "{APP_NAME} {layout_name(positions)} EQ"\n\n'
        "      filter.graph = {\n"
        "        nodes = [\n" + "\n".join(nodes) + "\n        ]\n\n"
        "        links = [\n" + "\n".join(links) + "\n        ]\n"
        + graph_ports
        +
        "      }\n\n"
        "      capture.props = {\n"
        f'        node.name = "{SINK}"\n'
        f'        node.description = "{APP_NAME} {layout_name(positions)} EQ"\n'
        '        media.class = "Audio/Sink"\n'
        + smart_lines
        + f"        audio.channels = {channel_count}\n"
        f"        audio.position = [ {position_text} ]\n"
        "      }\n\n"
        "      playback.props = {\n"
        f'        node.name = "{SINK}_output"\n'
        f'        node.description = "{APP_NAME} {layout_name(positions)} EQ Output"\n'
        "        node.passive = true\n"
        + target_line
        + "        stream.dont-remix = true\n"
        f"        audio.channels = {channel_count}\n"
        f"        audio.position = [ {position_text} ]\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "]\n"
    )

def fill_config_text(settings=None, compatibility=None):
    """Generate distro-appropriate PipeWire-Pulse Speaker Fill defaults."""
    if compatibility is None:
        compatibility = is_bazzite()
    s = settings or DEFAULT_CURRENT
    mode = s.get("fill_mode", "PSD")
    upmix = "false" if compatibility or mode == "OFF" else "true"
    method = "simple" if mode == "FULL" else "psd"
    rear_delay = float(s.get("rear_delay", 12.0))
    stereo_width = float(s.get("stereo_width", 0.0))
    lfe_cutoff = int(s.get("lfe_cutoff", 150))
    return (
        "stream.properties = {\n"
        + ("  # Bazzite: stereo fill uses the dedicated soundblaster_zse_fill sink.\n" if compatibility else
           "  # Ubuntu: v3.3.2 global PipeWire-Pulse Speaker Fill behavior.\n")
        + f"  channelmix.upmix = {upmix}\n"
        f'  channelmix.upmix-method = "{method}"\n'
        f"  channelmix.rear-delay = {rear_delay:.1f}\n"
        f"  channelmix.stereo-widen = {stereo_width:.2f}\n"
        f"  channelmix.lfe-cutoff = {lfe_cutoff}\n"
        "}\n"
    )


def parse_eq_config():
    gains = {f: 0.0 for f in BANDS}
    target = ""
    try:
        text = EQ_CONFIG.read_text()
        mt = re.search(r'filter\.smart\.target\s*=\s*\{[^}]*node\.name\s*=\s*"([^"]+)"', text, re.S)
        if not mt:
            mt = re.search(r'target\.object\s*=\s*"([^"]+)"', text)
        if mt:
            target = mt.group(1)
        for f in BANDS:
            m = re.search(rf'name\s*=\s*eq_(?:FL_)?{f}\b.*?"Gain"\s*=\s*(-?\d+(?:\.\d+)?)', text, re.S)
            if not m:
                m = re.search(rf"freq\s*=\s*{f}\s+gain\s*=\s*(-?\d+(?:\.\d+)?)", text)
            if m:
                gains[f] = float(m.group(1))
    except Exception:
        pass
    return gains, target


def ensure_configs(data, force=False):
    gains, existing_target = parse_eq_config()
    target = data["current"].get("hardware_sink") or existing_target or detect_hardware_sink()
    if not target or target == SINK:
        raise RuntimeError("No physical output sink could be detected. Choose one in Device Setup.")
    data["current"]["hardware_sink"] = target
    EQ_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    FILL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if force or not EQ_CONFIG.exists():
        EQ_CONFIG.write_text(eq_config_text(target, gains, preamp_db=effective_preamp_db(data["current"]), settings=data["current"]))
    if force or not FILL_CONFIG.exists():
        FILL_CONFIG.write_text(fill_config_text(data["current"]))
    save_data(data)


def restart_audio(target=None):
    # Fedora/Bazzite ships filter-chain.service, which runs `pipewire -c
    # filter-chain.conf`. Restart only that EQ client when changing EQ config;
    # do not churn the entire desktop audio stack every 30 seconds.
    if is_bazzite():
        result = run(["systemctl", "--user", "restart", "filter-chain.service"], capture=True)
        if result.returncode != 0:
            raise RuntimeError("Sound Blaster EQ service restart failed: " + (result.stderr.strip() or "unknown error"))
    else:
        result = run(["systemctl", "--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"], capture=True)
        if result.returncode != 0:
            raise RuntimeError("PipeWire restart command failed: " + (result.stderr.strip() or "unknown error"))
    if target and not wait_for_sink(target, 20):
        raise RuntimeError(f"Hardware target '{target}' is unavailable after audio reload")
    if not wait_for_sink(SINK, 20):
        raise RuntimeError(f"Hardware audio is available, but the Sound Blaster EQ node '{SINK}' did not load")
    set_default_sink(target)


def get_filter_node_id():
    # pw-dump does not accept a node name as a positional selector; dump the
    # graph and locate our main filter node by its persistent node.name.
    result = run(["pw-dump"], capture=True)
    if result.returncode != 0:
        return None
    try:
        objects = json.loads(result.stdout)
    except Exception:
        return None
    for obj in objects:
        try:
            if obj.get("info", {}).get("props", {}).get("node.name") == SINK:
                return int(obj["id"])
        except Exception:
            pass
    return None


def explicit_bass_graph_configured():
    try:
        return "name = preamp_FL" in EQ_CONFIG.read_text()
    except Exception:
        return False


def set_filter_controls(controls):
    node_id = get_filter_node_id()
    if node_id is None or not controls:
        return False
    values = []
    for name, value in controls.items():
        values.extend([f'"{name}"', f"{float(value):.8f}"])
    payload = '{ "params": [ ' + " ".join(values) + ' ] }'
    return run(["pw-cli", "s", str(node_id), "Props", payload], capture=True).returncode == 0


def apply_bass_management_live(settings):
    if is_bazzite() or not explicit_bass_graph_configured():
        return False
    return set_filter_controls(bass_dsp_controls(settings))


def persist_bass_management_config(settings):
    if is_bazzite() or not explicit_bass_graph_configured():
        return False
    gains, target = parse_eq_config()
    target = settings.get("hardware_sink") or target
    if not target:
        return False
    EQ_CONFIG.write_text(eq_config_text(
        target, gains, positions=["FL", "FR", "RL", "RR", "FC", "LFE"],
        preamp_db=effective_preamp_db(settings), settings=settings, compatibility=False))
    return True


def live_set_eq(freq, gain):
    if explicit_bass_graph_configured() and not is_bazzite():
        return set_filter_controls({f"eq_{pos}_{freq}:Gain": gain for pos in (*MAIN_BASS_POSITIONS, "LFE")})
    return set_filter_controls({f"eq_{freq}:Gain": gain})


def read_live_eq_gain(freq):
    """Read one live EQ band gain from the filter-chain Props."""
    node_id = get_filter_node_id()
    if node_id is None:
        return None
    result = run(["pw-cli", "enum-params", str(node_id), "Props"], capture=True)
    if result.returncode != 0:
        return None
    key = f"eq_FL_{freq}:Gain" if explicit_bass_graph_configured() and not is_bazzite() else f"eq_{freq}:Gain"
    match = re.search(rf'String\s+"{re.escape(key)}"\s+Float\s+(-?\d+(?:\.\d+)?)', result.stdout, re.S)
    return float(match.group(1)) if match else None


def restore_live_eq_verified(settings, attempts=10):
    """Reassert saved EQ after startup and require stable live readback.

    A newly-created filter-chain node can briefly accept controls and then be
    reset as PipeWire/WirePlumber finishes settling.  Require two consecutive
    matching readbacks before declaring the startup EQ restored.
    """
    eq = settings.get("eq", {})
    expected = {f: float(eq.get(str(f), eq.get(f, 0.0))) for f in BANDS}
    tolerance = 0.05
    stable_matches = 0
    for attempt in range(1, attempts + 1):
        writes_ok = True
        for freq, gain in expected.items():
            writes_ok = live_set_eq(freq, gain) and writes_ok
        time.sleep(0.30)
        readback = {freq: read_live_eq_gain(freq) for freq in BANDS}
        matches = writes_ok and all(
            readback[freq] is not None and abs(readback[freq] - gain) <= tolerance
            for freq, gain in expected.items()
        )
        stable_matches = stable_matches + 1 if matches else 0
        restore_log(
            f"EQ startup attempt {attempt}/{attempts}: "
            f"{'stable' if stable_matches >= 2 else 'ok-wait' if matches else 'retry'}"
        )
        if stable_matches >= 2:
            for freq, gain in expected.items():
                persist_eq_gain(freq, gain)
            return True
        if attempt < attempts:
            time.sleep(0.45)
    restore_log("EQ startup restore FAILED")
    return False


def live_set_preamp(db):
    linear = math.pow(10.0, float(db) / 20.0)
    if explicit_bass_graph_configured() and not is_bazzite():
        return set_filter_controls({f"preamp_{pos}:Mult": linear for pos in (*MAIN_BASS_POSITIONS, "LFE")})
    return set_filter_controls({"preamp:Mult": linear})


def read_live_preamp_mult():
    """Read the filter-chain linear preamp multiplier from its live Props."""
    node_id = get_filter_node_id()
    if node_id is None:
        return None
    result = run(["pw-cli", "enum-params", str(node_id), "Props"], capture=True)
    if result.returncode != 0:
        return None
    key = "preamp_FL:Mult" if explicit_bass_graph_configured() and not is_bazzite() else "preamp:Mult"
    match = re.search(rf'String\s+"{re.escape(key)}"\s+Float\s+(-?\d+(?:\.\d+)?)', result.stdout, re.S)
    return float(match.group(1)) if match else None


def persist_preamp_gain(db):
    if not EQ_CONFIG.exists():
        return
    text = EQ_CONFIG.read_text()
    linear = math.pow(10.0, float(db) / 20.0)
    pattern = r'(name\s*=\s*preamp(?:_[A-Z]+)?\b.*?control\s*=\s*\{.*?"Mult"\s*=\s*)-?\d+(?:\.\d+)?'
    text2, count = re.subn(pattern, lambda m: m.group(1) + f"{linear:.8f}", text, flags=re.S)
    if count:
        EQ_CONFIG.write_text(text2)


def persist_eq_gain(freq, gain):
    if not EQ_CONFIG.exists():
        return
    text = EQ_CONFIG.read_text()
    pattern = rf'(name\s*=\s*eq_(?:[A-Z]+_)?{freq}\b.*?control\s*=\s*\{{.*?"Gain"\s*=\s*)-?\d+(?:\.\d+)?'
    text2, count = re.subn(pattern, lambda m: m.group(1) + f"{float(gain):.1f}", text, flags=re.S)
    if count:
        EQ_CONFIG.write_text(text2)


def replace_setting(text, name, value):
    pattern = rf"({re.escape(name)}\s*=\s*)[^\n\r]+"
    if re.search(pattern, text):
        return re.sub(pattern, lambda m: m.group(1) + str(value), text, count=1)
    pos = text.rfind("}")
    if pos == -1:
        raise RuntimeError(f"Malformed PipeWire config: {FILL_CONFIG}")
    return text[:pos] + f"  {name} = {value}\n" + text[pos:]


def write_spatial(settings):
    # Rewrite this small generated drop-in atomically. Speaker Fill rules are
    # mode-dependent, so editing individual keys can leave stale global/rule
    # settings behind when switching OFF/PSD/FULL.
    FILL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILL_CONFIG.with_suffix(FILL_CONFIG.suffix + ".tmp")
    tmp.write_text(fill_config_text(settings))
    tmp.replace(FILL_CONFIG)


def configured_channel_positions():
    try:
        text = EQ_CONFIG.read_text()
        m = re.search(r'capture\.props\s*=\s*\{.*?audio\.position\s*=\s*\[([^\]]+)\]', text, re.S)
        if m:
            vals = normalize_channel_positions(m.group(1))
            if 2 <= len(vals) <= 6:
                return vals
    except Exception:
        pass
    target = DATA.get("current", {}).get("hardware_sink", "") if "DATA" in globals() else ""
    return sink_channel_positions(target) if target else ["FL","FR"]


def requested_channel_levels(settings, bypass=False):
    trims = {"FL": "fl", "FR": "fr", "FC": "fc", "LFE": "lfe", "RL": "rl", "RR": "rr"}
    positions = configured_channel_positions()
    levels_pct = []
    for pos in positions:
        key = trims.get(pos)
        pct = 100.0 if bypass or key is None else float(settings.get(key, 100.0))
        levels_pct.append(max(0.0, min(100.0, pct)))
    return positions, levels_pct


def channel_level_sink(settings=None):
    """Return the sink whose per-channel volume is actually in the live audio path."""
    if is_bazzite():
        current = settings or {}
        target = current.get("hardware_sink", "")
        if not target and "DATA" in globals():
            target = DATA.get("current", {}).get("hardware_sink", "")
        if target and sink_exists(target):
            return target
    return SINK


def read_channel_levels(name=SINK):
    """Read sink channel volumes as OS-displayed percentages in channel order."""
    if not sink_exists(name):
        return []
    result = run(["pactl", "get-sink-volume", name], capture=True)
    if result.returncode != 0:
        return []
    return [float(x) for x in re.findall(r"/\s*(\d+(?:\.\d+)?)%", result.stdout)]


def channel_levels_match(expected_pct, actual_pct, tolerance_pct=1.0):
    if len(expected_pct) != len(actual_pct):
        return False
    return all(abs(a - e) <= tolerance_pct for e, a in zip(expected_pct, actual_pct))


def percent_to_pactl_volume(percent):
    """Convert an OS-style 0..100 percent channel level to absolute Pulse volume."""
    pct = max(0.0, min(100.0, float(percent)))
    return int(round(65536.0 * pct / 100.0))


def apply_channel_levels(settings, bypass=False):
    target = channel_level_sink(settings)
    if not sink_exists(target):
        return False
    # Ubuntu keeps the verified virtual-EQ sink volume path. Bazzite's filter
    # output bypasses that sink volume, so its room-balance attenuation must be
    # applied to the selected physical multichannel sink instead.
    positions, levels_pct = requested_channel_levels(settings, bypass)
    argv = ["pactl", "set-sink-volume", target] + [str(percent_to_pactl_volume(v)) for v in levels_pct]
    restore_log(f"channel volume argv={argv!r} positions={positions} target_pct={[round(v, 1) for v in levels_pct]}")
    result = run(argv)
    return result.returncode == 0


def restore_log(message):
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with RESTORE_LOG.open("a") as fp:
            fp.write(f"{stamp} {message}\n")
        # Keep diagnostics lightweight.
        lines = RESTORE_LOG.read_text().splitlines()[-120:]
        RESTORE_LOG.write_text("\n".join(lines) + "\n")
    except Exception:
        pass


def restore_channel_levels_verified(settings, attempts=5):
    """Apply saved trims only after the virtual sink exists and verify stability.

    A bounded re-apply window handles the login race where WirePlumber/PipeWire
    can restore its own sink volume shortly after our autostart entry runs.
    Saved state is never replaced with transient runtime values.
    """
    positions, expected_pct = requested_channel_levels(settings)
    restore_log(f"channel restore requested positions={positions} pct={[round(v,1) for v in expected_pct]}")
    target = channel_level_sink(settings)
    for attempt in range(1, attempts + 1):
        if not sink_exists(target):
            restore_log(f"attempt {attempt}: channel-level sink not present target={target}")
            time.sleep(1.0)
            target = channel_level_sink(settings)
            continue
        ok = apply_channel_levels(settings)
        time.sleep(0.35)
        actual = read_channel_levels(target)
        if ok and channel_levels_match(expected_pct, actual):
            # Verify once more after a short settling interval; this catches a
            # later session-manager volume restore without an endless watcher.
            time.sleep(1.5)
            stable = read_channel_levels(target)
            if channel_levels_match(expected_pct, stable):
                restore_log(f"attempt {attempt}: verified stable readback={[round(v,2) for v in stable]}")
                return True
            restore_log(f"attempt {attempt}: reset after apply readback={[round(v,2) for v in stable]}")
        else:
            restore_log(f"attempt {attempt}: apply/readback mismatch readback={[round(v,2) for v in actual]}")
        if attempt < attempts:
            time.sleep(float(attempt))
    restore_log("channel restore FAILED after bounded retries")
    return False


def combined_eq_peak_db(settings):
    """Estimate the maximum gain of the *combined* 10-band EQ response.

    The filter graph uses cascaded RBJ-style peaking biquads at Q=1.4.  We
    evaluate the actual cascade across the audible band instead of treating a
    slider value as if it were the whole-EQ peak.  This is still a transfer-
    function estimate, not a real-time signal peak meter.
    """
    eq = settings.get("eq", {}) or {}
    fs = 48000.0
    q = 1.4
    # Log-spaced scan is plenty dense for a UI/headroom estimate.
    points = 768
    peak_db = -120.0
    for i in range(points):
        hz = 20.0 * ((20000.0 / 20.0) ** (i / (points - 1)))
        w = 2.0 * math.pi * hz / fs
        z1 = cmath.exp(-1j * w)
        z2 = z1 * z1
        total = 1.0 + 0j
        for freq in BANDS:
            try:
                gain_db = float(eq.get(str(freq), eq.get(freq, 0.0)))
            except Exception:
                gain_db = 0.0
            if abs(gain_db) < 1e-9:
                continue
            A = 10.0 ** (gain_db / 40.0)
            w0 = 2.0 * math.pi * float(freq) / fs
            alpha = math.sin(w0) / (2.0 * q)
            c = math.cos(w0)
            b0 = 1.0 + alpha * A
            b1 = -2.0 * c
            b2 = 1.0 - alpha * A
            a0 = 1.0 + alpha / A
            a1 = -2.0 * c
            a2 = 1.0 - alpha / A
            num = b0 + b1 * z1 + b2 * z2
            den = a0 + a1 * z1 + a2 * z2
            if abs(den) > 1e-15:
                total *= num / den
        mag = max(abs(total), 1e-12)
        peak_db = max(peak_db, 20.0 * math.log10(mag))
    return max(0.0, peak_db)


def safe_preamp_limit(settings):
    """Return a conservative DSP preamp ceiling for the current EQ curve.

    Safe Headroom protects the EQ/preamp DSP path and intentionally does not
    cancel user-selected per-channel trims.  A small 0.5 dB guard band is kept
    for rounding/interpolation margin.
    """
    peak_eq = combined_eq_peak_db(settings)
    if peak_eq <= 0.0:
        return 0.0
    return max(-24.0, -(peak_eq + 0.5))


def effective_preamp_db(settings, bypass=False):
    if bypass:
        return 0.0
    requested = float(settings.get("preamp", 0.0))
    if bool(settings.get("safe_headroom", False)):
        return min(requested, safe_preamp_limit(settings))
    return requested


def apply_preamp(settings, bypass=False, persist=True):
    db = effective_preamp_db(settings, bypass)
    ok = live_set_preamp(db)
    if ok and persist and not bypass:
        # Persist the effective DSP gain for a safe, pop-free startup. The
        # user's requested preamp remains separately stored in state.json.
        persist_preamp_gain(db)
    return ok


def restore_preamp_verified(settings, attempts=8, persist=False):
    """Apply the effective preamp until live readback survives settling."""
    expected_db = effective_preamp_db(settings)
    expected_mult = math.pow(10.0, expected_db / 20.0)
    tolerance = 0.0005
    restore_log(f"headroom target db={expected_db:.2f} mult={expected_mult:.8f} tolerance={tolerance:.7f}")
    for attempt in range(1, attempts + 1):
        ok = apply_preamp(settings, persist=False)
        restore_log(f"headroom attempt {attempt}/{attempts}: write target_mult={expected_mult:.8f} result={'ok' if ok else 'failed'}")
        time.sleep(0.4)
        actual = read_live_preamp_mult()
        restore_log(f"headroom attempt {attempt}/{attempts}: readback_mult={actual if actual is not None else 'unavailable'}")
        if ok and actual is not None and abs(actual - expected_mult) <= tolerance:
            # A second read catches PipeWire/WirePlumber replacing the value
            # shortly after accepting the first write during session startup.
            time.sleep(1.0)
            confirmed = read_live_preamp_mult()
            restore_log(f"headroom attempt {attempt}/{attempts}: settled_readback_mult={confirmed if confirmed is not None else 'unavailable'}")
            if confirmed is not None and abs(confirmed - expected_mult) <= tolerance:
                if persist:
                    persist_preamp_gain(expected_db)
                restore_log(f"headroom restore SUCCESS target_mult={expected_mult:.8f} live_mult={confirmed:.8f}")
                return True
        if attempt < attempts:
            time.sleep(0.6)
    final = read_live_preamp_mult()
    restore_log(f"headroom restore FAILED target_mult={expected_mult:.8f} live_mult={final if final is not None else 'unavailable'}")
    return False


def live_preamp_status(settings, live_mult=None):
    """Describe the calculated target and actual live preamp attenuation."""
    target_db = effective_preamp_db(settings)
    if live_mult is None:
        live_mult = read_live_preamp_mult()
    if live_mult is None:
        return f"target {target_db:+.1f} dB • live unavailable"
    if live_mult <= 0.0:
        return f"target {target_db:+.1f} dB • live muted/invalid ({live_mult:.6f})"
    live_db = 20.0 * math.log10(live_mult)
    return f"target {target_db:+.1f} dB • live {live_db:+.1f} dB (Mult {live_mult:.6f})"

def restore_at_login(data):
    restore_log(f"startup restore begin version={VERSION}")
    try:
        ensure_configs(data)
    except Exception as exc:
        restore_log(f"ensure_configs warning: {exc}")
    if not wait_for_sink(SINK, 20):
        restore_log(f"startup restore FAILED: {SINK} did not appear")
        return False
    target = data["current"].get("hardware_sink", "")
    if target and sink_exists(target):
        set_default_sink(target)
    apply_bass_management_live(data["current"])
    channels_ok = restore_channel_levels_verified(data["current"])
    # Apply headroom last so no subsequent startup settling work occurs after
    # its confirmed live readback.
    preamp_ok = restore_preamp_verified(data["current"], persist=False)
    restore_log(f"startup restore complete preamp={'ok' if preamp_ok else 'failed'} channels={'ok' if channels_ok else 'failed'}")
    return preamp_ok and channels_ok


def configure_target(data, target):
    if not target or target == SINK:
        raise RuntimeError("Choose a physical hardware sink, not the Sound Blaster EQ virtual sink")
    gains, _ = parse_eq_config()
    data["current"]["hardware_sink"] = target
    EQ_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    EQ_CONFIG.write_text(eq_config_text(target, gains, preamp_db=effective_preamp_db(data["current"]), settings=data["current"]))
    save_data(data)


def acquire_single_instance():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    lock_fp = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fp
    except BlockingIOError:
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(str(SOCKET_PATH))
            s.sendall(b"RAISE\n")
            s.close()
        except Exception:
            pass
        return None


LINE_MONITOR_PROC = None

def list_sources():
    r=run(["pactl","list","short","sources"],capture=True); out=[]
    if r.returncode==0:
        for line in r.stdout.splitlines():
            p=line.split("\t")
            if len(p)>=2 and not p[1].endswith(".monitor"): out.append(p[1])
    return out

def source_ports(source_name):
    """Return [(port_name, friendly_label, active)] for a Pulse/PipeWire source."""
    r = run(["pactl", "list", "sources"], capture=True)
    if r.returncode != 0:
        return []
    current = None
    in_ports = False
    active_port = ""
    ports = []
    found = False
    for raw in r.stdout.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("Name:"):
            current = stripped.split(":", 1)[1].strip()
            found = current == source_name
            in_ports = False
            if not found and ports:
                break
        elif found and stripped == "Ports:":
            in_ports = True
        elif found and stripped.startswith("Active Port:"):
            active_port = stripped.split(":", 1)[1].strip()
            in_ports = False
        elif found and in_ports and stripped:
            # Example: analog-input-linein: Line In (type: Line, ... )
            m = re.match(r"([^:]+):\s*(.*?)(?:\s*\(type:.*)?$", stripped)
            if m:
                pname, label = m.group(1).strip(), m.group(2).strip()
                ports.append((pname, label or pname))
    return [(name, label, name == active_port) for name, label in ports]



def set_input_gain(source_name, level_percent, boost_db=0.0):
    """Apply capture level plus optional software mic boost through PipeWire/Pulse.

    level_percent is the normal input level (0-100%). boost_db is added on top
    and may raise the effective source volume above 100%. This works across
    PipeWire/Pulse systems without relying on a card-specific ALSA mixer name.
    """
    if not source_name:
        return False
    try:
        level = max(0.0, min(100.0, float(level_percent)))
        boost = max(0.0, min(30.0, float(boost_db)))
        effective = level * (10.0 ** (boost / 20.0))
        effective = max(0.0, min(400.0, effective))
        return run(["pactl", "set-source-volume", source_name, f"{effective:.2f}%"]).returncode == 0
    except Exception:
        return False

def input_gain_summary(level_percent, boost_db):
    try:
        level=float(level_percent); boost=float(boost_db)
        eff=max(0.0,min(400.0,level*(10.0**(boost/20.0))))
        return f"Effective capture gain: {eff:.0f}%"
    except Exception:
        return "Effective capture gain: --"

def mic_thresholds(strength):
    strength = max(0.0, min(100.0, float(strength)))
    if strength <= 0.0:
        return 0.0, 0.0
    close_db = -70.0 + 35.0 * (strength / 100.0)
    open_db = close_db + 5.0
    return 10.0 ** (close_db / 20.0), 10.0 ** (open_db / 20.0)


def mic_config_text(source_name, settings):
    low = float(settings.get("mic_eq_low", 0.0))
    mid = float(settings.get("mic_eq_mid", 0.0))
    high = float(settings.get("mic_eq_high", 0.0))
    enabled = bool(settings.get("mic_noise_reduction", True))
    strength = float(settings.get("mic_noise_strength", 50.0)) if enabled else 0.0
    close_t, open_t = mic_thresholds(strength)
    return f'''context.modules = [
  {{
    name = libpipewire-module-filter-chain
    args = {{
      node.description = "Sound Blaster Processed Mic"
      media.name = "Sound Blaster Processed Mic"
      filter.graph = {{
        nodes = [
          {{ type = builtin name = mic_hp label = bq_highpass control = {{ "Freq" = 70.0 "Q" = 0.707 "Gain" = 0.0 }} }}
          {{ type = builtin name = mic_low label = bq_lowshelf control = {{ "Freq" = 160.0 "Q" = 0.707 "Gain" = {low:.1f} }} }}
          {{ type = builtin name = mic_mid label = bq_peaking control = {{ "Freq" = 1800.0 "Q" = 0.9 "Gain" = {mid:.1f} }} }}
          {{ type = builtin name = mic_high label = bq_highshelf control = {{ "Freq" = 6000.0 "Q" = 0.707 "Gain" = {high:.1f} }} }}
          {{ type = builtin name = mic_gate label = noisegate control = {{ "Close threshold" = {close_t:.8f} "Open threshold" = {open_t:.8f} "Attack (s)" = 0.008 "Hold (s)" = 0.080 "Release (s)" = 0.120 }} }}
        ]
        links = [
          {{ output = "mic_hp:Out" input = "mic_low:In" }}
          {{ output = "mic_low:Out" input = "mic_mid:In" }}
          {{ output = "mic_mid:Out" input = "mic_high:In" }}
          {{ output = "mic_high:Out" input = "mic_gate:In" }}
        ]
        inputs = [ "mic_hp:In" ]
        outputs = [ "mic_gate:Out" ]
      }}
      capture.props = {{
        node.name = "capture.soundblaster_processed_mic"
        target.object = "{source_name}"
        node.passive = true
        audio.channels = 2
        audio.position = [ FL FR ]
      }}
      playback.props = {{
        node.name = "{MIC_SOURCE}"
        node.description = "Sound Blaster Processed Mic"
        media.class = "Audio/Source"
        audio.channels = 2
        audio.position = [ FL FR ]
      }}
    }}
  }}
]
'''


def get_mic_filter_node_id():
    r = run(["pw-dump"], capture=True)
    if r.returncode != 0:
        return None
    try:
        objs = json.loads(r.stdout)
    except Exception:
        return None
    for obj in objs:
        try:
            if obj.get("info", {}).get("props", {}).get("node.name") == MIC_SOURCE:
                return int(obj["id"])
        except Exception:
            pass
    return None


def live_set_mic_processing(settings):
    node_id = get_mic_filter_node_id()
    if node_id is None:
        return False
    strength = float(settings.get("mic_noise_strength", 50.0)) if settings.get("mic_noise_reduction", True) else 0.0
    close_t, open_t = mic_thresholds(strength)
    params = [
        ("mic_low:Gain", float(settings.get("mic_eq_low", 0.0))),
        ("mic_mid:Gain", float(settings.get("mic_eq_mid", 0.0))),
        ("mic_high:Gain", float(settings.get("mic_eq_high", 0.0))),
        ("mic_gate:Close threshold", close_t),
        ("mic_gate:Open threshold", open_t),
    ]
    ok = True
    for name, value in params:
        payload = f'{{ "params": [ "{name}", {value:.8f} ] }}'
        ok = run(["pw-cli", "s", str(node_id), "Props", payload], capture=True).returncode == 0 and ok
    return ok


def write_mic_processing_config(source_name, settings):
    MIC_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if settings.get("mic_processing", False) and source_name:
        MIC_CONFIG.write_text(mic_config_text(source_name, settings))
    elif MIC_CONFIG.exists():
        MIC_CONFIG.unlink()


def set_source_port(source_name, port_name):
    if not source_name or not port_name:
        return False
    return run(["pactl", "set-source-port", source_name, port_name]).returncode == 0

def start_line_monitor(source, target):
    global LINE_MONITOR_PROC
    stop_line_monitor()
    if not source or not target: return False
    if not shutil.which("pw-loopback"): return False
    LINE_MONITOR_PROC=subprocess.Popen(["pw-loopback","--capture-props",f'target.object={source} node.passive=true',"--playback-props",f'target.object={target} media.role=Music'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return True

def stop_line_monitor():
    global LINE_MONITOR_PROC
    if LINE_MONITOR_PROC and LINE_MONITOR_PROC.poll() is None:
        LINE_MONITOR_PROC.terminate()
    LINE_MONITOR_PROC=None

# Background restore mode intentionally avoids the GUI/single-instance lock.
if "--generate-eq-config" in sys.argv:
    index = sys.argv.index("--generate-eq-config")
    try:
        _target = sys.argv[index + 1]
        _output = Path(sys.argv[index + 2])
    except Exception:
        print("usage: --generate-eq-config TARGET OUTPUT", file=sys.stderr)
        sys.exit(2)
    _data = load_data()
    _gains, _existing = parse_eq_config()
    _data["current"]["hardware_sink"] = _target
    # state.json is authoritative for the selected/current EQ.  Using only the
    # pre-install filter graph can resurrect a stale curve on the first launch
    # after an upgrade, until the user re-selects the preset once.
    _saved_eq = _data.get("current", {}).get("eq", {})
    if isinstance(_saved_eq, dict) and _saved_eq:
        _gains = {f: float(_saved_eq.get(str(f), _saved_eq.get(f, _gains.get(f, 0.0)))) for f in BANDS}
    _output.parent.mkdir(parents=True, exist_ok=True)
    _output.write_text(eq_config_text(
        _target, _gains, preamp_db=effective_preamp_db(_data["current"]),
        settings=_data["current"], compatibility=is_bazzite()))
    sys.exit(0)

if "--restore" in sys.argv:
    _data = load_data()
    restore_at_login(_data)
    sys.exit(0)

if "--version" in sys.argv:
    print(VERSION)
    sys.exit(0)

if "--check" in sys.argv:
    d = load_data()
    gains, target = parse_eq_config()
    print(f"version={VERSION}")
    print(f"eq_config={EQ_CONFIG} exists={EQ_CONFIG.exists()}")
    print(f"fill_config={FILL_CONFIG} exists={FILL_CONFIG.exists()}")
    print(f"configured_target={d['current'].get('hardware_sink') or target}")
    print(f"soundblaster_zse_eq_present={sink_exists(SINK)}")
    print(f"default_sink={default_sink_name()}")
    print("routing_mode=wireplumber-smart-filter")
    sys.exit(0)

_instance_lock = acquire_single_instance()
if _instance_lock is None:
    sys.exit(0)

DATA = load_data()
try:
    ensure_configs(DATA)
except Exception:
    pass
CURRENT_EQ, CONFIG_TARGET = parse_eq_config()
if CONFIG_TARGET and not DATA["current"].get("hardware_sink"):
    DATA["current"]["hardware_sink"] = CONFIG_TARGET
    save_data(DATA)

ACTIVE_POSITIONS=sink_channel_positions(DATA["current"].get("hardware_sink", ""))
ACTIVE_LAYOUT=layout_name(ACTIVE_POSITIONS)
CHANNEL_KEYS=list(dict.fromkeys(channel_key_for_position(p) for p in ACTIVE_POSITIONS if channel_key_for_position(p)))

root = tk.Tk(className="SoundBlasterLinuxControl")
root.title(f"{APP_NAME} {VERSION}")
root.geometry("1240x920")
root.minsize(980, 700)
root.resizable(True, True)

style = ttk.Style()
try:
    style.theme_use("clam")
except Exception:
    pass

# Sound-Blaster-inspired dark panel using only Tk/ttk built-ins.
BG = "#15191d"
PANEL = "#20262b"
TEXT = "#eef2f4"
MUTED = "#aeb8bf"
ACCENT = "#00b8d4"
GOOD = "#2fbf71"
WARN = "#e2a52b"
BAD = "#e05252"
root.configure(bg=BG)
style.configure("TFrame", background=BG)
style.configure("Panel.TFrame", background=PANEL)
style.configure("TLabel", background=BG, foreground=TEXT)
style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
style.configure("TLabelframe", background=BG, foreground=TEXT)
style.configure("TLabelframe.Label", background=BG, foreground=TEXT)
style.configure("TNotebook", background=BG, borderwidth=0)
style.configure("TNotebook.Tab", padding=(14, 7))
style.configure("TButton", padding=(8, 5))
style.configure("Accent.TButton", padding=(10, 6))
style.configure("Active.TButton", padding=(8, 5), background=ACCENT, foreground="#061317")
style.map("Active.TButton", background=[("active", ACCENT), ("pressed", ACCENT)], foreground=[("active", "#061317")])
style.configure("TRadiobutton", background=BG, foreground=TEXT)
style.configure("TCheckbutton", background=BG, foreground=TEXT)

status_var = tk.StringVar(value="Starting…")
mute_state_var = tk.StringVar(value="Audio active")
preset_var = tk.StringVar(value=DATA["current"].get("last_preset", "Current"))
bypass_var = tk.BooleanVar(value=False)
safe_headroom_var = tk.BooleanVar(value=bool(DATA["current"].get("safe_headroom", True)))
auto_reconnect_var = tk.BooleanVar(value=bool(DATA["current"].get("auto_reconnect", True)))
connection_var = tk.StringVar(value="Checking audio path…")

gui_ready = False
live_eq_jobs = {}
auto_apply_job = None
spatial_live_job = None
auto_save_job = None
auto_apply_busy = False
last_reconnect_attempt = 0.0
custom_name_labels = {}
channel_sliders = {}
builtin_preset_buttons = {}
custom_recall_buttons = {}
speaker_test_buttons = {}
active_preset_key = None
analyzer_canvas = None
analyzer_status_var = tk.StringVar(value="Analyzer starting…")
analyzer_levels = [-70.0] * 28
analyzer_proc = None
analyzer_procs = []
analyzer_stop = threading.Event()
channel_meter_canvas = None
channel_meter_levels = {}
channel_meter_peaks = {}
ANALYZER_FREQS = [40.0 * math.pow(16000.0 / 40.0, i / 19.0) for i in range(20)]
ANALYZER_WINDOW = [0.5 - 0.5 * math.cos(2.0 * math.pi * i / 2047.0) for i in range(2048)]
ANALYZER_COEFFS = [2.0 * math.cos(2.0 * math.pi * f / 48000.0) for f in ANALYZER_FREQS]


def socket_listener():
    try:
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(SOCKET_PATH))
        server.listen(2)
        while True:
            conn, _ = server.accept()
            try:
                msg = conn.recv(128).decode(errors="ignore")
                if "RAISE" in msg:
                    root.after(0, raise_window)
            finally:
                conn.close()
    except Exception:
        pass


def raise_window():
    root.deiconify()
    root.lift()
    root.focus_force()


threading.Thread(target=socket_listener, daemon=True).start()


def slider_style(scale):
    scale.configure(bg=PANEL, fg=TEXT, troughcolor="#39434a", highlightthickness=0,
                    activebackground=ACCENT, bd=0)


def refresh_active_preset_buttons():
    for name, btn in builtin_preset_buttons.items():
        active = active_preset_key == f"builtin:{name}"
        btn.configure(style="Active.TButton" if active else "TButton", text=("● " if active else "") + name)
    for slot, btn in custom_recall_buttons.items():
        active = active_preset_key == f"custom:{slot}"
        name = DATA["custom_presets"][slot].get("name", f"Custom {slot}")
        btn.configure(style="Active.TButton" if active else "TButton", text=("● " if active else "") + name)


def set_active_preset(key, display_name):
    global active_preset_key
    active_preset_key = key
    preset_var.set(display_name)
    refresh_active_preset_buttons()


def mark_preset_modified():
    global active_preset_key
    if active_preset_key is not None:
        active_preset_key = None
        preset_var.set("Modified")
        refresh_active_preset_buttons()


def on_eq_slider(freq):
    mark_preset_modified()
    update_headroom_warning()
    schedule_live_eq(freq)


def on_preamp_slider(_=None):
    # Master Preamp is persistent global gain and is intentionally independent
    # of EQ presets. Moving it must not mark the active EQ preset as modified.
    apply_levels_live()


def on_channel_slider(_=None):
    # Speaker/channel trims are persistent room calibration and do not alter
    # the active EQ preset indicator. Keep the shared state current immediately
    # so the live meters can compensate for PipeWire sink-volume attenuation
    # without waiting for the delayed state-file save.
    try:
        for k in CHANNEL_KEYS:
            DATA["current"][k] = float(channel_sliders[k].get())
    except Exception:
        pass
    apply_levels_live()


def gui_settings():
    out = {
        "preamp": float(preamp.get()),
        "fill_mode": fill_mode.get(),
        "rear_delay": float(rear_delay.get()),
        "stereo_width": float(stereo_width.get()),
        "lfe_cutoff": int(lfe_cutoff.get()),
        "safe_headroom": bool(safe_headroom_var.get()),
        "auto_reconnect": bool(auto_reconnect_var.get()),
        "hardware_sink": DATA["current"].get("hardware_sink", ""),
        "last_preset": preset_var.get(),
        "eq": {str(f): float(eq_sliders[f].get()) for f in BANDS},
    }
    for k in CHANNEL_KEYS:
        out[k] = float(channel_sliders[k].get())
    return out


def save_current_state():
    if not gui_ready:
        return
    s = gui_settings()
    DATA["current"].update({k: v for k, v in s.items() if k != "eq"})
    DATA["current"]["eq"] = s["eq"]
    save_data(DATA)


def schedule_save(_=None):
    global auto_save_job
    if not gui_ready:
        return
    if auto_save_job is not None:
        try: root.after_cancel(auto_save_job)
        except Exception: pass
    auto_save_job = root.after(300, save_current_state)


def estimated_headroom():
    settings = gui_settings()
    eq_peak = combined_eq_peak_db(settings)
    effective = effective_preamp_db(settings, bypass_var.get())
    # Channel levels are attenuation-only (0..100%), so they cannot reduce
    # headroom and do not belong in the worst-case positive-gain estimate.
    return -(effective + eq_peak)


def update_headroom_warning(_=None):
    if not gui_ready:
        return
    settings = gui_settings()
    requested = float(settings.get("preamp", 0.0))
    effective = effective_preamp_db(settings, bypass_var.get())
    live_mult = read_live_preamp_mult()
    live_db = 20.0 * math.log10(live_mult) if live_mult is not None and live_mult > 0.0 else None
    if bypass_var.get():
        headroom_label.config(text="PROCESSING BYPASSED", fg=WARN)
        gain_detail_var.set("EQ and preamp are bypassed; channel levels are temporarily at 100%")
        return
    hr = estimated_headroom()
    if hr >= 3:
        headroom_label.config(text=f"EST. PEAK MARGIN {hr:.1f} dB", fg=GOOD)
    elif hr >= 0:
        headroom_label.config(text=f"EST. PEAK MARGIN {hr:.1f} dB", fg=WARN)
    else:
        headroom_label.config(text=f"EST. OVER 0 dBFS +{-hr:.1f} dB", fg=BAD)
    if safe_headroom_var.get() and effective < requested - 0.01:
        live_text = f" • live {live_db:+.1f} dB" if live_db is not None else " • live unavailable"
        gain_detail_var.set(
            f"Safe Headroom • requested {requested:+.1f} dB • target {effective:+.1f} dB{live_text} • estimate assumes a 0 dBFS source peak"
        )
    else:
        live_text = f" • live {live_db:+.1f} dB" if live_db is not None else ""
        gain_detail_var.set(
            f"Preamp {requested:+.1f} dB • target {effective:+.1f} dB{live_text} • estimate assumes a 0 dBFS source peak"
        )


def apply_levels_live(_=None):
    if not gui_ready:
        return
    settings = gui_settings()
    apply_preamp(settings, bypass_var.get())
    apply_channel_levels(settings, bypass_var.get())
    schedule_save()
    update_headroom_warning()


def schedule_live_eq(freq):
    if not gui_ready:
        return
    old = live_eq_jobs.get(freq)
    if old is not None:
        try: root.after_cancel(old)
        except Exception: pass
    def do_live():
        live_eq_jobs.pop(freq, None)
        gain = 0.0 if bypass_var.get() else float(eq_sliders[freq].get())
        if live_set_eq(freq, gain):
            if not bypass_var.get():
                persist_eq_gain(freq, float(eq_sliders[freq].get()))
            status_var.set(f"Live EQ: {freq} Hz {gain:+.1f} dB")
        else:
            status_var.set("Live EQ unavailable — reconnecting may be required")
        settings = gui_settings()
        apply_preamp(settings, bypass_var.get())
        apply_channel_levels(settings, bypass_var.get())
        schedule_save()
        update_headroom_warning()
    live_eq_jobs[freq] = root.after(100, do_live)


def apply_all_live_eq():
    for f in BANDS:
        gain = 0.0 if bypass_var.get() else float(eq_sliders[f].get())
        live_set_eq(f, gain)
        if not bypass_var.get():
            persist_eq_gain(f, float(eq_sliders[f].get()))


def toggle_bypass():
    apply_all_live_eq()
    settings = gui_settings()
    apply_preamp(settings, bypass_var.get())
    apply_channel_levels(settings, bypass_var.get())
    status_var.set("Processing bypass ON" if bypass_var.get() else "Processing bypass OFF")
    update_headroom_warning()


def reset_controls():
    if not messagebox.askyesno(APP_NAME, "Reset the 10-band EQ to Flat?\n\nMaster Preamp and speaker/channel calibration will be preserved.", parent=root):
        return
    for f in BANDS:
        eq_sliders[f].set(0.0)
    set_active_preset("builtin:Flat", "Flat")
    apply_all_live_eq(); apply_levels_live(); schedule_save(); update_headroom_warning()


def load_settings_into_gui(settings, name="Current"):
    if not settings:
        return
    settings = dict(settings)
    # Migrate custom presets made by the earlier paired center/rear version.
    if "center" in settings and "fc" not in settings:
        settings["fc"] = settings.get("center", 0.0)
    if "rear" in settings:
        settings.setdefault("rl", settings.get("rear", 0.0))
        settings.setdefault("rr", settings.get("rear", 0.0))
    eq = settings.get("eq", {})
    for f in BANDS:
        if str(f) in eq: eq_sliders[f].set(eq[str(f)])
    # Deliberately ignore any legacy preamp/channel/spatial values stored in
    # older custom presets. Master Preamp and room calibration are persistent
    # global settings, not part of EQ presets.
    # Deliberately ignore any legacy channel/spatial values stored in older
    # custom presets. Those are persistent room calibration, not preset data.
    preset_var.set(name)
    apply_all_live_eq(); apply_levels_live(); schedule_save(); update_headroom_warning()


def load_builtin(name):
    settings = dict(BUILTIN_PRESETS[name])
    # Built-ins alter only the 10-band EQ. Master Preamp, channel trims and
    # spatial calibration remain exactly as the user set them.
    load_settings_into_gui(settings, name)
    set_active_preset(f"builtin:{name}", name)
    status_var.set(f"Preset loaded: {name}")


def preset_settings():
    """Return only the 10-band EQ curve that belongs in a preset."""
    return {
        "eq": {str(f): float(eq_sliders[f].get()) for f in BANDS},
    }


def save_custom(slot):
    entry = DATA["custom_presets"][slot]
    name = simpledialog.askstring(APP_NAME, f"Name for preset {slot}:", initialvalue=entry.get("name"), parent=root)
    if name is None: return
    entry["name"] = name.strip() or f"Custom {slot}"
    entry["settings"] = preset_settings()
    save_data(DATA); refresh_preset_labels(); set_active_preset(f"custom:{slot}", entry["name"]); status_var.set(f"Saved preset: {entry['name']}")


def load_custom(slot):
    entry = DATA["custom_presets"][slot]
    if not entry.get("settings"):
        messagebox.showinfo(APP_NAME, f"Custom preset {slot} has not been saved yet.", parent=root); return
    display = entry.get("name", f"Custom {slot}")
    load_settings_into_gui(entry["settings"], display)
    set_active_preset(f"custom:{slot}", display)


def refresh_preset_labels():
    for slot, lbl in custom_name_labels.items():
        lbl.config(text=DATA["custom_presets"][slot].get("name", f"Custom {slot}"))
    for slot, btn in custom_recall_buttons.items():
        btn.config(text=DATA["custom_presets"][slot].get("name", f"Custom {slot}"))
    refresh_active_preset_buttons()


FILL_PROC = None
FILL_SIGNATURE = None

def playback_stream_node_ids():
    """Return application playback nodes for Ubuntu's v3.3.2 live fill path."""
    result = run(["pw-dump"], capture=True)
    if result.returncode != 0:
        return []
    try:
        objects = json.loads(result.stdout)
    except Exception:
        return []
    ids = []
    for obj in objects:
        try:
            props = obj.get("info", {}).get("props", {})
            if props.get("media.class") != "Stream/Output/Audio":
                continue
            if props.get("node.name") == OUTPUT_NODE:
                continue
            ids.append(int(obj["id"]))
        except Exception:
            pass
    return ids


def restart_pipewire_pulse_defaults():
    """Reload PipeWire-Pulse stream defaults without restarting PipeWire/WirePlumber.

    PipeWire-Pulse reads stream.properties from its drop-ins at process start.
    Updating the generated Speaker Fill file alone therefore leaves newly-created
    stereo streams on stale channelmix defaults until pipewire-pulse is restarted.
    """
    result = run(["systemctl", "--user", "restart", "pipewire-pulse"], capture=True)
    if result.returncode != 0:
        return False
    end = time.time() + 5.0
    while time.time() < end:
        probe = run(["pactl", "info"], capture=True)
        if probe.returncode == 0:
            return True
        time.sleep(0.15)
    return False


def live_set_spatial_ubuntu(settings):
    """Apply global channelmix controls to existing Ubuntu streams."""
    mode = settings.get("fill_mode", "PSD")
    upmix = "false" if mode == "OFF" else "true"
    method = "simple" if mode == "FULL" else "psd"
    payload = (
        '{ params = [ '
        f'"channelmix.upmix" {upmix} '
        f'"channelmix.upmix-method" "{method}" '
        f'"channelmix.rear-delay" {float(settings.get("rear_delay", 12.0)):.1f} '
        f'"channelmix.stereo-widen" {float(settings.get("stereo_width", 0.0)):.2f} '
        f'"channelmix.lfe-cutoff" {int(settings.get("lfe_cutoff", 150))} '
        '] }'
    )
    ok = False
    for node_id in playback_stream_node_ids():
        if run(["pw-cli", "s", str(node_id), "Props", payload], capture=True).returncode == 0:
            ok = True
    return ok


def _sink_id_name_map():
    result = run(["pactl", "list", "short", "sinks"], capture=True)
    out = {}
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                out[parts[0].strip()] = parts[1].strip()
    return out

def playback_sink_inputs():
    """Return playback streams with Pulse sink id/name and original channel count."""
    result = run(["pactl", "list", "sink-inputs"], capture=True)
    if result.returncode != 0:
        return []
    sink_names = _sink_id_name_map()
    streams = []
    chunks = re.split(r"(?=Sink Input #\d+)", result.stdout)
    for chunk in chunks:
        m_id = re.search(r"Sink Input #(\d+)", chunk)
        if not m_id:
            continue
        m_sink = re.search(r"^\s*Sink:\s*(\d+)\s*$", chunk, re.M)
        m_spec = re.search(r"^\s*Sample Specification:.*?\s(\d+)ch\s", chunk, re.M)
        m_node = re.search(r'^\s*node\.name\s*=\s*"([^"]+)"', chunk, re.M)
        m_app = re.search(r'^\s*application\.name\s*=\s*"([^"]+)"', chunk, re.M)
        if not (m_sink and m_spec):
            continue
        sid = m_sink.group(1)
        streams.append({
            "id": int(m_id.group(1)),
            "sink_id": sid,
            "sink": sink_names.get(sid, ""),
            "channels": int(m_spec.group(1)),
            "node": m_node.group(1) if m_node else "",
            "app": m_app.group(1) if m_app else "",
        })
    return streams

def _fill_signature(settings):
    mode = settings.get("fill_mode", "PSD")
    return (mode, float(settings.get("rear_delay", 12.0)),
            float(settings.get("stereo_width", 0.0)),
            int(settings.get("lfe_cutoff", 150)))

def _kill_external_fill_loopback():
    """Stop only our named pw-loopback instance, including one from an older GUI."""
    result = run(["pgrep", "-f", rf"pw-loopback.*{FILL_LOOP_NAME}"], capture=True)
    if result.returncode == 0:
        for text in result.stdout.split():
            try:
                pid = int(text)
                if pid != os.getpid():
                    os.kill(pid, signal.SIGTERM)
            except Exception:
                pass

def stop_fill_loopback(move_streams=True):
    """Emergency/exit cleanup only. Normal mode changes never destroy the fill sink."""
    global FILL_PROC, FILL_SIGNATURE
    if move_streams and sink_exists(SINK):
        for stream in playback_sink_inputs():
            if stream["sink"] == FILL_SINK:
                run(["pactl", "move-sink-input", str(stream["id"]), SINK], capture=True)
    if FILL_PROC is not None and FILL_PROC.poll() is None:
        try:
            FILL_PROC.terminate(); FILL_PROC.wait(timeout=1.5)
        except Exception:
            try: FILL_PROC.kill()
            except Exception: pass
    _kill_external_fill_loopback()
    FILL_PROC = None
    FILL_SIGNATURE = None

def _fill_output_id():
    """Return the PipeWire object id for our persistent fill playback stream."""
    result = run(["pw-dump"], capture=True)
    if result.returncode != 0:
        return None
    try:
        objects = json.loads(result.stdout)
    except Exception:
        return None
    for obj in objects:
        info = obj.get("info", {}) if isinstance(obj, dict) else {}
        props = info.get("props", {}) if isinstance(info, dict) else {}
        if props.get("node.name") == FILL_OUTPUT_NODE:
            try: return int(obj.get("id"))
            except Exception: return None
    return None

def update_fill_processing(settings):
    """Change fill mode in-place so active browser/media streams never change sinks."""
    node_id = _fill_output_id()
    if node_id is None:
        return False
    mode = settings.get("fill_mode", "PSD")
    enabled = mode != "OFF"
    method = "simple" if mode == "FULL" else "psd"
    # PipeWire exposes channel-mixer controls in the node Props parameter.
    # Updating this adapter in-place avoids destroying the virtual sink and
    # therefore avoids Pulse clients interpreting a sink move as a pause.
    pod = ('{ params = [ '
           f'"channelmix.upmix" {str(enabled).lower()} '
           f'"channelmix.upmix-method" "{method}" '
           f'"channelmix.rear-delay" {float(settings.get("rear_delay",12.0)):.1f} '
           f'"channelmix.stereo-widen" {float(settings.get("stereo_width",0.0)):.2f} '
           f'"channelmix.lfe-cutoff" {int(settings.get("lfe_cutoff",150))} '
           '] }')
    r = run(["pw-cli", "set-param", str(node_id), "Props", pod], capture=True)
    return r.returncode == 0

def start_fill_loopback(settings, force_restart=False):
    """Create one persistent 2-channel virtual sink feeding the 5.1 EQ."""
    global FILL_PROC, FILL_SIGNATURE
    if not shutil.which("pw-loopback") or not sink_exists(SINK):
        return False
    if sink_exists(FILL_SINK) and not force_restart:
        FILL_SIGNATURE = _fill_signature(settings)
        return update_fill_processing(settings)
    if sink_exists(FILL_SINK) or force_restart:
        stop_fill_loopback(move_streams=True)
        time.sleep(0.15)
    mode = settings.get("fill_mode", "PSD")
    enabled = mode != "OFF"
    method = "simple" if mode == "FULL" else "psd"
    capture_props = (
        '{ node.name = "' + FILL_SINK + '" '
        'node.description = "Sound Blaster Stereo Speaker Fill" '
        'media.class = "Audio/Sink" node.virtual = true '
        'audio.channels = 2 audio.position = [ FL FR ] }'
    )
    playback_props = (
        '{ node.name = "' + FILL_OUTPUT_NODE + '" '
        'node.description = "Sound Blaster Stereo Fill 5.1 Output" '
        'node.passive = true stream.dont-remix = true '
        'audio.channels = 6 audio.position = [ FL FR RL RR FC LFE ] '
        f'channelmix.upmix = {str(enabled).lower()} '
        f'channelmix.upmix-method = "{method}" '
        f'channelmix.rear-delay = {float(settings.get("rear_delay",12.0)):.1f} '
        f'channelmix.stereo-widen = {float(settings.get("stereo_width",0.0)):.2f} '
        f'channelmix.lfe-cutoff = {int(settings.get("lfe_cutoff",150))} }}'
    )
    try:
        FILL_PROC = subprocess.Popen([
            "pw-loopback", "--name=" + FILL_LOOP_NAME,
            "--playback=" + SINK,
            "--capture-props=" + capture_props,
            "--playback-props=" + playback_props,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        FILL_PROC = None
        return False
    if not wait_for_sink(FILL_SINK, 4):
        stop_fill_loopback(move_streams=False)
        return False
    FILL_SIGNATURE = _fill_signature(settings)
    # Best effort: creation props already contain the requested mode.
    update_fill_processing(settings)
    return True

def route_speaker_fill_streams(settings, force_restart=False):
    """Keep stereo applications on one stable fill sink for OFF/PSD/FULL.

    The fill sink always exists while the GUI is active. OFF simply disables
    upmix in-place, leaving stereo on FL/FR; PSD/FULL enable upmix in-place.
    Native multichannel streams never enter this 2-channel sink.
    """
    if not start_fill_loopback(settings, force_restart=force_restart):
        return False
    ok = update_fill_processing(settings)
    for stream in playback_sink_inputs():
        if stream["node"] in (OUTPUT_NODE, FILL_OUTPUT_NODE):
            continue
        if stream["channels"] == 2:
            if stream["sink"] != FILL_SINK:
                r = run(["pactl", "move-sink-input", str(stream["id"]), FILL_SINK], capture=True)
                ok = ok and r.returncode == 0
        elif stream["sink"] == FILL_SINK and sink_exists(SINK):
            run(["pactl", "move-sink-input", str(stream["id"]), SINK], capture=True)
    return ok

def live_set_spatial(settings):
    """Apply the distro-specific, hardware-verified Speaker Fill path."""
    if is_bazzite():
        return route_speaker_fill_streams(settings, force_restart=False)
    return live_set_spatial_ubuntu(settings)

def _apply_spatial_live():
    global spatial_live_job
    spatial_live_job = None
    if not gui_ready or auto_apply_busy:
        return
    try:
        s = gui_settings()
        previous_text = ""
        try:
            previous_text = FILL_CONFIG.read_text()
        except Exception:
            pass
        new_text = fill_config_text(s)
        # Persist defaults first. On Ubuntu, PipeWire-Pulse only reads these
        # stream.properties at process start, so a changed file must be followed
        # by a PipeWire-Pulse-only refresh. This fixes stale upmix=true/simple
        # settings surviving after the GUI has already switched Speaker Fill OFF.
        write_spatial(s)
        save_current_state()
        refreshed = False
        if not is_bazzite() and previous_text != new_text:
            refreshed = restart_pipewire_pulse_defaults()
        live_ok = live_set_spatial(s)
        if is_bazzite():
            if live_ok:
                # Preserve v3.3.15: fill path updates can trigger session-state
                # restoration, so reassert persistent DSP/calibration values.
                apply_preamp(s, bypass_var.get())
                apply_channel_levels(s, bypass_var.get())
                status_var.set("Stereo Speaker Fill updated live" if s.get("fill_mode") != "OFF" else "Speaker Fill off — native channels discrete")
            else:
                status_var.set("Spatial defaults saved — new streams will use them")
        else:
            # A Pulse restart can recreate sink/session volume state. Reassert the
            # saved calibration and effective Safe Headroom after the refresh.
            if refreshed:
                apply_preamp(s, bypass_var.get())
                apply_channel_levels(s, bypass_var.get())
                activate_eq_route(move_existing=False)
                status_var.set("Spatial / Fill applied — PipeWire-Pulse defaults refreshed")
            elif live_ok:
                status_var.set("Spatial / Fill updated live")
            else:
                status_var.set("Spatial defaults saved — PipeWire-Pulse refresh failed")
    except Exception as e:
        status_var.set(f"Live spatial update failed: {e}")


def schedule_spatial_apply(_=None):
    global spatial_live_job
    if not gui_ready or auto_apply_busy:
        return
    if spatial_live_job is not None:
        try: root.after_cancel(spatial_live_job)
        except Exception: pass
    # Small debounce keeps slider drags smooth while still feeling immediate.
    spatial_live_job = root.after(90, _apply_spatial_live)


def toggle_mute():
    new_state = not get_sink_mute(SINK)
    set_sink_mute(new_state, SINK)
    update_mute_button()
    status_var.set("Audio muted" if new_state else "Audio active")


def update_mute_button():
    muted = get_sink_mute(SINK)
    mute_button.config(text="UNMUTE" if muted else "MUTE")
    mute_state_var.set("Muted" if muted else "Audio active")


def restore_gui_audio_state():
    """Restore saved runtime gain state on every normal GUI launch.

    The login --restore path already verifies channel trims.  Normal GUI
    startup must do the same, otherwise Tk sliders can show saved values while
    the live PipeWire sink remains at unity.  Safe Headroom is also asserted
    immediately so a stale/requested preamp cannot clip until the user toggles
    the checkbox.
    """
    settings = dict(DATA.get("current", {}))
    if not wait_for_sink(SINK, 12):
        restore_log("GUI startup restore skipped: EQ sink unavailable")
        return
    eq_ok = restore_live_eq_verified(settings, attempts=10)
    apply_bass_management_live(settings)
    channels_ok = restore_channel_levels_verified(settings, attempts=4)
    # Apply and verify Safe Headroom last; do not report success based only on
    # the calculated target or on an earlier transient write.
    preamp_ok = restore_preamp_verified(settings, attempts=8, persist=True)
    target_mult = math.pow(10.0, effective_preamp_db(settings) / 20.0)
    final_mult = read_live_preamp_mult()
    if preamp_ok and (final_mult is None or abs(final_mult - target_mult) > 0.0005):
        restore_log(f"headroom final GUI readback FAILED target_mult={target_mult:.8f} live_mult={final_mult if final_mult is not None else 'unavailable'}")
        preamp_ok = False
    preamp_state = live_preamp_status(settings, final_mult)
    try:
        root.after(0, lambda: update_headroom_warning())
        if preamp_ok and channels_ok and eq_ok:
            root.after(0, lambda: status_var.set("Saved EQ, channel levels and Safe Headroom restored"))
        elif not eq_ok:
            root.after(0, lambda: status_var.set("Saved EQ restore incomplete • audio controls restored"))
        elif not preamp_ok:
            root.after(0, lambda s=preamp_state: status_var.set(f"Safe Headroom NOT LIVE • {s}"))
        else:
            root.after(0, lambda: status_var.set("Safe Headroom verified • channel calibration restore incomplete"))
    except Exception:
        pass


def speaker_test_backend():
    """Return an ALSA PCM usable by speaker-test without distro assumptions."""
    result = run(["aplay", "-L"], capture=True)
    names = {line.strip() for line in result.stdout.splitlines() if line and not line[:1].isspace()} if result.returncode == 0 else set()
    if "pipewire" in names:
        return "pipewire"
    if "pulse" in names:
        return "pulse"
    return "default"


def test_speaker(channel):
    if not shutil.which("speaker-test"):
        messagebox.showerror(APP_NAME, "speaker-test is missing. Install alsa-utils.", parent=root); return
    aliases={"SL":"RL","SR":"RR"}; wanted=aliases.get(channel,channel)
    normalized=[aliases.get(p,p) for p in ACTIVE_POSITIONS]
    if wanted not in normalized: return
    if is_bazzite():
        # Preserve the hardware-verified Bazzite PipeWire mapping unchanged.
        backend = speaker_test_backend()
        if backend == "pipewire":
            speaker_numbers={"FL":1,"FR":3,"RL":5,"RR":4,"FC":2,"LFE":6}
        else:
            speaker_numbers={"FL":1,"FR":2,"RL":3,"RR":4,"FC":5,"LFE":6}
        number=speaker_numbers.get(wanted)
    else:
        # Ubuntu Pulse speaker-test uses ALSA's verified fixed selection order,
        # which is independent of PipeWire's FL FR RL RR FC LFE port order.
        target = DATA["current"].get("hardware_sink", SINK)
        if target and sink_exists(target):
            set_default_sink(target)
        backend = "pulse"
        speaker_numbers={"FL":1,"FC":2,"FR":3,"RR":4,"RL":5,"LFE":6}
        number=speaker_numbers.get(wanted)
    if number is None: return
    btn = speaker_test_buttons.get(channel)
    if btn:
        btn.configure(bg=ACCENT, fg="#061317", activebackground=ACCENT)
        root.after(1400, lambda b=btn: b.configure(bg=PANEL, fg=TEXT, activebackground="#39434a"))
    env = os.environ.copy()
    subprocess.Popen(["speaker-test", "-D", backend, "-c", str(len(ACTIVE_POSITIONS)), "-t", "sine", "-f", "700", "-s", str(number), "-l", "1"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def refresh_device_list():
    vals = [s for s in list_sinks() if s not in (SINK, FILL_SINK)]
    device_combo["values"] = vals
    current = DATA["current"].get("hardware_sink", "")
    if current in vals: device_var.set(current)
    elif vals and not device_var.get(): device_var.set(vals[0])


def apply_device_target():
    target = device_var.get().strip()
    if not target: return
    if not messagebox.askyesno(APP_NAME, f"Route the Sound Blaster EQ to:\n\n{target}\n\nPipeWire will restart once.", parent=root): return
    try:
        configure_target(DATA, target)
        restart_audio(DATA["current"].get("hardware_sink")); apply_channel_levels(gui_settings(), bypass_var.get()); apply_all_live_eq()
        status_var.set("Hardware output updated")
    except Exception as e:
        messagebox.showerror(APP_NAME, str(e), parent=root)


def reconnect_now(silent=False):
    """Manual EQ-only recovery.

    Never restarts the desktop PipeWire/WirePlumber stack on Bazzite.  The
    physical AC3 sink is a safe fallback and must remain uninterrupted when
    the optional EQ client is unavailable.
    """
    global last_reconnect_attempt
    last_reconnect_attempt = time.time()
    try:
        ensure_configs(DATA)
        target = DATA["current"].get("hardware_sink")
        if is_bazzite():
            if target and not sink_exists(target):
                raise RuntimeError(f"AC3 5.1 fallback target '{target}' is unavailable")
            result = run(["systemctl", "--user", "restart", "filter-chain.service"], capture=True)
            if result.returncode != 0:
                raise RuntimeError("EQ service retry failed: " + (result.stderr.strip() or "unknown error"))
            if not wait_for_sink(SINK, 8):
                raise RuntimeError("EQ service did not create the Sound Blaster EQ node; AC3 5.1 fallback remains active")
            if target and sink_exists(target):
                set_default_sink(target)
        else:
            restart_audio(target)
        apply_channel_levels(gui_settings(), bypass_var.get())
        apply_all_live_eq()
        if not silent:
            status_var.set("EQ path connected")
        return True
    except Exception as e:
        if not silent:
            status_var.set(f"EQ retry failed: {e}")
        return False


def update_connection_status():
    global last_reconnect_attempt
    eq_ok = sink_exists(SINK)
    target = DATA["current"].get("hardware_sink", "")
    hw_ok = bool(target and sink_exists(target))
    default_ok = bool(target and default_sink_name() == target)
    if eq_ok and hw_ok:
        connection_dot.config(fg=GOOD)
        if is_bazzite():
            route_state = "default EQ route" if default_sink_name() == SINK else "EQ route available"
            connection_var.set(f"EQ active • {route_state} • {target}")
        else:
            route_state = "default target" if default_ok else "available target"
            connection_var.set(f"Smart EQ active • {route_state} • {target}")
    elif eq_ok:
        connection_dot.config(fg=WARN)
        connection_var.set("EQ sink active • hardware target unavailable")
    else:
        if hw_ok:
            connection_dot.config(fg=WARN)
            if is_bazzite():
                connection_var.set("EQ unavailable • AC3 5.1 fallback active")
            else:
                connection_var.set("Sound Blaster EQ unavailable • hardware output active")
        else:
            connection_dot.config(fg=BAD)
            connection_var.set("Sound Blaster EQ and hardware target unavailable")
        # v3.3.8 safety rule: never auto-restart PipeWire/WirePlumber or the
        # EQ service from this polling loop. Recovery is explicitly user-driven.
    # Only Bazzite uses the persistent v3.3.15 fill sink and stream mover.
    if is_bazzite():
        try:
            if eq_ok:
                route_speaker_fill_streams(DATA["current"], force_restart=False)
        except Exception:
            pass
    root.after(1500, update_connection_status)


def analyzer_source_name():
    """Return the final physical sink monitor used for Live Output Levels.

    v3.3.31 deliberately meters the hardware sink monitor, not the virtual EQ
    sink monitor.  The physical monitor sits after the filter graph and after
    generated LFE/center/rear content, so its six discrete ports correspond to
    what is actually being sent toward the AC3 output.  Direct PipeWire capture
    (pw-record) is used below to avoid the Pulse compatibility layer remixing
    or inventing channels for the meter stream.
    """
    sources = []
    result = run(["pactl", "list", "short", "sources"], capture=True)
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                sources.append(parts[1])
    target = DATA["current"].get("hardware_sink", "")
    candidate = f"{target}.monitor" if target else ""
    if candidate and candidate in sources:
        return candidate
    fallback = f"{SINK}.monitor"
    if fallback in sources:
        return fallback
    return ""

def goertzel_db(samples, coeff):
    n = min(len(samples), len(ANALYZER_WINDOW))
    if n < 32:
        return -70.0
    q0 = q1 = q2 = 0.0
    for i in range(n):
        q0 = coeff * q1 - q2 + (samples[i] / 32768.0) * ANALYZER_WINDOW[i]
        q2, q1 = q1, q0
    power = q1 * q1 + q2 * q2 - coeff * q1 * q2
    mag = max(1e-9, math.sqrt(max(0.0, power)) / (n * 0.25))
    return max(-70.0, min(0.0, 20.0 * math.log10(mag)))


def pulse_channel_map(positions):
    names = {
        "FL": "front-left", "FR": "front-right", "FC": "front-center",
        "LFE": "lfe", "RL": "rear-left", "RR": "rear-right",
        "SL": "side-left", "SR": "side-right",
    }
    return ",".join(names.get(p, p.lower()) for p in positions)


def source_channel_info(source):
    """Return (semantic positions, native Pulse channel-map names).

    The analyzer must request exactly the monitor source's own channel count and
    channel map.  Asking for the GUI order can make Pulse/PipeWire remix the
    monitor, while omitting the sample spec leaves parec free to choose a
    default map that does not necessarily match the source.
    """
    result = run(["pactl", "list", "sources"], capture=True)
    if result.returncode != 0:
        return [], []
    reverse = {
        "front-left": "FL", "front-right": "FR", "front-center": "FC",
        "lfe": "LFE", "rear-left": "RL", "rear-right": "RR",
        "side-left": "SL", "side-right": "SR",
    }
    for chunk in re.split(r"(?=Source #\d+)", result.stdout):
        m_name = re.search(r"^\s*Name:\s*(\S+)\s*$", chunk, re.M)
        if not m_name or m_name.group(1) != source:
            continue
        m_map = re.search(r"^\s*Channel Map:\s*(.+?)\s*$", chunk, re.M)
        if not m_map:
            return [], []
        native_names = [name.strip().lower() for name in m_map.group(1).split(',') if name.strip()]
        positions = [reverse.get(name, name.upper()) for name in native_names]
        return positions, native_names
    return [], []


def source_channel_positions(source):
    """Compatibility wrapper returning only semantic channel positions."""
    positions, _ = source_channel_info(source)
    return positions

def reorder_meter_levels(levels, source_positions, display_positions):
    by_pos = dict(zip(source_positions, levels))
    return [by_pos.get(pos, -60.0) for pos in display_positions]


def meter_db_after_channel_level(db, percent):
    """Apply the OS-style sink channel level to a pre-volume monitor reading."""
    try:
        pct = max(0.0, min(100.0, float(percent)))
        base = float(db)
    except Exception:
        return -60.0
    if pct <= 0.0:
        return -60.0
    return max(-60.0, min(0.0, base + 20.0 * math.log10(pct / 100.0)))


def meter_levels_after_channel_controls(levels, positions, settings):
    out = []
    for db, pos in zip(levels, positions):
        key = channel_key_for_position(pos)
        pct = settings.get(key, 100.0) if key else 100.0
        out.append(meter_db_after_channel_level(db, pct))
    return out


def update_channel_meters(rms_levels, peak_levels):
    global channel_meter_levels, channel_meter_peaks
    channel_meter_levels = dict(zip(ACTIVE_POSITIONS, rms_levels))
    channel_meter_peaks = dict(zip(ACTIVE_POSITIONS, peak_levels))
    c = channel_meter_canvas
    if c is None or not c.winfo_exists():
        return
    w=max(260,c.winfo_width()); h=max(125,c.winfo_height())
    c.delete("all")
    positions=ACTIVE_POSITIONS[:6]
    if not positions: return
    left=34; right=10; top=14; bottom=24
    usable_w=max(1,w-left-right)
    barw=min(26,max(14,int(usable_w/(len(positions)*2.2))))
    for db in (0,-12,-24,-36,-48,-60):
        y=top+(-db/60.0)*(h-top-bottom)
        c.create_line(left,y,w-right,y,fill="#203039",width=1)
        c.create_text(left-5,y,text=str(db),fill=MUTED,anchor="e",font=("Arial",7))
    shorts={"FL":"FL","FR":"FR","FC":"C","LFE":"LFE","RL":"RL","RR":"RR","SL":"SL","SR":"SR"}
    for i,pos in enumerate(positions):
        cx=left+(i+0.5)*usable_w/len(positions)
        x0=cx-barw/2; x1=cx+barw/2
        # dark meter well
        c.create_rectangle(x0,top,x1,h-bottom,fill="#091217",outline=BORDER)
        db=max(-60.0,min(0.0,float(channel_meter_levels.get(pos,-60.0))))
        peak=max(-60.0,min(0.0,float(channel_meter_peaks.get(pos,-60.0))))
        y=top+(-db/60.0)*(h-top-bottom)
        # segmented-looking three-color meter based on current level
        zero_y=top
        red_y=top+(6/60.0)*(h-top-bottom)       # -6 dB
        yellow_y=top+(18/60.0)*(h-top-bottom)  # -18 dB
        base=h-bottom
        if y < base:
            # green portion -60..-18
            gy=max(y,yellow_y)
            if gy < base: c.create_rectangle(x0+3,gy,x1-3,base-2,fill="#32c76a",outline="")
            # yellow portion -18..-6
            yy=max(y,red_y)
            if yy < yellow_y: c.create_rectangle(x0+3,yy,x1-3,yellow_y,fill="#f0c62e",outline="")
            # red portion -6..0
            if y < red_y: c.create_rectangle(x0+3,y,x1-3,red_y,fill="#ef3e3e",outline="")
        py=top+(-peak/60.0)*(h-top-bottom)
        c.create_line(x0-2,py,x1+2,py,fill="#f4f7f8",width=1)
        c.create_text(cx,5,text=shorts.get(pos,pos),fill=TEXT,anchor="n",font=("Arial",8,"bold"))
        c.create_text(cx,h-12,text=f"{db:.1f}",fill=ACCENT2,anchor="center",font=("Arial",7,"bold"))


def _wait_for_pw_mono_port(node_name, timeout=2.0):
    """Wait until one mono pw-record node exposes its input_MONO port."""
    deadline = time.monotonic() + timeout
    wanted = f"{node_name}:input_MONO"
    while time.monotonic() < deadline and not analyzer_stop.is_set():
        result = run(["pw-link", "-i"], capture=True)
        if result.returncode == 0:
            available = {line.strip() for line in result.stdout.splitlines() if line.strip()}
            if wanted in available:
                return True
        time.sleep(0.05)
    return False


def _start_physical_port_meter(hardware_sink, pos, index):
    """Start one mono recorder linked to exactly one physical monitor port."""
    node_name = f"soundblaster-zse-meter-{os.getpid()}-{index}-{pos.lower()}"
    proc = subprocess.Popen(
        ["pw-record", "--raw", "--target=0", "-P", f"node.name={node_name}",
         "--format=s16", "--rate=48000", "--channels=1", "--channel-map=MONO",
         "--latency=80ms", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
    )
    if not _wait_for_pw_mono_port(node_name):
        detail = ""
        if proc.poll() is not None and proc.stderr:
            try:
                detail = proc.stderr.read().decode(errors="replace").strip()
            except Exception:
                detail = ""
        try:
            proc.terminate()
        except Exception:
            pass
        raise RuntimeError(detail or f"pw-record mono input did not appear for {pos}")
    output_port = f"{hardware_sink}:monitor_{pos}"
    input_port = f"{node_name}:input_MONO"
    result = run(["pw-link", output_port, input_port], capture=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "pw-link failed").strip()
        try:
            proc.terminate()
        except Exception:
            pass
        raise RuntimeError(f"Could not link {pos} meter port: {detail}")
    if proc.stdout:
        try:
            os.set_blocking(proc.stdout.fileno(), False)
        except (AttributeError, OSError):
            pass
    return node_name, proc


def _stop_analyzer_processes():
    """Terminate every per-channel recorder used by the analyzer."""
    global analyzer_proc, analyzer_procs
    procs = list(analyzer_procs)
    if analyzer_proc is not None and analyzer_proc not in procs:
        procs.append(analyzer_proc)
    for proc in procs:
        try:
            proc.terminate()
        except Exception:
            pass
    for proc in procs:
        try:
            proc.wait(timeout=0.4)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    analyzer_proc = None
    analyzer_procs = []


def analyzer_worker():
    global analyzer_proc, analyzer_procs
    if shutil.which("pw-record") is None or shutil.which("pw-link") is None:
        root.after(0, lambda: analyzer_status_var.set("Analyzer unavailable • install PipeWire tools (pw-record/pw-link)"))
        return
    while not analyzer_stop.is_set():
        source = analyzer_source_name()
        if not source:
            root.after(0, lambda: analyzer_status_var.set("Analyzer waiting for an audio monitor…"))
            time.sleep(1.5)
            continue
        hardware_sink = DATA["current"].get("hardware_sink", "")
        if not hardware_sink or source != f"{hardware_sink}.monitor":
            root.after(0, lambda: analyzer_status_var.set("Analyzer waiting for physical Sound Blaster monitor…"))
            time.sleep(1.0)
            continue
        display_positions = ACTIVE_POSITIONS[:6]
        if not display_positions:
            time.sleep(1.0)
            continue
        try:
            # v3.3.33: meter each hardware monitor port with its own mono
            # pw-record stream. This is the exact topology verified manually on
            # Ubuntu/PipeWire 1.6.2: stereo + Fill Off produced FL/FR signal and
            # true digital silence on RL/RR/FC/LFE. A single 6-channel recorder
            # was proven to cross-feed channels even when explicitly linked.
            recorders = {}
            analyzer_procs = []
            for index, pos in enumerate(display_positions):
                _node_name, proc = _start_physical_port_meter(hardware_sink, pos, index)
                recorders[pos] = proc
                analyzer_procs.append(proc)
            analyzer_proc = analyzer_procs[0] if analyzer_procs else None
            root.after(0, lambda s=hardware_sink: analyzer_status_var.set(
                f"Live physical output • isolated PipeWire port meters • {s}"))

            smoothed = [-70.0] * len(ANALYZER_FREQS)
            meter_smoothed = [-60.0] * len(display_positions)
            peak_hold = [-60.0] * len(display_positions)
            byte_buffers = {pos: bytearray() for pos in display_positions}
            sample_buffers = {pos: [] for pos in display_positions}

            while not analyzer_stop.is_set():
                alive = False
                got_data = False
                for pos in display_positions:
                    proc = recorders[pos]
                    if proc.poll() is None:
                        alive = True
                    if not proc.stdout:
                        continue
                    try:
                        chunk = os.read(proc.stdout.fileno(), 8192)
                    except BlockingIOError:
                        chunk = b""
                    except OSError:
                        chunk = b""
                    if chunk:
                        got_data = True
                        byte_buffers[pos].extend(chunk)
                        even = len(byte_buffers[pos]) - (len(byte_buffers[pos]) % 2)
                        if even:
                            values = array.array("h")
                            values.frombytes(byte_buffers[pos][:even])
                            del byte_buffers[pos][:even]
                            if sys.byteorder != "little":
                                values.byteswap()
                            sample_buffers[pos].extend(values.tolist())
                            # Keep enough history for stable meters/spectrum while
                            # bounding memory if the GUI thread is briefly busy.
                            if len(sample_buffers[pos]) > 8192:
                                del sample_buffers[pos][:-8192]
                if not alive:
                    break
                if not got_data:
                    time.sleep(0.01)
                    continue
                if not any(len(sample_buffers[pos]) >= 512 for pos in display_positions):
                    continue

                rms_display = []
                peaks_display = []
                channel_windows = []
                for pos in display_positions:
                    seq = sample_buffers[pos][-2048:]
                    channel_windows.append(seq)
                    if not seq:
                        rms_display.append(-60.0)
                        peaks_display.append(-60.0)
                        continue
                    sumsq = sum(float(v) * float(v) for v in seq) / len(seq)
                    r = max(1e-9, math.sqrt(sumsq) / 32768.0)
                    pk = max(1, max(abs(v) for v in seq)) / 32768.0
                    rms_display.append(max(-60.0, min(0.0, 20.0 * math.log10(r))))
                    peaks_display.append(max(-60.0, min(0.0, 20.0 * math.log10(pk))))

                meter_smoothed = [max(n, o * 0.72 + n * 0.28) for o, n in zip(meter_smoothed, rms_display)]
                peak_hold = [max(n, p - 0.8) for p, n in zip(peak_hold, peaks_display)]

                # Combined spectrum from the same isolated physical outputs.
                nonempty = [seq for seq in channel_windows if seq]
                if nonempty:
                    n = min(len(seq) for seq in nonempty)
                    n = min(n, 2048)
                    samples = [int(sum(seq[-n + i] for seq in nonempty) / len(nonempty)) for i in range(n)] if n else []
                    levels = [goertzel_db(samples, c) for c in ANALYZER_COEFFS]
                    smoothed = [max(new, old * 0.78 + new * 0.22) for old, new in zip(smoothed, levels)]
                    root.after(0, lambda vals2=smoothed[:]: update_analyzer_canvas(vals2))
                root.after(0, lambda r=meter_smoothed[:], p=peak_hold[:]: update_channel_meters(r, p))
        except Exception as exc:
            message = str(exc).strip() or exc.__class__.__name__
            root.after(0, lambda m=message: analyzer_status_var.set(f"Analyzer error • {m}"))
        finally:
            _stop_analyzer_processes()
        if not analyzer_stop.is_set():
            time.sleep(1.0)

def update_analyzer_canvas(levels):
    global analyzer_levels
    analyzer_levels = levels
    if analyzer_canvas is None or not analyzer_canvas.winfo_exists():
        return
    c = analyzer_canvas
    w = max(200, c.winfo_width())
    h = max(140, c.winfo_height())
    c.delete("all")
    # Reference lines: 0, -20, -40, -60 dBFS.
    for db in (0, -20, -40, -60):
        y = 8 + (-db / 70.0) * (h - 30)
        c.create_line(30, y, w - 8, y, fill="#39434a")
        c.create_text(26, y, text=str(db), fill=MUTED, anchor="e", font=("Arial", 8))
    usable_w = max(1, w - 42)
    gap = 2
    bw = max(2, usable_w / len(levels) - gap)
    for i, db in enumerate(levels):
        x0 = 34 + i * usable_w / len(levels)
        x1 = x0 + bw
        y0 = h - 18
        y1 = 8 + (-db / 70.0) * (h - 30)
        c.create_rectangle(x0, y1, x1, y0, fill=ACCENT, outline="")
    for freq, label in ((50, "50"), (200, "200"), (1000, "1k"), (4000, "4k"), (16000, "16k")):
        pos = math.log(freq / 40.0) / math.log(16000.0 / 40.0)
        x = 34 + pos * usable_w
        c.create_text(x, h - 7, text=label, fill=MUTED, anchor="center", font=("Arial", 8))


def start_analyzer():
    threading.Thread(target=analyzer_worker, daemon=True).start()


def on_safe_toggle():
    DATA["current"]["safe_headroom"] = bool(safe_headroom_var.get()); save_data(DATA)
    apply_levels_live()
    status_var.set("Safe Headroom ON" if safe_headroom_var.get() else "Safe Headroom OFF — requested preamp restored")
    update_headroom_warning()


def on_reconnect_toggle():
    DATA["current"]["auto_reconnect"] = bool(auto_reconnect_var.get()); save_data(DATA)


def on_close():
    analyzer_stop.set()
    _stop_analyzer_processes()
    save_current_state()
    try:
        if SOCKET_PATH.exists(): SOCKET_PATH.unlink()
    except Exception: pass
    root.destroy()


# Header / unified dark visual system
root.geometry("1380x1030")
root.minsize(1120, 760)

# A restrained Creative/Sound-Blaster-inspired palette.  All tabs share these
# styles so the utility looks like one application instead of separate forms.
BG = "#050b0f"
CARD = "#091219"
PANEL = "#0d1820"
PANEL2 = "#12222c"
BORDER = "#263b49"
TEXT = "#f5f8fa"
MUTED = "#a8bbc8"
ACCENT = "#159fe8"
ACCENT2 = "#53c2ff"
GOOD = "#39d27d"
WARN = "#f0b33c"
BAD = "#ff5757"
root.configure(bg=BG)

style.configure("TFrame", background=BG)
style.configure("Card.TFrame", background=CARD)
style.configure("Panel.TFrame", background=PANEL)
style.configure("TLabel", background=BG, foreground=TEXT)
style.configure("Card.TLabel", background=CARD, foreground=TEXT)
style.configure("Muted.TLabel", background=CARD, foreground=MUTED)
style.configure("Status.TLabel", background=BG, foreground=MUTED)
style.configure("TLabelframe", background=CARD, foreground=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, relief="solid")
style.configure("TLabelframe.Label", background=CARD, foreground=TEXT, font=("Arial", 10, "bold"))
style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT, padding=(16, 9), borderwidth=1)
style.map("TNotebook.Tab", background=[("selected", CARD), ("active", PANEL2)], foreground=[("selected", TEXT)])
style.configure("TButton", background=PANEL2, foreground=TEXT, padding=(10, 6), borderwidth=1)
style.map("TButton", background=[("active", "#263a47"), ("pressed", "#0f6fb6")], foreground=[("active", TEXT)])
style.configure("Accent.TButton", background=ACCENT, foreground="white", padding=(10, 6), borderwidth=1)
style.map("Accent.TButton", background=[("active", ACCENT2), ("pressed", "#0d6eae")])
style.configure("Active.TButton", background=ACCENT, foreground="white", padding=(9, 6), borderwidth=1)
style.map("Active.TButton", background=[("active", ACCENT2), ("pressed", ACCENT)])
style.configure("TCheckbutton", background=CARD, foreground=TEXT)
style.configure("TRadiobutton", background=CARD, foreground=TEXT)
# Keep disabled Speaker Fill crossover radios inside the dark card palette.
# Some ttk themes otherwise paint disabled TRadiobuttons with the system
# light background, which makes this row look unrelated to the rest of UI.
style.configure("SpeakerFill.TRadiobutton", background=CARD, foreground=TEXT)
style.map("SpeakerFill.TRadiobutton",
          background=[("disabled", CARD), ("active", CARD)],
          foreground=[("disabled", MUTED), ("active", TEXT)])
style.configure("TCombobox", fieldbackground=PANEL2, background=PANEL2, foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
style.map("TCombobox", fieldbackground=[("readonly", PANEL2)], background=[("readonly", PANEL2)], foreground=[("readonly", TEXT)])
style.configure("TEntry", fieldbackground=PANEL2, foreground=TEXT, insertcolor=TEXT, bordercolor=BORDER)
style.configure("TSpinbox", fieldbackground=PANEL2, foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER)
style.configure("Treeview", background=PANEL2, fieldbackground=PANEL2, foreground=TEXT, bordercolor=BORDER)
style.configure("Treeview.Heading", background=PANEL, foreground=TEXT)

# Tk widgets (Canvas/Label/Button) should inherit the same dark palette unless
# they explicitly choose another color. This prevents system light colors from
# leaking into the interface on KDE/GNOME themes.
root.option_add("*Background", BG)
root.option_add("*Foreground", TEXT)
root.option_add("*selectBackground", ACCENT)
root.option_add("*selectForeground", "white")
root.option_add("*insertBackground", TEXT)

# Canvas-backed Creative-style slider.  Tk's native Scale uses the widget
# background for the thumb, which made the control nearly disappear on the
# dark theme.  This keeps the same get/set/command API while drawing a clearly
# visible blue track and light thumb at all times.
class ModernScale(tk.Canvas):
    def __init__(self, master, from_=0, to=100, resolution=1, orient="horizontal",
                 length=200, command=None, showvalue=True, variable=None, **kwargs):
        self.from_ = float(from_)
        self.to = float(to)
        self.resolution = float(resolution) if resolution else 0.0
        self.orient_name = str(orient)
        self.vertical = self.orient_name in ("vertical", "v", str(tk.VERTICAL))
        self.length_px = int(length)
        self.command = command
        self.showvalue = bool(showvalue)
        self.variable = variable
        self._dragging = False
        self._hover = False
        self._value = self.from_
        width = 58 if self.vertical else self.length_px
        height = self.length_px if self.vertical else 42
        super().__init__(master, width=width, height=height, bg=CARD,
                         highlightthickness=0, bd=0, relief="flat",
                         takefocus=1)
        if variable is not None:
            try:
                self._value = float(variable.get())
                variable.trace_add("write", self._variable_changed)
            except Exception:
                pass
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        # Redraw whenever Tk gives the canvas its real geometry. Without this,
        # the active blue fill can be calculated from the tiny pre-layout size
        # and only appear after a hover forces another draw.
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<MouseWheel>", self._wheel)
        self.bind("<Up>", lambda e: self._step(-1 if self.vertical else 1))
        self.bind("<Down>", lambda e: self._step(1 if self.vertical else -1))
        self.bind("<Left>", lambda e: self._step(-1))
        self.bind("<Right>", lambda e: self._step(1))
        self.after_idle(self._draw)

    def cget(self, key):
        if key == "orient":
            return self.orient_name
        if key == "length":
            return self.length_px
        return super().cget(key)

    def _variable_changed(self, *_):
        try:
            v = float(self.variable.get())
        except Exception:
            return
        if abs(v - self._value) > 1e-9:
            self._value = self._clamp(v)
            self._draw()

    def _clamp(self, value):
        lo, hi = sorted((self.from_, self.to))
        value = max(lo, min(hi, float(value)))
        if self.resolution:
            value = self.from_ + round((value - self.from_) / self.resolution) * self.resolution
            value = max(lo, min(hi, value))
        return value

    def _fraction(self):
        span = self.to - self.from_
        return 0.0 if span == 0 else (self._value - self.from_) / span

    def _value_from_xy(self, x, y):
        pad = 11
        if self.vertical:
            usable = max(1, self.winfo_height() - 2 * pad)
            frac = (y - pad) / usable
        else:
            usable = max(1, self.winfo_width() - 2 * pad)
            frac = (x - pad) / usable
        frac = max(0.0, min(1.0, frac))
        return self._clamp(self.from_ + frac * (self.to - self.from_))

    def _set_user(self, value):
        value = self._clamp(value)
        if abs(value - self._value) < 1e-9:
            return
        self._value = value
        if self.variable is not None:
            try:
                self.variable.set(value)
            except Exception:
                pass
        self._draw()
        if self.command:
            try:
                self.command(str(value))
            except TypeError:
                self.command()

    def _press(self, event):
        self.focus_set()
        self._dragging = True
        self._set_user(self._value_from_xy(event.x, event.y))

    def _motion(self, event):
        if self._dragging:
            self._set_user(self._value_from_xy(event.x, event.y))

    def _release(self, _event):
        self._dragging = False

    def _enter(self, _event):
        self._hover = True
        self._draw()

    def _leave(self, _event):
        self._hover = False
        self._draw()

    def _wheel(self, event):
        step = self.resolution or 1.0
        self._set_user(self._value + (step if event.delta > 0 else -step))
        return "break"

    def _step(self, direction):
        self._set_user(self._value + direction * (self.resolution or 1.0))
        return "break"

    def set(self, value):
        self._value = self._clamp(value)
        if self.variable is not None:
            try:
                self.variable.set(self._value)
            except Exception:
                pass
        self._draw()

    def get(self):
        return self._value

    def _draw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        pad = 11
        frac = max(0.0, min(1.0, self._fraction()))
        track = "#2d3b45"
        accent = "#1599e5"
        accent_hi = "#58c2ff"
        thumb_fill = "#e9f5fb" if not self._hover else "#ffffff"
        thumb_outline = accent_hi if self._hover or self._dragging else accent
        if self.vertical:
            x = 20
            y0, y1 = pad, h - pad
            y = y0 + frac * (y1 - y0)
            self.create_line(x, y0, x, y1, fill=track, width=6, capstyle="round")
            self.create_line(x, y, x, y1, fill=accent, width=5, capstyle="round")
            r = 7
            self.create_oval(x-r, y-r, x+r, y+r, fill=thumb_fill, outline=thumb_outline, width=2)
            if self.showvalue:
                self.create_text(31, y, text=f"{self._value:.1f}", fill="#dff4ff",
                                 font=("Arial", 8, "bold"), anchor="w")
        else:
            x0, x1 = pad, w - pad
            y = 15
            x = x0 + frac * (x1 - x0)
            self.create_line(x0, y, x1, y, fill=track, width=6, capstyle="round")
            self.create_line(x0, y, x, y, fill=accent, width=5, capstyle="round")
            r = 7
            self.create_oval(x-r, y-r, x+r, y+r, fill=thumb_fill, outline=thumb_outline, width=2)
            if self.showvalue:
                self.create_text(w-4, 31, text=f"{self._value:.1f}", fill="#dff4ff",
                                 font=("Arial", 8, "bold"), anchor="e")

def slider_style(scale):
    # ModernScale is already fully drawn; retained for compatibility with the
    # existing UI construction calls.
    if isinstance(scale, ModernScale):
        return

header = tk.Frame(root, bg=BG)
header.pack(fill="x", padx=18, pady=(12, 6))
tk.Label(header, text=APP_NAME, bg=BG, fg=TEXT, font=("Arial", 21, "bold")).pack(side="left")
connection_dot = tk.Label(header, text="●", bg=BG, fg=WARN, font=("Arial", 15, "bold"))
connection_dot.pack(side="right", padx=(8, 0))
tk.Label(header, textvariable=connection_var, bg=BG, fg=TEXT, font=("Arial", 10)).pack(side="right")

# Dedicated warning/status strip.
gain_strip = tk.Frame(root, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
gain_strip.pack(fill="x", padx=18, pady=(0, 9))
headroom_label = tk.Label(gain_strip, text="", bg=CARD, fg=GOOD, font=("Arial", 11, "bold"), anchor="w")
headroom_label.pack(side="left", padx=(12, 16), pady=7)
gain_detail_var = tk.StringVar(value="")
gain_detail_label = tk.Label(gain_strip, textvariable=gain_detail_var, bg=CARD, fg=MUTED, font=("Arial", 10), anchor="e")
gain_detail_label.pack(side="right", padx=12, pady=7)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=18, pady=(0, 7))

# ---------- EQ & Levels ----------
eq_tab = ttk.Frame(notebook, padding=8); notebook.add(eq_tab, text="▥  EQ & Levels")
eq_tab.columnconfigure(0, weight=3); eq_tab.columnconfigure(1, weight=2)
eq_tab.rowconfigure(1, weight=1)

# Preset recall stays full-width because it is used constantly and is compact.
preset_box = ttk.LabelFrame(eq_tab, text=" PRESET RECALL ", padding=6)
preset_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 7))
builtin_row = ttk.Frame(preset_box, style="Card.TFrame"); builtin_row.pack(fill="x")
ttk.Label(builtin_row, text="Built-in", width=9, style="Card.TLabel").pack(side="left")
for name in BUILTIN_PRESETS:
    b=ttk.Button(builtin_row,text=name,command=lambda n=name:load_builtin(n)); b.pack(side="left",padx=2); builtin_preset_buttons[name]=b
ttk.Label(builtin_row,text="Active:",style="Card.TLabel").pack(side="left",padx=(12,3))
ttk.Label(builtin_row,textvariable=preset_var,style="Card.TLabel",font=("Arial",10,"bold")).pack(side="left")
ttk.Button(builtin_row,text="Reset EQ",command=reset_controls).pack(side="right",padx=2)
custom_row=ttk.Frame(preset_box,style="Card.TFrame"); custom_row.pack(fill="x",pady=(4,0))
ttk.Label(custom_row,text="Custom",width=9,style="Card.TLabel").pack(side="left")
for slot in ("1","2","3","4","5"):
    b=ttk.Button(custom_row,text=DATA["custom_presets"][slot].get("name",f"Custom {slot}"),command=lambda s=slot:load_custom(s)); b.pack(side="left",padx=2); custom_recall_buttons[slot]=b

# Main page uses two dense columns.  The analyzer belongs under the EQ so the
# entire left column reads top-to-bottom as shaping -> visualization -> preamp.
left = ttk.Frame(eq_tab, style="Card.TFrame", padding=8); left.grid(row=1,column=0,sticky="nsew",padx=(0,4))
right = ttk.Frame(eq_tab, style="Card.TFrame", padding=8); right.grid(row=1,column=1,sticky="nsew",padx=(4,0))
left.columnconfigure(0, weight=1); left.rowconfigure(1, weight=3); left.rowconfigure(2, weight=2)
right.columnconfigure(0, weight=1); right.rowconfigure(0, weight=0); right.rowconfigure(1, weight=1); right.rowconfigure(2, weight=0)

proc_bar=ttk.Frame(left,style="Card.TFrame"); proc_bar.grid(row=0,column=0,sticky="ew",pady=(0,5))
ttk.Checkbutton(proc_bar,text="MASTER BYPASS",variable=bypass_var,command=toggle_bypass).pack(side="left")
ttk.Checkbutton(proc_bar,text="Safe Headroom",variable=safe_headroom_var,command=on_safe_toggle).pack(side="left",padx=12)
mute_button=ttk.Button(proc_bar,text="MUTE",command=toggle_mute,width=9); mute_button.pack(side="left",padx=(4,7))
ttk.Label(proc_bar,textvariable=mute_state_var,style="Card.TLabel",font=("Arial",10,"bold")).pack(side="left")

eq_frame=ttk.LabelFrame(left,text=" LIVE 10-BAND EQUALIZER ",padding=6); eq_frame.grid(row=1,column=0,sticky="nsew")
eq_sliders={}
for col,freq in enumerate(BANDS):
    eq_frame.columnconfigure(col,weight=1)
    ttk.Label(eq_frame,text=f"{freq//1000}k" if freq>=1000 else str(freq),style="Card.TLabel").grid(row=0,column=col,padx=1)
    s=ModernScale(eq_frame,from_=20,to=-20,resolution=.5,orient="vertical",length=220,command=lambda _v,f=freq:on_eq_slider(f),showvalue=True)
    slider_style(s); s.set(CURRENT_EQ[freq]); s.grid(row=1,column=col,padx=1,sticky="ns"); eq_sliders[freq]=s

analyzer_frame=ttk.LabelFrame(left,text=" SPECTRUM ANALYZER ",padding=6); analyzer_frame.grid(row=2,column=0,sticky="nsew",pady=(6,0))
analyzer_canvas=tk.Canvas(analyzer_frame,width=690,height=170,bg="#071015",highlightthickness=1,highlightbackground=BORDER)
analyzer_canvas.pack(fill="both",expand=True)
ttk.Label(analyzer_frame,textvariable=analyzer_status_var,style="Muted.TLabel",wraplength=680).pack(anchor="w",pady=(3,0))

preamp_box=ttk.LabelFrame(left,text=" PREAMP ",padding=6); preamp_box.grid(row=3,column=0,sticky="ew",pady=(6,0))
cur=DATA["current"]
def hslider(parent,label,start,end,value,row,col=0,command=None,length=280,resolution=.5):
    ttk.Label(parent,text=label,width=14,anchor="e",style="Card.TLabel").grid(row=row,column=col,padx=5,pady=2)
    s=ModernScale(parent,from_=start,to=end,resolution=resolution,orient="horizontal",length=length,command=command,showvalue=True)
    slider_style(s); s.set(value); s.grid(row=row,column=col+1,sticky="ew",padx=4); return s
preamp_box.columnconfigure(1,weight=1)
preamp=hslider(preamp_box,"Master Preamp",6,-24,cur["preamp"],0,0,on_preamp_slider,390)

# Live discrete channel meters share the right column with persistent speaker
# calibration. They read the processed hardware monitor, so these are actual
# output levels rather than decorative indicators.
meters_frame=ttk.LabelFrame(right,text=f" {ACTIVE_LAYOUT} LIVE OUTPUT LEVELS (dBFS) ",padding=6); meters_frame.grid(row=0,column=0,sticky="ew")
channel_meter_canvas=tk.Canvas(meters_frame,width=430,height=150,bg="#071015",highlightthickness=1,highlightbackground=BORDER)
channel_meter_canvas.pack(fill="x",expand=True)

levels_frame=ttk.LabelFrame(right,text=f" {ACTIVE_LAYOUT} CHANNEL LEVELS (%) ",padding=8); levels_frame.grid(row=1,column=0,sticky="nsew",pady=(7,0))
levels_frame.columnconfigure(1,weight=1)
channel_sliders={}
for idx,key in enumerate(CHANNEL_KEYS):
    channel_sliders[key]=hslider(levels_frame,CHANNEL_LABELS[key],0,100,cur.get(key,100.0),idx,0,on_channel_slider,250,1)

# Compact signature card uses otherwise-dead lower-right space.
signature_box=ttk.LabelFrame(right,text=" SYSTEM SIGNATURE ",padding=6); signature_box.grid(row=2,column=0,sticky="ew",pady=(7,0))
signature_photo=None
if SIGNATURE_IMAGE.exists():
    try:
        signature_photo=tk.PhotoImage(file=str(SIGNATURE_IMAGE))
        # Keep the artwork present without allowing it to dictate the page height.
        if signature_photo.width() > 180 or signature_photo.height() > 180:
            signature_photo = signature_photo.subsample(2,2)
        sig=tk.Label(signature_box,image=signature_photo,bg=CARD,borderwidth=0); sig.image=signature_photo; sig.pack(side="right",padx=4,pady=2)
    except Exception:
        signature_photo=None
if signature_photo is None:
    tk.Label(signature_box,text="⚡  !!ZuEs!!",bg=CARD,fg="#d9c391",font=("Arial",18,"bold")).pack(side="right",padx=10,pady=12)
ttk.Label(signature_box,text="Sound Blaster Linux Control Center\n!!ZuEs!!",style="Muted.TLabel",justify="left").pack(side="left",padx=8)

# Bass Management state (optional DSP controls, disabled by default)
bass_management_var=tk.BooleanVar(value=cur.get("bass_management",False))
bass_crossover_var=tk.StringVar(value=str(cur.get("bass_crossover",80)))
lfe_lowpass_var=tk.StringVar(value=str(cur.get("lfe_lowpass",120)))
speaker_highpass_var=tk.StringVar(value=str(cur.get("speaker_highpass",80)))
lfe_trim_var=tk.DoubleVar(value=cur.get("lfe_trim",0.0))
bass_slope_var=tk.StringVar(value=str(cur.get("bass_slope","24")))
bass_routing_var=tk.StringVar(value=str(cur.get("bass_routing","REDIRECT")))

def save_bass_management(*args):
    DATA["current"]["bass_management"]=bool(bass_management_var.get())
    crossover=int(bass_crossover_var.get())
    DATA["current"]["bass_crossover"]=crossover
    DATA["current"]["lfe_lowpass"]=crossover
    DATA["current"]["speaker_highpass"]=crossover
    DATA["current"]["lfe_trim"]=float(lfe_trim_var.get())
    DATA["current"]["bass_slope"]=str(bass_slope_var.get())
    DATA["current"]["bass_routing"]=str(bass_routing_var.get())
    save_data(DATA); update_crossover_graph()
    if is_bazzite():
        status_var.set("Bass Management saved; Bazzite EQ routing remains unchanged")
    elif apply_bass_management_live(DATA["current"]):
        persist_bass_management_config(DATA["current"])
        status_var.set("Bass Management updated live")
    else:
        status_var.set("Bass Management saved; reinstall/rebuild once to activate the v3.3.22 DSP graph")

def bass_tone(freq,lfe=False):
    if not shutil.which("speaker-test"): return
    ch=max(2,len(ACTIVE_POSITIONS))
    if is_bazzite():
        backend=speaker_test_backend()
        target_channel=6 if lfe and "LFE" in ACTIVE_POSITIONS else 1
    else:
        target=DATA["current"].get("hardware_sink",SINK)
        if target and sink_exists(target): set_default_sink(target)
        backend="pulse"
        target_channel=6 if lfe and "LFE" in ACTIVE_POSITIONS else 1
    env=os.environ.copy()
    subprocess.Popen(["speaker-test","-D",backend,"-c",str(ch),"-t","sine","-f",str(freq),"-s",str(target_channel),"-l","1"],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def update_crossover_graph(*_):
    c=globals().get("crossover_canvas")
    if not c:return
    c.delete("curve"); w=max(c.winfo_width(),420); h=max(c.winfo_height(),155)
    fc=max(40.,float(bass_crossover_var.get() or 80)); slope=float(bass_slope_var.get() or 24)
    def xf(f):return 34+(math.log10(f/30.)/math.log10(250./30.))*(w-54)
    def yd(db):return 18+(-db/30.)*(h-40)
    hp=[];lp=[]
    for i in range(181):
        f=30.*(250./30.)**(i/180.); hpdb=max(-30.,slope*math.log2(f/fc)) if f<fc else 0.; lpdb=max(-30.,-slope*math.log2(f/fc)) if f>fc else 0.
        hp += [xf(f),yd(hpdb)]; lp += [xf(f),yd(lpdb)]
    c.create_line(*hp,width=2,fill=ACCENT2,tags="curve"); c.create_line(*lp,width=2,fill="#55c47a",dash=(5,3),tags="curve")
    x=xf(fc); c.create_line(x,15,x,h-18,fill=MUTED,dash=(2,3),tags="curve"); c.create_text(x+4,12,text=f"{int(fc)} Hz",fill=TEXT,anchor="nw",tags="curve")

# ---------- Spatial / Fill ----------
spatial_tab=ttk.Frame(notebook,padding=10); notebook.add(spatial_tab,text="◖  Spatial / Fill")
spatial_tab.columnconfigure(0,weight=1); spatial_tab.columnconfigure(1,weight=1)
fill_frame=ttk.LabelFrame(spatial_tab,text=" SPEAKER FILL ",padding=12); fill_frame.grid(row=0,column=0,sticky="new",padx=(0,5),pady=(0,8))
fill_mode=tk.StringVar(value=cur["fill_mode"])
speaker_fill_lfe_buttons=[]
def update_speaker_fill_lfe_state():
    state="disabled" if fill_mode.get()=="OFF" else "normal"
    for button in speaker_fill_lfe_buttons: button.configure(state=state)
def on_fill_mode_change():
    update_speaker_fill_lfe_state(); schedule_spatial_apply()
for i,mode in enumerate(("OFF","PSD","FULL")):
    ttk.Radiobutton(fill_frame,text=mode,variable=fill_mode,value=mode,command=on_fill_mode_change).grid(row=0,column=i,padx=12,pady=3)
ttk.Label(fill_frame,text="OFF = native channels   •   PSD = ambient surround   •   FULL = stronger all-speaker fill",style="Muted.TLabel",wraplength=540).grid(row=1,column=0,columnspan=3,sticky="w",pady=(8,0))

spatial_controls=ttk.LabelFrame(spatial_tab,text=" LIVE SPATIAL CONTROLS ",padding=12); spatial_controls.grid(row=1,column=0,sticky="new",padx=(0,5),pady=(0,8))
ttk.Label(spatial_controls,text="Rear Delay",style="Card.TLabel").grid(row=0,column=0,sticky="e")
rear_delay=ModernScale(spatial_controls,from_=0,to=30,resolution=1,orient="horizontal",length=420,command=schedule_spatial_apply); slider_style(rear_delay); rear_delay.set(cur["rear_delay"]); rear_delay.grid(row=0,column=1,padx=10)
ttk.Label(spatial_controls,text="Stereo Width",style="Card.TLabel").grid(row=1,column=0,sticky="e")
stereo_width=ModernScale(spatial_controls,from_=0,to=1,resolution=.05,orient="horizontal",length=420,command=schedule_spatial_apply); slider_style(stereo_width); stereo_width.set(cur["stereo_width"]); stereo_width.grid(row=1,column=1,padx=10)
ttk.Label(spatial_controls,text="Speaker Fill LFE Crossover",style="Card.TLabel").grid(row=2,column=0,sticky="e")
lfe_cutoff=tk.StringVar(value=str(cur["lfe_cutoff"])); cross=ttk.Frame(spatial_controls,style="Card.TFrame"); cross.grid(row=2,column=1,sticky="w",padx=10)
for hz in (80,100,120,150,180):
    button=ttk.Radiobutton(cross,text=f"{hz} Hz",variable=lfe_cutoff,value=str(hz),command=schedule_spatial_apply,style="SpeakerFill.TRadiobutton"); button.pack(side="left",padx=4); speaker_fill_lfe_buttons.append(button)
update_speaker_fill_lfe_state()
ttk.Label(spatial_controls,text="These controls update live without recreating the PipeWire stream.",style="Muted.TLabel").grid(row=3,column=0,columnspan=2,sticky="w",pady=(8,0))

bass_frame=ttk.LabelFrame(spatial_tab,text=" BASS MANAGEMENT ",padding=12); bass_frame.grid(row=0,column=1,rowspan=2,sticky="nsew",padx=(5,0),pady=(0,8))
ttk.Checkbutton(bass_frame,text="Enable Bass Management",variable=bass_management_var,command=save_bass_management).grid(row=0,column=0,columnspan=4,sticky="w",pady=(0,6))
ttk.Label(bass_frame,text="Crossover",style="Card.TLabel").grid(row=1,column=0,sticky="e")
for i,hz in enumerate((60,80,100,120)): ttk.Radiobutton(bass_frame,text=f"{hz} Hz",variable=bass_crossover_var,value=str(hz),command=save_bass_management).grid(row=1,column=i+1,padx=2)
ttk.Label(bass_frame,text="Slope",style="Card.TLabel").grid(row=2,column=0,sticky="e")
for i,(val,label) in enumerate((("12","12 dB/oct"),("24","24 dB/oct"))): ttk.Radiobutton(bass_frame,text=label,variable=bass_slope_var,value=val,command=save_bass_management).grid(row=2,column=i+1,sticky="w")
ttk.Label(bass_frame,text="Bass Routing",style="Card.TLabel").grid(row=3,column=0,sticky="e")
for i,(val,label) in enumerate((("LFE_ONLY","LFE only"),("REDIRECT","Redirected"),("DUPLICATE","Full duplicate"))): ttk.Radiobutton(bass_frame,text=label,variable=bass_routing_var,value=val,command=save_bass_management).grid(row=3,column=i+1,sticky="w",padx=2)
ttk.Label(bass_frame,text="LFE Trim",style="Card.TLabel").grid(row=4,column=0,sticky="e")
lfe_trim_scale=ModernScale(bass_frame,from_=-12,to=12,resolution=.5,orient="horizontal",variable=lfe_trim_var,command=save_bass_management,length=270); slider_style(lfe_trim_scale); lfe_trim_scale.grid(row=4,column=1,columnspan=3,sticky="w")
tone_frame=ttk.Frame(bass_frame,style="Card.TFrame"); tone_frame.grid(row=5,column=0,columnspan=4,pady=6,sticky="w")
ttk.Label(tone_frame,text="Bass Test:",style="Card.TLabel").pack(side="left")
for f in (50,80,120): ttk.Button(tone_frame,text=f"{f} Hz",command=lambda x=f:bass_tone(x)).pack(side="left",padx=3)
ttk.Button(tone_frame,text="LFE only",command=lambda:bass_tone(80,True)).pack(side="left",padx=3)
crossover_canvas=tk.Canvas(bass_frame,height=180,bg="#071015",highlightthickness=1,highlightbackground=BORDER); crossover_canvas.grid(row=6,column=0,columnspan=4,sticky="ew",pady=(6,2)); crossover_canvas.bind("<Configure>",update_crossover_graph)
root.after(200,update_crossover_graph)

# ---------- Presets & Test ----------
tools_tab=ttk.Frame(notebook,padding=10); notebook.add(tools_tab,text="★  Presets & Test")
tools_tab.columnconfigure(0,weight=1); tools_tab.columnconfigure(1,weight=2); tools_tab.rowconfigure(0,weight=1)
custom_frame=ttk.LabelFrame(tools_tab,text=" CUSTOM PRESET LIBRARY ",padding=12); custom_frame.grid(row=0,column=0,sticky="nsew",padx=(0,5))
for row,slot in enumerate(("1","2","3","4","5")):
    lbl=ttk.Label(custom_frame,text="",width=25,style="Card.TLabel"); lbl.grid(row=row,column=0,sticky="w",padx=5,pady=6); custom_name_labels[slot]=lbl
    ttk.Button(custom_frame,text="Save / Rename",command=lambda s=slot:save_custom(s)).grid(row=row,column=1,padx=5,pady=4)
ttk.Label(custom_frame,text="EQ presets do not alter your persistent speaker trims or master preamp.",style="Muted.TLabel",wraplength=350).grid(row=6,column=0,columnspan=2,sticky="w",pady=(14,0))

speaker_frame=ttk.LabelFrame(tools_tab,text=f" {ACTIVE_LAYOUT} SPEAKER TEST — ROOM VIEW ",padding=12); speaker_frame.grid(row=0,column=1,sticky="nsew",padx=(5,0))
for c in range(5):speaker_frame.columnconfigure(c,weight=1)
for r in range(5):speaker_frame.rowconfigure(r,weight=1)
def make_speaker_test_button(channel,label,row,col):
    btn=tk.Button(speaker_frame,text=f"▣\n{label}",command=lambda c=channel:test_speaker(c),bg=PANEL2,fg=TEXT,activebackground=ACCENT,activeforeground="white",relief="flat",bd=0,width=13,height=3,font=("Arial",10,"bold"),highlightthickness=1,highlightbackground=BORDER)
    btn.grid(row=row,column=col,padx=12,pady=8,sticky="nsew"); speaker_test_buttons[channel]=btn
_room={"FL":("Front Left",0,0),"FR":("Front Right",0,4),"FC":("Center",0,2),"LFE":("Sub / LFE",1,1),"RL":("Rear Left",4,0),"RR":("Rear Right",4,4),"SL":("Rear Left",4,0),"SR":("Rear Right",4,4)}
for _p in ACTIVE_POSITIONS:
    if _p in _room:_label,_r,_c=_room[_p];make_speaker_test_button(_p,_label,_r,_c)
ttk.Label(speaker_frame,text="LISTENER",style="Card.TLabel",font=("Arial",12,"bold")).grid(row=2,column=2,padx=20,pady=16)
ttk.Label(speaker_frame,text="Click a speaker to send a short test tone. The active speaker highlights.",style="Muted.TLabel").grid(row=5,column=0,columnspan=5,pady=(10,0))

# ---------- Line Input ----------
line_tab=ttk.Frame(notebook,padding=10); notebook.add(line_tab,text="♩  Line Input")
line_tab.columnconfigure(0,weight=1)
line_box=ttk.LabelFrame(line_tab,text=" INPUT MONITOR THROUGH OUTPUT PROCESSING ",padding=14); line_box.grid(row=0,column=0,sticky="new")
ttk.Label(line_box,text="Choose the Sound Blaster capture device and its physical input port. Monitoring is routed through the same output EQ and speaker processing.",style="Card.TLabel",wraplength=950).grid(row=0,column=0,columnspan=3,sticky="w",pady=(0,10))
line_source_var=tk.StringVar(); line_port_var=tk.StringVar(); line_port_map={}
input_level_var=tk.DoubleVar(value=float(DATA["current"].get("input_level",100.0)))
mic_boost_var=tk.DoubleVar(value=float(DATA["current"].get("mic_boost_db",0.0)))
input_gain_text=tk.StringVar(value=input_gain_summary(input_level_var.get(),mic_boost_var.get()))

def update_input_gain_label(*_):
    input_gain_text.set(input_gain_summary(input_level_var.get(),mic_boost_var.get()))

def apply_input_gain(*_):
    DATA["current"]["input_level"]=round(float(input_level_var.get()),1)
    DATA["current"]["mic_boost_db"]=round(float(mic_boost_var.get()),1)
    save_data(DATA)
    update_input_gain_label()
    src=line_source_var.get()
    if src and set_input_gain(src,input_level_var.get(),mic_boost_var.get()):
        status_var.set(f"Input level {input_level_var.get():.0f}% • Mic boost +{mic_boost_var.get():.0f} dB")

def on_line_port_selected(*_):
    port=line_port_map.get(line_port_var.get(),"")
    if port:
        set_source_port(line_source_var.get(),port)
    # Keep a previously chosen boost value but make the status explicit when a
    # non-microphone port is selected; users can still use it as software gain.
    apply_input_gain()

ttk.Label(line_box,text="Capture Device",style="Card.TLabel").grid(row=1,column=0,sticky="e",padx=(0,8))
line_combo=ttk.Combobox(line_box,textvariable=line_source_var,state="readonly",width=78); line_combo.grid(row=1,column=1,sticky="ew",pady=4)
ttk.Button(line_box,text="Refresh",command=lambda:refresh_line_sources()).grid(row=1,column=2,padx=(8,0))
ttk.Label(line_box,text="Physical Input",style="Card.TLabel").grid(row=2,column=0,sticky="e",padx=(0,8))
line_port_combo=ttk.Combobox(line_box,textvariable=line_port_var,state="readonly",width=48); line_port_combo.grid(row=2,column=1,sticky="w",pady=4)
line_box.columnconfigure(1,weight=1)

# Capture gain controls. Input Level is the normal capture level; Mic Boost is
# additional software gain and is useful on cards/drivers that do not expose a
# separate hardware boost control to PipeWire.
gain_box=ttk.LabelFrame(line_box,text=" INPUT GAIN ",padding=10); gain_box.grid(row=3,column=0,columnspan=3,sticky="ew",pady=(10,4))
gain_box.columnconfigure(1,weight=1)
ttk.Label(gain_box,text="Input Level",style="Card.TLabel").grid(row=0,column=0,sticky="e",padx=(0,8))
input_level_scale=ModernScale(gain_box,from_=0,to=100,resolution=1,orient="horizontal",variable=input_level_var,command=apply_input_gain,length=420); slider_style(input_level_scale); input_level_scale.grid(row=0,column=1,sticky="w")
ttk.Label(gain_box,textvariable=input_gain_text,style="Muted.TLabel").grid(row=0,column=2,sticky="w",padx=(10,0))
ttk.Label(gain_box,text="Mic Boost",style="Card.TLabel").grid(row=1,column=0,sticky="e",padx=(0,8))
mic_boost_scale=ModernScale(gain_box,from_=0,to=30,resolution=1,orient="horizontal",variable=mic_boost_var,command=apply_input_gain,length=420); slider_style(mic_boost_scale); mic_boost_scale.grid(row=1,column=1,sticky="w")
ttk.Label(gain_box,text="0 to +30 dB software gain",style="Muted.TLabel").grid(row=1,column=2,sticky="w",padx=(10,0))

mic_proc_box=ttk.LabelFrame(line_box,text=" MICROPHONE PROCESSING ",padding=10); mic_proc_box.grid(row=4,column=0,columnspan=3,sticky="ew",pady=(8,4))
mic_proc_box.columnconfigure(1,weight=1)
mic_processing_var=tk.BooleanVar(value=bool(DATA["current"].get("mic_processing",False)))
mic_noise_var=tk.BooleanVar(value=bool(DATA["current"].get("mic_noise_reduction",True)))
mic_noise_strength_var=tk.DoubleVar(value=float(DATA["current"].get("mic_noise_strength",50.0)))
mic_low_var=tk.DoubleVar(value=float(DATA["current"].get("mic_eq_low",0.0)))
mic_mid_var=tk.DoubleVar(value=float(DATA["current"].get("mic_eq_mid",0.0)))
mic_high_var=tk.DoubleVar(value=float(DATA["current"].get("mic_eq_high",0.0)))
mic_apply_job=None

def save_mic_processing_state():
    c=DATA["current"]
    c["mic_processing"]=bool(mic_processing_var.get())
    c["mic_noise_reduction"]=bool(mic_noise_var.get())
    c["mic_noise_strength"]=round(float(mic_noise_strength_var.get()),1)
    c["mic_eq_low"]=round(float(mic_low_var.get()),1)
    c["mic_eq_mid"]=round(float(mic_mid_var.get()),1)
    c["mic_eq_high"]=round(float(mic_high_var.get()),1)
    c["mic_source"]=line_source_var.get()
    save_data(DATA)

def apply_mic_processing_live(*_):
    global mic_apply_job
    save_mic_processing_state()
    if mic_apply_job is not None:
        try: root.after_cancel(mic_apply_job)
        except Exception: pass
    def _do():
        global mic_apply_job
        mic_apply_job=None
        if mic_processing_var.get() and live_set_mic_processing(DATA["current"]):
            status_var.set("Microphone EQ / noise reduction updated live")
    mic_apply_job=root.after(80,_do)

def rebuild_mic_source():
    save_mic_processing_state()
    src=line_source_var.get()
    try:
        write_mic_processing_config(src,DATA["current"])
        status_var.set("Restarting audio to update processed microphone…")
        root.update_idletasks()
        restart_audio(DATA["current"].get("hardware_sink"))
        if mic_processing_var.get():
            status_var.set("Processed microphone ready — select 'Sound Blaster Processed Mic' in your voice app")
        else:
            status_var.set("Processed microphone disabled")
    except Exception as e:
        messagebox.showerror(APP_NAME,f"Could not update microphone processing:\n\n{e}",parent=root)

proc_top=ttk.Frame(mic_proc_box,style="Card.TFrame"); proc_top.grid(row=0,column=0,columnspan=3,sticky="ew",pady=(0,5))
ttk.Checkbutton(proc_top,text="Enable Processed Mic",variable=mic_processing_var).pack(side="left")
ttk.Checkbutton(proc_top,text="Noise Reduction",variable=mic_noise_var,command=apply_mic_processing_live).pack(side="left",padx=(16,0))
ttk.Button(proc_top,text="Apply / Rebuild Mic Source",style="Accent.TButton",command=rebuild_mic_source).pack(side="right")

def mic_slider(label,var,row):
    ttk.Label(mic_proc_box,text=label,style="Card.TLabel").grid(row=row,column=0,sticky="e",padx=(0,8))
    sc=ModernScale(mic_proc_box,from_=-12,to=12,resolution=.5,orient="horizontal",variable=var,command=apply_mic_processing_live,length=360); slider_style(sc); sc.grid(row=row,column=1,sticky="w")
    return sc

mic_slider("EQ Low 160 Hz",mic_low_var,1)
mic_slider("EQ Mid 1.8 kHz",mic_mid_var,2)
mic_slider("EQ High 6 kHz",mic_high_var,3)
ttk.Label(mic_proc_box,text="Noise Strength",style="Card.TLabel").grid(row=4,column=0,sticky="e",padx=(0,8))
mic_noise_scale=ModernScale(mic_proc_box,from_=0,to=100,resolution=1,orient="horizontal",variable=mic_noise_strength_var,command=apply_mic_processing_live,length=360); slider_style(mic_noise_scale); mic_noise_scale.grid(row=4,column=1,sticky="w")
ttk.Label(mic_proc_box,text="PipeWire noise gate; higher values reject more low-level background noise.",style="Muted.TLabel",wraplength=390).grid(row=4,column=2,sticky="w",padx=(10,0))

def refresh_line_ports(*_):
    global line_port_map
    vals=source_ports(line_source_var.get()); line_port_map={label:name for name,label,_active in vals}
    labels=[label for _name,label,_active in vals]; line_port_combo["values"]=labels
    active=next((label for _name,label,a in vals if a),"")
    if labels: line_port_var.set(active or labels[0])
    else: line_port_var.set("")
    update_input_gain_label()
def refresh_line_sources():
    vals=list_sources(); line_combo["values"]=vals
    preferred=[x for x in vals if "creative" in x.lower() or "ca0132" in x.lower() or "line" in x.lower()]
    if vals and (line_source_var.get() not in vals): line_source_var.set((preferred or vals)[0])
    refresh_line_ports()
def start_line_ui():
    port=line_port_map.get(line_port_var.get(),"")
    if port and not set_source_port(line_source_var.get(),port):
        messagebox.showerror(APP_NAME,"Could not switch the selected physical input port.",parent=root);return
    if start_line_monitor(line_source_var.get(),DATA["current"].get("hardware_sink","")):status_var.set(f"Monitoring {line_port_var.get() or line_source_var.get()} through EQ")
    else:messagebox.showerror(APP_NAME,"Could not start line-input monitoring. Ensure pw-loopback is installed and select an input.",parent=root)
def stop_line_ui():stop_line_monitor();status_var.set("Line input monitoring stopped")
line_combo.bind("<<ComboboxSelected>>",lambda e:(refresh_line_ports(),apply_input_gain()))
line_port_combo.bind("<<ComboboxSelected>>",on_line_port_selected)
line_buttons=ttk.Frame(line_box,style="Card.TFrame"); line_buttons.grid(row=5,column=1,sticky="w",pady=(10,2))
ttk.Button(line_buttons,text="Monitor Through EQ",style="Accent.TButton",command=start_line_ui).pack(side="left",padx=(0,6))
ttk.Button(line_buttons,text="Stop Monitor",command=stop_line_ui).pack(side="left",padx=6)
ttk.Label(line_box,text="The monitor is session-only. Selecting Line In or Microphone changes the existing PipeWire source port. Input Level and Mic Boost are saved and restored. Processed Mic is a separate selectable source with voice EQ and noise reduction.",style="Muted.TLabel",wraplength=950).grid(row=6,column=0,columnspan=3,sticky="w",pady=(10,0))
refresh_line_sources()
root.after(250,apply_input_gain)

# ---------- Device Setup ----------
device_tab=ttk.Frame(notebook,padding=10); notebook.add(device_tab,text="⚙  Device Setup")
device_tab.columnconfigure(0,weight=1); device_tab.columnconfigure(1,weight=1)
device_box=ttk.LabelFrame(device_tab,text=" OUTPUT DEVICE ",padding=14); device_box.grid(row=0,column=0,sticky="new",padx=(0,5))
ttk.Label(device_box,text="Physical output target",style="Card.TLabel").pack(anchor="w")
device_row=ttk.Frame(device_box,style="Card.TFrame"); device_row.pack(fill="x",pady=10)
device_var=tk.StringVar(value=cur.get("hardware_sink",""));device_combo=ttk.Combobox(device_row,textvariable=device_var,state="readonly",width=62);device_combo.pack(side="left",fill="x",expand=True)
ttk.Button(device_row,text="Rescan",command=refresh_device_list).pack(side="left",padx=6)
ttk.Button(device_row,text="Use Selected",style="Accent.TButton",command=apply_device_target).pack(side="left")
retry_row = ttk.Frame(device_box, style="Card.TFrame")
retry_row.pack(fill="x", pady=(8,0))
ttk.Button(retry_row, text="Retry EQ", command=lambda: reconnect_now(silent=False)).pack(side="left")
ttk.Label(retry_row, text="Manual recovery only — the working AC3 5.1 fallback is never restarted automatically.", style="Muted.TLabel").pack(side="left", padx=(10,0))
ttk.Button(device_box,text="Reconnect Now",command=reconnect_now).pack(anchor="w",pady=10)
ttk.Label(device_box,text="The channel layout is detected from the selected PipeWire sink and the controls adapt from stereo through 5.1.",style="Muted.TLabel",wraplength=560).pack(anchor="w")

about_box=ttk.LabelFrame(device_tab,text=" PACKAGE / SYSTEM ",padding=14); about_box.grid(row=0,column=1,sticky="new",padx=(5,0))
ttk.Label(about_box,text=f"{APP_NAME} v{VERSION}",style="Card.TLabel",font=("Arial",13,"bold")).pack(anchor="w")
ttk.Label(about_box,text=f"Detected layout: {ACTIVE_LAYOUT}\nChannels: {' '.join(ACTIVE_POSITIONS)}\nPipeWire live EQ • spectrum analyzer • spatial fill • bass management • input monitor",style="Muted.TLabel",justify="left",wraplength=560).pack(anchor="w",pady=(8,0))
contact_frame=ttk.Frame(about_box,style="Card.TFrame")
contact_frame.pack(fill="x",pady=(14,0))
ttk.Label(contact_frame,text="Created by !!ZuEs!!",style="Card.TLabel",font=("Arial",11,"bold")).pack(anchor="w")
ttk.Label(contact_frame,text="Contact: GitHub Issues",style="Muted.TLabel").pack(anchor="w",pady=(2,0))
if SIGNATURE_IMAGE.exists():
    try:
        dev_sig=tk.PhotoImage(file=str(SIGNATURE_IMAGE)); dev_sig_lbl=tk.Label(about_box,image=dev_sig,bg=CARD,borderwidth=0); dev_sig_lbl.image=dev_sig; dev_sig_lbl.pack(anchor="e",pady=(10,0))
    except Exception:pass

# Real bottom status bar.
bottom=tk.Frame(root,bg="#050b0f",highlightthickness=1,highlightbackground=BORDER);bottom.pack(fill="x",padx=18,pady=(0,10))
tk.Label(bottom,text="PipeWire / WirePlumber",bg="#050b0f",fg=MUTED).pack(side="left",padx=10,pady=5)
tk.Label(bottom,text=f"Layout: {ACTIVE_LAYOUT}",bg="#050b0f",fg=MUTED).pack(side="left",padx=10)
tk.Label(bottom,textvariable=status_var,bg="#050b0f",fg=GOOD).pack(side="left",padx=18)
tk.Label(bottom,text=f"{VERSION}  •  !!ZuEs!!",bg="#050b0f",fg="#d9c391").pack(side="right",padx=10)

# Initialize
gui_ready = True
# Reassert saved EQ, channel calibration and Safe Headroom on every normal launch.
# Run the bounded verification off the Tk event thread so startup remains responsive.
threading.Thread(target=restore_gui_audio_state, daemon=True).start()
# Highlight a matching saved preset name when possible. If no exact recall key can
# be established, the UI simply reports Current until the user selects one.
saved_name = DATA["current"].get("last_preset", "Current")
for _name in BUILTIN_PRESETS:
    if saved_name == _name:
        active_preset_key = f"builtin:{_name}"
for _slot, _entry in DATA["custom_presets"].items():
    if saved_name == _entry.get("name") and _entry.get("settings"):
        active_preset_key = f"custom:{_slot}"
refresh_preset_labels(); refresh_device_list(); update_mute_button(); update_headroom_warning()
update_connection_status(); start_analyzer()
root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
