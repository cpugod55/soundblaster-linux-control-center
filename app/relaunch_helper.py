#!/usr/bin/env python3
"""Persistent per-user relaunch helper for Sound Blaster Linux Control Center.

The GUI intentionally exits while Output Setup rewrites/reloads the audio graph.
A long-lived user service owns this helper, so repeated GUI restarts do not depend
on the lifetime of a transient terminal or transient systemd unit.
"""

import argparse
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

APP_ID = "soundblaster-zse-control"
SERVICE_NAME = "soundblaster-zse-relaunch-helper.service"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/{os.getuid()}"))
SOCKET_PATH = RUNTIME_DIR / f"{APP_ID}-relaunch-helper.sock"
COOLDOWN_PATH = RUNTIME_DIR / f"{APP_ID}-relaunch-cooldown"
LAUNCHER = Path.home() / ".local/bin" / APP_ID


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def launch_after_exit(old_pid: int) -> None:
    # Serialize restarts. A second request can arrive while the previous GUI is
    # still alive; each request waits for its own old GUI to disappear first.
    with launch_after_exit.lock:
        deadline = time.monotonic() + 20.0
        while pid_alive(old_pid) and time.monotonic() < deadline:
            time.sleep(0.10)

        # Give the old GUI's socket/lock cleanup and desktop session a short
        # settling window before creating the replacement process.
        time.sleep(3.0)

        if not LAUNCHER.exists():
            return

        # Cross-instance guard: the replacement GUI reads this timestamp and
        # keeps Output Setup disabled briefly while the rebuilt graph settles.
        try:
            COOLDOWN_PATH.write_text(str(time.time()))
        except Exception:
            pass

        launch_env = os.environ.copy()
        launch_env["SOUNDBLASTER_OUTPUT_SETUP_RELAUNCH"] = "1"
        proc = subprocess.Popen(
            [str(LAUNCHER)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
            env=launch_env,
        )
        # Reap the child eventually without blocking the request listener.
        threading.Thread(target=proc.wait, daemon=True).start()


launch_after_exit.lock = threading.Lock()


def serve() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    try:
        SOCKET_PATH.unlink()
    except FileNotFoundError:
        pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(SOCKET_PATH))
    os.chmod(SOCKET_PATH, 0o600)
    server.listen(4)

    try:
        while True:
            conn, _ = server.accept()
            with conn:
                raw = conn.recv(128).decode("utf-8", "replace").strip()
                try:
                    old_pid = int(raw)
                except ValueError:
                    conn.sendall(b"ERR\n")
                    continue
                threading.Thread(target=launch_after_exit, args=(old_pid,), daemon=True).start()
                conn.sendall(b"OK\n")
    finally:
        server.close()
        try:
            SOCKET_PATH.unlink()
        except FileNotFoundError:
            pass


def request_restart(old_pid: int) -> int:
    def try_request() -> bool:
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(2.0)
            client.connect(str(SOCKET_PATH))
            client.sendall(f"{old_pid}\n".encode())
            reply = client.recv(32)
            client.close()
            return reply.startswith(b"OK")
        except OSError:
            return False

    if try_request():
        return 0

    # The installer normally keeps the helper running. This fallback covers a
    # manually stopped service or a fresh desktop session where it is not up yet.
    subprocess.run(
        ["systemctl", "--user", "start", SERVICE_NAME],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    for _ in range(20):
        time.sleep(0.10)
        if try_request():
            return 0
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=int, metavar="OLD_PID")
    args = parser.parse_args()
    if args.request is not None:
        return request_restart(args.request)
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
