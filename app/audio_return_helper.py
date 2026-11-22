#!/usr/bin/env python3
"""Vendor-neutral PipeWire default-output observer for SBLCC.

No Tk, no new audio graph, no headset-specific code. It invokes the
already-installed controller's headless --restore-selected operation only when
Linux chooses our Sound Blaster sink. It does not set the system default itself.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

APP_ID = "soundblaster-zse-control"
STATE = Path.home() / ".config" / APP_ID / "state.json"
CONTROL = Path.home() / ".local" / "lib" / APP_ID / "control.py"
RUNTIME = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/{os.getuid()}"))
LOCK = RUNTIME / f"{APP_ID}.lock"
WATCH_LOCK = RUNTIME / f"{APP_ID}-audio-return.lock"
POLL = 2.5


def command(*args, timeout=8):
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def configured_target():
    try:
        data = json.loads(STATE.read_text())
        return str(data.get("current", {}).get("hardware_sink") or "")
    except (ValueError, OSError, AttributeError, TypeError):
        return ""


def is_selected(default, target):
    if not target or not default:
        return False
    if default in ("soundblaster_zse_eq", "soundblaster_zse_fill", target):
        return True
    if not target.startswith("alsa_output.") or not default.startswith("alsa_output."):
        return False
    return target.rsplit(".", 1)[0] == default.rsplit(".", 1)[0]


def gui_running():
    # The controller holds an exclusive flock for its GUI lifetime.
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return False
        except BlockingIOError:
            return True


def default_output():
    r = command("pactl", "get-default-sink")
    return r.stdout.strip() if r and r.returncode == 0 else ""


def recover():
    if not CONTROL.exists() or gui_running():
        return False
    r = command("/usr/bin/python3", str(CONTROL), "--restore-selected", timeout=24)
    return bool(r and r.returncode == 0)


def playback_signature():
    """Track *routing*, not just the default name (which can stay unchanged).

    Only use sink-input IDs and their sink assignments. No vendor, headset,
    player, or application names are interpreted here.
    """
    result = command("pactl", "list", "short", "sink-inputs")
    if result is None or result.returncode != 0:
        return None
    pairs = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0].isdigit():
            pairs.append((fields[0], fields[1]))
    return tuple(sorted(pairs))


def observe(default, target, signature, previous):
    """Return whether the selected Sound Blaster needs a recovery check.

    Do not interpret unrelated default outputs as permission to make changes.
    """
    if signature is None or not is_selected(default, target):
        return False
    if previous is None:
        return True
    old_default, old_target, old_signature = previous
    return (default, target, signature) != (old_default, old_target, old_signature)


def watch(once=False):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with WATCH_LOCK.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        previous = None
        # One repair per external routing change, with a fresh baseline after
        # our own changes so moving a stream to Fill doesn't trigger a loop.
        while True:
            default = default_output()
            target = configured_target()
            signature = playback_signature()
            if observe(default, target, signature, previous):
                recover()
                # Capture the resulting routing as our new baseline.
                signature = playback_signature()
            if default and signature is not None:
                previous = (default, target, signature)
            if once:
                break
            time.sleep(POLL)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    raise SystemExit(watch(once=args.once))
